# Asia Miles Hybrid Award Optimizer — Agent Playbook

**Category:** Domain knowledge + deterministic candidate comparison. **Not live availability.**

When asked to optimize two-person Asia Miles redemptions from the Greater Bay Area:

1. Read `README.md`, `rules_2026_10.json`, and the relevant itinerary JSON, preferably via the current AndreOS knowledge source after integration.
2. Clarify (if not in context) intended destinations/date flexibility, exact independently usable account balances, and lowest acceptable cabin *on long haul* and *on short haul*.
3. Generate candidate tickets for: CX standard award J/W/Y; CX one-way mixed-cabin (J/W long + Y feeder); oneworld multi-carrier J/Y/F (never W); cash long/short; off-ticket short-hop award; ground transfer via HKG/SZX/CAN, PVG/SHA, TPE as appropriate.
4. Evaluate with `python3 optimizer.py --input <file>`. Preserve all source URLs, dates and fare/cabin availability statuses; never substitute a hardcoded hypothesis for an observed award seat or cash fare.
5. Confirm each target trip is end-to-end (no hidden gap across an open jaw), required airlines really operate and are eligible, time/order/stopover/open-jaw constraints, one-year validity and two seats; for multi-carrier ask Cathay to price whole ticket.
6. Output at least three meaningfully different plans **within the user's cabin preference**, showing independent balances, total miles, cash taxes/fare/ground, extra time, risks, and why each wins. Offer different cabin tiers as optional trade-offs, not strictly comparable substitutes.
7. If an input is missing, report a break-even inequality instead of inventing a fare. E.g. 170k PVG vs 210k CAN has a 40k miles/person spread; at 0.10 HKD/mi it equals HK$4,000/person **before** taxes and differences in comfort.
8. Distinguish `RULE_VERIFIED`, `ROUTE_EXISTENCE_CHECKED`, `MILES_PRICE_ESTIMATED`, `AWARD_SEATS_2_VERIFIED`, `CASH_QUOTED`, `AIRLINE_TICKETABLE`. Never claim ticketability based solely on static chart data.

Version 1 is only a calculator for **supplied candidate routes**, not an automatic geographic graph search nor a reservation engine. For live sources, use carrier official search and permitted specialist data providers. Do not store credentials or account identifiers in shared Knowledge files.
