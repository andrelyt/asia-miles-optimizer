import copy
import json
import unittest

from discovery._validation import ValidationError
from discovery.holiday_calendar import CalendarCoverageError, load_calendar, load_calendars
from discovery.leave_engine import evaluate_window, generate_windows, prune_windows
from tests._fixtures import config, request, snapshot


class LeaveEngineTests(unittest.TestCase):
    def setUp(self):
        self.calendar = load_calendars([snapshot(), snapshot(2027)])

    def evaluate(self, start, end, req=None):
        return evaluate_window(self.calendar, req or request(), start, end)

    def test_normal_weekend_and_zero_leave(self):
        result = self.evaluate("2026-01-10", "2026-01-11", request(budget_a=0, budget_b=0))
        self.assertFalse(result["errors"])
        self.assertEqual(result["leave_dates_by_traveler"], {"traveler_a": [], "traveler_b": []})
        self.assertEqual(result["calendar_trip_days"], 2)

    def test_official_public_holiday_zero_leave(self):
        result = self.evaluate("2026-01-01", "2026-01-01", request(budget_a=0, budget_b=0))
        self.assertFalse(result["errors"])
        self.assertEqual(result["holiday_status"], "OFFICIAL")
        self.assertFalse(result["holiday_uncertainty"])

    def test_weekend_makeup_consumes_leave(self):
        result = self.evaluate("2026-01-03", "2026-01-04")
        self.assertEqual(result["leave_dates_by_traveler"]["traveler_a"], ["2026-01-03"])
        self.assertEqual(result["day_types_by_traveler"]["traveler_a"]["2026-01-03"], "MAKEUP_WORKDAY")

    def test_personal_override_of_makeup_is_independent(self):
        req = request(); req["travelers"][0]["personal_days_off"] = ["2026-01-03"]
        result = self.evaluate("2026-01-03", "2026-01-04", req)
        self.assertEqual(result["leave_days_by_traveler"], {"traveler_a": 0, "traveler_b": 1})
        self.assertEqual(result["day_types_by_traveler"]["traveler_a"]["2026-01-03"], "PERSONAL_DAY_OFF")

    def test_blocked_date_wins_over_personal_and_holiday(self):
        req = request(); req["travelers"][0].update(blocked_dates=["2026-01-01"], personal_days_off=["2026-01-01"])
        result = self.evaluate("2026-01-01", "2026-01-01", req)
        self.assertEqual(result["errors"], [{"code": "BLOCKED_DATE", "traveler_id": "traveler_a", "date": "2026-01-01"}])
        data = snapshot(); data["days"][0]["day_type"] = "BLOCKED_DAY"
        result = evaluate_window(load_calendar(data), request(), "2026-01-01", "2026-01-01")
        self.assertEqual({e["traveler_id"] for e in result["errors"]}, {"traveler_a", "traveler_b"})

    def test_calendar_personal_day_off_applies_to_both(self):
        data = snapshot(); data["days"].append({"date": "2026-01-02", "day_type": "PERSONAL_DAY_OFF"})
        result = evaluate_window(load_calendar(data), request(), "2026-01-02", "2026-01-02")
        self.assertEqual(result["leave_days_by_traveler"], {"traveler_a": 0, "traveler_b": 0})

    def test_pre_holiday_bridge_exact_dates(self):
        result = self.evaluate("2026-04-02", "2026-04-05")
        self.assertEqual(result["leave_dates_by_traveler"]["traveler_a"], ["2026-04-02"])
        req = request(); req["holiday_types"] = ["qingming"]
        windows = generate_windows(self.calendar, req, config(before=1, after=2))["windows"]
        self.assertTrue(any(w["bridge_side"] == "BEFORE" and w["start_date"] == "2026-04-02" for w in windows))

    def test_post_holiday_bridge_exact_dates(self):
        result = self.evaluate("2026-04-03", "2026-04-06")
        self.assertEqual(result["leave_dates_by_traveler"]["traveler_a"], ["2026-04-06"])
        req = request(); req["holiday_types"] = ["qingming"]
        windows = generate_windows(self.calendar, req, config(before=1, after=3))["windows"]
        self.assertTrue(any(w["bridge_side"] == "AFTER" and w["end_date"] == "2026-04-06" for w in windows))

    def test_two_travelers_independent_budgets(self):
        req = request(budget_a=0, budget_b=1)
        result = self.evaluate("2026-01-01", "2026-01-02", req)
        self.assertEqual(result["errors"], [{"code": "LEAVE_BUDGET_EXCEEDED", "traveler_id": "traveler_a"}])
        req["travelers"][0]["personal_days_off"] = ["2026-01-02"]
        self.assertFalse(self.evaluate("2026-01-01", "2026-01-02", req)["errors"])

    def test_two_different_blocked_dates_filter_windows(self):
        req = request(); req["holiday_types"] = ["qingming"]
        req["travelers"][0]["blocked_dates"] = ["2026-04-02"]
        req["travelers"][1]["blocked_dates"] = ["2026-04-06"]
        windows = generate_windows(self.calendar, req, config(before=1, after=3))["windows"]
        self.assertTrue(windows)
        self.assertTrue(all(w["start_date"] > "2026-04-02" and w["end_date"] < "2026-04-06" for w in windows))
        req["travelers"][0]["blocked_dates"] = ["2026-04-03"]
        result = generate_windows(self.calendar, req, config(before=1, after=3))
        self.assertFalse(result["windows"])
        self.assertEqual(result["diagnostics"][0]["code"], "NO_FEASIBLE_WINDOWS")
        self.assertIn("BLOCKED_DATE", result["diagnostics"][0]["rejected_window_counts"])

    def test_budget_exceeded_produces_no_window_reason(self):
        req = request(budget_a=0, budget_b=0)
        req["leave_constraints"].update(min_calendar_trip_days=2, max_calendar_trip_days=2)
        result = generate_windows(self.calendar, req, config(before=0, after=1))
        self.assertFalse(result["windows"])
        self.assertIn("LEAVE_BUDGET_EXCEEDED", result["diagnostics"][0]["rejected_window_counts"])

    def test_per_trip_budget_limit_and_length(self):
        req = request(); req["leave_constraints"]["max_leave_days_per_trip"] = 0
        self.assertTrue(any(e["code"] == "PER_TRIP_LEAVE_EXCEEDED" for e in self.evaluate("2026-01-02", "2026-01-02", req)["errors"]))
        req["leave_constraints"]["min_calendar_trip_days"] = 2
        self.assertTrue(any(e["code"] == "TRIP_LENGTH_OUT_OF_BOUNDS" for e in self.evaluate("2026-01-01", "2026-01-01", req)["errors"]))

    def test_cross_year_window_and_budget_scope(self):
        req = request(year=2027)
        result = self.evaluate("2026-12-31", "2027-01-03", req)
        self.assertFalse(result["errors"])
        self.assertEqual(result["leave_dates_by_traveler"]["traveler_a"], ["2026-12-31"])
        self.assertEqual(result["calendar_trip_days"], 4)
        self.assertEqual(result["budget_scope"], "SINGLE_WINDOW_ALL_DATES_NOT_ANNUAL_PORTFOLIO")
        windows = generate_windows(self.calendar, req, config(before=1, after=2))["windows"]
        self.assertTrue(any(w["start_date"] == "2026-12-31" and w["end_date"] == "2027-01-03" for w in windows))

    def test_estimated_status_survives_to_serialized_windows(self):
        result = generate_windows(self.calendar, request(year=2027), config(before=1, after=2))
        serialized = json.loads(json.dumps(result))
        self.assertTrue(serialized["windows"])
        self.assertTrue(all(w["holiday_status"] == "ESTIMATED" and w["holiday_uncertainty"] for w in serialized["windows"]))
        self.assertTrue(all(w["holiday_evidence"] for w in serialized["windows"]))

    def test_day_estimate_does_not_fabricate_flight_time(self):
        result = self.evaluate("2026-01-01", "2026-01-01")
        self.assertIsNone(result["estimated_destination_full_days"])
        self.assertIsNone(result["estimated_transit_days"])
        self.assertTrue(result["day_estimate_assumptions"])

    def test_estimated_snapshot_cannot_be_upgraded_by_official_day(self):
        data = snapshot(2027); data["days"][0]["source_status"] = "OFFICIAL"
        result = evaluate_window(load_calendar(data), request(year=2027), "2027-01-01", "2027-01-01")
        self.assertEqual(result["holiday_evidence"][0]["source_status"], "OFFICIAL")
        self.assertEqual(result["holiday_status"], "ESTIMATED")
        data = snapshot(); data["days"][0]["source_status"] = "ESTIMATED"
        result = evaluate_window(load_calendar(data), request(), "2026-01-01", "2026-01-01")
        self.assertEqual(result["holiday_status"], "ESTIMATED")

    def test_missing_cross_year_snapshot_not_silently_inferred(self):
        calendar = load_calendar(snapshot(2027))
        with self.assertRaises(CalendarCoverageError): evaluate_window(calendar, request(year=2027), "2026-12-31", "2027-01-01")
        result = generate_windows(calendar, request(year=2027), config(before=1, after=2))
        self.assertTrue(any(d["code"] == "CALENDAR_YEAR_MISSING" for d in result["diagnostics"]))
        self.assertTrue(all(w["start_date"] >= "2027-01-01" for w in result["windows"]))

    def test_missing_holiday_and_planning_year_reasons(self):
        req = request(); req["holiday_types"] = ["mid_autumn"]
        self.assertEqual(generate_windows(self.calendar, req)["diagnostics"][0]["code"], "HOLIDAY_ANCHOR_MISSING")
        req = request(year=2028)
        self.assertEqual(generate_windows(self.calendar, req)["diagnostics"][0]["code"], "CALENDAR_YEAR_MISSING")

    def test_bridge_leave_disabled(self):
        req = request(); req["holiday_types"] = ["qingming"]
        req["leave_constraints"]["allow_bridge_leave"] = False
        result = generate_windows(self.calendar, req, config(before=1, after=3))
        self.assertTrue(result["windows"])
        self.assertTrue(all(not any(w["leave_dates_by_traveler"].values()) for w in result["windows"]))
        self.assertIn("BRIDGE_LEAVE_DISABLED", result["diagnostics"][0]["rejected_window_counts"])

    def test_all_default_families_and_optional_missing_are_explicit(self):
        req = request(); req["holiday_types"] = ["new_year", "qingming", "labor_day", "dragon_boat", "national_day"]
        result = generate_windows(self.calendar, req, config(before=0, after=2))
        self.assertEqual({w["holiday_type"] for w in result["windows"]}, set(req["holiday_types"]))
        self.assertTrue(all(w["start_date"] <= w["holiday_anchor_date"] <= w["end_date"] for w in result["windows"]))

    def test_search_config_bounds_and_cap_preserve_sides(self):
        req = request(); req["holiday_types"] = ["qingming"]
        result = generate_windows(self.calendar, req, config(before=1, after=3, cap=2))
        self.assertLessEqual(len(result["windows"]), 2)
        self.assertEqual(len({w["bridge_side"] for w in result["windows"]}), 2)
        self.assertTrue(result["diagnostics"][0]["truncated_by_config"])
        for w in result["windows"]:
            self.assertGreaterEqual(w["start_date"], "2026-04-02")
            self.assertLessEqual(w["end_date"], "2026-04-06")
        result = generate_windows(self.calendar, req, config(before=0, after=0))
        self.assertEqual(len(result["windows"]), 1)
        self.assertEqual(result["windows"][0]["calendar_trip_days"], 1)

    def test_invalid_requests_and_config_fail_validation(self):
        for field, value in [("annual_leave_budget", -1), ("annual_leave_budget", True), ("blocked_dates", ["2026-02-30"]), ("personal_days_off", ["2026-01-01", "2026-01-01"])]:
            req = request(); req["travelers"][0][field] = value
            with self.assertRaises(ValidationError): generate_windows(self.calendar, req)
        req = request(); req["travelers"][1]["id"] = "traveler_a"
        with self.assertRaises(ValidationError): generate_windows(self.calendar, req)
        req = request(); req["unexpected"] = 1
        with self.assertRaises(ValidationError): generate_windows(self.calendar, req)
        req = request(); req["leave_constraints"].update(min_calendar_trip_days=5, max_calendar_trip_days=2)
        with self.assertRaises(ValidationError): generate_windows(self.calendar, req)
        for bad in ({}, config(before=-1), config(after=True), config(cap=0)):
            with self.assertRaises(ValidationError): generate_windows(self.calendar, request(), bad)
        with self.assertRaises(ValidationError): self.evaluate("2026-01-02", "2026-01-01")

    def test_repeat_and_normalized_order_determinism_without_mutation(self):
        req = request(year=2027); cfg = config(before=1, after=2)
        before = copy.deepcopy((req, cfg))
        a = generate_windows(self.calendar, req, cfg)
        b = generate_windows(self.calendar, req, cfg)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        req["travelers"].reverse()
        other = load_calendars([snapshot(2027), snapshot()])
        self.assertEqual(a, generate_windows(other, req, cfg))
        req["travelers"].reverse()
        self.assertEqual((req, cfg), before)
        ids = [w["window_id"] for w in a["windows"]]
        self.assertEqual(len(ids), len(set(ids)))


class WindowDominanceTests(unittest.TestCase):
    def window(self, wid, duration, a, b, side="BEFORE", status="OFFICIAL"):
        return {"window_id": wid, "holiday_type": "qingming", "holiday_anchor_date": "2026-04-03",
                "bridge_side": side, "holiday_status": status, "start_date": "2026-04-01", "end_date": "2026-04-06",
                "calendar_trip_days": duration, "leave_days_by_traveler": {"a": a, "b": b}}

    def test_longer_no_more_leave_dominates(self):
        small = self.window("small", 3, 1, 1); large = self.window("large", 4, 1, 1)
        self.assertEqual([w["window_id"] for w in prune_windows([small, large])], ["large"])

    def test_equal_duration_lower_leave_dominates(self):
        high = self.window("high", 4, 2, 1); low = self.window("low", 4, 1, 1)
        self.assertEqual([w["window_id"] for w in prune_windows([high, low])], ["low"])

    def test_traveler_tradeoffs_pre_post_and_evidence_are_incomparable(self):
        windows = [self.window("a", 4, 0, 2), self.window("b", 4, 1, 0),
                   self.window("post", 3, 2, 2, side="AFTER"),
                   self.window("estimate", 5, 0, 0, status="ESTIMATED")]
        self.assertEqual(len(prune_windows(windows)), 4)
        self.assertEqual(prune_windows(windows), prune_windows(list(reversed(windows))))

    def test_date_distinct_ties_survive(self):
        a = self.window("a", 4, 1, 1); b = self.window("b", 4, 1, 1)
        b["start_date"] = "2026-04-02"
        self.assertEqual(len(prune_windows([a, b])), 2)


if __name__ == "__main__": unittest.main()
