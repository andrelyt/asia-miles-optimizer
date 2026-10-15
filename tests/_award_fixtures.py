"""SYNTHETIC TEST ONLY: no actual services, quotes, personal leave or account balances."""
import copy

from discovery.award_adapter import rules_digest
from discovery.candidate_generator import generate_candidates
from discovery.route_graph import load_route_graph, stable_id
from tests._route_fixtures import config, edge, graph_data, rules, travel_request


def reidentify(candidate):
    candidate['candidate_id'] = stable_id('candidate_', {k: v for k, v in candidate.items()
                                                       if k not in ('candidate_id', 'strategies')})
    return candidate


def candidate(strategy='ALL_J', mode='SINGLE_AWARD', carriers=None, three=False, window=None):
    request = travel_request()
    request['planning_year'] = 2027 if window else 2026
    edges = ([edge(), edge('BBB', 'DDD', 800), edge('DDD', 'CCC', 6000), edge('CCC', 'AAA', 6500)]
             if three else graph_data()['edges'])
    if carriers:
        for e, carrier in zip(edges, carriers):
            e['operating_carrier'] = carrier
    cfg = config(); cfg['route_search'].update(max_flight_legs_per_trip=4, max_connections=3)
    result = generate_candidates(load_route_graph(graph_data(edges)), request, rules(), window=window, config=cfg)
    row = next(c for c in result['candidates'] if strategy in c['strategies'] and c['ticketing_mode'] == mode)
    return copy.deepcopy(row), request, rules()


def source(level='SUPPLIED_CONFIRMED'):
    return {'evidence_level': level, 'source_url': 'https://example.invalid/TEST_SYNTHETIC_EVIDENCE',
            'observed_at': '2026-10-15T00:00:00Z', 'note': 'SYNTHETIC TEST ONLY; no actual quote or confirmation'}


def bound(c, r, level='SUPPLIED_CONFIRMED'):
    return dict(source(level), candidate_id=c['candidate_id'], rules_digest=rules_digest(r),
                rules_as_of=r['as_of'], rules_version=r['version'], booking_date='2026-10-15',
                travel_start_date=(c.get('holiday_window') or {}).get('start_date', '2026-12-01'),
                travel_end_date=(c.get('holiday_window') or {}).get('end_date', '2026-12-05'))


def evidence(c, request, r, quote_miles=10000):
    window = c.get('holiday_window')
    year = request['planning_year']
    review = dict(bound(c, r), decision='APPLICABLE', booking_date='2026-10-15',
                  travel_start_date=window['start_date'] if window else f'{year}-12-01',
                  travel_end_date=window['end_date'] if window else f'{year}-12-05')
    data = {'rule_review': review, 'quotes': {}, 'ticket_data': {}}
    for t in c['tickets']:
        if t['proposed_scheme'] == 'standard':
            data['quotes'][t['ticket_id']] = dict(bound(c, r, 'AIRLINE_QUOTED'), miles_per_person=quote_miles)
        elif t['proposed_scheme'] == 'standard_mixed':
            data['ticket_data'][t['ticket_id']] = {
                **bound(c, r), 'transfer_hours': 2, 'transfer_evidence': source(),
                'distance_confirmations': {str(i): dict(source(), distance_miles=c['legs'][i]['distance_miles'])
                                           for i in t['leg_indices']}}
    for entry in list(data['quotes'].values()) + list(data['ticket_data'].values()):
        for key in ('booking_date', 'travel_start_date', 'travel_end_date'):
            entry[key] = review[key]
    return data
