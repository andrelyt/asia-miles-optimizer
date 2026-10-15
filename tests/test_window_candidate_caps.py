"""Review regression: concrete windows get separate candidate caps. SYNTHETIC TEST only."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from planner import plan
from discovery._validation import ValidationError
from discovery.award_pricing import price_candidate
from discovery.candidate_generator import generate_candidates
from discovery.holiday_calendar import load_calendars
from discovery.leave_engine import generate_windows
from discovery.portfolio import optimize_portfolios, portfolio_config
from discovery.route_graph import load_route_graph
from tests._award_fixtures import evidence, bound

ROOT = Path(__file__).resolve().parents[1]


class WindowCandidateCapTests(unittest.TestCase):
    def setUp(self):
        self.input = json.loads((ROOT/'examples/planner_synthetic_test.json').read_text())
        self.rules = json.loads((ROOT/'rules_2026_10.json').read_text())
        self.req = self.input['request']; self.req['holiday_types'] = ['new_year','qingming']; self.req['max_trips'] = 2
        for t in self.req['travelers']: t['annual_leave_budget'] = 1
        self.req['leave_constraints'].update(min_calendar_trip_days=2,max_calendar_trip_days=3)
        self.input['search_config']['holiday_window'].update(days_before=1,days_after=2,max_generated_windows_per_holiday=30)
        self.input['portfolio_config'].update(max_candidates_per_window=1,max_candidates_total=3,max_per_view=5)
        self.cal = load_calendars(self.input['calendars'])
        actual = generate_windows(self.cal,self.req,self.input['search_config'])
        def window(start,end):
            return next(w for w in actual['windows'] if w['start_date']==start and w['end_date']==end)
        self.early=window('2027-04-01','2027-04-02')
        self.late=window('2027-04-02','2027-04-04')
        self.other=window('2027-01-01','2027-01-03')
        self.windows=[self.early,self.late,self.other]
        graph=load_route_graph(self.input['route_graph'])
        def candidates(w):
            return sorted(generate_candidates(graph,self.req,self.rules,window=w,config=self.input['search_config'])['candidates'],
                          key=lambda c:c['candidate_id'])
        # Use actual valid PR2 IDs, never fake or mutate identity hashes. Deliberately
        # adversarial: every early-window ID precedes every later-window ID.
        self.by_window={self.early['window_id']:candidates(self.early)[:2],
                        self.late['window_id']:candidates(self.late)[-2:],
                        self.other['window_id']:candidates(self.other)[:1]}
        self.assertLess(max(c['candidate_id'] for c in self.by_window[self.early['window_id']]),
                        min(c['candidate_id'] for c in self.by_window[self.late['window_id']]))
        self.input['evidence_by_candidate']={}
        for values in self.by_window.values():
            for c in values:
                ev=evidence(c,self.req,self.rules,quote_miles=1000)
                ev['tax_quote']=dict(bound(c,self.rules,'AIRLINE_QUOTED'),hkd_per_person=100)
                self.input['evidence_by_candidate'][c['candidate_id']]=ev

    def generated(self,*args,**kw):
        return {'candidates':copy.deepcopy(self.by_window[kw['window']['window_id']]),'diagnostics':[]}

    def run_plan(self):
        # Only narrow upstream *selection* to deterministic genuine PR1/PR2 data.
        # Real PR3 pricing, annual budgets, portfolio search and views all execute.
        with patch('planner.generate_windows',return_value={'windows':self.windows,'diagnostics':[]}), \
             patch('planner.generate_candidates',side_effect=self.generated):
            return plan(self.input,ROOT/'examples')

    def priced(self):
        return [price_candidate(c,self.req,self.rules,self.input['evidence_by_candidate'][c['candidate_id']])
                for values in self.by_window.values() for c in values]

    def test_cli_cap_is_per_window_even_with_adversarial_id_order(self):
        self.input['portfolio_config']['max_candidates_total']=10
        result=self.run_plan()
        retained={p['candidate']['holiday_window']['window_id'] for p in result['trips']}
        self.assertEqual(retained,{w['window_id'] for w in self.windows})
        self.assertEqual(len(result['trips']),3)
        counts=result['diagnostics']['orchestration_candidate_counts_by_window']
        self.assertEqual(counts[self.early['window_id']],{'before_window_cap':2,'after_window_cap':1,'after_global_cap':1})
        self.assertEqual(counts[self.late['window_id']],{'before_window_cap':2,'after_window_cap':1,'after_global_cap':1})
        self.assertTrue(result['search_truncated'])

    def test_later_zero_leave_window_enables_annual_two_trip_portfolio_and_views(self):
        self.assertEqual(set(self.early['leave_days_by_traveler'].values()),{1})
        self.assertEqual(set(self.late['leave_days_by_traveler'].values()),{0})
        result=self.run_plan()
        later_ids={c['candidate_id'] for c in self.by_window[self.late['window_id']]}
        early_ids={c['candidate_id'] for c in self.by_window[self.early['window_id']]}
        full=[r for r in result['budget_feasible'] if r['trip_count']==2]
        self.assertTrue(full)
        self.assertTrue(all(later_ids.intersection(r['candidate_ids']) for r in full))
        self.assertTrue(all(not early_ids.intersection(r['candidate_ids']) for r in full))
        for r in full:
            self.assertEqual(r['leave_days_by_traveler_by_year'],{'traveler_a':{'2027':1},'traveler_b':{'2027':1}})
        full_ids={r['portfolio_id'] for r in full}
        self.assertTrue(full_ids.intersection(result['views']['Leave Efficient']['budget_feasible']))
        self.assertTrue(full_ids.intersection(result['views']['Balanced']['budget_feasible']))

    def test_real_upstream_multiple_windows_preserve_low_leave_portfolio(self):
        result=plan(self.input,ROOT/'examples')
        later_ids={c['candidate_id'] for c in self.by_window[self.late['window_id']]}
        full=[r for r in result['budget_feasible'] if r['trip_count']==2]
        self.assertTrue(full)
        self.assertTrue(any(later_ids.intersection(r['candidate_ids']) for r in full))
        self.assertTrue({r['portfolio_id'] for r in full}.intersection(result['views']['Leave Efficient']['budget_feasible']))
        self.assertGreater(result['diagnostics']['windows_searched'],3)
        self.assertLessEqual(len(result['trips']),3)

    def test_direct_portfolio_api_does_not_recap_by_holiday_anchor(self):
        result=optimize_portfolios(self.priced(),self.req,self.cal,self.rules,self.input['balances_by_account'],
                                  self.input['funding_eligibility'],self.input['portfolio_config'])
        self.assertEqual({p['candidate']['holiday_window']['window_id'] for p in result['trips']},
                         {w['window_id'] for w in self.windows})
        self.assertTrue(any(r['trip_count']==2 for r in result['budget_feasible']))
        self.assertTrue(all(v['after_window_cap']==1 for v in result['diagnostics']['candidate_counts_by_window'].values()))

    def test_global_cap_after_window_cap_is_bounded_and_round_robins_windows(self):
        # Two candidates per window, three global slots: still one per window,
        # including both windows belonging to the same family.
        self.input['portfolio_config'].update(max_candidates_per_window=2,max_candidates_total=3)
        result=self.run_plan()
        self.assertEqual(len(result['trips']),3)
        self.assertEqual(len({p['candidate']['holiday_window']['window_id'] for p in result['trips']}),3)
        self.assertTrue(result['search_truncated'])
        self.input['portfolio_config']['max_candidates_total']=2
        smaller=self.run_plan()
        self.assertEqual(len(smaller['trips']),2)
        self.assertEqual(len({p['candidate']['holiday_window']['window_id'] for p in smaller['trips']}),2)
        self.assertTrue(smaller['search_truncated'])

    def test_direct_global_cap_also_round_robins_windows(self):
        cfg=dict(self.input['portfolio_config'],max_candidates_per_window=2,max_candidates_total=3)
        result=optimize_portfolios(self.priced(),self.req,self.cal,self.rules,self.input['balances_by_account'],
                                  self.input['funding_eligibility'],cfg)
        self.assertEqual(len({p['candidate']['holiday_window']['window_id'] for p in result['trips']}),3)
        self.assertTrue(result['search_truncated'])

    def test_permutations_keep_ids_order_and_counts_stable(self):
        first=self.run_plan()
        self.windows.reverse();self.req['travelers'].reverse()
        self.input['funding_eligibility'].reverse()
        for group in self.by_window.values():group.reverse()
        self.assertEqual(first,self.run_plan())
        rows=self.priced();forward=optimize_portfolios(rows,self.req,self.cal,self.rules,
             self.input['balances_by_account'],self.input['funding_eligibility'],self.input['portfolio_config'])
        reverse=optimize_portfolios(list(reversed(rows)),self.req,self.cal,self.rules,
             self.input['balances_by_account'],self.input['funding_eligibility'],self.input['portfolio_config'])
        self.assertEqual(forward,reverse)

    def test_no_truncation_when_each_window_and_global_capacity_are_sufficient(self):
        self.input['portfolio_config'].update(max_candidates_per_window=2,max_candidates_total=5)
        result=self.run_plan()
        self.assertEqual(len(result['trips']),5)
        self.assertFalse(result['search_truncated'])
        self.assertTrue(all(v['before_window_cap']==v['after_window_cap']==v['after_global_cap']
            for v in result['diagnostics']['orchestration_candidate_counts_by_window'].values()))

    def test_dated_window_without_identity_is_rejected_not_pooled_with_another_window(self):
        from tests._award_fixtures import reidentify
        c=copy.deepcopy(self.by_window[self.late['window_id']][0])
        del c['holiday_window']['window_id'];reidentify(c)
        row=price_candidate(c,self.req,self.rules,evidence(c,self.req,self.rules))
        result=optimize_portfolios([row],self.req,self.cal,self.rules,self.input['balances_by_account'],
                                  self.input['funding_eligibility'],self.input['portfolio_config'])
        self.assertFalse(result['trips'])
        self.assertEqual(result['rejected']['WINDOW_ID_REQUIRED'],1)

    def test_obsolete_family_cap_rejected_with_explicit_migration_message(self):
        with self.assertRaisesRegex(ValidationError,'use max_candidates_per_window'):
            portfolio_config({'max_candidates_per_holiday':1})
        self.assertEqual(portfolio_config()['max_candidates_per_window'],10)


if __name__=='__main__':unittest.main()
