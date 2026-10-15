"""Synthetic examples only, no real traveler identity or holiday claims."""
import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def snapshot(year=2026):
    return json.loads((FIXTURES / f"holiday_calendar_test_{year}.json").read_text())


def request(year=2026, budget_a=3, budget_b=3):
    return {
        "planning_year": year,
        "travelers": [
            {"id": "traveler_a", "annual_leave_budget": budget_a, "miles_balance": 0},
            {"id": "traveler_b", "annual_leave_budget": budget_b, "miles_balance": 0},
        ],
        "origin_airports": ["HKG"], "holiday_types": ["new_year"],
        "cabin_preferences": {
            "longhaul_minimum": "W", "longhaul_preferred": "J", "shorthaul_minimum": "Y",
            "allow_mixed_cabin": True, "allow_separate_tickets": True,
        },
        "leave_constraints": {"min_calendar_trip_days": 1, "max_calendar_trip_days": 7,
                              "max_leave_days_per_trip": 3, "allow_bridge_leave": True},
    }


def config(before=2, after=3, cap=30):
    return {"holiday_window": {"days_before": before, "days_after": after,
                               "max_generated_windows_per_holiday": cap}}
