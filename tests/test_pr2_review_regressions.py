"""PR2 review regressions; all airports/services/partner codes are synthetic TEST data."""
import copy
import json
import unittest

from discovery.candidate_generator import generate_candidates
from discovery.route_graph import load_route_graph
from tests._route_fixtures import config, edge, graph_data, rules, travel_request


class PR2ReviewRegressionTests(unittest.TestCase):
    def generate(self, outbound=2, returning=1, separate=True, carriers=None,
                 supplied=None, cfg=None, window=None):
        # Disjoint synthetic chains make directional limits observable independently.
        nodes = {'outbound': ['AAA', 'BBB', 'EEE', 'CCC'],
                 'return': ['CCC', 'DDD', 'FFF', 'AAA']}
        edges = []
        for direction, count in (('outbound', outbound), ('return', returning)):
            chain = nodes[direction][:count] + [nodes[direction][-1]]
            for i, (a, b) in enumerate(zip(chain, chain[1:])):
                carrier = carriers[i] if carriers and direction == 'outbound' else 'CX'
                edges.append(edge(a, b, 6000 if i == count - 1 else 800, carrier))
        request = travel_request()
        request['cabin_preferences']['allow_separate_tickets'] = separate
        limits = config() if cfg is None else copy.deepcopy(cfg)
        if cfg is None:
            limits['route_search'].update(max_flight_legs_per_trip=6, max_connections=4)
        return generate_candidates(load_route_graph(graph_data(edges)), request,
                                   rules() if supplied is None else supplied, config=limits, window=window)

    def rejections(self, result):
        return [r for d in result['diagnostics'] for r in d.get('ticket_structure_rejections', [])]

    def same_ticket(self, result, strategy='ALL_J'):
        return [c for c in result['candidates'] if c['ticketing_mode'] == 'SINGLE_AWARD' and strategy in c['strategies']]

    def test_one_sector_per_direction_can_form_standard(self):
        rows = self.same_ticket(self.generate(outbound=1, separate=False))
        self.assertTrue(rows)
        self.assertEqual([len(t['leg_indices']) for t in rows[0]['tickets']], [1, 1])
        self.assertTrue(all(t['proposed_scheme'] == 'standard' for t in rows[0]['tickets']))

    def test_two_sectors_can_form_standard_with_unchecked_transfer(self):
        rows = self.same_ticket(self.generate(separate=False)); self.assertTrue(rows)
        ticket = rows[0]['tickets'][0]
        self.assertEqual(ticket['leg_indices'], [0, 1])
        self.assertEqual(ticket['proposed_scheme'], 'standard')
        self.assertIn('TRANSFER_HOURS_REQUIRED', ticket['requirements'])
        self.assertIsNone(ticket['transfer_hours'])
        self.assertEqual(ticket['max_transfer_hours'], 24)

    def test_three_outbound_sectors_fail_closed_without_split(self):
        result = self.generate(outbound=3, separate=False)
        self.assertFalse(result['candidates'])
        reasons = self.rejections(result); self.assertTrue(reasons)
        self.assertEqual({r['code'] for r in reasons}, {'STANDARD_SECTOR_LIMIT_EXCEEDED'})
        self.assertEqual({r['direction'] for r in reasons}, {'outbound'})
        self.assertTrue(all(r['sector_count'] == 3 for r in reasons))
        self.assertTrue(all(r['rule_source']['evidence_type'] == 'OFFICIAL_PUBLISHED' for r in reasons))

    def test_search_relaxation_does_not_relax_award_limit(self):
        for bound in (4, 6, 10):
            with self.subTest(bound=bound):
                cfg = config(); cfg['route_search'].update(max_flight_legs_per_trip=bound, max_connections=8)
                result = self.generate(outbound=3, separate=False, cfg=cfg)
                self.assertFalse(result['candidates'])
                self.assertIn('STANDARD_SECTOR_LIMIT_EXCEEDED', {r['code'] for r in self.rejections(result)})

    def test_three_outbound_sectors_split_only_when_allowed(self):
        result = self.generate(outbound=3); self.assertTrue(result['candidates'])
        for c in result['candidates']:
            self.assertEqual(c['ticketing_mode'], 'SEPARATE_AWARDS')
            self.assertEqual([t['leg_indices'] for t in c['tickets']], [[0], [1], [2], [3]])
            self.assertTrue(all(t['proposed_scheme'] == 'standard' for t in c['tickets']))
            self.assertEqual(c['ticketability_status'], 'NOT_CHECKED')

    def test_return_direction_is_independently_limited(self):
        result = self.generate(outbound=1, returning=3, separate=False)
        self.assertFalse(result['candidates'])
        self.assertEqual({r['direction'] for r in self.rejections(result)}, {'return'})
        self.assertEqual({r['code'] for r in self.rejections(result)}, {'STANDARD_SECTOR_LIMIT_EXCEEDED'})

    def test_two_plus_two_is_allowed_not_rejected_by_total_four(self):
        rows = self.same_ticket(self.generate(returning=2, separate=False)); self.assertTrue(rows)
        self.assertEqual([len(t['leg_indices']) for t in rows[0]['tickets']], [2, 2])

    def test_award_sector_limit_is_read_from_rules(self):
        supplied = rules(); supplied['standard_award_constraints']['max_sectors_per_direction'] = 1
        result = self.generate(separate=False, supplied=supplied)
        self.assertFalse(result['candidates'])
        self.assertIn('STANDARD_SECTOR_LIMIT_EXCEEDED', {r['code'] for r in self.rejections(result)})
        self.assertTrue(self.generate(supplied=supplied)['candidates'])

    def test_transfer_count_and_hours_are_policy_driven(self):
        supplied = rules(); supplied['standard_award_constraints']['max_transfers_per_direction'] = 0
        result = self.generate(separate=False, supplied=supplied)
        self.assertFalse(result['candidates'])
        self.assertEqual({r['code'] for r in self.rejections(result)}, {'STANDARD_TRANSFER_LIMIT_EXCEEDED'})
        supplied['standard_award_constraints'].update(max_transfers_per_direction=1, max_transfer_hours=12)
        rows = self.same_ticket(self.generate(separate=False, supplied=supplied)); self.assertTrue(rows)
        self.assertEqual(rows[0]['tickets'][0]['max_transfer_hours'], 12)
        self.assertIn('TRANSFER_HOURS_REQUIRED', rows[0]['tickets'][0]['requirements'])

    def test_missing_or_uninterpretable_policy_fails_closed_even_for_split(self):
        for replacement in (None, {}, {'max_sectors_per_direction': True}):
            with self.subTest(replacement=replacement):
                supplied = rules(); supplied['standard_award_constraints'] = replacement
                result = self.generate(supplied=supplied)
                self.assertFalse(result['candidates'])
                self.assertIn('STANDARD_AWARD_POLICY_REQUIRED', {d['code'] for d in result['diagnostics']})
        supplied = rules(); del supplied['standard_award_constraints']
        self.assertFalse(self.generate(outbound=1, supplied=supplied)['candidates'])

    def test_cx_plus_cx_remains_supported_with_existing_mixed_capability(self):
        result = self.generate(carriers=['CX', 'CX'], separate=False)
        rows = self.same_ticket(result, 'LONG_J_SHORT_Y'); self.assertTrue(rows)
        self.assertEqual(rows[0]['tickets'][0]['proposed_scheme'], 'standard_mixed')
        self.assertNotIn('PARTNER_AGREEMENT_REQUIRED', rows[0]['tickets'][0]['requirements'])
        supplied = rules(); del supplied['standard_mixed_constraints']
        self.assertFalse(self.same_ticket(self.generate(separate=False, supplied=supplied), 'LONG_J_SHORT_Y'))

    def check_partner(self, carriers):
        result = self.generate(carriers=carriers, separate=False)
        rows = self.same_ticket(result); self.assertTrue(rows)
        for c in result['candidates']:
            ticket = c['tickets'][0]
            self.assertEqual(ticket['structure_status'], 'NEEDS_PARTNER_AGREEMENT_AND_QUOTE')
            self.assertTrue({'CARRIER_REDEMPTION_ELIGIBILITY_REQUIRED', 'PARTNER_AGREEMENT_REQUIRED',
                             'AIRLINE_QUOTE_REQUIRED'}.issubset(ticket['requirements']))
            self.assertEqual(c['pricing_status'], 'UNKNOWN')
            self.assertEqual(c['award_seat_status'], 'NOT_CHECKED')
            self.assertEqual(c['ticketability_status'], 'NOT_CHECKED')
            self.assertFalse(c['complete_price_comparison_eligible'])
            self.assertIsNone(c['miles_per_person']); self.assertIsNone(c['taxes_hkd_per_person'])
        mixed = self.same_ticket(result, 'LONG_J_SHORT_Y'); self.assertTrue(mixed)
        self.assertIsNone(mixed[0]['tickets'][0]['proposed_scheme'])
        return result

    def test_cx_plus_partner_is_quote_required_not_route_invalid(self):
        self.check_partner(['CX', 'ZZ'])

    def test_partner_plus_cx_is_quote_required_not_route_invalid(self):
        self.check_partner(['ZZ', 'CX'])

    def test_same_partner_is_quote_required_including_mixed_cabin(self):
        self.check_partner(['ZZ', 'ZZ'])

    def test_two_partners_have_official_same_ticket_rejection_but_split_remains(self):
        result = self.generate(carriers=['ZZ', 'ZY']); self.assertTrue(result['candidates'])
        self.assertFalse(self.same_ticket(result))
        self.assertTrue(all(c['ticketing_mode'] == 'SEPARATE_AWARDS' for c in result['candidates']))
        reasons = self.rejections(result)
        self.assertEqual({r['code'] for r in reasons}, {'STANDARD_MIXED_CARRIERS_REQUIRE_PRIMARY'})
        self.assertTrue(all('Standard Awards 4' in r['rule_source']['carrier_clause'] for r in reasons))
        self.assertFalse(self.generate(carriers=['ZZ', 'ZY'], separate=False)['candidates'])
        for c in result['candidates']:
            self.assertTrue(all(t['structure_status'] == 'NEEDS_PARTNER_AGREEMENT_AND_QUOTE' for t in c['tickets'][:2]))

    def test_carrier_policy_constraints_follow_fixture_not_python_constants(self):
        supplied = rules(); supplied['standard_award_constraints']['max_mixed_carriers'] = 1
        result = self.generate(carriers=['CX', 'ZZ'], separate=False, supplied=supplied)
        self.assertFalse(result['candidates'])
        self.assertEqual({r['code'] for r in self.rejections(result)}, {'STANDARD_CARRIER_COUNT_EXCEEDED'})
        # Synthetic fixture exercises the interpreter; not a real partnership assertion.
        supplied['standard_award_constraints'].update(max_mixed_carriers=2, mixed_carrier_requires_primary=False)
        rows = self.same_ticket(self.generate(carriers=['ZZ', 'ZY'], separate=False, supplied=supplied))
        self.assertTrue(rows)
        self.assertEqual(rows[0]['tickets'][0]['structure_status'], 'NEEDS_PARTNER_AGREEMENT_AND_QUOTE')

    def test_officially_excluded_standard_carrier_is_not_assumed_eligible(self):
        result = self.generate(carriers=['UO', 'UO'])
        self.assertFalse(result['candidates'])
        self.assertIn('STANDARD_CARRIER_EXCLUDED', {r['code'] for r in self.rejections(result)})

    def test_partner_ids_and_diagnostics_are_stable_without_mutating_rules(self):
        supplied = rules(); original = copy.deepcopy(supplied)
        first = self.generate(carriers=['CX', 'ZZ'], supplied=supplied)
        second = self.generate(carriers=['CX', 'ZZ'], supplied=supplied)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(supplied, original)
        self.assertEqual(self.generate(outbound=3), self.generate(outbound=3))
        # Carrier/evidence changes must not retain the old structure identity.
        self.assertTrue({c['candidate_id'] for c in first['candidates']}.isdisjoint(
            {c['candidate_id'] for c in self.generate(carriers=['CX', 'CX'])['candidates']}))

    def test_window_endpoints_and_snapshot_verification_are_explicit_assumptions(self):
        window = {'window_id': 'TEST_WINDOW', 'start_date': '2027-01-01', 'end_date': '2027-01-03',
                  'holiday_status': 'ESTIMATED', 'errors': []}
        result = self.generate(window=window); self.assertTrue(result['candidates'])
        for c in result['candidates']:
            self.assertEqual(c['route_status'], 'VERIFIED')
            assumptions = c['assumptions']
            self.assertEqual(assumptions['route_verification'], 'SUPPLIED_SNAPSHOT_EVIDENCE_ONLY')
            self.assertEqual(assumptions['route_dates'], 'WINDOW_ENDPOINTS_FOR_EACH_DIRECTION')
            for key in ('schedule_validation', 'overnight_arrival', 'timezone_local_dates'):
                self.assertEqual(assumptions[key], 'NOT_CHECKED')
            self.assertEqual(c['holiday_window']['window_id'], 'TEST_WINDOW')


if __name__ == '__main__':
    unittest.main()
