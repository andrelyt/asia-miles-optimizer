# FlyAsia research — cross-review and V2 engineering decisions

Date: 2026-10-15
Status: REVIEWED RESEARCH / NOT AN OFFICIAL AWARD RULE SOURCE

## Inputs and provenance

Two independent reports currently remain in separate, unmerged PRs:
- PR #3: https://github.com/andrelyt/asia-miles-optimizer/pull/3 — extensive English report (~62k chars), including public-script inspection and a separately identified gated split planner.
- PR #4: https://github.com/andrelyt/asia-miles-optimizer/pull/4 — concise Chinese report (~21k chars), 18 mixed-cabin cases and oneworld examples.

Both PRs add **the same repository path**, `docs/research/FLYASIA_RESEARCH.md`, so they must not be merged blindly or sequentially without deciding which text survives. Preserve both original PRs as evidence. This cross-review is independent of their proposed file path.

## Key findings and confidence

1. **Tool identity correction — HIGH confidence.** `/miles/asia-miles/oneworld-planner/` is a manual oneworld itinerary validator/distance-chart calculator, **not** an automatic multi-holiday or split-point optimizer. The separate `/miles/asia-miles/split-planner/` is described in FlyAsia tutorials but membership-gated; neither report operated its private interface. Do not attribute its claimed savings or algorithms to hands-on tests.
2. **Award map — HIGH confidence for observed interface, NOT for bookability.** Budget-to-direct-destination lookup, static route snapshot, distance-band chart, cabin/airline options and one-way count `floor(balance / one_way_price)`. No seat, date, tax, connection or ticketability verification. Useful V2 destination-discovery query pattern, not a source of confirmed availability.
3. **Mixed cabin — HIGH confidence for FlyAsia behavior, not official Cathay arithmetic.** Two connected sectors, one-way, total-distance band, segment-distance-weighted cabin prices, final floor to 100. Reports agree on the broad formula. PR #3 identifies an implementation nuance: FlyAsia rounds the raw blended sum to the nearest whole mile **before** floor-to-100; V1.1 floors the raw sum directly. This can differ at exact 100-mile thresholds. Do not silently replace V1.1 rounding. Add explicitly labeled third-party test vectors and an official-rule review gate.
4. **oneworld multi-carrier — HIGH confidence on official structural limits.** Official Cathay terms confirm 2 oneworld carriers without CX / >=3 with CX, 50,000 miles maximum, <=5 stopovers, <=2 transfers, <=2 open jaws, highest cabin pricing and no premium economy. FlyAsia validator can display a chart price even when other rules fail: chart lookup is not ticketability. See https://www.cathaypacific.com/content/dam/focal-point/cx/membership/programme-update/Cathay-membership-programme-terms-and-conditions-2026-EN.pdf
5. **Multi-trip savings — LOW confidence as actionable savings.** Reported London/Tokyo figures and constructed scenarios are illustrative/theoretical. Real ticket validity, route operation, seat inventory, award validity periods and ticketing must be independently confirmed. Do not use theoretical savings as strict comparable cost.

## Engineering decisions

### PR2 — Route Graph / Standard Candidate Generator (already open as PR #2)

PR #2 exists and reports 108 tests PASS; review its real diff before merging. Do **not** rewrite PR2 just to mimic FlyAsia. Follow-up enhancements only if contract-compatible:
- Destination-discovery mode: budget + origin + supported cabin + direct route filter; label chart estimates and avoid seat claims.
- Airline-on-route evidence and city-level airport equivalence (HND/NRT), with explicit source and stale status.
- Keep open-jaw classification in the appropriate itinerary validation layer; do not infer ground transfer time/cost.
- Do not import FlyAsia's unverified route inventory or award charts as VERIFIED facts.
- Category-2 applicability must be checked against official Cathay terms and existing versioned rules; do not patch from a third-party inferred country list.

### PR3 — V1 adapter / pricing regression
- Use report test matrices as **third-party comparison fixtures**, with source, date, input, expected FlyAsia output and evidence tag.
- Explicitly test rounding at exact hundred boundaries, total-distance band, reversed cabins, category 1/2, partner toggle, and unsupported third segment.
- Distinguish `FLYASIA_MATCH` from `OFFICIAL_RULE_VERIFIED`; mismatch is a review finding, not permission to change the pricing kernel.
- Same-ticket mixed and separate-ticket sums must remain separate structures.

### PR4 / P1 — Portfolio / Multi-trip
- Separate annual leave allocation from multi-trip single-award ticket feasibility.
- D2 needs its **own** bounded split-point/search design; public oneworld-planner has no automatic split-point search.
- Add evidence-aware, rule-by-rule explanation and candidate shareability if useful, without copying third-party UI/source code.

## Additional risk controls

- Flight route evidence, operating carrier, alliance eligibility, chart applicability, seats, cash taxes and ticketability are separate dimensions.
- FlyAsia's static charts, routes, distances and category assignments are third-party observations, not official booking quotes.
- The official standard-award one-way limit is two sectors with one transfer <=24 hours; roundtrip standard awards have their own limits. Check ticket boundaries before V1 adaptation.
- Unknown ground/open-jaw transport cost and travel time remain unknown.
- Any 2027 future booking must pass rules applicability checks; do not assume a 2026 chart remains current.

## Review disposition

**Both research PRs: useful evidence, not merge-ready as-is into a single canonical file.**
PR #3 is more comprehensive and makes the crucial split-planner distinction explicit. PR #4 is useful as a concise Chinese digest and independent case cross-check. Preferred future integration: keep one canonical detailed research file plus an explicitly named independent companion/digest file, without overwriting either source. No research PR was merged as part of this review.

Official source for structural award constraints: https://www.cathaypacific.com/content/dam/focal-point/cx/membership/programme-update/Cathay-membership-programme-terms-and-conditions-2026-EN.pdf
