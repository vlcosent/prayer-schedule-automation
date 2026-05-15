"""
Calculate optimal reassignments that maintain a balanced family count across
elders. Run this whenever the roster or directory changes to regenerate
``FIXED_REASSIGNMENT_MAP`` in ``prayer_schedule/algorithm.py``.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prayer_schedule_V10_DESKTOP_FIXED import ELDERS, ELDER_FAMILIES, get_master_pools
from prayer_schedule.config import POOL_COUNT, ROTATION_WEEKS

pools = get_master_pools()

print("POOL SIZES:")
for i, pool in enumerate(pools):
    print(f"Pool {i}: {len(pool)} families")

print("\n\nWEEK-BY-WEEK ANALYSIS:")
print("=" * 100)

for cycle_week in range(ROTATION_WEEKS):
    print(f"\nCYCLE WEEK {cycle_week}:")
    print("-" * 100)

    for elder_idx, elder in enumerate(ELDERS):
        pool_idx = (elder_idx + cycle_week) % POOL_COUNT
        pool_size = len(pools[pool_idx])
        elder_family = ELDER_FAMILIES[elder]

        in_pool = elder_family in pools[pool_idx]
        final_count = pool_size - 1 if in_pool else pool_size

        status = "*" if in_pool else " "
        print(f"{status} {elder:20} gets Pool {pool_idx} ({pool_size} fam) -> {final_count} families")

print("\n\nNOTE: After computing conflicts, paste the recommended FIXED_REASSIGNMENT_MAP")
print("      into prayer_schedule/algorithm.py, then run `python -m pytest tests/`.")
