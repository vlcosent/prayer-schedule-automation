"""
COMPREHENSIVE PRAYER SCHEDULE VERIFICATION
==========================================
This script performs deep verification to ensure:
1. Every church member is prayed for EVERY week
2. Each family is assigned to exactly ONE elder per week
3. No elder prays for their own family
4. No families are ever missed or duplicated
5. Proper rotation over 8-week cycle
"""

import csv
from io import StringIO
from datetime import datetime, timedelta

# Import configuration from main script
import sys
sys.path.insert(0, '/home/user/prayer-schedule-automation')
from prayer_schedule_V10_DESKTOP_FIXED import (
    ELDERS, ELDER_FAMILIES, parse_directory,
    assign_families_for_week_v10, get_master_pools,
    calculate_continuous_week, REFERENCE_MONDAY
)

def verify_complete_coverage():
    """
    CRITICAL VERIFICATION: Ensure every family is prayed for every week
    """
    print("="*80)
    print("COMPREHENSIVE PRAYER SCHEDULE VERIFICATION")
    print("="*80)

    all_families = set(parse_directory())
    total_families = len(all_families)
    elder_family_list = set(ELDER_FAMILIES.values())

    print(f"\n📊 CHURCH STATISTICS:")
    print(f"   Total families in directory: {total_families}")
    print(f"   Number of elders: {len(ELDERS)}")
    print(f"   Elder families: {len(elder_family_list)}")

    # Verify master pools
    print(f"\n🔍 MASTER POOL DISTRIBUTION:")
    master_pools = get_master_pools()
    total_in_pools = 0
    for i, pool in enumerate(master_pools):
        print(f"   Pool {i}: {len(pool)} families")
        total_in_pools += len(pool)

    if total_in_pools != total_families:
        print(f"   ❌ ERROR: Pools contain {total_in_pools} but should contain {total_families}")
        return False
    else:
        print(f"   ✅ All {total_families} families distributed across pools")

    # Test multiple weeks
    print(f"\n🔬 WEEKLY COVERAGE VERIFICATION (Testing 10 weeks):")
    print("-"*80)

    all_tests_passed = True

    for week_num in range(46, 56):  # Test 10 consecutive weeks
        print(f"\n📅 WEEK {week_num}:")

        assignments = assign_families_for_week_v10(week_num)

        # Collect all families assigned this week
        families_assigned_this_week = set()
        families_per_elder = {}

        for elder, families in assignments.items():
            families_per_elder[elder] = set(families)
            families_assigned_this_week.update(families)

        # Check 1: Are all non-elder families covered?
        # (Elder families should be covered by OTHER elders, not themselves)
        missing_families = all_families - families_assigned_this_week
        extra_families = families_assigned_this_week - all_families

        # Check if missing families are only elder families that filtered themselves
        expected_missing = set()
        for elder in ELDERS:
            elder_own_family = ELDER_FAMILIES[elder]
            # Check if this elder's family is in their assigned families
            if elder_own_family not in families_per_elder[elder]:
                # This elder doesn't have their own family (expected)
                # But WHO has this elder's family?
                family_covered_by = None
                for other_elder, other_families in families_per_elder.items():
                    if elder_own_family in other_families:
                        family_covered_by = other_elder
                        break

                if family_covered_by is None:
                    # This elder's family is not covered by anyone!
                    print(f"   ❌ CRITICAL: {elder}'s family not covered by any elder!")
                    print(f"      Family: {elder_own_family}")
                    all_tests_passed = False

        # Check 2: Total coverage
        coverage_percent = (len(families_assigned_this_week) / total_families) * 100

        if missing_families:
            print(f"   ⚠️  Missing families: {len(missing_families)}")
            for fam in list(missing_families)[:5]:  # Show first 5
                print(f"      - {fam}")
            if len(missing_families) > 5:
                print(f"      ... and {len(missing_families) - 5} more")
            all_tests_passed = False

        if extra_families:
            print(f"   ❌ Extra families (not in directory): {len(extra_families)}")
            all_tests_passed = False

        # Check 3: No duplicates (each family assigned to exactly one elder)
        family_assignment_count = {}
        for elder, families in families_per_elder.items():
            for family in families:
                if family not in family_assignment_count:
                    family_assignment_count[family] = []
                family_assignment_count[family].append(elder)

        duplicates_found = False
        for family, assigned_elders in family_assignment_count.items():
            if len(assigned_elders) > 1:
                print(f"   ❌ DUPLICATE: '{family}' assigned to {len(assigned_elders)} elders:")
                for elder in assigned_elders:
                    print(f"      - {elder}")
                duplicates_found = True
                all_tests_passed = False

        # Check 4: Elder own family check
        elder_has_own_family = False
        for elder, families in families_per_elder.items():
            elder_own_family = ELDER_FAMILIES[elder]
            if elder_own_family in families:
                print(f"   ❌ RULE VIOLATION: {elder} has their own family!")
                print(f"      Family: {elder_own_family}")
                elder_has_own_family = True
                all_tests_passed = False

        # Check 5: Family counts per elder
        print(f"\n   Elder assignments:")
        total_assigned = 0
        for elder, families in families_per_elder.items():
            count = len(families)
            total_assigned += count
            status = "✅" if 18 <= count <= 20 else "❌"
            print(f"      {status} {elder}: {count} families")
            if count < 18 or count > 20:
                all_tests_passed = False

        # Summary for this week
        print(f"\n   📊 Week {week_num} Summary:")
        print(f"      Total families in directory: {total_families}")
        print(f"      Total families assigned: {len(families_assigned_this_week)}")
        print(f"      Total assignments (sum): {total_assigned}")
        print(f"      Coverage: {coverage_percent:.1f}%")

        if not missing_families and not extra_families and not duplicates_found and not elder_has_own_family:
            print(f"      ✅ Week {week_num} PASSED all checks")
        else:
            print(f"      ❌ Week {week_num} FAILED verification")

    # Check 6: 8-week rotation cycle
    print(f"\n\n🔄 8-WEEK CYCLE VERIFICATION:")
    print("-"*80)

    week_start = 46
    cycle_perfect = True

    for elder in ELDERS:
        # Get assignments for week N and week N+8
        week1_families = set(assign_families_for_week_v10(week_start)[elder])
        week9_families = set(assign_families_for_week_v10(week_start + 8)[elder])

        if week1_families == week9_families:
            print(f"   ✅ {elder}: Week {week_start} = Week {week_start+8} (cycle repeats)")
        else:
            print(f"   ❌ {elder}: Cycle doesn't repeat correctly")
            diff1 = week1_families - week9_families
            diff2 = week9_families - week1_families
            if diff1:
                print(f"      In week {week_start} but not {week_start+8}: {len(diff1)} families")
            if diff2:
                print(f"      In week {week_start+8} but not {week_start}: {len(diff2)} families")
            cycle_perfect = False
            all_tests_passed = False

    # Check 7: Verify NO family repeats week-to-week for each elder
    print(f"\n\n🔀 WEEK-TO-WEEK ROTATION VERIFICATION:")
    print("-"*80)

    rotation_perfect = True
    for elder in ELDERS:
        elder_perfect = True
        for week in range(46, 53):  # Check 7 week transitions
            week1_families = set(assign_families_for_week_v10(week)[elder])
            week2_families = set(assign_families_for_week_v10(week + 1)[elder])

            overlap = week1_families & week2_families

            if overlap:
                if elder_perfect:  # Only print elder name once
                    print(f"   ❌ {elder}:")
                print(f"      Week {week} → Week {week+1}: {len(overlap)} repeated families")
                for fam in list(overlap)[:3]:
                    print(f"         - {fam}")
                elder_perfect = False
                rotation_perfect = False

        if elder_perfect:
            print(f"   ✅ {elder}: 100% new families every week")

    if not rotation_perfect:
        all_tests_passed = False

    # FINAL VERDICT
    print(f"\n\n{'='*80}")
    print("FINAL VERIFICATION RESULT:")
    print('='*80)

    if all_tests_passed:
        print("✅ ✅ ✅  ALL TESTS PASSED  ✅ ✅ ✅")
        print("\nEvery church member is prayed for every week.")
        print("All prayer rules are followed perfectly.")
        print("No edge cases detected.")
        return True
    else:
        print("❌ ❌ ❌  VERIFICATION FAILED  ❌ ❌ ❌")
        print("\nCRITICAL ISSUES DETECTED - See details above")
        return False

def verify_year_boundary():
    """
    CRITICAL VERIFICATION: Ensure the 8-week rotation cycle is continuous
    across year boundaries, where ISO week numbers reset from 52/53 to 1.

    This test uses calculate_continuous_week() to simulate multiple year
    transitions and verifies:
    1. Cycle positions advance by exactly 1 each week (no skips)
    2. No duplicate assignments between consecutive weeks
    3. The 8-week cycle completes correctly across year boundaries
    """
    print(f"\n\n{'='*80}")
    print("YEAR-BOUNDARY CONTINUITY VERIFICATION")
    print('='*80)

    all_passed = True

    # Test multiple year boundaries
    year_boundaries = [
        ("2025->2026", datetime(2025, 12, 1)),   # Start 4 weeks before boundary
        ("2026->2027", datetime(2026, 12, 7)),   # 2026 has 53 ISO weeks
        ("2027->2028", datetime(2027, 12, 6)),
        ("2028->2029", datetime(2028, 12, 11)),  # 2028 is a leap year
    ]

    for label, start_monday in year_boundaries:
        print(f"\n--- Testing {label} boundary ---")

        # Generate 12 consecutive weeks of assignments
        prev_cycle_pos = None
        prev_assignments = None

        boundary_ok = True
        for week_offset in range(12):
            monday = start_monday + timedelta(weeks=week_offset)
            continuous_week = calculate_continuous_week(monday)
            iso_year, iso_week, _ = monday.isocalendar()
            cycle_pos = (continuous_week - 1) % 8

            # Check cycle position advances by exactly 1
            if prev_cycle_pos is not None:
                expected = (prev_cycle_pos + 1) % 8
                if cycle_pos != expected:
                    print(f"   FAIL: {monday.strftime('%Y-%m-%d')} ISO W{iso_week}: "
                          f"cycle_pos={cycle_pos}, expected={expected} (discontinuity!)")
                    boundary_ok = False
                    all_passed = False

            # Check no family overlap between consecutive weeks
            assignments = assign_families_for_week_v10(continuous_week)
            if prev_assignments is not None:
                for elder in ELDERS:
                    prev_fams = set(prev_assignments[elder])
                    curr_fams = set(assignments[elder])
                    overlap = prev_fams & curr_fams
                    if overlap:
                        print(f"   FAIL: {elder} has {len(overlap)} overlapping families "
                              f"between weeks at {monday.strftime('%Y-%m-%d')}")
                        boundary_ok = False
                        all_passed = False

            prev_cycle_pos = cycle_pos
            prev_assignments = assignments

        if boundary_ok:
            print(f"   PASS: {label} - continuous rotation, no duplicates")

    # Verify continuous week matches ISO week within 2026
    print(f"\n--- Verifying continuous_week == ISO week within 2026 ---")
    alignment_ok = True
    monday = datetime(2025, 12, 29)  # ISO Week 1 of 2026
    for w in range(53):
        d = monday + timedelta(weeks=w)
        iso_year, iso_week, _ = d.isocalendar()
        cw = calculate_continuous_week(d)
        if iso_year == 2026 and cw != iso_week:
            print(f"   FAIL: {d.strftime('%Y-%m-%d')} ISO W{iso_week} != continuous W{cw}")
            alignment_ok = False
            all_passed = False
    if alignment_ok:
        print(f"   PASS: All 2026 weeks: continuous_week == ISO week")

    print(f"\n{'='*80}")
    if all_passed:
        print("YEAR-BOUNDARY VERIFICATION: ALL PASSED")
    else:
        print("YEAR-BOUNDARY VERIFICATION: FAILED")
    print('='*80)

    return all_passed


if __name__ == "__main__":
    import os
    os.chdir('/home/user/prayer-schedule-automation')

    success1 = verify_complete_coverage()
    success2 = verify_year_boundary()
    sys.exit(0 if (success1 and success2) else 1)
