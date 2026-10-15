# Phase 2B-1 — Cathay Standard Award applicability audit for 2027

**OBSERVATION-ONLY RULE AUDIT — NOT AN AWARD QUOTE — NOT AWARD AVAILABILITY — NOT BOOKABLE**

Audit date: 2026-10-15 (Asia/Hong_Kong date). [Issue #8](https://github.com/andrelyt/asia-miles-optimizer/issues/8) and all conversation comments read (0 comments).

## Decision

**Chart-conflict verdict: INCONCLUSIVE. Audit readiness: BLOCKED. PR3 decision: A — KEEP_RULE_VERSION_REVIEW_REQUIRED.**

The repository chart cannot currently be promoted to verified 2027 pricing. Equally, the lower numbers on the Japan campaign page must not replace it. Current official navigation sends Standard pricing to the redemption search, while two later secondary reconstructions match the repository. The marketing table is insufficient to prove a repository error. No current official full chart or authenticated, dated quote covering the requested routes/cabins was obtained. This is an evidence limitation, not a claim that such prices or award seats do not exist.

## Execution and reproducibility

- Branch: `main`; execution HEAD: `f1e2670fe3c30ed41fe1651b35220b552f860aff`; latest main fetched and fast-forward checked before audit; worktree clean.
- Python 3.9.6. Before audit: **258 passed / 0 failed / 0 errors**, exit 0 (2.646 seconds). Final rerun recorded below.
- Read in full: rules_2026_10.json, discovery/award_adapter.py, discovery/award_pricing.py, optimizer.py. Inspected README.md, SKILL.md, AGENTS.md, docs/PR3_AWARD_PRICING.md, docs/research/FLYASIA_CROSS_REVIEW.md, adapter/pricing tests and test_optimizer.py.
- Existing archived validation output was inspected, not changed or repriced. No planner run with new evidence, fake quote, fake account, or fabricated rule review was performed.

```bash
git fetch origin main
git merge --ff-only origin/main
git rev-parse HEAD
git status -sb
python3 -B -m unittest discover -p 'test_*.py' -v
git log --format='%h %s' -- rules_2026_10.json
git show 6303c49:rules_2026_10.json
```

## Repository chart inventory and provenance

The following are repository reference values, not airline quotes. F=— means no value is stored, not proof that a cabin is unavailable. route_type=— means that band has no type selector.

| Band | Min miles | Max miles | route_type | Y | W | J | F | Source / effective date |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| up_to_750 | 1 | 750 | — | 7000 | 11000 | 16000 | — | Shared secondary source list; per-cell effective_from/effective_to absent |
| 751_2750_type1 | 751 | 2750 | 1 | 9000 | 18000 | 27000 | 43000 | Shared secondary source list; per-cell effective_from/effective_to absent |
| 751_2750_type2 | 751 | 2750 | 2 | 13000 | 23000 | 33000 | 50000 | Shared secondary source list; per-cell effective_from/effective_to absent |
| 2751_5000 | 2751 | 5000 | — | 20000 | 39000 | 60000 | 90000 | Shared secondary source list; per-cell effective_from/effective_to absent |
| 5001_7500 | 5001 | 7500 | — | 27000 | 52000 | 91000 | 125000 | Shared secondary source list; per-cell effective_from/effective_to absent |
| 7501_plus | 7501 | 50000 | — | 38000 | 78000 | 119000 | 160000 | Shared secondary source list; per-cell effective_from/effective_to absent |

- rules version=1.1, as_of=2026-10-15. Neither field is an airline effective date. The source effective_from=2026-01-01 is attached to structural constraints, not cx_standard_chart prices. Every chart row lacks its own evidence URL, effective_from and effective_to.
- The final max_mi=50000 is the repository lookup bound. It is not evidence of an official Standard Award 50,000-mile maximum; the marketing table says 7,501+.
- Numeric chart content is identical as parsed to the original chart in commit `6303c49b3dae765fc18b5f2c846e1bdc89a75681` (2026-10-15 initialization). Subsequent commits `0840f4e` and `0045a27` added/refactored constraints without changing these chart cells.
- source_quality explicitly identifies a secondary reconstructed chart plus official conditions. Its shared sources include Points Plug and FlyAsia, without row-level lineage. [T3_POINTSPLUG](https://pointsplug.com/award-charts/cathay-asiamiles) and [T3_AFF](https://www.australianfrequentflyer.com.au/cathay-pacific-award-charts/) currently reproduce all six rows, including the disputed target-band values. That corroborates a post-May-2026 reconstruction, not official authentication.

## Official versus campaign evidence

The current [T1_REDEEM](https://www.cathaypacific.com/cx/en_HK/book-a-trip/redeem-flights/redeem-flight-awards.html) and [T1_CHART](https://flights.cathaypacific.com/en_HK/redeem-flights/flight-award-chart.html) were directly rendered in a browser after text-only fetches returned empty SPA content. The chart page sends Standard/partner pricing to redemption search. Its displayed numeric table is **upgrade** pricing; it was not copied as Standard pricing. The current redemption interface shows **Sign in to redeem**. No login, flight search or inventory request was made. A limited October/November 2026 Sydney 20,000-mile “from” offer is supporting marketing only, not a 2027 quote.

The Japanese [T2_JAPAN](https://flights.cathaypacific.com/en_JP/offers/bonus-miles2.html) is a Summer Bonus Miles Campaign, explicitly ended, with booking deadline 24 August 2026 and travel through 31 October 2026. It describes Tokyo-origin examples on CX-marketed/operated flights. The campaign awards bonus earning miles on qualifying return paid bookings; it does not establish a discounted Standard redemption chart. Its illustrative redemption table has no visible publication/update/effective date or explicit one-way label. Numerical resemblance to historical one-way tables is not enough to certify its current pricing basis.

| Disputed cell | Repository | Japan campaign | Current official confirmed value |
|---|---:|---:|---|
| Short Type 2 Y | 13,000 | 12,500 | UNKNOWN |
| Short Type 2 J | 33,000 | 32,000 | UNKNOWN |
| Medium W | 39,000 | 38,000 | UNKNOWN |
| Medium J | 60,000 | 58,000 | UNKNOWN |
| Long W | 52,000 | 50,000 | UNKNOWN |
| Long J | 91,000 | 84,000 | UNKNOWN |
| Ultra-long J | 119,000 | 110,000 | UNKNOWN |
| Ultra-long W (additional mismatch) | 78,000 | 75,000 | UNKNOWN |

Other Y/W/J cells: campaign Medium Y=20,000, Long Y=27,000 and Ultra-long Y=38,000 match repo; Short Type 2 W=23,000 matches. The campaign lacks the first two repo rows. None of these matches upgrades the entire chart.

### Resolution of the ten conflict questions

1. **Publish/update date:** no chart timestamp visible on the Japan page; campaign dates are not chart effective dates.
2. **Currently accessible versus current policy:** accessible and ended. Availability of a URL is not currency of its table.
3. **Japan market scope:** Japan campaign, Tokyo examples; no evidence of a distinct Japan-only global redemption tariff.
4. **Promotional price:** a bonus-mile paid-ticket offer is shown. No evidence that the example award prices are a redemption discount.
5. **Old chart residue:** plausible and supported by the chronology below, but exact table vintage remains STALE_OR_UNCERTAIN, not proven.
6. **One-way Standard:** CX-only redemption examples, but no visible one-way/effective-date certification for that table. Not a candidate-bound quote.
7. **Repo version:** initialization already had all six rows; shared secondary provenance matches post-May-2026 reconstruction, without per-cell official lineage.
8. **2025/2026 changes:** official 2025 annual report verifies a Standard Award revision; multiple secondary reports describe a later May 2026 redemption revision.
9. **Effective dates:** 2025-04-15 official; 2026-05-01 reported by secondary sources, not independently recovered as a preserved official notice in this audit.
10. **More authoritative source:** current official redemption-search entry and live legal terms were found; a complete current numeric Standard chart/dated quote was not recovered. Therefore INCONCLUSIVE, not REPO_CORRECT, OFFICIAL_PAGE_CORRECT, or an asserted BOTH_CONTEXT_DEPENDENT.

### Chronology: redemption versus earning

- [T1_ANNUAL](https://www.cathaypacific.com/content/dam/cx/about-us/investor-relations/interim-annual-reports/en/2025_cx_annual_report_en.pdf) (Annual Report 2025, signed 11 March 2026, printed page 17) explicitly dates a **Standard Award redemption chart** update to **15 April 2025**. It supplies no complete prices and does not establish a future chart.
- [T1_EARNING](https://www.cathaypacific.com/cx/en_CA/membership/news-and-updates/Changes-to-your-Status-Points-and-Asia-Miles-earnings-on-flights.html) concerns **Status Points and miles earned** for departures from **20 August 2025**. It is not a redemption chart. Its distance-zone examples were not used as CTS redemption evidence.
- [T3_FLYASIA](https://www.flyasia.co/2026/asiamiles-cathay-chart/) identifies its table as manually reconstructed and reports 1 May 2026 changes; [T3_AFF](https://www.australianfrequentflyer.com.au/cathay-pacific-award-charts/) (29 May 2026) and [T3_POINTSPLUG](https://pointsplug.com/award-charts/cathay-asiamiles) (reviewed 22 September 2026) support the later repo-like values. These remain SECONDARY_CORROBORATION. Earlier [T3_MILELION](https://milelion.com/2026/03/26/cathay-pacific-will-devalue-asia-miles-from-may-2026/) (26 March 2026) is a discovery lead with some different projected cells, so third-party agreement is not perfect across publication dates.
- The contemporaneous article's official announcement link now opens the current redemption page, without the historic adjustment notice in inspected content. Thus the precise official 2026 notice wording and complete tariff were not authenticated. Search absence is not proof no notice exists.

## Route-by-route provisional band audit

General clause 9 distinguishes Type 2 using endpoints/turnaround in Bangladesh, India, Indonesia, Japan, Nepal or Sri Lanka; transfer-only presence is treated differently. CTS is a Japanese endpoint in both directions, supporting Type 2 **if** its distance is within 751–2,750. This uses redemption terms, not earning zones. [T1_TERMS](https://www.cathaypacific.com/content/dam/focal-point/cx/membership/programme-update/Cathay-membership-programme-terms-and-conditions-2026-EN.pdf).

| Directed route | Research distance miles | Provisional band | Repo Y | Repo W | Repo J | Evidence status |
|---|---:|---|---:|---:|---:|---|
| HKG–AKL | 5687 | 5001_7500 | 27000 | 52000 | 91000 | DISTANCE_PROVISIONAL; pricing UNKNOWN |
| AKL–HKG | 5687 | 5001_7500 | 27000 | 52000 | 91000 | DISTANCE_PROVISIONAL; pricing UNKNOWN |
| HKG–ZRH | 5774 | 5001_7500 | 27000 | 52000 | 91000 | DISTANCE_PROVISIONAL; pricing UNKNOWN |
| ZRH–HKG | 5774 | 5001_7500 | 27000 | 52000 | 91000 | DISTANCE_PROVISIONAL; pricing UNKNOWN |
| HKG–CTS | 2131 | 751_2750_type2 | 13000 | 23000 | 33000 | DISTANCE_PROVISIONAL; pricing UNKNOWN |
| CTS–HKG | 2131 | 751_2750_type2 | 13000 | 23000 | 33000 | DISTANCE_PROVISIONAL; pricing UNKNOWN |
| HKG–SYD | 4581 | 2751_5000 | 20000 | 39000 | 60000 | DISTANCE_PROVISIONAL; pricing UNKNOWN |
| SYD–HKG | 4581 | 2751_5000 | 20000 | 39000 | 60000 | DISTANCE_PROVISIONAL; pricing UNKNOWN |

Distances are unchanged approximate great-circle research values from the existing UNVERIFIED graph, not Cathay official award-calculation mileage. No official numeric distance was obtained for any of the eight directed legs. Directional symmetry above reflects the supplied research values, not separately verified airline tariffs. Route bands and all displayed miles stay provisional; W/J in a table does not prove a flight operates those cabins. No live schedule, seat or tax check was performed.

## Standard structure and mixed cabins

The live legal page and PDF share commencement **1 January 2026**, without a stated award-rule end date. General clauses 5/6 allow two sectors per direction, one-way one transfer up to 24 hours; clause 16 uses directional distance and sums connecting sectors. Standard clause 3 permits mixed cabins, apportions each direction using sector Great Circle Distance, and floors the sum to 100. [T1_TERMS](https://www.cathaypacific.com/content/dam/focal-point/cx/membership/programme-update/Cathay-membership-programme-terms-and-conditions-2026-EN.pdf); [T1_LEGAL](https://www.cathaypacific.com/cx/en_HK/legal-and-privacy/cathay-membership-terms-and-conditions.html).

J/W and W/J are covered by that general mixed-cabin permission; no pair-specific ban is stated there. This does not certify every itinerary. With J outbound/W return (or reverse), evaluate directions separately; two direct directions do not become a same-direction two-sector mixed ticket. Same-direction J/W needs appropriate sector data. Highest-cabin whole-ticket pricing belongs to another award scheme and was not applied. The clause does not specify FlyAsia's intermediate integer rounding; V1.1 was unchanged.

## Booking horizon arithmetic

Standard clause 7(a) states CX booking up to **360 days** before departure. [T1_TERMS](https://www.cathaypacific.com/content/dam/focal-point/cx/membership/programme-update/Cathay-membership-programme-terms-and-conditions-2026-EN.pdf). As of 2026-10-15, date arithmetic gives a latest horizon date of **2027-10-10**. Calendar arithmetic ignores exact departure time/timezone release details:

| Travel date | Days ahead | At most 360 days? |
|---|---:|---|
| 2027-05-01 Labor Day anchor | 198 | YES |
| 2027-10-01 National Day anchor | 351 | YES |
| 2027-10-08 latest retained validation endpoint | 358 | YES |
| 2027-10-10 | 360 | YES, boundary |
| 2027-10-12 | 362 | NO as of audit date |
| 2027-10-16 | 366 | NO as of audit date |

All 24 windows retained by the first validation (May endpoints through May 8; September/October endpoints through October 8) fall within this arithmetic range. “May/October is too early to book” is therefore not a valid blanket explanation of the PR3 gate. No inference about schedules or inventory follows.

## Rule Applicability Matrix

| Rule | Current evidence | 2027 applicability |
|---|---|---|
| Standard Award structure | T1_TERMS General 5/6, live T1_LEGAL | CURRENT_NO_KNOWN_EXPIRY |
| CX booking horizon rule | T1_TERMS Standard 7(a), 360 days | CURRENT_NO_KNOWN_EXPIRY |
| Target-window horizon arithmetic | 2026-10-15 to prior retained dates <=360 days | VERIFIED |
| CX numeric award chart | Secondary repo reconstruction vs undated campaign | CONFLICTING |
| Directional distance-band method | T1_TERMS General 16 | CURRENT_NO_KNOWN_EXPIRY |
| Eight route numeric distances / assigned bands | Approximate research only | PROVISIONAL |
| CTS Short Type 2 geography | T1_TERMS General 9, conditional distance band | CURRENT_NO_KNOWN_EXPIRY |
| Mixed-cabin method | T1_TERMS Standard 3; exact inputs still needed | CURRENT_NO_KNOWN_EXPIRY |
| Any candidate's final mileage quote | Not acquired | NOT_EVALUATED |
| Taxes | Outside audit | NOT_EVALUATED |
| Seat availability | Outside audit | NOT_EVALUATED |
| Ticketability / operating schedule | Outside audit | NOT_EVALUATED |
| Account balances / funding eligibility | Outside audit | NOT_EVALUATED |

CURRENT_NO_KNOWN_EXPIRY corresponds to CURRENT_RULE_NO_KNOWN_EXPIRY in prose; neither means VERIFIED_FOR_2027. No award-rule effective_to was located. Terms permit later programme changes; a 2026 filename does not itself create either expiry or perpetual validity. The T&C's calendar-year/status-transition material for 2027 is not evidence of a redemption tariff change. Future tariff certainty remains unverified.

## Why all first-run candidates stop at PR3, and the next gate

All 100 archived trips have input_evidence={} and status RULE_VERSION_REVIEW_REQUIRED. In award_adapter.py, _reviewed() requires a sourced SUPPLIED_CONFIRMED decision=APPLICABLE, matching candidate_id, exact rules_digest, rules_version, rules_as_of, and valid booking/travel dates matching the window. adapt_candidate() checks this **before** processing tickets. No such reviews exist. This is deliberate even for 2026; rules.as_of is not an applicability interval and the code does not turn a year comparison or booking-horizon calculation into approval.

Tests exercising this contract include test_future_chart_requires_explicit_applicability_review, test_as_of_is_not_an_effective_date_even_in_2026, test_rule_review_cannot_be_third_party_or_for_another_rule, test_modified_rules_invalidate_review_without_silent_repricing and test_cross_year_review_uses_window_not_just_start_year.

After a legitimate review, ordinary Standard still requires a positive integer AIRLINE_QUOTED per-ticket price with matching source/time/candidate/rules/date scope. No chart-derived Standard quote is permitted. CX mixed estimates additionally require sourced distances, transfer hours and route_type when applicable, and remain RULE_ESTIMATED. A report is not runtime evidence and nothing here injects or manufactures APPLICABLE.

**Decision A remains mandatory:** the numeric conflict lacks enough Tier 1 evidence for B. C (RULE_SNAPSHOT_INCORRECT) is not established merely by the Japan page; current secondary reconstructions match the repo. Keep the existing gate unchanged and preserve UNKNOWN prices.

## Evidence register

Ratings describe claims, not blanket reliability. CONFLICTING is the relationship between price sources, not a reason to discard the official structural terms. UNKNOWN covers the absent current official cell values. checked_at is the retrieval date, not publication or effective date.

### T1_TERMS — Cathay Membership Programme Terms and Conditions

- URL: [Cathay Membership Programme Terms and Conditions](https://www.cathaypacific.com/content/dam/focal-point/cx/membership/programme-update/Cathay-membership-programme-terms-and-conditions-2026-EN.pdf).
- checked_at: 2026-10-15; Tier 1; rating OFFICIAL_CURRENT.
- effective_from: 2026-01-01; effective_to: unknown.
- Supports: Standard clauses 3/7/8; General clauses 5/6/9/16
- Limitations: No numeric Standard chart; no 2027 guarantee.
- locator: PDF page index 22 / printed 23; General pages index 19-20

### T1_LEGAL — Cathay Membership Programme Terms and Conditions

- URL: [Cathay Membership Programme Terms and Conditions](https://www.cathaypacific.com/cx/en_HK/legal-and-privacy/cathay-membership-terms-and-conditions.html).
- checked_at: 2026-10-15; Tier 1; rating OFFICIAL_CURRENT.
- effective_from: 2026-01-01; effective_to: unknown.
- Supports: Live legal page displays same commencement date.
- Limitations: Not a new price chart.

### T1_REDEEM — Redeem flight awards | Cathay HK

- URL: [Redeem flight awards | Cathay HK](https://www.cathaypacific.com/cx/en_HK/book-a-trip/redeem-flights/redeem-flight-awards.html).
- checked_at: 2026-10-15; Tier 1; rating OFFICIAL_CURRENT.
- effective_from: None; effective_to: unknown.
- Supports: Current mileage-search entry point.
- Limitations: Browser-visible Sign in to redeem; no authenticated price query performed.
- access: Browser rendered successfully; text-only fetch empty; curl returned SPA shell.

### T1_CHART — Flight awards charts | Cathay HK

- URL: [Flight awards charts | Cathay HK](https://flights.cathaypacific.com/en_HK/redeem-flights/flight-award-chart.html).
- checked_at: 2026-10-15; Tier 1; rating OFFICIAL_CURRENT.
- effective_from: None; effective_to: unknown.
- Supports: Redirects Standard pricing to flight search.
- Limitations: Visible upgrade table is not Standard Award pricing.
- access: Browser rendered; no full numeric Standard table in inspected content.

### T1_ANNUAL — Annual Report 2025

- URL: [Annual Report 2025](https://www.cathaypacific.com/content/dam/cx/about-us/investor-relations/interim-annual-reports/en/2025_cx_annual_report_en.pdf).
- checked_at: 2026-10-15; Tier 1; rating OFFICIAL_DATED.
- effective_from: 2025-04-15; effective_to: unknown.
- Supports: Confirms Standard redemption update effective 2025-04-15.
- Limitations: Not full chart; reporting year does not establish 2026/2027 rates.
- locator: printed page 17 / PDF index 18
- document_date: 2026-03-11

### T1_EARNING — Changes to Status Points and Asia Miles earnings on flights

- URL: [Changes to Status Points and Asia Miles earnings on flights](https://www.cathaypacific.com/cx/en_CA/membership/news-and-updates/Changes-to-your-Status-Points-and-Asia-Miles-earnings-on-flights.html).
- checked_at: 2026-10-15; Tier 1; rating OFFICIAL_DATED.
- effective_from: 2025-08-20; effective_to: unknown.
- Supports: Earning and Status Points adjustments.
- Limitations: Not redemption-price evidence; not used to classify CTS.

### T2_JAPAN — Summer Bonus Miles Campaign

- URL: [Summer Bonus Miles Campaign](https://flights.cathaypacific.com/en_JP/offers/bonus-miles2.html).
- checked_at: 2026-10-15; Tier 2; rating OFFICIAL_MARKETING; currency STALE_OR_UNCERTAIN.
- effective_from: None; effective_to: unknown.
- Supports: Tokyo-origin illustrative award table.
- Limitations: Campaign ended; no chart effective/update date or 2027 quote; stale-price risk.
- campaign_booking_deadline: 2026-08-24
- campaign_departure_end: 2026-10-31

### T3_POINTSPLUG — Cathay Pacific Asia Miles award chart and sweet spots

- URL: [Cathay Pacific Asia Miles award chart and sweet spots](https://pointsplug.com/award-charts/cathay-asiamiles).
- checked_at: 2026-10-15; Tier 3; rating SECONDARY_CORROBORATION.
- effective_from: None; effective_to: unknown.
- Supports: Reconstructed six-band values match repository.
- Limitations: Not official or independently authenticated quote.
- reported_effective_from: 2026-05-01
- displayed_review_date: 2026-09-22

### T3_AFF — Cathay’s New Asia Miles Award Charts in 2026

- URL: [Cathay’s New Asia Miles Award Charts in 2026](https://www.australianfrequentflyer.com.au/cathay-pacific-award-charts/).
- checked_at: 2026-10-15; Tier 3; rating SECONDARY_CORROBORATION.
- effective_from: None; effective_to: unknown.
- Supports: Unofficial post-May-2026 table matches repository.
- Limitations: Secondary reconstruction only.
- reported_effective_from: 2026-05-01
- displayed_publication_date: 2026-05-29

### T3_FLYASIA — 亞洲萬里通標準獎勵 | Asia Miles 兌換國泰航空的規則

- URL: [亞洲萬里通標準獎勵 | Asia Miles 兌換國泰航空的規則](https://www.flyasia.co/2026/asiamiles-cathay-chart/).
- checked_at: 2026-10-15; Tier 3; rating SECONDARY_CORROBORATION.
- effective_from: None; effective_to: unknown.
- Supports: Reported May-2026 revision; manually reconstructed table.
- Limitations: Cannot override official rules; not official mileage distances.
- reported_effective_from: 2026-05-01
- displayed_dates: ['2026-03-25', '2026-09-15']

### T3_MILELION — Cathay Pacific will devalue Asia Miles from May 2026

- URL: [Cathay Pacific will devalue Asia Miles from May 2026](https://milelion.com/2026/03/26/cathay-pacific-will-devalue-asia-miles-from-may-2026/).
- checked_at: 2026-10-15; Tier 3; rating SECONDARY_CORROBORATION.
- effective_from: None; effective_to: unknown.
- Supports: Contemporaneous discovery link to official redemption page.
- Limitations: March prediction differs from later reconstructions; destination link now shows current UI, not archived announcement.
- reported_effective_from: 2026-05-01
- displayed_publication_date: 2026-03-26

## Minimum next evidence and audit boundaries

1. Obtain a current official route/cabin mileage requirement or dated airline response for each directed HKG–CTS/SYD/AKL/ZRH Y/W/J case, explicitly identifying Standard Award, CX operation, booking date, travel scope, pricing basis and effective date. A mileage response is not seat evidence.
2. Obtain an official explanation or preserved dated official chart/update resolving the eight mismatched cells and the 2026 change. Do not replace the repo chart from the ended campaign or third-party reconstructions alone.
3. Obtain official award-calculation distance/band confirmation per directed route. For a mixed estimate, also obtain exact sector distances, transfer hours and necessary route-type evidence.
4. Only after reconciliation and explicit candidate/date/rule-digest review may a separate task supply real evidence to PR3. Any proven snapshot correction requires its own authorized change and regressions. None is performed here.

No assertions were made about seats existing or absent, bookability, tax amounts, beneficiary eligibility, account funding, or a guaranteed 2027 tariff. Calendar ESTIMATED, routes UNVERIFIED, prices UNKNOWN and seats/ticketability NOT_CHECKED remain unchanged.

## Final verification

Final complete suite: **258 total / 258 passed / 0 failed / 0 errors**, exit 0. Before and after tests use the exact unittest command above; no tests were modified.

All existing tracked files must remain byte-identical to execution HEAD. The exact four audited production SHA256 values are:

- `rules_2026_10.json`: `1b88502223b3df56da028d488c4a03d1517dc9daef074c51c55342f93d684867`.
- `optimizer.py`: `9dc77fe6b9db185c9c95d7382399057c46e3b790cb439dfe1d393ae4522c553d`.
- `discovery/award_adapter.py`: `5eb2134d4e9a439ef134ad1f0844c576256e7057f00fb6583fcc08491e1a292c`.
- `discovery/award_pricing.py`: `85ab2e31603bd1a3abdb2899c8143706819a2138f846ecc714443da25e5d7a10`.

Only this new audit report and public rule-evidence JSON are committed. Raw downloads/SPA shells, scratch scripts and test logs stay outside the repo. No code, tests, schemas, rules, existing evidence, personal accounts or Canonical Memory were changed; no PR was created.
