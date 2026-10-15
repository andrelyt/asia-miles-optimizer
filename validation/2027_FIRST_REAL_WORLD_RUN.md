# 2027 First Real-world Validation Run

**CONDITIONAL VALIDATION OUTPUT · NOT AWARD AVAILABILITY · NOT BOOKABLE · NO LIVE SEAT CHECK**

Observation-only execution on 2026-10-15. No code, rules, schemas, input, quotes or evidence were changed. This report records a bounded planning run, not a bookable itinerary.

## Environment and execution

- GitHub main execution HEAD: `ce926bc9c0c95fdc6514b41f146ba1d3d7aec333`.
- Python: `3.9.6`.
- Worktree clean before and after updating main (initial branch was the prior PR4 branch; execution used main only).
- Full suite: **258 passed / 0 failed / 0 errors / 258 total**, exit 0; 2.655 seconds. No failing tracebacks.

```bash
python3 -B -m unittest discover -p 'test_*.py' -v
python3 -B planner.py \
  --input validation/2027_conditional_planner_input.json \
  --output /tmp/2027_conditional_result.json
```

- Planner exit code: **0**. stdout: empty. stderr: empty.
- Original output SHA256: `6e64cfe49a850125cb4c1bd15d009fc6e93a46a2fd2e45f92322b24d142bdfce`.

## Input evidence summary

- Request: 2027; andre / dony; annual leave 15 / 13; HKG; labor_day + national_day; AKL / ZRH / CTS / SYD; max_trips 2; longhaul minimum W, preferred J. All requested fields match.
- `travelers[].miles_balance=0` is an existing schema placeholder, not a verified funding account. `balances_by_account=null`; no real balances were supplied or inferred.
- Calendar: two ESTIMATED anchors only (May 1 and October 1), source_url null; ordinary weekday/weekend fallback remains ESTIMATED. No official 2027 substitution or makeup-workday schedule is known. Leave counts below are conditional planning estimates.
- Routes: 8 directed CX research edges, all UNVERIFIED. Distances are explicitly APPROXIMATE_GREAT_CIRCLE_RESEARCH_VALUE_NOT_CATHAY_TICKETED_MILEAGE. Sources are research provenance, not a verified 2027 schedule, flight-specific cabin inventory, reward-seat evidence or ticketability.
- evidence_by_candidate empty; no airline award/tax quote, no seat evidence, no applicability review, no confirmed funding eligibility, no verified account snapshot.

Input SHA256 (unchanged tracked files):

- `validation/2027_calendar_estimated_anchors_only.json`: `813c1bc5d94aa9b1e69a3d52e3b87ea2813e234fc05d426633772f308e00b10a`.
- `validation/2027_conditional_planner_input.json`: `6820386f2ed610c2aa4fd93dca4788ccdee08c7f55b23f59b0cba3cf90580c18`.
- `validation/2027_hkg_four_dest_route_graph_unverified.json`: `bed3c5b830c5378e56d50d0a4c3cad52321a5f8aee65a870bfa582d138462045`.
- `validation/2027_travel_request.json`: `7a0f2e3409761bb22a4acdd192d59694439146c988e2ba75b678354d38b229d5`.

## Holiday windows

PR1 feasible before Pareto pruning: labor_day 43, national_day 43. Returned and searched: labor_day **8**, national_day **16**, total **24**. max_windows=30 did not truncate windows. All 24 concrete windows survived candidate caps with at least 4 candidates.

| Holiday | Window ID | Start | End | Calendar days | andre leave | dony leave | Evidence |
|---|---|---|---|---:|---:|---:|---|
| labor_day | window_515ac928a7a50ff1e710027e | 2027-04-24 | 2027-05-01 | 8 | 5 | 5 | ESTIMATED |
| labor_day | window_db76a341444399146036e378 | 2027-04-24 | 2027-05-02 | 9 | 5 | 5 | ESTIMATED |
| labor_day | window_8d9888ed1d218d034a6e05d6 | 2027-04-24 | 2027-05-03 | 10 | 6 | 6 | ESTIMATED |
| labor_day | window_27cf3879cea04f459330a5a9 | 2027-04-24 | 2027-05-04 | 11 | 7 | 7 | ESTIMATED |
| labor_day | window_c71c29f6bba69062c8f4b8d2 | 2027-04-24 | 2027-05-05 | 12 | 8 | 8 | ESTIMATED |
| labor_day | window_ad49e1ad530d1e5b60eb91ac | 2027-04-24 | 2027-05-06 | 13 | 9 | 9 | ESTIMATED |
| labor_day | window_b59c2141fc00cc01a4d8e760 | 2027-04-24 | 2027-05-08 | 15 | 10 | 10 | ESTIMATED |
| labor_day | window_6d12c749fa71ebe5f722a580 | 2027-05-01 | 2027-05-08 | 8 | 5 | 5 | ESTIMATED |
| national_day | window_b4751150bd8eaacaec5f7e91 | 2027-09-24 | 2027-10-01 | 8 | 5 | 5 | ESTIMATED |
| national_day | window_9f902a5d2991462cbfd2d913 | 2027-09-24 | 2027-10-03 | 10 | 5 | 5 | ESTIMATED |
| national_day | window_307e775c00875bcdad34edbb | 2027-09-24 | 2027-10-04 | 11 | 6 | 6 | ESTIMATED |
| national_day | window_9852aa1c99ea82c60d1c4977 | 2027-09-24 | 2027-10-05 | 12 | 7 | 7 | ESTIMATED |
| national_day | window_07585bf3488a180fbdea0f5e | 2027-09-24 | 2027-10-06 | 13 | 8 | 8 | ESTIMATED |
| national_day | window_10856f690b1e4d20a0144a09 | 2027-09-24 | 2027-10-07 | 14 | 9 | 9 | ESTIMATED |
| national_day | window_93de36af95b1fd375d72d10c | 2027-09-24 | 2027-10-08 | 15 | 10 | 10 | ESTIMATED |
| national_day | window_705051653986e2ab4cefb41e | 2027-09-25 | 2027-10-01 | 7 | 4 | 4 | ESTIMATED |
| national_day | window_4c25bd166386ea7d17d1cd72 | 2027-09-25 | 2027-10-03 | 9 | 4 | 4 | ESTIMATED |
| national_day | window_30c226d4b3f862c435df351d | 2027-09-25 | 2027-10-04 | 10 | 5 | 5 | ESTIMATED |
| national_day | window_2573ae3cbb3450378deaa081 | 2027-09-25 | 2027-10-05 | 11 | 6 | 6 | ESTIMATED |
| national_day | window_5fe307a3e59f06c594f23d87 | 2027-09-25 | 2027-10-06 | 12 | 7 | 7 | ESTIMATED |
| national_day | window_269e2010451149b105f17b66 | 2027-09-25 | 2027-10-07 | 13 | 8 | 8 | ESTIMATED |
| national_day | window_bd1dea94d70ce06d4e706025 | 2027-09-25 | 2027-10-08 | 14 | 9 | 9 | ESTIMATED |
| national_day | window_86fd253ac6f7f0f7f724d601 | 2027-10-01 | 2027-10-07 | 7 | 4 | 4 | ESTIMATED |
| national_day | window_b249e9ada014139bd24311f3 | 2027-10-01 | 2027-10-08 | 8 | 5 | 5 | ESTIMATED |

## Candidate generation

Read-only diagnostic replay used the identical supplied snapshots/configuration and the existing PR1/PR2 functions, with no modified inputs or relaxed caps, to count intermediate candidates not serialized by the CLI. Counts reconciled with orchestration diagnostics. PR2 strategy aliases are deduplicated; counts below are unique candidate structures.

| Destination | Before PR4 caps | After per-window cap | After global cap / PR3 | Final cabin structures (out/return) |
|---|---:|---:|---:|---|
| AKL | 96 | 55 | 23 | `{"J/J": 3, "J/W": 9, "W/J": 5, "W/W": 6}` |
| ZRH | 96 | 56 | 21 | `{"J/J": 5, "J/W": 9, "W/J": 3, "W/W": 4}` |
| CTS | 120 | 80 | 32 | `{"J/J": 8, "J/W": 5, "W/J": 7, "W/W": 6, "Y/Y": 6}` |
| SYD | 96 | 49 | 24 | `{"J/J": 5, "J/W": 3, "W/J": 5, "W/W": 11}` |

- Total candidate pipeline: **408 → 240 → 100**. Every window had 17 → 10 → 4 or 5. The inner PR4 diagnostic sees already-capped input (100), whereas orchestration diagnostics retain the true 408 pre-cap count.
- All raw and retained routes are direct outbound + direct return; no separate-award structures were generated. SINGLE_AWARD denotes an award structure per direction, not one priced roundtrip ticket. Asymmetric J/W and W/J structures remain present. Cabin quantities after both intermediate caps are recorded below.

- Before caps: `{"AKL": {"J/J": 24, "J/W": 24, "W/J": 24, "W/W": 24}, "CTS": {"J/J": 24, "J/W": 24, "W/J": 24, "W/W": 24, "Y/Y": 24}, "SYD": {"J/J": 24, "J/W": 24, "W/J": 24, "W/W": 24}, "ZRH": {"J/J": 24, "J/W": 24, "W/J": 24, "W/W": 24}}`.
- After window cap: `{"AKL": {"J/J": 10, "J/W": 15, "W/J": 14, "W/W": 16}, "CTS": {"J/J": 18, "J/W": 13, "W/J": 15, "W/W": 10, "Y/Y": 24}, "SYD": {"J/J": 9, "J/W": 12, "W/J": 12, "W/W": 16}, "ZRH": {"J/J": 17, "J/W": 14, "W/J": 10, "W/W": 15}}`.
- After global cap: `{"AKL": {"J/J": 3, "J/W": 9, "W/J": 5, "W/W": 6}, "CTS": {"J/J": 8, "J/W": 5, "W/J": 7, "W/W": 6, "Y/Y": 6}, "SYD": {"J/J": 5, "J/W": 3, "W/J": 5, "W/W": 11}, "ZRH": {"J/J": 5, "J/W": 9, "W/J": 3, "W/W": 4}}`.

- All 100 retained route_status values are UNVERIFIED; all 200 retained legs preserve the research-distance provenance. Longhaul Y-only candidates are excluded by W minimum; CTS shorthaul Y/Y is permitted.
- Window start/end dates are generation assumptions only. Schedule, overnight arrival, timezone/local dates and destination full days remain NOT_CHECKED/unknown.

## PR3 pricing outcomes

| Status | Count |
|---|---:|
| EVALUATED | 0 |
| NEEDS_DATA | 0 |
| NEEDS_AIRLINE_QUOTE | 0 |
| RULE_VERSION_REVIEW_REQUIRED | 100 |
| UNSUPPORTED | 0 |

All 100 pricing_status=UNKNOWN; per_person_miles and group_miles=null; v1_evaluated=false; kernel_result=null. Rule applicability review is the first gate, so missing quotes do not appear as NEEDS_AIRLINE_QUOTE yet. There are still no quotes. Known subtotal=0 means no priced component, not a zero-priced award. Taxes remain null; complete_price_comparison_eligible=false for every trip and portfolio.

## PR4 portfolios and search

- Returned portfolios: **1300**; conditional Pareto front: **1300**; budget-feasible Pareto front: **0**. PARETO_DOMINATED=0 because unknown prices prevent strict dominance inference.
- Rejections: `{"ANNUAL_LEAVE_BUDGET_EXCEEDED": 1027, "PARETO_DOMINATED": 0, "SAME_HOLIDAY_ALTERNATIVE": 2673}`; total **3700** rejected search states (not 3700 distinct routes).
- search_truncated=**true**; portfolio_states_visited=**5000** (configured cap); allocation_states_visited=**0**. Candidate caps also truncated search. No global optimum is established.
- Returned trip-count distribution: `{"1": 100, "2": 1200}`.
- Every returned portfolio is leave-feasible under the ESTIMATED calendar; annual per-traveler dates were independently checked against 2027 budgets 15 / 13. No account allocation was attempted, no pooling occurred, and unknown account capacity is not true mileage-budget infeasibility.

## Recommendation views

All budget_feasible lists are empty. These are conditional research leads, not price-comparable recommendations. Miles Saver has no mileage information to establish savings; its IDs are a deterministic conditional ordering, not evidence of cheapest cost.

### Miles Saver

- Ordering: Mileage only within price classes; never total-cost ranking
- budget_feasible: `[]`
- conditional portfolio IDs:

  - `portfolio_0017c47dba5c0c6b2c730d78`
  - `portfolio_001ab767671420451fa40205`
  - `portfolio_0033b3f051912cb2c2ff683e`
  - `portfolio_01ff3b4e0551b75c3c9a6136`
  - `portfolio_00a9b21be46f62bbc49de05e`

### Comfort First

- Ordering: Mean longhaul ordinal cabin rank, then trips
- budget_feasible: `[]`
- conditional portfolio IDs:

  - `portfolio_04894c2041993737d7366a3c`
  - `portfolio_10519c9e7f163efb6fe50efb`
  - `portfolio_0e7e67606ceb77bf6809b92c`
  - `portfolio_40c605a388e5a5d1dd917153`
  - `portfolio_018fb75bb008f20c9c0737a3`

### Balanced

- Ordering: Nondominated diversity; no weighted score
- budget_feasible: `[]`
- conditional portfolio IDs:

  - `portfolio_0017c47dba5c0c6b2c730d78`
  - `portfolio_001ab767671420451fa40205`
  - `portfolio_0033b3f051912cb2c2ff683e`
  - `portfolio_01ff3b4e0551b75c3c9a6136`
  - `portfolio_00a9b21be46f62bbc49de05e`

### Leave Efficient

- Ordering: Zero leave first, then calendar days per group leave day
- budget_feasible: `[]`
- conditional portfolio IDs:

  - `portfolio_3f61c6d18f0d9844ffc84f7f`
  - `portfolio_025bf6d946f14640fcbe3748`
  - `portfolio_88769958b13c31d8e5d89be2`
  - `portfolio_0b5c4165744dd1388e13e8f3`
  - `portfolio_f3e4cfa33c3cddd2e1fd43ab`

## Safety checks

| Check | Result |
|---|---|
| Unknown price remains null, not zero | PASS |
| No nonexistent mileage quote generated | PASS |
| ESTIMATED calendar not upgraded to OFFICIAL | PASS |
| UNVERIFIED routes not upgraded to VERIFIED | PASS |
| Unchecked seats not described as available | PASS |
| Unchecked ticketability not described as bookable | PASS |
| No CONFIRMED_BUDGET_FEASIBLE without account / eligibility evidence | PASS |
| No pooling of traveler mileage accounts | PASS |
| Truncated search does not claim global optimum | PASS |
| No unsupported 可出票 / 有票 / 已确认奖励位 claims | PASS |

All checks concern this supplied-input execution. No balances exist, so account-allocation correctness with real accounts was not exercised. Missing-tax known subtotal=0 is accompanied by taxes_hkd=null and complete_price_comparison_eligible=false; no complete cost is inferred.

## Blockers, interpretation and observations

- No observed safety blocker in this run. Execution succeeds; validation is **CONDITIONAL**, not confirmed travel or budget feasibility.
- NO_ROUTE: not observed for the four supplied pairs. UNVERIFIED snapshot connectivity is not verified route/schedule availability.
- NO_PRICE_EVIDENCE: present on all 100 candidates, plus RULE_VERSION_REVIEW_REQUIRED for 2027.
- NO_ACCOUNT_EVIDENCE and NO_FUNDING_ELIGIBILITY: present on every portfolio; no confirmed annual mileage capacity is inferred.
- NO_SEAT_EVIDENCE: present everywhere; unknown is not unavailable.
- TRUE_BUDGET_INFEASIBLE: not established for mileage. 1027 state rejections concern genuine leave-budget excess under the supplied estimated calendar only; they say nothing about award inventory.
- SEARCH_TRUNCATED: present; cap-dependent coverage/order must be disclosed. No cap sensitivity run was performed.
- Conditional Miles Saver emits five IDs despite entirely unknown miles, and matches Balanced in this run. Its output is explicitly within price classes and complete_price_comparison_eligible=false, but consumers must not read the view name as a savings claim.
- No new code defect was proven by this observation. Low evidence coverage and capped search limit decision usefulness. No repair was attempted.

## Next evidence needed

1. Official 2027 calendar and makeup-workday snapshot when actually published; until then keep these leave estimates conditional.
2. Date-specific operating schedules, exact cabins and suitable distance provenance; current GCD values cannot substantiate airline ticketed mileage.
3. Candidate-bound airline mileage and tax quotes plus explicit booking/travel rule applicability review for 2027.
4. Explicit account snapshots and payer/beneficiary funding eligibility, independently recorded; avoid public account identifiers or balances.
5. Live award-seat evidence and airline ticketability verification separately, with timestamps; neither follows from a local quote or route.

## Artifacts and scope audit

The committed result copies the planner JSON with only a validation_notice in existing top-level metadata. No output schema exists in schemas/; no schema or computational field was changed. The original /tmp result remains untouched and its SHA256 is recorded above. The added metadata states CONDITIONAL VALIDATION OUTPUT / NOT AWARD AVAILABILITY / NOT BOOKABLE / NO LIVE SEAT CHECK. This is output labeling authorized for this validation, not a planner modification.

Only this report and the labeled result are committed. All existing tracked source, tests, configuration, schemas, rules and validation inputs remain byte-identical to execution HEAD. No credentials, account identifiers or real account balances were added. No PR was created and no feature implemented.
