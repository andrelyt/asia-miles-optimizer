# V2 Alpha PR2 — Route Graph + Standard Candidate Generator

Scope: directed route evidence, bounded path discovery and standard-award
structures. No live sources, inventory, prices, V1 adapter, portfolio or planner
CLI. PR1 and the V1.1 kernel remain intact; existing schemas and award rules are
unchanged. Standard Python only.

## APIs

```python
from discovery.route_graph import load_route_graph
from discovery.candidate_generator import generate_candidates

# Sources may be mappings or JSON paths for the graph loader.
graph = load_route_graph(route_snapshot)
paths = graph.find_paths("AAA", "CCC", config=search_config,
                         travel_date="2027-01-01")
result = generate_candidates(graph, request, rules=explicit_rule_snapshot,
                             window=optional_pr1_window, config=search_config)
```

`request` conforms to travel_request.schema.json; `route_snapshot` conforms to
route_graph.schema.json. The existing standard-library schema helper now also
supports number/exclusiveMinimum, needed by that existing route schema. It rejects
zero/negative/non-finite distances, invalid cabins, date formats and extra fields.
Duplicate traveler IDs, self-loop edges, contradictory validity dates and
conflicting duplicate route relationships are explicit validation errors. Exact
normalized duplicate edges are deduplicated. Parallel carriers/validity periods
remain distinct edges. Cabin arrays/edge order do not affect IDs or search order.

## Route facts and provenance

Every returned edge comes from the supplied snapshot, in its supplied direction.
A→B never implies B→A. Search has no repeated airports in a direction and stops
when the target is reached. It creates no route, connection or cabin evidence.
Each edge preserves carrier, alliance, distance/source, cabin set, URL,
observation time, validity dates and declared/effective route status. Missing edge
observation time inherits the snapshot's observation time.

VERIFIED is supplied evidence, **not independent live verification by this code**.
A declared VERIFIED edge without a usable HTTP(S) source URL becomes UNVERIFIED,
with a note. VERIFIED evidence expired by the snapshot date becomes STALE.
UNVERIFIED or STALE inputs are never promoted. No wall-clock aging threshold is
invented; results depend on the snapshot and explicit travel date, not today's
clock. Missing distance-source metadata stays missing; route verification is not
distance/pricing verification.

With an explicit travel date, edges outside known valid_from/valid_until bounds
are excluded (inclusive endpoints). Without one, date validity is NOT_CHECKED;
STALE leads may remain discoverable. For a supplied holiday window, all outbound
legs use the start date and all inbound legs the end date as an explicit coarse
assumption. This is not flight schedule or minimum-connection-time validation.

Aggregate status is UNVERIFIED if any leg is UNVERIFIED, otherwise STALE if any is
STALE, otherwise VERIFIED. Even all-VERIFIED paths do not establish award seats,
carrier redemption eligibility or ticketability.

## Search bounds

All bounds come from config/search_config.json:

- max_flight_legs_per_trip applies to the **whole roundtrip**, not each ticket or
  each direction independently. Default 3 permits 2+1 legs; 2+2 requires at least 4.
- max_connections also applies across both directions (total legs minus two).
- A standalone find_paths call applies those upper bounds to its one direction;
  the generator reserves at least one leg for the other direction and checks the
  combined trip again. Splitting tickets never bypasses trip limits.
- max_raw_paths_per_od caps completed directed paths per origin/destination.
- beam_width bounds retained partial paths per depth. Shorter distance, then
  stable edge ID breaks equal-depth ties; this is a deterministic search heuristic,
  not price/time/global-optimality ranking.

Path diagnostics expose beam_truncated, path_limit_reached, date_exclusions,
validity_status and effective leg bounds. A reached path cap may or may not have
omitted another path. No-path results use NO_PATH_WITHIN_BOUNDS. These are bounded
search results, not proof that a real-world route cannot exist.

## Cabin strategies and ticket grouping

Strategies: ALL_J, LONG_J_SHORT_Y, LONG_W_SHORT_Y, ALL_W, ALL_Y,
OUTBOUND_J_RETURN_W, OUTBOUND_W_RETURN_J and PREFERRED.

Every leg's selected cabin must exist on its edge and meet the hard minimum.
A Y baseline below the request minimum is omitted, never used to weaken the
request. PREFERRED chooses the greater of the longhaul preferred and hard minimum;
other valid strategies remain available. longhaul_preferred_met is a reporting
field, not a filter or weighted score. F hard/preferred cabins can be represented
by PREFERRED where the supplied edges support F.

Because the route schema has distance but no haul classification, the config
adds candidate_generation.longhaul_distance_threshold_miles (default 4000).
Distance >= threshold is treated as longhaul **for cabin generation only**. This
is an explicit, adjustable structural assumption, not an airline's definition or
an Asia Miles award-price band. It is echoed on each candidate; no award chart
was added/changed or duplicated.

allow_mixed_cabin controls cabin variation within a direction, including split
tickets. allow_asymmetric_roundtrip controls the two asymmetric strategies and
defaults to false when absent. allow_separate_tickets enables split variants.

SINGLE_AWARD means one proposed award **per direction** (normally two tickets for
the roundtrip), not one combined roundtrip award. SEPARATE_AWARDS splits each
leg into its own ticket. Two direct flights have identical grouping either way,
so no phantom split variant is created. Single-ticket cross-carrier connections
are conservatively unsupported in this milestone; the split structure can still
be retained. This is a representation restriction, not a claim about airline rules.

For same-ticket mixed cabins, structural leg-count/carrier capability is read
from the caller's standard_mixed_constraints; Python does not maintain separate
CX/two-leg policy constants. Missing capability data suppresses the same-ticket
mixed variant, while supported split candidates remain possible. Transfer hours,
route type where required, carrier redemption eligibility, applicable rule version
and whole-ticket quotation remain explicit requirements. No mixed-cabin savings
are assumed and no proportional/oneworld pricing is performed here.

## Determinism, caps and output

The outbound/return Cartesian product is traversed lazily, not materialized.
max_candidates_per_strategy is a cap across all OD pairs and ticket modes within
that strategy. preserve_strategy_diversity=true alternates ticket modes while
filling each strategy's cap, preserving structural alternatives where the cap
allows; false exhausts the first mode first. Each strategy has its own cap, so
one strategy cannot consume another strategy's allowance. Diagnostics disclose
selected counts, limit_reached and rejection reasons. A tight bound cannot promise
all possible variants or global optimality.

Identical physical/evidence/ticket structures merge strategy aliases. Candidate
IDs hash normalized structure and evidence, excluding the strategy label. Input
traveler/airport/edge/cabin ordering does not change IDs. Changed source evidence
may change IDs. Retained candidates are sorted by ID, **not by desirability**.

Each candidate carries separate holiday_status (null when no window),
route_status, pricing_status=UNKNOWN, award_seat_status=NOT_CHECKED and
ticketability_status=NOT_CHECKED. A supplied PR1 window is copied, including its
ID and evidence; ESTIMATED status/uncertainty cannot become OFFICIAL. The generator
does not re-run leave validation or annual budgets. Invalid windows are rejected.

lifecycle remains GENERATED: these are not V1_VALID scenarios. Miles and taxes
are null, complete_price_comparison_eligible is false, and
rule_version_review_required is true. Caller-supplied rules are used for current
representation capability only, not a claim of applicability to future booking
or travel dates. PR3 must resolve/quote/map safely through V1.1, returning explicit
unsupported/review-required reasons rather than approximating.

## Explicit data/scope gaps

Only airport destinations are resolved: city/country/region values emit
DESTINATION_RESOLUTION_REQUIRED rather than guessed airports. Unsupported required
targets prevent candidates; multiple required airports emit
MULTI_DESTINATION_UNSUPPORTED. With no required targets, supplied airport targets
are alternatives. Multiple origin airports are alternatives, but each roundtrip
returns to its starting airport. Reposition airports are deferred explicitly.

Insufficient route/cabin/config data returns diagnostics and
NO_FEASIBLE_STANDARD_CANDIDATES, not invented fares, reverse services or weaker
preferences. PR3 V1 adaptation and PR4 annual/holiday orchestration remain out of
scope. Runtime VERIFIED labels are assertions of the supplied evidence; the test
fixtures use TEST snapshot IDs, example.invalid URLs and synthetic distances,
not real carrier service claims.

Run the full regression suite:

```bash
python3 -B -m unittest discover -p 'test_*.py' -v
```
