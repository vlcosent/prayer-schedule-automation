"""Core assignment-algorithm tests — invariants across many weeks."""
from __future__ import annotations

import pytest

from prayer_schedule import algorithm
from prayer_schedule.algorithm import (
    assign_families_for_week_v10,
    create_v10_master_pools,
    get_master_pools,
)
from prayer_schedule.config import (
    FAMILIES_PER_ELDER_MAX,
    FAMILIES_PER_ELDER_MIN,
    POOL_COUNT,
    ROTATION_WEEKS,
)


# Test a range wide enough to cover two full rotation cycles.
WEEK_RANGE = range(32, 32 + ROTATION_WEEKS * 2)


def test_pool_distribution_sums_to_161() -> None:
    pools = create_v10_master_pools()
    assert len(pools) == POOL_COUNT
    total = sum(len(p) for p in pools)
    assert total == 161


def test_pool_sizes_evenly_split() -> None:
    pools = create_v10_master_pools()
    # 161 = 23 * 7 → every pool has exactly 23 families.
    sizes = sorted(len(p) for p in pools)
    assert sizes == [23] * POOL_COUNT


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
def test_each_elder_gets_in_range(week: int, elders: list[str]) -> None:
    assignments = assign_families_for_week_v10(week)
    assert set(assignments.keys()) == set(elders)
    for elder, fams in assignments.items():
        assert FAMILIES_PER_ELDER_MIN <= len(fams) <= FAMILIES_PER_ELDER_MAX, (
            elder,
            len(fams),
        )


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


def test_rotation_cycle_repeats(elders: list[str]) -> None:
    for elder in elders:
        first = assign_families_for_week_v10(32)[elder]
        second = assign_families_for_week_v10(32 + ROTATION_WEEKS)[elder]
        assert set(first) == set(second), (
            f"{elder}'s week 32 and week {32 + ROTATION_WEEKS} differ"
        )


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


def test_assign_families_raises_when_reassignment_map_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If FIXED_REASSIGNMENT_MAP is missing an entry for an elder whose family
    landed in their own pool, the algorithm must fail loudly rather than
    silently routing the family to a guessed elder.

    Cycle position 1 (week_number=2) is known to have Larry McDuffee's family
    filtered into his pool; clearing the map for that position guarantees a
    missing entry.
    """
    monkeypatch.setattr(algorithm, "FIXED_REASSIGNMENT_MAP", {})
    with pytest.raises(RuntimeError, match="FIXED_REASSIGNMENT_MAP missing entry"):
        assign_families_for_week_v10(2)
