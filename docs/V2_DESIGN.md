# Asia Miles Optimizer V2.0 Alpha — Product & Architecture Baseline

Status: DESIGN BASELINE  
Baseline kernel: V1.1  
Purpose: turn supplied-candidate comparison into bounded candidate discovery plus holiday/leave planning without weakening deterministic validation.

## 1. Product question
V1.1 answers: **Given these candidate itineraries, how do they validate and compare?**

V2 answers: **Given travelers, leave budgets, holiday opportunities, origin flexibility, cabin preferences and destinations/regions, which travel windows and candidate award structures are worth checking?**

V2 is not a booking engine.

## 2. Architecture

```
Natural-language/user request
        |
        v
Travel Request (structured)
        |
   +----+------------------+
   |                       |
Holiday Engine          Award Discovery
   |                       |
Holiday calendar        Route graph
Leave windows           Strategy generators
   |                       |
   +----------+------------+
              v
       Planning Orchestrator
              |
              v
       Candidate -> V1 Adapter
              |
              v
       V1.1 evaluate()
              |
              v
       Evidence-aware Pruner
              |
              v
       Portfolio / Pareto views
```

### Ownership boundaries
- Holiday Engine owns calendar/leave arithmetic, not destination desirability.
- Route Graph owns route evidence, not award availability.
- Candidate Generator owns bounded structural exploration, not award pricing truth.
- V1.1 owns deterministic award/cost/account validation.
- Recommendation layer owns explanation and trade-off presentation, not hidden rule overrides.

## 3. Holiday & Leave Engine

### Supported holiday families
Default: new_year, qingming, labor_day, dragon_boat, national_day.
Optional: spring_festival, mid_autumn.

### Day types
PUBLIC_HOLIDAY, WEEKEND, MAKEUP_WORKDAY, WORKDAY, PERSONAL_DAY_OFF, BLOCKED_DAY.

Official calendar entries override generic weekday/weekend inference. A weekend marked MAKEUP_WORKDAY consumes leave unless the traveler has a personal override.

### Holiday evidence
`source_status`: OFFICIAL or ESTIMATED.
An ESTIMATED calendar may generate planning windows but all downstream recommendations retain an uncertainty flag. Never invent future makeup-workdays.

### Window generation
For each selected holiday:
1. Build a bounded date neighborhood.
2. Enumerate continuous windows within min/max trip length.
3. Count required leave separately per traveler.
4. Reject blocked dates or individual leave-budget breaches.
5. Record exact leave dates per traveler.
6. Pareto-prune windows dominated on equal-or-longer travel duration with no leave advantage.
7. Preserve several distinct windows when they represent meaningful pre-holiday/post-holiday trade-offs.

Track separately:
- calendar_trip_days
- estimated_destination_full_days
- estimated_transit_days
- leave_days_by_traveler
- leave_dates_by_traveler

Destination/transit day estimates must carry assumptions until actual flights are known.

## 4. Standard Award Generator — P0

Generate meaningful combinations, not just single-cabin tickets.

### Cabin patterns
- J/J
- J/Y for long/short segments
- W/Y for long/short segments
- W/W
- Y/Y baseline
- outbound J / return W
- outbound W / return J
- same-ticket mixed cabin where supported
- separate award tickets where beneficial

Hard minimum cabin and soft preferred cabin are separate inputs.

### Ticketing modes
- SINGLE_AWARD
- SEPARATE_AWARDS
- AWARD_PLUS_CASH
- AWARD_PLUS_GROUND

Do not assume mixed cabin saves miles. Standard mixed pricing and oneworld highest-cabin pricing are different adapters.

## 5. Route Graph

A route edge represents evidence that a service relationship exists or is hypothesized; it never represents award inventory.

Required edge concepts:
- origin / destination
- operating_carrier
- alliance
- distance_miles and distance source
- supported/observed cabins
- route_status: VERIFIED | STALE | UNVERIFIED
- source_url / observed_at / valid_from / valid_until when known

Alpha search bounds belong in config, not award rules.

A candidate containing UNVERIFIED edges may be retained as a discovery lead but cannot be labeled route-verified.

## 6. Candidate strategies

A. Standard awards: P0, including mixed cabin and separate-ticket combinations.
B. oneworld multi-carrier: P1 bounded structures; pricing remains V1.1 rule-driven.
C. Hybrid: P1 award + cash/ground repositioning.
D1. Holiday Portfolio: P1 choose trips across holidays under annual leave/miles budgets.
D2. Multi-trip Award: P1 theoretical structures combining separate trips; default ticketability NEEDS_AIRLINE_VALIDATION.

Holiday portfolio quality and multi-trip ticketability are separate questions.

## 7. Candidate lifecycle

```
GENERATED
  -> PRECHECK_FAILED
  -> PRECHECK_PASSED
  -> V1_INVALID
  -> V1_VALID
  -> ROUTE_VERIFIED (only if all required edges verified)
  -> EVIDENCE_PENDING
```

Evidence dimensions remain independent:
- holiday_status
- route_status
- pricing_status
- award_seat_status
- ticketability_status

Do not collapse them into a single confidence score.

## 8. Ranking

First gate by validity/evidence; then compare only genuinely comparable dimensions.

Primary objective views:
- Miles Saver
- Comfort First
- Balanced
- Leave Efficient

Use Pareto dominance where inputs are comparable. Unknown taxes/cash cannot be treated as zero. Incomplete or assumed costs cannot strictly dominate a complete quoted cost solely because their visible numeric value is lower.

Do not start Alpha with one opaque weighted score. Preserve trade-offs.

## 9. Annual portfolio

Input may specify annual leave budget independently for each traveler and max trips/year.

For each holiday, generate Top-N viable trip candidates. Use bounded enumeration/dynamic programming across holidays, reject overlapping trips and budget breaches, then Pareto-prune annual portfolios.

Potential dimensions:
- total miles by account
- leave used by traveler
- number of long/short-haul trips
- known cash
- cabin utility
- reposition/transit burden
- evidence completeness

## 10. Rules versioning

A future trip must not blindly use the latest filename.

Rules need applicability metadata capable of distinguishing:
- booking/ticketing effective dates
- travel effective dates
- verification status

If applicable rules cannot be determined, return RULE_VERSION_REVIEW_REQUIRED rather than silently pricing with an uncertain version.

## 11. Alpha acceptance

Alpha is acceptable only if:
- V1.1 regression tests remain green.
- official/estimated holiday states are preserved end-to-end.
- makeup workdays affect leave correctly.
- two travelers' leave budgets are independent.
- generator creates multiple standard award cabin/ticketing patterns without user-supplied scenarios.
- candidates adapt into V1.1 rather than reimplement pricing.
- unverified route/seat/ticketability evidence is never upgraded implicitly.
- same snapshot/input yields deterministic output.
- insufficient data produces an explicit reason, not fabricated candidates.

## 12. Deferred
Live award-seat search, live cash/tax APIs, booking, login/account integration, global exhaustive graph search, UI, and unsupported alternative award pricing algorithms are post-Alpha.


## Phase 2B-2 approved reference-planning extension

An explicit supplied secondary-corroborated reference profile may support separate
planning estimates without resolving the official applicability gate. The original
gate is retained in official_pricing_status. Estimate and quote fields, evidence
levels, planning-only Pareto, and estimated versus confirmed budget statuses are
kept distinct; see [REFERENCE_CHART_ESTIMATE.md](REFERENCE_CHART_ESTIMATE.md).
Default behavior and V1.1 pricing arithmetic remain unchanged. Estimated budgets
cannot be labeled CONFIRMED_BUDGET_FEASIBLE, including older mixed-cabin estimates.
