# AGENTS.md — Asia Miles Optimizer

## Source of truth
GitHub is the executable code, schemas, rules, tests and design Source of Truth. AndreOS is discovery/context/checkpoint only.

## Read order
Before changing code, read:
1. `SKILL.md`
2. `README.md`
3. `docs/V2_DESIGN.md`
4. `docs/V2_IMPLEMENTATION_PLAN.md`
5. latest applicable `rules_*.json`
6. schemas/config relevant to the task
7. existing tests

## Non-negotiable architecture
- V1.1 `optimizer.py` remains the deterministic pricing/validation kernel. Do not duplicate its policy rules in V2.
- V2 discovers travel windows and candidate itineraries, then adapts candidates into V1.1 scenarios for deterministic evaluation.
- Policy/rule data belongs in versioned rule files; search-performance knobs belong in config; user preferences belong in request input.
- Holiday facts, route facts, award inventory and ticketability are separate evidence dimensions.
- Never infer award-seat availability from route existence.
- Never infer ticketability from local rule validation.
- Unknown cost is unknown, never zero.
- ESTIMATED holidays must never be presented as official.
- Unverified routes must never be presented as verified.
- A theoretical multi-trip ticket must not enter strict price ranking as confirmed ticketable.

## V2 Alpha scope
P0:
- Holiday Calendar + Leave Engine
- travel-window generation for New Year, Qingming, Labor Day, Dragon Boat and National Day; Spring Festival/Mid-Autumn optional
- two-traveler independent leave budgets and blocked dates
- route graph with evidence metadata
- standard award candidate generation including J/W/Y mixed cabins, asymmetric outbound/return and separate tickets
- adapter into V1.1 `evaluate()`
- deterministic candidate pruning and Pareto-safe comparison

P1:
- oneworld multi-carrier candidate generation
- hybrid award + cash/ground candidates
- annual holiday portfolio optimization
- theoretical multi-trip award structures

Out of Alpha:
- login/account scraping
- live award inventory
- automatic booking/ticketing
- global exhaustive search
- UI
- unsupported new pricing algorithms

## Evidence states
Use independent fields, not one overloaded status:
- holiday: OFFICIAL | ESTIMATED
- route: VERIFIED | STALE | UNVERIFIED
- pricing: RULE_VERIFIED | RULE_ESTIMATED | QUOTED | UNKNOWN
- award seats: VERIFIED | NOT_CHECKED | UNAVAILABLE | UNKNOWN
- ticketability: CONFIRMED | NEEDS_AIRLINE_VALIDATION | NOT_CHECKED

## Development rules
- Standard Python first; avoid new dependencies unless justified.
- Same input + same rules + same data snapshot must produce deterministic candidates/results.
- Candidate IDs must be stable for identical normalized inputs.
- Every new behavior needs regression tests.
- Do not weaken V1.1 validation merely to make generated candidates pass.
- If V1.1 lacks a legitimate pricing behavior, document the gap and add rule evidence/tests before changing the kernel.
- Keep real credentials, account identifiers and personal balances out of committed examples.
- Generated output/cache files stay untracked.

## Required completion report
For every implementation task report: files changed, behavior added, tests before/after, rule/schema changes, unresolved limitations, branch, commit SHA and whether acceptance is PASS / CONDITIONAL PASS / FAIL.
