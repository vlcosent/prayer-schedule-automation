"""
Calculate optimal reassignments that maintain 18-20 family balance
"""
import sys
sys.path.insert(0, '/home/user/prayer-schedule-automation')

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

# Manually calculate best reassignments
recommendations = {
    0: "Kyle's family (from Pool 5, 19 fam) → Assign to elder with 19 families",
    1: "Frank's family (from Pool 3, 19 fam) → Assign to elder with 19 families\n     Jerry's family (from Pool 4, 19 fam) → Assign to elder with 19 families",
    2: "Brian's family (from Pool 3, 19 fam) → Assign to elder with 19 families\n     Larry's family (from Pool 1, 20 fam) → Assign to elder with 18 families",
    5: "Jonathan's family (from Pool 1, 20 fam) → Assign to elder with 18-19 families",
    7: "Alan's family (from Pool 7, 19 fam) → Assign to elder with 19 families"
}

for week, rec in recommendations.items():
    print(f"\nCycle Week {week}:")
    print(f"  {rec}")
