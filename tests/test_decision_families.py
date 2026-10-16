"""Synthetic TEST identities and small synthetic balance units only."""
import copy
import unittest
from discovery.approximate_funding import simulate, validate_scenario
from discovery.decision_families import canonical_key, overlap, representative_key, summarize_families, verification_priority, family_dominates
from discovery.award_pricing import price_candidate
from discovery.portfolio import optimize_portfolios
from tests.test_reference_estimate import fixture


def scenario(a=300,b=250):
    return {'evidence_level':'USER_REPORTED_APPROXIMATE','balances_by_traveler':{'traveler_a':a,'traveler_b':b}}


def key_fixture(holiday='labor_day',dest='AKL',out='J',back='W'):
    c={'origin':'HKG','destination':dest,'holiday_window':{'holiday_type':holiday},
       'legs':[{'direction':'outbound','cabin':out},{'direction':'return','cabin':back}]}
    return {'candidate_ids':['TEST_CANDIDATE']},{'TEST_CANDIDATE':c}


def portfolio_fixture(c,q,r,p,cal,approx=True):
    price=price_candidate(c,q,r,reference_chart=p)
    # In-memory TEST values derived from reference arithmetic, not user balances.
    pp=price['estimate']['miles_per_person']
    funding={'evidence_level':'USER_REPORTED_APPROXIMATE','balances_by_traveler':{t['id']:pp+1000 for t in q['travelers']}} if approx else None
    return optimize_portfolios([price],q,cal,r,reference_chart=p,approximate_funding=funding)


class FamilyIdentityTests(unittest.TestCase):
    def test_same_strategy_dates_do_not_change_family(self):
        row,cs=key_fixture();one=canonical_key(row,cs);cs['TEST_CANDIDATE']['holiday_window']['start_date']='2027-05-02'
        self.assertEqual(one,canonical_key(row,cs))
    def test_destination_changes_family(self):
        self.assertNotEqual(canonical_key(*key_fixture(dest='CTS')),canonical_key(*key_fixture(dest='AKL')))
    def test_holiday_changes_family(self):
        self.assertNotEqual(canonical_key(*key_fixture()),canonical_key(*key_fixture(holiday='national_day')))
    def test_cabin_direction_preserved(self):
        self.assertNotEqual(canonical_key(*key_fixture(out='J',back='W')),canonical_key(*key_fixture(out='W',back='J')))
    def test_y_and_w_not_merged(self):
        self.assertNotEqual(canonical_key(*key_fixture(out='Y',back='Y')),canonical_key(*key_fixture(out='W',back='W')))
    def test_trip_count_changes_family(self):
        p,c=key_fixture();one=canonical_key(p,c);c['TEST_OTHER']=copy.deepcopy(c['TEST_CANDIDATE']);p['candidate_ids'].append('TEST_OTHER')
        self.assertNotEqual(one,canonical_key(p,c))
    def test_canonical_order_deterministic(self):
        p,c=key_fixture();c['TEST_OTHER']=copy.deepcopy(c['TEST_CANDIDATE']);c['TEST_OTHER']['holiday_window']['holiday_type']='national_day'
        p['candidate_ids'].append('TEST_OTHER');one=canonical_key(p,c);p['candidate_ids'].reverse();self.assertEqual(one,canonical_key(p,c))
    def test_portfolio_and_candidate_ids_not_part_of_key(self):
        p,c=key_fixture();one=canonical_key(p,c);p['portfolio_id']='TEST_DIFFERENT';c['TEST_NEW']=c.pop('TEST_CANDIDATE');p['candidate_ids']=['TEST_NEW']
        self.assertEqual(one,canonical_key(p,c))
    def test_overlap_calculation(self):
        x=overlap(['a','b','c'],['b','c','d']);self.assertEqual(x['intersection'],2);self.assertEqual(x['jaccard'],.5)
    def test_exact_ids_differ_family_can_match(self):
        self.assertEqual(overlap(['id1'],['id2'])['intersection'],0)
        self.assertEqual(overlap([canonical_key(*key_fixture())],[canonical_key(*key_fixture())])['overlap'],1)


class ApproximateFundingTests(unittest.TestCase):
    def test_independent_approximate_budget(self):
        out=simulate({'traveler_a':248,'traveler_b':248},scenario())
        self.assertEqual(out['status'],'ESTIMATED_BUDGET_FEASIBLE');self.assertEqual(out['remaining_by_traveler']['traveler_b'],2)
    def test_no_pooling_or_cross_funding(self):
        out=simulate({'traveler_a':260,'traveler_b':260},scenario());self.assertEqual(out['status'],'INFEASIBLE')
        self.assertEqual(out['exceeded_travelers'],['traveler_b'])
    def test_annual_spend_cumulative(self):
        self.assertEqual(simulate({'traveler_a':130+130,'traveler_b':130+130},scenario())['status'],'INFEASIBLE')
    def test_partial_balance_unknown(self):
        self.assertEqual(simulate({'traveler_a':50,'traveler_b':50},scenario(b=None))['status'],'UNKNOWN')
    def test_invalid_scenario_not_downgraded(self):
        for bad in (scenario(a=-1),scenario(a=True),{'evidence_level':'AIRLINE_VERIFIED','balances_by_traveler':{}}):
            with self.assertRaises(ValueError):validate_scenario(bad,['traveler_a','traveler_b'])
    def test_approximate_cannot_create_confirmed(self):
        c,q,r,p,cal=fixture();result=portfolio_fixture(c,q,r,p,cal)
        self.assertFalse(result['budget_feasible']);row=result['conditional'][0]
        self.assertEqual(row['status'],'ESTIMATED_BUDGET_FEASIBLE');self.assertFalse(row['complete_price_comparison_eligible'])
        self.assertEqual(row['approximate_funding']['evidence_level'],'USER_REPORTED_APPROXIMATE')
    def test_no_default_change_to_payment_account_policy(self):
        c,q,r,p,cal=fixture();result=portfolio_fixture(c,q,r,p,cal,False)
        self.assertNotIn('approximate_scenario',result['diagnostics'])
    def test_cannot_mix_two_payment_policies(self):
        c,q,r,p,cal=fixture();fund={'evidence_level':'USER_REPORTED_APPROXIMATE','balances_by_traveler':{t['id']:1 for t in q['travelers']}}
        with self.assertRaises(ValueError):optimize_portfolios([],q,cal,r,{'TEST_PAYER':1},approximate_funding=fund)
    def test_annual_leave_and_second_traveler_bind_independently(self):
        from tests._portfolio_fixtures import trip,request,calendar,rules
        q=request();q['leave_constraints'].update(max_leave_days_per_trip=13,max_calendar_trip_days=16);q['travelers'][0]['annual_leave_budget']=15;q['travelers'][1]['annual_leave_budget']=13
        a=trip(start='2027-01-01',end='2027-01-12',req=q)
        b=trip(start='2027-04-02',end='2027-04-12',family='qingming',req=q)
        funding={'evidence_level':'USER_REPORTED_APPROXIMATE','balances_by_traveler':{t['id']:1000000 for t in q['travelers']}}
        out=optimize_portfolios([a,b],q,calendar(),rules(),approximate_funding=funding)
        diag=out['diagnostics']['approximate_scenario'];self.assertGreater(diag['leave_exceeded_by_traveler'].get('traveler_b',0),0)
        self.assertEqual(diag['leave_exceeded_only_by_traveler'].get('traveler_b'),1)
        self.assertTrue(all(row['trip_count']==1 for row in out['conditional']))


class FamilyPresentationTests(unittest.TestCase):
    def setUp(self):
        self.c,self.q,self.r,self.p,self.cal=fixture();self.result=portfolio_fixture(self.c,self.q,self.r,self.p,self.cal)
    def test_representative_deterministic(self):
        one=summarize_families(self.result,self.q);two=summarize_families(copy.deepcopy(self.result),self.q)
        self.assertEqual(one,two)
    def test_representative_prefers_lower_leave(self):
        p=self.result['conditional'][0];b=copy.deepcopy(p)
        for values in b['leave_days_by_traveler_by_year'].values():
            for y in values:values[y]+=1
        self.assertLess(representative_key(p,self.q),representative_key(b,self.q))
    def test_aggregation_does_not_mutate_candidates_or_portfolios(self):
        before=copy.deepcopy(self.result);summarize_families(self.result,self.q);self.assertEqual(self.result,before)
    def test_shortlist_bounded_and_roles_deduplicated(self):
        out=summarize_families(self.result,self.q);ids=[x['family_id'] for x in out['verification_shortlist']]
        self.assertEqual(len(ids),len(set(ids)));self.assertLessEqual(len(ids),8)
        self.assertGreater(len(out['verification_shortlist'][0]['roles']),1)
    def test_priority_deterministic(self):
        f=summarize_families(self.result,self.q)['families'][0]
        self.assertEqual(verification_priority(f,True),verification_priority(copy.deepcopy(f),True))
        self.assertEqual(verification_priority(f,True),'HIGH')
    def test_family_pareto_respects_miles_comfort_duration_leave(self):
        f=summarize_families(self.result,self.q)['families'][0];b=copy.deepcopy(f);b['best_representative']['estimate']['total_miles']+=100
        self.assertTrue(family_dominates(f,b));b['best_representative']['travel_calendar_days']+=1
        self.assertFalse(family_dominates(f,b))
    def test_exhaustion_metadata_small_universe(self):
        from planner import plan
        from tests._portfolio_fixtures import snapshots
        from tests._route_fixtures import graph_data,edge
        q=copy.deepcopy(self.q);q['holiday_types']=['labor_day']
        supplied={'request':q,'calendars':snapshots(),'route_graph':graph_data([edge('HKG','AKL',5687),edge('AKL','HKG',5687)]),
                  'rules':self.r,'reference_chart':self.p,'decision_families':True,
                  'portfolio_config':{'max_candidates_total':1000,'max_candidates_per_window':1000,'max_states':10000}}
        result=plan(supplied);meta=result['diagnostics']['universe'];self.assertTrue(meta['CURRENT_UNIVERSE_EXHAUSTED']);self.assertFalse(meta['GLOBAL_OPTIMUM'])

    def test_shortlist_covers_distinct_destinations_before_variants(self):
        fixtures=[fixture(dest) for dest in ['CTS','SYD','AKL','ZRH']]
        c,q,r,p,cal=fixtures[0];q['destinations']=[{'type':'airport','value':d,'priority':'optional'} for d in ['CTS','SYD','AKL','ZRH']]
        priced=[price_candidate(f[0],q,r,reference_chart=p) for f in fixtures]
        fund={'evidence_level':'USER_REPORTED_APPROXIMATE','balances_by_traveler':{t['id']:500000 for t in q['travelers']}}
        out=optimize_portfolios(priced,q,cal,r,reference_chart=p,approximate_funding=fund)
        summary=summarize_families(out,q);ids={x['family_id'] for x in summary['verification_shortlist']}
        covered={t['destination'] for f in summary['families'] if f['family_id'] in ids for t in f['trips']}
        self.assertEqual(covered,{'CTS','SYD','AKL','ZRH'})


class AnnualApproximateIntegrationTests(unittest.TestCase):
    def test_two_individually_affordable_trips_exceed_annual_own_account(self):
        from tests._portfolio_fixtures import trip, request, calendar, rules
        q = request()
        first = trip(req=q, miles=10000)
        second = trip(start='2027-04-02', end='2027-04-04', family='qingming', req=q, miles=10000)
        # Each roundtrip is 20k per TEST traveler; two require 40k.
        fund = {'evidence_level': 'USER_REPORTED_APPROXIMATE',
                'balances_by_traveler': {'traveler_a': 50000, 'traveler_b': 30000}}
        out = optimize_portfolios([first, second], q, calendar(), rules(), approximate_funding=fund)
        self.assertEqual(out['rejected']['APPROXIMATE_TRAVELER_FUNDING_INFEASIBLE'], 1)
        self.assertTrue(out['conditional'])
        self.assertTrue(all(p['trip_count'] == 1 for p in out['conditional']))
        self.assertFalse(out['budget_feasible'])

    def test_unknown_mileage_cannot_become_estimated_funding_feasible(self):
        from tests._portfolio_fixtures import trip, request, calendar, rules
        q = request()
        fund = {'evidence_level': 'USER_REPORTED_APPROXIMATE',
                'balances_by_traveler': {t['id']: 100000 for t in q['travelers']}}
        out = optimize_portfolios([trip(req=q, quoted=False)], q, calendar(), rules(), approximate_funding=fund)
        self.assertEqual(out['diagnostics']['approximate_scenario']['funding_states'], {'UNKNOWN': 1})
        self.assertEqual(out['conditional'][0]['status'], 'CONDITIONAL')
        self.assertIsNone(out['conditional'][0]['approximate_funding']['spend_by_traveler'])
