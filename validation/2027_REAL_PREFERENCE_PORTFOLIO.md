# Phase 2C — Real Preference Portfolio Validation & Decision Family Stability

**PLANNING ONLY · NOT BOOKABLE · NO LIVE SEAT CHECK · NO AIRLINE QUOTE · TAXES UNKNOWN**

## Execution and evidence

Execution base main: `88f3cc803d234e7f0c8a2098ad218bf8f8d6e4dc`. Python 3.9.6. Initial workspace clean; implementation was uncommitted during execution. This commit contains the executed implementation plus final presentation refinements. Implementation hashes are recorded in the metrics JSON.

Baseline: **298 passed / 0 failed / 0 errors**. Final full suite: **327 passed / 0 failed / 0 errors**, including 29 new tests; command `python3 -B -m unittest discover -p 'test_*.py' -v` (11.576 seconds).

Approximate balance scenario: **A=300k / B=250k**, USER_REPORTED_APPROXIMATE. Anonymous runtime travelers A/B retain independent annual leave 15/13. Both travel together; HKG only, May/October 2027, CTS/SYD/AKL/ZRH, 1–2 trips. Longhaul W minimum, J preferred; J/W and W/J allowed. Runtime inputs were private temporary files, not committed. Public JSON omits balance values, remainders and identity mappings; it retains estimated spending and a scenario digest. The original validation inputs are unchanged.

Calendar stays ESTIMATED anchors only, all eight graph edges stay UNVERIFIED, distances/bands stay provisional, reference prices stay RULE_ESTIMATED / SECONDARY_CORROBORATED_REFERENCE. The official 2027 pricing gate stays RULE_VERSION_REVIEW_REQUIRED. No quotes, seats, schedules, taxes, verified balances or funding eligibility were added.

## Reproduction and safety ceiling

Runtime-only input extends the existing conditional planner input with the unchanged reference profile, anonymous IDs, `decision_families=true` and the explicit own-account approximate funding scenario. Common caps: max_windows=30, max_candidates_per_window=17, max_states=90000, max_allocation_states=20000, max_per_view=5. Only max_candidates_total differs (100/200/408).

Command for each private input:

```bash
python3 -B planner.py --input /tmp/private_phase2c/C100_input.json --output /tmp/private_phase2c/C100_result.json
# Repeat for C200 and C408; external process-group supervisor stops each at 60 seconds.
```

Primary searches all exited 0 with empty stdout/stderr. Memory below is cumulative child-process peak RSS observed after completion (macOS getrusage), not an enforced memory ceiling. Sandbox did not permit live ps monitoring. A later validation replay completed C100/C200 (3.718s/6.348s), with **identical non-presentation JSON**, but C408 was stopped safely at 60.531s (exit -15, RUNTIME_CEILING_60_SECONDS). That replay is **FULL_CANDIDATE_EXHAUSTION_NOT_COMPLETED**; it does not erase the completed primary run. Timing is environment-dependent and not a performance guarantee.

The successful primary C408 snapshot supplies the exhaustion evidence. The only subsequent search-facing edit makes candidate-cap metadata distinguish actual caps from invalid-input filtering; it is identical on this input. Final shortlist destination coverage was reapplied using summarize_families to completed snapshots, without rerunning search or changing candidates/portfolios. Output and implementation hashes, both run observations and comparison details are recorded in JSON. No further cap experiments are planned.

## Search, funding and leave

| Run | Generated / retained | States | Runtime s | Observed MiB | Candidate cap | Search truncated | Pareto portfolios | Families / family Pareto |
|---|---:|---:|---:|---:|---|---|---:|---:|
| C100 | 408 / 100 | 5,050 | 1.025 | 60.1 | True | True | 555 | 164 / 164 |
| C200 | 408 / 200 | 20,100 | 2.253 | 107.5 | True | True | 1,463 | 221 / 221 |
| C408 | 408 / 408 | 83,436 | 11.620 | 263.8 | False | False | 5,231 | 231 / 231 |

**CURRENT_UNIVERSE_EXHAUSTED=true** for the successful C408 run: 408 + C(408,2) = **83,436** states, EXHAUSTIVE_WITHIN_CURRENT_CANDIDATE_UNIVERSE. **GLOBAL_OPTIMUM=false**. C100/C200 exhausted their retained subsets only.

All returned portfolios/families are ESTIMATED_BUDGET_FEASIBLE in the conditional channel. Confirmed portfolios=0, unknown funding states=0 in this reference-priced scenario. Missing verified balances/eligibility remains unresolved, regardless of the simulated arithmetic.

| Run | Funding feasible before Pareto | Funding infeasible | Funding unknown | Leave rejected | A breached | B breached | B-only breach | Pareto removed | Same-holiday alternatives |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C100 | 1,040 | 287 | 0 | 984 | 412 | 984 | 572 | 485 | 2,739 |
| C200 | 3,765 | 1,235 | 0 | 4,111 | 1,747 | 4,111 | 2,364 | 2,302 | 10,989 |
| C408 | 15,657 | 4,692 | 0 | 17,051 | 7,225 | 17,051 | 9,826 | 10,426 | 46,036 |

These are sequential state classifications: holiday/overlap → annual leave → own-account funding → Pareto. C408: 46,036 same-holiday alternatives + 17,051 leave failures + 4,692 funding failures + 10,426 Pareto removals + 5,231 retained = 83,436. Thus the 13-day shared travel ceiling excludes **17,051** combinations; **9,826** breach only B, not A. This is not an estimate of how many would survive all other gates with a larger leave budget.

Funding is cumulative by traveler across trips, with no cross-funding or pooling. 260k/person is infeasible because B exceeds 250k, even though group 520k < 550k; 248k/person is feasible only as an approximate simulation. Unknown mileage or a missing balance never becomes numeric zero or confirmed feasibility (regression tests cover this).

Family counts are over the returned planning Pareto front, not every pre-Pareto date variant. All 231 C408 families remain nondominated: within each destination/holiday mix, lower miles trade off against cabin comfort. Preserving destinations and different trip counts prevents an artificial universal winner.

## Exact vs decision-family stability

| Pair | View | Exact intersection / 5 | Family intersection / 5 |
|---|---|---:|---:|
| C100_vs_C200 | Miles Saver | 1/5 (20%) | 4/5 (80%) |
| C100_vs_C200 | Balanced | 0/5 (0%) | 2/5 (40%) |
| C100_vs_C200 | Comfort First | 3/5 (60%) | 5/5 (100%) |
| C100_vs_C200 | Leave Efficient | 4/5 (80%) | 2/5 (40%) |
| C100_vs_C408 | Miles Saver | 1/5 (20%) | 4/5 (80%) |
| C100_vs_C408 | Balanced | 0/5 (0%) | 2/5 (40%) |
| C100_vs_C408 | Comfort First | 0/5 (0%) | 5/5 (100%) |
| C100_vs_C408 | Leave Efficient | 1/5 (20%) | 1/5 (20%) |
| C200_vs_C408 | Miles Saver | 2/5 (40%) | 5/5 (100%) |
| C200_vs_C408 | Balanced | 1/5 (20%) | 5/5 (100%) |
| C200_vs_C408 | Comfort First | 0/5 (0%) | 5/5 (100%) |
| C200_vs_C408 | Leave Efficient | 1/5 (20%) | 2/5 (40%) |

**PHASE_2C_DECISION_STABILITY_VERDICT = MODERATELY_STABLE.** C200→C408 Miles Saver/Balanced/Comfort First are DATE_LEVEL_SENSITIVE_BUT_DECISION_STABLE (100% family overlap against 40%/20%/0% exact overlap). Comfort First is family-stable across every comparison. Leave Efficient is genuinely less stable (40% for C200→C408, 20% C100→C408); Balanced also changes strategy between C100 and larger universes. Do not generalize date-level stability to all views. Canonical tie breaks in family views intentionally differ from exact-ID tie breaks; this diagnoses a decision abstraction, not a strict decomposition of every rank movement.

## Top strategy families (C408)

Dates do not enter family IDs. J/W means outbound J, inbound W, using separate directional awards; it is not a new same-ticket mixed-cabin pricing formula. Representatives prefer lower leave, then mileage, uncertainty and deterministic IDs; no preferred-duration target was supplied. Family Pareto includes duration. No original candidates/portfolios were removed by aggregation.

### Miles Saver

1. `1_TRIPS|MAY:CTS:Y-Y`
2. `1_TRIPS|OCT:CTS:Y-Y`
3. `1_TRIPS|MAY:CTS:W-W`
4. `1_TRIPS|OCT:CTS:W-W`
5. `2_TRIPS|MAY:CTS:Y-Y|OCT:CTS:Y-Y`

### Balanced

1. `2_TRIPS|MAY:CTS:Y-Y|OCT:CTS:Y-Y`
2. `2_TRIPS|MAY:CTS:W-W|OCT:CTS:Y-Y`
3. `2_TRIPS|MAY:CTS:Y-Y|OCT:CTS:W-W`
4. `2_TRIPS|MAY:CTS:J-W|OCT:CTS:Y-Y`
5. `2_TRIPS|MAY:CTS:W-J|OCT:CTS:Y-Y`

### Comfort First

1. `2_TRIPS|MAY:AKL:J-J|OCT:CTS:J-J`
2. `2_TRIPS|MAY:AKL:J-J|OCT:CTS:J-W`
3. `2_TRIPS|MAY:AKL:J-J|OCT:CTS:W-J`
4. `2_TRIPS|MAY:AKL:J-J|OCT:CTS:W-W`
5. `2_TRIPS|MAY:AKL:J-J|OCT:CTS:Y-Y`

### Leave Efficient

1. `1_TRIPS|OCT:AKL:J-J`
2. `1_TRIPS|OCT:AKL:J-W`
3. `1_TRIPS|OCT:AKL:W-J`
4. `1_TRIPS|OCT:AKL:W-W`
5. `1_TRIPS|OCT:CTS:J-J`

Best one-trip mileage: May CTS Y/Y, 26k/person (October CTS Y/Y is the equal-mileage holiday alternative). Best one-trip longhaul/leave leader: October AKL J/J, 182k/person and four leave days each. Best two-trip mileage: May CTS Y/Y + October CTS Y/Y, 52k/person, nine leave days each. Best two-trip comfort: May AKL J/J + October CTS J/J, 248k/person, nine leave days each. These are view-specific choices, not full-cost winners. Balanced has no repeat-destination penalty, so the two-CTS year should be explicitly discussed with the traveler.

## Phase 2C verification shortlist

Seven families cover all four destinations and the requested roles; roles merge, eight is a ceiling. Every row is **RULE_ESTIMATED · DISTANCE_PROVISIONAL · CALENDAR_ESTIMATED · ROUTE_UNVERIFIED · SEATS_NOT_CHECKED · TAXES_UNKNOWN · TICKETABILITY_NOT_CHECKED**, with full-price comparison false.

| # / priority | Strategy and representative dates | Miles per A / B; group | Leave A used/remain; B used/remain | Approximate remainder A / B | Roles |
|---|---|---:|---|---:|---|
| 1 / MEDIUM | May CTS Y/Y 2027-04-24→2027-05-02 (9 days; leave A/B 5/5) | 26k / 26k; 52k | 5/10; 5/8 | ~274k / ~224k | BEST_MILES_SAVER |
| 2 / MEDIUM | May CTS Y/Y 2027-04-24→2027-05-02 (9 days; leave A/B 5/5) + Oct CTS Y/Y 2027-09-25→2027-10-03 (9 days; leave A/B 4/4) | 52k / 52k; 104k | 9/6; 9/4 | ~248k / ~198k | BEST_BALANCED, STRONG_TWO_TRIP |
| 3 / HIGH | May AKL J/J 2027-04-24→2027-05-02 (9 days; leave A/B 5/5) + Oct CTS J/J 2027-09-25→2027-10-03 (9 days; leave A/B 4/4) | 248k / 248k; 496k | 9/6; 9/4 | ~52k / ~2k | BEST_COMFORT_FIRST, LONGHAUL_J |
| 4 / HIGH | Oct AKL J/J 2027-09-25→2027-10-03 (9 days; leave A/B 4/4) | 182k / 182k; 364k | 4/11; 4/9 | ~118k / ~68k | BEST_LEAVE_EFFICIENT, STRONG_ONE_TRIP |
| 5 / HIGH | May SYD J/W 2027-04-24→2027-05-02 (9 days; leave A/B 5/5) | 99k / 99k; 198k | 5/10; 5/8 | ~201k / ~151k | MIXED_CABIN_EFFICIENT |
| 6 / HIGH | May CTS Y/Y 2027-04-24→2027-05-02 (9 days; leave A/B 5/5) + Oct ZRH W/W 2027-09-25→2027-10-03 (9 days; leave A/B 4/4) | 130k / 130k; 260k | 9/6; 9/4 | ~170k / ~120k | DESTINATION_DIVERSITY |
| 7 / HIGH | May SYD W/J 2027-04-24→2027-05-02 (9 days; leave A/B 5/5) | 99k / 99k; 198k | 5/10; 5/8 | ~201k / ~151k | MIXED_CABIN_ALTERNATIVE_DIRECTION |

All shortlist rows: funding **ESTIMATED_BUDGET_FEASIBLE**, never verified account balances or payer/beneficiary authorization. Dates are window endpoints, not verified flight operating/arrival dates. Representative dates commonly start before the named holiday because bridge leave is permitted. For example, April 24→May 2 uses five leave days each; September 25→October 3 uses four.

### J dependence, savings and balance sensitivity

- Most J-dependent: comfort family May AKL J/J + October CTS J/J (four J directional checks for two people), and October AKL J/J (two longhaul J directional checks). SYD J/W and W/J need J on opposite directions, so availability may favor one family over the other. None has checked seats.
- Within the unchanged reference chart, SYD J/W or W/J is 99k/person versus J/J 120k: **21k/person saved**. AKL/ZRH J/W is 143k versus J/J 182k: **39k/person saved**. CTS J/W is 56k versus J/J 66k: 10k/person. These are sums of separately priced directional awards, not evidence about FlyAsia or same-ticket mixed rounding; no rounding changed.
- The selected 248k/person comfort year leaves approximate A52k/B2k, only 0.8% of B’s assumed balance. Any higher quote can reverse funding feasibility. Two SYD J/J trips at 240k/person (other families, not the shortlist) leave B10k, also within the 5% caution band. Approximate proximity drives HIGH verification priority, not confidence.

## Next evidence: Phase 2D scope

The final shortlist yields **16 unique directional route/planning-date/cabin leads**, deduplicated across seven families. Each needs joint two-person availability; this is not 16 confirmed flights or inventory queries performed. Preserve the family alternatives instead of checking every date variant.

| Origin | Destination | Planning date | Cabin |
|---|---|---|---|
| AKL | HKG | 2027-05-02 | J |
| AKL | HKG | 2027-10-03 | J |
| CTS | HKG | 2027-05-02 | Y |
| CTS | HKG | 2027-10-03 | J |
| CTS | HKG | 2027-10-03 | Y |
| HKG | AKL | 2027-04-24 | J |
| HKG | AKL | 2027-09-25 | J |
| HKG | CTS | 2027-04-24 | Y |
| HKG | CTS | 2027-09-25 | J |
| HKG | CTS | 2027-09-25 | Y |
| HKG | SYD | 2027-04-24 | J |
| HKG | SYD | 2027-04-24 | W |
| HKG | ZRH | 2027-09-25 | W |
| SYD | HKG | 2027-05-02 | J |
| SYD | HKG | 2027-05-02 | W |
| ZRH | HKG | 2027-10-03 | W |

Next obtain actual operating dates/times, cabin existence, two award seats on the same flights, airline miles and tax quotes, official rule applicability for travel dates, verified balances and funding/beneficiary eligibility; then revalidate leave/overnight/timezone effects. Calendar makeup days remain unknown. Prioritize HIGH near-limit/longhaul families first, retain CTS baseline and ZRH W/W as alternatives. This phase performs none of those checks. Stop candidate-cap experiments for this fixed universe after the completed C408 run; new evidence may justify a later search with changed inputs.

## Manual safety review

- **PASS** — no_unknown_mileage_zero_fallback.
- **PASS** — no_generated_airline_quote.
- **PASS** — calendar_remains_estimated.
- **PASS** — routes_remain_unverified.
- **PASS** — seats_not_checked.
- **PASS** — ticketability_not_checked.
- **PASS** — no_confirmed_budget.
- **PASS** — no_pooling.
- **PASS** — official_2027_review_gate_retained.
- **PASS** — unknown_taxes_not_zero.
- **PASS** — no_global_optimality.
- **PASS** — optimizer.py, rounding, award adapter/pricing, rules, schemas, prior validation evidence and original 298 tests are unchanged; no new dependencies, credentials, browser/API integrations or Canonical Memory writes.
- **PASS** — committed JSON contains only anonymous traveler IDs, no personal balance values, remainders, names, emails or account identifiers. Runtime raw outputs remain private/untracked.

## Implementation, limitations and acceptance

Added discovery/approximate_funding.py (explicit own-account simulation), discovery/decision_families.py (canonical key/representatives/Pareto/views/shortlist/lead set), tests/test_decision_families.py (29 synthetic regressions). Updated discovery/portfolio.py and planner.py opt-in paths, README.md/SKILL.md and docs/DECISION_FAMILIES.md. Added this report and anonymized metrics JSON. No policy/schema change.

New tests cover date-free identity, direction, ordering, representative determinism/lower leave, overlap, no mutation, independent accounts/no pooling, cumulative annual spend through real optimizer integration, unknown prices/balances, B-only leave breach, no confirmed upgrade, default behavior, bounded/diverse shortlist, priority, planning dominance and exhaustion metadata.

Implementation acceptance: **PASS for the requested Phase 2C scope**. Decision stability remains **MODERATELY_STABLE**, not full operational readiness. Known limits: four destinations/direct roundtrips only, family Pareto over representatives of the returned planning front, no duration target, ordinal cabin scores/tie-sensitive views, repeated destinations not penalized, estimated holiday dates and distance bands, no official future tariff, no tax/full-cost or schedule/seat/ticketability evidence. Runtime C408 variability is recorded above; do not promise a fixed completion time. No PR created; delivery targets main.
