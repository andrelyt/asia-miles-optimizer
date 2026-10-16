# Phase 2D — Shortlist Evidence Verification

**SHORTLIST EVIDENCE TRIAGE · NOT BOOKABLE · NO AUTHENTICATED AWARD INVENTORY · NO AIRLINE QUOTE**

## Execution and scope

Execution main: `f0d324c55daba0387d7ffd8d736f25ac429643f2`; public observation date **2026-10-16 (Asia/Shanghai)**, session 01:40–02:00 UTC. Initial checkout clean, Python 3.9.6. Read AGENTS.md, README.md, SKILL.md, the Phase 2C contract/report and committed best_representative metadata. GitHub is the code/evidence source of truth.

Only this report and its machine-readable metrics are added. No runtime module, algorithm, schema, rule, rounding, reference profile, prior validation evidence or personal data changed. No C100/C200/C408 run. No new optimizer phase, login, credential access, purchase or booking. No automatic monitoring task created.

Baseline and final full suite both **327 passed / 0 failed / 0 errors**. Command: `python3 -B -m unittest discover -p 'test_*.py' -v`. No production code was added, so no new unit tests. Fifteen separate artifact consistency assertions check reuse, status separation, no pooling, low buffer, savings and privacy-related invariants; they are not counted as unit tests.

## Evidence reuse graph and minimum query set

Seven families contain ten trip occurrences and twenty directional/cabin obligations before deduplication. The complete requirement graph has **16 unique direction/date/cabin leaves**, **12 direction/date schedule nodes**, **six roundtrip date packets**, and **four route/product bundles**. Query IDs and family edges are explicit in JSON.

This is the minimum complete packet set under these packet semantics: each packet contains at least one dated requirement that no other packet can satisfy. A packet is a research work item, not a claim that one HTTP request verifies both directions and all cabins. Four route bundles allow product/reference reuse; three broad bundles AKL/SYD/CTS merely touch all seven families and leave ZRH unverified, so that is not a complete evidence cover.

| Packet / priority | Route and exact primary dates | Cabin requirements | Family numbers reached |
|---|---|---|---|
| P1 / P1 | HKG↔AKL, 2027-04-24 / 2027-05-02 | J | 3 |
| P2 / P1 | HKG↔AKL, 2027-09-25 / 2027-10-03 | J | 4 |
| P3 / P2 | HKG↔ZRH, 2027-09-25 / 2027-10-03 | W | 6 |
| P4 / P3 | HKG↔SYD, 2027-04-24 / 2027-05-02 | J / W | 5, 7 |
| P5 / P4 | HKG↔CTS, 2027-04-24 / 2027-05-02 | Y | 1, 2, 6 |
| P6 / P4 | HKG↔CTS, 2027-09-25 / 2027-10-03 | J / Y | 2, 3 |

Reuse: CTS May Y supports #1/#2/#6; CTS October Y/J shares one schedule pair across #2/#3, but Y and J inventory remain different. SYD shares two schedule nodes across #5/#7, but needs four directional cabin checks. AKL J product/reference evidence supports #3/#4, while May and October schedules/seat checks remain separate. ZRH W belongs to #6. Quotes, taxes, dates, operators and two-seat inventory never inherit from a generic product page.

No DATE_FLEX search was added. The timetable UI displays a surrounding week; only exact primary-date cells were transcribed. A timetable cell’s commercial availability label is not an award observation. Initial SYD/CTS page attempts stalled; one public-page reload recovered results. Failed/stale/loading views were not treated as absence evidence.

## Dated public schedule observations

Source: [Cathay public timetable](https://www.cathaypacific.com/cx/en_HK/book-a-trip/timetable.html), queried manually in an unauthenticated browser, with each outbound/return tab inspected. All times below are local; +1 means arrival on the next local calendar date. Status is **SCHEDULE_PUBLISHED**, not an operated-flight confirmation. The site omits full flights, so missing results cannot establish route cancellation or no award inventory.

| Departure date | Direction | Flight / actual operator | Departure → arrival | Duration | Published aircraft | Target CX schedule |
|---|---|---|---|---|---|---|
| 2027-05-02 | AKL→HKG | CX198 / Cathay Pacific | 13:25→21:05 | 11h40 | Airbus A350 | SCHEDULE_PUBLISHED |
| 2027-10-03 | AKL→HKG | CX7402 / Air New Zealand | 11:15→17:45 | 11h30 | Boeing 787 | SCHEDULE_UNKNOWN |
| 2027-05-02 | CTS→HKG | CX581 / Cathay Pacific | 16:40→20:55 | 5h15 | Not separately captured | SCHEDULE_PUBLISHED |
| 2027-10-03 | CTS→HKG | CX581 / Cathay Pacific | 16:40→20:55 | 5h15 | Boeing 777 | SCHEDULE_PUBLISHED |
| 2027-04-24 | HKG→AKL | CX113 / Cathay Pacific | 21:10→11:50 +1 | 10h40 | Airbus A350 | SCHEDULE_PUBLISHED |
| 2027-09-25 | HKG→AKL | CX7401 / Air New Zealand | 19:15→10:50 +1 | 10h35 | Boeing 787 | SCHEDULE_UNKNOWN |
| 2027-04-24 | HKG→CTS | CX580 / Cathay Pacific | 09:15→15:20 | 5h05 | Boeing 777 | SCHEDULE_PUBLISHED |
| 2027-09-25 | HKG→CTS | CX580 / Cathay Pacific | 09:15→15:20 | 5h05 | Boeing 777 | SCHEDULE_PUBLISHED |
| 2027-04-24 | HKG→SYD | CX181 / Cathay Pacific | 00:45→11:45 | 9h00 | Airbus A350 | SCHEDULE_PUBLISHED |
| 2027-04-24 | HKG→SYD | CX139 / Cathay Pacific | 09:10→20:10 | 9h00 | Airbus A350 | SCHEDULE_PUBLISHED |
| 2027-04-24 | HKG→SYD | CX111 / Cathay Pacific | 19:05→06:10 +1 | 9h05 | Airbus A350 | SCHEDULE_PUBLISHED |
| 2027-04-24 | HKG→SYD | CX161 / Cathay Pacific | 21:35→08:40 +1 | 9h05 | Airbus A350 | SCHEDULE_PUBLISHED |
| 2027-09-25 | HKG→ZRH | CX383 / Cathay Pacific | 00:25→07:30 | 13h05 | Airbus A350 | SCHEDULE_PUBLISHED |
| 2027-05-02 | SYD→HKG | CX110 / Cathay Pacific | 07:40→15:10 | 9h30 | Not separately captured | SCHEDULE_PUBLISHED |
| 2027-05-02 | SYD→HKG | CX162 / Cathay Pacific | 10:10→17:45 | 9h35 | Not separately captured | SCHEDULE_PUBLISHED |
| 2027-05-02 | SYD→HKG | CX100 / Cathay Pacific | 14:05→21:30 | 9h25 | Not separately captured | SCHEDULE_PUBLISHED |
| 2027-05-02 | SYD→HKG | CX138 / Cathay Pacific | 21:55→05:10 +1 | 9h15 | Not separately captured | SCHEDULE_PUBLISHED |
| 2027-10-03 | ZRH→HKG | CX382 / Cathay Pacific | 13:30→06:55 +1 | 11h25 | Airbus A350 | SCHEDULE_PUBLISHED |

The table records selected nonstop options relevant to the strategies, not an exhaustive flight list. Swiss/JAL connecting or codeshare alternatives displayed in ZRH/CTS searches were excluded from CX-only reference pricing. For October AKL, only NZ-operated CX7401/CX7402 were observed: their timetable is published, but the **target CX-operated schedule remains SCHEDULE_UNKNOWN**. This is not proof that no CX flight will operate, and is not NO_SEAT_OBSERVED.

### Cabin evidence and temporal scope

- May AKL and October ZRH publish Airbus A350 aircraft-family links. [CX A350-900](https://www.cathaypacific.com/cx/en_HK/flying-with-us/aircraft-and-fleet/airbus-a350/900.html) and [A350-1000](https://www.cathaypacific.com/cx/en_HK/flying-with-us/aircraft-and-fleet/airbus-a350/1000.html) product/configuration pages support J/W cabin plausibility. SYD outbound also publishes A350; its J/W route product is corroborated by [Cathay’s Sydney cabin announcement](https://news.cathaypacific.com/cathay-pacific-s-highly-anticipated-aria-suite-takes-business-to-new-heights-in-australia-w2llcd).
- CTS publishes Boeing 777 on the captured outbound dates and October return. [The official 777 product page](https://www.cathaypacific.com/cx/en_HK/flying-with-us/aircraft-and-fleet/boeing-777/300.html) supports J/Y existence. No CTS lie-flat/Aria promise is made. May CTS return and SYD return aircraft were not separately transcribed, so their aircraft fields remain null.
- Aircraft family/product compatibility is **REFERENCE**, not a final date-specific tail/cabin-sale attestation. Exact variants and substitutions can change. No query has CONFIRMED cabin inventory or two confirmed award seats. October AKL CX cabin-on-schedule is UNKNOWN because only NZ operation was seen; do not substitute an NZ cabin into the CX formula.

### Schedule effects on leave and trip duration

1. AKL May: CX113 arrives April 25 at 11:50, one day after the April 24 departure. The nine-day window is not nine destination days. The October CX operation gap prevents simply reusing May’s schedule for #4.
2. ZRH: CX383 departs HKG at 00:25 on September 25; airport positioning may need the previous evening. CX382 departing October 3 arrives HKG **October 4 at 06:55**, beyond the Phase 2C end date. Taking the full arrival day off could raise the annual leave assumption for #6 from nine to ten each (still within 15/13), but home/work positioning and 2027 makeup days are unknown. This is an impact warning, not a validated new leave result; original inputs and counts remain untouched.
3. SYD: CX139 offers a same-local-day outbound arrival, while CX111/CX161 arrive the next morning. Return daytime options reach HKG May 2; CX138 reaches HKG May 3. Selecting the latter can change leave and destination full days. Do not silently choose the overnight option while retaining the original end date.

## Pricing, seats, taxes and funding remain independent

All 16 cabin queries retain **RULE_ESTIMATED**, `airline_quoted_miles=null`, and **RULE_VERSION_REVIEW_REQUIRED**. The [official flight award chart page](https://flights.cathaypacific.com/en_HK/redeem-flights/flight-award-chart.html) sends Standard pricing to the redemption search; its visible upgrade chart is not a Standard award quote. No route-specific dated airline-published Standard price was obtained. Promotional economy prices for other dates/cabins were not imported. Third-party reconstructions remain references and cannot upgrade quote/seat/ticketability.

[The redemption entry](https://www.cathaypacific.com/cx/en_HK/book-a-trip/redeem-flights/redeem-flight-awards.html) displays a sign-in requirement. **AUTHENTICATED_AWARD_INVENTORY_NOT_ACCESSIBLE** in this session. Every seat status is **NOT_CHECKED**, with inventory checked_at=null. There are zero SEAT_CONFIRMED_1/2 or NO_SEAT_OBSERVED observations. If a later logged-in search finds no seats, it must record exact checked_at, passengers, dates, cabins and source; NO_SEAT_OBSERVED never means NO_AWARD_EXISTS.

All target-date tax totals remain **UNKNOWN / null**, not zero. [The public fuel-surcharge notice](https://www.cathaypacific.com/cx/en_HK/latest-news/other-news/fuel-surcharge-updates.html), updated October 15, currently lists Hong Kong-origin CX-sector components of HKD1,362 for the relevant longhaul region and HKD339 for other sectors. These are only **REFERENCE_TAX components**, are periodically revised, depend on journey origin/carrier, exclude other taxes, and do not establish 2027 award tax totals. No amount enters a portfolio total.

Original own-account funding math remains **USER_REPORTED_APPROXIMATE / ESTIMATED_BUDGET_FEASIBLE**. Accounts are independent, spending cumulative, no pooling. There is no verified balance, funding-beneficiary eligibility or confirmed-budget upgrade. No balance values or account identifiers are copied to the new JSON.

## SYD directional cabin comparison

| Out / back | Reference miles per person | Saving vs J/J |
|---|---:|---:|
| J/J | 120k | 0k |
| J/W | 99k | 21k |
| W/J | 99k | 21k |
| W/W | 78k | 42k |

These are separately priced directional awards under the unchanged reference chart, not a new same-ticket mixed formula. Actual award cabins and final quote remain unobserved. With daytime and overnight flights in both directions, route direction alone cannot identify the better use of J; personal sleep/comfort preferences and selected flight times are missing. No jetlag/health benefit is inferred. **DIRECTIONAL_J_PREFERENCE_UNRESOLVED**; #5 and #7 remain distinct alternatives rather than an invented winner.

## AKL / ZRH / SYD decision comparison

| Dimension | AKL | ZRH | SYD |
|---|---|---|---|
| Reference miles/person | J/J 182k; #3 annual 248k | W/W 104k; with CTS Y/Y 130k | J/J 120k; J/W or W/J 99k; W/W 78k |
| Cabin strategy | J/J, May versus October operation must stay separate | W/W, A350 product reference | J/W or W/J, direction unresolved |
| Original leave | October-only four days; #3 annual nine | Annual #6 nine; next-day return needs recheck | Five days; selected night return can alter end date |
| Approx funding | Only math; #3 VERY_LOW_BUFFER | Original annual math feasible; not confirmed | Original math feasible; not confirmed |
| Schedule | May CX published; October only NZ codeshare observed | CX383/CX382 published; overnight HKG return | Four nonstop choices each direction published |
| Seat evidence | NOT_CHECKED | NOT_CHECKED | NOT_CHECKED |
| Tax evidence | Total UNKNOWN | Total UNKNOWN | Total UNKNOWN |
| Main evidence risk | Operator gap in October; #3 buffer | Arrival-day/positioning/calendar; W inventory | J/W seats and timing choice; final quote |

No subjective destination-quality score is added. CTS is a PRIMARY_TRIP only for #1’s low-cost objective; in the annual combinations it is a LOW_COST_COMPLEMENT. Low mileage is not evidence that CTS is the best destination. Repeating CTS twice (#2) needs an explicit travel-value/preference decision, not automatic promotion from the mileage ranking.

## Family readiness and verdicts

Each dimension uses CONFIRMED / REFERENCE / UNKNOWN / CONFLICTING independently. Published future schedules are REFERENCE in this readiness scale, even when their schedule facet is SCHEDULE_PUBLISHED. No scalar percentage hides unknowns.

| # | Family | Pricing | Schedule | Cabin | Seat | Tax | Funding | Calendar | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `1_TRIPS\|MAY:CTS:Y-Y` | REFERENCE | REFERENCE | REFERENCE | UNKNOWN | UNKNOWN | REFERENCE | REFERENCE | **PROMOTE_TO_MONITOR** |
| 2 | `2_TRIPS\|MAY:CTS:Y-Y\|OCT:CTS:Y-Y` | REFERENCE | REFERENCE | REFERENCE | UNKNOWN | UNKNOWN | REFERENCE | REFERENCE | **KEEP_FOR_VERIFICATION** |
| 3 | `2_TRIPS\|MAY:AKL:J-J\|OCT:CTS:J-J` | REFERENCE | REFERENCE | REFERENCE | UNKNOWN | UNKNOWN | REFERENCE | REFERENCE | **DOWNGRADE** |
| 4 | `1_TRIPS\|OCT:AKL:J-J` | REFERENCE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | REFERENCE | REFERENCE | **KEEP_FOR_VERIFICATION** |
| 5 | `1_TRIPS\|MAY:SYD:J-W` | REFERENCE | REFERENCE | REFERENCE | UNKNOWN | UNKNOWN | REFERENCE | REFERENCE | **PROMOTE_TO_MONITOR** |
| 6 | `2_TRIPS\|MAY:CTS:Y-Y\|OCT:ZRH:W-W` | REFERENCE | REFERENCE | REFERENCE | UNKNOWN | UNKNOWN | REFERENCE | REFERENCE | **PROMOTE_TO_MONITOR** |
| 7 | `1_TRIPS\|MAY:SYD:W-J` | REFERENCE | REFERENCE | REFERENCE | UNKNOWN | UNKNOWN | REFERENCE | REFERENCE | **PROMOTE_TO_MONITOR** |

- **PROMOTE_TO_MONITOR #1, #5, #6, #7**: four families / three decision branches (CTS baseline, SYD asymmetric alternatives, CTS+ZRH annual). Published CX schedules and product compatibility justify spending time on seats/quotes next. #6 additionally needs the recorded arrival-day leave/positioning recheck; no final annual feasibility is certified.
- **KEEP_FOR_VERIFICATION #2**: valid low-mileage repeated-CTS option, but whether two CTS trips meet travel goals remains unconfirmed. No route or seat-based elimination.
- **KEEP_FOR_VERIFICATION #4**: October AKL-only retains potential, but the public results did not establish CX operation. Obtain an operator-specific schedule or partner redemption agreement/quote before using the current CX-only estimate.
- **DOWNGRADE #3**: **MILEAGE_BUFFER_RISK / VERY_LOW_BUFFER**. The 248k/person annual estimate leaves Traveler B roughly 2k under the approximate scenario. That cannot be treated like AKL-only 182k: a small quote change or balance error can reverse feasibility. This is a funding-margin decision, not a claim that J seats do not exist.
- **ELIMINATE: none**. NOT_CHECKED seats, missing CX display and unknown taxes are not grounds for asserting impossibility.

## Minimum next manual Cathay work

One authenticated session can in principle execute **four roundtrip single-cabin two-adult searches** for the four promoted families (eight directional/cabin observations). This lower bound assumes the UI returns both directional results for the specified cabin; a one-way-only workflow needs eight. Final separate-ticket quotes, taxes, funding authorization and ticketability may require additional steps. No guarantee about UI call count or availability is made.

| Destination | Cabin | Depart / return | Adults | Reuse |
|---|---|---|---:|---|
| CTS | Y | 2027-04-24 / 2027-05-02 | 2 | #1/#6 |
| SYD | J | 2027-04-24 / 2027-05-02 | 2 | #5/#7 |
| SYD | W | 2027-04-24 / 2027-05-02 | 2 | #5/#7 |
| ZRH | W | 2027-09-25 / 2027-10-03 | 2 | #6 |

Full coverage of all seven families would require at least eight such roundtrip/cabin searches, or sixteen one-way cabin checks. The six public research packets are not six award-seat checks. Start with the four promoted families; do not mechanically run all sixteen leaves. If October AKL is reconsidered, resolve the operator/eligibility gap first. User login is needed; no credentials or personal account screenshots should enter public artifacts.

Recommend **Phase 2E bounded manual award availability monitoring** for these four families / three branches. Keep J/W vs W/J unresolved until dated two-seat observations. Record checked_at and source for every inventory observation, then obtain final quotes/taxes and verify each own-account budget. No BOOK NOW, no BOOKABLE_OBSERVED and no confirmed funding claim.

## Safety, tests and acceptance

- **PASS** — reuse_graph_complete.
- **PASS** — duplicate_queries_collapsed.
- **PASS** — family_aggregation_complete.
- **PASS** — unknown_seat_does_not_eliminate.
- **PASS** — no_seat_observed_requires_timestamp.
- **PASS** — quote_precedes_reference_within_scope.
- **PASS** — unknown_tax_not_zero.
- **PASS** — very_low_buffer_retained.
- **PASS** — independent_account_policy_preserved.
- **PASS** — mixed_savings_consistent.
- **PASS** — j_w_and_w_j_separate.
- **PASS** — schedule_independent_of_seat.
- **PASS** — seat_independent_of_price.
- **PASS** — promote_not_bookable.
- **PASS** — official_source_scope_not_historical_substitution.

The negative-seat timestamp assertion is vacuous in this run because no inventory observation was made. Quote-over-reference and official-source precedence are stated review rules, not a newly implemented runtime adapter. No evidence result is fed back into optimizer schemas or original UNVERIFIED route snapshots. Manual review checks source scope, date/operator binding, no inferred inventory, unchanged kernel/rules and public-artifact privacy.

**Phase 2D triage acceptance: PASS. Booking readiness: NOT VERIFIED.** Four families are prioritized without pretending that unknown evidence is confirmed. Two continue verification, one is downgraded, none eliminated. Rule applicability, final calendar/makeup days, exact cabin configurations, two award seats, airline quotes, complete taxes, verified balances/eligibility and ticketability remain unresolved.

## Source register

- [CX_TIMETABLE](https://www.cathaypacific.com/cx/en_HK/book-a-trip/timetable.html) — checked 2026-10-16; Published commercial timetable; full flights may be omitted. UI available is NOT award-seat availability. CX flight number alone does not prove CX operation.
- [CX_A350_900](https://www.cathaypacific.com/cx/en_HK/flying-with-us/aircraft-and-fleet/airbus-a350/900.html) — checked 2026-10-16; Published A350-900 configuration includes J, W and Y; no dated seat inventory.
- [CX_A350_1000](https://www.cathaypacific.com/cx/en_HK/flying-with-us/aircraft-and-fleet/airbus-a350/1000.html) — checked 2026-10-16; Published A350-1000 product page; aircraft-family configuration reference, not a tail assignment.
- [CX_777](https://www.cathaypacific.com/cx/en_HK/flying-with-us/aircraft-and-fleet/boeing-777/300.html) — checked 2026-10-16; Published 777-300 J/Y cabin configuration; timetable only identifies Boeing 777 family. No promise of a flat-bed or Aria product on CTS.
- [CX_REDEMPTION](https://www.cathaypacific.com/cx/en_HK/book-a-trip/redeem-flights/redeem-flight-awards.html) — checked 2026-10-16; Unauthenticated page displays Sign in to redeem; no authenticated inventory accessed.
- [CX_AWARD_CHART](https://flights.cathaypacific.com/en_HK/redeem-flights/flight-award-chart.html) — checked 2026-10-16; Public chart directs standard/partner/mixed-carrier searches to redemption. Upgrade/companion charts are not Standard quotes; no target-date Standard price obtained.
- [CX_SURCHARGE](https://www.cathaypacific.com/cx/en_HK/latest-news/other-news/fuel-surcharge-updates.html) — checked 2026-10-16; Current per-sector surcharge notice is publicly available and periodically revised. It is not a complete 2027 award tax quote; no amount entered into candidate totals.
- [CX_SYD_PRODUCT](https://news.cathaypacific.com/cathay-pacific-s-highly-anticipated-aria-suite-takes-business-to-new-heights-in-australia-w2llcd) — checked 2026-10-16; J/W products published on selected Sydney flights historically. Does not bind a 2027 aircraft or guarantee Aria.
- [CX_AKL_2025](https://news.cathaypacific.com/cathay-pacific-increases-lift-off-from-auckland-qdb630) — checked 2026-10-16; Historical schedule, NOT used to backfill September/October 2027 CX operation.
- PHASE2C_REFERENCE: `validation/2027_REAL_PREFERENCE_METRICS.json` — frozen Phase 2C evidence and family metadata; SHA-256 in JSON.
