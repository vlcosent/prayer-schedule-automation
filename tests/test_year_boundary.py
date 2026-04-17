"""Regression tests for the ISO-week year-boundary bug.

Without `calculate_continuous_week`, the rotation cycle position would
jump when ISO week numbers reset from 52/53 → 1 at year boundaries.
This test locks in the fix so a future refactor can't re-introduce the bug.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from prayer_schedule.algorithm import (
    assign_families_for_week_v10,
    calculate_continuous_week,
)
from prayer_schedule.config import CENTRAL_TZ, REFERENCE_MONDAY


YEAR_BOUNDARIES = [
    (datetime(2025, 12, 29, tzinfo=CENTRAL_TZ), datetime(2026, 1, 5, tzinfo=CENTRAL_TZ)),
    (datetime(2026, 12, 28, tzinfo=CENTRAL_TZ), datetime(2027, 1, 4, tzinfo=CENTRAL_TZ)),
    (datetime(2027, 12, 27, tzinfo=CENTRAL_TZ), datetime(2028, 1, 3, tzinfo=CENTRAL_TZ)),
    (datetime(2028, 12, 25, tzinfo=CENTRAL_TZ), datetime(2029, 1, 1, tzinfo=CENTRAL_TZ)),
]


def test_reference_monday_is_iso_week1_of_2026() -> None:
    iso = REFERENCE_MONDAY.isocalendar()
    assert iso.year == 2026
    assert iso.week == 1


@pytest.mark.parametrize("week1, week2", YEAR_BOUNDARIES)
def test_cycle_position_advances_by_one_across_year(
    week1: datetime, week2: datetime
) -> None:
    cw1 = calculate_continuous_week(week1)
    cw2 = calculate_continuous_week(week2)
    assert cw2 - cw1 == 1, f"continuous_week jumped from {cw1} to {cw2}"
    assert ((cw2 - 1) % 8 - (cw1 - 1) % 8) % 8 == 1


@pytest.mark.parametrize("week1, week2", YEAR_BOUNDARIES)
def test_no_family_overlap_across_year_boundary(
    week1: datetime, week2: datetime
) -> None:
    cw1 = calculate_continuous_week(week1)
    cw2 = calculate_continuous_week(week2)
    a1 = assign_families_for_week_v10(cw1)
    a2 = assign_families_for_week_v10(cw2)
    for elder in a1:
        overlap = set(a1[elder]) & set(a2[elder])
        assert not overlap, f"{elder}: {week1}→{week2} repeated families: {overlap}"


def test_continuous_week_matches_iso_within_2026() -> None:
    """Within 2026, continuous_week must equal ISO week (by design of REFERENCE_MONDAY)."""
    monday = REFERENCE_MONDAY
    for _ in range(53):
        iso = monday.isocalendar()
        if iso.year != 2026:
            break
        assert calculate_continuous_week(monday) == iso.week
        monday = monday + timedelta(days=7)


def test_leap_year_2028_week_math() -> None:
    # 2028 is a leap year. Pick a Monday in March to confirm math still works.
    d = datetime(2028, 3, 6, tzinfo=CENTRAL_TZ)
    cw = calculate_continuous_week(d)
    assert cw > 0
    # Assignments should still be valid.
    assignments = assign_families_for_week_v10(cw)
    assert sum(len(v) for v in assignments.values()) == 161
