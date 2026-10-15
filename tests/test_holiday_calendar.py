import copy
import unittest

from discovery._validation import ValidationError
from discovery.holiday_calendar import CalendarCoverageError, load_calendar, load_calendars
from tests._fixtures import FIXTURES, snapshot


class HolidayCalendarTests(unittest.TestCase):
    def test_load_path_and_normal_weekend_fallback(self):
        calendar = load_calendar(FIXTURES / "holiday_calendar_test_2026.json")
        day = calendar.day("2026-01-04")
        self.assertEqual(day["day_type"], "WEEKEND")
        self.assertTrue(day["inferred_weekday_weekend"])
        self.assertEqual(calendar.day("2026-01-05")["day_type"], "WORKDAY")

    def test_official_public_holiday_and_makeup_precedence(self):
        calendar = load_calendar(snapshot())
        self.assertEqual(calendar.day("2026-01-01")["day_type"], "PUBLIC_HOLIDAY")
        self.assertEqual(calendar.day("2026-01-01")["source_status"], "OFFICIAL")
        self.assertEqual(calendar.day("2026-01-03")["day_type"], "MAKEUP_WORKDAY")
        self.assertFalse(calendar.day("2026-01-03")["inferred_weekday_weekend"])

    def test_explicit_weekday_weekend_override(self):
        data = snapshot(); data["days"].append({"date": "2026-01-05", "day_type": "WEEKEND"})
        self.assertEqual(load_calendar(data).day("2026-01-05")["day_type"], "WEEKEND")

    def test_per_day_status_and_source_override(self):
        data = snapshot(); data["days"][0].update(source_status="ESTIMATED", source_url="https://example.invalid/estimate")
        day = load_calendar(data).day("2026-01-01")
        self.assertEqual(day["source_status"], "ESTIMATED")
        self.assertEqual(day["calendar_source_status"], "OFFICIAL")
        self.assertEqual(day["source_url"], "https://example.invalid/estimate")
        data["source_status"] = "ESTIMATED"; data["days"][0]["source_status"] = "OFFICIAL"
        self.assertEqual(load_calendar(data).day("2026-01-01")["source_status"], "OFFICIAL")

    def test_estimated_calendar_does_not_invent_makeup_days(self):
        calendar = load_calendar(snapshot(2027))
        self.assertEqual(calendar.day("2027-01-02")["day_type"], "WEEKEND")
        self.assertEqual(calendar.day("2027-01-02")["source_status"], "ESTIMATED")

    def test_missing_year_fails_explicitly(self):
        with self.assertRaisesRegex(CalendarCoverageError, "CALENDAR_YEAR_MISSING"):
            load_calendar(snapshot()).day("2027-01-01")

    def test_cross_year_snapshot_loading(self):
        calendar = load_calendars([snapshot(2027), snapshot()])
        self.assertEqual(calendar.day("2026-12-31")["source_status"], "OFFICIAL")
        self.assertEqual(calendar.day("2027-01-01")["source_status"], "ESTIMATED")

    def test_calendar_schema_rejects_required_enum_and_extra_fields(self):
        for field, value in [("calendar_id", ""), ("year", True), ("source_status", "UNKNOWN"), ("days", {})]:
            with self.subTest(field=field):
                data = snapshot(); data[field] = value
                with self.assertRaises(ValidationError): load_calendar(data)
        data = snapshot(); del data["jurisdiction"]
        with self.assertRaises(ValidationError): load_calendar(data)
        data = snapshot(); data["surprise"] = 1
        with self.assertRaises(ValidationError): load_calendar(data)
        data = snapshot(); data["days"][0]["surprise"] = 1
        with self.assertRaises(ValidationError): load_calendar(data)

    def test_invalid_date_and_datetime_formats(self):
        for value in ("2026-02-30", "20260101", "2026-1-01", "2026-01-01T00:00:00Z"):
            with self.subTest(value=value):
                data = snapshot(); data["days"][0]["date"] = value
                with self.assertRaises(ValidationError): load_calendar(data)
        for value in ("not-a-time", "2026-02-30T00:00:00Z", "2026-10-15T00:00:00"):
            data = snapshot(); data["observed_at"] = value
            with self.assertRaises(ValidationError): load_calendar(data)
        data = snapshot(); data["observed_at"] = None
        load_calendar(data)

    def test_duplicate_dates_and_mismatching_year_rejected(self):
        data = snapshot(); data["days"].append(copy.deepcopy(data["days"][0]))
        with self.assertRaisesRegex(ValidationError, "duplicate calendar date"): load_calendar(data)
        data = snapshot(); data["days"][0]["date"] = "2027-01-01"
        with self.assertRaisesRegex(ValidationError, "year differs"): load_calendar(data)

    def test_mismatching_jurisdictions_and_duplicate_snapshots_rejected(self):
        other = snapshot(2027); other["jurisdiction"] = "OTHER_TEST"
        with self.assertRaisesRegex(ValidationError, "jurisdictions"): load_calendars([snapshot(), other])
        with self.assertRaisesRegex(ValidationError, "duplicate calendar year"): load_calendars([snapshot(), snapshot()])
        with self.assertRaises(ValidationError): load_calendars([])

    def test_snapshot_is_copied(self):
        data = snapshot(); calendar = load_calendar(data)
        data["days"][0]["day_type"] = "WORKDAY"
        day = calendar.day("2026-01-01"); day["day_type"] = "WORKDAY"
        self.assertEqual(calendar.day("2026-01-01")["day_type"], "PUBLIC_HOLIDAY")

    def test_holiday_anchors_are_explicit_and_sorted(self):
        calendar = load_calendar(snapshot())
        self.assertEqual([d.isoformat() for d in calendar.holiday_dates(2026, "new_year")], ["2026-01-01"])
        self.assertEqual(calendar.holiday_dates(2026, "mid_autumn"), [])


if __name__ == "__main__": unittest.main()
