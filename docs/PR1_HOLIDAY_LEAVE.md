# V2 Alpha PR1 — Holiday Calendar + Leave Engine

Implemented milestone 1 only. V1.1 pricing, schemas and search config are unchanged.
No route discovery, candidate adaptation, portfolio optimizer or planner CLI is
included in this milestone. No third-party runtime dependency is required.

## Interfaces

- `discovery.holiday_calendar.load_calendar(mapping_or_json_path)` validates one
  annual snapshot against `schemas/holiday_calendar.schema.json`.
- `load_calendars(iterable_of_mappings_or_paths)` combines annual snapshots of
  the same jurisdiction. Supply adjacent years for cross-year windows. Duplicate
  years/dates and dates outside their snapshot year are ambiguous and rejected.
- `calendar.day("YYYY-MM-DD")` returns explicit day data or weekday/weekend
  fallback, including source status, URL, observation time, calendar identity,
  snapshot status and an inference flag. Missing years raise
  `CalendarCoverageError`; an absent snapshot is never treated as an empty
  official calendar.
- `evaluate_window(calendar, travel_request, start_date, end_date)` calculates
  one inclusive window's leave, blocked-date/budget/length errors and evidence.
  It is an arithmetic interface; holiday-anchor membership and bridge policy
  are checked by the generator, not this standalone calculator.
- `generate_windows(calendar, travel_request, config=None)` validates the full
  existing Travel Request contract and returns `windows`, `diagnostics` and
  `metadata`. It reads holiday search bounds from `config/search_config.json`
  by default; a supplied config must contain the existing `holiday_window`
  section. Other modules' config is not interpreted here.
- `prune_windows(windows)` exposes the same deterministic dominance rule used
  during generation; it expects valid generated window structures.

Example using **TEST-only fixtures**, not a real holiday calendar:

```python
from discovery.holiday_calendar import load_calendars
from discovery.leave_engine import generate_windows

calendar = load_calendars([
    "tests/fixtures/holiday_calendar_test_2026.json",
    "tests/fixtures/holiday_calendar_test_2027.json",
])
# request is a mapping conforming to schemas/travel_request.schema.json.
result = generate_windows(calendar, request)
```

The standard-library validator reads the existing schema files and implements
only their used keywords, including required/additional properties, types,
enums, array uniqueness, numeric bounds, patterns and date/date-time formats.
It is not a general-purpose Draft 2020-12 implementation. Unsupported keywords
encountered during validation fail explicitly rather than being ignored.
`ValidationError` is raised for invalid input; schemas have not been relaxed.

## Calendar and traveler precedence

1. Explicit snapshot entries override generic weekdays/weekends. MAKEUP_WORKDAY
   on a Saturday/Sunday consumes leave. The loader never creates makeup entries.
2. Calendar BLOCKED_DAY or a traveler's blocked_dates excludes that traveler from
   the window, even when it is also a holiday/personal day off.
3. A traveler's personal_days_off overrides a workday or makeup workday.
4. WORKDAY and MAKEUP_WORKDAY consume one leave day. PUBLIC_HOLIDAY, WEEKEND and
   PERSONAL_DAY_OFF consume none. A calendar PERSONAL_DAY_OFF applies to all
   travelers; traveler-specific overrides belong in the Travel Request.
5. Exact leave dates and counts are separate for each traveler. Their budgets
   are never pooled.

Per-day source_status overrides the snapshot status for that day. Window
`holiday_status=ESTIMATED` and `holiday_uncertainty=true` remain conservative if
ANY used day **or its supplying snapshot** is ESTIMATED, even when a day in that
snapshot is individually OFFICIAL. Evidence is copied into each result; personal
leave overrides never upgrade holiday evidence. OFFICIAL is supplied evidence,
not an independent verification performed by this code.

## Enumeration, budgets and bounds

`holiday_name` on PUBLIC_HOLIDAY entries must use the selected canonical
`holiday_types` code (new_year, qingming, labor_day, dragon_boat, national_day;
optional spring_festival/mid_autumn). Free-form names remain legal calendar data
but are not guessed into festival types. Missing anchors yield
`HOLIDAY_ANCHOR_MISSING`, not invented festival dates.

For each family in planning_year, the neighborhood spans its first/last explicit
public-holiday anchor plus configured days_before/days_after. Every enumerated
continuous window includes at least one of those anchors. Trip length constraints
apply inclusively. With no supplied length limits, minimum is one day and maximum
is the bounded neighborhood length. `allow_bridge_leave` defaults to true; false
rejects windows requiring leave outside the family's first/last public-holiday
anchor. Non-working surrounding days can still extend a zero-leave window.

Each feasible window is checked independently against every traveler's
annual_leave_budget and optional max_leave_days_per_trip. For cross-year windows,
ALL required leave dates count against that single supplied budget as a
conservative per-window ceiling. `budget_scope` says
`SINGLE_WINDOW_ALL_DATES_NOT_ANNUAL_PORTFOLIO`. This neither allocates leave to
separate years nor reserves annual leave across multiple trips; PR4 owns that.

If a neighbor year's snapshot is missing, windows using it are skipped and
`CALENDAR_YEAR_MISSING` diagnostics are returned; fully covered windows remain
available. If none survive, `NO_FEASIBLE_WINDOWS` includes rejection counts
(BLOCKED_DATE, LEAVE_BUDGET_EXCEEDED, PER_TRIP_LEAVE_EXCEEDED,
TRIP_LENGTH_OUT_OF_BOUNDS, BRIDGE_LEAVE_DISABLED as applicable).

## Pruning and stable output

A window dominates another only when its duration is equal/longer, leave is no
higher for EVERY traveler, and at least one dimension is strictly better. Prune
only within the same holiday anchor, bridge direction (BEFORE/AFTER/BOTH/CORE)
and holiday evidence status. This preserves pre/post alternatives and traveler
trade-offs. Date-distinct ties survive. Different evidence states are not ranked
as interchangeable facts.

After pruning, the configured max_generated_windows_per_holiday cap is applied
with deterministic round-robin selection across bridge directions, longer windows
first within a direction (then traveler-id-ordered leave counts and date/id ties).
`truncated_by_config` exposes any truncation; a tight cap cannot promise every
alternative or global optimality. No opaque weighted score is used.

Window IDs hash normalized window content, including dates, sorted traveler
results and evidence. Reordering traveler inputs or annual snapshots does not
change output. A changed evidence snapshot may change IDs, intentionally.

Each window separately reports calendar_trip_days, leave_days_by_traveler and
leave_dates_by_traveler. estimated_destination_full_days and estimated_transit_days
are **null** with explicit day_estimate_assumptions until flight information is
available. This milestone makes no claims about route, award-seat, pricing or
ticketability evidence.

## Tests and data boundaries

```bash
python3 -B -m unittest discover -p 'test_*.py' -v
```

`tests/__init__.py` ensures root discovery includes V2 tests alongside V1.1.
All committed holiday fixtures use jurisdiction TEST and explicit synthetic ids
and source URLs. Their dates/day types are test arrangements, not real government
announcements. No official 2027 China holiday calendar was fabricated.
