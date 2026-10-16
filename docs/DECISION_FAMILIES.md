# Phase 2C: decision families and explicit approximate funding

Offline planning only. NOT BOOKABLE. No sources, evidence snapshots, policy chart,
rounding, schema or V1.1 pricing algorithm change in this phase.

## Interfaces

- `optimize_portfolios(..., approximate_funding=None)` accepts an opt-in object with
  exactly `evidence_level: USER_REPORTED_APPROXIMATE` and `balances_by_traveler`.
  Keys must exactly match traveler IDs; values are nonnegative integer miles or
  null. Do not pass `balances_by_account` with this object: these are different
  funding policies. The default PR4 general payer/beneficiary allocator is unchanged.
- `planner.plan()` accepts this object inline or from a local resource path, and a
  boolean `decision_families` (default false). Local CLI usage is unchanged:
  `python3 -B planner.py --input /tmp/private_scenario.json --output /tmp/private_result.json`.
  Keep both files private: runtime results expose spending and approximate remainders.
  No real balance example is committed.
- `approximate_funding.validate_scenario()` validates and copies the scenario;
  `simulate()` compares whole-horizon own-account spending independently. A known
  excess yields INFEASIBLE, a missing price/balance yields UNKNOWN, otherwise
  ESTIMATED_BUDGET_FEASIBLE. The digest binds portfolio IDs to the scenario without
  making it an airline account attestation. Digests are identifiers, not anonymization
  guarantees; do not publish runtime inputs or remainders for personal scenarios.
- `decision_families.summarize_families(result, request)` adds a presentation view
  over returned planning Pareto portfolios. It does not prune original candidates,
  rerun pricing or delete original portfolios. Supports direct outbound/return
  only; connecting/missing-holiday structures raise an explicit error.
- `canonical_key()`, `representative_key()`, `family_dominates()`, `overlap()` and
  `verification_priority()` are deterministic pure helpers.

## Funding, leave and gates

Every traveler participates in all trips. PR3 currently supplies the same per-person
price for every member of that candidate group. Sum that per-person amount across
all annual trips, then compare each traveler's own balance; never sum accounts,
reset balances for each trip, or infer permission to cross-fund. A known individual
excess rejects the combination before planning Pareto. Leave dates remain a union
by traveler and calendar year using the existing PR4 logic.

Diagnostics count leave breaches per traveler, exclusive single-traveler breaches,
and approximate funding states. Stages are sequential: structural/holiday/overlap
rejections precede leave, leave precedes funding, funding precedes Pareto. Counts
at different stages are not independent counterfactual rejection estimates.

Approximate success is still in `conditional`, with
`APPROXIMATE_BALANCES_NOT_AIRLINE_VERIFIED`, `funding_eligibility_status=NOT_CHECKED`,
and `complete_price_comparison_eligible=false`. It cannot populate the confirmed
`budget_feasible` array. The reference chart remains RULE_ESTIMATED;
RULE_VERSION_REVIEW_REQUIRED and quote/seat/tax/ticketability gates remain unchanged.
Unknown taxes are null, excluded from limited planning mileage comparisons.

## Family and representative semantics

Key: trip count plus sorted holiday/destination/outbound-inbound cabin tuples,
for example `2_TRIPS|MAY:CTS:Y-Y|OCT:SYD:J-J`. J/W and W/J are different.
No dates, account identities, candidate IDs or portfolio IDs enter the key.
Current family scope is the HKG direct roundtrip validation universe; it is not a
universal identity for multi-origin, connecting or D2 itineraries.

Representative ordering: lower maximum individual annual leave, lower group leave,
known/lower estimated mileage, fewer uncertain evidence labels, sorted candidate
IDs, then portfolio ID. No preferred-duration target is supplied by the current
request model; valid durations have equal fit at this step. Duration is retained
as a Pareto criterion. Candidate/portfolio IDs resolve exact ties deterministically.

Family Pareto compares representatives within the same holiday/destination mix,
evidence/status/reference basis and year layout. Dimensions are estimated mileage,
trip count, group and individual per-year leave, longhaul/all-sector cabin rank,
and travel days. More valid travel days are preferred for this planning comparison;
no destination full-day or schedule claim follows. Destinations are not assumed
interchangeable. All families remain listed with a flag even if dominated. If every
family trades comfort for miles, all may legitimately remain nondominated.

Four eligible family views select at most five ESTIMATED_BUDGET_FEASIBLE families:
Miles Saver uses estimated miles; Balanced uses trip count then miles; Comfort
First uses longhaul cabin rank then trip count; Leave Efficient uses zero leave,
then calendar-days/group-leave ratio and duration. Canonical keys break family
ties, avoiding arbitrary date-ID tie breaks. Balanced does not reward destination
novelty: two CTS trips can outrank a costlier mixed-destination year.

Shortlist roles: view leaders, strong one/two-trip, efficient asymmetric longhaul,
longhaul J, missing-destination coverage, and optionally the reverse W/J direction.
Roles merge by family ID; eight is a ceiling. HIGH priority means a feasible
core premium choice or within 5% of an approximate account limit; MEDIUM means
another feasible alternative, LOW means non-feasible/unknown. Priority asks for
future evidence, never asserts inventory. Leads deduplicate origin/destination/
planning-date/cabin; two travelers require joint availability in later validation.
Window endpoints are planning date assumptions, not operated flight dates,
arrival dates, timezone/overnight validation or verified schedules.

## Stability and exhaustion

Report exact portfolio Top-5 intersection divided by the larger list length, and
family Top-5 overlap separately (also expose Jaccard). This prevents many date
variants from hiding stable strategies. Ranking ties and representative changes
can still matter; high family overlap must not erase true strategy changes.

Opt-in universe metadata exposes generated/retained counts, actual window/global
candidate-cap truncation, theoretical one-through-max-trips combinations, visited
states and `CURRENT_UNIVERSE_EXHAUSTED`. A true exhaustion flag requires no search
truncation and all theoretical states visited. It is deliberately conservative if
invalid smaller subsets prevent exploration. `GLOBAL_OPTIMUM` is always false.
The Phase 2C C408 experiment uses a 60-second external wall-clock ceiling; memory
is observed after completion, not claimed to be hard limited. Its full success
ends cap experiments for this fixed universe; next work is shortlist evidence.
