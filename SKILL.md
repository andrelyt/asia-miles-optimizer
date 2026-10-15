# Asia Miles Hybrid Award Optimizer — V1.1 Agent Playbook

**V1.1 kernel category:** deterministic comparison of supplied candidates. No live search, route generation, ticketability confirmation or booking.

1. Discover the project via AndreOS; read this file, README.md, the latest applicable `rules_*.json` and the itinerary JSON from GitHub. GitHub is code/rules Source of Truth; AndreOS stores references/checkpoints. CLI defaults to the latest zero-padded `rules_YYYY_MM.json`; use `--rules` to pin reproducible calculations.
2. Establish destinations, date flexibility, independent usable account balances, accepted home airports and minimum long/short-haul cabins. Dates are context only in V1.1. Never treat sample balances or fares as personal facts or live observations.
3. Supply explicitly sourced candidate tickets; the V1.1 CLI does not generate them. Supported schemes: `standard` (input miles), `standard_mixed` (two continuous one-way CX legs with distances and transfer_hours, route_type where applicable), `oneworld_multi` (rules-driven chart/constraints). Link award legs in trips using ticket_id; outbound and return mixed awards are separate tickets. Current oneworld rules prohibit W; J/Y uses whole-ticket highest cabin pricing.
4. Evaluate using `python3 -B optimizer.py --input <file> --rules <rules-file> --output <result.json> --csv <result.csv>`. Inspect errors and exit code; invalid results have null valued cost. Run `python3 -B -m unittest discover -p 'test_*.py' -v` when maintaining the project.
5. Link each cash flight/ground leg through cash_item_id to a cash_items id. Shared roundtrip/combined quotes count once. All amounts are HKD per person. Use null for unknowns, quote_type="quoted" only for observed quotes, otherwise assumption; taxes require taxes_quote_type too. Explain zero taxes when already included. Program cannot verify source authenticity or that an aggregate quote truly covers every leg.
6. Before comparing prices read cost_status, complete_price_comparison_eligible, missing_cost_components, assumed_cost_components, errors and warnings. COMPLETE_QUOTED/true means complete declared cash under the chosen miles valuation, not official final cost or ticketability. PARTIAL_LOWER_BOUND, ASSUMPTION, PARTIAL_ASSUMPTION and INVALID are not full-price comparable. With assumptions a number is not a guaranteed real-price lower bound.
7. CLI groups by category and ranks complete declared costs only within each category; partial/assumed rows preserve input order and invalid rows go last. Category is supplied by the caller. Do not describe this display order as a global recommendation, compare different cabin tiers as equal, or call a lower partial number the winner. If cost is missing, show a conditional/break-even comparison without inventing amounts. Keep the same miles valuation when comparing separate runs.
8. Read account_allocation_status: NOT_REQUIRED for no miles payable, NOT_CHECKED if not checked, FEASIBLE or INSUFFICIENT. Mathematical balance feasibility does not verify redemption nominee eligibility. Results do not access real accounts or pool balances. Each passenger is assumed to use the same itinerary.
9. Separately obtain external evidence for route operation, dates/order, stopovers/open jaws/city repeats, ticket validity, two seats, taxes and whole-ticket pricing. Program checks supplied counts/distances, not real-world chronology. Do not turn user-provided confirmation flags into independently verified evidence. Keep source URLs, observation dates and uncertainty in the report.
10. Report only meaningfully supported plans within cabin preferences; if there are fewer than three, do not fabricate candidates. Explain known miles/cash, missing costs, extra time and risks. Distinguish external evidence stages such as RULE_VERIFIED, ROUTE_EXISTENCE_CHECKED, MILES_PRICE_ESTIMATED, AWARD_SEATS_2_VERIFIED, CASH_QUOTED and AIRLINE_TICKETABLE; these are reporting labels, not automatic program attestations.

Rules JSON owns policy parameters. If a changed rule requests a new unsupported pricing algorithm, report the explicit error rather than inventing a price or reverting to old constants. Changing PE eligibility also needs W prices. Static charts and mixed-cabin proportional estimates never establish ticketability.

The V1.1 CLI does not perform discovery. Live availability, external service/API integration, global exhaustive optimization, reservation/issuance and UI remain outside V2 Alpha. Do not store login credentials or real account identifiers in shared code/Knowledge files; do not mutate AndreOS Canonical Memory.


## V2 development handoff

When asked to implement or extend V2, read `AGENTS.md`, `docs/V2_DESIGN.md`, `docs/V2_IMPLEMENTATION_PLAN.md`, the schemas and search config before coding. Treat those files as the current V2 Alpha design contract.

V2 discovery must feed candidates through the V1.1 deterministic kernel rather than reimplement pricing policy. Keep holiday status, route evidence, award-seat evidence and ticketability independent. An `ESTIMATED` holiday, `UNVERIFIED` route, unchecked award seat or theoretical multi-trip structure must never be silently upgraded by recommendation prose.

PR1 Holiday/Leave interfaces are documented in `docs/PR1_HOLIDAY_LEAVE.md`.
Use `generate_windows()` with schema-conforming requests and supplied calendar
snapshots; inspect diagnostics and holiday_uncertainty. Missing adjacent calendar
years and holiday anchors are explicit data gaps. Null destination/transit day
estimates must stay unknown until flights are supplied. Independent budgets are
checked per window, not as an annual portfolio. Synthetic TEST calendars must
never be described as actual official holiday announcements. PR1 itself does not implement route discovery; PR2 is documented below. PR3–PR4
remain unimplemented.


PR2 Route Graph / Standard Candidate Generator interfaces are documented in
`docs/PR2_ROUTE_CANDIDATES.md`. Supply a route snapshot, schema-conforming request
and an explicit rule snapshot; do not assume the newest rule filename is
applicable to future travel. Inspect directed-path/search diagnostics, individual
edge evidence and candidate requirements. The configurable longhaul distance
cutoff is a generation assumption, not award policy. Candidate prices/taxes stay
unknown; route evidence never verifies award seats, carrier redemption eligibility
or ticketability. Candidate IDs/order are deterministic, not a recommendation
ranking. Only airport destinations are resolved in PR2; missing geographic
resolution, multi-required destinations and repositioning must remain explicit
limitations. PR3 adaptation/pricing and PR4 orchestration remain deferred.

For PR2, inspect per-strategy `ticket_structure_rejections` and each ticket's
requirements/status. `standard_award_constraints` owns directional sector/transfer
and mixed-carrier limits independently of route-search config; absent/invalid
policy fails closed. CX + partner can remain pending agreement/quote; never infer
eligibility from that candidate. Two different non-CX carriers are excluded from a
single Standard ticket by the sourced policy, while separate awards may remain.
A partner mixed-cabin ticket's `proposed_scheme=null` requires PR3 review: do not
map it into the CX-only mixed formula. No PR2 candidate has a complete comparable
price. `VERIFIED` means supplied snapshot provenance only, not live or independent
route/seat/ticketability verification. Window endpoints are generation assumptions,
with schedule, overnight arrival and timezone/local-date checks NOT_CHECKED.
Muse/Grok FlyAsia research is THIRD_PARTY_OBSERVED; it must not override official
policy, partner eligibility, Category 2 or V1.1 rounding/pricing. Those reviews and
the adapter remain PR3 work.
