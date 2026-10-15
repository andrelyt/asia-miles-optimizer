# PR4 — Annual Holiday Portfolio & Planner CLI

Acceptance contract: [PR4_PORTFOLIO_SPEC.md](PR4_PORTFOLIO_SPEC.md). This is D1:
select multiple independent holiday trips for the same traveler party. It does
not create a D2 multi-trip award ticket, prices, partner agreements, seats or bookings.
All committed example data is **SYNTHETIC TEST ONLY**, including fictional dates,
quotes, balances and eligibility attestations. No network/dependency is required.

## Run

```bash
python3 -B planner.py --input examples/planner_synthetic_test.json --output /tmp/TEST_portfolios.json
python3 -B -m unittest discover -p 'test_*.py' -v
```

Omit `--output` for JSON on stdout. All input resource paths resolve relative to
the input JSON file. JSON is sorted, deterministic, and rejects nonfinite values.
Valid planning inputs with no viable portfolio return exit 0 and rejection
counts; malformed input/schema/config/resources return exit 2 with INVALID_INPUT
JSON on stderr. Invalid individual trip structures/quotes go into rejection counts.

The CLI input object accepts:

| Key | Contract |
| --- | --- |
| request | Existing travel_request.schema.json object or local JSON path |
| calendars | One snapshot, list of snapshots/paths, or path containing that list; adjacent years when needed |
| route_graph | Existing route snapshot object/path |
| rules | Explicit versioned rules object/path; never auto-assume a latest chart applies |
| search_config | Optional existing PR1/PR2 search-config object/path |
| portfolio_config | Optional new PR4 config object/path; defaults config/portfolio_config.json |
| evidence_by_candidate | Optional map/path of unchanged PR2 candidate ID -> existing PR3 evidence contract |
| balances_by_account | Explicit account ID -> nonnegative integer miles or null; optional object/path |
| funding_eligibility | Optional list/path of externally supplied payer/passenger eligibility attestations |
| data_label | Optional supplied snapshot label, e.g. SYNTHETIC_TEST_ONLY |

Quotes and applicability review are never manufactured by runtime. Without supplied
evidence, PR3 outcomes remain pending; the planner returns conditional discovery
leads. Output `trips` retains selected PR3 outcomes/candidates/IDs for a later
explicitly sourced evidence pass. Evidence binding/source requirements are unchanged
from [PR3](PR3_AWARD_PRICING.md). Unused candidate-evidence IDs are disclosed rather
than reassigned to another candidate. The static test example has fictional
AIRLINE_QUOTED attestations solely to exercise the budget-feasible path; these are
not actual airline quotes and must not be used as real travel evidence.

## Interfaces and pipeline

- `planner.plan(input_mapping, base_dir='.')`: load supplied resources, PR1 windows,
  PR2 candidates, PR3 prices and PR4 portfolios; return structured output.
- `discovery.portfolio.optimize_portfolios(priced_candidates, request, calendar,
  rules, balances_by_account=None, funding_eligibility=None, config=None)`: pure
  selection with explicit budgets, supplied calendar and rules.
- `annual_budgets()`, `window_request()`: separate annual budget ownership from
  unchanged PR1 single-window evaluation.
- `dominates()`, `pareto_front()`, `recommendation_views()`: conservative comparison
  and four bounded transparent views.
- `discovery.portfolio_funding.allocate()`: bounded indivisible global account
  assignment with memoized residual states, no award-price algorithm.

PR4 replays cached candidate evidence through the actual PR3 price_candidate()
interface. It does not trust cached mile totals, a previous account snapshot or
per-trip FEASIBLE flags. PR3 is called without balances, avoiding its exponential
per-trip account enumeration; PR4 assigns all ticket/passenger jobs together under
its own state bound. No PR1–PR3, V1.1, rule or existing schema file is modified.

## Annual leave

Default budgets apply only to request.planning_year, independently for every
traveler. Explicit optional overrides are:

```json
{
  "leave_budgets_by_year": {
    "2026": {"traveler_a": 2, "traveler_b": 1},
    "2027": {"traveler_a": 3, "traveler_b": 4}
  }
}
```

An explicit year's mapping must contain the entire party and is authoritative
for that year. No year inherits another year's allowance, even if no leave would
be needed that year. Any cross-year travel interval requires explicit coverage
for every touched year. Missing year allowance rejects that trip; it is not silently
borrowed from the planning year.

PR1 retains its original single-window budget semantics. PR4 uses a copied
request with the sum of explicitly available yearly budgets as PR1's temporary
window cap, then enforces actual per-year budgets itself. This permits a legitimate
2+2-day cross-year window with two annual two-day allowances. It never raises
per-trip limits or removes blocked dates. The original request stays unchanged.

Exact leave dates are recomputed from the supplied PR1 calendar and traveler
personal/blocked dates. Supplied window leave/evidence must match that calculation.
The selected public-holiday anchor and bridge-leave settings are rechecked.
MAKEUP_WORKDAY consumes leave unless a personal override applies. Portfolio leave
is a union of dates per traveler, grouped by the **date's calendar year**. Counts
are not sums of window claims, and duplicated dates never consume leave twice.

Intervals overlap inclusively: one trip ending on another's start date conflicts;
ending the previous day is allowed. Different windows/candidates for the same
holiday family/anchor are alternatives, never separate trips. Duplicate candidates
are deduplicated; conflicting duplicate results are rejected. IDs from another
party are invalid. Unknown dates remain conditional with leave_status=UNKNOWN and
TRAVEL_DATES_REQUIRED / LEAVE_DATES_REQUIRED / OVERLAP_NOT_CHECKED; they cannot
claim budget feasibility. At most one undated alternative occurs in a portfolio.

## Whole-portfolio miles and eligibility

Every resolved per-person ticket generates one indivisible job per passenger.
One account pays the entire job; two accounts cannot pool miles for it. Accounts
can pay for passengers other than their owners, subject to external eligibility.
The allocation search starts fresh for each portfolio and considers every trip.
A trip individually feasible with 40,000 miles cannot justify two trips from a
50,000-mile snapshot. Accounts totaling 80,000 in 35,000/45,000 fragments cannot
fund eight indivisible 10,000-mile jobs; the solver rejects that combination.

The explicit balance snapshot caps the **entire planning horizon**. No automatic
new-year refill, future accrual, refunds or transfers are assumed. Output reports
spend per account, remaining balances and spend grouped by the supplied review's
booking year. Travel dates do not invent a mileage debit year. Cross-year leave
budgets and mileage-account snapshots are different constraints.

None, an empty mapping or any null account balance makes the full balance snapshot
unknown. Known amounts are retained, but annual feasibility is NOT_CHECKED; unknown
amounts never become zero. A known zero balance is a real constraint. Legacy
traveler.miles_balance is never imported as a payment-account balance.

An optional eligibility record has `account_id`, `traveler_id`, `decision=ELIGIBLE`,
`valid_from`, `valid_until`, plus PR3-style `evidence_level=SUPPLIED_CONFIRMED`,
`source_url` and timezone-aware `observed_at`. Its date range must cover the supplied booking date through the trip end.
The solver first searches assignments using these supplied-confirmed payer/passenger
edges. If none is found, a numerically feasible unconstrained assignment remains
conditional with FUNDING_BENEFICIARY_ELIGIBILITY_REQUIRED. Source syntax or a label
alone does not authenticate an agreement. Original attestations are retained in
funding_eligibility_evidence; automated funding_eligibility_status remains
NOT_CHECKED, while funding_eligibility_evidence_status describes supplied coverage.

If unknown tickets remain, known-mile jobs can establish only a lower bound. A
known lower bound already exceeding balances is rejected; otherwise no complete
annual allocation/spend is claimed. The search limit returns unresolved conditional
leads, never INFEASIBLE merely because the search stopped.

## Disjoint status groups

`budget_feasible` holds CONFIRMED_BUDGET_FEASIBLE model results: all leave/mile
requirements are known, annual account allocation succeeds, PR3 representation
and applicability checks pass, and supplied funding attestations cover the chosen
allocation. `conditional` holds plausible alternatives with explicit budget_blockers
and missing_data. Unknown miles, partner quotes, rule review, dates, balances or
eligibility never enter budget_feasible. Invalid/unsupported structures, invalid
Standard quotes and proven overbudget/overlap combinations are rejected.

"Confirmed" means budget-model feasibility **under supplied inputs**, including
ESTIMATED calendar assumptions. It is never independent official verification,
route schedule validation, seat availability or ticketability. These channels stay
separate in `evidence`; all PR3 per-trip evidence remains in `trips`. Outputs retain
SUPPLIED_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED. Window endpoints remain planning
assumptions. Even a budget-feasible portfolio keeps seat/ticketability NOT_CHECKED.

Missing taxes do not invalidate leave/mileage budgets, but taxes_hkd remains null,
TAX_QUOTE_REQUIRED is disclosed, and complete_price_comparison_eligible=false.
Budget blockers and other missing evidence are separate. Known-mile/tax subtotals
are explicitly named; incomplete totals/spend are null, not invented zero costs.
Mixed mileage remains RULE_ESTIMATED and cannot enter full quoted-price comparison.

## Pareto dimensions and views

Within compatible complete quoted-cost classes, strict dominance requires no
worse trip count, calendar days, each traveler's annual leave, total miles, every
account's canonical spend, cash taxes, sector/transfer burden, and comfort; at
least one must be strictly better. Evidence channels and holiday-family sets must
match. Unknown destination-day or comfort dimensions must have compatible presence.

Unknown costs/taxes, conditional results, estimates versus quotes, or different
holiday/evidence classes never erase a fully quoted alternative through a lower
visible number. Estimate/partial frontiers are deliberately conservative: no cost
dominance pruning is attempted without complete comparable quotes. Different
feasible account assignments may also leave extra nondominated alternatives.

Comfort is the arithmetic mean of V1 CABIN_RANK across long-haul legs, with its
histogram retained. This is an explicitly ordinal structural metric, not flight
hours or a monetary utility. No long-haul legs means null. Sector and transfer
burden comes from actual candidate structure; no reposition legs are generated.
Destination full days stay null when PR1 has no flight-based estimate.

Leave efficiency is calendar travel days / summed traveler leave-person-days.
A zero denominator yields null plus zero_leave=true, never Infinity. Per-traveler
leave-by-year is authoritative; this ratio does not merge annual entitlements.

Each view emits separate budget_feasible and conditional ID arrays, bounded by
max_per_view **per channel**. Trip counts are round-robined first; holiday/cabin/
price classes are diversified inside each count. With a small cap, not every
class can be guaranteed. Views are transparent orderings, not a universal ranking:

- **Miles Saver**: complete known mileage first, within price-evidence classes;
  no total-cost claims when taxes/quotes are missing. Unknown subtotals never rank
  as full itinerary mileage.
- **Comfort First**: higher mean long-haul cabin rank, then trip count.
- **Balanced**: nondominated diversity across trip counts/families/cabins, no score.
- **Leave Efficient**: zero-leave alternatives, then efficiency and calendar days.

A portfolio can appear in several views. In the committed synthetic example, the
Miles Saver view includes 1/2/3 Y trips at 4,000/8,000/12,000 group miles. Comfort,
Balanced and Leave Efficient preserve other travel/cabin/leave tradeoffs within
the fictional 24,000-mile combined account snapshot.

## Bounds and determinism

config/portfolio_config.json has max_states=5000, max_allocation_states=20000,
max_windows=30, max_candidates_per_window=10, max_candidates_total=100 and
max_per_view=5. The sample explicitly supplies smaller/different bounds. These
are search limits, never award rules. The old portfolio placeholders inside the
PR1/PR2 search config do not replace this separate PR4 contract.

The candidate unit is a **concrete window_id**, not a holiday family or anchor.
Every retained selected window receives up to max_candidates_per_window candidates
before the global max_candidates_total cap. Neither the CLI nor the direct
portfolio API applies a second family-wide cap. The global cap round-robins window
IDs: when it has at least one slot per eligible window, no such window loses all
candidates merely because another window's candidate IDs sort earlier. If global
capacity is smaller than the number of windows, some windows necessarily disappear;
search_truncated and per-window counts disclose that loss. max_windows remains a
separate upstream limit; no candidate guarantee applies to unselected windows.

The former PR4 setting max_candidates_per_holiday is rejected with a migration
message; rename it to max_candidates_per_window. There is no implicit family cap
or compatibility alias. Existing unused portfolio placeholders in the unchanged
PR1/PR2 search_config.json are not PR4 controls. The synthetic example removes that
unused search-config section and uses the explicit PR4 field only.

The CLI reports orchestration_candidate_counts_by_window and the direct optimizer
reports candidate_counts_by_window, each with before_window_cap, after_window_cap
and after_global_cap. The latter counts viable supplied results after PR3/calendar
revalidation, which runs linearly over the supplied list before retention caps.
Global portfolio enumeration still receives at most max_candidates_total trips.
Preserving multiple windows does not permit booking them as multiple trips for
the same holiday: the existing family/anchor exclusion remains in force. It keeps
alternatives for annual leave/comfort tradeoffs, including a later zero-leave
window when an earlier window would exhaust another holiday's leave allowance.

Portfolio states include attempted invalid combinations; funding states include
reserved/generated branches and share one cap across all portfolios/eligibility
searches. Windows/candidates are capped with deterministic diversity before PR3
pricing. Search truncation propagates PR1/PR2 caps, candidate/window caps and
portfolio/allocation caps. Diagnostics report bounds, rejection counts, retained
candidates and states. These bounded results never promise a global optimum or
prove an unsearched route/portfolio impossible.

Portfolio IDs bind selected candidate/evaluation identities, normalized request,
yearly budgets, balances and supplied funding attestations. Input party/account/
calendar/route order does not change substantive results or IDs. Raw snapshot
metadata digests can change with raw snapshot ordering, intentionally disclosing
that input detail. Replaying identical JSON produces identical serialized output.

## Remaining scope

No live availability, automatic booking, partner pricing/eligibility verification,
D2 award assembly, cash/ground hybrids, UI or guaranteed exhaustive optimization.
Calendar coverage and budget years must be supplied. The single planning year
selects holiday anchors; adjacent snapshots support cross-year windows, not an
automatic multi-year holiday search. Account allocation is bounded and may remain
conditional at its limit. Full cost comparison is deliberately conservative.
