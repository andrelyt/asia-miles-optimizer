"""Bounded, evidence-preserving holiday windows; no routes or award pricing."""
import copy
from datetime import timedelta
import hashlib
import json
from pathlib import Path

from ._validation import ValidationError, parse_date, validate
from .holiday_calendar import CalendarCoverageError

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "search_config.json"


def _request(supplied):
    request = copy.deepcopy(supplied)
    validate(request, "travel_request.schema.json")
    travelers = request["travelers"]
    if len({t["id"] for t in travelers}) != len(travelers):
        raise ValidationError("traveler ids must be unique")
    request["planning_year"] = int(request["planning_year"])
    for traveler in travelers:
        traveler["annual_leave_budget"] = int(traveler["annual_leave_budget"])
    request["travelers"] = sorted(travelers, key=lambda t: t["id"])
    constraints = request.get("leave_constraints", {})
    if constraints.get("min_calendar_trip_days", 1) > constraints.get("max_calendar_trip_days", float("inf")):
        raise ValidationError("min_calendar_trip_days exceeds max_calendar_trip_days")
    return request


def _bounds(config):
    if config is None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    try:
        bounds = copy.deepcopy(config["holiday_window"])
        for field in ("days_before", "days_after", "max_generated_windows_per_holiday"):
            value = bounds[field]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError("holiday_window." + field + " must be a nonnegative integer")
        if bounds["max_generated_windows_per_holiday"] == 0:
            raise ValidationError("max_generated_windows_per_holiday must be positive")
    except (KeyError, TypeError) as exc:
        raise ValidationError("missing/invalid holiday_window search config") from exc
    return bounds


def _evaluate_window(calendar, request, start, end):
    if end < start:
        raise ValidationError("window end precedes start")
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    evidence = [calendar.day(day) for day in days]
    leave_dates = {}
    day_types = {}
    errors = []
    constraints = request.get("leave_constraints", {})
    for traveler in request["travelers"]:
        tid = traveler["id"]
        blocked = set(traveler.get("blocked_dates", []))
        personal = set(traveler.get("personal_days_off", []))
        leave_dates[tid] = []
        day_types[tid] = {}
        for info in evidence:
            day = info["date"]
            kind = info["day_type"]
            # Blocking always wins; a personal override can remove makeup leave.
            if day in blocked or kind == "BLOCKED_DAY":
                kind = "BLOCKED_DAY"
                errors.append({"code": "BLOCKED_DATE", "traveler_id": tid, "date": day})
            elif day in personal:
                kind = "PERSONAL_DAY_OFF"
            if kind in ("WORKDAY", "MAKEUP_WORKDAY"):
                leave_dates[tid].append(day)
            day_types[tid][day] = kind
        required = len(leave_dates[tid])
        if required > traveler["annual_leave_budget"]:
            errors.append({"code": "LEAVE_BUDGET_EXCEEDED", "traveler_id": tid})
        if required > constraints.get("max_leave_days_per_trip", required):
            errors.append({"code": "PER_TRIP_LEAVE_EXCEEDED", "traveler_id": tid})
    duration = len(days)
    if duration < constraints.get("min_calendar_trip_days", 1) or duration > constraints.get("max_calendar_trip_days", duration):
        errors.append({"code": "TRIP_LENGTH_OUT_OF_BOUNDS"})
    estimated = any(e["source_status"] == "ESTIMATED" or e["calendar_source_status"] == "ESTIMATED" for e in evidence)
    return {
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "calendar_trip_days": duration,
        "estimated_destination_full_days": None, "estimated_transit_days": None,
        "day_estimate_assumptions": ["FLIGHTS_NOT_KNOWN_DESTINATION_AND_TRANSIT_DAYS_NOT_ESTIMATED"],
        "leave_days_by_traveler": {tid: len(dates) for tid, dates in leave_dates.items()},
        "leave_dates_by_traveler": leave_dates,
        "day_types_by_traveler": day_types,
        "holiday_status": "ESTIMATED" if estimated else "OFFICIAL",
        "holiday_uncertainty": estimated, "holiday_evidence": evidence,
        "budget_scope": "SINGLE_WINDOW_ALL_DATES_NOT_ANNUAL_PORTFOLIO",
        "errors": errors,
    }


def evaluate_window(calendar, request, start_date, end_date):
    """Evaluate one inclusive window. Invalid request raises ValidationError.

    CalendarCoverageError is explicit when any year snapshot is absent.
    Blocked/budget/length failures are machine-readable entries in errors.
    """
    request = _request(request)
    return _evaluate_window(calendar, request, parse_date(start_date), parse_date(end_date))


def _sort_key(window):
    return (window["holiday_type"], window["holiday_anchor_date"], window["bridge_side"],
            window["start_date"], window["end_date"], window["window_id"])


def prune_windows(windows):
    """Pareto prune within equal holiday, bridge direction and evidence state.

    Longer duration and no greater leave for ANY traveler dominates only when
    at least one dimension is strictly better. Date-distinct ties survive.
    Pre/post/both bridge choices and official/estimated evidence never dominate
    across groups. No scalar weighted score is used.
    """
    result = []
    group_fields = ("holiday_type", "holiday_anchor_date", "bridge_side", "holiday_status")
    for window in windows:
        dominated = False
        for other in windows:
            if other is window or any(other[k] != window[k] for k in group_fields):
                continue
            a, b = other["leave_days_by_traveler"], window["leave_days_by_traveler"]
            if a.keys() != b.keys():
                continue
            no_worse = other["calendar_trip_days"] >= window["calendar_trip_days"] and all(a[t] <= b[t] for t in a)
            strictly_better = other["calendar_trip_days"] > window["calendar_trip_days"] or any(a[t] < b[t] for t in a)
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            result.append(window)
    return sorted(result, key=_sort_key)


def _cap_diverse(windows, limit):
    # Round robin by bridge direction preserves distinct choices where cap allows.
    groups = {}
    for window in sorted(windows, key=lambda w: (-w["calendar_trip_days"], tuple(sorted(w["leave_days_by_traveler"].items())), _sort_key(w))):
        groups.setdefault(window["bridge_side"], []).append(window)
    result = []
    while len(result) < limit and any(groups.values()):
        for side in sorted(groups):
            if groups[side] and len(result) < limit:
                result.append(groups[side].pop(0))
    return sorted(result, key=_sort_key)


def generate_windows(calendar, request, config=None):
    """Return bounded windows plus explicit missing/blocked/budget diagnostics.

    Holiday anchors come ONLY from PUBLIC_HOLIDAY entries whose holiday_name is
    a request holiday_types code. No fixed festival dates or makeup workdays are
    fabricated. Each window contains at least one selected public holiday.
    """
    request = _request(request)
    bounds = _bounds(config)
    constraints = request.get("leave_constraints", {})
    all_windows, diagnostics = [], []
    for holiday in sorted(request["holiday_types"]):
        try:
            anchors = calendar.holiday_dates(request["planning_year"], holiday)
        except CalendarCoverageError as exc:
            diagnostics.append({"holiday_type": holiday, "code": "CALENDAR_YEAR_MISSING", "detail": str(exc)})
            continue
        if not anchors:
            diagnostics.append({"holiday_type": holiday, "code": "HOLIDAY_ANCHOR_MISSING"})
            continue
        first, last = anchors[0], anchors[-1]
        lower = first - timedelta(days=bounds["days_before"])
        upper = last + timedelta(days=bounds["days_after"])
        min_days = int(constraints.get("min_calendar_trip_days", 1))
        max_days = min(int(constraints.get("max_calendar_trip_days", (upper - lower).days + 1)), (upper - lower).days + 1)
        viable, rejected, missing_years = [], {}, set()
        for offset in range((upper - lower).days + 1):
            start = lower + timedelta(days=offset)
            for length in range(min_days, max_days + 1):
                end = start + timedelta(days=length - 1)
                if end > upper or not any(start <= anchor <= end for anchor in anchors):
                    continue
                try:
                    window = _evaluate_window(calendar, request, start, end)
                except CalendarCoverageError as exc:
                    missing_years.add(str(exc))
                    continue
                if not constraints.get("allow_bridge_leave", True):
                    if any(day < first.isoformat() or day > last.isoformat() for dates in window["leave_dates_by_traveler"].values() for day in dates):
                        window["errors"].append({"code": "BRIDGE_LEAVE_DISABLED"})
                if window["errors"]:
                    for code in {e["code"] for e in window["errors"]}:
                        rejected[code] = rejected.get(code, 0) + 1
                    continue
                before, after = start < first, end > last
                side = "BOTH" if before and after else "BEFORE" if before else "AFTER" if after else "CORE"
                window.update(holiday_type=holiday, holiday_anchor_date=first.isoformat(), bridge_side=side)
                normalized = json.dumps(window, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                window["window_id"] = "window_" + hashlib.sha256(normalized.encode()).hexdigest()[:24]
                viable.append(window)
        pruned = prune_windows(viable)
        retained = _cap_diverse(pruned, bounds["max_generated_windows_per_holiday"])
        all_windows.extend(retained)
        diagnostics.append({
            "holiday_type": holiday, "code": "WINDOWS_GENERATED" if retained else "NO_FEASIBLE_WINDOWS",
            "feasible_before_pruning": len(viable), "pareto_retained": len(pruned),
            "returned": len(retained), "truncated_by_config": len(pruned) > len(retained),
            "rejected_window_counts": dict(sorted(rejected.items())),
        })
        for detail in sorted(missing_years):
            diagnostics.append({"holiday_type": holiday, "code": "CALENDAR_YEAR_MISSING", "detail": detail})
    return {
        "windows": sorted(all_windows, key=_sort_key), "diagnostics": diagnostics,
        "metadata": {"milestone": "V2_ALPHA_PR1", "jurisdiction": calendar.jurisdiction,
                     "holiday_window_config": bounds, "annual_portfolio_checked": False},
    }
