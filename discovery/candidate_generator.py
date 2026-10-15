"""Bounded standard-award structures. No pricing, V1 adapter or availability."""
import copy
import re

from optimizer import CABIN_RANK
from ._search_config import search_config
from ._validation import ValidationError, parse_date, validate
from .route_graph import route_status, stable_id

STRATEGIES = ("ALL_J", "LONG_J_SHORT_Y", "LONG_W_SHORT_Y", "ALL_W", "ALL_Y",
              "OUTBOUND_J_RETURN_W", "OUTBOUND_W_RETURN_J", "PREFERRED")


def _window(supplied):
    if supplied is None:
        return None
    window = copy.deepcopy(supplied)
    for key in ("start_date", "end_date", "holiday_status"):
        if key not in window:
            raise ValidationError("window missing " + key)
    if parse_date(window["end_date"]) < parse_date(window["start_date"]):
        raise ValidationError("window dates reversed")
    if window["holiday_status"] not in ("OFFICIAL", "ESTIMATED") or window.get("errors"):
        raise ValidationError("invalid/infeasible supplied holiday window")
    evidence = window.get("holiday_evidence", [])
    if not isinstance(evidence, list) or any(not isinstance(e, dict) for e in evidence):
        raise ValidationError("holiday_evidence must be a list of evidence objects")
    if "holiday_uncertainty" in window and not isinstance(window["holiday_uncertainty"], bool):
        raise ValidationError("holiday_uncertainty must be boolean")
    uncertain = window["holiday_status"] == "ESTIMATED" or window.get("holiday_uncertainty", False)
    uncertain |= any(e.get("source_status") == "ESTIMATED" or e.get("calendar_source_status") == "ESTIMATED" for e in evidence)
    window["holiday_uncertainty"] = bool(uncertain)
    if uncertain:
        window["holiday_status"] = "ESTIMATED"
    return window


def _destinations(request, diagnostics):
    destinations = request.get("destinations", [])
    required = [d for d in destinations if d.get("priority", "preferred") == "required"]
    unresolved_required = False
    for d in destinations:
        if d["type"] != "airport":
            diagnostics.append({"code": "DESTINATION_RESOLUTION_REQUIRED", "destination": copy.deepcopy(d)})
            unresolved_required |= d in required
        elif not re.fullmatch("[A-Z]{3}", d["value"]):
            raise ValidationError("airport destination must be a three-letter IATA code")
    required_airports = {d["value"] for d in required if d["type"] == "airport"}
    if len(required_airports) > 1:
        diagnostics.append({"code": "MULTI_DESTINATION_UNSUPPORTED"})
        return []
    if unresolved_required:
        return []
    airports = sorted(required_airports or {d["value"] for d in destinations if d["type"] == "airport"})
    if not airports:
        diagnostics.append({"code": "NO_AIRPORT_DESTINATIONS"})
    return airports


def _cabins(path, strategy, direction, preferences, threshold):
    cabins = []
    for edge in path:
        longhaul = edge["distance_miles"] >= threshold
        if strategy in ("ALL_J", "ALL_W", "ALL_Y"):
            cabin = strategy[-1]
        elif strategy.startswith("LONG_"):
            cabin = strategy[5] if longhaul else "Y"
        elif strategy == "OUTBOUND_J_RETURN_W":
            cabin = "J" if direction == "outbound" else "W"
        elif strategy == "OUTBOUND_W_RETURN_J":
            cabin = "W" if direction == "outbound" else "J"
        else:
            preferred = preferences["longhaul_preferred"] if longhaul else preferences["shorthaul_minimum"]
            minimum = preferences["longhaul_minimum"] if longhaul else preferences["shorthaul_minimum"]
            cabin = max((preferred, minimum), key=CABIN_RANK.__getitem__)
        minimum = preferences["longhaul_minimum"] if longhaul else preferences["shorthaul_minimum"]
        if cabin not in edge["cabins"] or CABIN_RANK[cabin] < CABIN_RANK[minimum]:
            return None
        cabins.append(cabin)
    if len(set(cabins)) > 1 and not preferences["allow_mixed_cabin"]:
        return None
    return cabins


def _standard_policy(rules):
    """Missing/uninterpretable policy never inherits search config defaults."""
    policy = rules.get("standard_award_constraints")
    if not isinstance(policy, dict):
        return None
    for key, minimum in (("max_sectors_per_direction", 1), ("max_transfers_per_direction", 0),
                         ("max_transfer_hours", 1), ("max_mixed_carriers", 1)):
        value = policy.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            return None
    source = policy.get("source")
    if (not isinstance(policy.get("primary_carrier"), str) or not policy["primary_carrier"] or
            not isinstance(policy.get("mixed_carrier_requires_primary"), bool) or
            not isinstance(policy.get("excluded_single_carriers"), list) or
            any(not isinstance(c, str) or not c for c in policy["excluded_single_carriers"]) or
            not isinstance(source, dict) or source.get("evidence_type") != "OFFICIAL_PUBLISHED" or
            not isinstance(source.get("url"), str) or not source["url"].startswith("https://") or
            any(not isinstance(source.get(k), str) or not source[k]
                for k in ("structure_clauses", "carrier_clause"))):
        return None
    return policy


def _tickets(legs, mode, mixed_constraints, policy):
    tickets = []
    for direction in ("outbound", "return"):
        indices = [i for i, leg in enumerate(legs) if leg["direction"] == direction]
        groups = [[i] for i in indices] if mode == "SEPARATE_AWARDS" else [indices]
        for group in groups:
            selected = [legs[i] for i in group]
            carriers = {leg["operating_carrier"] for leg in selected}
            mixed = len({leg["cabin"] for leg in selected}) > 1
            partner = carriers != {policy["primary_carrier"]}
            reason = None
            if len(group) > policy["max_sectors_per_direction"]:
                reason = "STANDARD_SECTOR_LIMIT_EXCEEDED"
            elif len(group) - 1 > policy["max_transfers_per_direction"]:
                reason = "STANDARD_TRANSFER_LIMIT_EXCEEDED"
            elif len(carriers) == 1 and carriers.intersection(policy["excluded_single_carriers"]):
                reason = "STANDARD_CARRIER_EXCLUDED"
            elif len(carriers) > policy["max_mixed_carriers"]:
                reason = "STANDARD_CARRIER_COUNT_EXCEEDED"
            elif (len(carriers) > 1 and policy["mixed_carrier_requires_primary"] and
                  policy["primary_carrier"] not in carriers):
                reason = "STANDARD_MIXED_CARRIERS_REQUIRE_PRIMARY"
            elif mixed and not partner:
                if (not mixed_constraints or len(selected) != mixed_constraints["leg_count"] or
                        any(l["operating_carrier"] not in mixed_constraints["allowed_carriers"] for l in selected)):
                    reason = "CX_MIXED_REPRESENTATION_UNSUPPORTED"
            if reason:
                return None, {"code": reason, "direction": direction, "ticketing_mode": mode,
                              "sector_count": len(group), "carriers": sorted(carriers),
                              "rule_source": copy.deepcopy(policy["source"])}
            requirements = ["RULE_VERSION_REVIEW_REQUIRED", "CARRIER_REDEMPTION_ELIGIBILITY_REQUIRED", "AIRLINE_QUOTE_REQUIRED"]
            if partner:
                requirements.append("PARTNER_AGREEMENT_REQUIRED")
            if len(group) > 1:
                requirements += ["TRANSFER_HOURS_REQUIRED", "ONE_WAY_GEOGRAPHY_REVIEW_REQUIRED"]
            if mixed:
                requirements.append("ROUTE_TYPE_IF_REQUIRED")
            tickets.append({
                "ticket_id": direction + "_" + str(len(tickets) + 1),
                "direction": direction, "leg_indices": group,
                # A partner mixed-cabin quote cannot be mapped to the CX-only formula.
                "proposed_scheme": None if partner and mixed else ("standard_mixed" if mixed else "standard"),
                "structure_status": "NEEDS_PARTNER_AGREEMENT_AND_QUOTE" if partner else "PENDING_RULE_AND_QUOTE_REVIEW",
                "miles_per_person": None, "transfer_hours": None,
                "max_transfer_hours": policy["max_transfer_hours"],
                "requirements": requirements,
                "rule_source": copy.deepcopy(policy["source"]),
            })
    return tickets, None


def _stream(graph, request, pairs, bounds, strategy, mode, mixed, policy, threshold, window, rejected, structure_rejections):
    preferences = request["cabin_preferences"]
    for origin, destination, outbound_paths, return_paths in pairs:
        for outbound in outbound_paths:
            for returning in return_paths:
                out_cabins = _cabins(outbound, strategy, "outbound", preferences, threshold)
                back_cabins = _cabins(returning, strategy, "return", preferences, threshold)
                if out_cabins is None or back_cabins is None:
                    rejected["CABIN_UNSUPPORTED_OR_BELOW_MINIMUM"] = rejected.get("CABIN_UNSUPPORTED_OR_BELOW_MINIMUM", 0) + 1
                    continue
                legs = []
                for direction, path, cabins in (("outbound", outbound, out_cabins), ("return", returning, back_cabins)):
                    for edge, cabin in zip(path, cabins):
                        leg = copy.deepcopy(edge)
                        leg.update(direction=direction, cabin=cabin, long_haul=edge["distance_miles"] >= threshold)
                        legs.append(leg)
                # Whole-trip bounds are checked before ticket grouping.
                if len(legs) > bounds["max_flight_legs_per_trip"] or len(legs) - 2 > bounds["max_connections"]:
                    rejected["ROUNDTRIP_SEARCH_BOUND_EXCEEDED"] = rejected.get("ROUNDTRIP_SEARCH_BOUND_EXCEEDED", 0) + 1
                    continue
                if mode == "SEPARATE_AWARDS" and len(legs) == 2:
                    continue  # Identical to one award per direction, not a new variant.
                tickets, rejection = _tickets(legs, mode, mixed, policy)
                if rejection:
                    code = rejection["code"]
                    rejected[code] = rejected.get(code, 0) + 1
                    structure_rejections[stable_id("rejection_", rejection)] = rejection
                    continue
                long_legs = [l for l in legs if l["long_haul"]]
                candidate = {
                    "origin": origin, "destination": destination, "legs": legs, "tickets": tickets,
                    "ticketing_mode": mode, "lifecycle": "GENERATED",
                    "traveler_ids": sorted(t["id"] for t in request["travelers"]),
                    "route_snapshot_id": graph.snapshot_id, "route_snapshot_observed_at": graph.observed_at,
                    "holiday_window": copy.deepcopy(window),
                    "holiday_status": window["holiday_status"] if window else None,
                    "route_status": route_status(legs), "pricing_status": "UNKNOWN",
                    "award_seat_status": "NOT_CHECKED", "ticketability_status": "NOT_CHECKED",
                    "miles_per_person": None, "taxes_hkd_per_person": None,
                    "complete_price_comparison_eligible": False,
                    "rule_version_review_required": True,
                    "longhaul_preferred_met": all(CABIN_RANK[l["cabin"]] >= CABIN_RANK[preferences["longhaul_preferred"]] for l in long_legs) if long_legs else None,
                    "assumptions": {"longhaul_distance_threshold_miles": threshold,
                                    "route_dates": "WINDOW_ENDPOINTS_FOR_EACH_DIRECTION" if window else "NOT_CHECKED",
                                    "leave_validation": "NOT_CHECKED_BY_PR2",
                                    "route_verification": "SUPPLIED_SNAPSHOT_EVIDENCE_ONLY",
                                    "schedule_validation": "NOT_CHECKED",
                                    "overnight_arrival": "NOT_CHECKED",
                                    "timezone_local_dates": "NOT_CHECKED"},
                }
                candidate["candidate_id"] = stable_id("candidate_", candidate)
                candidate["strategies"] = [strategy]
                yield candidate


def generate_candidates(graph, request, rules, window=None, config=None):
    """Generate airport roundtrip structures only, not V1 scenarios or prices.

    Caller supplies a rule snapshot explicitly for ticket structure and capability;
    this does not establish its future applicability or price any award.
    """
    validate(request, "travel_request.schema.json")
    request = copy.deepcopy(request)
    if len({t["id"] for t in request["travelers"]}) != len(request["travelers"]):
        raise ValidationError("traveler ids must be unique")
    config = search_config(config, candidates=True)
    window = _window(window)
    bounds, generation = config["route_search"], config["candidate_generation"]
    if not isinstance(rules, dict):
        raise ValidationError("an explicit rule snapshot mapping is required")
    mixed = rules.get("standard_mixed_constraints")
    if mixed is not None:
        if (not isinstance(mixed, dict) or isinstance(mixed.get("leg_count"), bool) or
                not isinstance(mixed.get("leg_count"), int) or mixed["leg_count"] < 1 or
                not isinstance(mixed.get("allowed_carriers"), list) or not mixed["allowed_carriers"]):
            raise ValidationError("invalid standard_mixed_constraints capability data")
    policy = _standard_policy(rules)
    if policy is None:
        return {"candidates": [], "diagnostics": [{"code": "STANDARD_AWARD_POLICY_REQUIRED"},
                                                 {"code": "NO_FEASIBLE_STANDARD_CANDIDATES"}],
                "metadata": {"milestone": "V2_ALPHA_PR2", "search_config": config,
                             "pricing_performed": False, "v1_evaluated": False}}
    diagnostics = []
    destinations = _destinations(request, diagnostics)
    if request.get("reposition_airports"):
        diagnostics.append({"code": "REPOSITIONING_DEFERRED"})
    pairs = []  # Factored path lists, never the outbound/return product.
    if bounds["max_flight_legs_per_trip"] < 2:
        diagnostics.append({"code": "SEARCH_LIMIT_NO_ROUNDTRIP"})
    else:
        for origin in sorted(request["origin_airports"]):
            for destination in destinations:
                if origin == destination:
                    continue
                outgoing = graph.find_paths(origin, destination, config, window["start_date"] if window else None, bounds["max_flight_legs_per_trip"] - 1)
                returning = graph.find_paths(destination, origin, config, window["end_date"] if window else None, bounds["max_flight_legs_per_trip"] - 1)
                diagnostics.append({"code": "OD_SEARCH", "origin": origin, "destination": destination,
                                    "outbound": outgoing["diagnostics"], "return": returning["diagnostics"]})
                if outgoing["paths"] and returning["paths"]:
                    pairs.append((origin, destination, outgoing["paths"], returning["paths"]))
    candidates = {}
    for strategy in STRATEGIES:
        if strategy.startswith("OUTBOUND_") and not request["cabin_preferences"].get("allow_asymmetric_roundtrip", False):
            diagnostics.append({"code": "ASYMMETRIC_DISABLED", "strategy": strategy})
            continue
        modes = ["SINGLE_AWARD"] + (["SEPARATE_AWARDS"] if request["cabin_preferences"]["allow_separate_tickets"] else [])
        rejected = {}
        structure_rejections = {}
        streams = [_stream(graph, request, pairs, bounds, strategy, mode, mixed, policy,
                           generation["longhaul_distance_threshold_miles"], window, rejected, structure_rejections) for mode in modes]
        selected = 0
        while streams and selected < generation["max_candidates_per_strategy"]:
            for stream in list(streams):
                try:
                    candidate = next(stream)
                except StopIteration:
                    streams.remove(stream)
                    continue
                cid = candidate["candidate_id"]
                if cid in candidates:
                    candidates[cid]["strategies"].append(strategy)
                else:
                    candidates[cid] = candidate
                selected += 1
                if selected >= generation["max_candidates_per_strategy"]:
                    break
                if not generation["preserve_strategy_diversity"]:
                    break  # Exhaust first mode before visiting the next.
        diagnostics.append({"code": "STRATEGY_GENERATED" if selected else "NO_STRATEGY_CANDIDATES",
                            "strategy": strategy, "selected": selected,
                            "limit_reached": selected == generation["max_candidates_per_strategy"],
                            "rejections": dict(sorted(rejected.items())),
                            "ticket_structure_rejections": [structure_rejections[k] for k in sorted(structure_rejections)]})
    rows = sorted(candidates.values(), key=lambda c: c["candidate_id"])
    for row in rows:
        row["strategies"] = sorted(set(row["strategies"]))
    if not rows:
        diagnostics.append({"code": "NO_FEASIBLE_STANDARD_CANDIDATES"})
    return {"candidates": rows, "diagnostics": diagnostics,
            "metadata": {"milestone": "V2_ALPHA_PR2", "search_config": config,
                         "pricing_performed": False, "v1_evaluated": False}}
