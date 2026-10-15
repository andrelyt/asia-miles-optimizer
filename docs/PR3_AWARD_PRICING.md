# V2 Alpha PR3 — Award Pricing Adapter

This implements the PR3 acceptance spec around the unchanged V1.1 kernel.
Standard Python only; no live searches, partner integration, booking, portfolio,
new award charts, Category 2 inference or alternative rounding algorithm.

## Interfaces

```python
from discovery.award_adapter import adapt_candidate, rules_digest
from discovery.award_pricing import price_candidate

mapped = adapt_candidate(candidate, request, rules, evidence=supplied_evidence,
                         balances_by_account=account_snapshot)
priced = price_candidate(candidate, request, rules, evidence=supplied_evidence,
                         balances_by_account=account_snapshot)
```

`candidate` is an unchanged PR2 generated candidate, not a V1 scenario. `request`
uses the existing travel-request schema. The adapter checks candidate content
against its stable ID, traveler identities, path continuity, selected destination,
allowed origins, current mixed/separate preferences and canonical PR2 ticket
partition/policy. It reuses PR2 policy/grouping helpers rather than copying award
limits. It rejects combined-roundtrip, oneworld, hybrid and arbitrary regrouping
instead of approximating their semantics. Supported roundtrip candidates retain
one proposed award per direction, or independent per-sector awards.

`adapt_candidate` returns `READY_FOR_EVALUATION` only when every ticket can be
mapped. It does not run the whole V1 scenario. `price_candidate` then calls
`optimizer.evaluate(scenario, rules, settings)` once. For partial ticket resolution,
the existing `mixed_cabin_price` kernel function can provide a per-ticket estimate;
no second price or rounding formula exists in V2. A mixed ticket is re-evaluated by
V1 when the whole scenario becomes ready. `v1_evaluated` records that distinction.
Neither function mutates its inputs or rewrites Candidate IDs. Separate evaluation
IDs bind the candidate, normalized request, actual rules, evidence and balances.
Ordering of traveler IDs, object keys and account keys does not change results.

## Explicit supplementary evidence contract

The optional `evidence` mapping has these keys:

| Key | Contents |
| --- | --- |
| `rule_review` | Explicit supplied applicability review of the selected rule content for booking and travel dates |
| `quotes` | Mapping of candidate `ticket_id` to a whole-ticket, per-person airline mileage quote |
| `ticket_data` | Mapping of candidate `ticket_id` to missing mixed-ticket inputs |
| `tax_quote` | One whole-candidate, per-person HKD tax/surcharge quote, covering all tickets |

A source record needs `source_url` (HTTP(S) with host), `observed_at` (timezone-aware
ISO datetime) and `evidence_level`. These are **caller-supplied attestations**;
this package does not retrieve URLs, corroborate sources or establish freshness.
Public output makes this explicit through
`evidence_verification_status=SUPPLIED_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED`.
AIRLINE_QUOTED and manual applicability reviews do not authenticate an airline
quote, its source domain, or official approval of future rule applicability.
A live external check is still required where appropriate. There is no invented
quote expiry duration. Quote prices must apply equally to every traveler on the
shared itinerary; traveler-specific fare or cabin differences are unsupported.

Every review, quote and mixed-ticket-data entry binds:

- `candidate_id`: the unmodified PR2 ID;
- `rules_digest`: `rules_digest(rules)`, which binds actual content, not a filename;
- `rules_version`, `rules_as_of`: the exact snapshot metadata;
- `booking_date`, `travel_start_date`, `travel_end_date`: explicit ISO dates.

Quote and ticket-data dates must equal the rule review's dates. Evidence is keyed
by exact ticket ID; stale keys or evidence for another candidate/rule/date cannot
silently price the current structure. All supplied valid evidence is retained in
`input_evidence`, with ticket-level copies in `tickets[].evidence`.

### Rule applicability

`rule_review` additionally needs `decision="APPLICABLE"` and
`evidence_level="SUPPLIED_CONFIRMED"` with source and time. Booking must not follow
travel start; the travel interval must cover the request planning year. When a
holiday window is supplied, the review's travel endpoints must match it, including
cross-year windows. These dates scope the supplied applicability review; they do
not validate flights or turn PR2 window assumptions into actual schedules.

The current rules' `as_of` is not an effective booking/travel range. Therefore,
**even a 2026 scenario requires an explicit review**, and 2027 never silently uses
a 2026 chart. Missing/wrongly scoped review returns RULE_VERSION_REVIEW_REQUIRED
without pricing tickets. SUPPLIED_CONFIRMED is an attestation of the review,
not an assertion that this code verified official applicability.

### Ordinary Standard quotes

A quote needs `evidence_level="AIRLINE_QUOTED"` and strictly positive integer
`miles_per_person`, plus the source, scope and dates above. The adapter uses this
number as V1 `standard` input and reports QUOTED. The internal V1 `verified` input
flag merely records this supplied quote classification; it is not independent
verification. A one-sector quote and a two-sector whole-ticket quote stay distinct.
Without the quote, miles remain null / pricing UNKNOWN / NEEDS_AIRLINE_QUOTE.
Zero/nonpositive or otherwise invalid Standard mileage returns NEEDS_DATA with
INVALID_STANDARD_QUOTE_MILES on the affected ticket. That ticket contributes no
known mileage subtotal; any valid other ticket is retained only as a partial
subtotal. The whole scenario does not enter V1 evaluation or complete comparison.
Zero quoted taxes and zero account balances remain valid numeric inputs.
No ordinary Standard price is derived from distance charts. THIRD_PARTY_OBSERVED,
assumption values, wrong rule bindings and missing provenance do not become quotes.

### CX mixed-cabin estimates

The candidate must fit current PR2 structural policy and existing
`standard_mixed_constraints`. `ticket_data[ticket_id]` requires:

- the candidate/rule/date bindings above;
- numeric `transfer_hours` plus `transfer_evidence` (a SUPPLIED_CONFIRMED source record);
- `distance_confirmations`: mapping from string **global candidate leg index** to a
  SUPPLIED_CONFIRMED source record with `distance_miles` equal to that leg's value;
  the leg must also retain nonempty `distance_source`;
- when the applicable existing chart band requires a type, `route_type` and
  `route_type_evidence` (SUPPLIED_CONFIRMED source record). A supplied type in any
  band also requires evidence. The adapter does not infer type from countries.

The kernel validates numerical limits, supported chart cells and types and does
all proportional arithmetic and rounding. Missing inputs return NEEDS_DATA;
existing kernel representability failures return UNSUPPORTED with the kernel
reason. An otherwise successful mixed price is always RULE_ESTIMATED, with an
explicit airline-quote requirement. Even with quoted taxes it cannot enter strict
complete-price comparison.

### Partners and separate awards

CX+partner, partner+CX and partner-only candidates remain NEEDS_AIRLINE_QUOTE with
PARTNER_AGREEMENT_REQUIRED and CARRIER_REDEMPTION_ELIGIBILITY_REQUIRED. This Alpha
adapter intentionally does **not** resolve partner agreements or accept a supplied
partner quote as sufficient to evaluate a partner ticket. It retains such evidence
for later review. It never applies the CX-only mixed formula to partner metal.
Different non-CX carriers sharing a Standard ticket are rejected by the existing
versioned PR2 policy, not because missing prices made the route invalid. Separate
partner awards remain independent unresolved tickets.

SEPARATE_AWARDS maps every sector to its own V1 `standard` quote. A three-sector
outbound path can be three independent awards plus the return; it cannot be
combined into a three-sector Standard ticket. There is no split-point planner.

## Travelers and payment accounts

`request.travelers[].id` remains the passenger identity. Pass
`balances_by_account={account_id: balance_miles}` explicitly; the adapter never
imports `request.travelers[].miles_balance` as an implicit payment-account snapshot.
The existing request schema is unchanged and still requires that legacy field.
This separation permits accounts whose owners are not passengers and supports
unknown account balances without changing the PR1/PR2 schema.

V1 enumerates payments independently for every passenger/ticket pair. Each pair
is paid wholly by one account; accounts are never pooled to fund a single pair.
An account may fund either traveler mathematically. Beneficiary eligibility is
outside local validation: `funding_eligibility_status=NOT_CHECKED` always.

None, an empty mapping or any null balance means the complete balance snapshot
is unknown. Known amounts are retained, but V1 receives no balance constraint and
reports NOT_CHECKED, never INSUFFICIENT. With all balances known, V1 returns FEASIBLE
and explicit payer/passenger/ticket allocations, or INSUFFICIENT. The latter yields
NEEDS_DATA + ACCOUNT_BALANCE_INSUFFICIENT while preserving valid mile requirements.
A zero known balance is a real constraint, not unknown. Negative, fractional,
nonfinite, string and boolean mileage/balance values are rejected.

The V1 account enumeration remains exponential: this Alpha interface targets small
shared-itinerary groups and ticket counts, not large account optimizations.

## Outputs and interpretation

`price_candidate` returns one primary status; read ticket statuses/diagnostics as
well. Applicability review gates pricing first; then unsupported structures or
missing data take precedence over missing quotes. Candidate evidence is retained.

| Status | Meaning |
| --- | --- |
| EVALUATED | Whole ready scenario ran through V1 without validation/funding errors; still no seat/ticketability confirmation |
| RULE_VERSION_REVIEW_REQUIRED | Booking/travel applicability not supplied or not safely scoped |
| NEEDS_DATA | Missing/invalid inputs, or explicit insufficient account allocation |
| NEEDS_AIRLINE_QUOTE | Ordinary quote missing/untrusted, or partner pricing/agreement pending |
| UNSUPPORTED | Ticket structure or current V1 representation/validation cannot be used safely |

Read the distinct numeric layers:

- `tickets[].miles_per_person`, `tickets[].group_miles` are individual ticket requirements;
- `per_person_miles`, `miles_by_traveler`, `group_miles` are complete itinerary requirements;
- incomplete itinerary totals are null; `known_miles_subtotal_per_person` and
  `known_group_miles_subtotal` count only resolved ticket requirements, never full costs;
- `account_allocation` separates payer and passenger; account status is independent;
- `taxes_hkd_per_person` is null unless a correctly scoped AIRLINE_QUOTED tax record
  supplies `hkd_per_person`. An explicitly sourced zero is allowed, never invented.

`holiday_status`, `route_status`, `pricing_status`, `award_seat_status` and
`ticketability_status` remain separate. ESTIMATED holidays and STALE/UNVERIFIED
routes survive unchanged. VERIFIED continues to mean supplied snapshot evidence
only. Seats and ticketability remain NOT_CHECKED, even when the mileage quote is
present and the kernel succeeds.

The **top-level** `complete_price_comparison_eligible` is authoritative. It requires
successful evaluation, all ticket prices QUOTED and complete quoted cash/taxes.
All mixed estimates, partial prices, assumptions and validation failures are false.
A true value compares only the supplied complete cost model, not confirmed
bookability. `kernel_result` is the unmodified V1 return; its own completeness flag
only describes V1's declared cash-cost model, so it may differ for mixed estimates.
Do not rank using that nested flag. EVALUATED and validation_scope=V1_INPUT_MODEL_ONLY describe the represented
V1 checks, not a comprehensive airline-rule check. PR2 schedule, one-way geography
and transfer requirements are not erased by a quoted price. No ranking or
portfolio is implemented here.

## Synthetic examples and third-party comparisons

`tests/_award_fixtures.py` builds exclusively synthetic TEST candidates, evidence,
quotes and accounts. A runnable synthetic example is:

```python
from tests._award_fixtures import candidate, evidence
from discovery.award_pricing import price_candidate

c, request, rules = candidate("LONG_J_SHORT_Y")
result = price_candidate(c, request, rules, evidence(c, request, rules),
                         balances_by_account={"TEST_EXTERNAL_PAYER": 1000000})
assert result["pricing_status"] == "RULE_ESTIMATED"
assert result["award_seat_status"] == "NOT_CHECKED"
assert not result["complete_price_comparison_eligible"]
```

The example's confirmations and quotes are fictional test attestations using
example.invalid; they must never be reused as real travel evidence. The integration
test runs an actual synthetic PR1 window -> PR2 candidate -> PR3 -> V1 flow with
ESTIMATED holidays and STALE route evidence, without personal data.

`tests/fixtures/flyasia_pr3_comparisons.json` preserves eight historical Muse/Grok
comparison vectors, source/time/report references and THIRD_PARTY_OBSERVED tagging.
Replays use displayed rounded distances and synthetic airport chains, not real
route assertions. Current vectors match the recorded outputs; FLYASIA_MATCH does
not mean OFFICIAL_RULE_VERIFIED. A separate synthetic hundred-boundary probe
preserves V1 18,000 versus 18,100 implied by the reported FlyAsia implementation.
That second value is explicitly an implementation inference, **not a UI observation**.
The partner toggle's reported 31,700 is retained as research and never fed into
pricing. Tests cover total-distance band and reversed cabins; Category 2 is explicit
fixture input, never inferred from third-party country lists. Any future mismatch
is a rule-review finding; rounding, Category 2 and pricing tables are unchanged.

Run all regressions:

```bash
python3 -B -m unittest discover -p 'test_*.py' -v
```


## Phase 2B-2 optional planning layer

The ordinary Standard quote and applicability contracts above remain the default
and are unchanged in award_adapter.py. The public price_candidate wrapper can now
accept an explicit reference_chart. Its separate estimate channel is documented in
[REFERENCE_CHART_ESTIMATE.md](REFERENCE_CHART_ESTIMATE.md). It may return
status/pricing_status RULE_ESTIMATED while preserving official_pricing_status,
quote=null and quoted totals=null. This is an explicit opt-in exception for
planning reference arithmetic, not a new source of ordinary Standard quotes.
