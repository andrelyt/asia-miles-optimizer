# V2 Alpha — Real-world Validation Plan (2027 May Day / National Day)
Status: VALIDATION PLAN, NOT A VERIFIED TRAVEL RESULT
Prepared: 2026-10-15
Baseline: main PR4 squash e38f6c8aed8f1c494042ee3c061d3b4bc15ebaa1

## Goal and non-goals
Evaluate whether PR1→PR2→PR3→PR4 produces useful 2027 annual holiday travel *leads* for two travelers, not whether award seats can be booked. Do not change the core algorithms until failure modes are documented. No fabricated airline routes, 2027 official makeup workdays, mileage quotes, account balances, eligibility or flight schedules.

## User scenario — preferences, not verified availability
- Year 2027; holiday families labor_day and national_day; 1–2 weeks per long-haul trip; maximum 2 annual trips for the first pass, optionally compare 1 and 3.
- Same two travelers for all trips. Origin HKG preferred; SZX/CAN and PVG/TPE possible reposition alternatives only when explicitly supplied with real route evidence. Do not treat five airports as costless equivalent home airports.
- Long-haul W minimum / J preferred; short-haul Y minimum; mixed cabins and separate awards may be explored, but price/status gates remain unchanged.
- Destination **candidates for discussion** (not routes or asserted CX services): North America western national parks, Japan/Hokkaido, New Zealand, Northern Europe, Patagonia, and other user-approved destinations. Prior visits to Milan/Dolomites/Rome/London/Paris inform novelty preferences but are not automatically excluded.
- No invented leave or miles: schema-required `travelers[].miles_balance=0` is only a schema placeholder and is **not** a payment account. If balances_by_account is absent, remain conditional. Never use this placeholder for funding.
- Need user-provided annual leave per traveler, annual available account balances and beneficiary eligibility before any budget-feasible classification. No account credentials, membership IDs or identifying data in committed fixtures.

## Evidence ladder
1. Calendar: official 2027 State Council notice if available, otherwise ESTIMATED only. Statutory holiday minimum is NOT the final makeup-workday schedule. Keep an explicit snapshot date and source.
2. Routes: only sourced directed edges with operating carrier, cabins, observed_at, and source_url; availability, actual 2027 operating dates and timezones NOT_CHECKED. Prefer small audited graph over large guessed graph.
3. Pricing: real candidate-bound airline mileage quote and tax quote only if actually obtained. No extrapolated CX Standard award miles. Partner quotes stay pending under PR3 rules. For 2027, explicit applicability review required, not inferred from 2026 chart.
4. Accounts: explicit nonnegative balances_by_account and separately sourced payer/beneficiary eligibility. Do not pool accounts.
5. Seats and ticketability: NOT_CHECKED until a future live verification stage, even for budget-feasible outputs.

## Validation runs
A. Pipeline smoke test: existing synthetic fixture. Label SYNTHETIC_TEST; deterministic replay; no user-facing travel recommendation from this data.
B. Real preference + no verified quotes/accounts: supplied 2027 estimated calendar and small audited route graph, omit quote evidence and balances. Expect conditional only; no fake mileage total; complete_price_comparison_eligible=false; NOT_CHECKED seats/ticketability.
C. Verified-evidence subset: only if user/airline supplies candidate-bound evidence; test 1 trip vs 2 trips, per-traveler leave, independent account allocation, different holiday windows and four views. Do not elevate user-supplied evidence to independently verified.
D. Sensitivity: HKG only vs HKG+reposition airports; W vs J long-haul minimum; max_trips=1/2; per-window and global cap increases; compare IDs, diversity, search_truncated and runtime.

## Scorecard / acceptance
- Input coverage: official/estimated calendar, audited route edge count, quote coverage, tax coverage, account completeness and rule review coverage.
- Correctness: no invalid leave or miles funding, no same-holiday double-booking, no price unknown→zero, no confirmed budget on missing eligibility, no seat/booking claims.
- Usefulness: number of distinct destinations, long-haul cabin classes, genuinely different pre/post-holiday windows, and feasible 1 vs 2 trip tradeoffs. Include actual total leave dates by traveler/year.
- Explainability: each recommendation identifies its constituent trip IDs, dates, known miles/unknowns, cash completeness, account allocations or blockers, and search caps.
- Stability: replay identical inputs exactly; vary caps to expose truncation and recommendation instability. Any output dependent on unverified assumptions must remain visibly conditional.
- Pass/Fail: never judge a conditional-only real-world run as 'no travel options'. Distinguish no routes, no priced tickets, no verified availability, and true annual budget infeasibility.

## First-run deliverables
1. `validation/2027_preference_profile.example.json`: clearly labeled USER_PREFERENCE_DRAFT (no real financial data); must not be passed directly as a complete planner input without calendar/route evidence.
2. `validation/2027_evidence_manifest.example.json`: a checklist/manifest with fields status, source_url, observed_at, applicable dates, evidence level; null for missing.
3. `validation/2027_runbook.md`: exact CLI commands for synthetic smoke test, and real evidence assembly once sourced.
4. `validation/2027_scorecard.md`: results table distinguishing RUN / BLOCKED / NOT_RUN; do not claim tests or runs not actually performed.
5. A final short list of user inputs needed: annual leave days for each traveler; spendable miles in each account; acceptable 2027 holiday windows; preferred destination shortlist; willingness to reposition and acceptable cabin minimum.

## Gate
Do not make a PR5 feature change as part of this phase. Commit documentation or non-sensitive example manifests only if needed. Do not create official-looking 2027 calendars or airline price/route snapshots. Keep all real results labeled by evidence status and source.
