#!/usr/bin/env python3
"""Offline D1 planner CLI. JSON resources are supplied objects or local paths."""
import argparse
import copy
import json
from pathlib import Path
import sys

from discovery._validation import ValidationError
from discovery._search_config import search_config
from discovery.award_pricing import price_candidate
from discovery.candidate_generator import generate_candidates
from discovery.holiday_calendar import load_calendars
from discovery.leave_engine import _request, generate_windows
from discovery.portfolio import (annual_budgets, diverse_limit, optimize_portfolios,
                                 portfolio_config, window_request, normalized_request)
from discovery.route_graph import load_route_graph, stable_id


def _resource(value, base):
    if isinstance(value, str):
        return json.loads((base / value).read_text(encoding='utf-8'))
    return copy.deepcopy(value)


def plan(supplied, base_dir='.'):
    """PR1 -> PR2 -> PR3 -> PR4. No quote generation, I/O except local resources."""
    if not isinstance(supplied, dict): raise ValidationError('planner input must be an object')
    allowed = {'data_label', 'request', 'calendars', 'route_graph', 'rules', 'search_config',
               'portfolio_config', 'evidence_by_candidate', 'balances_by_account', 'funding_eligibility'}
    if set(supplied) - allowed or not {'request', 'calendars', 'route_graph', 'rules'} <= set(supplied):
        raise ValidationError('unknown/missing planner inputs')
    base = Path(base_dir)
    request = normalized_request(_resource(supplied['request'], base))
    sources = _resource(supplied['calendars'], base)
    if not isinstance(sources, list): sources = [sources]
    snapshots = [_resource(v, base) for v in sources]
    calendar = load_calendars(snapshots)
    raw_graph = _resource(supplied['route_graph'], base); graph = load_route_graph(raw_graph)
    rules = _resource(supplied['rules'], base)
    search = search_config(_resource(supplied.get('search_config'), base), candidates=True)
    config = portfolio_config(_resource(supplied.get('portfolio_config'), base))
    budgets = annual_budgets(request, config)
    evidence = _resource(supplied.get('evidence_by_candidate', {}), base)
    if not isinstance(evidence, dict): raise ValidationError('evidence_by_candidate must be an object')
    balances = _resource(supplied.get('balances_by_account'), base)
    eligibility = _resource(supplied.get('funding_eligibility'), base)
    windows = generate_windows(calendar, window_request(request, budgets), search)
    selected_windows = diverse_limit(windows['windows'], config['max_windows'], lambda w: w['holiday_type'],
                                    lambda w: (w['holiday_type'], w['start_date'], w['end_date'], w['window_id']))
    truncated = len(selected_windows) < len(windows['windows']) or any(d.get('truncated_by_config') for d in windows['diagnostics'])
    candidates = {}; route_diagnostics = []
    for window in selected_windows:
        found = generate_candidates(graph, request, rules, window=window, config=search)
        route_diagnostics.append({'window_id': window['window_id'], 'diagnostics': found['diagnostics']})
        for d in found['diagnostics']:
            truncated |= bool(d.get('limit_reached'))
            if d['code'] == 'OD_SEARCH':
                truncated |= any(d[direction].get(k, False) for direction in ('outbound', 'return')
                                 for k in ('beam_truncated', 'path_limit_reached'))
        for c in found['candidates']: candidates[c['candidate_id']] = c
    groups = {}
    for c in candidates.values(): groups.setdefault(c['holiday_window']['holiday_type'], []).append(c)
    selected = []
    for family in sorted(groups):
        group = groups[family]
        kept = diverse_limit(group, config['max_candidates_per_holiday'],
                             lambda c: (bool(evidence.get(c['candidate_id'])), c['holiday_window']['window_id'],
                                        tuple(l['cabin'] for l in c['legs']), c['ticketing_mode']),
                             lambda c: (not bool(evidence.get(c['candidate_id'])), c['candidate_id']))
        truncated |= len(kept) < len(group); selected.extend(kept)
    kept = diverse_limit(selected, config['max_candidates_total'], lambda c: c['holiday_window']['holiday_type'],
                         lambda c: (not bool(evidence.get(c['candidate_id'])), c['candidate_id']))
    truncated |= len(kept) < len(selected)
    # Do not run PR3's exponential per-trip account enumeration: PR4 allocates all
    # trips globally under its explicit state limit, using PR3 ticket requirements.
    priced = [price_candidate(c, request, rules, evidence.get(c['candidate_id'])) for c in sorted(kept, key=lambda c: c['candidate_id'])]
    result = optimize_portfolios(priced, request, calendar, rules, balances, eligibility, config)
    result['search_truncated'] |= truncated
    result['input_snapshots'] = {'data_label': supplied.get('data_label'),
        'calendar_ids': sorted(s['calendar_id'] for s in snapshots), 'route_snapshot_id': graph.snapshot_id,
        'rules_version': rules.get('version'), 'rules_as_of': rules.get('as_of'),
        'request_digest': stable_id('request_', request), 'route_digest': stable_id('routes_', raw_graph)}
    result['diagnostics']['holiday_windows'] = windows['diagnostics']
    result['diagnostics']['route_search'] = route_diagnostics
    result['diagnostics']['windows_searched'] = len(selected_windows)
    result['diagnostics']['unused_candidate_evidence'] = sorted(set(evidence) - {c['candidate_id'] for c in kept})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Offline supplied-evidence annual holiday portfolio planner (no booking)')
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', type=Path, help='Default: JSON to stdout')
    args = parser.parse_args(argv)
    try:
        supplied = json.loads(args.input.read_text(encoding='utf-8'))
        result = plan(supplied, args.input.resolve().parent)
        rendered = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
        if args.output: args.output.write_text(rendered, encoding='utf-8')
        else: sys.stdout.write(rendered)
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        sys.stderr.write(json.dumps({'status': 'INVALID_INPUT', 'error': str(exc)}, ensure_ascii=False) + '\n')
        return 2


if __name__ == '__main__':
    sys.exit(main())
