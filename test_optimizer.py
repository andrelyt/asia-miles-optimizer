import json, unittest
from pathlib import Path
from optimizer import evaluate, tier_price, mixed_cabin_price
P=Path(__file__).parent
R=json.loads((P/'rules_2026_10.json').read_text())
C=json.loads((P/'sample_input.json').read_text())

class OptimizerTests(unittest.TestCase):
    def test_oneworld_210k(self): self.assertEqual(tier_price(16686,'J',R['oneworld_bands'])[0],210000)
    def test_oneworld_170k(self): self.assertEqual(tier_price(13529,'J',R['oneworld_bands'])[0],170000)
    def test_no_pe_in_oneworld(self):
        with self.assertRaises(ValueError): tier_price(16000,'W',R['oneworld_bands'])
    def test_oneworld_mixed_still_highest(self):
        a=[x for x in C['scenarios'] if x['id']=='B'][0]; b=[x for x in C['scenarios'] if x['id']=='I'][0]
        self.assertEqual(evaluate(a,R,C['settings'])['per_person_miles'],evaluate(b,R,C['settings'])['per_person_miles'])
    def test_all_options_have_connected_trips_and_no_errors(self):
        for x in C['scenarios']:
            with self.subTest(id=x['id']): self.assertFalse(evaluate(x,R,C['settings'])['errors'])
    def test_account_cant_be_combined(self):
        settings=dict(C['settings']); settings['balances_by_account']={'Andre':200000,'Dony':200000}; x=[o for o in C['scenarios'] if o['id']=='B'][0]
        self.assertTrue(any('账户' in e for e in evaluate(x,R,settings)['errors']))
    def test_standard_mixed_proportional_round_down_to_hundred(self):
        legs=[{'from':'PVG','to':'HKG','airline':'CX','cabin':'Y','distance_mi':800},{'from':'HKG','to':'LHR','airline':'CX','cabin':'J','distance_mi':5994}]
        expected=int(((800/6794*27000)+(5994/6794*91000))//100*100)
        self.assertEqual(mixed_cabin_price(legs,{'transfer_hours':2},R['cx_standard_chart']),expected)
    def test_expected_2026_pe_longhaul_price(self):
        g=[o for o in C['scenarios'] if o['id']=='G'][0]; self.assertEqual(evaluate(g,R,C['settings'])['per_person_miles'],130000)
    def test_missing_tax_not_quoted(self):
        a=[o for o in C['scenarios'] if o['id']=='A'][0]; self.assertIn('LOWER_BOUND',evaluate(a,R,C['settings'])['cost_status'])
if __name__=='__main__': unittest.main()
