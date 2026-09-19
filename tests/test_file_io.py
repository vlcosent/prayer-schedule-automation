"""File-I/O tests: atomic-write cleanup, archive naming/idempotency, log rotation."""
from __future__ import annotations

import os
from datetime import datetime

import pytest

from prayer_schedule import file_io
from prayer_schedule.config import CENTRAL_TZ


def test_atomic_write_unlinks_tmp_on_replace_failure(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If os.replace fails after the tmp file is written, the tmp file must
    be cleaned up so it doesn't accumulate or shadow future writes.
    """
    target = os.path.join(str(tmp_path), "out.txt")
    tmp = f"{target}.tmp"

    def boom(_src: str, _dst: str) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(file_io.os, "replace", boom)

    with pytest.raises(OSError, match="simulated replace failure"):
        file_io._atomic_write(target, "hello")

    assert not os.path.exists(tmp), f"orphaned tmp file: {tmp}"
    assert not os.path.exists(target)


def test_archive_file_name_uses_following_monday() -> None:
    """Archive names carry the *following* Monday (the rollover day) plus the
    archived week's number, matching every file already in ``archive/``."""
    monday = datetime(2026, 9, 7, tzinfo=CENTRAL_TZ)  # ISO week 37
    assert file_io.archive_file_name(37, monday) == "Prayer_Schedule_2026-09-14_Week37.txt"


def test_archive_file_name_crosses_year_boundary() -> None:
    monday = datetime(2026, 12, 28, tzinfo=CENTRAL_TZ)  # ISO week 53 of 2026
    assert file_io.archive_file_name(53, monday) == "Prayer_Schedule_2027-01-04_Week53.txt"


def test_archive_file_name_rejects_non_monday() -> None:
    with pytest.raises(ValueError, match="must be a Monday"):
        file_io.archive_file_name(37, datetime(2026, 9, 8, tzinfo=CENTRAL_TZ))


def test_archive_week_schedule_writes_new_file(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(file_io, "DESKTOP_DIR", str(tmp_path))
    monday = datetime(2026, 9, 7, tzinfo=CENTRAL_TZ)

    assert file_io.archive_week_schedule("Week 37 body\n", 37, monday) is True

    archive_dir = os.path.join(str(tmp_path), "archive")
    assert os.listdir(archive_dir) == ["Prayer_Schedule_2026-09-14_Week37.txt"]
    with open(os.path.join(archive_dir, "Prayer_Schedule_2026-09-14_Week37.txt"), encoding="utf-8") as handle:
        assert handle.read() == "Week 37 body\n"


def test_archive_week_schedule_is_idempotent(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second call for the same week must leave the existing file untouched,
    so Tuesday..Sunday runs (and re-runs) never rewrite history."""
    monkeypatch.setattr(file_io, "DESKTOP_DIR", str(tmp_path))
    monday = datetime(2026, 9, 7, tzinfo=CENTRAL_TZ)

    assert file_io.archive_week_schedule("original\n", 37, monday) is True
    assert file_io.archive_week_schedule("different\n", 37, monday) is False

    archive_dir = os.path.join(str(tmp_path), "archive")
    assert os.listdir(archive_dir) == ["Prayer_Schedule_2026-09-14_Week37.txt"]
    with open(os.path.join(archive_dir, "Prayer_Schedule_2026-09-14_Week37.txt"), encoding="utf-8") as handle:
        assert handle.read() == "original\n"


def test_archive_week_schedule_reports_io_errors(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed archive write must not raise: the daily email still has to go out."""
    monkeypatch.setattr(file_io, "DESKTOP_DIR", str(tmp_path))

    def boom(_path: str, _content: str) -> None:
        raise OSError("simulated disk full")

    monkeypatch.setattr(file_io, "_atomic_write", boom)

    monday = datetime(2026, 9, 7, tzinfo=CENTRAL_TZ)
    assert file_io.archive_week_schedule("x", 37, monday) is False


def test_log_activity_rotates_when_oversized(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Once the log exceeds ``_LOG_MAX_BYTES``, the next write must move the
    old log to ``<log>.1`` and start fresh so desktop installs don't grow an
    unbounded file."""
    monkeypatch.setattr(file_io, "DESKTOP_DIR", str(tmp_path))
    monkeypatch.setattr(file_io, "_LOG_MAX_BYTES", 100)  # tiny for the test

    log_file = os.path.join(str(tmp_path), file_io._LOG_FILE_NAME)
    with open(log_file, "w", encoding="utf-8") as handle:
        handle.write("x" * 200)  # already over the limit
    assert os.path.getsize(log_file) > 100

    file_io.log_activity("after-rotation message")

    rotated = f"{log_file}.1"
    assert os.path.exists(rotated), "rotated copy not created"
    assert os.path.getsize(rotated) > 100, "rotated copy should contain the prior content"
    assert os.path.getsize(log_file) < 100, "new log should start fresh"
    with open(log_file, encoding="utf-8") as handle:
        body = handle.read()
    assert "after-rotation message" in body


def test_log_activity_does_not_rotate_under_threshold(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Below the threshold, no rotation occurs."""
    monkeypatch.setattr(file_io, "DESKTOP_DIR", str(tmp_path))
    monkeypatch.setattr(file_io, "_LOG_MAX_BYTES", 1_048_576)

    file_io.log_activity("first")
    file_io.log_activity("second")

    log_file = os.path.join(str(tmp_path), file_io._LOG_FILE_NAME)
    assert os.path.exists(log_file)
    assert not os.path.exists(f"{log_file}.1")
