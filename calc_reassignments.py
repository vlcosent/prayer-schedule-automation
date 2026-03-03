"""
Calculate optimal reassignments that maintain 18-20 family balance
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prayer_schedule_V10_DESKTOP_FIXED import ELDERS, ELDER_FAMILIES, get_master_pools

pools = get_master_pools()

print("POOL SIZES:")
for i, pool in enumerate(pools):
    print(f"Pool {i}: {len(pool)} families")

print("\n\nWEEK-BY-WEEK ANALYSIS:")
print("="*100)

for cycle_week in range(8):
    print(f"\nCYCLE WEEK {cycle_week}:")
    print("-"*100)

    # Calculate pool assignments
    for elder_idx, elder in enumerate(ELDERS):
        pool_idx = (elder_idx + cycle_week) % 8
        pool_size = len(pools[pool_idx])
        elder_family = ELDER_FAMILIES[elder]

        # Check if elder's family is in their pool
        in_pool = elder_family in pools[pool_idx]

        final_count = pool_size
        if in_pool:
            final_count -= 1  # Filtered out

        status = "🔥" if in_pool else "  "
        print(f"{status} {elder:20} gets Pool {pool_idx} ({pool_size} fam) → {final_count} families")

print("\n\nRECOMMENDED REASSIGNMENTS:")
print("="*100)

# Manually calculate best reassignments (161 families, Pool 0=21, Pools 1-7=20)
recommendations = {
    1: "Alan's family -> Jerry Wood (SAFE)\n     Frank's family -> Jonathan Loveday (SAFE)\n     Kyle's family -> Brian McLaughlin (SAFE)",
    4: "Brian's family -> Larry McDuffee (SAFE)\n     Larry's family -> Brian McLaughlin (SAFE)",
    5: "L.A.'s family -> Jonathan Loveday (SAFE)",
    6: "Jerry's family -> Kyle Fairman (SAFE)",
    7: "Jonathan's family -> Frank Bohannon (SAFE)"
}

for week, rec in recommendations.items():
    print(f"\nCycle Week {week}:")
    print(f"  {rec}")
