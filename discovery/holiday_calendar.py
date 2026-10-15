"""Holiday snapshot loading and date classification, independent of award rules."""
import copy
from datetime import date
import json
from pathlib import Path

from ._validation import ValidationError, parse_date, validate


class CalendarCoverageError(ValueError):
    """No snapshot covers the requested year; do not invent holiday facts."""


class HolidayCalendar:
    """One jurisdiction, one or more annual snapshots, no conflicting dates."""

    def __init__(self, snapshots):
        self._snapshots = {}
        self._days = {}
        jurisdiction = None
        for supplied in snapshots:
            snapshot = copy.deepcopy(supplied)
            validate(snapshot, "holiday_calendar.schema.json")
            year = int(snapshot["year"])
            if not 1 <= year <= 9999:
                raise ValidationError("calendar year outside supported date range")
            if year in self._snapshots:
                raise ValidationError("duplicate calendar year: " + str(year))
            if jurisdiction is not None and snapshot["jurisdiction"] != jurisdiction:
                raise ValidationError("calendar jurisdictions must match")
            jurisdiction = snapshot["jurisdiction"]
            self._snapshots[year] = snapshot
            for entry in snapshot["days"]:
                day = parse_date(entry["date"])
                if day.year != year:
                    raise ValidationError("calendar entry year differs from snapshot year")
                if day in self._days:
                    raise ValidationError("duplicate calendar date: " + day.isoformat())
                self._days[day] = entry
        if not self._snapshots:
            raise ValidationError("at least one calendar snapshot is required")
        self.jurisdiction = jurisdiction

    def day(self, value):
        day = value if type(value) is date else parse_date(value)
        snapshot = self._snapshots.get(day.year)
        if snapshot is None:
            raise CalendarCoverageError("CALENDAR_YEAR_MISSING: " + str(day.year))
        entry = self._days.get(day, {})
        return {
            "date": day.isoformat(),
            "day_type": entry.get("day_type", "WEEKEND" if day.weekday() >= 5 else "WORKDAY"),
            "holiday_name": entry.get("holiday_name"),
            "source_status": entry.get("source_status", snapshot["source_status"]),
            "source_url": entry.get("source_url", snapshot.get("source_url")),
            "observed_at": snapshot.get("observed_at"),
            "calendar_id": snapshot["calendar_id"],
            "calendar_source_status": snapshot["source_status"],
            "inferred_weekday_weekend": not bool(entry),
        }

    def holiday_dates(self, year, holiday_type):
        if year not in self._snapshots:
            raise CalendarCoverageError("CALENDAR_YEAR_MISSING: " + str(year))
        return sorted(day for day, entry in self._days.items()
                      if day.year == year and entry["day_type"] == "PUBLIC_HOLIDAY"
                      and entry.get("holiday_name") == holiday_type)


def load_calendar(source):
    """Load a schema-conforming mapping or JSON path into an annual calendar."""
    if isinstance(source, (str, Path)):
        source = json.loads(Path(source).read_text(encoding="utf-8"))
    return HolidayCalendar([source])


def load_calendars(sources):
    """Combine adjacent annual snapshots for cross-year planning."""
    snapshots = []
    for source in sources:
        if isinstance(source, (str, Path)):
            source = json.loads(Path(source).read_text(encoding="utf-8"))
        snapshots.append(source)
    return HolidayCalendar(snapshots)
