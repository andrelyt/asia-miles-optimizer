# 2027 May / October — Calendar and Return-Direction Evidence Gate
Research date: 2026-10-15. NOT A PLANNER RUN. No inferred official makeup days or award seats.

## Calendar anchors (civil Gregorian arithmetic, not official 2027 holiday schedule)
- 2027-05-01 Saturday (Labor Day statutory anchor).
- 2027-10-01 Friday (National Day statutory anchor).
- **Do not** reuse the 2026 official calendar as a 2027 schedule. The currently found State Council release is for 2026 only: https://big5.www.gov.cn/gate/big5/www.gov.cn/zhengce/zhengceku/202511/content_7047091.htm
- Any tentative leave count is an *ordinary Mon–Fri baseline*, explicitly excluding yet-unknown holiday substitution and makeup-workdays. Do not encode it as official or as exact leave required.
- The holiday_calendar schema needs day-level evidence; no executable estimated snapshot has been created here because its assumptions need explicit user review.

## Round-trip route-direction evidence (official Cathay sources)
| Pair | Outbound HKG → | Return → HKG | Evidence limitation |
|---|---|---|---|
| AKL | https://flights.cathaypacific.com/destinations/en_HK/flights-from-hong-kong-to-auckland | https://flights.cathaypacific.com/destinations/en_HK/flights-from-new-zealand-to-hong-kong-sar and https://news.cathaypacific.com/cathay-pacific-increases-lift-off-from-auckland-qdb630 | Cathay 2025 press release identifies CX198 AKL→HKG and seasonal CX188 for 2025–26, not 2027 service |
| ZRH | https://flights.cathaypacific.com/destinations/en_HK/flights-from-hong-kong-sar-to-zurich | https://flights.cathaypacific.com/destinations/en_CH/flights-from-zurich-to-hong-kong-sar | Sales page lists a 2027 round-trip fare observation, not award seats |
| CTS | https://flights.cathaypacific.com/destinations/en_HK/flights-from-hong-kong-to-sapporo | https://flights.cathaypacific.com/destinations/en_HK/flights-from-sapporo | Outbound direct route described; reverse sales page lists CTS→HKG, not May 2027 award inventory |
| SYD | https://flights.cathaypacific.com/destinations/en_HK/flights-from-hong-kong-to-sydney | https://flights.cathaypacific.com/destinations/en_HK/flights-from-sydney | Outbound direct route described; reverse sales page lists SYD→HKG, not October 2027 award inventory |

## Important evidence interpretation
- These sources justify **researching** eight directed legs. They do not yet justify a schema-valid graph with exact `distance_miles`, exact cabin availability, 2027 flight schedule, or `route_status=VERIFIED` in the sense of fully confirmed travel dates.
- Source page generic descriptions of Premium Economy and Business do not prove W/J on a specific route, aircraft, flight or award date.
- Public cash-fare teasers are not Asia Miles redemption quotes and must never populate PR3.
- For a South Island itinerary, HKG↔AKL alone does not include the domestic flight/ground segment to the South Island. Include transfer cost/time and possible CHC seasonal service separately.
- Dates in flight sales pages are sample cash itineraries, not holiday award availability.

## Tentative comparison windows (NOT official leave calculation)
- May: 2027-04-30→2027-05-09 (10 calendar days); 2027-05-01→2027-05-09 (9 days).
- October: 2027-09-30→2027-10-10 (11 days); 2027-10-01→2027-10-12 (12 days); 2027-10-01→2027-10-16 (16 days).
- These are *candidate planning windows only*. The actual leave engine must calculate each person's leave once the official/estimated calendar snapshot and user-specific days off are provided.

## Next executable-data gates
1. Independently source great-circle / ticketed sector mileage (do not invent) and exact per-route cabin possibilities; keep provenance and timestamps.
2. Assemble explicitly estimated 2027 day-level calendar with assumptions visible and reviewable; no invented official makeup days.
3. Create schema-valid directed route graph only from confirmed fields; where required fields remain unknown, report BLOCKED rather than injecting zero/guess.
4. Run the CLI conditional-only and record its output SHA, counts, errors and search_truncated; do not call this a real price ranking.
5. Actual account snapshots, beneficiary eligibility, airline award-mile and tax quotes, and applicable 2027 rule review are needed for confirmed budget feasibility.
