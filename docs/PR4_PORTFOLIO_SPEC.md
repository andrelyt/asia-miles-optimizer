# V2 Alpha PR4 — Annual Holiday Portfolio & Planner CLI
Status: IMPLEMENTATION SPEC / REVIEW REQUIRED
Date: 2026-10-15
Baseline: main after PR3 merge a5e431ca01797a0d33b48b8ab49b91f4f86aea81

## 1. Product decision
Choose a bounded portfolio of 1..max_trips distinct holiday trips for the SAME traveler group, not the cheapest standalone itinerary. Show multiple nondominated alternatives with explainable tradeoffs. No opaque universal score.

PR4 is **D1 annual holiday portfolio**. It is NOT D2 multi-trip award ticket construction, partner ticket pricing, live availability, or booking.

## 2. Inputs and orchestration
Use PR1 holiday windows, PR2 candidates and PR3 price_candidate outcomes; reuse their actual current interfaces, not imagined shapes. New discovery/portfolio.py with pure function(s), planner.py CLI and tests. Read existing schemas, AGENTS.md, SKILL.md and PR3 pricing docs before implementation. Accept bounded supplied route graph, holiday calendar, travel request, versioned rules, optional per-candidate supplied pricing evidence, explicit payment account balances, and search limits. Do not create airline quotes or fabricate official holiday data. Existing travel_request.schema.json already has max_trips and individual annual_leave_budget. Prefer an optional PR4-specific config/schema for portfolio settings over breaking existing V1/PR1–PR3 input contracts.

Candidate groups must share the same traveler IDs; don't silently mix different passenger parties. Distinct candidates for the same window are alternatives, not separate trips.

## 3. Hard constraints
- 1 <= trips <= max_trips; enforce an explicit bounded cap on combinations/states.
- No overlapping calendar intervals; handle inclusive start/end and cross-year correctly. For unknown dates, mark unresolved and exclude from confirmed portfolios.
- Per-traveler annual leave: union of exact leave dates over selected trips, then count by **leave date's calendar year** against that year's explicit budget. No counting duplicated dates twice. Reject if year budget absent; do not implicitly reuse 2026 allowance for 2027. For a single planning-year-only request, either restrict portfolios to that year or demand explicit per-year leave budgets for cross-year windows; never silently charge all days to one year.
- Per-payment-account annual mileage spend must be feasible across ALL selected trips, not each trip separately. Account-to-passenger allocation can differ by trip; do not sum per-trip FEASIBLE flags as proof. Respect indivisible ticket/passenger allocation semantics of existing V1.1; preserve unknown balances as unknown, and do not pool accounts.
- A portfolio with any UNKNOWN miles, missing rule applicability, partner quote, missing payment account balance or unresolved funding eligibility cannot be classified as **CONFIRMED_BUDGET_FEASIBLE**. It may appear in CONDITIONAL leads with explicit missing evidence.
- Keep hard cabin minima, request blocked dates, valid ticket structures and candidate travel window constraints. A PR3 outcome UNSUPPORTED/invalid must not become a feasible trip.

## 4. Status channels
Emit two disjoint result groups:
A. `budget_feasible`: all annual leave and miles amounts are known, account allocation is feasible across portfolio, and structural/rule checks pass. This label means only *budget* feasibility, not award availability, route schedule or ticketability.
B. `conditional`: structurally plausible, leave-feasible combinations with unknown mileage, unconfirmed partner eligibility, rule review pending, unknown balances, etc. Include blockers and required next evidence; NEVER claim budget feasible.
Invalid/overbudget portfolios go to diagnostics/rejection counts, not recommendations. Explicitly retain holiday_status, route_status, pricing_status, award_seat_status and ticketability_status; don't upgrade VERIFIED snapshot to bookable. Even A can have NOT_CHECKED seats/ticketability.
No unknown numeric field should be converted to 0. Known mile subtotals are lower bounds, not complete totals. Taxes unknown => null and no complete-cost ranking.

## 5. Optimization and diversity
Portfolio dimensions:
- number of trips, travel calendar days and estimated destination full days (if known);
- leave days used by traveler (minimize), leave efficiency (only when denominator valid);
- total miles by account and total miles (minimize only when all tickets quoted/estimable under supported rules; mark mixed estimates separately from quoted);
- long-haul cabin experience/comfort (deterministic, documented ordinal metric from legs, no invented flight durations);
- transfers/sector/reposition burden from observed structure, not fabricated travel time;
- holiday, route and price evidence completeness as categorical flags (not a single numeric confidence).
Pareto dominance only within compatible comparison classes: confirmed vs conditional separate; quoted vs estimated cost never silently treated equivalent; unknown cash cannot dominate known cash; no strict price comparisons when taxes unknown. Maintain deterministic stable portfolio IDs and ordering; prune only when genuine dominance is provable.
Offer 4 **views** as transparent filters/orderings, not hidden weighted sums: Miles Saver, Comfort First, Balanced, Leave Efficient. A portfolio may appear in multiple views. Balanced uses nondominated diversity, not arbitrary weighted total.
Limit each view's count and total enumerated states via config; include truncation flag and diagnostics. Keep materially different holiday families, trip counts and cabin mixes when possible.

## 6. Account and evidence semantics
Do not infer spendable account balances from traveler.miles_balance; PR3 requires explicit balances_by_account. Never treat PR3's per-trip account_allocation as a globally valid annual allocation. Funding/beneficiary eligibility remains NOT_CHECKED even if numeric allocation succeeds. Allow externally supplied rule applicability review per candidate; if absent retain RULE_VERSION_REVIEW_REQUIRED, don't manufacture it.
A quote/evidence object is only caller supplied; source_url format alone is not official verification. Explicitly retain SUPPLIED_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED. Travel dates based on window endpoints are planning assumptions, not confirmed schedules.

## 7. CLI
planner.py accepts a documented JSON input file with paths/objects to synthetic/test calendar, route graph, request, rules, config and optional evidence/account snapshots. No network access. JSON output includes input snapshot metadata, budget_feasible, conditional, rejected summary, four views, deterministic IDs, per-traveler leave-by-year, account allocation, total known miles and unknown fields, evidence flags, missing_data, and search_truncated. Exit nonzero on invalid input. Provide sample synthetic invocation. No personal balances or credentials committed.

## 8. Mandatory regression cases
- 193 prior tests pass (Codex-reported baseline; run to verify).
- 2 travelers, independent leave budgets; overlapping trips; adjacent nonoverlap; same holiday alternate windows; blocked dates; makeup workday; cross-year with and without explicit next-year leave budget.
- max_trips 1/2/3; no candidate and no feasible portfolio; stable ordering/IDs under input permutation; duplicate candidate and duplicate trip selection.
- per-trip affordable but annual total exceeds account balance; indivisible ticket assignment across accounts; unknown/partial balances; one payer funding both passengers with eligibility still unchecked.
- one known + one unknown miles, partner quote pending, 2027 rule review pending, missing tax, mixed cabin estimate, quoted Standard, stale route, estimated holiday; no false completeness or bookability.
- Pareto strict dominance vs incomparable unknown/estimated costs; 4 view diversity; search truncation and boundedness.
- synthetic PR1→PR2→PR3→PR4→planner CLI end-to-end; deterministic JSON replay; V1.1 regression unchanged.

## 9. Scope control / delivery
Do not change optimizer.py, pricing rounding, official award rules, PR1–PR3 behavior, existing schemas without explicit justification, or build D2 multi-trip award structure. Do not add external dependencies, scrape live availability or generate fake prices.
New branch codex/v2-alpha-pr4-portfolio, new PR, do not merge. Run full `python3 -B -m unittest discover -p 'test_*.py' -v`. Report tests before/after, changed files, CLI example, boundedness settings, conditional/confirmed examples, SHA, PR URL, known limitations and merge readiness.
