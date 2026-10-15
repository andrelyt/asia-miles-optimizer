# V2.0 Alpha — Implementation Plan for Codex

This file defines what remains for the coding agent after product/architecture contracts have been fixed.

## Baseline
Start from main after V1.1 PASS. Run the complete existing suite before changes and record the count. Do not modify AndreOS Canonical Memory.

## PR / milestone 1 — Holiday Calendar + Leave Engine

Suggested modules:
- `discovery/holiday_calendar.py`
- `discovery/leave_engine.py`
- `tests/test_holiday_calendar.py`
- `tests/test_leave_engine.py`

Implement:
- load/validate holiday-calendar schema
- weekday/weekend fallback
- explicit OFFICIAL/ESTIMATED override
- MAKEUP_WORKDAY precedence
- traveler blocked/personal days
- continuous window enumeration
- exact leave dates and leave counts per traveler
- deterministic dominance pruning
- cross-year window support

Do not fabricate a 2027 official China holiday calendar. Fixtures may be synthetic and clearly marked TEST/ESTIMATED.

Acceptance cases:
- normal weekend
- official public holiday
- weekend makeup workday
- pre-holiday bridge leave
- post-holiday bridge leave
- two travelers with different blocked dates/budgets
- zero leave
- budget exceeded
- cross-year window
- ESTIMATED status propagates

## PR / milestone 2 — Route Graph + Standard Candidate Generator

Suggested modules:
- `discovery/route_graph.py`
- `discovery/candidate_generator.py`
- `tests/test_route_graph.py`
- `tests/test_candidate_generator.py`

Implement route schema loading and bounded path discovery.
Generate at minimum:
- all-J
- long-J/short-Y
- long-W/short-Y
- all-W where route supports W
- Y baseline
- outbound-J/return-W
- outbound-W/return-J
- separate-award variants

Requirements:
- no unsupported cabin on an edge
- no invented route
- stable candidate IDs
- deterministic ordering
- search limits from `config/search_config.json`
- UNVERIFIED edges propagate route evidence state

## PR / milestone 3 — Candidate Adapter + V1.1 Integration

Suggested:
- `discovery/v1_adapter.py`
- `tests/test_v1_adapter.py`
- end-to-end fixtures

Map V2 candidate structures to existing V1.1 scenario schema. Reuse `evaluate()`.

Requirements:
- do not duplicate award charts/oneworld policy constants
- preserve same-ticket mixed vs separate-ticket semantics
- preserve independent passenger/account balances
- unknown costs stay unknown
- if candidate cannot be represented safely in V1.1, fail with explicit ADAPTER_UNSUPPORTED rather than approximating

If legitimate support requires kernel changes, make the smallest separately tested V1.1-compatible change and document why.

## PR / milestone 4 — Portfolio + CLI

Suggested:
- `discovery/portfolio.py`
- `planner.py`
- `tests/test_portfolio.py`
- `tests/test_planner_e2e.py`

Implement:
- combine holiday windows + candidates
- annual leave/miles constraints
- no overlapping trips
- evidence-aware Pareto pruning
- recommendation views: Miles Saver, Comfort First, Balanced, Leave Efficient
- machine-readable JSON output

Do not add an opaque universal score in Alpha.

## P1 after P0 acceptance
- bounded oneworld multi-carrier structural generator
- hybrid cash/ground reposition candidates
- annual multi-holiday portfolio depth
- theoretical multi-trip award structures

## End-to-end acceptance fixture
Synthetic planning year; 2 travelers; independent leave/miles budgets; 5 holiday families; long-haul minimum W/preferred J; short-haul minimum Y; several verified and unverified route edges.

Expected:
- multiple feasible holiday windows
- at least 3 meaningfully different standard-award strategies when data supports them
- V1.1 evaluates adapted candidates
- invalid candidates are explained
- incomplete costs are not falsely ranked as cheapest
- ESTIMATED holiday and UNVERIFIED route labels survive to final JSON
- rerun is deterministic

## Completion discipline
For each milestone:
1. baseline tests
2. implement
3. add regression tests
4. run full suite
5. inspect diff and generated files
6. commit cleanly
7. report commit SHA + PASS/CONDITIONAL PASS/FAIL

Do not implement future milestones opportunistically unless required for a clean interface.
