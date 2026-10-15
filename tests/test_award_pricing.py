"""End-to-end kernel integration; quotes/accounts/services are SYNTHETIC TEST ONLY."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from optimizer import evaluate
from discovery.award_pricing import price_candidate
from discovery.candidate_generator import generate_candidates
from discovery.route_graph import load_route_graph
from tests._award_fixtures import bound, candidate, evidence, reidentify, source
from tests._route_fixtures import graph_data, rules, travel_request


class AwardPricingTests(unittest.TestCase):
    def setUp(self):
        self.c, self.req, self.rules = candidate()
        self.ev = evidence(self.c, self.req, self.rules)

    def price(self, **kw):
        return price_candidate(self.c, self.req, self.rules, kw.pop('evidence', self.ev), **kw)

    def mixed(self, cabins=('J', 'Y'), distances=(498, 1355), route_type=2):
        self.c, self.req, self.rules = candidate('LONG_J_SHORT_Y')
        for i, (cabin, distance) in enumerate(zip(cabins, distances)):
            self.c['legs'][i].update(cabin=cabin, distance_miles=distance)
        reidentify(self.c)
        self.ev = evidence(self.c, self.req, self.rules)
        self.ev['ticket_data']['outbound_1'].update(route_type=route_type, route_type_evidence=source())
        return self.price()

    def test_standard_single_and_two_sector_tickets_use_only_supplied_quote(self):
        result = self.price()
        self.assertEqual(result['status'], 'EVALUATED')
        self.assertTrue(result['v1_evaluated'])
        self.assertEqual(result['per_person_miles'], 20000)
        self.assertEqual(result['group_miles'], 40000)
        self.assertEqual([t['miles_per_person'] for t in result['tickets']], [10000, 10000])
        self.assertEqual([t['leg_indices'] for t in result['tickets']], [[0, 1], [2]])
        self.assertEqual(result['pricing_status'], 'QUOTED')
        self.assertEqual(result['tickets'][0]['evidence']['quote']['source_url'], self.ev['quotes']['outbound_1']['source_url'])

    def test_entire_direct_roundtrip_keeps_two_one_way_quotes(self):
        from tests._route_fixtures import edge
        self.req = travel_request()
        self.c = next(c for c in generate_candidates(load_route_graph(graph_data([
            edge('AAA', 'CCC', 6000), edge('CCC', 'AAA', 6000)])), self.req, self.rules)['candidates']
                      if 'OUTBOUND_J_RETURN_W' in c['strategies'])
        self.ev = evidence(self.c, self.req, self.rules)
        self.ev['quotes']['outbound_1']['miles_per_person'] = 91000
        self.ev['quotes']['return_2']['miles_per_person'] = 52000
        result = self.price()
        self.assertEqual(result['per_person_miles'], 143000)
        self.assertEqual(len(result['tickets']), 2)
        self.assertEqual([l['cabin'] for l in result['scenario']['trips'][0]['legs']], ['J', 'W'])

    def test_cx_mixed_j_y_calls_evaluate_with_standard_mixed(self):
        result = self.mixed()
        self.assertEqual(result['status'], 'EVALUATED')
        self.assertEqual(result['tickets'][0]['miles_per_person'], 18300)
        self.assertEqual(result['scenario']['award_tickets'][0]['scheme'], 'standard_mixed')
        self.assertEqual(result['kernel_result'], evaluate(result['scenario'], self.rules, result['settings']))
        self.assertEqual(result['pricing_status'], 'RULE_ESTIMATED')
        self.assertFalse(result['complete_price_comparison_eligible'])

    def test_cx_mixed_w_y(self):
        result = self.mixed(('W', 'Y'))
        self.assertEqual(result['tickets'][0]['miles_per_person'], 15600)
        self.assertEqual(result['pricing_status'], 'RULE_ESTIMATED')

    def test_cx_mixed_j_w(self):
        result = self.mixed(('J', 'W'))
        self.assertEqual(result['tickets'][0]['miles_per_person'], 25600)
        self.assertEqual(result['pricing_status'], 'RULE_ESTIMATED')

    def test_unknown_standard_never_calls_kernel_or_fabricates_zero(self):
        self.ev['quotes'].clear()
        with patch('discovery.award_pricing.evaluate') as kernel:
            result = self.price(); kernel.assert_not_called()
        self.assertEqual(result['status'], 'NEEDS_AIRLINE_QUOTE')
        self.assertIsNone(result['group_miles'])
        self.assertIsNone(result['per_person_miles'])
        self.assertFalse(result['v1_evaluated'])

    def test_partial_known_prices_are_subtotal_not_complete_total(self):
        del self.ev['quotes']['return_2']
        result = self.price()
        self.assertEqual(result['known_miles_subtotal_per_person'], 10000)
        self.assertEqual(result['known_group_miles_subtotal'], 20000)
        self.assertIsNone(result['group_miles'])
        self.assertIsNone(result['tickets'][1]['miles_per_person'])

    def test_missing_transfer_hours_or_source_blocks_estimate(self):
        self.c, self.req, self.rules = candidate('LONG_J_SHORT_Y')
        self.ev = evidence(self.c, self.req, self.rules)
        for key in ('transfer_hours', 'transfer_evidence'):
            ev = copy.deepcopy(self.ev); del ev['ticket_data']['outbound_1'][key]
            result = self.price(evidence=ev)
            self.assertEqual(result['status'], 'NEEDS_DATA')
            self.assertIn('TRANSFER_HOURS_REQUIRED', result['tickets'][0]['diagnostics'])
            self.assertIsNone(result['tickets'][0]['miles_per_person'])

    def test_missing_route_type_or_evidence_blocks_typed_band(self):
        self.mixed()
        for key in ('route_type', 'route_type_evidence'):
            ev = copy.deepcopy(self.ev); del ev['ticket_data']['outbound_1'][key]
            result = self.price(evidence=ev)
            self.assertEqual(result['status'], 'NEEDS_DATA')
            self.assertIn('SOURCED_ROUTE_TYPE_REQUIRED', result['tickets'][0]['diagnostics'])

    def test_unsourced_or_mismatched_distance_blocks_estimate(self):
        self.mixed()
        for value in ({}, {'0': dict(source(), distance_miles=999)}):
            ev = copy.deepcopy(self.ev); ev['ticket_data']['outbound_1']['distance_confirmations'] = value
            result = self.price(evidence=ev)
            self.assertEqual(result['status'], 'NEEDS_DATA')
            self.assertIsNone(result['tickets'][0]['miles_per_person'])

    def test_invalid_transfer_and_route_type_do_not_crash(self):
        self.mixed()
        for key, value in [('transfer_hours', -1), ('transfer_hours', 25),
                           ('transfer_hours', True), ('route_type', 99)]:
            ev = copy.deepcopy(self.ev); ev['ticket_data']['outbound_1'][key] = value
            result = self.price(evidence=ev)
            self.assertIn(result['status'], ('NEEDS_DATA', 'UNSUPPORTED'))
            self.assertFalse(result['complete_price_comparison_eligible'])

    def test_three_sector_split_prices_four_independent_awards(self):
        self.c, self.req, self.rules = candidate(mode='SEPARATE_AWARDS', three=True)
        self.ev = evidence(self.c, self.req, self.rules)
        for i, t in enumerate(self.c['tickets']): self.ev['quotes'][t['ticket_id']]['miles_per_person'] = (i + 1) * 1000
        result = self.price()
        self.assertEqual(result['status'], 'EVALUATED')
        self.assertEqual(result['per_person_miles'], 10000)
        self.assertEqual([t['leg_indices'] for t in result['tickets']], [[0], [1], [2], [3]])
        self.assertTrue(all(t['scheme'] == 'standard' for t in result['scenario']['award_tickets']))

    def test_separate_awards_not_priced_with_same_ticket_mixed_formula(self):
        same = self.mixed()
        self.c, self.req, self.rules = candidate('LONG_J_SHORT_Y', mode='SEPARATE_AWARDS')
        self.ev = evidence(self.c, self.req, self.rules)
        result = self.price()
        self.assertEqual(len(result['tickets']), 3)
        self.assertEqual(result['per_person_miles'], 30000)
        self.assertNotEqual(same['per_person_miles'], result['per_person_miles'])

    def test_three_sector_same_ticket_rejected_before_evaluate(self):
        self.c, self.req, self.rules = candidate(mode='SEPARATE_AWARDS', three=True)
        self.c['ticketing_mode'] = 'SINGLE_AWARD'
        self.c['tickets'][0]['leg_indices'] = [0, 1, 2]; reidentify(self.c)
        result = self.price()
        self.assertEqual(result['status'], 'UNSUPPORTED')
        self.assertIn('STANDARD_SECTOR_LIMIT_EXCEEDED', result['diagnostics'])
        self.assertFalse(result['v1_evaluated'])

    def test_partner_combinations_retained_without_cx_formula_even_with_quotes(self):
        for carriers in (['CX', 'ZZ'], ['ZZ', 'CX'], ['ZZ', 'ZZ']):
            with self.subTest(carriers=carriers):
                self.c, self.req, self.rules = candidate('LONG_J_SHORT_Y', carriers=carriers)
                self.ev = evidence(self.c, self.req, self.rules)
                with patch('discovery.award_adapter.mixed_cabin_price', side_effect=AssertionError('CX formula used')):
                    result = self.price()
                self.assertEqual(result['status'], 'NEEDS_AIRLINE_QUOTE')
                self.assertIn('PARTNER_AGREEMENT_REQUIRED', result['tickets'][0]['diagnostics'])
                self.assertIsNone(result['tickets'][0]['miles_per_person'])
                self.assertEqual(result['route_status'], 'VERIFIED')
                self.assertEqual(result['award_seat_status'], 'NOT_CHECKED')
                self.assertEqual(result['ticketability_status'], 'NOT_CHECKED')

    def test_partner_a_plus_b_can_remain_separate_quote_required_tickets(self):
        self.c, self.req, self.rules = candidate(carriers=['ZZ', 'ZY'], mode='SEPARATE_AWARDS')
        self.ev = evidence(self.c, self.req, self.rules)
        result = self.price()
        self.assertEqual(result['status'], 'NEEDS_AIRLINE_QUOTE')
        self.assertEqual(result['tickets'][0]['status'], 'NEEDS_AIRLINE_QUOTE')
        self.assertEqual(result['tickets'][1]['status'], 'NEEDS_AIRLINE_QUOTE')

    def test_independent_accounts_and_two_travelers_requirements(self):
        result = self.price(balances_by_account={'TEST_A': 20000, 'TEST_B': 20000})
        self.assertEqual(result['status'], 'EVALUATED')
        self.assertEqual(result['miles_by_traveler'], {'traveler_a': 20000, 'traveler_b': 20000})
        self.assertEqual(result['group_miles'], 40000)
        self.assertEqual(result['account_allocation_status'], 'FEASIBLE')
        for payer, balance in [('TEST_A', 20000), ('TEST_B', 20000)]:
            self.assertLessEqual(sum(a['miles'] for a in result['account_allocation'] if a['payer'] == payer), balance)
        self.assertEqual({a['passenger'] for a in result['account_allocation']}, {'traveler_a', 'traveler_b'})
        self.assertTrue(all(t['group_miles'] == 20000 for t in result['tickets']))

    def test_payment_account_may_fund_other_travelers(self):
        result = self.price(balances_by_account={'TEST_EXTERNAL_PAYER': 40000})
        self.assertEqual(result['account_allocation_status'], 'FEASIBLE')
        self.assertEqual({a['payer'] for a in result['account_allocation']}, {'TEST_EXTERNAL_PAYER'})
        self.assertEqual(result['funding_eligibility_status'], 'NOT_CHECKED')

    def test_insufficient_accounts_do_not_erase_mile_requirements(self):
        result = self.price(balances_by_account={'TEST_A': 10000, 'TEST_B': 0})
        self.assertEqual(result['status'], 'NEEDS_DATA')
        self.assertEqual(result['account_allocation_status'], 'INSUFFICIENT')
        self.assertEqual(result['group_miles'], 40000)
        self.assertIn('ACCOUNT_BALANCE_INSUFFICIENT', result['diagnostics'])
        self.assertFalse(result['complete_price_comparison_eligible'])

    def test_combined_balances_cannot_fund_an_indivisible_ticket_by_pooling(self):
        result = self.price(balances_by_account={'TEST_A': 12000, 'TEST_B': 28000})
        self.assertEqual(result['group_miles'], 40000)
        self.assertEqual(result['account_allocation_status'], 'INSUFFICIENT')

    def test_unknown_and_partially_unknown_balances_are_not_insufficient(self):
        for balances in (None, {}, {'TEST_A': 1, 'TEST_UNKNOWN': None}):
            result = self.price(balances_by_account=balances)
            self.assertEqual(result['status'], 'EVALUATED')
            self.assertEqual(result['account_allocation_status'], 'NOT_CHECKED')
            self.assertFalse(result['account_allocation'])

    def test_unknown_taxes_stay_null_and_not_comparable(self):
        result = self.price()
        self.assertIsNone(result['taxes_hkd_per_person'])
        self.assertIsNone(result['scenario']['taxes_and_surcharges_hkd_per_person'])
        self.assertFalse(result['complete_price_comparison_eligible'])
        self.assertEqual(result['kernel_result']['cost_status'], 'PARTIAL_LOWER_BOUND')

    def test_sourced_cash_completeness_does_not_confirm_seats_or_ticketability(self):
        self.ev['tax_quote'] = dict(bound(self.c, self.rules, 'AIRLINE_QUOTED'), hkd_per_person=1234)
        result = self.price()
        self.assertTrue(result['complete_price_comparison_eligible'])
        self.assertEqual(result['taxes_hkd_per_person'], 1234)
        self.assertEqual(result['award_seat_status'], 'NOT_CHECKED')
        self.assertEqual(result['ticketability_status'], 'NOT_CHECKED')
        self.assertEqual(result['kernel_result']['group_cash_hkd_known'], 2468)

    def test_quoted_taxes_do_not_make_mixed_estimate_comparable(self):
        self.mixed()
        self.ev['tax_quote'] = dict(bound(self.c, self.rules, 'AIRLINE_QUOTED'), hkd_per_person=0)
        result = self.price()
        self.assertEqual(result['pricing_status'], 'RULE_ESTIMATED')
        self.assertFalse(result['complete_price_comparison_eligible'])

    def test_assumed_or_wrong_scope_taxes_are_unknown(self):
        for level in ('ASSUMPTION', 'THIRD_PARTY_OBSERVED'):
            self.ev['tax_quote'] = dict(bound(self.c, self.rules, level), hkd_per_person=100)
            result = self.price()
            self.assertIsNone(result['taxes_hkd_per_person'])
            self.assertFalse(result['complete_price_comparison_eligible'])

    def test_kernel_minimum_cabin_validation_is_not_weakened(self):
        self.req['cabin_preferences']['longhaul_minimum'] = 'F'
        result = self.price()
        self.assertEqual(result['status'], 'UNSUPPORTED')
        self.assertIn('V1_VALIDATION_FAILED', result['diagnostics'])
        self.assertIsNone(result['group_miles'])

    def test_evaluation_ids_and_allocations_are_deterministic_after_normalization(self):
        balances = {'TEST_B': 20000, 'TEST_A': 20000}
        one = self.price(balances_by_account=balances)
        self.req['travelers'].reverse()
        two = self.price(balances_by_account=dict(reversed(list(balances.items()))))
        self.assertEqual(one, two)
        self.assertEqual(one['candidate_id'], self.c['candidate_id'])
        self.assertNotEqual(one['evaluation_id'], one['candidate_id'])
        self.ev['quotes']['return_2']['miles_per_person'] += 1
        self.assertNotEqual(self.price()['evaluation_id'], one['evaluation_id'])

    def test_pr1_pr2_pr3_synthetic_end_to_end_preserves_evidence(self):
        from discovery.holiday_calendar import load_calendar
        from discovery.leave_engine import generate_windows
        from tests._fixtures import snapshot
        request = travel_request(); request['planning_year'] = 2027
        windows = generate_windows(load_calendar(snapshot(2027)), request,
                                  {'holiday_window': {'days_before': 0, 'days_after': 2, 'max_generated_windows_per_holiday': 30}})['windows']
        data = graph_data(); data['edges'][0]['route_status'] = 'STALE'
        candidates = generate_candidates(load_route_graph(data), request, rules(), window=windows[0])['candidates']
        c = next(c for c in candidates if 'LONG_J_SHORT_Y' in c['strategies'] and c['ticketing_mode'] == 'SINGLE_AWARD')
        ev = evidence(c, request, rules())
        pending = price_candidate(c, request, rules())
        self.assertEqual(pending['status'], 'RULE_VERSION_REVIEW_REQUIRED')
        result = price_candidate(c, request, rules(), ev)
        self.assertEqual(result['status'], 'EVALUATED')
        self.assertEqual(result['holiday_status'], 'ESTIMATED')
        self.assertEqual(result['route_status'], 'STALE')
        self.assertEqual(result['candidate']['holiday_window'], windows[0])
        self.assertEqual(result['award_seat_status'], 'NOT_CHECKED')
        self.assertEqual(result['ticketability_status'], 'NOT_CHECKED')
        self.assertEqual(result, price_candidate(c, request, rules(), ev))
        ev['rule_review']['travel_end_date'] = '2027-12-31'
        self.assertEqual(price_candidate(c, request, rules(), ev)['status'], 'RULE_VERSION_REVIEW_REQUIRED')

    def test_flyasia_observations_replay_through_adapter_as_estimates(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/flyasia_pr3_comparisons.json').read_text())
        self.assertEqual(fixture['evidence_level'], 'THIRD_PARTY_OBSERVED')
        for case in fixture['cases']:
            with self.subTest(case=case['id']):
                result = self.mixed(case['cabins'], case['distances'], case['route_type'])
                actual = result['tickets'][0]['miles_per_person']
                self.assertEqual(actual, case['v1_miles'])
                self.assertEqual(actual, case['observed_miles'])  # FLYASIA_MATCH, not official verification.
                self.assertEqual(result['pricing_status'], 'RULE_ESTIMATED')
                self.assertFalse(result['complete_price_comparison_eligible'])

    def test_inferred_hundred_boundary_mismatch_is_preserved_not_patched(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/flyasia_pr3_comparisons.json').read_text())
        case = fixture['synthetic_boundary']
        result = self.mixed(case['cabins'], case['distances'], case['route_type'])
        self.assertEqual(result['tickets'][0]['miles_per_person'], 18000)
        self.assertEqual(case['reported_implementation_implied_miles'], 18100)
        self.assertNotEqual(result['tickets'][0]['miles_per_person'], case['reported_implementation_implied_miles'])
        self.assertEqual(case['observation_kind'], 'REPORTED_IMPLEMENTATION_INFERENCE_NOT_UI_OBSERVED')

    def test_flyasia_partner_toggle_does_not_supply_a_partner_price(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/flyasia_pr3_comparisons.json').read_text())
        self.assertEqual(fixture['partner_toggle']['observed_partner_miles'], 31700)
        self.c, self.req, self.rules = candidate('LONG_J_SHORT_Y', carriers=['CX', 'ZZ'])
        self.ev = evidence(self.c, self.req, self.rules)
        self.assertEqual(self.price()['status'], 'NEEDS_AIRLINE_QUOTE')


    def test_mixed_ticket_data_must_bind_candidate_rules_and_dates(self):
        self.mixed()
        for key, value in [('candidate_id', 'different'), ('rules_digest', 'different'),
                           ('travel_start_date', '2028-01-01')]:
            ev = copy.deepcopy(self.ev); ev['ticket_data']['outbound_1'][key] = value
            result = self.price(evidence=ev)
            self.assertEqual(result['status'], 'NEEDS_DATA')
            self.assertIn('TICKET_DATA_SCOPE_REQUIRED', result['tickets'][0]['diagnostics'])

    def test_wrong_date_or_candidate_tax_quote_cannot_complete_cost(self):
        for key, value in [('candidate_id', 'other'), ('travel_end_date', '2028-01-01')]:
            self.ev['tax_quote'] = dict(bound(self.c, self.rules, 'AIRLINE_QUOTED'), hkd_per_person=100)
            self.ev['tax_quote'][key] = value
            result = self.price()
            self.assertIsNone(result['taxes_hkd_per_person'])
            self.assertFalse(result['complete_price_comparison_eligible'])

    def test_fully_ready_candidate_really_calls_v1_evaluate_once(self):
        with patch('discovery.award_pricing.evaluate', wraps=evaluate) as kernel:
            result = self.price()
            kernel.assert_called_once_with(result['scenario'], self.rules, result['settings'])

    def test_zero_quoted_miles_are_rejected_before_v1_evaluation(self):
        for quote in self.ev['quotes'].values(): quote['miles_per_person'] = 0
        with patch('discovery.award_pricing.evaluate') as kernel:
            result = self.price(balances_by_account={'TEST_ZERO': 0})
            kernel.assert_not_called()
        self.assertEqual(result['status'], 'NEEDS_DATA')
        self.assertFalse(result['v1_evaluated'])
        self.assertIsNone(result['scenario'])
        self.assertIsNone(result['group_miles'])
        self.assertIsNone(result['per_person_miles'])
        self.assertFalse(result['complete_price_comparison_eligible'])
        self.assertEqual(result['known_miles_subtotal_per_person'], 0)
        self.assertTrue(all(t['miles_per_person'] is None for t in result['tickets']))
        self.assertTrue(all(t['diagnostics'] == ['INVALID_STANDARD_QUOTE_MILES'] for t in result['tickets']))

    def test_zero_miles_plus_quoted_zero_taxes_cannot_become_comparable(self):
        for quote in self.ev['quotes'].values(): quote['miles_per_person'] = 0
        self.ev['tax_quote'] = dict(bound(self.c, self.rules, 'AIRLINE_QUOTED'), hkd_per_person=0)
        with patch('discovery.award_pricing.evaluate') as kernel:
            result = self.price(); kernel.assert_not_called()
        self.assertEqual(result['status'], 'NEEDS_DATA')
        self.assertIsNone(result['kernel_result'])
        self.assertFalse(result['complete_price_comparison_eligible'])
        self.assertEqual(result['known_group_miles_subtotal'], 0)
        self.assertTrue(all(t['group_miles'] is None for t in result['tickets']))

    def test_one_nonpositive_quote_keeps_only_valid_ticket_subtotals(self):
        for invalid_ticket in ('outbound_1', 'return_2'):
            for invalid_miles in (0, -1):
                with self.subTest(ticket=invalid_ticket, miles=invalid_miles):
                    ev = copy.deepcopy(self.ev)
                    ev['quotes'][invalid_ticket]['miles_per_person'] = invalid_miles
                    ev['tax_quote'] = dict(bound(self.c, self.rules, 'AIRLINE_QUOTED'), hkd_per_person=0)
                    with patch('discovery.award_pricing.evaluate') as kernel:
                        result = self.price(evidence=ev); kernel.assert_not_called()
                    self.assertEqual(result['status'], 'NEEDS_DATA')
                    self.assertEqual(result['pricing_status'], 'UNKNOWN')
                    self.assertFalse(result['complete_price_comparison_eligible'])
                    self.assertIsNone(result['group_miles'])
                    self.assertEqual(result['known_miles_subtotal_per_person'], 10000)
                    self.assertEqual(result['known_group_miles_subtotal'], 20000)
                    bad = next(t for t in result['tickets'] if t['ticket_id'] == invalid_ticket)
                    self.assertEqual(bad['status'], 'NEEDS_DATA')
                    self.assertIn('INVALID_STANDARD_QUOTE_MILES', bad['diagnostics'])
                    self.assertIsNone(bad['miles_per_person'])
                    self.assertIsNone(bad['group_miles'])

    def test_positive_miles_with_quoted_zero_taxes_still_evaluate(self):
        for quote in self.ev['quotes'].values(): quote['miles_per_person'] = 1
        self.ev['tax_quote'] = dict(bound(self.c, self.rules, 'AIRLINE_QUOTED'), hkd_per_person=0)
        result = self.price()
        self.assertEqual(result['status'], 'EVALUATED')
        self.assertEqual(result['group_miles'], 4)
        self.assertEqual(result['taxes_hkd_per_person'], 0)
        self.assertTrue(result['complete_price_comparison_eligible'])
        self.assertEqual(result['evidence_verification_status'], 'SUPPLIED_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED')


if __name__ == '__main__':
    unittest.main()
