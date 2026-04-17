"""Startup-validator tests."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from prayer_schedule.algorithm import assign_families_for_week_v10, calculate_continuous_week
from prayer_schedule.config import CENTRAL_TZ
from prayer_schedule.elders import get_week_schedule
from prayer_schedule.validation import (
    validate_elder_data,
    validate_reassignment_map,
    verify_email_date,
    verify_schedule,
    verify_today_elder_assignment,
)


def test_validate_elder_data_passes() -> None:
    ok, issues = validate_elder_data()
    assert ok, issues


def test_validate_reassignment_map_passes() -> None:
    ok, issues = validate_reassignment_map()
    assert ok, issues


def test_verify_schedule_on_real_assignments() -> None:
    assignments = assign_families_for_week_v10(32)
    ok, issues = verify_schedule(assignments)
    assert ok, issues


def test_verify_today_elder_assignment_friday() -> None:
    # A Friday: Kyle Fairman is on duty.
    friday = datetime(2026, 4, 17, 12, 0, tzinfo=CENTRAL_TZ)
    monday = friday - timedelta(days=4)
    cw = calculate_continuous_week(monday)
    assignments = assign_families_for_week_v10(cw)
    schedule = get_week_schedule(cw)
    ok, msg = verify_today_elder_assignment(friday, schedule, assignments)
    assert ok, msg
    assert "Kyle Fairman" in msg


def test_verify_today_elder_fails_on_empty_assignment() -> None:
    friday = datetime(2026, 4, 17, 12, 0, tzinfo=CENTRAL_TZ)
    schedule = get_week_schedule(1)
    bad_assignments = {elder: [] for elder in schedule["Friday"]}
    for elder in schedule["Monday"]:
        bad_assignments.setdefault(elder, [])
    ok, msg = verify_today_elder_assignment(friday, schedule, bad_assignments)
    assert not ok
    assert "Kyle Fairman" in msg


def test_verify_email_date_passes_for_valid_friday() -> None:
    friday = datetime(2026, 4, 17, 9, 0, tzinfo=CENTRAL_TZ)
    monday = datetime(2026, 4, 13, tzinfo=CENTRAL_TZ)
    ok, msg = verify_email_date(friday, monday)
    assert ok, msg


def test_verify_email_date_rejects_out_of_week() -> None:
    friday = datetime(2026, 4, 17, 9, 0, tzinfo=CENTRAL_TZ)
    wrong_monday = datetime(2026, 4, 6, tzinfo=CENTRAL_TZ)  # week before
    ok, _ = verify_email_date(friday, wrong_monday)
    assert not ok
