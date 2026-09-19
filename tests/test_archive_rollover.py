"""Tests for the daily archive rollover orchestrated by ``cli.py``.

Last week's schedule is regenerated from the algorithm and written to
``archive/`` only when missing, so the rollover works from a fresh CI
checkout (no leftover current-week file) and survives a dropped Monday run.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest

from prayer_schedule import cli, file_io
from prayer_schedule.algorithm import (
    assign_families_for_week_v10,
    calculate_continuous_week,
)
from prayer_schedule.config import CENTRAL_TZ, REFERENCE_MONDAY
from prayer_schedule.output import generate_text_schedule


def test_archives_previous_week_from_scratch(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(file_io, "DESKTOP_DIR", str(tmp_path))
    this_monday = datetime(2026, 9, 14, tzinfo=CENTRAL_TZ)  # ISO week 38

    assert cli._archive_previous_week(this_monday) is True

    archive_dir = os.path.join(str(tmp_path), "archive")
    assert os.listdir(archive_dir) == ["Prayer_Schedule_2026-09-14_Week37.txt"]
    with open(os.path.join(archive_dir, "Prayer_Schedule_2026-09-14_Week37.txt"), encoding="utf-8") as handle:
        body = handle.read()
    assert "Week 37: September 07 - September 13, 2026" in body

    previous_monday = this_monday - timedelta(days=7)
    expected = generate_text_schedule(
        37,
        previous_monday,
        assign_families_for_week_v10(calculate_continuous_week(previous_monday)),
    )
    assert body == expected


def test_rollover_is_idempotent_across_daily_runs(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tuesday..Sunday runs find the file already present and leave it alone."""
    monkeypatch.setattr(file_io, "DESKTOP_DIR", str(tmp_path))
    this_monday = datetime(2026, 9, 14, tzinfo=CENTRAL_TZ)
    archive_path = os.path.join(str(tmp_path), "archive", "Prayer_Schedule_2026-09-14_Week37.txt")

    assert cli._archive_previous_week(this_monday) is True
    first_mtime = os.stat(archive_path).st_mtime_ns

    for _ in range(6):
        assert cli._archive_previous_week(this_monday) is False

    assert os.listdir(os.path.join(str(tmp_path), "archive")) == ["Prayer_Schedule_2026-09-14_Week37.txt"]
    assert os.stat(archive_path).st_mtime_ns == first_mtime


def test_rollover_across_year_boundary(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2026 has 53 ISO weeks; the first Monday of 2027 archives week 53."""
    monkeypatch.setattr(file_io, "DESKTOP_DIR", str(tmp_path))

    assert cli._archive_previous_week(datetime(2027, 1, 4, tzinfo=CENTRAL_TZ)) is True

    archive_dir = os.path.join(str(tmp_path), "archive")
    assert os.listdir(archive_dir) == ["Prayer_Schedule_2027-01-04_Week53.txt"]
    with open(os.path.join(archive_dir, "Prayer_Schedule_2027-01-04_Week53.txt"), encoding="utf-8") as handle:
        body = handle.read()
    assert body.startswith(
        "=" * 60 + "\nCROSSVILLE CHURCH OF CHRIST\nWeek 53: December 28 - January 03, 2027\n"
    )


def test_nothing_to_archive_before_reference_week(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The week before REFERENCE_MONDAY has no continuous week number; the
    rollover must skip cleanly instead of raising."""
    monkeypatch.setattr(file_io, "DESKTOP_DIR", str(tmp_path))

    assert cli._archive_previous_week(REFERENCE_MONDAY) is False

    assert not os.path.exists(os.path.join(str(tmp_path), "archive"))
    assert "Nothing to archive" in capsys.readouterr().out
