"""Mapping/gates with exclusively synthetic TEST snapshots and evidence."""
import copy
import unittest

from discovery.award_adapter import adapt_candidate
from tests._award_fixtures import candidate, evidence, reidentify, source


class AwardAdapterTests(unittest.TestCase):
    def setUp(self):
        self.c, self.req, self.rules = candidate()
        self.ev = evidence(self.c, self.req, self.rules)

    def adapt(self, **kw):
        return adapt_candidate(self.c, self.req, self.rules, kw.pop('evidence', self.ev), **kw)

    def test_single_sector_standard_mapping_preserves_ticket_boundaries(self):
        row = self.adapt()
        self.assertEqual(row['status'], 'READY_FOR_EVALUATION')
        self.assertEqual([t['scheme'] for t in row['scenario']['award_tickets']], ['standard', 'standard'])
        self.assertEqual([l['ticket_id'] for l in row['scenario']['trips'][0]['legs']],
                         ['outbound_1', 'outbound_1', 'return_2'])
        self.assertEqual(row['scenario']['trips'][0]['legs'][-1]['distance_mi'], 6500)

    def test_missing_standard_quote_is_unknown_not_distance_derived(self):
        self.ev['quotes'].clear()
        row = self.adapt()
        self.assertEqual(row['status'], 'NEEDS_AIRLINE_QUOTE')
        self.assertTrue(all(t['miles_per_person'] is None for t in row['tickets']))
        self.assertIsNone(row['scenario'])

    def test_third_party_quote_never_becomes_verified(self):
        for q in self.ev['quotes'].values(): q['evidence_level'] = 'THIRD_PARTY_OBSERVED'
        row = self.adapt()
        self.assertEqual(row['status'], 'NEEDS_AIRLINE_QUOTE')
        self.assertEqual(row['pricing_status'], 'UNKNOWN')
        self.assertEqual(row['tickets'][0]['evidence']['quote']['evidence_level'], 'THIRD_PARTY_OBSERVED')

    def test_quote_requires_candidate_and_exact_rule_binding(self):
        for key, value in [('candidate_id', 'other'), ('rules_digest', 'other'),
                           ('rules_version', 'other'), ('rules_as_of', '2026-01-01')]:
            with self.subTest(key=key):
                ev = copy.deepcopy(self.ev); ev['quotes']['outbound_1'][key] = value
                self.assertEqual(self.adapt(evidence=ev)['status'], 'NEEDS_AIRLINE_QUOTE')

    def test_quote_requires_source_and_timezone_aware_time(self):
        for key, value in [('source_url', None), ('source_url', 'file:///tmp/quote'),
                           ('observed_at', '2026-10-15'), ('observed_at', 'bad')]:
            ev = copy.deepcopy(self.ev); ev['quotes']['outbound_1'][key] = value
            self.assertEqual(self.adapt(evidence=ev)['status'], 'NEEDS_AIRLINE_QUOTE')

    def test_future_chart_requires_explicit_applicability_review(self):
        self.req['planning_year'] = 2027
        row = self.adapt()
        self.assertEqual(row['status'], 'RULE_VERSION_REVIEW_REQUIRED')
        self.assertEqual(row['pricing_status'], 'UNKNOWN')
        self.assertEqual(self.adapt(evidence=evidence(self.c, self.req, self.rules))['status'], 'READY_FOR_EVALUATION')

    def test_as_of_is_not_an_effective_date_even_in_2026(self):
        del self.ev['rule_review']
        self.assertEqual(self.adapt()['status'], 'RULE_VERSION_REVIEW_REQUIRED')

    def test_rule_review_cannot_be_third_party_or_for_another_rule(self):
        for key, value in [('evidence_level', 'THIRD_PARTY_OBSERVED'), ('rules_digest', 'other'),
                           ('decision', 'UNKNOWN'), ('booking_date', '2028-01-01')]:
            ev = copy.deepcopy(self.ev); ev['rule_review'][key] = value
            self.assertEqual(self.adapt(evidence=ev)['status'], 'RULE_VERSION_REVIEW_REQUIRED')

    def test_modified_rules_invalidate_review_without_silent_repricing(self):
        self.rules['cx_standard_chart'][0]['miles']['Y'] += 1
        self.assertEqual(self.adapt()['status'], 'RULE_VERSION_REVIEW_REQUIRED')

    def test_unknown_balances_not_imported_from_traveler_schema(self):
        row = self.adapt()
        self.assertEqual(row['balance_evidence_status'], 'UNKNOWN')
        self.assertEqual(row['settings']['balances_by_account'], {})
        self.assertEqual(row['settings']['passengers'], ['traveler_a', 'traveler_b'])

    def test_partial_unknown_balance_never_replaced_with_zero(self):
        row = self.adapt(balances_by_account={'TEST_A': 12345, 'TEST_B': None})
        self.assertEqual(row['balances_by_account']['TEST_B'], None)
        self.assertEqual(row['settings']['balances_by_account'], {})
        self.assertEqual(row['balance_evidence_status'], 'UNKNOWN')

    def test_invalid_quote_and_balance_numbers_are_rejected(self):
        for value in (-1, True, float('nan'), '10000', 1.5):
            ev = copy.deepcopy(self.ev); ev['quotes']['outbound_1']['miles_per_person'] = value
            self.assertEqual(self.adapt(evidence=ev)['status'], 'NEEDS_DATA')
            self.assertEqual(self.adapt(balances_by_account={'TEST_A': value})['status'], 'NEEDS_DATA')

    def test_unsupported_modes_schemes_and_roundtrip_grouping(self):
        for mode in ('ROUNDTRIP_AWARD', 'AWARD_PLUS_CASH', 'ONEWORLD_MULTI'):
            c = copy.deepcopy(self.c); c['ticketing_mode'] = mode; reidentify(c)
            self.assertEqual(adapt_candidate(c, self.req, self.rules)['status'], 'UNSUPPORTED')
        self.c['tickets'][0]['proposed_scheme'] = 'oneworld_multi'; reidentify(self.c)
        self.assertEqual(self.adapt()['status'], 'UNSUPPORTED')

    def test_duplicate_missing_and_boolean_leg_references_rejected(self):
        for indices in ([0, 0], [0], [False, 1], [0, 1, 2]):
            c = copy.deepcopy(self.c); c['tickets'][0]['leg_indices'] = indices; reidentify(c)
            self.assertEqual(adapt_candidate(c, self.req, self.rules)['status'], 'UNSUPPORTED')

    def test_stable_candidate_id_cannot_silently_describe_changed_legs(self):
        self.c['legs'][0]['distance_miles'] += 1
        self.assertEqual(self.adapt()['status'], 'NEEDS_DATA')

    def test_route_continuity_and_traveler_binding(self):
        self.c['legs'][0]['destination'] = 'ZZZ'; reidentify(self.c)
        self.assertEqual(self.adapt()['status'], 'NEEDS_DATA')
        self.c, _, _ = candidate(); self.req['travelers'][0]['id'] = 'DIFFERENT_TEST_TRAVELER'
        self.assertEqual(self.adapt()['status'], 'NEEDS_DATA')

    def test_supplied_evidence_and_inputs_not_mutated(self):
        args = copy.deepcopy((self.c, self.req, self.rules, self.ev))
        self.adapt()
        self.assertEqual(args, (self.c, self.req, self.rules, self.ev))

    def test_malformed_input_returns_diagnostic_without_crash(self):
        for ev in ([], 'bad', {'ticket_data': []}, {'quotes': []}):
            if isinstance(ev, dict): ev['rule_review'] = self.ev['rule_review']
            row = self.adapt(evidence=ev)
            self.assertEqual(row['status'], 'NEEDS_DATA')
            self.assertTrue(row['diagnostics'])
        self.assertEqual(adapt_candidate(None, self.req, self.rules)['status'], 'NEEDS_DATA')

    def test_unknown_ticket_evidence_is_not_silently_ignored(self):
        self.ev['quotes']['NONEXISTENT_TEST_TICKET'] = {}
        self.assertEqual(self.adapt()['status'], 'NEEDS_DATA')

    def test_split_ticket_preference_rechecked(self):
        self.c, self.req, self.rules = candidate(mode='SEPARATE_AWARDS')
        self.req['cabin_preferences']['allow_separate_tickets'] = False
        self.assertEqual(self.adapt()['status'], 'UNSUPPORTED')

    def test_missing_policy_fails_closed(self):
        del self.rules['standard_award_constraints']
        self.assertEqual(self.adapt()['status'], 'UNSUPPORTED')


    def test_quote_dates_cannot_be_reused_for_another_booking_or_trip(self):
        for key in ('booking_date', 'travel_start_date', 'travel_end_date'):
            ev = copy.deepcopy(self.ev); ev['quotes']['outbound_1'][key] = '2027-01-01'
            self.assertEqual(self.adapt(evidence=ev)['status'], 'NEEDS_AIRLINE_QUOTE')

    def test_invalid_route_state_cannot_be_promoted_to_verified(self):
        self.c['legs'][0]['route_status'] = 'UNRECOGNIZED_TEST_STATE'; reidentify(self.c)
        row = self.adapt()
        self.assertEqual(row['status'], 'NEEDS_DATA')
        self.assertEqual(row['route_status'], 'UNVERIFIED')

    def test_aggregate_evidence_cannot_upgrade_a_stale_leg(self):
        self.c['legs'][0]['route_status'] = 'STALE'; reidentify(self.c)
        row = self.adapt()
        self.assertEqual(row['status'], 'NEEDS_DATA')
        self.assertEqual(row['route_status'], 'UNVERIFIED')

    def test_verified_route_without_source_is_rejected(self):
        self.c['legs'][0]['source_url'] = None; reidentify(self.c)
        self.assertEqual(self.adapt()['status'], 'NEEDS_DATA')

    def test_cross_year_review_uses_window_not_just_start_year(self):
        window = {'start_date': '2026-12-31', 'end_date': '2027-01-03',
                  'holiday_status': 'ESTIMATED', 'errors': []}
        self.c, self.req, self.rules = candidate(window=window)
        self.ev = evidence(self.c, self.req, self.rules)
        self.assertEqual(self.adapt()['status'], 'READY_FOR_EVALUATION')
        self.c['holiday_status'] = 'OFFICIAL'; reidentify(self.c)
        row = self.adapt()
        self.assertEqual(row['status'], 'NEEDS_DATA')
        self.assertIsNone(row['holiday_status'])


    def test_changed_destination_or_mixed_preference_cannot_reuse_candidate(self):
        self.req['destinations'][0]['value'] = 'ZZZ'
        self.assertEqual(self.adapt()['status'], 'UNSUPPORTED')
        self.c, self.req, self.rules = candidate('LONG_J_SHORT_Y')
        self.req['cabin_preferences']['allow_mixed_cabin'] = False
        self.assertEqual(self.adapt()['status'], 'UNSUPPORTED')


if __name__ == '__main__':
    unittest.main()
