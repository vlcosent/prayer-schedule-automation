"""Directory parsing tests."""
from __future__ import annotations

import pytest

from prayer_schedule.directory import DIRECTORY_CSV, parse_directory


def test_family_count(directory_families: list[str]) -> None:
    assert len(directory_families) == 161


def test_families_sorted(directory_families: list[str]) -> None:
    assert directory_families == sorted(directory_families)


def test_no_duplicate_families(directory_families: list[str]) -> None:
    assert len(directory_families) == len(set(directory_families))


def test_families_well_formed(directory_families: list[str]) -> None:
    for fam in directory_families:
        assert ", " in fam, f"malformed family entry: {fam!r}"


def test_parse_rejects_malformed_csv() -> None:
    bad_csv = "Last Name,First Names\nOnlyLastName\n"
    with pytest.raises(ValueError):
        parse_directory(bad_csv)


def test_parse_rejects_duplicates() -> None:
    dup_csv = "Last Name,First Names\nSmith,John\nSmith,John\n"
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        parse_directory(dup_csv)


def test_parse_skips_empty_rows() -> None:
    csv_with_blank = "Last Name,First Names\nSmith,John\n\n\n"
    families = parse_directory(csv_with_blank)
    assert families == ["Smith, John"]


def test_directory_csv_has_header() -> None:
    assert DIRECTORY_CSV.startswith("Last Name,First Names\n")
