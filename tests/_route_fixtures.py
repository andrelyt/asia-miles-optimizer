"""Synthetic route relationships only; no actual airline/service assertions."""
import json
from pathlib import Path

from tests._fixtures import request

ROOT = Path(__file__).resolve().parents[1]


def rules():
    return json.loads((ROOT / 'rules_2026_10.json').read_text())


def config():
    return json.loads((ROOT / 'config/search_config.json').read_text())


def edge(origin='AAA', destination='BBB', distance=800, carrier='CX', status='VERIFIED', cabins=None, **extra):
    data = {'origin': origin, 'destination': destination, 'operating_carrier': carrier,
            'distance_miles': distance, 'distance_source': 'SYNTHETIC_TEST_DISTANCE',
            'cabins': cabins if cabins is not None else ['Y', 'W', 'J', 'F'], 'route_status': status,
            'source_url': 'https://example.invalid/synthetic-route-test',
            'observed_at': '2026-10-01T00:00:00Z'}
    data.update(extra)
    return data


def graph_data(edges=None):
    return {'snapshot_id': 'TEST_SYNTHETIC_ROUTES_NOT_REAL_SERVICES',
            'observed_at': '2026-10-15T00:00:00Z',
            'edges': edges if edges is not None else [edge(), edge('BBB', 'CCC', 6000), edge('CCC', 'AAA', 6500)]}


def travel_request():
    data = request()
    data['origin_airports'] = ['AAA']
    data['destinations'] = [{'type': 'airport', 'value': 'CCC', 'priority': 'required'}]
    data['cabin_preferences'].update(longhaul_minimum='Y', allow_asymmetric_roundtrip=True)
    return data
