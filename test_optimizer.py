import copy, csv, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from optimizer import evaluate, tier_price, mixed_cabin_price, sort_results, latest_rules
P=Path(__file__).parent
R=json.loads((P/'rules_2026_10.json').read_text())
C=json.loads((P/'sample_input.json').read_text())

class OptimizerTests(unittest.TestCase):
    def test_oneworld_210k(self): self.assertEqual(tier_price(16686,'J',R['oneworld_bands'],R['oneworld_constraints'])[0],210000)
    def test_oneworld_170k(self): self.assertEqual(tier_price(13529,'J',R['oneworld_bands'],R['oneworld_constraints'])[0],170000)
    def test_no_pe_in_oneworld(self):
        with self.assertRaises(ValueError): tier_price(16000,'W',R['oneworld_bands'],R['oneworld_constraints'])
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
        self.assertEqual(mixed_cabin_price(legs,{'transfer_hours':2},R['cx_standard_chart'],R['standard_mixed_constraints']),expected)
    def test_expected_2026_pe_longhaul_price(self):
        g=[o for o in C['scenarios'] if o['id']=='G'][0]; self.assertEqual(evaluate(g,R,C['settings'])['per_person_miles'],130000)
    def test_missing_tax_not_quoted(self):
        a=[o for o in C['scenarios'] if o['id']=='A'][0]; self.assertIn('LOWER_BOUND',evaluate(a,R,C['settings'])['cost_status'])



def scenario(sid):
    return copy.deepcopy(next(x for x in C['scenarios'] if x['id']==sid))


class CorrectnessRegressionTests(unittest.TestCase):
    def check(self,option,rules=None,settings=None):
        return evaluate(option,rules or R,settings or C['settings'])

    def test_standard_mixed_evaluate_and_account_allocation(self):
        o=scenario('M'); r=self.check(o)
        expected=2*int((800/6794*27000+5994/6794*91000)//100*100)
        self.assertFalse(r['errors']); self.assertEqual(r['per_person_miles'],expected)
        self.assertEqual(r['group_miles'],2*expected)
        self.assertEqual(sum(a['miles'] for a in r['account_allocation']),r['group_miles'])
        self.assertEqual(r['account_allocation_status'],'FEASIBLE')
        settings=copy.deepcopy(C['settings']); settings['balances_by_account']={'A':1,'B':1}
        self.assertTrue(any('账户' in e for e in self.check(o,settings=settings)['errors']))

    def test_standard_mixed_invalid_input_returns_errors(self):
        mutations=[('transfer_hours',None),('transfer_hours',-1),('transfer_hours',25),('transfer_hours','2'),('route_type',3)]
        for key,value in mutations:
            with self.subTest(key=key,value=value):
                o=scenario('M'); o['award_tickets'][0][key]=value
                self.assertTrue(self.check(o)['errors'])
        for key,value in [('distance_mi',0),('distance_mi',-1),('distance_mi',None),('distance_mi','800'),('cabin','BAD'),('airline','BA'),('from',None)]:
            with self.subTest(key=key,value=value):
                o=scenario('M'); o['trips'][0]['legs'][0][key]=value
                self.assertTrue(self.check(o)['errors'])
        o=scenario('M'); o['trips'][0]['legs'][1]['from']='NRT'
        self.assertTrue(self.check(o)['errors'])
        o=scenario('M'); o['trips'][0]['legs'].pop(0)
        self.assertTrue(self.check(o)['errors'])

    def test_standard_mixed_short_route_type_required(self):
        o=scenario('M')
        for leg in o['trips'][0]['legs']: leg['distance_mi']=800
        self.assertTrue(self.check(o)['errors'])
        for ticket in o['award_tickets']: ticket['route_type']=1
        self.assertFalse(self.check(o)['errors'])

    def test_cash_only_with_balances(self):
        r=self.check(scenario('C'))
        self.assertFalse(r['errors']); self.assertEqual(r['group_miles'],0)
        self.assertEqual(r['account_allocation_status'],'NOT_REQUIRED')
        self.assertEqual(r['account_allocation'],[])
        self.assertEqual(r['group_cash_hkd_known'],6000)
        self.assertEqual(r['valued_miles_plus_known_cash_hkd'],6000)

    def test_cash_only_still_validates_paths_and_cabins(self):
        o=scenario('C'); o['trips'][0]['legs'][1]['from']='NRT'
        self.assertTrue(any('断点' in e for e in self.check(o)['errors']))
        o=scenario('C'); settings=copy.deepcopy(C['settings']); settings['min_shorthaul_cabin']='J'
        self.assertTrue(any('最低舱位' in e for e in self.check(o,settings=settings)['errors']))
        o['trips'][0]['legs'][0]['cabin']='INVALID'
        self.assertTrue(any('舱位代码非法' in e for e in self.check(o)['errors']))

    def test_standard_invalid_miles_never_reduce_ranked_cost(self):
        for value in (-1,None,'100',True,float('nan'),float('inf'),1.5):
            with self.subTest(value=value):
                o=scenario('A'); o['award_tickets'][0]['miles_per_person']=value
                r=self.check(o)
                self.assertTrue(r['errors']); self.assertGreaterEqual(r['per_person_miles'],0)
                self.assertEqual(r['cost_status'],'INVALID')
                self.assertIsNone(r['valued_miles_plus_known_cash_hkd'])
                self.assertFalse(r['complete_price_comparison_eligible'])

    def test_empty_trips_and_empty_legs(self):
        for mode in ('missing','empty','null','empty_legs','null_legs'):
            with self.subTest(mode=mode):
                o=scenario('C')
                if mode=='missing': del o['trips']
                elif mode=='empty': o['trips']=[]
                elif mode=='null': o['trips']=None
                elif mode=='null_legs': o['trips'][0]['legs']=None
                else: o['trips'][0]['legs']=[]
                self.assertTrue(self.check(o)['errors'])

    def test_mixed_round_trip_and_cross_trip_rejected(self):
        o=scenario('M'); o['trips'][0]['legs'][1]['to']='PVG'
        self.assertTrue(any('单程' in e for e in self.check(o)['errors']))
        o=scenario('M'); legs=o['trips'][0]['legs']
        o['trips']=[{'id':'a','legs':legs[:1]}, {'id':'b','legs':legs[1:]}]
        self.assertTrue(any('同一次 trip' in e for e in self.check(o)['errors']))

    def test_duplicate_ticket_and_unlinked_award_rejected(self):
        o=scenario('A'); o['award_tickets'].append(copy.deepcopy(o['award_tickets'][0]))
        self.assertTrue(any('重复' in e for e in self.check(o)['errors']))
        o=scenario('A'); o['trips'][0]['legs'][0]['ticket_id']='missing'
        self.assertTrue(any('缺少 ticket' in e for e in self.check(o)['errors']))

    def test_invalid_account_balance_and_valuation_rejected(self):
        for field in ('balances_by_account','mile_value_hkd'):
            settings=copy.deepcopy(C['settings'])
            settings[field]={'A':-1} if field=='balances_by_account' else -0.1
            self.assertTrue(self.check(scenario('B'),settings=settings)['errors'])

    def test_negative_cash_and_taxes_are_invalid(self):
        for value in (-1,'100',True,float('nan'),float('inf')):
            for field in ('cash','tax'):
                with self.subTest(value=value,field=field):
                    o=scenario('C')
                    if field=='cash': o['cash_items'][0]['hkd_per_person']=value
                    else: o['taxes_and_surcharges_hkd_per_person']=value
                    r=self.check(o); self.assertTrue(r['errors']); self.assertIsNone(r['valued_miles_plus_known_cash_hkd'])

    def test_oneworld_invalid_distance_and_counts(self):
        for value in (0,-1,None,'16000',True,float('nan')):
            with self.subTest(value=value):
                o=scenario('B'); o['award_tickets'][0]['total_flight_distance_mi']=value
                self.assertTrue(self.check(o)['errors'])
        for field in ('stopovers','transfers','open_jaws'):
            for value in (-1,'2',1.5):
                o=scenario('B'); o['award_tickets'][0][field]=value
                self.assertTrue(self.check(o)['errors'])

    def test_rules_dynamic_carrier_count_with_cx(self):
        r=copy.deepcopy(R); r['oneworld_constraints']['carrier_count_if_CX_included']=4
        self.assertTrue(self.check(scenario('B'),rules=r)['errors'])
        r['oneworld_constraints']['carrier_count_if_CX_included']=3
        self.assertFalse(self.check(scenario('B'),rules=r)['errors'])

    def test_rules_dynamic_carrier_count_without_cx(self):
        o=scenario('B')
        for trip in o['trips']:
            for leg in trip['legs']:
                if leg.get('airline')=='CX': leg['airline']='QR'
        r=copy.deepcopy(R); r['oneworld_constraints']['carrier_count_if_no_CX']=3
        self.assertTrue(self.check(o,rules=r)['errors'])
        r['oneworld_constraints']['carrier_count_if_no_CX']=2
        self.assertFalse(self.check(o,rules=r)['errors'])

    def test_rules_dynamic_stopover_transfer_openjaw_limits(self):
        for field,limit in [('stopovers','max_stopovers'),('transfers','max_transfers'),('open_jaws','max_open_jaws')]:
            with self.subTest(field=field):
                o=scenario('B'); o['award_tickets'][0][field]=3
                r=copy.deepcopy(R); r['oneworld_constraints'][limit]=3
                self.assertFalse(self.check(o,rules=r)['errors'])
                r['oneworld_constraints'][limit]=2
                self.assertTrue(self.check(o,rules=r)['errors'])

    def test_rules_dynamic_max_flight_miles(self):
        r=copy.deepcopy(R); r['oneworld_constraints']['max_flight_miles']=16000
        self.assertTrue(self.check(scenario('B'),rules=r)['errors'])
        r['oneworld_constraints']['max_flight_miles']=17000
        self.assertFalse(self.check(scenario('B'),rules=r)['errors'])
        self.assertEqual(self.check(scenario('B'),rules=r)['ticket_details'][0]['distance_headroom_mi'],314)

    def test_rules_dynamic_pe_and_price_band(self):
        o=scenario('B')
        for trip in o['trips']:
            for leg in trip['legs']:
                if leg.get('payment')=='award': leg['cabin']='W'
        self.assertTrue(self.check(o)['errors'])
        r=copy.deepcopy(R); r['oneworld_constraints']['premium_economy_offered']=True
        # A changed policy alone must not invent a missing price.
        self.assertTrue(self.check(o,rules=r)['errors'])
        for band in r['oneworld_bands']: band['miles']['W']=123456
        result=self.check(o,rules=r)
        self.assertFalse(result['errors']); self.assertEqual(result['per_person_miles'],123456)

    def test_rules_highest_cabin_disabled_fails_closed(self):
        r=copy.deepcopy(R); r['oneworld_constraints']['whole_ticket_highest_cabin_pricing']=False
        self.assertTrue(any('替代混舱算法' in e for e in self.check(scenario('I'),rules=r)['errors']))
        self.assertFalse(self.check(scenario('B'),rules=r)['errors'])

    def test_rules_dynamic_allowed_carriers_and_warning(self):
        r=copy.deepcopy(R); r['oneworld_constraints']['allowed_carriers'].remove('JL')
        self.assertTrue(self.check(scenario('B'),rules=r)['errors'])
        r=copy.deepcopy(R); r['oneworld_constraints']['distance_warning_headroom_mi']=2000
        self.assertTrue(any('跳档' in w for w in self.check(scenario('B'),rules=r)['warnings']))

    def test_rules_dynamic_mixed_transfer_and_rounding(self):
        r=copy.deepcopy(R); r['standard_mixed_constraints']['max_transfer_hours']=1
        self.assertTrue(self.check(scenario('M'),rules=r)['errors'])
        r['standard_mixed_constraints']['max_transfer_hours']=2
        r['standard_mixed_constraints']['round_down_increment']=1000
        result=self.check(scenario('M'),rules=r)
        self.assertFalse(result['errors']); self.assertEqual(result['per_person_miles'],2*83000)

    def quoted_cash(self):
        o=scenario('C'); o['cash_items'][0]['quote_type']='quoted'; o['taxes_quote_type']='quoted'
        return o

    def test_complete_cash_cost_does_not_require_award_seats(self):
        r=self.check(self.quoted_cash())
        self.assertEqual(r['cost_status'],'COMPLETE_QUOTED')
        self.assertTrue(r['complete_price_comparison_eligible'])
        self.assertFalse(r['missing_cost_components']); self.assertFalse(r['assumed_cost_components'])

    def test_partial_assumption_and_unlabelled_cost_status(self):
        o=self.quoted_cash(); o['taxes_and_surcharges_hkd_per_person']=None
        r=self.check(o); self.assertEqual(r['cost_status'],'PARTIAL_LOWER_BOUND')
        self.assertFalse(r['complete_price_comparison_eligible']); self.assertTrue(r['missing_cost_components'])
        o['cash_items'][0]['quote_type']='assumption'
        self.assertEqual(self.check(o)['cost_status'],'PARTIAL_ASSUMPTION')
        o['taxes_and_surcharges_hkd_per_person']=0
        self.assertEqual(self.check(o)['cost_status'],'ASSUMPTION')
        del o['cash_items'][0]['quote_type']
        self.assertFalse(self.check(o)['complete_price_comparison_eligible'])

    def test_unpriced_cash_leg_cannot_look_complete(self):
        o=self.quoted_cash(); o['cash_items']=[]
        r=self.check(o); self.assertEqual(r['cost_status'],'PARTIAL_LOWER_BOUND')
        self.assertFalse(r['complete_price_comparison_eligible'])

    def test_sort_preserves_partial_order_and_groups_cabins(self):
        expensive=self.quoted_cash(); expensive['id']='expensive'; expensive['cash_items'][0]['hkd_per_person']=9000
        cheap=self.quoted_cash(); cheap['id']='cheap'
        partial=scenario('C'); partial['id']='partial'; partial['cash_items'][0]['hkd_per_person']=1
        partial2=scenario('C'); partial2['id']='partial2'; partial2['cash_items'][0]['hkd_per_person']=0
        invalid=scenario('C'); invalid['id']='invalid'; invalid['trips']=[]
        rows=sort_results([self.check(o) for o in [invalid,partial,expensive,partial2,cheap]])
        self.assertEqual([r['id'] for r in rows],['cheap','expensive','partial','partial2','invalid'])
        other=self.check(scenario('A')); rows=sort_results(rows+[other])
        self.assertEqual(rows[-1]['id'],'invalid')
        self.assertEqual(other['category'],'full_business')

    def test_missing_balance_explicitly_not_checked(self):
        settings=copy.deepcopy(C['settings']); settings['balances_by_account']={}
        self.assertEqual(self.check(scenario('B'),settings=settings)['account_allocation_status'],'NOT_CHECKED')

    def test_latest_rules_selection(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            for name in ('rules_2026_10.json','rules_2027_01.json'): (base/name).write_text('{}')
            self.assertEqual(latest_rules(base).name,'rules_2027_01.json')

    def test_cli_json_csv_and_invalid_exit(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); output=base/'result.json'; csvpath=base/'result.csv'
            command=[sys.executable,'-B',str(P/'optimizer.py'),'--output',str(output),'--csv',str(csvpath)]
            completed=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            data=json.loads(output.read_text()); self.assertEqual(data['metadata']['version'],'1.1')
            self.assertEqual(len(data['results']),len(C['scenarios']))
            self.assertTrue(all(not r['complete_price_comparison_eligible'] for r in data['results']))
            with csvpath.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
            self.assertIn('complete_price_comparison_eligible',rows[0])
            invalid=copy.deepcopy(C); invalid['scenarios'][0]['trips']=[]
            inputpath=base/'invalid.json'; inputpath.write_text(json.dumps(invalid))
            completed=subprocess.run(command+['--input',str(inputpath)],capture_output=True,text=True)
            self.assertEqual(completed.returncode,1,completed.stderr)
            self.assertEqual(json.loads(output.read_text())['results'][-1]['cost_status'],'INVALID')


if __name__=='__main__': unittest.main()
