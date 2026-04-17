"""Pool distribution, week-number arithmetic, and weekly family assignment.

This is the heart of the V10 rotation algorithm. ``create_v10_master_pools``
distributes the 161 families round-robin into 8 pools.
``assign_families_for_week_v10`` selects the weekly pool per elder, filters
out each elder's own family, and redistributes filtered families according
to :data:`FIXED_REASSIGNMENT_MAP` to guarantee 19-21 families per elder and
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
    which causes the 8-week rotation cycle_position to jump (e.g., from 3 to 0
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

    Returns a list of ``POOL_COUNT`` lists. With 161 families and 8 pools,
    Pool 0 ends up with 21 families and Pools 1-7 have 20 each.
    """
    families = parse_directory()

    # Create the pools.
    pools: list[list[str]] = [[] for _ in range(POOL_COUNT)]

    # Distribute all families round-robin style.  This naturally achieves
    # the target sizes (21, 20, 20, 20, 20, 20, 20, 20 for 161 families).
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


# Fixed reassignment mapping based on conflict analysis (161 families):
# Pool 0: 21 families, Pools 1-7: 20 families each
# - Cycle week 1: Alan Judd's, Frank Bohannon's, and Kyle Fairman's families filtered
# - Cycle week 4: Brian McLaughlin's and Larry McDuffee's families filtered
# - Cycle week 5: L.A. Fox's family filtered
# - Cycle week 6: Jerry Wood's family filtered
# - Cycle week 7: Jonathan Loveday's family filtered
#
# Reassignments chosen to maintain 19-21 family balance and avoid repeats:
# Each target verified SAFE (family not in target's adjacent-week pools)
FIXED_REASSIGNMENT_MAP: dict[int, dict[str, str]] = {
    1: {"Alan Judd": "Jerry Wood",               # Alan(19) filtered -> Jerry(20->21) SAFE
        "Frank Bohannon": "Jonathan Loveday",    # Frank(19) filtered -> Jonathan(20->21) SAFE
        "Kyle Fairman": "Brian McLaughlin"},     # Kyle(19) filtered -> Brian(20->21) SAFE
    4: {"Brian McLaughlin": "Larry McDuffee",    # Brian(19) filtered -> Larry(19->20) SAFE
        "Larry McDuffee": "Brian McLaughlin"},   # Larry(19) filtered -> Brian(19->20) SAFE
    5: {"L.A. Fox": "Jonathan Loveday"},         # L.A.(19) filtered -> Jonathan(20->21) SAFE
    6: {"Jerry Wood": "Kyle Fairman"},           # Jerry(19) filtered -> Kyle(20->21) SAFE
    7: {"Jonathan Loveday": "Frank Bohannon"},   # Jonathan(19) filtered -> Frank(20->21) SAFE
}


def assign_families_for_week_v10(week_number: int) -> dict[str, list[str]]:
    """Compute the per-elder family assignments for ``week_number``.

    Behaviour (preserves the V10 contract used by the helper scripts):

    1. Each elder ``i`` is assigned pool ``(i + cycle_position) % 8`` where
       ``cycle_position = (week_number - 1) % 8``.
    2. If an elder's own family is in their assigned pool, it is filtered
       out and re-targeted to another elder via :data:`FIXED_REASSIGNMENT_MAP`.
    3. The reassignment targets are pre-verified to be adjacency-safe (no
       week-to-week repeats for any elder).

    Returns a dict mapping elder name -> list of family strings for the week.
    """
    master_pools = get_master_pools()

    # Calculate position in the 8-week cycle.
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
