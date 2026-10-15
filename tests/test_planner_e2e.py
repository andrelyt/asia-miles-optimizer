"""Offline planner contract and real CLI replay with synthetic TEST data only."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from planner import plan
from discovery._validation import ValidationError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/planner_synthetic_test.json'


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.input = json.loads(EXAMPLE.read_text())

    def run_plan(self, data=None):
        return plan(self.input if data is None else data, EXAMPLE.parent)

    def test_real_pr1_pr2_pr3_pr4_synthetic_flow(self):
        result = self.run_plan()
        self.assertTrue(result['budget_feasible']); self.assertTrue(result['conditional'])
        self.assertTrue(any(r['trip_count'] == 3 for r in result['budget_feasible']))
        self.assertEqual(set(result['views']), {'Miles Saver','Comfort First','Balanced','Leave Efficient'})
        self.assertTrue(result['input_snapshots']['data_label'].startswith('SYNTHETIC_TEST'))
        for row in result['budget_feasible']:
            self.assertEqual(row['evidence']['holiday_status'], ['ESTIMATED'])
            self.assertEqual(row['evidence']['route_status'], ['STALE'])
            self.assertEqual(row['evidence']['award_seat_status'], ['NOT_CHECKED'])
            self.assertEqual(row['evidence']['ticketability_status'], ['NOT_CHECKED'])
            self.assertEqual(row['funding_eligibility_status'], 'NOT_CHECKED')
            self.assertTrue(all(v <= self.input['balances_by_account'][a] for a,v in row['account_spend_miles'].items()))
        self.assertTrue(any('RULE_VERSION_REVIEW_REQUIRED' in r['missing_data'] for r in result['conditional']))

    def test_real_cli_writes_deterministic_json_and_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs=[]
            for n in (1,2):
                out=Path(tmp)/f'TEST_{n}.json'
                process=subprocess.run([sys.executable,'-B',str(ROOT/'planner.py'),'--input',str(EXAMPLE),'--output',str(out)],
                                       capture_output=True,text=True)
                self.assertEqual(process.returncode,0,process.stderr)
                outputs.append(out.read_bytes())
            self.assertEqual(outputs[0],outputs[1])
            self.assertEqual(json.loads(outputs[0]),self.run_plan())

    def test_cli_stdout_and_invalid_input_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad=Path(tmp)/'TEST_bad.json';bad.write_text('{"request":{}}')
            process=subprocess.run([sys.executable,'-B',str(ROOT/'planner.py'),'--input',str(bad)],capture_output=True,text=True)
            self.assertNotEqual(process.returncode,0)
            self.assertEqual(json.loads(process.stderr)['status'],'INVALID_INPUT')
            # Small no-route example exercises structured stdout without output file.
            source=copy.deepcopy(self.input);source['route_graph']['edges']=[]
            source['rules']=str(ROOT/'rules_2026_10.json')
            good=Path(tmp)/'TEST_empty.json';good.write_text(json.dumps(source))
            process=subprocess.run([sys.executable,'-B',str(ROOT/'planner.py'),'--input',str(good)],capture_output=True,text=True)
            self.assertEqual(process.returncode,0,process.stderr)
            self.assertEqual(json.loads(process.stdout)['budget_feasible'],[])

    def test_unknown_accounts_and_missing_quotes_are_conditional(self):
        self.input.pop('balances_by_account');self.input.pop('evidence_by_candidate')
        result=self.run_plan()
        self.assertFalse(result['budget_feasible']);self.assertTrue(result['conditional'])
        self.assertTrue(all(r['total_miles'] is None for r in result['conditional']))
        self.assertTrue(all(r['account_spend_miles'] is None for r in result['conditional']))
        self.assertTrue(all('PAYMENT_ACCOUNT_BALANCES_REQUIRED' in r['missing_data'] for r in result['conditional']))

    def test_partial_account_snapshots_do_not_become_budget_feasible(self):
        self.input['balances_by_account']['TEST_PAYER_B']=None
        result=self.run_plan()
        self.assertFalse(result['budget_feasible'])
        self.assertTrue(result['conditional'])
        self.assertTrue(all(r['account_allocation_status']=='NOT_CHECKED' for r in result['conditional']))

    def test_unconfirmed_funding_can_never_be_reported_budget_feasible(self):
        self.input.pop('funding_eligibility')
        result=self.run_plan()
        self.assertFalse(result['budget_feasible'])
        self.assertTrue(any(r['account_allocation_status']=='FEASIBLE' for r in result['conditional']))

    def test_calendar_route_request_evidence_permutations_are_stable(self):
        one=self.run_plan()
        self.input['calendars'].reverse();self.input['route_graph']['edges'].reverse()
        self.input['request']['travelers'].reverse();self.input['request']['holiday_types'].reverse()
        for edge in self.input['route_graph']['edges']: edge['cabins'].reverse()
        self.input['funding_eligibility'].reverse()
        two=self.run_plan()
        # Raw route digest intentionally reflects the supplied snapshot ordering;
        # compare normalized substantive output and stable portfolio IDs.
        one['input_snapshots'].pop('route_digest');two['input_snapshots'].pop('route_digest')
        self.assertEqual(one,two)

    def test_caps_report_truncation_for_windows_candidates_and_states(self):
        self.input['portfolio_config'].update(max_windows=1,max_states=2,max_candidates_total=2)
        result=self.run_plan()
        self.assertTrue(result['search_truncated'])
        self.assertLessEqual(result['diagnostics']['windows_searched'],1)
        self.assertLessEqual(result['diagnostics']['portfolio_states_visited'],2)
        self.assertLessEqual(len(result['trips']),2)

    def test_paths_and_inline_objects_use_same_interfaces(self):
        inline=self.run_plan()
        with tempfile.TemporaryDirectory() as tmp:
            source=copy.deepcopy(self.input);source['rules']=str(ROOT/'rules_2026_10.json')
            for key in ('request','route_graph','calendars','evidence_by_candidate','funding_eligibility','balances_by_account'):
                path=Path(tmp)/(key+'.json');path.write_text(json.dumps(source[key]));source[key]=path.name
            result=plan(source,tmp)
            self.assertEqual(inline,result)

    def test_invalid_config_accounts_unknown_keys_and_budget_types(self):
        for key,value in [('portfolio_config',{'max_states':False}),('balances_by_account',{'TEST':-1}),
                          ('portfolio_config',{'leave_budgets_by_year':{'2027':{'traveler_a':1}}})]:
            supplied=copy.deepcopy(self.input);supplied[key]=value
            with self.assertRaises((ValueError,TypeError)): self.run_plan(supplied)
        self.input['invented_input']=True
        with self.assertRaises(ValidationError):self.run_plan()

    def test_runtime_never_creates_quote_or_applicability_evidence(self):
        self.input.pop('evidence_by_candidate')
        result=self.run_plan()
        self.assertTrue(all(row['pricing_status']=='UNKNOWN' for row in result['trips']))
        self.assertTrue(all(row['input_evidence']=={} for row in result['trips']))

    def test_no_mutation_and_bounded_global_funding(self):
        original=copy.deepcopy(self.input)
        self.run_plan()
        self.assertEqual(original,self.input)
        self.input['portfolio_config']['max_allocation_states']=2
        result=self.run_plan()
        self.assertTrue(result['search_truncated'])
        self.assertLessEqual(result['diagnostics']['allocation_states_visited'],2)
        self.assertFalse(result['budget_feasible'])


if __name__=='__main__': unittest.main()
