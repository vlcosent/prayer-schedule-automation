"""Command-line entry point: orchestrates the daily schedule run."""

from __future__ import annotations

import traceback
from datetime import datetime, timedelta, timezone

from . import config
from .algorithm import (
    assign_families_for_week_v10,
    calculate_continuous_week,
    calculate_week_number,
)
from .config import DESKTOP_DIR
from .elders import get_week_schedule
from .email_service import send_daily_combined_email
from .file_io import archive_previous_schedule, log_activity, update_desktop_files
from .output import generate_schedule_content
from .utils import get_today
from .validation import (
    validate_elder_data,
    validate_email_config,
    validate_reassignment_map,
    verify_email_date,
    verify_schedule,
    verify_today_elder_assignment,
    verify_v10_algorithm,
)


def main() -> bool:
    """Main execution with combined daily email.

    Behaviour:
      * Monday: Regenerate weekly schedule files + send combined email.
      * Tuesday-Sunday: Refresh HTML/text files + send combined email.
      * Every day: exactly 1 email (today's assignment + week overview).
    """
    try:
        today = get_today()
        is_monday = today.weekday() == 0
        day_names = [
            "Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday", "Sunday",
        ]
        today_name = day_names[today.weekday()]

        log_activity(
            f"Starting prayer schedule system ({today_name}) "
            "(VERSION 11 - COMBINED EMAIL)"
        )
        print(f"\n[DATE] Server UTC time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[DATE] Central Time (church local): {today.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[DATE] Today: {today_name}, {today.strftime('%B %d, %Y')}")

        # Startup config validation — fail loudly on any drift before doing work.
        print("\nValidating configuration...")
        elder_ok, elder_issues = validate_elder_data()
        if not elder_ok:
            for issue in elder_issues:
                print(f"   [X] {issue}")
            print("[X] ELDER DATA VALIDATION FAILED — aborting")
            return False
        map_ok, map_issues = validate_reassignment_map()
        if not map_ok:
            for issue in map_issues:
                print(f"   [X] {issue}")
            print("[X] REASSIGNMENT MAP VALIDATION FAILED — aborting")
            return False
        email_ok, email_issues = validate_email_config()
        if not email_ok:
            for issue in email_issues:
                print(f"   [X] {issue}")
            print("[X] EMAIL CONFIG VALIDATION FAILED — aborting")
            return False
        print("[OK] Elder data, reassignment map, and email config are consistent.")

        # First verify the algorithm.
        print("\nRunning algorithm verification...")
        if not verify_v10_algorithm():
            print("\n[X] V10 algorithm verification FAILED!")
            print("Aborting to prevent generating incorrect schedules.")
            return False

        print("\n[OK] Algorithm verification PASSED!")

        # Get current week information - always find this week's Monday.
        days_back = today.weekday()
        monday = today - timedelta(days=days_back)
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

        # Verify the email date is correct before proceeding.
        date_valid, date_msg = verify_email_date(today, monday)
        print(f"\n[DATE CHECK] {date_msg}")
        if not date_valid:
            print("[X] DATE VERIFICATION FAILED - aborting to prevent wrong-date email")
            return False

        week_num = calculate_week_number(monday)
        continuous_week_num = calculate_continuous_week(monday)

        print("\nCrossville Church of Christ - Prayer Schedule Generator")
        print("VERSION 10 - DAILY EMAIL EDITION")
        print("=" * 60)
        print(f"Today: {today_name}, {today.strftime('%B %d, %Y')}")
        print(f"Week {week_num} ({monday.strftime('%B %d')} - {(monday + timedelta(days=6)).strftime('%B %d, %Y')})")
        print(f"Continuous week: {continuous_week_num} (cycle position: {(continuous_week_num - 1) % 8})")
        print(f"\nALL FILES WILL BE SAVED TO: {DESKTOP_DIR}")

        # Generate assignments using the continuous week number to avoid
        # year-boundary discontinuities in the 8-week rotation cycle.
        elder_assignments = assign_families_for_week_v10(continuous_week_num)

        # Verify assignments.
        print("\nVerifying current week assignments...")
        is_valid, issues = verify_schedule(elder_assignments)

        if not is_valid:
            print("\n[X] VALIDATION FAILED:")
            for issue in issues:
                print(f"  - {issue}")
            return False

        print("[OK] All verification checks passed!")

        # Sanity-check that today's scheduled elder(s) actually have families assigned.
        schedule_for_today = get_week_schedule(week_num)
        today_ok, today_msg = verify_today_elder_assignment(
            today, schedule_for_today, elder_assignments
        )
        print(f"[TODAY CHECK] {today_msg}")
        if not today_ok:
            print("[X] TODAY-ELDER VERIFICATION FAILED — aborting to prevent wrong email")
            return False

        # Show family counts.
        print("\nFamily counts:")
        total_families_assigned = 0
        for elder, families in elder_assignments.items():
            print(f"  {elder}: {len(families)} families")
            total_families_assigned += len(families)

        print(f"\nTotal families assigned this week: {total_families_assigned}")
        print(f"Elders with assignments: {len(elder_assignments)}")

        # Show today's assignment.
        schedule = get_week_schedule(week_num)
        todays_elders = schedule.get(today_name, [])
        print(f"\nToday's prayer assignment ({today_name}):")
        for elder in todays_elders:
            families = elder_assignments.get(elder, [])
            print(f"  {elder}: {len(families)} families")

        if is_monday:
            # === MONDAY: Full regeneration ===
            print("\n--- MONDAY: Full schedule regeneration ---")

            # Archive previous week's schedule before generating new one.
            print("\nArchiving previous schedule...")
            archive_previous_schedule()
        else:
            print(f"\n--- {today_name.upper()}: Daily update ---")

        # Generate / refresh content every day (for day highlighting on website).
        html_content, text_content = generate_schedule_content(
            week_num, monday, elder_assignments
        )

        print("\nUpdating current week files...")
        if not update_desktop_files(html_content, text_content):
            print("\n[WARNING] Some files could not be updated")
            return False

        log_activity(
            "Generated Week " + str(week_num) + " schedule (Monday full run)"
            if is_monday
            else "Daily update for " + today_name + ", Week " + str(week_num)
        )

        # === EVERY DAY: Send one combined email ===
        if config.EMAIL_ENABLED:
            print(f"\nSending combined daily email for {today_name}...")
            email_ok = send_daily_combined_email(
                today, week_num, monday, elder_assignments
            )
            if not email_ok:
                print("   [ERROR] Email delivery failed - schedule files were still saved")
                return False
        else:
            print("\nEmail delivery is disabled (set EMAIL_ENABLED=true to send)")

        print(f"\n[OK] {'Schedule generation' if is_monday else 'Daily update'} complete!")
        print(f"All files have been saved to: {DESKTOP_DIR}")

        return True

    except Exception as exc:
        print("\n[CRITICAL ERROR] Unexpected error occurred:")
        print(f"  {exc}")
        traceback.print_exc()
        return False
