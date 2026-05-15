"""Pool distribution, week-number arithmetic, and weekly family assignment.

This is the heart of the V10 rotation algorithm. ``create_v10_master_pools``
distributes the 161 families round-robin into 7 pools.
``assign_families_for_week_v10`` selects the weekly pool per elder, filters
out each elder's own family, and redistributes filtered families according
to :data:`FIXED_REASSIGNMENT_MAP` to guarantee 22-24 families per elder and
no week-to-week repeats.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .config import POOL_COUNT, REFERENCE_MONDAY
from .directory import parse_directory
from .elders import ELDER_FAMILIES, ELDERS


def calculate_week_number(date: datetime) -> int:
    """Return the ISO week number for ``date`` (printed for debug visibility)."""
    iso_year, iso_week, iso_day = date.isocalendar()

    # Log the ISO week for debugging (preserves behaviour of the original script).
    print(f"  Date {date.strftime('%Y-%m-%d')} = ISO Week {iso_week} of {iso_year}")

    return iso_week


def calculate_continuous_week(monday_date: datetime) -> int:
    """Return a continuous week number that never resets at year boundaries.

    ISO week numbers reset from 52/53 to 1 at the start of each ISO year,
    which causes the rotation cycle_position to jump (e.g., from 3 to 0
    instead of advancing to 4). This function returns a monotonically increasing
    week number based on a fixed reference date (:data:`REFERENCE_MONDAY`),
    ensuring the cycle always advances by exactly 1 each week.

    The reference is chosen so that for all of 2026, the continuous week number
    equals the ISO week number, maintaining identical behavior to the old code
    within the current year while fixing the year-boundary problem.
    """
    # Strip timezone info for arithmetic so callers can pass either
    # naive or aware datetimes (e.g., verification tests use naive dates).
    ref = REFERENCE_MONDAY.replace(tzinfo=None)
    md = monday_date.replace(tzinfo=None) if monday_date.tzinfo else monday_date
    days_diff = (md - ref).days
    return (days_diff // 7) + 1  # 1-based to match ISO week convention


def create_v10_master_pools() -> list[list[str]]:
    """Distribute all families round-robin into ``POOL_COUNT`` sorted pools.

    Returns a list of ``POOL_COUNT`` lists. With 161 families and 7 pools,
    each pool ends up with exactly 23 families (161 = 7 * 23).
    """
    families = parse_directory()

    # Create the pools.
    pools: list[list[str]] = [[] for _ in range(POOL_COUNT)]

    # Distribute all families round-robin style.  With 161 families and 7
    # pools this naturally achieves 23 families in every pool.
    for i, family in enumerate(families):
        pool_idx = i % POOL_COUNT
        pools[pool_idx].append(family)

    # Sort each pool for consistency.
    for pool in pools:
        pool.sort()

    return pools


# Module-level cache so ``get_master_pools()`` is idempotent per process.
_MASTER_POOLS: Optional[list[list[str]]] = None


def get_master_pools() -> list[list[str]]:
    """Return the cached master pools, building them on first access."""
    global _MASTER_POOLS
    if _MASTER_POOLS is None:
        _MASTER_POOLS = create_v10_master_pools()
    return _MASTER_POOLS


# Fixed reassignment mapping based on conflict analysis (161 families, 7 pools
# of 23 families each). For each cycle position 0..6, any elder whose own
# family lands in their assigned pool has it filtered out; this map names the
# elder who absorbs that filtered family.
# - Cycle 1: Larry McDuffee's family filtered (in Pool 0)
# - Cycle 2: Brian McLaughlin's family filtered (in Pool 2)
# - Cycle 3: Frank Bohannon's, Jonathan Loveday's, and L.A. Fox's families filtered
# - Cycle 4: Jerry Wood's family filtered (in Pool 6)
# - Cycle 6: Kyle Fairman's family filtered (in Pool 3)
#
# Reassignments chosen to maintain 22-24 family balance and avoid repeats:
# Each target verified SAFE (family not in target's adjacent-week pools).
FIXED_REASSIGNMENT_MAP: dict[int, dict[str, str]] = {
    1: {"Larry McDuffee": "Frank Bohannon"},     # Larry(22) filtered -> Frank(23->24) SAFE
    2: {"Brian McLaughlin": "Jerry Wood"},       # Brian(22) filtered -> Jerry(23->24) SAFE
    3: {"Frank Bohannon": "Jonathan Loveday",    # Frank(22) filtered -> Jonathan(22->23) SAFE
        "Jonathan Loveday": "Brian McLaughlin",  # Jonathan(22) filtered -> Brian(23->24) SAFE
        "L.A. Fox": "Frank Bohannon"},           # L.A.(22) filtered -> Frank(22->23) SAFE
    4: {"Jerry Wood": "Brian McLaughlin"},       # Jerry(22) filtered -> Brian(23->24) SAFE
    6: {"Kyle Fairman": "Brian McLaughlin"},     # Kyle(22) filtered -> Brian(23->24) SAFE
}


def assign_families_for_week_v10(week_number: int) -> dict[str, list[str]]:
    """Compute the per-elder family assignments for ``week_number``.

    Behaviour (preserves the V10 contract used by the helper scripts):

    1. Each elder ``i`` is assigned pool ``(i + cycle_position) % POOL_COUNT``
       where ``cycle_position = (week_number - 1) % POOL_COUNT``.
    2. If an elder's own family is in their assigned pool, it is filtered
       out and re-targeted to another elder via :data:`FIXED_REASSIGNMENT_MAP`.
    3. The reassignment targets are pre-verified to be adjacency-safe (no
       week-to-week repeats for any elder).

    Returns a dict mapping elder name -> list of family strings for the week.
    """
    master_pools = get_master_pools()

    # Calculate position in the rotation cycle.
    cycle_position = (week_number - 1) % POOL_COUNT

    # First, collect filtered (elder-own) families and who owns them.
    filtered_families_data: list[tuple[str, str, int]] = []
    for elder_idx, elder in enumerate(ELDERS):
        pool_idx = (elder_idx + cycle_position) % POOL_COUNT
        elder_own_family = ELDER_FAMILIES.get(elder)

        if elder_own_family in master_pools[pool_idx]:
            # This elder's family is in their pool and needs reassignment.
            filtered_families_data.append((elder_own_family, elder, elder_idx))

    # First pass: assign pools and filter out own families.
    assignments: dict[str, list[str]] = {}
    for elder_idx, elder in enumerate(ELDERS):
        pool_idx = (elder_idx + cycle_position) % POOL_COUNT

        pool_families = master_pools[pool_idx].copy()
        elder_own_family = ELDER_FAMILIES.get(elder)

        if elder_own_family in pool_families:
            pool_families.remove(elder_own_family)

        assignments[elder] = pool_families

    # Second pass: redistribute filtered families using the fixed reassignment
    # table to guarantee consistency and no week-to-week repeats.
    reassignment_map = FIXED_REASSIGNMENT_MAP.get(cycle_position, {})

    for elder_family, owner_elder, owner_idx in filtered_families_data:
        best_elder = reassignment_map.get(owner_elder)

        # Fallback if not in map (shouldn't happen with a correct map).
        if not best_elder:
            best_elder = ELDERS[(owner_idx + 4) % len(ELDERS)]

        assignments[best_elder].append(elder_family)

    return assignments
