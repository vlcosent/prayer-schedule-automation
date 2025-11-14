"""
Analyze which elder families are in which pools to understand the coverage issue
"""

import sys
sys.path.insert(0, '/home/user/prayer-schedule-automation')

from prayer_schedule_V10_DESKTOP_FIXED import (
    ELDERS, ELDER_FAMILIES, get_master_pools, assign_families_for_week_v10
)

# Get master pools
pools = get_master_pools()

print("ELDER FAMILY DISTRIBUTION ACROSS POOLS")
print("="*80)

# Check which pool contains each elder's family
for elder in ELDERS:
    elder_family = ELDER_FAMILIES[elder]

    # Find which pool contains this family
    found_in_pool = None
    for pool_idx, pool in enumerate(pools):
        if elder_family in pool:
            found_in_pool = pool_idx
            break

    print(f"\n{elder}:")
    print(f"  Family: {elder_family}")
    print(f"  Located in: Pool {found_in_pool}")

print("\n\nELDER ROTATION PATTERN (Who gets which pool each week)")
print("="*80)
print(f"{'Week':<8}", end='')
for elder in ELDERS:
    print(f"{elder[:15]:<17}", end='')
print()
print("-"*150)

for week in range(1, 9):  # 8-week cycle
    cycle_position = (week - 1) % 8
    print(f"Week {week:<3}", end='')

    for elder_idx, elder in enumerate(ELDERS):
        pool_idx = (elder_idx + cycle_position) % 8
        print(f"Pool {pool_idx:<14}", end='')
    print()

print("\n\nPROBLEM ANALYSIS: When does each elder get their OWN family's pool?")
print("="*80)

for elder_idx, elder in enumerate(ELDERS):
    elder_family = ELDER_FAMILIES[elder]

    # Find which pool contains this family
    family_pool = None
    for pool_idx, pool in enumerate(pools):
        if elder_family in pool:
            family_pool = pool_idx
            break

    # Find which week this elder gets that pool
    problem_weeks = []
    for week in range(1, 9):
        cycle_position = (week - 1) % 8
        assigned_pool = (elder_idx + cycle_position) % 8

        if assigned_pool == family_pool:
            problem_weeks.append(week)

    if problem_weeks:
        print(f"\n❌ {elder}:")
        print(f"   Family in Pool {family_pool}")
        print(f"   Gets Pool {family_pool} in week(s): {problem_weeks}")
        print(f"   → Family will be REMOVED and NOT covered in these weeks!")
    else:
        print(f"\n✅ {elder}: Never gets their own family's pool")

print("\n\nWEEKLY COVERAGE GAPS:")
print("="*80)

for week in range(46, 54):  # One complete cycle
    assignments = assign_families_for_week_v10(week)

    # Collect all assigned families
    all_assigned = set()
    for families in assignments.values():
        all_assigned.update(families)

    # Check which elder families are missing
    missing = []
    for elder in ELDERS:
        elder_family = ELDER_FAMILIES[elder]
        if elder_family not in all_assigned:
            missing.append(f"{elder}'s family")

    if missing:
        print(f"Week {week}: MISSING {len(missing)}: {', '.join(missing)}")
    else:
        print(f"Week {week}: ✅ All families covered")
