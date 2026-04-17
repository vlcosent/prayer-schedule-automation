"""Validation helpers for elder data, email configuration, and weekly schedules.

This module intentionally collects every "is this still correct?" check so
``cli.main()`` can run them upfront and fail fast before generating files or
sending email.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from . import config
from .algorithm import assign_families_for_week_v10
from .config import (
    DAYS_OF_WEEK,
    ELDER_COUNT,
    FAMILIES_PER_ELDER_MAX,
    FAMILIES_PER_ELDER_MIN,
    POOL_COUNT,
)
from .directory import parse_directory
from .elders import ELDER_DATA, ELDER_FAMILIES, ELDERS


# ----------------------------------------------------------------------
# Email-date and configuration validators
# ----------------------------------------------------------------------

def verify_email_date(today: datetime, monday: datetime) -> tuple[bool, str]:
    """Verify the email date is correct before sending.

    Returns an ``(is_valid, message)`` tuple. Checks:

    1. Today falls within the Monday-Sunday week range.
    2. Today's weekday offset from Monday matches ``datetime.weekday()``.
    """
    today_name = DAYS_OF_WEEK[today.weekday()]
    sunday = monday + timedelta(days=6)

    # Check today falls within the week.
    today_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
    if today_date < monday or today_date > sunday:
        return False, (f"DATE MISMATCH: Today {today.strftime('%Y-%m-%d')} ({today_name}) "
                       f"is outside week range {monday.strftime('%Y-%m-%d')} to {sunday.strftime('%Y-%m-%d')}")

    # Check the day index is consistent.
    expected_offset = (today_date - monday).days
    if expected_offset != today.weekday():
        return False, (f"DAY MISMATCH: {today_name} offset={expected_offset} "
                       f"but weekday()={today.weekday()}")

    return True, (f"DATE VERIFIED: {today_name}, {today.strftime('%B %d, %Y')} "
                  f"is day {expected_offset + 1}/7 of week {monday.strftime('%b %d')}-{sunday.strftime('%b %d, %Y')}")


def validate_email_config() -> tuple[bool, list[str]]:
    """Validate the email configuration read from environment variables.

    Returns ``(is_valid, issues)``. Only *non-fatal* advisory checks live
    here; ``cli.main`` still defers to :func:`verify_email_date` for the
    per-send check. The returned issues list is empty when the configuration
    is consistent and email is enabled.
    """
    issues: list[str] = []

    if not config.EMAIL_ENABLED:
        return True, issues

    if not config.SENDER_EMAIL:
        issues.append("EMAIL_ENABLED=true but SENDER_EMAIL is empty")
    if not config.SENDER_PASSWORD:
        issues.append("EMAIL_ENABLED=true but SENDER_PASSWORD is empty")
    if not config.RECIPIENT_EMAILS:
        issues.append("EMAIL_ENABLED=true but RECIPIENT_EMAILS is empty")

    return (not issues), issues


# ----------------------------------------------------------------------
# Elder-data validators
# ----------------------------------------------------------------------

def validate_elder_data() -> tuple[bool, list[str]]:
    """Validate :data:`~prayer_schedule.elders.ELDER_DATA` for internal consistency.

    Checks:
      * elder count matches :data:`~prayer_schedule.config.ELDER_COUNT`
      * no duplicate elder names
      * each elder has at least one assigned day
      * assigned days are valid members of :data:`DAYS_OF_WEEK`
      * every day in the week is covered by at least one elder
      * elders' own families appear in the directory
    """
    issues: list[str] = []

    if len(ELDER_DATA) != ELDER_COUNT:
        issues.append(
            f"ELDER_DATA has {len(ELDER_DATA)} elders, expected {ELDER_COUNT}"
        )

    seen: set[str] = set()
    for e in ELDER_DATA:
        name = e["name"]
        if name in seen:
            issues.append(f"Duplicate elder name: {name}")
        seen.add(name)

        if not e["days"]:
            issues.append(f"{name}: no assigned days")
        for day in e["days"]:
            if day not in DAYS_OF_WEEK:
                issues.append(f"{name}: invalid day {day!r}")

    # Every day of the week should be covered by at least one elder.
    days_covered: set[str] = set()
    for e in ELDER_DATA:
        for day in e["days"]:
            if day in DAYS_OF_WEEK:
                days_covered.add(day)
    uncovered = [d for d in DAYS_OF_WEEK if d not in days_covered]
    if uncovered:
        issues.append(f"Days with no assigned elder: {uncovered}")

    # Elder families should all appear in the directory.
    try:
        directory = set(parse_directory())
    except ValueError as exc:
        issues.append(f"DIRECTORY_CSV parse error: {exc}")
        directory = set()

    for e in ELDER_DATA:
        if directory and e["family"] not in directory:
            issues.append(
                f"{e['name']}'s family not found in directory: {e['family']!r}"
            )

    return (not issues), issues


def validate_reassignment_map() -> tuple[bool, list[str]]:
    """Validate :data:`FIXED_REASSIGNMENT_MAP` covers every conflict.

    For every cycle position in ``0..POOL_COUNT-1``, any elder whose own
    family lands in their assigned pool must either have an entry in the
    reassignment map (preferred) or be covered by the default fallback.
    This check enforces the *preferred* path.
    """
    # Local import to avoid any cycle in static analyzers.
    from .algorithm import FIXED_REASSIGNMENT_MAP, get_master_pools

    issues: list[str] = []
    pools = get_master_pools()

    for cycle_position in range(POOL_COUNT):
        conflicts: list[str] = []
        for elder_idx, elder in enumerate(ELDERS):
            pool_idx = (elder_idx + cycle_position) % POOL_COUNT
            elder_family = ELDER_FAMILIES.get(elder)
            if elder_family in pools[pool_idx]:
                conflicts.append(elder)

        mapping = FIXED_REASSIGNMENT_MAP.get(cycle_position, {})
        for elder in conflicts:
            if elder not in mapping:
                issues.append(
                    f"Cycle position {cycle_position}: {elder}'s family filtered "
                    "but no entry in FIXED_REASSIGNMENT_MAP"
                )
            else:
                target = mapping[elder]
                if target not in ELDERS:
                    issues.append(
                        f"Cycle position {cycle_position}: {elder} -> "
                        f"{target!r} is not a known elder"
                    )

    return (not issues), issues


# ----------------------------------------------------------------------
# Weekly schedule validators
# ----------------------------------------------------------------------

def verify_schedule(assignments: dict[str, list[str]]) -> tuple[bool, list[str]]:
    """Verify a week of assignments meets the algorithm invariants."""
    issues: list[str] = []

    # Check family counts (19-21 inclusive is acceptable).
    for elder, families in assignments.items():
        actual = len(families)
        if actual < FAMILIES_PER_ELDER_MIN or actual > FAMILIES_PER_ELDER_MAX:
            issues.append(
                f"{elder}: {actual} families "
                f"(should be {FAMILIES_PER_ELDER_MIN}-{FAMILIES_PER_ELDER_MAX})"
            )

    # Check for elders receiving their own families.
    for elder, families in assignments.items():
        elder_family = ELDER_FAMILIES.get(elder)
        if elder_family in families:
            issues.append(f"{elder} has their own family in the list!")

    # Check for duplicate assignments.
    family_counts: dict[str, int] = {}
    for families in assignments.values():
        for family in families:
            family_counts[family] = family_counts.get(family, 0) + 1

    for family, count in family_counts.items():
        if count > 1:
            issues.append(f"{family} assigned {count} times this week")

    return (not issues), issues


def verify_today_elder_assignment(
    today: datetime,
    schedule: dict[str, list[str]],
    assignments: dict[str, list[str]],
) -> tuple[bool, str]:
    """Ensure every elder scheduled for today has a non-empty family list."""
    today_name = DAYS_OF_WEEK[today.weekday()]
    todays_elders = schedule.get(today_name, [])

    if not todays_elders:
        return False, f"No elders are scheduled for {today_name}"

    for elder in todays_elders:
        families = assignments.get(elder)
        if families is None:
            return False, f"{elder} has no entry in the week's assignments"
        if not families:
            return False, f"{elder} has an empty family list for {today_name}"

    return True, (
        f"{today_name}: {len(todays_elders)} elder(s) scheduled "
        f"({', '.join(todays_elders)})"
    )


def verify_v10_algorithm() -> bool:
    """Run the 5 algorithm checks across 16 weeks and print human-readable results.

    Returns ``True`` when every check passes. Output matches the original
    script's formatting verbatim (this is the ``-> ok/fail`` message the CI
    workflow relies on).
    """
    print("\nVERIFYING V10 ALGORITHM")
    print("=" * 60)

    all_perfect = True

    # Track histories.
    elder_histories: dict[str, list[set[str]]] = {elder: [] for elder in ELDERS}

    # Generate 16 weeks of assignments.
    for week in range(32, 48):
        assignments = assign_families_for_week_v10(week)
        for elder, families in assignments.items():
            elder_histories[elder].append(set(families))

    # Check 1: Family counts.
    print("\n1. FAMILY COUNT VERIFICATION:")
    week_assignments = assign_families_for_week_v10(32)
    for elder, families in week_assignments.items():
        actual = len(families)
        # We accept 19-21 families as valid.
        if 19 <= actual <= 21:
            print(f"   [OK] {elder}: {actual} families")
        else:
            print(f"   [X] {elder}: {actual} families (should be 19-21)")
            all_perfect = False

    # Check 2: Elder own family.
    print("\n2. ELDER OWN FAMILY CHECK:")
    for elder in ELDERS:
        elder_family = ELDER_FAMILIES[elder]
        has_own_family = False
        for week_families in elder_histories[elder]:
            if elder_family in week_families:
                has_own_family = True
                break

        if has_own_family:
            print(f"   [X] {elder}: HAS OWN FAMILY")
            all_perfect = False
        else:
            print(f"   [OK] {elder}: Never has own family")

    # Check 3: Week-to-week rotation.
    print("\n3. WEEK-TO-WEEK ROTATION CHECK:")
    week_perfect = True
    for elder in ELDERS:
        elder_perfect = True
        for i in range(1, len(elder_histories[elder])):
            prev_week = elder_histories[elder][i - 1]
            curr_week = elder_histories[elder][i]

            overlap = prev_week & curr_week

            if overlap:
                if elder_perfect:  # Only print elder name once.
                    print(f"   [X] {elder}:")
                print(f"       Week {32 + i}: {len(overlap)} repeats")
                elder_perfect = False
                week_perfect = False

        if elder_perfect:
            print(f"   [OK] {elder}: Perfect rotation - 100% new families every week")

    if not week_perfect:
        all_perfect = False

    # Check 4: 8-week cycle.
    print("\n4. EIGHT-WEEK CYCLE CHECK:")
    for elder in ELDERS:
        match = True
        for i in range(8):
            if elder_histories[elder][i] != elder_histories[elder][i + 8]:
                match = False
                break

        if match:
            print(f"   [OK] {elder}: 8-week cycle repeats correctly")
        else:
            print(f"   [X] {elder}: 8-week cycle doesn't match")
            all_perfect = False

    # Check 5: All families covered.
    print("\n5. FAMILY COVERAGE CHECK:")
    all_families_used: set[str] = set()
    for week in range(8):  # Check one complete cycle.
        assignments = assign_families_for_week_v10(week + 32)
        for families in assignments.values():
            all_families_used.update(families)

    all_families = set(parse_directory())
    missing = all_families - all_families_used
    extra = all_families_used - all_families

    if not missing and not extra:
        print(f"   [OK] All {len(all_families)} families are included in rotation")
    else:
        if missing:
            print(f"   [X] Missing families: {missing}")
        if extra:
            print(f"   [X] Extra families: {extra}")
        all_perfect = False

    return all_perfect
