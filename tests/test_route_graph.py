import copy
import json
from pathlib import Path
import tempfile
import unittest

from discovery._validation import ValidationError
from discovery.route_graph import load_route_graph, route_status
from tests._route_fixtures import config, edge, graph_data


class RouteGraphTests(unittest.TestCase):
    def test_schema_path_load_and_preserved_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'graph.json'; path.write_text(json.dumps(graph_data()))
            graph = load_route_graph(path)
        row = graph.find_paths('AAA', 'CCC')['paths'][0][0]
        self.assertEqual(row['source_url'], 'https://example.invalid/synthetic-route-test')
        self.assertEqual(row['distance_source'], 'SYNTHETIC_TEST_DISTANCE')
        self.assertEqual(row['observed_at'], '2026-10-01T00:00:00Z')
        self.assertEqual(row['route_status'], 'VERIFIED')

    def test_only_explicit_directed_edges_no_reverse_or_invented_routes(self):
        graph = load_route_graph(graph_data([edge()]))
        self.assertEqual(len(graph.find_paths('AAA', 'BBB')['paths']), 1)
        self.assertFalse(graph.find_paths('BBB', 'AAA')['paths'])
        self.assertFalse(graph.find_paths('AAA', 'CCC')['paths'])
        self.assertFalse(graph.find_paths('AAA', 'AAA')['paths'])

    def test_connected_paths_and_cycles_not_expanded(self):
        graph = load_route_graph(graph_data([edge(), edge('BBB', 'AAA'), edge('BBB', 'CCC')]))
        result = graph.find_paths('AAA', 'CCC')
        self.assertEqual(len(result['paths']), 1)
        self.assertEqual([(e['origin'], e['destination']) for e in result['paths'][0]], [('AAA', 'BBB'), ('BBB', 'CCC')])
        for path in result['paths']:
            airports = [path[0]['origin']] + [e['destination'] for e in path]
            self.assertEqual(len(set(airports)), len(airports))

    def test_schema_numeric_distance_and_cabin_rejection(self):
        for value in (0, -1, True, '800', float('nan'), float('inf')):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError): load_route_graph(graph_data([edge(distance=value)]))
        for cabins in ([], ['Z'], ['J', 'J']):
            with self.assertRaises(ValidationError): load_route_graph(graph_data([edge(cabins=cabins)]))
        data = graph_data(); data['edges'][0]['unknown'] = True
        with self.assertRaises(ValidationError): load_route_graph(data)
        data = graph_data(); data['edges'][0]['origin'] = 'aa'
        with self.assertRaises(ValidationError): load_route_graph(data)

    def test_invalid_dates_selfloops_and_conflicts_rejected(self):
        for row in (edge(valid_from='2026-12-01', valid_until='2026-01-01'), edge(valid_from='2026-02-30'), edge('AAA', 'AAA')):
            with self.assertRaises(ValidationError): load_route_graph(graph_data([row]))
        with self.assertRaisesRegex(ValidationError, 'conflicting'):
            load_route_graph(graph_data([edge(), edge(distance=999)]))
        self.assertEqual(len(load_route_graph(graph_data([edge(), edge()])).edges()), 1)

    def test_verified_missing_source_downgraded_without_promoting_others(self):
        graph = load_route_graph(graph_data([edge(source_url=None), edge('BBB', 'CCC', status='STALE')]))
        path = graph.find_paths('AAA', 'CCC')['paths'][0]
        self.assertEqual(path[0]['declared_route_status'], 'VERIFIED')
        self.assertEqual(path[0]['route_status'], 'UNVERIFIED')
        self.assertEqual(route_status(path), 'UNVERIFIED')
        self.assertIn('VERIFIED_WITHOUT_SOURCE_URL', path[0]['evidence_notes'])
        row = load_route_graph(graph_data([edge(status='UNVERIFIED')])).edges()[0]
        self.assertEqual(row['route_status'], 'UNVERIFIED')

    def test_expired_snapshot_becomes_stale_and_validity_dates_filter(self):
        graph = load_route_graph(graph_data([edge(valid_from='2026-01-01', valid_until='2026-09-30')]))
        self.assertEqual(graph.edges()[0]['route_status'], 'STALE')
        self.assertFalse(graph.find_paths('AAA', 'BBB', travel_date='2026-10-01')['paths'])
        self.assertEqual(len(graph.find_paths('AAA', 'BBB', travel_date='2026-09-30')['paths']), 1)
        graph = load_route_graph(graph_data([edge(valid_from='2027-01-01')]))
        self.assertFalse(graph.find_paths('AAA', 'BBB', travel_date='2026-12-31')['paths'])
        self.assertTrue(graph.find_paths('AAA', 'BBB', travel_date='2027-01-01')['paths'])

    def test_empty_evidence_is_not_verified_and_malformed_url_is_safe(self):
        self.assertEqual(route_status([]), 'UNVERIFIED')
        graph = load_route_graph(graph_data([edge(source_url='http://[')]))
        self.assertEqual(graph.edges()[0]['route_status'], 'UNVERIFIED')

    def test_search_leg_and_connection_limits_come_from_config(self):
        graph = load_route_graph(graph_data())
        cfg = config(); cfg['route_search']['max_connections'] = 0
        self.assertFalse(graph.find_paths('AAA', 'CCC', cfg)['paths'])
        cfg['route_search']['max_connections'] = 2; cfg['route_search']['max_flight_legs_per_trip'] = 1
        self.assertFalse(graph.find_paths('AAA', 'CCC', cfg)['paths'])
        cfg['route_search']['max_flight_legs_per_trip'] = 2
        self.assertTrue(graph.find_paths('AAA', 'CCC', cfg)['paths'])
        self.assertFalse(graph.find_paths('AAA', 'CCC', cfg, max_legs=1)['paths'])

    def test_beam_and_raw_path_caps_are_deterministic(self):
        data = graph_data([edge('AAA', 'BBB'), edge('BBB', 'DDD'), edge('AAA', 'CCC'), edge('CCC', 'DDD')])
        graph = load_route_graph(data); cfg = config(); cfg['route_search']['beam_width'] = 1
        result = graph.find_paths('AAA', 'DDD', cfg)
        self.assertEqual(len(result['paths']), 1); self.assertTrue(result['diagnostics']['beam_truncated'])
        cfg['route_search']['beam_width'] = 10; cfg['route_search']['max_raw_paths_per_od'] = 1
        result = graph.find_paths('AAA', 'DDD', cfg)
        self.assertEqual(len(result['paths']), 1); self.assertTrue(result['diagnostics']['path_limit_reached'])
        data['edges'].reverse()
        self.assertEqual(result, load_route_graph(data).find_paths('AAA', 'DDD', cfg))

    def test_normalization_repeat_and_defensive_copy(self):
        data = graph_data(); before = copy.deepcopy(data); graph = load_route_graph(data)
        a = graph.find_paths('AAA', 'CCC')
        self.assertEqual(a, graph.find_paths('AAA', 'CCC'))
        data['edges'].reverse()
        for row in data['edges']: row['cabins'].reverse()
        self.assertEqual(a, load_route_graph(data).find_paths('AAA', 'CCC'))
        a['paths'][0][0]['cabins'].clear()
        self.assertTrue(graph.find_paths('AAA', 'CCC')['paths'][0][0]['cabins'])
        data['edges'].reverse()
        for row in data['edges']: row['cabins'].reverse()
        self.assertEqual(data, before)

    def test_invalid_config_and_empty_graph_diagnostics(self):
        graph = load_route_graph(graph_data([]))
        self.assertEqual(graph.find_paths('AAA', 'CCC')['diagnostics']['code'], 'NO_PATH_WITHIN_BOUNDS')
        for key, value in (('beam_width', 0), ('max_connections', -1), ('max_raw_paths_per_od', True)):
            cfg = config(); cfg['route_search'][key] = value
            with self.assertRaises(ValidationError): graph.find_paths('AAA', 'CCC', cfg)
        with self.assertRaises(ValidationError): graph.find_paths('bad', 'CCC')


if __name__ == '__main__': unittest.main()
