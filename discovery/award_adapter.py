"""Fail-closed PR2 -> V1.1 mapping. Supplied evidence is never independently verified."""
import copy
import re
from datetime import datetime
from urllib.parse import urlparse

from optimizer import CABIN_RANK, mixed_cabin_price, number
from ._validation import ValidationError, parse_date, validate
from .candidate_generator import _destinations, _standard_policy, _tickets, _window
from .route_graph import route_status, stable_id


def rules_digest(rules):
    """Bind reviews/quotes to the actual rule content, not just a reusable filename."""
    return stable_id("rules_", rules)


def sourced(value, levels):
    if not isinstance(value, dict) or value.get("evidence_level") not in levels:
        return False
    try:
        url = urlparse(value.get("source_url", ""))
        timestamp = datetime.fromisoformat(value.get("observed_at", "").replace("Z", "+00:00"))
        return url.scheme in ("http", "https") and bool(url.netloc) and timestamp.utcoffset() is not None
    except (ValueError, TypeError, AttributeError):
        return False


def _bound(value, candidate, rules):
    return (isinstance(value, dict) and value.get("candidate_id") == candidate["candidate_id"] and
            value.get("rules_digest") == rules_digest(rules) and
            value.get("rules_version") == rules.get("version") and
            value.get("rules_as_of") == rules.get("as_of"))


def _dated(value, candidate, rules, review):
    return _bound(value, candidate, rules) and all(value.get(k) == review[k]
        for k in ("booking_date", "travel_start_date", "travel_end_date"))


def _reviewed(review, candidate, request, rules):
    if not (_bound(review, candidate, rules) and sourced(review, {"SUPPLIED_CONFIRMED"}) and
            review.get("decision") == "APPLICABLE"):
        return False
    try:
        if not isinstance(rules.get("version"), str) or not rules["version"]:
            return False
        parse_date(rules["as_of"])
        start, end, booking = [parse_date(review[k]) for k in ("travel_start_date", "travel_end_date", "booking_date")]
        if start > end or booking > start or not start.year <= request["planning_year"] <= end.year:
            return False
        window = candidate.get("holiday_window")
        return not window or (review["travel_start_date"] == window["start_date"] and
                              review["travel_end_date"] == window["end_date"])
    except (ValueError, KeyError, TypeError):
        return False


def _validate_candidate(candidate, request, rules):
    validate(request, "travel_request.schema.json")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("candidate_id"), str):
        raise ValidationError("candidate_id required")
    shape = {k: v for k, v in candidate.items() if k not in ("candidate_id", "strategies")}
    if stable_id("candidate_", shape) != candidate["candidate_id"]:
        raise ValidationError("candidate content differs from its stable ID")
    travelers = [t["id"] for t in request["travelers"]]
    if len(set(travelers)) != len(travelers) or sorted(travelers) != candidate.get("traveler_ids"):
        raise ValidationError("candidate/request traveler identities differ or repeat")
    if candidate.get("origin") not in request["origin_airports"]:
        raise ValidationError("candidate origin not permitted")
    if candidate.get("destination") not in _destinations(request, []):
        return "CANDIDATE_DESTINATION_NOT_REQUESTED"
    legs, tickets = candidate.get("legs"), candidate.get("tickets")
    if not isinstance(legs, list) or not legs or not isinstance(tickets, list) or not tickets:
        raise ValidationError("nonempty candidate legs/tickets required")
    for leg in legs:
        if not isinstance(leg, dict):
            raise ValidationError("invalid leg")
        for key in ("origin", "destination"):
            if not isinstance(leg.get(key), str) or not re.fullmatch("[A-Z]{3}", leg[key]):
                raise ValidationError("invalid airport")
        if (leg.get("direction") not in ("outbound", "return") or
                leg.get("cabin") not in CABIN_RANK or leg["cabin"] not in leg.get("cabins", []) or
                not isinstance(leg.get("operating_carrier"), str) or not leg["operating_carrier"]):
            raise ValidationError("invalid leg cabin/carrier/direction")
        number(leg.get("distance_miles"), "distance", positive=True)
        if leg.get("route_status") not in ("VERIFIED", "STALE", "UNVERIFIED"):
            raise ValidationError("invalid route evidence status")
        url = urlparse(leg.get("source_url") or "")
        if leg["route_status"] == "VERIFIED" and not (url.scheme in ("http", "https") and url.netloc):
            raise ValidationError("VERIFIED route lacks supplied source")
    directions = [l["direction"] for l in legs]
    if "outbound" not in directions or "return" not in directions or directions != sorted(directions):
        raise ValidationError("outbound followed by return required")
    out = [l for l in legs if l["direction"] == "outbound"]
    back = [l for l in legs if l["direction"] == "return"]
    if (legs[0]["origin"] != candidate["origin"] or legs[-1]["destination"] != candidate["origin"] or
            out[-1]["destination"] != candidate["destination"] or back[0]["origin"] != candidate["destination"] or
            any(a["destination"] != b["origin"] for a, b in zip(legs, legs[1:]))):
        raise ValidationError("candidate path discontinuity/endpoints")
    if candidate.get("route_status") != route_status(legs):
        raise ValidationError("candidate route status differs from leg evidence")
    window = _window(candidate.get("holiday_window"))
    if (window != candidate.get("holiday_window") or
            candidate.get("holiday_status") != (window["holiday_status"] if window else None)):
        raise ValidationError("candidate holiday status differs from window evidence")
    mode = candidate.get("ticketing_mode")
    if mode not in ("SINGLE_AWARD", "SEPARATE_AWARDS"):
        return "ADAPTER_TICKETING_MODE_UNSUPPORTED"
    if mode == "SEPARATE_AWARDS" and not request["cabin_preferences"]["allow_separate_tickets"]:
        return "SEPARATE_TICKETS_NOT_ALLOWED"
    if not request["cabin_preferences"]["allow_mixed_cabin"] and any(
            len({l["cabin"] for l in legs if l["direction"] == d}) > 1 for d in ("outbound", "return")):
        return "MIXED_CABIN_NOT_ALLOWED"
    policy = _standard_policy(rules)
    if policy is None:
        return "STANDARD_AWARD_POLICY_REQUIRED"
    expected, rejection = _tickets(legs, mode, rules.get("standard_mixed_constraints"), policy)
    if rejection:
        return rejection["code"]
    if len(tickets) != len(expected):
        return "ADAPTER_TICKET_GROUPING_UNSUPPORTED"
    for actual, canonical in zip(tickets, expected):
        if not isinstance(actual, dict) or any(actual.get(k) != canonical[k]
                for k in ("ticket_id", "direction", "leg_indices", "proposed_scheme")):
            return "ADAPTER_TICKET_GROUPING_UNSUPPORTED"
        # Python bool compares equal to 0/1; it is never a valid leg index.
        if any(type(i) is not int for i in actual["leg_indices"]):
            return "ADAPTER_TICKET_GROUPING_UNSUPPORTED"
    return None


def _ticket(ticket, candidate, rules, inputs, quotes, review):
    tid = ticket["ticket_id"]
    legs = [candidate["legs"][i] for i in ticket["leg_indices"]]
    data = inputs.get(tid, {})
    row = {"ticket_id": tid, "direction": ticket["direction"], "leg_indices": list(ticket["leg_indices"]),
           "status": "NEEDS_AIRLINE_QUOTE", "pricing_status": "UNKNOWN", "miles_per_person": None,
           "diagnostics": [], "evidence": {"ticket_data": copy.deepcopy(data), "quote": copy.deepcopy(quotes.get(tid))}}
    primary = rules["standard_award_constraints"]["primary_carrier"]
    if any(l["operating_carrier"] != primary for l in legs):
        row["diagnostics"] = ["PARTNER_AGREEMENT_REQUIRED", "CARRIER_REDEMPTION_ELIGIBILITY_REQUIRED", "AIRLINE_QUOTE_REQUIRED"]
        return row, None
    # Standard quotes are scoped to candidate, ticket key and the exact rules snapshot.
    if ticket["proposed_scheme"] == "standard":
        quote = quotes.get(tid)
        if not (_dated(quote, candidate, rules, review) and sourced(quote, {"AIRLINE_QUOTED"})):
            row["diagnostics"] = ["SOURCED_STANDARD_QUOTE_REQUIRED"]
            return row, None
        miles = number(quote.get("miles_per_person"), "quoted miles", integer=True)
        row.update(status="EVALUATED", pricing_status="QUOTED", miles_per_person=miles)
        return row, {"id": tid, "scheme": "standard", "miles_per_person": miles, "pricing_status": "verified"}
    if ticket["proposed_scheme"] != "standard_mixed":
        row.update(status="UNSUPPORTED", diagnostics=["ADAPTER_SCHEME_UNSUPPORTED"])
        return row, None
    missing = []
    if not _dated(data, candidate, rules, review):
        missing.append("TICKET_DATA_SCOPE_REQUIRED")
    confirmations = data.get("distance_confirmations", {})
    for index, leg in zip(ticket["leg_indices"], legs):
        confirmation = confirmations.get(str(index))
        if not (sourced(confirmation, {"SUPPLIED_CONFIRMED"}) and
                type(confirmation.get("distance_miles")) in (int, float) and
                confirmation["distance_miles"] == leg["distance_miles"] and leg.get("distance_source")):
            missing.append("SOURCED_DISTANCE_REQUIRED:" + str(index))
    if not sourced(data.get("transfer_evidence"), {"SUPPLIED_CONFIRMED"}) or data.get("transfer_hours") is None:
        missing.append("TRANSFER_HOURS_REQUIRED")
    total = sum(l["distance_miles"] for l in legs)
    applicable = [b for b in rules["cx_standard_chart"] if b["min_mi"] <= total <= b["max_mi"]]
    if any("route_type" in b for b in applicable) or data.get("route_type") is not None:
        if data.get("route_type") is None or not sourced(data.get("route_type_evidence"), {"SUPPLIED_CONFIRMED"}):
            missing.append("SOURCED_ROUTE_TYPE_REQUIRED")
    if missing:
        row.update(status="NEEDS_DATA", diagnostics=missing)
        return row, None
    v1ticket = {"id": tid, "scheme": "standard_mixed", "transfer_hours": data["transfer_hours"]}
    if "route_type" in data:
        v1ticket["route_type"] = data["route_type"]
    v1legs = [_leg(l, tid) for l in legs]
    # Reuse kernel arithmetic/rounding verbatim; no chart calculation in this layer.
    number(data["transfer_hours"], "transfer_hours")
    try:
        miles = mixed_cabin_price(v1legs, v1ticket, rules["cx_standard_chart"], rules["standard_mixed_constraints"])
    except (ValueError, KeyError, TypeError) as exc:
        row.update(status="UNSUPPORTED", diagnostics=["V1_MIXED_UNSUPPORTED: " + str(exc)])
        return row, None
    row.update(status="EVALUATED", pricing_status="RULE_ESTIMATED", miles_per_person=miles,
               diagnostics=["MIXED_CABIN_ESTIMATE_AIRLINE_QUOTE_REQUIRED"])
    return row, v1ticket


def _leg(leg, tid):
    return {"from": leg["origin"], "to": leg["destination"], "airline": leg["operating_carrier"],
            "cabin": leg["cabin"], "distance_mi": leg["distance_miles"], "long_haul": leg["long_haul"],
            "payment": "award", "ticket_id": tid}


def adapt_candidate(candidate, request, rules, evidence=None, balances_by_account=None):
    """Return explicit readiness + V1 mapping. Does not search, quote or verify evidence.

    balances_by_account is an explicit payment-account snapshot. None/partial-null
    means unknown; request.travelers[].miles_balance is not implicitly imported.
    """
    evidence = copy.deepcopy(evidence) if evidence is not None else {}
    result = {"status": "NEEDS_DATA", "candidate_id": candidate.get("candidate_id") if isinstance(candidate, dict) else None,
              "diagnostics": [], "tickets": [], "scenario": None, "settings": None,
              "pricing_status": "UNKNOWN", "award_seat_status": "NOT_CHECKED", "ticketability_status": "NOT_CHECKED",
              "complete_price_comparison_eligible": False, "validation_scope": "V1_INPUT_MODEL_ONLY",
              "rule_review": copy.deepcopy(evidence.get("rule_review")) if isinstance(evidence, dict) else None,
              "holiday_status": None,
              "route_status": "UNVERIFIED", "funding_eligibility_status": "NOT_CHECKED"}
    try:
        if not isinstance(evidence, dict) or not isinstance(rules, dict):
            raise ValidationError("evidence/rules must be mappings")
        unsupported = _validate_candidate(candidate, request, rules)
        result["holiday_status"] = candidate.get("holiday_status")
        result["candidate"] = copy.deepcopy(candidate)
        result["input_evidence"] = copy.deepcopy(evidence)
        result["route_status"] = route_status(candidate["legs"])
        result["rules"] = {"digest": rules_digest(rules), "as_of": rules.get("as_of"), "version": rules.get("version")}
        normalized = copy.deepcopy(request)
        normalized["travelers"] = sorted(normalized["travelers"], key=lambda t: t["id"])
        for traveler in normalized["travelers"]:
            for key in ("blocked_dates", "personal_days_off"):
                if key in traveler:
                    traveler[key] = sorted(traveler[key])
        for key in ("origin_airports", "holiday_types", "reposition_airports"):
            if key in normalized:
                normalized[key] = sorted(normalized[key])
        result["evaluation_id"] = stable_id("evaluation_", {"candidate_id": result["candidate_id"],
            "request": normalized, "rules": rules, "evidence": evidence, "balances": balances_by_account})
        if unsupported:
            result.update(status="UNSUPPORTED", diagnostics=[unsupported])
            return result
        balances = copy.deepcopy(balances_by_account)
        if balances is not None:
            if not isinstance(balances, dict) or any(not isinstance(k, str) or not k for k in balances):
                raise ValidationError("payment account IDs must be nonempty strings")
            for val in balances.values():
                if val is not None:
                    number(val, "account balance", integer=True)
        known_balances = bool(balances) and all(v is not None for v in balances.values())
        result["balances_by_account"] = balances
        result["balance_evidence_status"] = "SUPPLIED" if known_balances else "UNKNOWN"
        if not _reviewed(evidence.get("rule_review"), candidate, request, rules):
            result.update(status="RULE_VERSION_REVIEW_REQUIRED", diagnostics=["BOOKING_AND_TRAVEL_RULE_APPLICABILITY_REQUIRED"])
            return result
        inputs, quotes = evidence.get("ticket_data", {}), evidence.get("quotes", {})
        if not isinstance(inputs, dict) or not isinstance(quotes, dict):
            raise ValidationError("ticket_data/quotes must be mappings keyed by ticket ID")
        tids = {t["ticket_id"] for t in candidate["tickets"]}
        if (set(inputs) | set(quotes)) - tids:
            raise ValidationError("evidence references unknown ticket")
        v1tickets = []
        for ticket in candidate["tickets"]:
            if not isinstance(inputs.get(ticket["ticket_id"], {}), dict):
                raise ValidationError("ticket_data entry must be a mapping")
            row, v1ticket = _ticket(ticket, candidate, rules, inputs, quotes, evidence["rule_review"])
            result["tickets"].append(row)
            if v1ticket is not None:
                v1tickets.append(v1ticket)
        pending = {r["status"] for r in result["tickets"]} - {"EVALUATED"}
        if pending:
            result["status"] = next(s for s in ("UNSUPPORTED", "NEEDS_DATA", "NEEDS_AIRLINE_QUOTE") if s in pending)
            return result
        tax = evidence.get("tax_quote")
        tax_ready = _dated(tax, candidate, rules, evidence["rule_review"]) and sourced(tax, {"AIRLINE_QUOTED"})
        tax_amount = number(tax.get("hkd_per_person"), "taxes") if tax_ready else None
        scenario = {"id": result["evaluation_id"], "name": "PR3 supplied candidate", "category": "PR3_AWARD",
                    "award_tickets": v1tickets, "cash_items": [], "taxes_and_surcharges_hkd_per_person": tax_amount,
                    "taxes_quote_type": "quoted" if tax_ready else None,
                    "trips": [{"id": "candidate_trip", "must_visit": [candidate["destination"]], "legs": []}]}
        for ticket in candidate["tickets"]:
            for index in ticket["leg_indices"]:
                scenario["trips"][0]["legs"].append(_leg(candidate["legs"][index], ticket["ticket_id"]))
        preferences = request["cabin_preferences"]
        settings = {"passengers": sorted(t["id"] for t in request["travelers"]), "home_airports": sorted(request["origin_airports"]),
                    "min_longhaul_cabin": preferences["longhaul_minimum"], "min_shorthaul_cabin": preferences["shorthaul_minimum"],
                    "balances_by_account": dict(sorted(balances.items())) if known_balances else {}}
        result.update(status="READY_FOR_EVALUATION", scenario=scenario, settings=settings,
                      pricing_status="RULE_ESTIMATED" if any(t["pricing_status"] == "RULE_ESTIMATED" for t in result["tickets"]) else "QUOTED")
        result["tax_quote"] = copy.deepcopy(tax)
        if not tax_ready:
            result["diagnostics"].append("SOURCED_TAX_QUOTE_REQUIRED")
        result["diagnostics"].append("PAYER_BENEFICIARY_ELIGIBILITY_NOT_CHECKED")
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        result.pop("input_evidence", None)
        result.update(status="NEEDS_DATA", diagnostics=["INVALID_OR_MISSING_INPUT: " + str(exc)],
                      scenario=None, settings=None, pricing_status="UNKNOWN")
    return result
