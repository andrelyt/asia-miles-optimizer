"""Synthetic TEST routes, reviews and accounts; public chart is reference only."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from discovery.award_adapter import rules_digest
from discovery.award_pricing import price_candidate
from discovery.candidate_generator import generate_candidates
from discovery.leave_engine import evaluate_window
from discovery.portfolio import optimize_portfolios, recommendation_views, planning_pareto_front
from discovery.route_graph import load_route_graph, stable_id
from tests._award_fixtures import evidence, reidentify
from tests._portfolio_fixtures import calendar, request
from tests._route_fixtures import edge, graph_data, rules

ROOT = Path(__file__).resolve().parents[1]


def fixture(dest='AKL', strategy='ALL_J', start='2027-05-07', end='2027-05-10', family='labor_day'):
    req = request(); req['origin_airports'] = ['HKG']; req['destinations'] = [{'type': 'airport', 'value': dest, 'priority': 'optional'}]
    req['holiday_types'] = ['qingming', 'labor_day']; req['max_trips'] = 2
    cal = calendar(); r = rules()
    window = evaluate_window(cal, req, start, end)
    window.update(holiday_type=family, holiday_anchor_date=cal.holiday_dates(2027, family)[0].isoformat(), bridge_side='CORE')
    window['window_id'] = stable_id('TEST_window_', window)
    distance = {'CTS': 2131, 'SYD': 4581, 'AKL': 5687, 'ZRH': 5774}[dest]
    graph = load_route_graph(graph_data([edge('HKG', dest, distance, status='UNVERIFIED'), edge(dest, 'HKG', distance, status='UNVERIFIED')]))
    candidates = generate_candidates(graph, req, r, window=window)['candidates']
    c = next(c for c in candidates if strategy in c['strategies'])
    profile = json.loads((ROOT/'validation/2027_reference_chart_profile.json').read_text())
    # Only structural attestation fixtures; no source authentication is simulated.
    profile['sources'] = [dict(s, url='https://TEST-publisher-'+str(i)+'.invalid/chart',
                               note='SYNTHETIC TEST CORROBORATION') for i, s in enumerate(profile['sources'])]
    return c, req, r, profile, cal


class ReferenceEstimateTests(unittest.TestCase):
    def run_price(self, dest='AKL', strategy='ALL_J'):
        c,q,r,p,_=fixture(dest,strategy)
        return price_candidate(c,q,r,reference_chart=p)

    def test_direct_cx_calls_existing_kernel_lookup(self):
        c,q,r,p,_=fixture()
        from optimizer import cx_standard_base
        with patch('discovery.reference_estimate.cx_standard_base', wraps=cx_standard_base) as lookup:
            out=price_candidate(c,q,r,reference_chart=p)
        self.assertEqual(lookup.call_count,2);self.assertEqual(out['estimate']['group_miles'],364000)

    def test_j_j(self):self.assertEqual(self.run_price()['estimate']['miles_per_person'],182000)
    def test_w_w(self):self.assertEqual(self.run_price(strategy='ALL_W')['estimate']['miles_per_person'],104000)
    def test_j_w(self):self.assertEqual(self.run_price(strategy='OUTBOUND_J_RETURN_W')['estimate']['miles_per_person'],143000)
    def test_w_j(self):self.assertEqual(self.run_price(strategy='OUTBOUND_W_RETURN_J')['estimate']['miles_per_person'],143000)
    def test_cts_type2(self):self.assertEqual(self.run_price('CTS')['estimate']['tickets'][0]['band'],'751_2750_type2')
    def test_cts_y_baseline(self):self.assertEqual(self.run_price('CTS','ALL_Y')['estimate']['miles_per_person'],26000)
    def test_syd_medium(self):self.assertEqual(self.run_price('SYD')['estimate']['miles_per_person'],120000)
    def test_akl_long(self):self.assertEqual(self.run_price('AKL')['estimate']['miles_per_person'],182000)
    def test_zrh_long(self):self.assertEqual(self.run_price('ZRH')['estimate']['miles_per_person'],182000)

    def test_estimate_is_not_a_quote_or_kernel_evaluation(self):
        out=self.run_price();self.assertEqual(out['pricing_status'],'RULE_ESTIMATED');self.assertIsNone(out['quote'])
        self.assertIsNone(out['group_miles']);self.assertIsNone(out['per_person_miles']);self.assertFalse(out['v1_evaluated'])
        self.assertIsNone(out['kernel_result']);self.assertFalse(out['complete_price_comparison_eligible'])
        self.assertEqual(out['official_pricing_status'],'RULE_VERSION_REVIEW_REQUIRED')

    def test_estimate_never_upgrades_route_seats_or_ticketability(self):
        out=self.run_price();self.assertEqual(out['route_status'],'UNVERIFIED')
        self.assertEqual(out['award_seat_status'],'NOT_CHECKED');self.assertEqual(out['ticketability_status'],'NOT_CHECKED')
        self.assertEqual(out['estimate']['distance_status'],'DISTANCE_PROVISIONAL');self.assertEqual(out['holiday_status'],'ESTIMATED')

    def test_future_applicability_explicit(self):
        out=self.run_price();self.assertEqual(out['estimate']['rule_applicability'],'CURRENT_REFERENCE_NOT_VERIFIED_FOR_TRAVEL_DATES')
        self.assertEqual(out['input_evidence'],{})

    def test_modified_rules_invalidate_stale_estimate(self):
        c,q,r,p,_=fixture();r['cx_standard_chart'][4]['miles']['J']+=1
        out=price_candidate(c,q,r,reference_chart=p);self.assertIsNone(out['estimate'])
        self.assertIn('REFERENCE_PROFILE_OR_RULE_BINDING_INVALID',out['diagnostics'])

    def test_unknown_band_fails_closed(self):
        c,q,r,p,_=fixture();p['route_bands']['HKG-AKL']['band']='unknown'
        self.assertIsNone(price_candidate(c,q,r,reference_chart=p)['estimate'])

    def test_unknown_cabin_fails_closed(self):
        c,q,r,p,_=fixture();c['legs'][0]['cabin']='BAD';reidentify(c)
        self.assertIsNone(price_candidate(c,q,r,reference_chart=p)['estimate'])

    def test_missing_cabin_price_fails_closed(self):
        c,q,r,p,_=fixture();del r['cx_standard_chart'][4]['miles']['J'];p['rules_digest']=rules_digest(r)
        for s in p['sources']:s['chart_digest']=stable_id('chart_',r['cx_standard_chart'])
        self.assertIsNone(price_candidate(c,q,r,reference_chart=p)['estimate'])

    def test_valid_quote_overrides_estimate(self):
        c,q,r,p,_=fixture();ev=evidence(c,q,r,10000)
        out=price_candidate(c,q,r,ev,reference_chart=p)
        self.assertEqual(out['pricing_status'],'QUOTED');self.assertIsNone(out['estimate']);self.assertEqual(out['quote']['group_miles'],40000)

    def test_invalid_quote_does_not_fall_back_and_hide_error(self):
        c,q,r,p,_=fixture();ev=evidence(c,q,r,0)
        out=price_candidate(c,q,r,ev,reference_chart=p)
        self.assertEqual(out['status'],'NEEDS_DATA');self.assertIsNone(out['estimate'])

    def test_two_independent_publishers_required(self):
        for mode in ('one','same','different_chart'):
            c,q,r,p,_=fixture()
            if mode=='one':p['sources']=p['sources'][:1]
            elif mode=='same':p['sources'][1]['url']=p['sources'][0]['url']
            else:p['sources'][1]['chart_digest']='stale'
            self.assertIsNone(price_candidate(c,q,r,reference_chart=p)['estimate'])

    def test_no_opt_in_keeps_existing_gate(self):
        c,q,r,_,_=fixture();out=price_candidate(c,q,r)
        self.assertEqual(out['status'],'RULE_VERSION_REVIEW_REQUIRED');self.assertNotIn('estimate',out)

    def test_route_type_must_have_explicit_band_evidence(self):
        c,q,r,p,_=fixture('CTS');del p['route_bands']['HKG-CTS']['route_type_source_url']
        self.assertIsNone(price_candidate(c,q,r,reference_chart=p)['estimate'])

    def test_partner_not_estimated(self):
        c,q,r,p,_=fixture();c['legs'][0]['operating_carrier']='JL';reidentify(c)
        self.assertIsNone(price_candidate(c,q,r,reference_chart=p)['estimate'])

    def test_deterministic_and_no_mutation(self):
        c,q,r,p,_=fixture();before=copy.deepcopy((c,q,r,p))
        self.assertEqual(price_candidate(c,q,r,reference_chart=p),price_candidate(c,q,r,reference_chart=p))
        self.assertEqual((c,q,r,p),before)


class ReferencePortfolioTests(unittest.TestCase):
    def result(self, balances=None, setup=None):
        c,q,r,p,cal=setup or fixture()
        priced=price_candidate(c,q,r,reference_chart=p)
        return optimize_portfolios([priced],q,cal,r,balances,config={'max_allocation_states':1000},reference_chart=p)

    def test_independent_accounts_estimated_feasible_never_confirmed(self):
        out=self.result({'TEST_A':300000,'TEST_B':250000});self.assertEqual(out['budget_feasible'],[])
        row=out['conditional'][0];self.assertEqual(row['status'],'ESTIMATED_BUDGET_FEASIBLE')
        self.assertIsNone(row['total_miles']);self.assertIsNone(row['account_spend_miles'])
        self.assertEqual(row['estimate']['total_miles'],364000)
        for account,spend in row['estimate']['account_spend_miles'].items():self.assertLessEqual(spend,{'TEST_A':300000,'TEST_B':250000}[account])
        self.assertFalse(row['complete_price_comparison_eligible']);self.assertEqual(row['funding_eligibility_status'],'NOT_CHECKED')

    def test_260k_per_person_cannot_pool_300k_250k(self):
        c,q,r,p,cal=fixture();r['cx_standard_chart'][4]['miles']['J']=130000
        p['rules_digest']=rules_digest(r)
        for s in p['sources']:s['chart_digest']=stable_id('chart_',r['cx_standard_chart'])
        out=self.result({'TEST_A':300000,'TEST_B':250000},(c,q,r,p,cal))
        self.assertEqual(out['conditional'],[]);self.assertIn('INDIVISIBLE_ANNUAL_ACCOUNT_ALLOCATION_INFEASIBLE',out['rejected'])

    def test_unknown_balance_remains_conditional(self):
        for balances in (None,{'TEST_A':300000,'TEST_B':None}):
            out=self.result(balances);self.assertEqual(out['conditional'][0]['status'],'CONDITIONAL')
            self.assertEqual(out['conditional'][0]['estimate']['budget_status'],'UNKNOWN')

    def test_cumulative_accounts_across_two_trips(self):
        c,q,r,p,cal=fixture();c2,*_=fixture(start='2027-04-02',end='2027-04-05',family='qingming')
        priced=[price_candidate(x,q,r,reference_chart=p) for x in (c,c2)]
        out=optimize_portfolios(priced,q,cal,r,{'TEST_A':300000,'TEST_B':250000},reference_chart=p)
        self.assertTrue(out['conditional']);self.assertTrue(all(x['trip_count']==1 for x in out['conditional']))
        self.assertIn('ANNUAL_ACCOUNT_BALANCE_EXCEEDED',out['rejected'])

    def test_cached_estimate_cannot_override_changed_rules(self):
        c,q,r,p,cal=fixture();row=price_candidate(c,q,r,reference_chart=p);r['cx_standard_chart'][4]['miles']['J']+=1
        out=optimize_portfolios([row],q,cal,r,reference_chart=p)
        self.assertTrue(all(x['total_miles'] is None and 'estimate' not in x for x in out['conditional']))

    def test_miles_and_balanced_ranking_use_estimates(self):
        c,q,r,p,cal=fixture();w,*_=fixture(strategy='ALL_W')
        out=optimize_portfolios([price_candidate(x,q,r,reference_chart=p) for x in (c,w)],q,cal,r,reference_chart=p)
        rows={x['portfolio_id']:x for x in out['conditional']}
        for view in ('Miles Saver','Balanced'):
            self.assertEqual(out['views'][view]['ranking_basis'],'RULE_ESTIMATED_MILES')
            self.assertEqual(rows[out['views'][view]['conditional'][0]]['estimate']['total_miles'],208000)

    def test_quote_priority_in_reference_ranking(self):
        a={'portfolio_id':'quote','pricing_status':'QUOTED','total_miles':500000,'trip_count':1}
        b={'portfolio_id':'estimate','pricing_status':'RULE_ESTIMATED','total_miles':None,'estimate':{'total_miles':100000},'trip_count':1}
        # Only inspect modified views; fill dimensions required by unchanged views.
        for row in (a,b):row.update(longhaul_cabin_mean_rank=3,zero_leave=False,leave_efficiency=1,travel_calendar_days=7,holiday_families=['labor_day'],longhaul_cabin_histogram={'J':2})
        views=recommendation_views({'conditional':[b,a]},5,True)
        self.assertEqual(views['Miles Saver']['conditional'],['quote','estimate'])
        self.assertEqual(views['Miles Saver']['ranking_basis'],'EVIDENCE_TIER_THEN_MILES')

    def test_missing_window_does_not_crash_planning_pareto(self):
        c,q,r,p,cal=fixture();c['holiday_window']=None;c['holiday_status']=None;reidentify(c)
        out=self.result(setup=(c,q,r,p,cal));self.assertEqual(out['conditional'][0]['status'],'CONDITIONAL')


class ReferenceSafetyReviewTests(unittest.TestCase):
    def test_below_requested_minimum_cabin_not_estimated(self):
        c,q,r,p,_=fixture('CTS','ALL_Y');q['cabin_preferences']['shorthaul_minimum']='J'
        self.assertIsNone(price_candidate(c,q,r,reference_chart=p)['estimate'])

    def test_reference_source_attestation_requires_boolean_true(self):
        c,q,r,p,_=fixture();p['sources'][0]['independent_publication']='yes'
        self.assertIsNone(price_candidate(c,q,r,reference_chart=p)['estimate'])

    def test_reference_check_cannot_predate_rules_snapshot(self):
        c,q,r,p,_=fixture();p['checked_at']='2025-01-01'
        self.assertIsNone(price_candidate(c,q,r,reference_chart=p)['estimate'])

    def test_legacy_mixed_estimate_never_confirmed_budget(self):
        from tests._portfolio_fixtures import trip,funding
        q=request();r=rules();cal=calendar();row=trip(mixed=True)
        out=optimize_portfolios([row],q,cal,r,{'TEST_PAYER':1000000},funding())
        self.assertFalse(out['budget_feasible'])
        self.assertEqual(out['conditional'][0]['status'],'ESTIMATED_BUDGET_FEASIBLE')

    def test_shorthaul_cabin_experience_not_erased_by_planning_pareto(self):
        c,q,r,p,cal=fixture('CTS','ALL_J');w,*_=fixture('CTS','ALL_W');y,*_=fixture('CTS','ALL_Y')
        out=optimize_portfolios([price_candidate(x,q,r,reference_chart=p) for x in (c,w,y)],q,cal,r,reference_chart=p)
        self.assertEqual(len(out['conditional']),3)

    def test_planning_dominance_is_not_complete_price_comparison(self):
        c,q,r,p,cal=fixture();out=optimize_portfolios([price_candidate(c,q,r,reference_chart=p)],q,cal,r,reference_chart=p)
        a=out['conditional'][0];b=copy.deepcopy(a);b['portfolio_id']='TEST_COSTLIER';b['estimate']['total_miles']+=1000
        self.assertEqual(planning_pareto_front([a,b]),[a])
        self.assertFalse(a['complete_price_comparison_eligible'])
        b['planning_destinations']=['TEST_OTHER_DESTINATION']
        self.assertEqual(len(planning_pareto_front([a,b])),2)

    def test_supplied_funding_attestation_cannot_confirm_reference_budget(self):
        from tests._portfolio_fixtures import funding
        c,q,r,p,cal=fixture();out=optimize_portfolios([price_candidate(c,q,r,reference_chart=p)],q,cal,r,{'TEST_PAYER':1000000},funding(),reference_chart=p)
        self.assertFalse(out['budget_feasible']);self.assertEqual(out['conditional'][0]['status'],'ESTIMATED_BUDGET_FEASIBLE')
        self.assertFalse(out['conditional'][0]['complete_price_comparison_eligible'])

    def test_allocation_limit_is_unknown_not_estimated_feasible(self):
        c,q,r,p,cal=fixture();out=optimize_portfolios([price_candidate(c,q,r,reference_chart=p)],q,cal,r,{'TEST_PAYER':1000000},config={'max_allocation_states':1},reference_chart=p)
        row=out['conditional'][0];self.assertEqual(row['status'],'CONDITIONAL');self.assertTrue(out['search_truncated'])
        self.assertIn('ANNUAL_ALLOCATION_SEARCH_LIMIT',row['budget_blockers'])
