"""D1 bounded holiday portfolios. Independent annual leave/account constraints."""
import copy
import json
from collections import Counter
from pathlib import Path

from optimizer import CABIN_RANK, number
from ._validation import ValidationError, parse_date
from .award_adapter import rules_digest
from .award_pricing import price_candidate
from .leave_engine import _request, evaluate_window
from .portfolio_funding import allocate
from .route_graph import stable_id

CONFIG_PATH = Path(__file__).resolve().parents[1] / 'config/portfolio_config.json'
VIEWS = ('Miles Saver', 'Comfort First', 'Balanced', 'Leave Efficient')


def portfolio_config(supplied=None):
    config = json.loads(CONFIG_PATH.read_text())
    if supplied is not None:
        if isinstance(supplied, dict) and 'max_candidates_per_holiday' in supplied:
            raise ValidationError('use max_candidates_per_window; the former family-wide max_candidates_per_holiday is no longer supported')
        if not isinstance(supplied, dict) or set(supplied) - set(config):
            raise ValidationError('unknown/invalid PR4 configuration')
        config.update(copy.deepcopy(supplied))
    for key in set(config) - {'leave_budgets_by_year'}:
        if type(config[key]) is not int or config[key] < 1:
            raise ValidationError(key + ' must be a positive integer')
    if not isinstance(config['leave_budgets_by_year'], dict):
        raise ValidationError('leave_budgets_by_year must be a mapping')
    return config


def normalized_request(supplied):
    request = _request(supplied)
    for key in ('origin_airports', 'reposition_airports', 'holiday_types'):
        if key in request: request[key] = sorted(request[key])
    if 'destinations' in request:
        request['destinations'] = sorted(request['destinations'], key=lambda d: stable_id('', d))
    for traveler in request['travelers']:
        for key in ('blocked_dates', 'personal_days_off'):
            if key in traveler: traveler[key] = sorted(traveler[key])
    return request


def annual_budgets(request, config):
    travelers = {t['id'] for t in request['travelers']}
    budgets = {str(request['planning_year']): {t['id']: t['annual_leave_budget'] for t in request['travelers']}}
    for year, values in config['leave_budgets_by_year'].items():
        if not isinstance(year, str) or len(year) != 4 or not year.isdigit() or not 1 <= int(year) <= 9999:
            raise ValidationError('annual leave budget year must be YYYY')
        if not isinstance(values, dict) or set(values) != travelers:
            raise ValidationError('each explicit annual budget must cover the whole traveler group')
        for val in values.values():
            if type(val) is not int: raise ValidationError('annual leave budgets must be integers')
            number(val, 'annual leave budget', integer=True)
        budgets[year] = copy.deepcopy(values)
    return budgets


def window_request(request, budgets):
    """PR1 single-window cap is not a per-year cap. Validate actual years in PR4."""
    result = copy.deepcopy(request)
    for t in result['travelers']:
        t['annual_leave_budget'] = sum(v[t['id']] for v in budgets.values())
    return result


def diverse_limit(rows, limit, key, order):
    """Round robin transparent structural classes; no numerical utility score."""
    groups = {}
    for row in sorted(rows, key=order):
        groups.setdefault(key(row), []).append(row)
    result = []
    while len(result) < limit and any(groups.values()):
        for group in groups.values():
            if group and len(result) < limit:
                result.append(group.pop(0))
    return result


def _prepare(row, request, calendar, rules, budgets):
    if not isinstance(row, dict) or not isinstance(row.get('candidate'), dict):
        return None, 'INVALID_PR3_RESULT'
    if row.get('status') == 'UNSUPPORTED' or any(str(d).startswith('INVALID_OR_MISSING_INPUT') for d in row.get('diagnostics', [])):
        return None, 'INVALID_OR_UNSUPPORTED_PR3_RESULT'
    if any('INVALID_STANDARD_QUOTE_MILES' in t.get('diagnostics', []) for t in row.get('tickets', [])):
        return None, 'INVALID_STANDARD_QUOTE_MILES'
    c = row['candidate']
    # Replay supplied evidence through PR3; cached totals and per-trip payer choices
    # are not trusted annual constraints. No account enumeration inside PR3 here.
    priced = price_candidate(c, request, rules, row.get('input_evidence'))
    if priced['status'] == 'UNSUPPORTED' or 'candidate' not in priced:
        return None, 'INVALID_OR_UNSUPPORTED_PR3_RESULT'
    if any('INVALID_STANDARD_QUOTE_MILES' in t.get('diagnostics', []) for t in priced['tickets']):
        return None, 'INVALID_STANDARD_QUOTE_MILES'
    if any(str(d).startswith('INVALID_OR_MISSING_INPUT') for d in priced['diagnostics']):
        return None, 'INVALID_OR_MISSING_PRICING_INPUT'
    prefs = request['cabin_preferences']
    for leg in c['legs']:
        minimum = prefs['longhaul_minimum'] if leg['long_haul'] else prefs['shorthaul_minimum']
        if CABIN_RANK[leg['cabin']] < CABIN_RANK[minimum]:
            return None, 'CABIN_BELOW_MINIMUM'
    window = c.get('holiday_window')
    blockers = []
    leave, years, dates = None, [], None
    if window:
        if not isinstance(window.get('window_id'), str) or not window['window_id']:
            return None, 'WINDOW_ID_REQUIRED'
        try:
            start, end = parse_date(window['start_date']), parse_date(window['end_date'])
            years = [str(y) for y in range(start.year, end.year + 1)]
            if any(y not in budgets for y in years):
                return None, 'ANNUAL_LEAVE_BUDGET_YEAR_MISSING'
            if window.get('holiday_type') not in request['holiday_types']:
                return None, 'HOLIDAY_NOT_REQUESTED'
            anchors = calendar.holiday_dates(request['planning_year'], window['holiday_type'])
            if not anchors or window.get('holiday_anchor_date') != anchors[0].isoformat() or not any(start <= a <= end for a in anchors):
                return None, 'WINDOW_HOLIDAY_ANCHOR_MISMATCH'
            checked = evaluate_window(calendar, window_request(request, budgets), window['start_date'], window['end_date'])
        except ValueError:
            return None, 'CALENDAR_COVERAGE_OR_WINDOW_INVALID'
        if not request.get('leave_constraints', {}).get('allow_bridge_leave', True) and any(
                d < anchors[0].isoformat() or d > anchors[-1].isoformat()
                for values in checked['leave_dates_by_traveler'].values() for d in values):
            return None, 'BRIDGE_LEAVE_DISABLED'
        if checked['errors']:
            return None, checked['errors'][0]['code']
        years = [str(y) for y in range(start.year, end.year + 1)]
        if any(y not in budgets for y in years):
            return None, 'ANNUAL_LEAVE_BUDGET_YEAR_MISSING'
        leave = {t: sorted(set(v)) for t, v in checked['leave_dates_by_traveler'].items()}
        for t, values in leave.items():
            for year in years:
                if sum(v.startswith(year + '-') for v in values) > budgets[year][t]:
                    return None, 'ANNUAL_LEAVE_BUDGET_EXCEEDED'
        if (window.get('leave_dates_by_traveler') != checked['leave_dates_by_traveler'] or
                window.get('holiday_status') != checked['holiday_status'] or window.get('errors')):
            return None, 'WINDOW_CALENDAR_EVIDENCE_MISMATCH'
        dates = (window['start_date'], window['end_date'])
    else:
        blockers += ['TRAVEL_DATES_REQUIRED', 'LEAVE_DATES_REQUIRED', 'OVERLAP_NOT_CHECKED']
    if priced['status'] != 'EVALUATED':
        blockers.append(priced['status'])
    tickets = priced['tickets']
    complete_miles = len(tickets) == len(c['tickets']) and all(t['miles_per_person'] is not None for t in tickets)
    known = sum(t['miles_per_person'] for t in tickets if t['miles_per_person'] is not None) * len(c['traveler_ids'])
    if not complete_miles:
        blockers.append('COMPLETE_MILEAGE_REQUIRED')
    tax = priced['taxes_hkd_per_person']
    return {'candidate_id': c['candidate_id'], 'priced': priced, 'candidate': c, 'dates': dates,
            'window_key': window['window_id'] if window else 'UNRESOLVED_DATES',
            'holiday_key': (window['holiday_type'], window['holiday_anchor_date']) if window else ('UNRESOLVED_DATES',),
            'leave': leave, 'years': years, 'blockers': blockers, 'known_miles': known,
            'total_miles': known if complete_miles else None,
            'taxes_hkd': tax * len(c['traveler_ids']) if tax is not None else None}, None


def _portfolio(trips, request, budgets, balances, eligibility, counter, config):
    traveler_ids = sorted(t['id'] for t in request['travelers'])
    if len({t['holiday_key'] for t in trips}) != len(trips):
        return None, 'SAME_HOLIDAY_ALTERNATIVE'
    dated = sorted(t['dates'] for t in trips if t['dates'])
    if any(b[0] <= a[1] for a, b in zip(dated, dated[1:])):
        return None, 'OVERLAPPING_TRIPS'
    leave = {tid: {} for tid in traveler_ids}
    for trip in trips:
        if trip['leave'] is None:
            continue
        for tid, values in trip['leave'].items():
            for year in trip['years']:
                leave[tid].setdefault(year, set()).update(v for v in values if v.startswith(year + '-'))
    for tid, years in leave.items():
        if any(len(days) > budgets[year][tid] for year, days in years.items()):
            return None, 'ANNUAL_LEAVE_BUDGET_EXCEEDED'
    missing = {reason for t in trips for reason in t['blockers']}
    jobs = []
    for trip in trips:
        review = trip['priced'].get('rule_review') or {}
        for ticket in trip['priced']['tickets']:
            if ticket['miles_per_person'] is None:
                continue
            for tid in traveler_ids:
                jobs.append({'candidate_id': trip['candidate_id'], 'ticket_id': ticket['ticket_id'],
                             'passenger': tid, 'miles': ticket['miles_per_person'],
                             'start_date': trip['dates'][0] if trip['dates'] else None,
                             'end_date': trip['dates'][1] if trip['dates'] else None,
                             'booking_date': review.get('booking_date'),
                             'booking_year': review.get('booking_date', '')[:4] or None})
    all_known = all(t['total_miles'] is not None for t in trips)
    known_balances = bool(balances) and all(v is not None for v in balances.values())
    allocation, allocation_status, eligibility_ready = None, 'NOT_CHECKED', False
    if known_balances:
        if sum(j['miles'] for j in jobs) > sum(balances.values()):
            return None, 'ANNUAL_ACCOUNT_BALANCE_EXCEEDED'
        state, allocation = allocate(jobs, balances, eligibility, counter, config['max_allocation_states'], True)
        eligibility_ready = state == 'FEASIBLE' and all_known and all(t['dates'] for t in trips)
        if state == 'INFEASIBLE':
            state, allocation = allocate(jobs, balances, eligibility, counter, config['max_allocation_states'])
        if state == 'INFEASIBLE':
            return None, 'INDIVISIBLE_ANNUAL_ACCOUNT_ALLOCATION_INFEASIBLE'
        allocation_status = 'FEASIBLE' if state == 'FEASIBLE' and all_known else 'NOT_CHECKED'
        if state == 'LIMIT':
            missing.add('ANNUAL_ALLOCATION_SEARCH_LIMIT')
        if not all_known:
            missing.add('ANNUAL_MILEAGE_TOTAL_UNKNOWN')
    else:
        missing.add('PAYMENT_ACCOUNT_BALANCES_REQUIRED')
    if not eligibility_ready:
        missing.add('FUNDING_BENEFICIARY_ELIGIBILITY_REQUIRED')
    if not all_known:
        missing.add('ANNUAL_MILEAGE_TOTAL_UNKNOWN')
    complete_dates = all(t['dates'] for t in trips)
    leave_dates = {t: {y: sorted(v) for y, v in sorted(years.items())} for t, years in leave.items()}
    leave_counts = {t: {y: len(v) for y, v in years.items()} for t, years in leave_dates.items()}
    total_leave = sum(n for years in leave_counts.values() for n in years.values()) if complete_dates else None
    days = sum((parse_date(t['dates'][1]) - parse_date(t['dates'][0])).days + 1 for t in trips) if complete_dates else None
    long = [l for t in trips for l in t['candidate']['legs'] if l['long_haul']]
    histogram = {c: sum(l['cabin'] == c for l in long) for c in CABIN_RANK}
    cabin_mean = sum(CABIN_RANK[l['cabin']] for l in long) / len(long) if long else None
    sectors = sum(len(t['candidate']['legs']) for t in trips)
    taxes_known = all(t['taxes_hkd'] is not None for t in trips)
    prices = {t['priced']['pricing_status'] for t in trips}
    price_status = 'UNKNOWN' if not all_known or 'UNKNOWN' in prices else 'RULE_ESTIMATED' if 'RULE_ESTIMATED' in prices else 'QUOTED'
    group = 'CONDITIONAL' if missing else 'CONFIRMED_BUDGET_FEASIBLE'
    confirmed_allocation = allocation if all_known and allocation_status == 'FEASIBLE' else None
    spend = {a: sum(j['miles'] for j in confirmed_allocation if j['payer'] == a) for a in sorted(balances)} if confirmed_allocation is not None else None
    annual_spend = None
    if confirmed_allocation is not None:
        annual_spend = {a: {} for a in sorted(balances)}
        for j in confirmed_allocation:
            year = j['booking_year']
            annual_spend[j['payer']][year] = annual_spend[j['payer']].get(year, 0) + j['miles']
    identities = [(t['candidate_id'], t['priced'].get('evaluation_id')) for t in trips]
    pid = stable_id('portfolio_', {'trips': sorted(identities), 'request': _request(request),
                                  'budgets': budgets, 'balances': balances, 'eligibility': sorted(eligibility, key=lambda e: stable_id('', e))})
    evidence = {channel: sorted({t['priced'][channel] for t in trips}, key=str)
                for channel in ('holiday_status', 'route_status', 'pricing_status', 'award_seat_status', 'ticketability_status')}
    destination = [t['candidate'].get('holiday_window', {}).get('estimated_destination_full_days') for t in trips if t['dates']]
    return {'portfolio_id': pid, 'candidate_ids': sorted(t['candidate_id'] for t in trips), 'status': group,
            'trip_count': len(trips), 'holiday_families': sorted({t['holiday_key'][0] for t in trips}),
            'travel_calendar_days': days, 'estimated_destination_full_days': sum(destination) if len(destination) == len(trips) and all(v is not None for v in destination) else None,
            'leave_dates_by_traveler_by_year': leave_dates, 'leave_days_by_traveler_by_year': leave_counts,
            'leave_status': 'FEASIBLE' if complete_dates else 'UNKNOWN',
            'group_leave_days': total_leave, 'leave_efficiency': days / total_leave if total_leave else None,
            'zero_leave': complete_dates and total_leave == 0,
            'total_miles': sum(t['total_miles'] for t in trips) if all_known else None,
            'known_miles_subtotal': sum(t['known_miles'] for t in trips),
            'taxes_hkd': sum(t['taxes_hkd'] for t in trips) if taxes_known else None,
            'known_taxes_hkd_subtotal': sum(t['taxes_hkd'] for t in trips if t['taxes_hkd'] is not None),
            'account_spend_miles': spend, 'account_spend_by_booking_year': annual_spend,
            'remaining_miles_by_account': {a: balances[a] - spend[a] for a in spend} if spend is not None else None,
            'account_allocation': confirmed_allocation, 'account_allocation_status': allocation_status,
            'known_ticket_allocation': allocation, 'funding_eligibility_status': 'NOT_CHECKED',
            'funding_eligibility_evidence_status': 'SUPPLIED_CONFIRMED' if eligibility_ready else 'UNKNOWN',
            'pricing_status': price_status, 'evidence': evidence,
            'evidence_verification_status': 'SUPPLIED_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED',
            'budget_blockers': sorted(missing),
            'missing_data': sorted(missing | ({'TAX_QUOTE_REQUIRED'} if not taxes_known else set())), 'longhaul_cabin_mean_rank': cabin_mean, 'longhaul_cabin_histogram': histogram,
            'flight_sectors': sectors, 'transfers': sectors - 2 * len(trips), 'reposition_legs': 0,
            'complete_price_comparison_eligible': not missing and all(t['priced']['complete_price_comparison_eligible'] for t in trips),
            'schedule_status': 'NOT_CHECKED_WINDOW_ENDPOINTS_ARE_PLANNING_ASSUMPTIONS'}, None


def dominates(a, b):
    """Conservative strict dominance only with genuinely comparable complete quotes."""
    if (not a['complete_price_comparison_eligible'] or not b['complete_price_comparison_eligible'] or
            any(a[k] != b[k] for k in ('status', 'pricing_status', 'evidence', 'holiday_families'))):
        return False
    if (a['estimated_destination_full_days'] is None) != (b['estimated_destination_full_days'] is None):
        return False
    if (a['longhaul_cabin_mean_rank'] is None) != (b['longhaul_cabin_mean_rank'] is None):
        return False
    av = [-a['trip_count'], -a['travel_calendar_days'], a['total_miles'], a['taxes_hkd'], a['flight_sectors'], a['transfers']]
    bv = [-b['trip_count'], -b['travel_calendar_days'], b['total_miles'], b['taxes_hkd'], b['flight_sectors'], b['transfers']]
    for field in ('account_spend_miles',):
        if a[field].keys() != b[field].keys():
            return False
        for key in sorted(a[field]):
            av.append(a[field][key]); bv.append(b[field][key])
    for tid in a['leave_days_by_traveler_by_year']:
        if a['leave_days_by_traveler_by_year'][tid].keys() != b['leave_days_by_traveler_by_year'][tid].keys():
            return False
        for year in a['leave_days_by_traveler_by_year'][tid]:
            av.append(a['leave_days_by_traveler_by_year'][tid][year]); bv.append(b['leave_days_by_traveler_by_year'][tid][year])
    for field in ('estimated_destination_full_days', 'longhaul_cabin_mean_rank'):
        if a[field] is not None:
            av.append(-a[field]); bv.append(-b[field])
    return all(x <= y for x, y in zip(av, bv)) and any(x < y for x, y in zip(av, bv))


def pareto_front(rows):
    return sorted([r for r in rows if not any(other is not r and dominates(other, r) for other in rows)], key=lambda r: r['portfolio_id'])


def recommendation_views(fronts, limit):
    result = {}
    for view in VIEWS:
        def order(r):
            if view == 'Miles Saver':
                return (r['total_miles'] is None, r['pricing_status'], r['total_miles'] or 0, r['portfolio_id'])
            if view == 'Comfort First':
                return (r['longhaul_cabin_mean_rank'] is None, -(r['longhaul_cabin_mean_rank'] or 0), -r['trip_count'], r['portfolio_id'])
            if view == 'Leave Efficient':
                return (not r['zero_leave'], r['leave_efficiency'] is None, -(r['leave_efficiency'] or 0), -(r['travel_calendar_days'] or 0), r['portfolio_id'])
            return (-r['trip_count'], r['portfolio_id'])
        result[view] = {'ordering': {'Miles Saver': 'Mileage only within price classes; never total-cost ranking',
                                    'Comfort First': 'Mean longhaul ordinal cabin rank, then trips',
                                    'Balanced': 'Nondominated diversity; no weighted score',
                                    'Leave Efficient': 'Zero leave first, then calendar days per group leave day'}[view]}
        for group, rows in fronts.items():
            by_count = {}
            for r in sorted(rows, key=order):
                by_count.setdefault(r['trip_count'], []).append(r)
            queues = [diverse_limit(values, len(values),
                       lambda r: (tuple(r['holiday_families']), r['pricing_status'],
                                  tuple(r['longhaul_cabin_histogram'].values())), order)
                      for values in by_count.values()]
            chosen = []
            while len(chosen) < limit and any(queues):
                for queue in queues:
                    if queue and len(chosen) < limit:
                        chosen.append(queue.pop(0))
            result[view][group] = [r['portfolio_id'] for r in chosen]
    return result


def optimize_portfolios(priced_candidates, request, calendar, rules, balances_by_account=None,
                        funding_eligibility=None, config=None):
    """Pure bounded portfolio selection, reusing actual PR1/PR3 contracts.

    Replays original supplied PR3 evidence; never trusts cached price/allocation.
    Missing funding confirmations keep numeric-feasible portfolios conditional.
    """
    request = normalized_request(request); config = portfolio_config(config); budgets = annual_budgets(request, config)
    if not isinstance(priced_candidates, list):
        raise ValidationError('priced_candidates must be a list')
    balances = copy.deepcopy(balances_by_account)
    if balances is not None:
        if not isinstance(balances, dict) or any(not isinstance(k, str) or not k for k in balances):
            raise ValidationError('balances must map explicit account IDs')
        for v in balances.values():
            if v is not None: number(v, 'balance', integer=True)
    eligibility = copy.deepcopy(funding_eligibility) if funding_eligibility is not None else []
    if not isinstance(eligibility, list): raise ValidationError('funding_eligibility must be a list')
    for e in eligibility:
        if not isinstance(e, dict) or e.get('decision') != 'ELIGIBLE' or not isinstance(e.get('account_id'), str) or e.get('traveler_id') not in {t['id'] for t in request['travelers']}:
            raise ValidationError('invalid funding eligibility record')
        if parse_date(e['valid_from']) > parse_date(e['valid_until']): raise ValidationError('eligibility dates reversed')
    rejected = Counter(); unique = {}
    for row in priced_candidates:
        tid = row.get('candidate_id') if isinstance(row, dict) else None
        if tid in unique:
            if unique[tid] != row: raise ValidationError('conflicting duplicate candidate result')
            rejected['DUPLICATE_CANDIDATE'] += 1
        else:
            unique[tid] = row
    truncated = False
    ordered = sorted(unique.values(), key=lambda r: str(r.get('candidate_id')) if isinstance(r, dict) else '')
    trips = []
    for row in ordered:
        trip, reason = _prepare(row, request, calendar, rules, budgets)
        if reason: rejected[reason] += 1
        else: trips.append(trip)
    by_window = {}
    for t in trips: by_window.setdefault(t['window_key'], []).append(t)
    trips = []
    window_counts = {}
    for key in sorted(by_window):
        group = by_window[key]
        selected = diverse_limit(group, config['max_candidates_per_window'],
                                 lambda t: (t['priced']['pricing_status'], tuple(l['cabin'] for l in t['candidate']['legs'])),
                                 lambda t: (t['total_miles'] is None, t['candidate_id']))
        truncated |= len(selected) < len(group); trips.extend(selected)
        window_counts[key] = {'before_window_cap': len(group), 'after_window_cap': len(selected)}
    if len(trips) > config['max_candidates_total']:
        truncated = True
        trips = diverse_limit(trips, config['max_candidates_total'], lambda t: t['window_key'],
                              lambda t: (t['total_miles'] is None, t['candidate_id']))
    for key in window_counts:
        window_counts[key]['after_global_cap'] = sum(t['window_key'] == key for t in trips)
    trips.sort(key=lambda t: t['candidate_id'])
    counter = {'visited': 0, 'truncated': False}; visited = 0; rows = []
    frontier = [()]
    for _ in range(request.get('max_trips', 1)):
        following = []
        for indices in frontier:
            for index in range(indices[-1] + 1 if indices else 0, len(trips)):
                if visited >= config['max_states']:
                    truncated = True; break
                visited += 1
                combination = indices + (index,)
                row, reason = _portfolio([trips[i] for i in combination], request, budgets, balances, eligibility, counter, config)
                if reason: rejected[reason] += 1
                else: rows.append(row); following.append(combination)
            if visited >= config['max_states']: break
        frontier = following
        if not frontier or visited >= config['max_states']: break
    truncated |= visited >= config['max_states']
    fronts = {'budget_feasible': pareto_front([r for r in rows if r['status'] == 'CONFIRMED_BUDGET_FEASIBLE']),
              'conditional': pareto_front([r for r in rows if r['status'] == 'CONDITIONAL'])}
    rejected['PARETO_DOMINATED'] = len(rows) - sum(len(v) for v in fronts.values())
    return {**fronts, 'views': recommendation_views(fronts, config['max_per_view']),
            'rejected': dict(sorted(rejected.items())), 'search_truncated': truncated or counter['truncated'],
            'diagnostics': {'portfolio_states_visited': visited, 'allocation_states_visited': counter['visited'],
                            'candidate_counts_by_window': window_counts,
                            'config': config, 'leave_budgets_by_year': budgets, 'trip_candidates_retained': len(trips)},
            'trips': [t['priced'] for t in trips],
            'balances_by_account': dict(sorted(balances.items())) if balances is not None else None,
            'funding_eligibility_evidence': sorted(eligibility, key=lambda e: stable_id('', e)), 'metadata': {'milestone': 'V2_ALPHA_PR4', 'rules_digest': rules_digest(rules),
                'budget_feasibility_is_not_bookability': True, 'evidence_verification_status': 'SUPPLIED_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED'}}
