"""PR4 annual budgets and evidence-safe multi-trip selection; synthetic TEST only."""
import copy
import unittest

from discovery._validation import ValidationError
from discovery.portfolio import optimize_portfolios, dominates, pareto_front
from tests._portfolio_fixtures import calendar, funding, request, trip
from tests._route_fixtures import rules


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.req = request(); self.cal = calendar(); self.rules = rules()
        self.one = trip()
        self.two = trip('2027-04-02', '2027-04-04', 'qingming')
        self.three = trip('2027-05-07', '2027-05-09', 'labor_day')

    def run_portfolio(self, rows=None, balances=None, eligibility=None, config=None):
        return optimize_portfolios(rows if rows is not None else [self.one, self.two, self.three], self.req, self.cal, self.rules,
                                   balances if balances is not None else {'TEST_PAYER': 200000},
                                   funding() if eligibility is None else eligibility, config)

    def rows(self, result):
        return result['budget_feasible'] + result['conditional']

    def test_multi_trip_portfolios_not_standalone_ranking(self):
        result = self.run_portfolio()
        self.assertEqual({r['trip_count'] for r in result['budget_feasible']}, {1, 2, 3})
        full = next(r for r in result['budget_feasible'] if r['trip_count'] == 3)
        self.assertEqual(full['total_miles'], 120000)
        self.assertEqual(full['account_spend_miles'], {'TEST_PAYER': 120000})
        self.assertEqual(full['account_spend_by_booking_year'], {'TEST_PAYER': {'2026': 120000}})
        self.assertEqual(full['funding_eligibility_status'], 'NOT_CHECKED')

    def test_each_traveler_annual_leave_is_independent(self):
        self.req['travelers'][0]['annual_leave_budget'] = 0
        result = self.run_portfolio()
        self.assertTrue(result['rejected'].get('LEAVE_BUDGET_EXCEEDED', 0))
        self.assertTrue(all(self.one['candidate_id'] not in r['candidate_ids'] for r in self.rows(result)))

    def test_makeup_workday_is_charged_from_actual_calendar(self):
        row = self.run_portfolio([self.one])['budget_feasible'][0]
        for traveler in ('traveler_a', 'traveler_b'):
            self.assertEqual(row['leave_dates_by_traveler_by_year'][traveler]['2027'], ['2027-01-02'])
            self.assertEqual(row['leave_days_by_traveler_by_year'][traveler]['2027'], 1)

    def test_leave_budget_accumulates_across_trips(self):
        # Each trip separately uses <=2 days, but their annual union needs 3.
        a = trip('2027-01-01', '2027-01-04')
        b = trip('2027-04-02', '2027-04-05', 'qingming')
        for t in self.req['travelers']: t['annual_leave_budget'] = 2
        result = self.run_portfolio([a, b])
        self.assertTrue(all(r['trip_count'] == 1 for r in self.rows(result)))
        self.assertEqual(result['rejected']['ANNUAL_LEAVE_BUDGET_EXCEEDED'], 1)

    def test_blocked_dates_are_rechecked_not_trusted_from_cache(self):
        self.req['travelers'][1]['blocked_dates'] = ['2027-04-03']
        result = self.run_portfolio([self.two])
        self.assertFalse(self.rows(result))
        self.assertEqual(result['rejected']['BLOCKED_DATE'], 1)

    def test_same_holiday_alternate_windows_cannot_count_as_two_trips(self):
        alternate = trip('2027-01-01', '2027-01-04')
        result = self.run_portfolio([self.one, alternate])
        self.assertTrue(all(r['trip_count'] == 1 for r in self.rows(result)))
        self.assertEqual(result['rejected']['SAME_HOLIDAY_ALTERNATIVE'], 1)

    def test_overlap_is_inclusive_and_adjacent_is_allowed(self):
        from discovery.holiday_calendar import load_calendars
        from tests._portfolio_fixtures import snapshots
        ss = snapshots(); ss[1]['days'].append({'date': '2027-01-03', 'day_type': 'PUBLIC_HOLIDAY', 'holiday_name': 'labor_day'})
        # First labor anchor becomes January 3, distinct family with shared boundary.
        self.cal = load_calendars(ss)
        a = trip(cal=self.cal); overlap = trip('2027-01-03', '2027-01-05', 'labor_day', cal=self.cal)
        result = self.run_portfolio([a, overlap])
        self.assertTrue(all(r['trip_count'] == 1 for r in self.rows(result)))
        self.assertEqual(result['rejected']['OVERLAPPING_TRIPS'], 1)
        ss[1]['days'][-1]['date'] = '2027-01-04'; self.cal = load_calendars(ss)
        a = trip(cal=self.cal); adjacent = trip('2027-01-04', '2027-01-06', 'labor_day', cal=self.cal)
        result = self.run_portfolio([a, adjacent])
        self.assertTrue(any(r['trip_count'] == 2 for r in result['budget_feasible']))

    def test_cross_year_requires_previous_year_explicit_budget(self):
        cross = trip('2026-12-31', '2027-01-03')
        result = self.run_portfolio([cross])
        self.assertFalse(self.rows(result))
        self.assertEqual(result['rejected']['ANNUAL_LEAVE_BUDGET_YEAR_MISSING'], 1)
        cfg = {'leave_budgets_by_year': {'2026': {'traveler_a': 1, 'traveler_b': 1}}}
        result = self.run_portfolio([cross], config=cfg)
        row = result['budget_feasible'][0]
        self.assertEqual(row['leave_days_by_traveler_by_year']['traveler_a'], {'2026': 1, '2027': 1})

    def test_cross_year_does_not_reuse_planning_year_budget(self):
        cross = trip('2026-12-31', '2027-01-03')
        cfg = {'leave_budgets_by_year': {'2026': {'traveler_a': 0, 'traveler_b': 5}}}
        result = self.run_portfolio([cross], config=cfg)
        self.assertFalse(self.rows(result))
        self.assertEqual(result['rejected']['ANNUAL_LEAVE_BUDGET_EXCEEDED'], 1)

    def test_max_trips_one_two_three(self):
        for maximum in (1, 2, 3):
            self.req['max_trips'] = maximum
            result = self.run_portfolio()
            self.assertEqual(max(r['trip_count'] for r in self.rows(result)), maximum)

    def test_per_trip_affordable_is_not_annual_feasible(self):
        result = self.run_portfolio(balances={'TEST_PAYER': 50000})
        self.assertEqual({r['trip_count'] for r in self.rows(result)}, {1})
        self.assertTrue(result['rejected']['ANNUAL_ACCOUNT_BALANCE_EXCEEDED'])

    def test_indivisible_annual_tickets_cannot_pool_accounts(self):
        result = self.run_portfolio([self.one, self.two], balances={'TEST_A': 35000, 'TEST_B': 45000}, eligibility=funding(('TEST_A', 'TEST_B')))
        self.assertTrue(all(r['trip_count'] == 1 for r in self.rows(result)))
        self.assertTrue(result['rejected']['INDIVISIBLE_ANNUAL_ACCOUNT_ALLOCATION_INFEASIBLE'])

    def test_global_account_assignment_does_not_reuse_per_trip_allocations(self):
        result = self.run_portfolio([self.one, self.two], balances={'TEST_A': 40000, 'TEST_B': 40000}, eligibility=funding(('TEST_A', 'TEST_B')))
        full = next(r for r in result['budget_feasible'] if r['trip_count'] == 2)
        self.assertEqual(full['account_spend_miles'], {'TEST_A': 40000, 'TEST_B': 40000})
        self.assertEqual(len(full['account_allocation']), 8)

    def test_unknown_or_partial_balances_always_conditional(self):
        for balances in ({}, {'TEST_A': None}, {'TEST_A': 1, 'TEST_B': None}):
            result = self.run_portfolio([self.one], balances=balances)
            self.assertFalse(result['budget_feasible'])
            row = result['conditional'][0]
            self.assertIn('PAYMENT_ACCOUNT_BALANCES_REQUIRED', row['missing_data'])
            self.assertIsNone(row['account_spend_miles'])

    def test_unresolved_funding_eligibility_is_conditional_even_if_numbers_fit(self):
        result = self.run_portfolio([self.one], eligibility=[])
        self.assertFalse(result['budget_feasible'])
        row = result['conditional'][0]
        self.assertEqual(row['account_allocation_status'], 'FEASIBLE')
        self.assertIn('FUNDING_BENEFICIARY_ELIGIBILITY_REQUIRED', row['budget_blockers'])
        self.assertEqual(row['funding_eligibility_status'], 'NOT_CHECKED')

    def test_eligibility_confirmations_are_scoped_to_payer_passenger_and_dates(self):
        eligibility = funding(('TEST_A',), ('traveler_a',)) + funding(('TEST_B',), ('traveler_b',))
        result = self.run_portfolio([self.one], balances={'TEST_A': 20000, 'TEST_B': 20000}, eligibility=eligibility)
        row = result['budget_feasible'][0]
        self.assertTrue(all(a['payer'] == ('TEST_A' if a['passenger'] == 'traveler_a' else 'TEST_B') for a in row['account_allocation']))
        for e in eligibility: e['valid_until'] = '2026-12-31'
        self.assertFalse(self.run_portfolio([self.one], balances={'TEST_A': 20000, 'TEST_B': 20000}, eligibility=eligibility)['budget_feasible'])

    def test_one_known_plus_one_unknown_has_no_complete_total(self):
        unknown = trip('2027-04-02', '2027-04-04', 'qingming', quoted=False)
        result = self.run_portfolio([self.one, unknown])
        full = next(r for r in result['conditional'] if r['trip_count'] == 2)
        self.assertIsNone(full['total_miles'])
        self.assertEqual(full['known_miles_subtotal'], 40000)
        self.assertIsNone(full['account_spend_miles'])
        self.assertIn('RULE_VERSION_REVIEW_REQUIRED', full['missing_data'])

    def test_partner_pending_remains_conditional_not_invalid_route(self):
        partner = trip(carrier='ZZ')
        result = self.run_portfolio([partner])
        self.assertFalse(result['budget_feasible'])
        self.assertIn('NEEDS_AIRLINE_QUOTE', result['conditional'][0]['missing_data'])
        self.assertIsNone(result['conditional'][0]['total_miles'])

    def test_unknown_tax_does_not_enable_strict_cost_comparison(self):
        result = self.run_portfolio([trip(taxes=None)])
        row = result['budget_feasible'][0]
        self.assertIsNone(row['taxes_hkd'])
        self.assertIn('TAX_QUOTE_REQUIRED', row['missing_data'])
        self.assertFalse(row['complete_price_comparison_eligible'])

    def test_mixed_estimates_stay_separate_from_quoted_costs(self):
        result = self.run_portfolio([trip(mixed=True), self.one])
        self.assertEqual({r['pricing_status'] for r in self.rows(result)}, {'RULE_ESTIMATED', 'QUOTED'})
        estimated = next(r for r in self.rows(result) if r['pricing_status'] == 'RULE_ESTIMATED')
        self.assertFalse(estimated['complete_price_comparison_eligible'])
        self.assertEqual(estimated['evidence']['ticketability_status'], ['NOT_CHECKED'])

    def test_estimated_holiday_and_stale_route_evidence_preserved(self):
        from tests._award_fixtures import reidentify, evidence
        row = copy.deepcopy(self.one); c = row['candidate']
        c['legs'][0]['route_status'] = 'STALE'; c['route_status'] = 'STALE'; reidentify(c)
        from discovery.award_pricing import price_candidate
        row = price_candidate(c, self.req, self.rules, evidence(c, self.req, self.rules))
        result = self.run_portfolio([row])['budget_feasible'][0]
        self.assertEqual(result['evidence']['holiday_status'], ['ESTIMATED'])
        self.assertEqual(result['evidence']['route_status'], ['STALE'])
        self.assertEqual(result['evidence']['award_seat_status'], ['NOT_CHECKED'])

    def test_unsupported_invalid_and_zero_quote_do_not_become_conditional(self):
        invalid = copy.deepcopy(self.one); invalid['status'] = 'UNSUPPORTED'
        self.assertFalse(self.rows(self.run_portfolio([invalid])))
        from discovery.award_pricing import price_candidate
        from tests._award_fixtures import evidence
        ev = evidence(self.one['candidate'], self.req, self.rules, quote_miles=0)
        zero = price_candidate(self.one['candidate'], self.req, self.rules, ev)
        self.assertFalse(self.rows(self.run_portfolio([zero])))

    def test_cached_miles_and_allocations_are_replayed_not_trusted(self):
        fake = copy.deepcopy(self.one); fake['group_miles'] = 1; fake['account_allocation_status'] = 'FEASIBLE'
        row = self.run_portfolio([fake])['budget_feasible'][0]
        self.assertEqual(row['total_miles'], 40000)

    def test_no_candidates_and_no_feasible_portfolio(self):
        self.assertFalse(self.rows(self.run_portfolio([])))
        result = self.run_portfolio(balances={'TEST_PAYER': 1})
        self.assertFalse(self.rows(result))
        self.assertTrue(result['rejected'])

    def test_stable_order_ids_dedup_and_no_duplicate_trip(self):
        original = self.run_portfolio()
        self.req['travelers'].reverse()
        replay = self.run_portfolio([self.three, self.two, self.one])
        self.assertEqual(original, replay)
        dedup = self.run_portfolio([self.one, self.one, self.two])
        self.assertEqual(dedup['rejected']['DUPLICATE_CANDIDATE'], 1)
        self.assertTrue(all(len(r['candidate_ids']) == len(set(r['candidate_ids'])) for r in self.rows(dedup)))

    def test_conflicting_duplicate_and_mixed_traveler_groups_rejected(self):
        bad = copy.deepcopy(self.one); bad['status'] = 'UNSUPPORTED'
        with self.assertRaises(ValidationError): self.run_portfolio([self.one, bad])
        self.req['travelers'][0]['id'] = 'OTHER_TEST_PASSENGER'
        self.assertFalse(self.rows(self.run_portfolio([self.one], eligibility=[])))

    def test_strict_dominance_only_with_complete_compatible_quotes(self):
        cheaper = trip(miles=5000); costly = trip(miles=10000)
        # Evidence values and geometry are equal; candidate IDs identical would
        # conflict, so compare separate results from independent supplied snapshots.
        a = self.run_portfolio([cheaper])['budget_feasible'][0]
        b = self.run_portfolio([costly])['budget_feasible'][0]
        self.assertTrue(dominates(a, b))
        self.assertEqual(pareto_front([b, a]), [a])
        b['taxes_hkd'] = None; b['complete_price_comparison_eligible'] = False
        self.assertFalse(dominates(a, b)); self.assertFalse(dominates(b, a))
        b = copy.deepcopy(a); b['pricing_status'] = 'RULE_ESTIMATED'
        self.assertFalse(dominates(a, b))

    def test_four_views_are_bounded_and_preserve_trip_count_diversity(self):
        result = self.run_portfolio(config={'max_per_view': 3})
        self.assertEqual(set(result['views']), {'Miles Saver', 'Comfort First', 'Balanced', 'Leave Efficient'})
        indexed = {r['portfolio_id']: r for r in self.rows(result)}
        for view in result['views'].values():
            self.assertLessEqual(len(view['budget_feasible']), 3)
            self.assertEqual({indexed[i]['trip_count'] for i in view['budget_feasible']}, {1, 2, 3})
        self.assertTrue(all(r['leave_efficiency'] is None and r['zero_leave'] for r in self.rows(self.run_portfolio([self.two]))))

    def test_search_and_allocation_limits_are_explicit_not_infeasibility(self):
        result = self.run_portfolio(config={'max_states': 2})
        self.assertTrue(result['search_truncated'])
        self.assertLessEqual(result['diagnostics']['portfolio_states_visited'], 2)
        result = self.run_portfolio(config={'max_allocation_states': 1})
        self.assertTrue(result['search_truncated'])
        self.assertFalse(result['budget_feasible'])
        self.assertTrue(any('ANNUAL_ALLOCATION_SEARCH_LIMIT' in r['missing_data'] for r in result['conditional']))

    def test_config_caps_and_validation(self):
        result = self.run_portfolio(config={'max_candidates_total': 1})
        self.assertTrue(result['search_truncated'])
        self.assertEqual(result['diagnostics']['trip_candidates_retained'], 1)
        for cfg in ({'max_states': 0}, {'unexpected': 1}):
            with self.assertRaises(ValidationError): self.run_portfolio(config=cfg)

    def test_no_mutation(self):
        saved = copy.deepcopy((self.one, self.req, self.rules))
        self.run_portfolio([self.one])
        self.assertEqual(saved, (self.one, self.req, self.rules))


    def test_unknown_dates_are_conditional_and_leave_overlap_unresolved(self):
        from tests._award_fixtures import reidentify, evidence
        from discovery.award_pricing import price_candidate
        c = copy.deepcopy(self.one['candidate']); c['holiday_window'] = None; c['holiday_status'] = None; reidentify(c)
        row = price_candidate(c, self.req, self.rules, evidence(c, self.req, self.rules))
        result = self.run_portfolio([row])
        self.assertFalse(result['budget_feasible'])
        unknown = result['conditional'][0]
        self.assertEqual(unknown['leave_status'], 'UNKNOWN')
        self.assertIsNone(unknown['group_leave_days'])
        self.assertIn('TRAVEL_DATES_REQUIRED', unknown['missing_data'])

    def test_missing_next_year_budget_not_replaced_by_previous_year(self):
        from tests._portfolio_fixtures import snapshots
        from discovery.holiday_calendar import load_calendars
        ss = snapshots(); ss[0]['days'] = [{'date':'2026-12-31', 'day_type':'PUBLIC_HOLIDAY', 'holiday_name':'new_year'}]
        self.cal = load_calendars(ss); self.req['planning_year'] = 2026
        row = trip('2026-12-31', '2027-01-03', req=self.req, cal=self.cal)
        result = self.run_portfolio([row])
        self.assertFalse(self.rows(result))
        self.assertEqual(result['rejected']['ANNUAL_LEAVE_BUDGET_YEAR_MISSING'], 1)
        cfg = {'leave_budgets_by_year': {'2027': {'traveler_a':1, 'traveler_b':1}}}
        row = self.run_portfolio([row], config=cfg)['budget_feasible'][0]
        self.assertEqual(row['leave_days_by_traveler_by_year']['traveler_a'], {'2026':0, '2027':1})

    def test_per_year_budgets_allow_cross_year_without_single_window_cap_error(self):
        self.req['leave_constraints']['max_leave_days_per_trip'] = 4
        row = trip('2026-12-30','2027-01-04', req=self.req)
        for t in self.req['travelers']: t['annual_leave_budget'] = 2
        cfg = {'leave_budgets_by_year': {'2026': {'traveler_a':2,'traveler_b':2}}}
        result = self.run_portfolio([row], config=cfg)
        self.assertTrue(result['budget_feasible'])
        self.assertEqual(result['budget_feasible'][0]['leave_days_by_traveler_by_year']['traveler_a'], {'2026':2,'2027':2})

    def test_price_and_cabin_tradeoffs_are_incomparable(self):
        y = trip(strategy='ALL_Y', miles=5000)
        j = trip(strategy='ALL_J', miles=10000)
        result = self.run_portfolio([y,j])
        self.assertEqual(len(result['budget_feasible']),2)
        self.assertEqual({r['longhaul_cabin_mean_rank'] for r in result['budget_feasible']}, {1,3})
        for a in result['budget_feasible']:
            for b in result['budget_feasible']: self.assertFalse(dominates(a,b))

    def test_pareto_prunes_an_actual_more_expensive_equivalent_snapshot(self):
        from tests._award_fixtures import reidentify, evidence, bound
        from discovery.award_pricing import price_candidate
        c=copy.deepcopy(self.one['candidate']);c['route_snapshot_id']='TEST_OTHER_SNAPSHOT';reidentify(c)
        ev=evidence(c,self.req,self.rules,quote_miles=20000)
        ev['tax_quote']=dict(bound(c,self.rules,'AIRLINE_QUOTED'),hkd_per_person=100)
        costly=price_candidate(c,self.req,self.rules,ev)
        result=self.run_portfolio([self.one,costly])
        self.assertEqual(len(result['budget_feasible']),1)
        self.assertEqual(result['rejected']['PARETO_DOMINATED'],1)

    def test_normalized_request_and_eligibility_order_do_not_change_ids(self):
        self.req['origin_airports']=['BBB','AAA']
        self.req['travelers'][0]['personal_days_off']=['2027-05-20','2027-05-21']
        one=self.run_portfolio([self.one])
        self.req['origin_airports'].reverse();self.req['holiday_types'].reverse()
        self.req['travelers'][0]['personal_days_off'].reverse()
        two=self.run_portfolio([self.one],eligibility=list(reversed(funding())))
        self.assertEqual(one,two)

    def test_incomplete_known_subtotal_over_budget_is_rejected(self):
        from discovery.award_pricing import price_candidate
        ev=copy.deepcopy(self.one['input_evidence']);del ev['quotes']['return_2']
        partial=price_candidate(self.one['candidate'],self.req,self.rules,ev)
        result=self.run_portfolio([partial],balances={'TEST_PAYER':10000})
        self.assertFalse(self.rows(result))
        self.assertEqual(result['rejected']['ANNUAL_ACCOUNT_BALANCE_EXCEEDED'],1)


    def test_untrusted_eligibility_label_cannot_confirm_budget(self):
        records=funding()
        for e in records:e['evidence_level']='THIRD_PARTY_OBSERVED'
        result=self.run_portfolio([self.one],eligibility=records)
        self.assertFalse(result['budget_feasible'])
        self.assertEqual(result['funding_eligibility_evidence'],records)
        self.assertTrue(result['conditional'])

    def test_zero_annual_balance_is_known_constraint_not_unknown(self):
        result=self.run_portfolio([self.one],balances={'TEST_PAYER':0})
        self.assertFalse(self.rows(result))
        self.assertEqual(result['rejected']['ANNUAL_ACCOUNT_BALANCE_EXCEEDED'],1)

    def test_duplicate_leave_days_are_unioned_by_calendar_year(self):
        from discovery.portfolio import _portfolio, annual_budgets, portfolio_config
        # This exercises union semantics directly, independent of the earlier
        # exact-window evidence validation and duplicate-trip guard.
        from discovery.portfolio import _prepare
        cfg=portfolio_config();budgets=annual_budgets(self.req,cfg)
        prepared,reason=_prepare(self.one,self.req,self.cal,self.rules,budgets)
        self.assertIsNone(reason)
        prepared['leave']['traveler_a'] *= 2
        row,reason=_portfolio([prepared],self.req,budgets,{'TEST_PAYER':200000},funding(),
                             {'visited':0,'truncated':False},cfg)
        self.assertIsNone(reason)
        self.assertEqual(row['leave_days_by_traveler_by_year']['traveler_a']['2027'],1)

    def test_allocation_state_cap_counts_generated_branches(self):
        accounts={f'TEST_{i}':40000 for i in range(20)}
        result=self.run_portfolio([self.one],balances=accounts,eligibility=[],config={'max_allocation_states':3})
        self.assertLessEqual(result['diagnostics']['allocation_states_visited'],3)
        self.assertTrue(result['search_truncated'])
        self.assertFalse(result['budget_feasible'])

    def test_eligibility_must_cover_booking_not_only_future_travel(self):
        records=funding()
        for record in records:record['valid_from']='2027-01-01'
        result=self.run_portfolio([self.one],eligibility=records)
        self.assertFalse(result['budget_feasible'])
        self.assertIn('FUNDING_BENEFICIARY_ELIGIBILITY_REQUIRED',result['conditional'][0]['missing_data'])



if __name__ == '__main__': unittest.main()
