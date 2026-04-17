"""Tests for build_landing_page.py archive rendering."""
from __future__ import annotations

import os
import sys
from datetime import date

# Make the repo root importable (conftest.py already does this for the
# prayer_schedule package, but build_landing_page.py sits at the repo root).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import build_landing_page as blp  # noqa: E402


def test_archive_regex_matches_canonical_name() -> None:
    m = blp.ARCHIVE_RE.match("Prayer_Schedule_2026-01-05_Week1.txt")
    assert m is not None
    assert m.group("date") == "2026-01-05"
    assert m.group("week") == "1"


def test_archive_regex_rejects_non_archive_files() -> None:
    assert blp.ARCHIVE_RE.match("README.md") is None
    assert blp.ARCHIVE_RE.match("Prayer_Schedule_Current_Week.html") is None


def test_collect_archive_entries_sorted_newest_first(tmp_path) -> None:
    (tmp_path / "Prayer_Schedule_2026-01-05_Week1.txt").write_text("x")
    (tmp_path / "Prayer_Schedule_2026-01-12_Week2.txt").write_text("x")
    (tmp_path / "Prayer_Schedule_2025-12-29_Week52.txt").write_text("x")
    (tmp_path / "README.md").write_text("ignored")

    entries = blp.collect_archive_entries(str(tmp_path))
    assert [e["date"] for e in entries] == [
        date(2026, 1, 12),
        date(2026, 1, 5),
        date(2025, 12, 29),
    ]


def test_render_includes_archive_links(tmp_path) -> None:
    (tmp_path / "Prayer_Schedule_2026-01-05_Week1.txt").write_text("x")
    entries = blp.collect_archive_entries(str(tmp_path))
    html = blp.render(entries, current_exists=True)
    assert "Prayer_Schedule_2026-01-05_Week1.txt" in html
    assert "Week 1" in html
    assert "View This Week" in html


def test_render_handles_empty_archive() -> None:
    html = blp.render([], current_exists=False)
    assert "Current week schedule not yet generated" in html
    assert "No archived schedules yet" in html


def test_render_escapes_unusual_filenames(tmp_path) -> None:
    # The regex won't match, so this should not be included.
    (tmp_path / "Prayer_Schedule_2026-01-05_Week1<script>.txt").write_text("x")
    entries = blp.collect_archive_entries(str(tmp_path))
    assert entries == []
