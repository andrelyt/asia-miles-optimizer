"""SYNTHETIC TEST data only: fictional holidays, routes, quotes and payer attestations."""
from discovery.award_pricing import price_candidate
from discovery.candidate_generator import generate_candidates
from discovery.holiday_calendar import load_calendars
from discovery.leave_engine import evaluate_window
from discovery.route_graph import load_route_graph, stable_id
from tests._award_fixtures import evidence, bound, source
from tests._route_fixtures import edge, graph_data, rules, travel_request


def snapshots():
    return [{'calendar_id': 'TEST_SYNTHETIC_NOT_REAL_' + str(y), 'jurisdiction': 'TEST', 'year': y,
             'source_status': 'ESTIMATED', 'source_url': 'https://example.invalid/SYNTHETIC_TEST',
             'days': ([{'date': '2027-01-01', 'day_type': 'PUBLIC_HOLIDAY', 'holiday_name': 'new_year'},
                       {'date': '2027-04-02', 'day_type': 'PUBLIC_HOLIDAY', 'holiday_name': 'qingming'},
                       {'date': '2027-05-07', 'day_type': 'PUBLIC_HOLIDAY', 'holiday_name': 'labor_day'},
                       {'date': '2027-01-02', 'day_type': 'MAKEUP_WORKDAY'}] if y == 2027 else [])}
            for y in (2026, 2027)]


def request():
    req = travel_request(); req['planning_year'] = 2027
    req['holiday_types'] = ['new_year', 'qingming', 'labor_day']; req['max_trips'] = 3
    for t in req['travelers']: t['annual_leave_budget'] = 10
    return req


def calendar():
    return load_calendars(snapshots())


def funding(accounts=('TEST_PAYER',), travelers=('traveler_a', 'traveler_b')):
    return [dict(source(), account_id=a, traveler_id=t, decision='ELIGIBLE',
                 valid_from='2026-01-01', valid_until='2028-12-31') for a in accounts for t in travelers]


def trip(start='2027-01-01', end='2027-01-03', family='new_year', strategy='ALL_J',
         miles=10000, quoted=True, taxes=100, mixed=False, carrier='CX', req=None, cal=None):
    req = req or request(); cal = cal or calendar(); r = rules()
    window = evaluate_window(cal, req, start, end)
    window.update(holiday_type=family, holiday_anchor_date=cal.holiday_dates(req['planning_year'], family)[0].isoformat(), bridge_side='CORE')
    window['window_id'] = stable_id('TEST_window_', window)
    edges = graph_data()['edges'] if mixed else [edge('AAA', 'CCC', 6000, carrier=carrier), edge('CCC', 'AAA', 6000)]
    candidates = generate_candidates(load_route_graph(graph_data(edges)), req, r, window=window)['candidates']
    c = next(c for c in candidates if ('LONG_J_SHORT_Y' if mixed else strategy) in c['strategies'] and c['ticketing_mode'] == 'SINGLE_AWARD')
    ev = evidence(c, req, r, miles) if quoted else {}
    if quoted and taxes is not None: ev['tax_quote'] = dict(bound(c, r, 'AIRLINE_QUOTED'), hkd_per_person=taxes)
    return price_candidate(c, req, r, ev)
