"""Core assignment-algorithm tests — invariants across many weeks."""
from __future__ import annotations

import pytest

from prayer_schedule.algorithm import (
    assign_families_for_week_v10,
    create_v10_master_pools,
    get_master_pools,
)


# Test a range wide enough to cover two full 8-week cycles.
WEEK_RANGE = range(32, 48)


def test_pool_distribution_sums_to_161() -> None:
    pools = create_v10_master_pools()
    assert len(pools) == 8
    total = sum(len(p) for p in pools)
    assert total == 161


def test_pool_sizes_19_to_21() -> None:
    pools = create_v10_master_pools()
    # 161 = 20*8 + 1 → one pool has 21, the rest have 20.
    sizes = sorted(len(p) for p in pools)
    assert sizes == [20, 20, 20, 20, 20, 20, 20, 21]


def test_no_family_in_two_pools() -> None:
    pools = create_v10_master_pools()
    all_families: list[str] = []
    for p in pools:
        all_families.extend(p)
    assert len(all_families) == len(set(all_families))


def test_get_master_pools_is_cached() -> None:
    # Sanity: repeated calls return the same list object.
    assert get_master_pools() is get_master_pools()


@pytest.mark.parametrize("week", list(WEEK_RANGE))
def test_each_week_covers_161_families(week: int, directory_families: list[str]) -> None:
    assignments = assign_families_for_week_v10(week)
    flat: list[str] = []
    for fams in assignments.values():
        flat.extend(fams)
    assert len(flat) == 161
    assert set(flat) == set(directory_families)


@pytest.mark.parametrize("week", list(WEEK_RANGE))
def test_each_elder_gets_19_to_21(week: int, elders: list[str]) -> None:
    assignments = assign_families_for_week_v10(week)
    assert set(assignments.keys()) == set(elders)
    for elder, fams in assignments.items():
        assert 19 <= len(fams) <= 21, (elder, len(fams))


@pytest.mark.parametrize("week", list(WEEK_RANGE))
def test_no_elder_gets_own_family(week: int, elder_families: dict[str, str]) -> None:
    assignments = assign_families_for_week_v10(week)
    for elder, fams in assignments.items():
        assert elder_families[elder] not in fams, f"{elder} got own family in week {week}"


@pytest.mark.parametrize("week", list(WEEK_RANGE))
def test_no_duplicate_families_in_week(week: int) -> None:
    assignments = assign_families_for_week_v10(week)
    flat: list[str] = []
    for fams in assignments.values():
        flat.extend(fams)
    assert len(flat) == len(set(flat))


def test_eight_week_cycle_repeats(elders: list[str]) -> None:
    for elder in elders:
        first = assign_families_for_week_v10(32)[elder]
        second = assign_families_for_week_v10(40)[elder]
        assert set(first) == set(second), f"{elder}'s week 32 and week 40 differ"


def test_week_to_week_full_rotation(elders: list[str]) -> None:
    """Each elder should see 100% new families week-over-week."""
    for week in WEEK_RANGE:
        this_week = assign_families_for_week_v10(week)
        next_week = assign_families_for_week_v10(week + 1)
        for elder in elders:
            overlap = set(this_week[elder]) & set(next_week[elder])
            assert not overlap, (
                f"{elder}: week {week} and week {week + 1} share {overlap}"
            )
