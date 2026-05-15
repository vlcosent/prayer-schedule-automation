"""
Calculate optimal reassignments that maintain a balanced family count across
elders. Run this whenever the roster or directory changes to regenerate
``FIXED_REASSIGNMENT_MAP`` in ``prayer_schedule/algorithm.py``.

Also self-checks: the script exits non-zero if the conflict set computed from
the live directory + roster names elders that the current
``FIXED_REASSIGNMENT_MAP`` does not have entries for (drift detection). It
does NOT auto-suggest reassignment targets — those have to balance counts
across the week, which is a human judgement.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prayer_schedule_V10_DESKTOP_FIXED import ELDERS, ELDER_FAMILIES, get_master_pools
from prayer_schedule.algorithm import FIXED_REASSIGNMENT_MAP
from prayer_schedule.config import POOL_COUNT, ROTATION_WEEKS

pools = get_master_pools()

print("POOL SIZES:")
for i, pool in enumerate(pools):
    print(f"Pool {i}: {len(pool)} families")

print("\n\nWEEK-BY-WEEK ANALYSIS:")
print("=" * 100)

# Build the conflict set: cycle_position -> {elder_with_own_family_filtered}
conflicts: dict[int, set[str]] = {}
for cycle_week in range(ROTATION_WEEKS):
    print(f"\nCYCLE WEEK {cycle_week}:")
    print("-" * 100)
    conflicts[cycle_week] = set()

    for elder_idx, elder in enumerate(ELDERS):
        pool_idx = (elder_idx + cycle_week) % POOL_COUNT
        pool_size = len(pools[pool_idx])
        elder_family = ELDER_FAMILIES[elder]

        in_pool = elder_family in pools[pool_idx]
        final_count = pool_size - 1 if in_pool else pool_size

        status = "*" if in_pool else " "
        print(f"{status} {elder:20} gets Pool {pool_idx} ({pool_size} fam) -> {final_count} families")
        if in_pool:
            conflicts[cycle_week].add(elder)


print("\n\nMAP DRIFT CHECK:")
print("=" * 100)
missing: list[tuple[int, str]] = []
spurious: list[tuple[int, str]] = []
for cycle_week, conflict_elders in conflicts.items():
    mapped = set(FIXED_REASSIGNMENT_MAP.get(cycle_week, {}).keys())
    for elder in conflict_elders - mapped:
        missing.append((cycle_week, elder))
    for elder in mapped - conflict_elders:
        spurious.append((cycle_week, elder))

if not missing and not spurious:
    print("MAP IS CURRENT — every conflict has a reassignment entry and no entry is unused.")
    sys.exit(0)

if missing:
    print("MISSING from FIXED_REASSIGNMENT_MAP:")
    for cycle_week, elder in missing:
        print(f"  cycle_position={cycle_week}: {elder!r} (own family lands in their pool)")
if spurious:
    print("UNUSED entries in FIXED_REASSIGNMENT_MAP (no conflict for this elder at this cycle):")
    for cycle_week, elder in spurious:
        print(f"  cycle_position={cycle_week}: {elder!r}")

print("\nMAP NEEDS UPDATE: review the analysis above and pick targets that")
print("keep every elder's weekly family count within FAMILIES_PER_ELDER_MIN..MAX,")
print("then update FIXED_REASSIGNMENT_MAP in prayer_schedule/algorithm.py.")
sys.exit(1)
