# Validation Phase 2A — 2027 search-cap sensitivity

**CONDITIONAL VALIDATION OUTPUT · NOT AWARD AVAILABILITY · NOT BOOKABLE · NO LIVE SEAT CHECK**

Issue: [#7 — Validation Phase 2A: 2027 search-cap sensitivity](https://github.com/andrelyt/asia-miles-optimizer/issues/7). Issue body and all comments read before execution (0 comments). Executed 2026-10-15; observation-only.

## Execution identity and scope

- Execution branch: `main`; HEAD **`5f9659a99f2e5ee38a4d06afa351d1d3844b93fc`** (latest GitHub main at start). Python **3.9.6**. Worktree initially clean.
- Original first-run execution HEAD: `ce926bc9c0c95fdc6514b41f146ba1d3d7aec333`. The current main adds only its report/result; S0 reproduces the original raw output byte for byte.
- Full tests: `python3 -B -m unittest discover -p 'test_*.py' -v`: **258 total / 258 passed / 0 failed / 0 errors**, exit 0; 3.436 seconds. No traceback. No production code or existing tests changed afterward.
- Temporary input variants and raw outputs live under `/tmp/amo-2027-phase2a-hqcnsy0e`; none are committed. Symlinks resolve the unchanged relative resource references to existing tracked evidence. No external data was fetched and no missing evidence was supplied.
- Only `validation/2027_SEARCH_SENSITIVITY.md` and optional `validation/2027_SEARCH_SENSITIVITY_METRICS.json` are delivered. Existing planner, schemas, rules, config, validation inputs and previous results remain unchanged. No PR, features or Canonical Memory changes.

## Experiment matrix and byte-equivalent inputs

| Run | max_states | max_candidates_total | max_candidates_per_window |
| --- | --- | --- | --- |
| S0 | 5000 | 100 | 10 |
| S1 | 10000 | 100 | 10 |
| S2 | 20000 | 100 | 10 |
| S3 | 20000 | 200 | 15 |

Only the numeric tokens listed above were replaced in temporary copies of `validation/2027_conditional_planner_input.json`. S0 is byte-identical to that input; S1/S2 replace max_states only; S3 replaces all three tokens. Every other byte, including path strings, is unchanged. max_windows=30, max_allocation_states=20000, max_per_view=5 and all PR1/PR2 search settings remain fixed.

Unchanged input/evidence SHA256:

- `validation/2027_conditional_planner_input.json`: `6820386f2ed610c2aa4fd93dca4788ccdee08c7f55b23f59b0cba3cf90580c18`.
- `validation/2027_travel_request.json`: `7a0f2e3409761bb22a4acdd192d59694439146c988e2ba75b678354d38b229d5`.
- `validation/2027_calendar_estimated_anchors_only.json`: `813c1bc5d94aa9b1e69a3d52e3b87ea2813e234fc05d426633772f308e00b10a`.
- `validation/2027_hkg_four_dest_route_graph_unverified.json`: `bed3c5b830c5378e56d50d0a4c3cad52321a5f8aee65a870bfa582d138462045`.
- `rules_2026_10.json`: `1b88502223b3df56da028d488c4a03d1517dc9daef074c51c55342f93d684867`.
- `config/search_config.json`: `17953ee5314b5f40b7217b50a6a9a7b167d45aa69ba8a07c0cba69ed25496f64`.

Exact variant input/output SHA256:

- **S0** input: `6820386f2ed610c2aa4fd93dca4788ccdee08c7f55b23f59b0cba3cf90580c18`; raw output: `6e64cfe49a850125cb4c1bd15d009fc6e93a46a2fd2e45f92322b24d142bdfce` (5749083 bytes).
- **S1** input: `0458f4b77e31c56ca51d9e4c51760bb2b6114761e3f906e7b3388d3606cfa98f`; raw output: `e03a11cea9dc95bcbc618618fa189cb95d6cd5a93691ba892d5b98c628a936ec` (5782259 bytes).
- **S2** input: `63729b622937f6a760e7eb4df5b733a4da24c1fced9f76ddc68ab12cc416642f`; raw output: `15c8b13bed79f56e143d8f21b0e247828c6f53835131f7fd7f8aeab95eea0182` (5782259 bytes).
- **S3** input: `111e83d413b06e9f1520db3d5cc4ef87b04b5e523471ad425c39a100733b65ee`; raw output: `b69f925d4c982c3238c3c92435a2f3f0a2c258167ae826ab0af905bf733d0278` (19368389 bytes).

## Exact commands and reproducibility

The planner commands actually executed, from the repository root:

```bash
python3 -B planner.py --input /tmp/amo-2027-phase2a-hqcnsy0e/validation/S0_input.json --output /tmp/amo-2027-phase2a-hqcnsy0e/S0_result.json
python3 -B planner.py --input /tmp/amo-2027-phase2a-hqcnsy0e/validation/S1_input.json --output /tmp/amo-2027-phase2a-hqcnsy0e/S1_result.json
python3 -B planner.py --input /tmp/amo-2027-phase2a-hqcnsy0e/validation/S2_input.json --output /tmp/amo-2027-phase2a-hqcnsy0e/S2_result.json
python3 -B planner.py --input /tmp/amo-2027-phase2a-hqcnsy0e/validation/S3_input.json --output /tmp/amo-2027-phase2a-hqcnsy0e/S3_result.json
```

All four stdout and stderr streams were empty. Runtime includes process startup, JSON serialization and disk write; each configuration ran once, so these are observations, not benchmark averages.

To recreate the byte-equivalent temporary variants and resource layout without changing the repository, run the following preparation from a checkout of the execution SHA, then execute the four planner commands using the printed temporary directory:

```python
from pathlib import Path
import tempfile
repo = Path.cwd()
tmp = Path(tempfile.mkdtemp(prefix="amo-2027-phase2a-", dir="/tmp"))
(tmp / "validation").mkdir()
(tmp / "config").mkdir()
for name in ("2027_travel_request.json",
             "2027_calendar_estimated_anchors_only.json",
             "2027_hkg_four_dest_route_graph_unverified.json"):
    (tmp / "validation" / name).symlink_to(repo / "validation" / name)
(tmp / "rules_2026_10.json").symlink_to(repo / "rules_2026_10.json")
(tmp / "config/search_config.json").symlink_to(repo / "config/search_config.json")
source = (repo / "validation/2027_conditional_planner_input.json").read_text()
for label, states, total, per_window in (
    ("S0", 5000, 100, 10), ("S1", 10000, 100, 10),
    ("S2", 20000, 100, 10), ("S3", 20000, 200, 15)):
    text = source.replace('"max_states": 5000', '"max_states": ' + str(states))
    text = text.replace('"max_candidates_total": 100',
                        '"max_candidates_total": ' + str(total))
    text = text.replace('"max_candidates_per_window": 10',
                        '"max_candidates_per_window": ' + str(per_window))
    (tmp / "validation" / (label + "_input.json")).write_text(text)
print(tmp)
```

SHA256 values above validate the recreated variants. The experiment harness checked each parsed variant against the baseline with exactly the permitted cap differences, and checked S0 input byte equality. Source calendar/route/request data were consumed through read-only symlinks.

## Core results

| Run | Exit | Runtime seconds | Candidates pre / window / global | States visited | Returned = conditional Pareto | 1-trip / 2-trip | Confirmed budget | search_truncated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S0 | 0 | 0.990 | 408 / 240 / 100 | 5000 | 1300 | 100 / 1200 | 0 | true |
| S1 | 0 | 0.937 | 408 / 240 / 100 | 5050 | 1310 | 100 / 1210 | 0 | true |
| S2 | 0 | 0.923 | 408 / 240 / 100 | 5050 | 1310 | 100 / 1210 | 0 | true |
| S3 | 0 | 4.334 | 408 / 360 / 200 | 20000 | 5045 | 200 / 4845 | 0 | true |

Every run returned 24 concrete windows (8 labor_day, 16 national_day). Candidate pre/window/global counts use `diagnostics.orchestration_candidate_counts_by_window`, not the inner PR4 counters that start from already-capped CLI input. Conditional Pareto count equals returned count in each run; PARETO_DOMINATED=0. Unknown prices prevent strict price dominance and make a large conditional front unsurprising. All allocation_states_visited=0.

### Candidate versus state truncation

| Run | Window cap truncated | Global candidate cap truncated | Portfolio state cap reached |
| --- | --- | --- | --- |
| S0 | true | true | true |
| S1 | true | true | false |
| S2 | true | true | false |
| S3 | true | true | true |

- **S0:** candidate pruning and the 5,000-state cap both bind.
- **S1/S2:** enumeration of the retained 100-candidate set ends after 100 single trips + C(100,2)=4,950 pairs = 5,050 states. Neither portfolio-state cap binds. Both still report search_truncated=true because candidate caps removed alternatives; neither is a global optimum.
- **S3:** candidate pruning still binds (408 → 360 → 200), and 20,000 visited states is below 200 + C(200,2)=20,100 possible states for this retained set. It is also portfolio-state truncated.
- S1 and S2 full parsed results are identical after removing only diagnostics.config.max_states. Different raw SHA256 values reflect that recorded configuration value, not a recommendation change.
- S0 is byte-identical to the first run raw output (SHA256 6e64cfe49a850125cb4c1bd15d009fc6e93a46a2fd2e45f92322b24d142bdfce); its parsed content equals the committed previous result after removing only that archive's validation_notice.

- S0 candidate IDs shared with S0: 100 / 100; 0 new; 0 S0 candidates absent. Identical structures preserve their IDs; expanded caps change the retained population.
- S1 candidate IDs shared with S0: 100 / 100; 0 new; 0 S0 candidates absent. Identical structures preserve their IDs; expanded caps change the retained population.
- S2 candidate IDs shared with S0: 100 / 100; 0 new; 0 S0 candidates absent. Identical structures preserve their IDs; expanded caps change the retained population.
- S3 candidate IDs shared with S0: 100 / 100; 100 new; 0 S0 candidates absent. Identical structures preserve their IDs; expanded caps change the retained population.

### Rejection counts

| Run | ANNUAL_LEAVE_BUDGET_EXCEEDED | SAME_HOLIDAY_ALTERNATIVE | PARETO_DOMINATED | Total rejected states |
| --- | --- | --- | --- | --- |
| S0 | 1027 | 2673 | 0 | 3700 |
| S1 | 1034 | 2706 | 0 | 3740 |
| S2 | 1034 | 2706 | 0 | 3740 |
| S3 | 4031 | 10924 | 0 | 14955 |

Rejections describe evaluated portfolio states, not unavailable routes or missing award seats. Leave-budget rejection uses the unchanged ESTIMATED calendar. No mileage-budget infeasibility was established.

## Destination and holiday-pair distributions

Candidate destination distribution after all caps:

| Run | AKL | ZRH | CTS | SYD |
| --- | --- | --- | --- | --- |
| S0 | 23 | 21 | 32 | 24 |
| S1 | 23 | 21 | 32 | 24 |
| S2 | 23 | 21 | 32 | 24 |
| S3 | 46 | 51 | 63 | 40 |

Destination distribution among returned portfolios, measured as **trip occurrences** (a two-trip portfolio contributes twice; the same destination twice contributes twice):

| Run | AKL | ZRH | CTS | SYD | Total trip occurrences |
| --- | --- | --- | --- | --- | --- |
| S0 | 583 (23.32%) | 502 (20.08%) | 805 (32.20%) | 610 (24.40%) | 2500 |
| S1 | 592 (23.49%) | 507 (20.12%) | 811 (32.18%) | 610 (24.21%) | 2520 |
| S2 | 592 (23.49%) | 507 (20.12%) | 811 (32.18%) | 610 (24.21%) | 2520 |
| S3 | 2208 (22.33%) | 2498 (25.26%) | 2982 (30.15%) | 2202 (22.26%) | 9890 |

Portfolio participation (a portfolio counts once per distinct destination; columns need not sum to portfolio count):

| Run | AKL | ZRH | CTS | SYD |
| --- | --- | --- | --- | --- |
| S0 | 517 | 454 | 682 | 540 |
| S1 | 524 | 459 | 687 | 540 |
| S2 | 524 | 459 | 687 | 540 |
| S3 | 1979 | 2191 | 2541 | 1966 |

Holiday-family pairs for all two-trip portfolios:

| Run | labor_day + national_day | Other holiday pairs |
| --- | --- | --- |
| S0 | 1200 | 0 |
| S1 | 1210 | 0 |
| S2 | 1210 | 0 |
| S3 | 4845 | 0 |

Every two-trip portfolio pairs Labor Day and National Day; repeated-family alternatives are rejected. To expose destination movement within that constant holiday pair, the finer pair counts are:

| Holiday:destination pair | S0 | S1 | S2 | S3 |
| --- | --- | --- | --- | --- |
| labor_day:AKL + national_day:AKL | 66 | 68 | 68 | 229 |
| labor_day:AKL + national_day:CTS | 73 | 74 | 74 | 227 |
| labor_day:AKL + national_day:SYD | 75 | 75 | 75 | 154 |
| labor_day:AKL + national_day:ZRH | 57 | 60 | 60 | 214 |
| labor_day:CTS + national_day:AKL | 107 | 108 | 108 | 429 |
| labor_day:CTS + national_day:CTS | 123 | 124 | 124 | 441 |
| labor_day:CTS + national_day:SYD | 122 | 122 | 122 | 292 |
| labor_day:CTS + national_day:ZRH | 96 | 98 | 98 | 401 |
| labor_day:SYD + national_day:AKL | 62 | 62 | 62 | 344 |
| labor_day:SYD + national_day:CTS | 69 | 69 | 69 | 353 |
| labor_day:SYD + national_day:SYD | 70 | 70 | 70 | 236 |
| labor_day:SYD + national_day:ZRH | 56 | 56 | 56 | 322 |
| labor_day:ZRH + national_day:AKL | 54 | 54 | 54 | 336 |
| labor_day:ZRH + national_day:CTS | 60 | 60 | 60 | 335 |
| labor_day:ZRH + national_day:SYD | 62 | 62 | 62 | 225 |
| labor_day:ZRH + national_day:ZRH | 48 | 48 | 48 | 307 |

## Four recommendation views and overlap

All IDs below belong to conditional portfolios; all four budget_feasible view lists are empty in every run. These are not priced, available or bookable travel recommendations. **Miles Saver has no price evidence and establishes no savings.**

### Miles Saver

S0 Top 5 (S1 and S2 have the exact same five IDs in the exact same order):

- `portfolio_0017c47dba5c0c6b2c730d78`
- `portfolio_001ab767671420451fa40205`
- `portfolio_0033b3f051912cb2c2ff683e`
- `portfolio_01ff3b4e0551b75c3c9a6136`
- `portfolio_00a9b21be46f62bbc49de05e`

S3 Top 5:

- `portfolio_0000e75c58670a08284a8714`
- `portfolio_0017c47dba5c0c6b2c730d78`
- `portfolio_001ab767671420451fa40205`
- `portfolio_002403a688e3cc003fb86e5d`
- `portfolio_011300eb3a7d979a0602f7b3`

| Run vs S0 | Intersection | Top-5 overlap | Jaccard |
| --- | --- | --- | --- |
| S0 | 5 | 100% | 1.000 |
| S1 | 5 | 100% | 1.000 |
| S2 | 5 | 100% | 1.000 |
| S3 | 2 | 40% | 0.250 |

### Comfort First

S0 Top 5 (S1 and S2 have the exact same five IDs in the exact same order):

- `portfolio_04894c2041993737d7366a3c`
- `portfolio_10519c9e7f163efb6fe50efb`
- `portfolio_0e7e67606ceb77bf6809b92c`
- `portfolio_40c605a388e5a5d1dd917153`
- `portfolio_018fb75bb008f20c9c0737a3`

S3 Top 5:

- `portfolio_00266a8940f0170d42338176`
- `portfolio_100a918813729878cc664406`
- `portfolio_00e1cc0813dceb6df6311e96`
- `portfolio_17440900d81731cd0755ca4f`
- `portfolio_002403a688e3cc003fb86e5d`

| Run vs S0 | Intersection | Top-5 overlap | Jaccard |
| --- | --- | --- | --- |
| S0 | 5 | 100% | 1.000 |
| S1 | 5 | 100% | 1.000 |
| S2 | 5 | 100% | 1.000 |
| S3 | 0 | 0% | 0.000 |

### Balanced

S0 Top 5 (S1 and S2 have the exact same five IDs in the exact same order):

- `portfolio_0017c47dba5c0c6b2c730d78`
- `portfolio_001ab767671420451fa40205`
- `portfolio_0033b3f051912cb2c2ff683e`
- `portfolio_01ff3b4e0551b75c3c9a6136`
- `portfolio_00a9b21be46f62bbc49de05e`

S3 Top 5:

- `portfolio_0017c47dba5c0c6b2c730d78`
- `portfolio_0000e75c58670a08284a8714`
- `portfolio_002403a688e3cc003fb86e5d`
- `portfolio_001ab767671420451fa40205`
- `portfolio_00266a8940f0170d42338176`

| Run vs S0 | Intersection | Top-5 overlap | Jaccard |
| --- | --- | --- | --- |
| S0 | 5 | 100% | 1.000 |
| S1 | 5 | 100% | 1.000 |
| S2 | 5 | 100% | 1.000 |
| S3 | 2 | 40% | 0.250 |

### Leave Efficient

S0 Top 5 (S1 and S2 have the exact same five IDs in the exact same order):

- `portfolio_3f61c6d18f0d9844ffc84f7f`
- `portfolio_025bf6d946f14640fcbe3748`
- `portfolio_88769958b13c31d8e5d89be2`
- `portfolio_0b5c4165744dd1388e13e8f3`
- `portfolio_f3e4cfa33c3cddd2e1fd43ab`

S3 Top 5:

- `portfolio_1abc419af2cf0d43e92286f1`
- `portfolio_00a1a8d8c0ae46ce7e2746eb`
- `portfolio_1c29817e2d76b5c73086a855`
- `portfolio_0b5c4165744dd1388e13e8f3`
- `portfolio_30980b01b07487572dd9e2cd`

| Run vs S0 | Intersection | Top-5 overlap | Jaccard |
| --- | --- | --- | --- |
| S0 | 5 | 100% | 1.000 |
| S1 | 5 | 100% | 1.000 |
| S2 | 5 | 100% | 1.000 |
| S3 | 1 | 20% | 0.111 |

## Stability classification

Issue #7 convention, not planner policy: STABLE requires all Top-5 sets unchanged and major distributions changing <5%; MODERATELY_SENSITIVE applies when Top-5 overlap is at least 60% or distribution changes are 5–20%; HIGHLY_SENSITIVE applies when any Top-5 overlap is below 60% or a major distribution changes >20%. When clauses overlap, the highest sensitivity takes precedence.

For reproducibility, major distributions here are normalized 1/2-trip mix, destination trip-occurrence shares, and holiday-family pair shares. “Percent change” means relative change of each normalized share from S0; percentage-point deltas are separately retained. This avoids treating the larger sample size alone as distribution shift. Raw counts and finer destination-pair counts are supplied above; no weighted scoring was added.

| Run | Classification vs S0 | Maximum relative share change | Maximum absolute share change (percentage points) |
| --- | --- | --- | --- |
| S0 | STABLE | 0.000% | 0.000 |
| S1 | STABLE | 0.794% | 0.194 |
| S2 | STABLE | 0.794% | 0.194 |
| S3 | HIGHLY_SENSITIVE | 48.464% | 5.178 |

S1/S2 add ten two-trip portfolios (+0.77% total returned) without changing any view Top 5. S3 materially changes membership and view order: overlaps are 40% Miles Saver, 0% Comfort First, 40% Balanced, 20% Leave Efficient. The one-trip share falls from 7.692% to 3.964% (−48.464% relative); maximum absolute share movement is 5.178 percentage points (the destination distribution). Even if distribution thresholds were interpreted as percentage points, the Top-5 overlap criterion independently makes S3 HIGHLY_SENSITIVE.

S3 changes candidate count and per-window cap together, while its state cap binds. This experiment cannot isolate those two candidate knobs or claim that its recommendations have converged. S1/S2 stability is conditional on the retained 100-candidate population, not global stability.

## Safety invariants

The same ten first-run safety invariants were checked on every retained trip and returned portfolio. No safety status changed:

| Invariant | S0 | S1 | S2 | S3 |
| --- | --- | --- | --- | --- |
| Unknown award price remains null, not zero | PASS | PASS | PASS | PASS |
| No invented mileage quote or kernel evaluation | PASS | PASS | PASS | PASS |
| ESTIMATED calendar never upgraded to OFFICIAL | PASS | PASS | PASS | PASS |
| UNVERIFIED route never upgraded to VERIFIED | PASS | PASS | PASS | PASS |
| Unchecked award seats never described as available | PASS | PASS | PASS | PASS |
| Unchecked ticketability never described as bookable | PASS | PASS | PASS | PASS |
| No confirmed budget without verified balances / eligibility | PASS | PASS | PASS | PASS |
| No mileage-account pooling | PASS | PASS | PASS | PASS |
| No global-optimum claim under truncated search | PASS | PASS | PASS | PASS |
| No unsupported 可出票 / 有票 / 已确认奖励位 claim | PASS | PASS | PASS | PASS |

- PR3 status counts: S0/S1/S2 each 100 RULE_VERSION_REVIEW_REQUIRED; S3 200. EVALUATED / NEEDS_DATA / NEEDS_AIRLINE_QUOTE / UNSUPPORTED all 0. This is the first applicability gate, not evidence that quotes exist.
- All pricing remains UNKNOWN; mileage totals and taxes remain null. Known subtotals=0 mean no known priced components. complete_price_comparison_eligible=false everywhere.
- Every holiday stays ESTIMATED and every route stays UNVERIFIED. All award-seat and ticketability states remain NOT_CHECKED; no date-specific schedule or official ticketed mileage is inferred.
- No account allocation is performed. Balances are null; eligibility empty. Unknown funding is not infeasibility, and this run does not exercise real-account payment correctness.
- These are per-run safety observations, not a proof of correctness for other inputs. No fake evidence or real financial accounts were added.

## Outcome and next evidence

**Observation-only experiment COMPLETE; no observed safety blocker. Cap sensitivity: S1 STABLE, S2 STABLE, S3 HIGHLY_SENSITIVE versus S0. All conclusions remain CONDITIONAL.**

The existing 5,000-state limit omits a small number of valid pairs within the 100 retained candidates, without affecting these four Top-5 lists. Raising the candidate cap changes the retained search space and all four recommendation sets, demonstrating that the baseline recommendations depend on pruning. None of these runs is globally optimal, and none supplies mileage or availability evidence.

NO_ROUTE is not established for any supplied destination. NO_PRICE_EVIDENCE, NO_ACCOUNT_EVIDENCE, NO_FUNDING_ELIGIBILITY, NO_SEAT_EVIDENCE, pending 2027 rule applicability and SEARCH_TRUNCATED remain distinct blockers to stronger claims. TRUE_BUDGET_INFEASIBLE is not established for mileage; annual leave excess is a separate observed rejection reason.

Further decision confidence requires explicit 2027 rule review; candidate-bound airline mileage/tax quotes; dated route/cabin/schedule evidence; actual payer/beneficiary eligibility and independently recorded balances; official calendar evidence when published; and separate live seat/ticketability checks. These evidence gaps were not filled in this experiment. Any further cap experiment needs its own declared matrix; no new search or policy defaults are proposed by this report.

## Delivery audit

Only this new Markdown report and its optional machine-readable metrics JSON are committed. Temporary variant inputs, raw outputs and logs stay outside Git. Mainline code, tests, schemas, rules, configs, original validation evidence and archived first-run artifacts are unchanged. No generated caches, credentials, real account balances or new personal evidence were introduced.
