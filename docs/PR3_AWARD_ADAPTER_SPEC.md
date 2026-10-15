# V2 Alpha PR3 — Award Adapter & Pricing Acceptance Spec
Status: READY AFTER PR2 BLOCKERS RESOLVED
Date: 2026-10-15

## Prerequisites
PR2 #2 must first fix per-direction Standard Award <=2 sectors and explicitly support or diagnose Cathay+partner mixed-carrier structures. Reinspect current optimizer.py API and rules schema before implementation.

## Core requirements
- Implement a deterministic adapter from PR2 candidate/ticket groups into existing V1.1 evaluate() input; no second pricing kernel.
- Return structured outcomes: EVALUATED / UNSUPPORTED / NEEDS_DATA / RULE_VERSION_REVIEW_REQUIRED / NEEDS_AIRLINE_QUOTE. No invented transfer times, cash/taxes, route type, carrier eligibility or award quotes.
- Keep Standard one-way, Standard roundtrip, same-ticket mixed cabin, per-sector separate awards, and oneworld multicarrer tickets distinct.
- CX-only mixed cabin may use versioned V1.1 standard_mixed rules when representable. Mixed-carrier/partner pricing must not be fabricated; retain as quote-required if no applicable rule.
- Enforce two travelers' account balances independently. Unknown balances and missing taxes remain unknown; no strict price comparison on incomplete costs.
- Preserve holiday status, route snapshot evidence, pricing status, award seat NOT_CHECKED, ticketability NOT_CHECKED as independent dimensions.
- Date applicability: 2027 travel does not automatically validate a 2026 price chart; explicit effective-date review.
- Preserve deterministic candidate IDs, use separate evaluation IDs, and produce machine-readable diagnostics.

## Mandatory tests
- Existing V1.1 + PR1 + PR2 suite remains green.
- One/two/three sectors per direction; mixed CX+partner and partner+partner; outbound J/inbound W; long J/short Y and W/short Y; same-ticket mixed vs split awards.
- FlyAsia comparison fixtures from docs/research/FLYASIA_RESEARCH_MUSE.md and FLYASIA_RESEARCH_GROK.md, tagged THIRD_PARTY_OBSERVED: total-distance band, category 2, exact 100-mile rounding boundary, partner toggle. Third-party mismatch triggers review, not kernel mutation.
- Estimated holiday and stale route propagation, 2027 rule version, unknown taxes/seats, independent traveler balances.
- One synthetic end-to-end PR1 window -> PR2 candidate -> PR3 adapter -> V1.1 evaluate example, with no bookability claims.

## Out of scope
Live award seats, live tax/cash prices, partner agreement verification, D2 automatic split planner, PR4 annual portfolio.

## Delivery
Add tests and docs, run full suite, create reviewable PR; no auto-merge. Research reports are third-party observations, not official Cathay terms.
Official terms: https://www.cathaypacific.com/content/dam/focal-point/cx/membership/programme-update/Cathay-membership-programme-terms-and-conditions-2026-EN.pdf
