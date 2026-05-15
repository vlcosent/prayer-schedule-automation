"""File-I/O tests: atomic-write cleanup, archive timezone, archive idempotency."""
from __future__ import annotations

import os
from datetime import datetime, timezone

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


def test_archive_filename_uses_central_date(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The archive filename should reflect the Central-time date, not server UTC.

    Pick a UTC instant where Central is the *prior* calendar day (UTC just
    after midnight, Central still in the previous day). The archive name must
    use the Central date.
    """
    monkeypatch.setattr(file_io, "DESKTOP_DIR", str(tmp_path))
    current_txt = os.path.join(str(tmp_path), "Prayer_Schedule_Current_Week.txt")
    with open(current_txt, "w", encoding="utf-8") as handle:
        handle.write("WEEK 5\nDaily prayer schedule body\n")

    # 2026-05-15 03:00 UTC = 2026-05-14 22:00 Central (CDT, UTC-5).
    fixed_utc = datetime(2026, 5, 15, 3, 0, tzinfo=timezone.utc)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:  # type: ignore[override]
            if tz is None:
                return fixed_utc.replace(tzinfo=None)
            return fixed_utc.astimezone(tz)

    monkeypatch.setattr(file_io, "datetime", FrozenDateTime)

    assert file_io.archive_previous_schedule() is True

    archive_dir = os.path.join(str(tmp_path), "archive")
    entries = os.listdir(archive_dir)
    assert len(entries) == 1, entries
    # Central calendar day is the 14th, not the 15th (UTC).
    assert "2026-05-14" in entries[0], entries[0]
    assert "Week5" in entries[0], entries[0]


def test_archive_does_not_overwrite_existing(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running archive twice in the same Central day must not silently
    overwrite the prior archive; the second run should land at a suffixed
    name so both copies survive.
    """
    monkeypatch.setattr(file_io, "DESKTOP_DIR", str(tmp_path))

    archive_dir = os.path.join(str(tmp_path), "archive")
    os.makedirs(archive_dir, exist_ok=True)

    # First run: write current schedule and archive it.
    current_txt = os.path.join(str(tmp_path), "Prayer_Schedule_Current_Week.txt")
    with open(current_txt, "w", encoding="utf-8") as handle:
        handle.write("WEEK 5\nFirst content\n")
    assert file_io.archive_previous_schedule() is True

    first_listing = sorted(os.listdir(archive_dir))
    assert len(first_listing) == 1

    # Second run on the same Central day: write a different current schedule
    # and archive again. Both archives should coexist.
    with open(current_txt, "w", encoding="utf-8") as handle:
        handle.write("WEEK 5\nSecond content\n")
    assert file_io.archive_previous_schedule() is True

    final_listing = sorted(os.listdir(archive_dir))
    assert len(final_listing) == 2, final_listing

    # Verify the second archive contains the second body — i.e., the first
    # archive was not overwritten.
    bodies = sorted(
        open(os.path.join(archive_dir, name), encoding="utf-8").read()
        for name in final_listing
    )
    assert "First content" in bodies[0]
    assert "Second content" in bodies[1]


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
