import copy
import json
import unittest

from discovery._validation import ValidationError
from discovery.candidate_generator import generate_candidates, STRATEGIES
from discovery.route_graph import load_route_graph
from tests._route_fixtures import config, edge, graph_data, rules, travel_request


class CandidateGeneratorTests(unittest.TestCase):
    def generate(self, data=None, request=None, cfg=None, window=None, rule_data=None):
        return generate_candidates(load_route_graph(data if data is not None else graph_data()),
                                   request if request is not None else travel_request(),
                                   rule_data if rule_data is not None else rules(), window=window, config=cfg)

    def test_required_cabin_strategies_and_separate_ticket_variants(self):
        result = self.generate(); rows = result['candidates']
        self.assertEqual({s for c in rows for s in c['strategies']}, set(STRATEGIES))
        for strategy in STRATEGIES:
            self.assertTrue(any(strategy in c['strategies'] and c['ticketing_mode'] == 'SINGLE_AWARD' for c in rows), strategy)
            self.assertTrue(any(strategy in c['strategies'] and c['ticketing_mode'] == 'SEPARATE_AWARDS' for c in rows), strategy)
        jy = next(c for c in rows if 'LONG_J_SHORT_Y' in c['strategies'] and c['ticketing_mode'] == 'SINGLE_AWARD')
        self.assertEqual([l['cabin'] for l in jy['legs']], ['Y', 'J', 'J'])
        self.assertEqual(jy['tickets'][0]['proposed_scheme'], 'standard_mixed')
        self.assertEqual(jy['tickets'][0]['leg_indices'], [0, 1])
        asym = next(c for c in rows if 'OUTBOUND_W_RETURN_J' in c['strategies'])
        self.assertEqual([l['cabin'] for l in asym['legs']], ['W', 'W', 'J'])

    def test_no_unsupported_cabin_and_no_invented_edges(self):
        data = graph_data(); data['edges'][0]['cabins'] = ['Y']
        data['edges'][1]['cabins'] = ['Y', 'J']; data['edges'][2]['cabins'] = ['Y', 'J']
        rows = self.generate(data=data)['candidates']; self.assertTrue(rows)
        available = {(e['origin'], e['destination'], e['operating_carrier']): e for e in data['edges']}
        for c in rows:
            for leg in c['legs']:
                raw = available[(leg['origin'], leg['destination'], leg['operating_carrier'])]
                self.assertIn(leg['cabin'], raw['cabins'])
        self.assertFalse(any('ALL_W' in c['strategies'] for c in rows))
        self.assertFalse(self.generate(data=graph_data([edge(), edge('BBB', 'CCC', 6000)]))['candidates'])

    def test_hard_minimum_not_weakened_for_y_baseline(self):
        request = travel_request(); request['cabin_preferences']['longhaul_minimum'] = 'W'
        rows = self.generate(request=request)['candidates']; self.assertTrue(rows)
        self.assertFalse(any('ALL_Y' in c['strategies'] for c in rows))
        for c in rows:
            self.assertTrue(all(l['cabin'] in ('W', 'J', 'F') for l in c['legs'] if l['long_haul']))
        request['cabin_preferences']['longhaul_minimum'] = 'F'
        request['cabin_preferences']['longhaul_preferred'] = 'F'
        self.assertTrue(self.generate(request=request)['candidates'])

    def test_soft_preference_is_reported_not_hard_filtered(self):
        request = travel_request(); request['cabin_preferences'].update(longhaul_minimum='W', longhaul_preferred='J')
        rows = self.generate(request=request)['candidates']
        self.assertTrue(any(c['longhaul_preferred_met'] is True for c in rows))
        self.assertTrue(any(c['longhaul_preferred_met'] is False for c in rows))

    def test_preferences_disable_asymmetric_mixed_and_separate(self):
        request = travel_request(); request['cabin_preferences'].update(allow_mixed_cabin=False, allow_separate_tickets=False, allow_asymmetric_roundtrip=False)
        rows = self.generate(request=request)['candidates']; self.assertTrue(rows)
        self.assertTrue(all(c['ticketing_mode'] == 'SINGLE_AWARD' for c in rows))
        self.assertFalse(any(s.startswith('OUTBOUND_') for c in rows for s in c['strategies']))
        for c in rows:
            for direction in ('outbound', 'return'):
                self.assertEqual(len({l['cabin'] for l in c['legs'] if l['direction'] == direction}), 1)

    def test_mixed_capability_uses_supplied_rules_not_hardcoded_carrier(self):
        data = graph_data()
        for e in data['edges']: e['operating_carrier'] = 'ZZ'
        rows = self.generate(data=data)['candidates']
        pending = next(c for c in rows if 'LONG_J_SHORT_Y' in c['strategies'] and c['ticketing_mode'] == 'SINGLE_AWARD')
        self.assertIsNone(pending['tickets'][0]['proposed_scheme'])
        self.assertEqual(pending['tickets'][0]['structure_status'], 'NEEDS_PARTNER_AGREEMENT_AND_QUOTE')
        self.assertTrue(any('LONG_J_SHORT_Y' in c['strategies'] and c['ticketing_mode'] == 'SEPARATE_AWARDS' for c in rows))
        supplied = rules(); supplied['standard_mixed_constraints']['allowed_carriers'] = ['ZZ']
        supplied['standard_award_constraints']['primary_carrier'] = 'ZZ'  # Synthetic policy fixture only.
        priced_shape = next(c for c in self.generate(data=data, rule_data=supplied)['candidates']
                            if 'LONG_J_SHORT_Y' in c['strategies'] and c['ticketing_mode'] == 'SINGLE_AWARD')
        self.assertEqual(priced_shape['tickets'][0]['proposed_scheme'], 'standard_mixed')

    def test_different_carriers_are_not_assumed_same_ticket(self):
        data = graph_data(); data['edges'][0]['operating_carrier'] = 'ZZ'
        rows = self.generate(data=data)['candidates']; self.assertTrue(rows)
        self.assertTrue(any(c['ticketing_mode'] == 'SEPARATE_AWARDS' for c in rows))
        same = next(c for c in rows if c['ticketing_mode'] == 'SINGLE_AWARD')
        self.assertIn('PARTNER_AGREEMENT_REQUIRED', same['tickets'][0]['requirements'])
        self.assertEqual(same['pricing_status'], 'UNKNOWN')

    def test_whole_roundtrip_leg_and_connection_caps(self):
        cfg = config(); cfg['route_search']['max_flight_legs_per_trip'] = 2
        self.assertFalse(self.generate(cfg=cfg)['candidates'])
        cfg['route_search']['max_flight_legs_per_trip'] = 3
        rows = self.generate(cfg=cfg)['candidates']; self.assertTrue(rows)
        self.assertTrue(all(len(c['legs']) <= 3 for c in rows))
        cfg['route_search']['max_connections'] = 0
        self.assertFalse(self.generate(cfg=cfg)['candidates'])
        cfg['route_search']['max_flight_legs_per_trip'] = 1
        self.assertTrue(any(d['code'] == 'SEARCH_LIMIT_NO_ROUNDTRIP' for d in self.generate(cfg=cfg)['diagnostics']))

    def test_per_strategy_limit_and_ticketing_diversity(self):
        cfg = config(); cfg['candidate_generation']['max_candidates_per_strategy'] = 2
        rows = self.generate(cfg=cfg)['candidates']
        for strategy in STRATEGIES:
            selected = [c for c in rows if strategy in c['strategies']]
            self.assertLessEqual(len(selected), 2)
            self.assertEqual({c['ticketing_mode'] for c in selected}, {'SINGLE_AWARD', 'SEPARATE_AWARDS'})

    def test_diversity_flag_changes_bounded_selection(self):
        data = graph_data(); data['edges'].append(edge('AAA', 'CCC', 6200))
        cfg = config(); cfg['candidate_generation']['max_candidates_per_strategy'] = 2
        diverse = self.generate(data=data, cfg=cfg)['candidates']
        cfg['candidate_generation']['preserve_strategy_diversity'] = False
        sequential = self.generate(data=data, cfg=cfg)['candidates']
        self.assertEqual({c['ticketing_mode'] for c in diverse if 'ALL_J' in c['strategies']}, {'SINGLE_AWARD', 'SEPARATE_AWARDS'})
        self.assertEqual({c['ticketing_mode'] for c in sequential if 'ALL_J' in c['strategies']}, {'SINGLE_AWARD'})

    def test_two_connecting_directions_need_four_total_legs(self):
        data = graph_data([edge(), edge('BBB', 'CCC', 6000), edge('CCC', 'DDD', 6000), edge('DDD', 'AAA')])
        self.assertFalse(self.generate(data=data)['candidates'])
        cfg = config(); cfg['route_search']['max_flight_legs_per_trip'] = 4
        rows = self.generate(data=data, cfg=cfg)['candidates']; self.assertTrue(rows)
        self.assertTrue(all(len(c['legs']) == 4 for c in rows))
        cfg['route_search']['max_connections'] = 1
        self.assertFalse(self.generate(data=data, cfg=cfg)['candidates'])

    def test_route_source_downgrade_reaches_candidate(self):
        data = graph_data(); data['edges'][0]['source_url'] = None
        rows = self.generate(data=data)['candidates']; self.assertTrue(rows)
        self.assertTrue(all(c['route_status'] == 'UNVERIFIED' for c in rows))

    def test_no_phantom_separate_variants_for_two_direct_flights(self):
        data = graph_data([edge('AAA', 'CCC', 6000), edge('CCC', 'AAA', 6000)])
        rows = self.generate(data=data)['candidates']; self.assertTrue(rows)
        self.assertTrue(all(c['ticketing_mode'] == 'SINGLE_AWARD' for c in rows))
        self.assertTrue(any(len(c['strategies']) > 1 for c in rows))

    def test_verified_stale_unverified_are_independent_of_awards(self):
        for status in ('VERIFIED', 'STALE', 'UNVERIFIED'):
            with self.subTest(status=status):
                data = graph_data(); data['edges'][1]['route_status'] = status
                rows = self.generate(data=data)['candidates']; self.assertTrue(rows)
                for c in rows:
                    self.assertEqual(c['route_status'], status)
                    self.assertEqual(c['award_seat_status'], 'NOT_CHECKED')
                    self.assertEqual(c['ticketability_status'], 'NOT_CHECKED')
                    self.assertEqual(c['pricing_status'], 'UNKNOWN')
                    self.assertIsNone(c['miles_per_person']); self.assertIsNone(c['taxes_hkd_per_person'])
                    self.assertFalse(c['complete_price_comparison_eligible'])
                    self.assertTrue(c['rule_version_review_required'])
                    self.assertEqual(c['lifecycle'], 'GENERATED')

    def test_holiday_estimate_propagates_and_date_validity_filters(self):
        window = {'window_id': 'TEST_WINDOW', 'start_date': '2027-01-01', 'end_date': '2027-01-03', 'holiday_status': 'ESTIMATED', 'errors': []}
        rows = self.generate(window=window)['candidates']; self.assertTrue(rows)
        for c in json.loads(json.dumps(rows)):
            self.assertEqual(c['holiday_status'], 'ESTIMATED')
            self.assertTrue(c['holiday_window']['holiday_uncertainty'])
        data = graph_data(); data['edges'][2]['valid_until'] = '2027-01-02'
        self.assertFalse(self.generate(data=data, window=window)['candidates'])
        window['holiday_status'] = 'OFFICIAL'
        window['holiday_evidence'] = [{'source_status': 'ESTIMATED'}]
        self.assertTrue(all(c['holiday_status'] == 'ESTIMATED' for c in self.generate(window=window)['candidates']))

    def test_actual_pr1_window_evidence_reaches_pr2(self):
        from discovery.holiday_calendar import load_calendar
        from discovery.leave_engine import generate_windows
        from tests._fixtures import snapshot
        req = travel_request(); req['planning_year'] = 2027
        result = generate_windows(load_calendar(snapshot(2027)), req,
                                  {'holiday_window': {'days_before': 0, 'days_after': 2, 'max_generated_windows_per_holiday': 30}})
        self.assertTrue(result['windows'])
        window = result['windows'][0]
        rows = self.generate(request=req, window=window)['candidates']; self.assertTrue(rows)
        self.assertTrue(all(c['holiday_window']['window_id'] == window['window_id'] for c in rows))
        self.assertTrue(all(c['holiday_status'] == 'ESTIMATED' for c in rows))
        self.assertTrue(all(c['award_seat_status'] == 'NOT_CHECKED' for c in rows))

    def test_stable_ids_normalized_input_order_and_deduplication(self):
        request = travel_request(); data = graph_data(); cfg = config(); supplied = rules()
        original = copy.deepcopy((request, data, cfg, supplied))
        a = self.generate(data=data, request=request, cfg=cfg, rule_data=supplied)
        self.assertEqual(a, self.generate(data=data, request=request, cfg=cfg, rule_data=supplied))
        request['travelers'].reverse(); data['edges'].reverse()
        for e in data['edges']: e['cabins'].reverse()
        b = self.generate(data=data, request=request, cfg=cfg, rule_data=supplied)
        self.assertEqual(a, b)
        ids = [c['candidate_id'] for c in a['candidates']]
        self.assertEqual(len(ids), len(set(ids)))
        request['travelers'].reverse(); data['edges'].reverse()
        for e in data['edges']: e['cabins'].reverse()
        self.assertEqual((request, data, cfg, supplied), original)
        data['edges'][1]['route_status'] = 'UNVERIFIED'
        changed = self.generate(data=data)['candidates']
        self.assertTrue(set(ids).isdisjoint({c['candidate_id'] for c in changed}))

    def test_destinations_are_not_guessed_or_required_targets_dropped(self):
        req = travel_request(); req['destinations'] = [{'type': 'region', 'value': 'Europe', 'priority': 'required'}]
        result = self.generate(request=req)
        self.assertFalse(result['candidates']); self.assertIn('DESTINATION_RESOLUTION_REQUIRED', {d['code'] for d in result['diagnostics']})
        req['destinations'] += [{'type': 'airport', 'value': 'CCC', 'priority': 'preferred'}]
        self.assertFalse(self.generate(request=req)['candidates'])
        req = travel_request(); req['destinations'].append({'type': 'airport', 'value': 'DDD', 'priority': 'required'})
        self.assertFalse(self.generate(request=req)['candidates'])
        req = travel_request(); del req['destinations']
        self.assertFalse(self.generate(request=req)['candidates'])

    def test_threshold_is_configured_assumption_not_award_policy(self):
        cfg = config(); cfg['candidate_generation']['longhaul_distance_threshold_miles'] = 7000
        rows = self.generate(cfg=cfg)['candidates']; self.assertTrue(rows)
        self.assertTrue(all(not l['long_haul'] for c in rows for l in c['legs']))
        self.assertTrue(all(c['assumptions']['longhaul_distance_threshold_miles'] == 7000 for c in rows))

    def test_invalid_input_and_window_do_not_crash(self):
        request = travel_request(); request['origin_airports'] = ['invalid']
        with self.assertRaises(ValidationError): self.generate(request=request)
        with self.assertRaises(ValidationError): self.generate(window={'start_date': '2027-01-01'})
        window = {'start_date': '2027-01-01', 'end_date': '2027-01-03', 'holiday_status': 'OFFICIAL', 'errors': [{'code': 'BLOCKED_DATE'}]}
        with self.assertRaises(ValidationError): self.generate(window=window)
        cfg = config(); cfg['candidate_generation']['max_candidates_per_strategy'] = 0
        with self.assertRaises(ValidationError): self.generate(cfg=cfg)


if __name__ == '__main__': unittest.main()
