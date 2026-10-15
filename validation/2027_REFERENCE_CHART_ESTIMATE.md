# Phase 2B-2 — Reference Chart Estimate validation

**CONDITIONAL PLANNING ESTIMATE — NOT AN AIRLINE QUOTE — NOT AWARD AVAILABILITY — NOT BOOKABLE — NO LIVE SEAT CHECK**

Date: 2026-10-15. Execution base HEAD: `7c80c671f9284b900b6d4d9f82aa72cf3174b323`; branch main; initial worktree clean; Python 3.9.6. This approved development adds an explicitly opt-in reference layer. Phase 2A and Phase 2B-1 original artifacts/evidence remain unchanged.

## Acceptance and headline results

**Implementation PASS; sensitivity verdict PARTIAL_IMPROVEMENT_STILL_HIGHLY_SENSITIVE.** No claim of official current/2027 pricing, seat inventory, funding eligibility, complete cost or global optimality follows. Enter Phase 2C only as a separately evidence-gated stage, not as confirmed booking recommendations.

- Before: 258 passed, 0 failed/errors. After: **298 passed, 0 failed/errors**; 40 added regression tests, no existing tests weakened.
- Both E100/E200 CLI runs exited 0; stdout/stderr empty. Explicit profile kept identical; all original preference/calendar/route/rule resources unchanged.
- E100: 100/100 RULE_ESTIMATED candidates. E200: 200/200. All retain official_pricing_status RULE_VERSION_REVIEW_REQUIRED; quote=null; original quoted mileage totals=null.
- No balances or funding evidence were added to the real-preference runs: estimated budget-feasible=0 and confirmed budget-feasible=0. This is UNKNOWN funding, not budget infeasibility.

## Reference evidence and interface

Read [REFERENCE_CHART_ESTIMATE.md](../docs/REFERENCE_CHART_ESTIMATE.md) for the full contract. Runtime uses V1.1 cx_standard_base; optimizer.py, award_adapter.py, schemas, numeric rules and rounding are unchanged. Public rule evidence is newly attested in [2027_reference_chart_profile.json](2027_reference_chart_profile.json), with exact rules/chart bindings and provisional route bands.

Two independently published tables were rechecked on 2026-10-15: [Australian Frequent Flyer](https://www.australianfrequentflyer.com.au/cathay-pacific-award-charts/) (29 May 2026) and [FlyAsia](https://www.flyasia.co/2026/asiamiles-cathay-chart/) (displayed update 15 September 2026). All six reference rows agree. These are SECONDARY_CORROBORATION; source independence/authenticity is a manual attestation, not something URLs or Python can prove. No Japan campaign values replace the rule chart. Reference profile digest: `reference_3469a10ccd50ec1c931a9cba`.

## Controlled matrix

Both experiments use max_states=25000 (above the 20,100 combinations for 200 retained candidates), max_candidates_per_window=15, max_windows=30, max_allocation_states=20000, max_per_view=5. Only max_candidates_total differs (100 versus 200). This isolates the total candidate cap, unlike the original Phase 2A S0/S3 comparison which also changed per-window and state caps. A matched no-reference control was run at each configuration with identical retained candidate IDs.

| Run | Candidates pre/window/global | States | Conditional before planning Pareto | Returned conditional planning front | Planning dominated | search_truncated | Runtime seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E100 | 408/360/100 | 5050 | 1310 | 636 | 674 | True | 0.959 |
| E200 | 408/360/200 | 20100 | 5068 | 1835 | 3233 | True | 2.563 |

Portfolio-state caps do not bind: E100 visits 100+C(100,2)=5,050 states; E200 200+C(200,2)=20,100. Candidate caps still truncate 408 candidates to 100/200, so search_truncated remains true in both. No globally optimal result is claimed.

Planning Pareto shrinks the fronts by **51.45%** (1,310→636) and **63.79%** (5,068→1,835). This is comparison on estimated miles and explicitly comparable planning dimensions only; unknown taxes/cash were not treated as zero. Different destinations/evidence classes and cabin/leave/duration tradeoffs remain. The strict complete-quote dominance function is unchanged.

Exact commands used from repo root:

```bash
python3 -B -m unittest discover -p 'test_*.py' -v
python3 -B planner.py --input /tmp/amo-reference-b8lof1rw/E100_input.json --output /tmp/amo-reference-b8lof1rw/E100_result.json
python3 -B planner.py --input /tmp/amo-reference-b8lof1rw/E200_input.json --output /tmp/amo-reference-b8lof1rw/E200_result.json
python3 -B planner.py --input /tmp/amo-reference-b8lof1rw/E100_CONTROL_input.json --output /tmp/amo-reference-b8lof1rw/E100_CONTROL_result.json
python3 -B planner.py --input /tmp/amo-reference-b8lof1rw/E200_CONTROL_input.json --output /tmp/amo-reference-b8lof1rw/E200_CONTROL_result.json
```

Inputs/results are temporary under `/tmp/amo-reference-b8lof1rw`. Full raw results are not committed. Their input/output SHA256 values and commands are retained in the metrics JSON. For reproducibility, create a temporary copy of validation/2027_conditional_planner_input.json, resolve its existing resource paths relative to validation/, and add reference_chart pointing to validation/2027_reference_chart_profile.json. Set the fixed caps above and total=100/200. Keep balances_by_account=null, funding_eligibility=[] and evidence_by_candidate={}. No source resource is edited. Controls are the exact same temporary inputs with reference_chart omitted.

## Destination/cabin reference arithmetic

Every figure below is per-person / two-traveler group **roundtrip reference miles**, not a quote. The two directions are separately looked up. J/W and W/J totals are equal here; that does not merge their ticket/cabin structures. Y/Y remains subject to candidate minimum-cabin policy.

| Destination | Provisional band | W/W pp / group | J/J pp / group | J/W or W/J pp / group | Y/Y pp / group |
| --- | --- | --- | --- | --- | --- |
| CTS | Short Type 2 | 46,000 / 92,000 | 66,000 / 132,000 | 56,000 / 112,000 | 26,000 / 52,000 |
| SYD | Medium | 78,000 / 156,000 | 120,000 / 240,000 | 99,000 / 198,000 | Excluded by longhaul W minimum |
| AKL | Long | 104,000 / 208,000 | 182,000 / 364,000 | 143,000 / 286,000 | Excluded by longhaul W minimum |
| ZRH | Long | 104,000 / 208,000 | 182,000 / 364,000 | 143,000 / 286,000 | Excluded by longhaul W minimum |

One-way W/J reference values: CTS 23,000/33,000; SYD 39,000/60,000; AKL and ZRH 52,000/91,000. Distance labels remain DISTANCE_PROVISIONAL; all routes UNVERIFIED and calendars ESTIMATED. Table W/J presence does not verify aircraft cabins or award inventory.

## Distribution of returned portfolios

These are post-planning-Pareto counts. Destination/cabin counts measure trip occurrences, not unique routes; each two-trip portfolio contributes two trips.

| Run | One-trip / two-trip | AKL | ZRH | CTS | SYD |
| --- | --- | --- | --- | --- | --- |
| E100 | 90 / 546 | 283 | 249 | 413 | 237 |
| E200 | 164 / 1671 | 851 | 972 | 1122 | 561 |

| Run | J/J | W/W | J/W | W/J | Y/Y |
| --- | --- | --- | --- | --- | --- |
| E100 | 292 | 260 | 275 | 235 | 120 |
| E200 | 941 | 806 | 747 | 725 | 287 |

Estimated **group annual** mileage distribution:

| Run | Min | Median | Max | Distinct mileage totals |
| --- | --- | --- | --- | --- |
| E100 | 52000 | 372000.0 | 728000 | 57 |
| E200 | 52000 | 398000 | 728000 | 56 |

The complete frequency histogram and all destination/cabin candidate estimates are machine-readable in 2027_REFERENCE_CHART_ESTIMATE_METRICS.json. Different trip counts and comfort levels explain differing miles; lower estimated miles is not a complete-price or experience winner.

## Four views and cap stability

| View | Matched UNKNOWN control overlap | E100/E200 estimate overlap | Estimate Jaccard |
| --- | --- | --- | --- |
| Miles Saver | 40% | 60% | 0.429 |
| Balanced | 40% | 40% | 0.250 |
| Comfort First | 0% | 20% | 0.111 |
| Leave Efficient | 20% | 40% | 0.250 |

Using Phase 2A's classification convention, the overall experiment remains HIGHLY_SENSITIVE because multiple view overlaps are below 60%. Miles Saver improves to MODERATELY_SENSITIVE by the Top-5 overlap criterion alone, but that does not certify convergence. Mean four-view overlap increases from 25% in matched controls to 40% with references. This is a partial observed improvement, **not a demonstrated broad stability solution**; new evidence-bound IDs and deterministic tie ordering can also affect overlap.

Miles Saver now has a defined planning meaning: it ranks known reference miles within the evidence tier, rather than pretending unknown prices are comparable. Balanced ranks trip count then estimated miles. Both output ranking_basis RULE_ESTIMATED_MILES. Comfort First and Leave Efficient retain their ordering logic; the changed planning front can change their retained choices. Every budget_feasible view list remains empty.

### Miles Saver

**E100 Top 5**

- `portfolio_04de3bf90882c0086b3661d8`: 1 trip(s), 52000 estimated group miles.
- `portfolio_0754dd02eb41d1150d67bda8`: 1 trip(s), 52000 estimated group miles.
- `portfolio_2cdc725e24894a49a7623452`: 1 trip(s), 52000 estimated group miles.
- `portfolio_8946e8607ee4ad6d120e5df6`: 1 trip(s), 52000 estimated group miles.
- `portfolio_9ace3483f686127e602f1332`: 1 trip(s), 52000 estimated group miles.

**E200 Top 5**

- `portfolio_04de3bf90882c0086b3661d8`: 1 trip(s), 52000 estimated group miles.
- `portfolio_0754dd02eb41d1150d67bda8`: 1 trip(s), 52000 estimated group miles.
- `portfolio_0c5384c2b6a14dbf66421d24`: 1 trip(s), 52000 estimated group miles.
- `portfolio_2cdc725e24894a49a7623452`: 1 trip(s), 52000 estimated group miles.
- `portfolio_3d4d998acc4099605a8d86ce`: 1 trip(s), 52000 estimated group miles.

### Balanced

**E100 Top 5**

- `portfolio_34138029895c35f68f4e4530`: 2 trip(s), 104000 estimated group miles.
- `portfolio_7f411ae0ee05970cdd10740f`: 2 trip(s), 104000 estimated group miles.
- `portfolio_eb3d488beee3145a93d9749e`: 2 trip(s), 104000 estimated group miles.
- `portfolio_f0b07400650f63f4fd1fc2ac`: 2 trip(s), 104000 estimated group miles.
- `portfolio_18d7016a35ea5d4fae153176`: 2 trip(s), 144000 estimated group miles.

**E200 Top 5**

- `portfolio_099873b6c6d7b5e467329880`: 2 trip(s), 104000 estimated group miles.
- `portfolio_1418656856ac2c2e7216d3dc`: 2 trip(s), 104000 estimated group miles.
- `portfolio_31abb7c2f2263566094af724`: 2 trip(s), 104000 estimated group miles.
- `portfolio_34138029895c35f68f4e4530`: 2 trip(s), 104000 estimated group miles.
- `portfolio_7f411ae0ee05970cdd10740f`: 2 trip(s), 104000 estimated group miles.

### Comfort First

**E100 Top 5**

- `portfolio_0bddc3d71f078ecfd5976496`: 2 trip(s), 728000 estimated group miles.
- `portfolio_0ba30e8ef7bf2dcaff37eaa0`: 1 trip(s), 364000 estimated group miles.
- `portfolio_0c045ebdc533d1c66b56591e`: 2 trip(s), 476000 estimated group miles.
- `portfolio_72d707cb3e822e2d8bb9d55d`: 1 trip(s), 240000 estimated group miles.
- `portfolio_08d7492b6cfd9d0070f775f6`: 2 trip(s), 650000 estimated group miles.

**E200 Top 5**

- `portfolio_01b0ab386308e5005ad1f1d1`: 2 trip(s), 352000 estimated group miles.
- `portfolio_0ba30e8ef7bf2dcaff37eaa0`: 1 trip(s), 364000 estimated group miles.
- `portfolio_020d0bff6a615b2a34f55232`: 2 trip(s), 604000 estimated group miles.
- `portfolio_6240c26457502f0d45754776`: 1 trip(s), 364000 estimated group miles.
- `portfolio_01ac5ef856ea5ac0929fe1f3`: 2 trip(s), 650000 estimated group miles.

### Leave Efficient

**E100 Top 5**

- `portfolio_0446402b12793dcb02ade485`: 1 trip(s), 198000 estimated group miles.
- `portfolio_0f470c97a73a00987a580802`: 2 trip(s), 484000 estimated group miles.
- `portfolio_5728707aff154aba6fdd3e8a`: 1 trip(s), 156000 estimated group miles.
- `portfolio_375930b2c81d2a0deca0cba2`: 2 trip(s), 354000 estimated group miles.
- `portfolio_a0c7f578f6453df2acf46860`: 1 trip(s), 132000 estimated group miles.

**E200 Top 5**

- `portfolio_0446402b12793dcb02ade485`: 1 trip(s), 198000 estimated group miles.
- `portfolio_01ac5ef856ea5ac0929fe1f3`: 2 trip(s), 650000 estimated group miles.
- `portfolio_3656c3c9fcbb035df86f8e34`: 1 trip(s), 92000 estimated group miles.
- `portfolio_0253c27eb241f237215b4725`: 2 trip(s), 338000 estimated group miles.
- `portfolio_5728707aff154aba6fdd3e8a`: 1 trip(s), 156000 estimated group miles.

## Budget and safety results

- Real-preference E100/E200: estimated budget-feasible **0 / 0**, confirmed **0 / 0**. All allocations remain unknown because account evidence was deliberately absent. No real account balances were used or committed.
- A separate SYNTHETIC TEST simulation yields one ESTIMATED_BUDGET_FEASIBLE portfolio and zero confirmed, with per-account spending within independent balances. Its funding eligibility remains NOT_CHECKED. Synthetic tests cover the requested 182k/person feasible case and 260k/person non-pooling counterexample, as well as cumulative consumption across two trips. The 260k example uses a deliberately synthetic in-memory tariff; it is not a price claim about the shipped chart.
- Reference estimates cannot create CONFIRMED_BUDGET_FEASIBLE even when synthetic funding attestations are present. Missing or partial balances and allocation limits remain conditional/unknown.
- Every reference quote field is null, top-level quoted miles remain null, kernel_result is null, v1_evaluated=false, taxes unknown and complete_price_comparison_eligible=false. Estimate values are explicitly separate.
- All reference source/distance/future-applicability labels remain intact; no official chart certification, seat, ticketability, schedule, tax or funding evidence is fabricated.

| Invariant | E100 | E200 |
| --- | --- | --- |
| estimated_routes_preserved | PASS | PASS |
| future_rule_warning | PASS | PASS |
| no_account_evidence_added | PASS | PASS |
| no_confirmed_budget | PASS | PASS |
| no_seat_or_ticketability_upgrade | PASS | PASS |
| not_full_price_comparable | PASS | PASS |
| quote_fields_null | PASS | PASS |
| tax_unknown_not_zero | PASS | PASS |
| truncation_visible | PASS | PASS |

## Tests and manual code review

Full suite: **298 total / 298 passed / 0 failed / 0 errors**. The original 258 remain green; 40 new tests include direct lookup reuse; J/J, W/W, J/W, W/J and CTS Y/Y; all four bands/routes; exact quote precedence; no fallback over an invalid quote; publisher/date/digest binding; stale-rule rejection; no cabin/band invention; provisional route propagation; future applicability; independent annual accounts/no pooling; missing/partial balances/allocation limits; planning dominance and shorthaul comfort tradeoffs; and estimate/confirmed separation.

Manual review examined quote fallback, candidate/profile replay, annual indivisible allocation, nullable fields, evidence-tier ranking and planning Pareto classes. Fixes made during review: enforce request cabin minima, include shorthaul cabin experience in planning dominance, require literal boolean source attestations, preserve unknown dates, and ensure pre-existing mixed estimates cannot receive confirmed budget status. No independent review agent was used.

The original 2027 no-profile planner output was replayed and matches its original raw SHA256 exactly: `6e64cfe49a850125cb4c1bd15d009fc6e93a46a2fd2e45f92322b24d142bdfce`. Both reference CLI runs were also deterministically replayed. V1.1 numeric pricing and rounding are unchanged; adapter and all original tests/evidence remain byte-identical. The older mixed estimate budget label is intentionally made stricter, without altering its numeric result.

## Changed files and limits

- discovery/reference_estimate.py: explicit profile validation and direct-CX V1 lookup, no second tariff algorithm.
- discovery/award_pricing.py: quote-first wrapper with separate opt-in estimate output.
- discovery/portfolio.py: planning-ticket replay, separate estimated budgets, planning-only Pareto, labeled Miles Saver/Balanced ranking, legacy mixed-budget protection.
- planner.py: optional local reference profile resource and explicit planning metadata.
- tests/test_reference_estimate.py: 40 additional safety/correctness regressions.
- validation/2027_reference_chart_profile.json: new lower-tier public-source attestation and provisional route-band scope.
- validation/2027_REFERENCE_CHART_ESTIMATE_METRICS.json: E100/E200, matched controls, distributions, IDs, hashes and safety metrics.
- validation/2027_REFERENCE_CHART_ESTIMATE.md: this report.
- docs/REFERENCE_CHART_ESTIMATE.md, docs/PR3_AWARD_PRICING.md, docs/V2_DESIGN.md, README.md and SKILL.md: separate planning/reference contracts and opt-in usage.

No rules, schema, optimizer, adapter, original tests or existing validation evidence changed. No new dependency, login, live seat/fare search, booking, PR4/D2 extension, account scraping or Canonical change. Unknown taxes remain outside planning Pareto; estimates cannot establish complete cost. Separate/partner/connecting reference pricing remains unsupported. Source authenticity and independence remain human-reviewed attestations, not automated verification. Candidate truncation still materially affects results.

## Phase 2C recommendation

Proceed only with a separate, narrow evidence-acquisition/verification definition: explicit 2027 rule review and dated airline mileage/tax responses, then independent schedule/cabin, award-seat and ticketability checks. Do not remove review gates or present estimated budget simulations as final booking recommendations. Candidate-cap robustness remains an unresolved limitation and should accompany any later decision.
