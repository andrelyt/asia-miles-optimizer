# 2027 Holiday Validation — Phase 1 Official Route Evidence
Date: 2026-10-15
Status: PUBLIC WEB RESEARCH, NOT EXECUTED PLANNER OUTPUT
Privacy: user-specific account balances and leave counts intentionally excluded from this committed evidence file.

## Evidence rules
All entries are official Cathay Pacific flight sales/route information pages. They demonstrate marketed city-pair route direction as displayed at research time, **not** availability on a specific 2027 holiday date, operating schedule, cabin on a specific aircraft, reward-seat availability, award price, taxes or ticketability. Do not map these pages to a candidate-bound `AIRLINE_QUOTED` award price. Do not use cash economy fare teasers as award prices. Return-direction routes need their own evidence before constructing directed edges. Precise flight-distance data and cabin inventory are not yet sourced, so this list is **not** a schema-valid route_graph.json and must not be silently upgraded into one.

## Official source shortlist
| Outbound city pair | Official source | Evidence interpretation |
|---|---|---|
| HKG–AKL | https://flights.cathaypacific.com/destinations/en_HK/flights-from-hong-kong-to-auckland | Official page describes direct HKG–AKL flights |
| HKG–SYD | https://flights.cathaypacific.com/destinations/en_HK/flights-from-hong-kong-to-sydney | Official page describes direct HKG–SYD flights |
| HKG–ZRH | https://flights.cathaypacific.com/destinations/en_HK/flights-from-hong-kong-sar-to-zurich | Official route/fare page for HKG–ZRH |
| HKG–LHR | https://flights.cathaypacific.com/destinations/en_HK/flights-from-hong-kong-to-london | Official page describes direct HKG–LHR flights |
| HKG–YVR | https://flights.cathaypacific.com/destinations/en_HK/flights-from-hong-kong-sar-to-vancouver | Official route/fare page for HKG–YVR |
| HKG–CTS | https://flights.cathaypacific.com/destinations/en_HK/flights-from-hong-kong-to-sapporo | Official page describes direct HKG–CTS flights |
| HKG–NRT/HND | https://flights.cathaypacific.com/destinations/en_HK/flights-from-hong-kong-to-tokyo | Official page describes direct HKG–Tokyo flights; airport-specific service needs care |

## Redemption-policy evidence
- https://www.cathaypacific.com/cx/en_HK/membership/asia-miles/fly_with_miles.html — current promotional flight award alerts with limited travel dates; not 2027 May/October quotations.
- https://www.cathaypacific.com/content/dam/cx/about-us/investor-relations/interim-annual-reports/en/2025_cx_annual_report_en.pdf — Cathay 2025 annual report says Standard Award chart was updated effective 15 April 2025. Not evidence that a 2026 rule version is applicable unchanged to 2027 dates.
- https://www.cathaypacific.com/content/dam/cx/membership/changes-to-status-points-and-am-earnings-on-flights-full-table.pdf — this is an EARNING table, **not** a redemption award price chart; never import as award quotes.

## Initial holiday-to-destination hypotheses
- May Day: AKL (South Island onward ground/domestic transfer), CTS (springtime Hokkaido), ZRH (shoulder-season Alpine constraints), SYD (Australian autumn). Candidate ideas only.
- National Day: ZRH/LHR (Europe), AKL (New Zealand spring), YVR (western Canada shoulder-season; some high-altitude closures), SYD (Australian spring). Candidate ideas only.
- For previously visited western Canada and London, prioritize genuinely different regional experiences over repeating the same city.
- No seasonal preference should override evidence of date-specific flight service, route feasibility, leave dates or reward seats.

## Blocking data for executable real-world graph and quotes
1. Directed **return** edges and sourced precise distances for each desired origin-destination.
2. Official 2027 holiday/makeup-workday schedule, or a clearly ESTIMATED calendar with explicit day-by-day assumptions.
3. Date-specific operating schedules/cabin configuration for shortlisted travel windows.
4. Candidate-bound Standard award miles and taxes, plus 2027 rule applicability review.
5. Payer eligibility and actual account snapshots for confirmed budget feasibility.

## Proposed execution order
First audit HKG↔AKL, HKG↔ZRH, HKG↔CTS and HKG↔SYD. Run conditional-only scenarios before adding cash/reward quotes; no invented return edges or mileage distances. Expand to LHR/YVR/Tokyo only after first useful holiday-window comparisons. Report exact blocked prerequisites if the CLI cannot run on incomplete evidence. This file is a research shortlist, not a claimed completed optimizer run.
