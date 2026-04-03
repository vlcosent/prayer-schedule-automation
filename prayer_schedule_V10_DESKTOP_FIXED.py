"""
Crossville Church of Christ - Prayer Schedule System (VERSION 11 - COMBINED EMAIL)
==================================================================================
DESKTOP VERSION - All files saved to desktop
COMBINED EMAIL EDITION - One email per day with today's assignment + week overview

Features:
- 100% new families every week GUARANTEED
- No elder ever prays for their own family
- ONE combined email per day: today's prayer assignment + weekly schedule overview
- Website highlights current day of the week at the top
- ASCII only output (no Unicode errors)
- Perfect 8-week rotation cycle
- Flexible family counts (19-21 per elder) to ensure perfect rotation
- Automatic archiving of previous schedules
- ALL FILES SAVED TO DESKTOP (or current directory in CI)

DAILY SCHEDULE:
- Monday: Full schedule regeneration + single combined email
- Tuesday-Sunday: HTML/text file refresh + single combined email
- GitHub Actions runs every day at 1:00 PM UTC (8:00 AM CDT)

FIXES APPLIED:
1. Fixed hard-coded user path - now uses expanduser
2. Added comprehensive error handling
3. Fixed HTML character encoding issues
4. Removed unnecessary rebalancing code
5. Fixed weekly assignment count
6. Added better ISO week handling
7. Added secure email delivery functionality
8. Added automatic schedule archiving
9. Fixed year-boundary rotation bug: ISO week numbers reset from 52/53 to 1
   at year boundaries, causing cycle_position to jump and duplicate family
   assignments. Now uses continuous week counting from a fixed reference date.
10. Fixed total_assignments counter to show total families (161) not elder count (8)
11. Added daily email automation - sends prayer reminder each day
12. Added day-of-week highlighting on website (JavaScript-based)
13. Combined weekly + daily emails into a single daily email (1 email/day)
"""

import csv
from io import StringIO
from datetime import datetime, timedelta
import os
import sys
import traceback
import shutil
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate

# ============== CONFIGURATION SECTION ==============
# FIXED: Use expanduser to get desktop path dynamically
# AUTO-DETECT: Works in both desktop and CI (GitHub Actions) environments
try:
    # Check if running in GitHub Actions or CI environment
    is_ci = os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'

    if is_ci:
        # In CI environment, use current directory
        DESKTOP_DIR = os.getcwd()
        print(f"CI environment detected. Using current directory: {DESKTOP_DIR}")
    else:
        # In desktop environment, use Desktop folder
        DESKTOP_DIR = os.path.expanduser("~/Desktop")
        if not os.path.exists(DESKTOP_DIR):
            # Fallback for Windows if Desktop doesn't exist at standard location
            DESKTOP_DIR = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
            if not os.path.exists(DESKTOP_DIR):
                # If still no desktop found, use current directory
                DESKTOP_DIR = os.getcwd()
                print(f"Warning: Could not find desktop, using current directory: {DESKTOP_DIR}")
except Exception:
    # Ultimate fallback
    DESKTOP_DIR = os.getcwd()
    print(f"Warning: Could not find desktop, using current directory: {DESKTOP_DIR}")

BASE_DIR = DESKTOP_DIR

# ============== EMAIL CONFIGURATION ==============
# Email settings - credentials loaded from environment variables
EMAIL_ENABLED = os.environ.get('EMAIL_ENABLED', 'false').lower() == 'true'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'churchprayerlistelders@gmail.com')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', '')
RECIPIENT_EMAILS = os.environ.get('RECIPIENT_EMAILS', '')


# US Central Time via IANA timezone database (stdlib since Python 3.9).
# Automatically handles CST (UTC-6) and CDT (UTC-5) transitions.
from zoneinfo import ZoneInfo
CENTRAL_TZ = ZoneInfo("America/Chicago")


def get_today():
    """Get current date/time in US Central Time.

    Uses the IANA timezone database so DST transitions are always correct,
    even if US rules change in the future (via tzdata updates).
    """
    return datetime.now(CENTRAL_TZ)


def verify_email_date(today, monday):
    """Verify the email date is correct before sending.

    Returns (is_valid, message) tuple. Checks:
    1. Today falls within the Monday-Sunday week range
    2. Today's day name matches the expected day
    """
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_name = day_names[today.weekday()]
    sunday = monday + timedelta(days=6)

    # Check today falls within the week
    today_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
    if today_date < monday or today_date > sunday:
        return False, (f"DATE MISMATCH: Today {today.strftime('%Y-%m-%d')} ({today_name}) "
                       f"is outside week range {monday.strftime('%Y-%m-%d')} to {sunday.strftime('%Y-%m-%d')}")

    # Check the day index is consistent
    expected_offset = (today_date - monday).days
    if expected_offset != today.weekday():
        return False, (f"DAY MISMATCH: {today_name} offset={expected_offset} "
                       f"but weekday()={today.weekday()}")

    return True, (f"DATE VERIFIED: {today_name}, {today.strftime('%B %d, %Y')} "
                  f"is day {expected_offset + 1}/7 of week {monday.strftime('%b %d')}-{sunday.strftime('%b %d, %Y')}")


# Church Elders (8 total)
ELDERS = [
    "Alan Judd",
    "Brian McLaughlin", 
    "Frank Bohannon",
    "Jerry Wood",
    "Jonathan Loveday",
    "Kyle Fairman",
    "L.A. Fox",
    "Larry McDuffee"
]

# Elder families
ELDER_FAMILIES = {
    "Alan Judd": "Judd, Alan & Amy; Anderson, Adrian, Adam",
    "Brian McLaughlin": "McLaughlin, Brian & Heather",
    "Frank Bohannon": "Bohannon, Frank & Paula",
    "Jerry Wood": "Wood, Jerry & Rebecca",
    "Jonathan Loveday": "Loveday, Jonathan & Sylvia; Jabin",
    "Kyle Fairman": "Fairman, Kyle & Leigh Ann; Wyatt, Audrey",
    "L.A. Fox": "Fox, L.A. & Cindy",
    "Larry McDuffee": "McDuffee, Larry & Linda"
}

# Church Directory CSV - All 161 families
DIRECTORY_CSV = """Last Name,First Names
Allred,"Patric & Courtney; Brady Hoyt, Allie Grace"
Austin,Shawn
Badger,Marvin & Kathy
Baisley,Teresa
Barnwell,"Michele; Taylor"
Beach,Bruce
Beaty,Ethel
Beaty,Gene & Norma
Bell,Jim & Beth
Benedict,Larry & Peggy
Blyly,"Garrett & Taylor; Ellison, Bellamy"
Bohannon,Frank & Paula
Bow,Katherine
Brady,Donald & Donna
Brewer,Sandra
Brock,Lilly
Brock,"Philip & Brooke; Olliver (Ollie), Thea"
Brown,Connie
Brown,Earl
Brown,Eddie
Brown,"Harold & Arlene"
Brown,Kim
Brown,Wilma
Burchenal,Robert
Burnette,Howard & Kathy
Bush,"John & Sunshine; Serena, Sydney"
Cairns,Rod & Starla
Clark,"Sandra; Silas, Sydney"
Cole,Aprel
Comer,Gail
Cosentini,"Victor & Paige; Cooper"
Crabtree,Tommy & Cathy
Davis,Gail
Davis,J.C. & Lana
Delmonte,Steve & Jenny
Dodson,Bendell
Edwards,Emily
Evans,Janie
Fairman,"Kyle & Leigh Ann; Wyatt, Audrey"
Fawehinmi,Ethan
Folk,Roberta
Fowler,Rick & Sue
Fox,Jean
Fox,L.A. & Cindy
Fox,Richard
Fulford,Sharon
Graham,Pat
Griffies,David & Mary
Griffin,Donna & Wendell
Griffin,"Dylan & Julia; Eli, Noah, Isaiah"
Haga,David & Patty
Hall,Robin
Harris,Jimmy & Donna
Hassler,Rebecca
Hassler,Steve & Barbara
Hawn,Daniel
Haymon,Vernon
Haynes,Cameron & Evette
Hedgecoth,Myra
Hennessee,"Dale & Charlotte; Kadrienne, Kambry"
Hollars,Kathy
Hoover,Buddy & Jane
Houston,"Jeanene & Steve; Stevie"
Houston,Ruby
Hudson,Brett
Hughes,Dona
Hunt,Jeff & Sonia
Hunt,Wendell & Betty
Isaacson,Michael & Terry
Iverson,Don & Cathy
Jackson,Gene & Thelda
Jackson,Robert & Tracy
Jenkins,Miriam
Judd,"Alan & Amy; Anderson, Adrian, Adam"
Keck,"Jim & Andrea; Conner, Emily"
Kerley,Marvin & Rachel
Kimbro,Sue
Lane,Patsy
Lau,"Gary & Hannah; David, Maren, Major"
Law,Stephen Charles
Lipe,David & Linda
Loveday,Coye
Loveday,"Doug & Wendy; Amy"
Loveday,"Jonathan & Sylvia; Jabin"
Madden,Cassey
Marshall,Brenda
Martin,"David & Elissa; Reid, Landyn, Avery"
Martin,Jaton
Maxwell,Sue
Maynard,Betty
McCormick,Michael & Ginger
McDuffee,Larry & Linda
McGhee,Jason & Sara
McLaughlin,Brian & Heather
Meadows,Ted & Elaine
Mitchell,Jeanette
Mize,Aileen
Mize,Al & Elaine
Napier,Natalie
O'Dell,Betty & Bill
O'Guin,Linda
Parham,"Johnny & Charity; Eli"
Parham,Jordan
Parham,"Tom & Jill; Brantley"
Parsons,Charles
Pernell,Jerry & Tammi
Pierce,Chris & Alex
Potter,Rhonda & David
Pritt,Judy
Pritt,"Scott & Kellee"
Randolph,Clyde & Betty
Rector,Mary
Rector,"Troy; Kadence"
Redwine,Chris & Dana
Reed,Ima Jeanne
Reed,"Nathan & Sara; Ridley, Beau, Tate"
Rives,Marla
Roberts,"Jackson & Kayla; Jensen"
Roberts,"Jared & Shavonna; Dylan, Lola, Evan"
Roberts,Mark & Lynn
Roberts,"Matt & Jody; Tony, Ethan, Sheridan"
Rose,Lisa
Rothery,Ginny
Savage,"Brandon & Jenny; Clara, Charlotte"
Saylors,John & Linda
Sears,"Jake & Baylee; Summit, Jett"
Seiber,"Seth & Madison; Kayson, Kendall"
Selby,"Brian; Gavin"
Simmons,Bruce & Louise
Slate,Ray & Martha
Smith,Joe Lee
Smith,Roger & Dianna
Smith,Scott & Juanita
Sparks,Carol
Sparks,Jerry & Judy
Stevens,Kyle & Laura Li
Stover,Lewis & Judy
Swafford,"Russell & Christiana; Jeremiah, Lilly, Tempest"
Thomas,Elon & Betty
Thompson,"Christopher & Brittany; Nautica"
Trotter,Linda
Vaden,David & Sheila
Vaughn,Dennis & Diane
Walker,Barbara
Warner,Jean
Weathers,"Barry & Nancy"
Webb,Richard & Sylvia
Wells,Martha
White,Doris
Whittenburg,Dan & Johnnie
Wiese,Allena (A- lynn-a)
Wilson,Ray
Wood,"Chase & Abby; Lakelyn, Landry"
Wood,Jerry & Rebecca
Wootton,Rebecca
Wyatt,"Jason & Rachel; Mason"
Wyatt,"Stephanie; Sue Ann"
Wyatt,Sarah
Young,Donna & David
Young,Mickey & Pat
Young,Scott"""

def parse_directory():
    """Parse the CSV directory"""
    all_families = []
    csv_reader = csv.DictReader(StringIO(DIRECTORY_CSV))
    for row in csv_reader:
        family_name = f"{row['Last Name']}, {row['First Names']}"
        all_families.append(family_name)
    return sorted(all_families)

def get_week_schedule(week_number):
    """Fixed weekly schedule - CORRECTED TO COUNT ASSIGNMENTS NOT ELDERS"""
    return {
        "Monday": ["Alan Judd", "Brian McLaughlin"],  # 2 assignments
        "Tuesday": ["Frank Bohannon"],                 # 1 assignment
        "Wednesday": ["Jerry Wood"],                   # 1 assignment
        "Thursday": ["Jonathan Loveday"],              # 1 assignment
        "Friday": ["Kyle Fairman"],                    # 1 assignment
        "Saturday": ["L.A. Fox"],                      # 1 assignment
        "Sunday": ["Larry McDuffee"]                   # 1 assignment
    }  # Total: 8 assignments (but 9 prayer slots since Monday has 2)

def calculate_week_number(date):
    """Calculate ISO week number for display purposes"""
    iso_year, iso_week, iso_day = date.isocalendar()

    # Log the ISO week for debugging
    print(f"  Date {date.strftime('%Y-%m-%d')} = ISO Week {iso_week} of {iso_year}")

    return iso_week

# Reference Monday for continuous week counting.
# This is the Monday of ISO Week 1 of 2026, chosen so that within 2026,
# continuous week numbers match ISO week numbers exactly. This avoids the
# bug where ISO week numbers reset from 52 (or 53) to 1 at year boundaries,
# which caused cycle_position discontinuities and duplicate family assignments.
REFERENCE_MONDAY = datetime(2025, 12, 29, tzinfo=CENTRAL_TZ)

def calculate_continuous_week(monday_date):
    """Calculate a continuous week number that never resets at year boundaries.

    ISO week numbers reset from 52/53 to 1 at the start of each ISO year,
    which causes the 8-week rotation cycle_position to jump (e.g., from 3 to 0
    instead of advancing to 4). This function returns a monotonically increasing
    week number based on a fixed reference date, ensuring the cycle always
    advances by exactly 1 each week.

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

def create_v10_master_pools():
    """
    Create the V10 master pools with simple, correct distribution.
    FIXED: Removed unnecessary rebalancing code
    """
    families = parse_directory()

    # Create 8 pools
    pools = [[] for _ in range(8)]

    # Distribute all families round-robin style
    # This naturally achieves the target sizes!
    for i, family in enumerate(families):
        pool_idx = i % 8
        pools[pool_idx].append(family)

    # FIXED: Removed unnecessary rebalancing code
    # The round-robin distribution already achieves:
    # - Pool 0: 21 families (161 % 8 = 1, so first pool gets extra)
    # - Pools 1-7: 20 families each

    # Sort each pool for consistency
    for pool in pools:
        pool.sort()

    return pools

# Global storage
MASTER_POOLS = None

def get_master_pools():
    """Get or create master pools"""
    global MASTER_POOLS
    if MASTER_POOLS is None:
        MASTER_POOLS = create_v10_master_pools()
    return MASTER_POOLS

def assign_families_for_week_v10(week_number):
    """
    Get family assignments for a specific week using V10 algorithm.
    This ensures no elder ever gets their own family through filtering.
    FIXED: Filtered families are redistributed using a deterministic strategy
    that maximizes separation to avoid week-to-week repeats.
    """
    master_pools = get_master_pools()

    # Calculate position in 8-week cycle
    cycle_position = (week_number - 1) % 8

    # First collect filtered families
    filtered_families_data = []  # [(family, owner_elder, owner_idx)]
    for elder_idx, elder in enumerate(ELDERS):
        pool_idx = (elder_idx + cycle_position) % 8
        elder_own_family = ELDER_FAMILIES.get(elder)

        if elder_own_family in master_pools[pool_idx]:
            # This elder's family is in their pool, needs reassignment
            filtered_families_data.append((elder_own_family, elder, elder_idx))

    # Get assignments for this week
    assignments = {}

    # First pass: Assign pools and filter out own families
    for elder_idx, elder in enumerate(ELDERS):
        # Calculate which pool this elder gets this week
        pool_idx = (elder_idx + cycle_position) % 8

        # Get the pool and filter out elder's own family
        pool_families = master_pools[pool_idx].copy()
        elder_own_family = ELDER_FAMILIES.get(elder)

        # Remove elder's own family if it's in the pool
        if elder_own_family in pool_families:
            pool_families.remove(elder_own_family)

        assignments[elder] = pool_families

    # Second pass: Redistribute filtered families using FIXED reassignment table
    # This ensures consistency and prevents week-to-week repeats
    #
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
    FIXED_REASSIGNMENT_MAP = {
        1: {"Alan Judd": "Jerry Wood",               # Alan(19) filtered -> Jerry(20->21) SAFE
            "Frank Bohannon": "Jonathan Loveday",    # Frank(19) filtered -> Jonathan(20->21) SAFE
            "Kyle Fairman": "Brian McLaughlin"},     # Kyle(19) filtered -> Brian(20->21) SAFE
        4: {"Brian McLaughlin": "Larry McDuffee",    # Brian(19) filtered -> Larry(19->20) SAFE
            "Larry McDuffee": "Brian McLaughlin"},   # Larry(19) filtered -> Brian(19->20) SAFE
        5: {"L.A. Fox": "Jonathan Loveday"},         # L.A.(19) filtered -> Jonathan(20->21) SAFE
        6: {"Jerry Wood": "Kyle Fairman"},           # Jerry(19) filtered -> Kyle(20->21) SAFE
        7: {"Jonathan Loveday": "Frank Bohannon"},   # Jonathan(19) filtered -> Frank(20->21) SAFE
    }

    reassignment_map = FIXED_REASSIGNMENT_MAP.get(cycle_position, {})

    for elder_family, owner_elder, owner_idx in filtered_families_data:
        # Use the fixed reassignment map
        best_elder = reassignment_map.get(owner_elder)

        # Fallback if not in map (shouldn't happen with correct map)
        if not best_elder:
            best_elder = ELDERS[(owner_idx + 4) % len(ELDERS)]

        # Assign the filtered family to the designated elder
        assignments[best_elder].append(elder_family)

    return assignments

def verify_v10_algorithm():
    """Thoroughly verify the V10 algorithm"""
    print("\nVERIFYING V10 ALGORITHM")
    print("=" * 60)
    
    # Test 16 weeks
    all_perfect = True
    
    # Track histories
    elder_histories = {elder: [] for elder in ELDERS}
    
    # Generate 16 weeks of assignments
    for week in range(32, 48):
        assignments = assign_families_for_week_v10(week)
        for elder, families in assignments.items():
            elder_histories[elder].append(set(families))
    
    # Check 1: Family counts
    print("\n1. FAMILY COUNT VERIFICATION:")
    week_assignments = assign_families_for_week_v10(32)
    for elder, families in week_assignments.items():
        actual = len(families)
        # We accept 19-21 families as valid
        if 19 <= actual <= 21:
            print(f"   [OK] {elder}: {actual} families")
        else:
            print(f"   [X] {elder}: {actual} families (should be 19-21)")
            all_perfect = False
    
    # Check 2: Elder own family
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
    
    # Check 3: Week-to-week rotation
    print("\n3. WEEK-TO-WEEK ROTATION CHECK:")
    week_perfect = True
    for elder in ELDERS:
        elder_perfect = True
        for i in range(1, len(elder_histories[elder])):
            prev_week = elder_histories[elder][i-1]
            curr_week = elder_histories[elder][i]
            
            overlap = prev_week & curr_week
            
            if overlap:
                if elder_perfect:  # Only print elder name once
                    print(f"   [X] {elder}:")
                print(f"       Week {32+i}: {len(overlap)} repeats")
                elder_perfect = False
                week_perfect = False
        
        if elder_perfect:
            print(f"   [OK] {elder}: Perfect rotation - 100% new families every week")
    
    if not week_perfect:
        all_perfect = False
    
    # Check 4: 8-week cycle
    print("\n4. EIGHT-WEEK CYCLE CHECK:")
    for elder in ELDERS:
        # Check if weeks 0-7 match weeks 8-15
        match = True
        for i in range(8):
            if elder_histories[elder][i] != elder_histories[elder][i+8]:
                match = False
                break
        
        if match:
            print(f"   [OK] {elder}: 8-week cycle repeats correctly")
        else:
            print(f"   [X] {elder}: 8-week cycle doesn't match")
            all_perfect = False
    
    # Check 5: All families covered
    print("\n5. FAMILY COVERAGE CHECK:")
    all_families_used = set()
    for week in range(8):  # Check one complete cycle
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

def generate_schedule_content(week_number, start_date, elder_assignments):
    """Generate schedule content (HTML and text) - FIXED ENCODING"""
    
    schedule = get_week_schedule(week_number)
    end_date = start_date + timedelta(days=6)
    date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
    
    # HTML version for desktop - Professional style with FIXED ENCODING
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>Prayer Schedule - Week {week_number}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="3600">
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: #2c3e50;
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ margin: 0 0 10px 0; font-size: 2.5em; }}
        .header h2 {{ margin: 0 0 10px 0; font-size: 1.8em; }}
        .header h3 {{ margin: 0; font-size: 1.2em; opacity: 0.9; }}
        .content {{ padding: 30px; }}
        /* Day-of-week navigation bar */
        .day-nav {{
            display: flex;
            justify-content: center;
            gap: 4px;
            padding: 15px 20px;
            background: #1a252f;
            flex-wrap: wrap;
        }}
        .day-nav .day-pill {{
            padding: 10px 18px;
            border-radius: 25px;
            font-size: 0.95em;
            font-weight: 600;
            color: #8899a6;
            background: transparent;
            border: 2px solid transparent;
            transition: all 0.3s ease;
            cursor: default;
            text-align: center;
            min-width: 80px;
        }}
        .day-nav .day-pill.today {{
            background: #e67e22;
            color: white;
            border-color: #e67e22;
            box-shadow: 0 2px 12px rgba(230, 126, 34, 0.4);
            transform: scale(1.08);
        }}
        .day-nav .day-pill.past {{
            color: #5a6a7a;
            border-color: #2c3e50;
        }}
        .day-nav .day-pill.future {{
            color: #8899a6;
            border-color: #2c3e50;
        }}
        .day-nav .day-pill .day-label {{
            display: block;
            font-size: 0.85em;
            opacity: 0.7;
        }}
        .day-nav .day-pill.today .day-label {{
            opacity: 1;
        }}
        /* Today's prayer focus banner */
        .today-banner {{
            background: linear-gradient(135deg, #e67e22, #d35400);
            color: white;
            padding: 25px 30px;
            text-align: center;
            display: none;
        }}
        .today-banner h2 {{
            margin: 0 0 8px 0;
            font-size: 1.5em;
        }}
        .today-banner .today-elder {{
            font-size: 1.3em;
            font-weight: bold;
            margin: 5px 0;
        }}
        .today-banner .today-count {{
            font-size: 0.95em;
            opacity: 0.9;
        }}
        .schedule-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .schedule-table th, .schedule-table td {{
            border: 1px solid #ddd;
            padding: 15px;
            text-align: left;
        }}
        .schedule-table th {{
            background: #3498db;
            color: white;
            font-size: 1.1em;
        }}
        .schedule-table tr:nth-child(even) {{ background-color: #f8f9fa; }}
        .schedule-table tr:hover {{ background-color: #e8f4f8; }}
        .schedule-table tr.today-row {{
            background-color: #fef3e2 !important;
            border-left: 4px solid #e67e22;
        }}
        .schedule-table tr.today-row td {{
            font-weight: bold;
            color: #d35400;
        }}
        .highlight {{ background-color: #fff3cd !important; font-weight: bold; }}
        .prayer-list {{
            margin: 40px 0;
            page-break-inside: avoid;
            border-left: 4px solid #3498db;
            padding-left: 20px;
        }}
        .prayer-list.today-prayer-list {{
            border-left-color: #e67e22;
            background: #fef9f3;
            padding: 20px;
            border-radius: 0 8px 8px 0;
        }}
        .prayer-list h3 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            font-size: 1.3em;
        }}
        .prayer-list.today-prayer-list h3 {{
            color: #d35400;
            border-bottom-color: #e67e22;
        }}
        .family-list {{
            columns: 2;
            column-gap: 40px;
            list-style-type: none;
            padding: 0;
        }}
        .family-list li {{
            margin: 8px 0;
            padding: 5px;
            border-radius: 5px;
            transition: background-color 0.3s;
        }}
        .family-list li:hover {{
            background-color: #e8f4f8;
        }}
        .family-list li:before {{
            content: "\\2022";  /* FIXED: Using proper CSS escape for bullet */
            color: #3498db;
            font-weight: bold;
            margin-right: 8px;
        }}
        .today-prayer-list .family-list li:before {{
            color: #e67e22;
        }}
        .update-time {{
            text-align: center;
            color: #7f8c8d;
            margin-top: 20px;
            font-style: italic;
        }}
        .note {{
            background-color: #e8f4fd;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 20px 0;
        }}
        @media print {{
            body {{ background: white; }}
            .container {{ box-shadow: none; }}
            .day-nav {{ display: none; }}
            .today-banner {{ display: none !important; }}
        }}
        @media (max-width: 600px) {{
            .day-nav .day-pill {{
                padding: 8px 10px;
                min-width: 40px;
                font-size: 0.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Crossville Church of Christ</h1>
            <h2>Elder Prayer Schedule - Week {week_number}</h2>
            <h3>{date_range}</h3>
        </div>

        <!-- Day-of-week navigation bar: highlights current day -->
        <div class="day-nav" id="dayNav">
    """

    # Generate day pills with data attributes for JS highlighting
    current_date_for_nav = start_date
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        elders_for_day = schedule[day]
        elder_names_for_nav = " & ".join(elders_for_day)
        date_str = current_date_for_nav.strftime('%Y-%m-%d')
        html += f"""        <div class="day-pill" data-date="{date_str}" data-day="{day}">
                {day[:3]}
                <span class="day-label">{current_date_for_nav.strftime('%b %d')}</span>
            </div>
    """
        current_date_for_nav += timedelta(days=1)

    html += f"""    </div>

        <!-- Today's prayer focus banner (shown dynamically via JS) -->
        <div class="today-banner" id="todayBanner">
            <h2>Today's Prayer Focus</h2>
            <div class="today-elder" id="todayElder"></div>
            <div class="today-count" id="todayCount"></div>
        </div>

        <div class="content">
            <div class="note">
                <strong>Note:</strong> Each elder has 19-21 families to ensure complete rotation coverage.
                Monday always has two elders assigned for prayer.
                Daily emails are sent each morning to remind everyone of today's prayer assignment.
            </div>

            <h2>This Week's Prayer Schedule</h2>
            <table class="schedule-table">
                <tr>
                    <th scope="col">Day</th>
                    <th scope="col">Date</th>
                    <th scope="col">Elder(s) Assigned</th>
                </tr>
    """
    
    # Plain text version
    text = f"""============================================================
CROSSVILLE CHURCH OF CHRIST
Week {week_number}: {date_range}
============================================================

Note: Monday always has two elders assigned.

"""
    
    # Add daily schedule
    current_date = start_date
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        elders = schedule[day]
        elder_names = " & ".join(elders)
        highlight_class = "highlight" if len(elders) > 1 else ""
        date_attr = current_date.strftime('%Y-%m-%d')

        html += f"""
                <tr class="{highlight_class}" data-date="{date_attr}" data-day="{day}">
                    <td><strong>{day}</strong></td>
                    <td>{current_date.strftime('%B %d')}</td>
                    <td>{elder_names}</td>
                </tr>
        """

        text += f"{day}, {current_date.strftime('%B %d')}: {elder_names}\n"
        current_date += timedelta(days=1)
    
    html += """
            </table>
            
            <h2>Prayer Lists for This Week</h2>
    """
    
    text += f"\n{'='*60}\nPRAYER LISTS\n{'='*60}\n"
    
    # Add prayer lists
    current_date = start_date

    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        elders = schedule[day]
        date_attr = current_date.strftime('%Y-%m-%d')

        for elder in elders:
            prayer_group = elder_assignments[elder]

            # HTML version
            html += f"""
            <div class="prayer-list" data-date="{date_attr}" data-day="{day}" data-elder="{elder}" data-count="{len(prayer_group)}">
                <h3>{elder} - {day}, {current_date.strftime('%B %d')}</h3>
                <p><em>{len(prayer_group)} families to pray for:</em></p>
                <ul class="family-list">
            """

            for family in prayer_group:
                # Escape HTML special characters
                family_escaped = family.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html += f"            <li>{family_escaped}</li>\n"

            html += """            </ul>
            </div>
            """
            
            # Text version
            text += f"\n{elder} - {day}, {current_date.strftime('%B %d')}\n"
            text += f"{'-'*50}\n"
            text += f"{len(prayer_group)} families:\n\n"
            
            for i, family in enumerate(prayer_group, 1):
                text += f"{i:3}. {family}\n"
            
            text += "\n"
        
        current_date += timedelta(days=1)
    
    # Footer with JavaScript for dynamic day highlighting
    html += f"""
            <div class="update-time">
                Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                <br>Daily emails sent every morning. Schedule regenerated each Monday.
            </div>
        </div>
    </div>

    <script>
    (function() {{
        // Get today's date in YYYY-MM-DD format (local timezone)
        var now = new Date();
        var yyyy = now.getFullYear();
        var mm = String(now.getMonth() + 1).padStart(2, '0');
        var dd = String(now.getDate()).padStart(2, '0');
        var todayStr = yyyy + '-' + mm + '-' + dd;
        var todayDayIdx = now.getDay(); // 0=Sun, 1=Mon, ...

        // Highlight the day pill
        var pills = document.querySelectorAll('.day-pill');
        var foundToday = false;
        pills.forEach(function(pill) {{
            var pillDate = pill.getAttribute('data-date');
            if (pillDate === todayStr) {{
                pill.classList.add('today');
                foundToday = true;
            }} else if (pillDate < todayStr) {{
                pill.classList.add('past');
            }} else {{
                pill.classList.add('future');
            }}
        }});

        // Highlight today's row in the schedule table
        var rows = document.querySelectorAll('.schedule-table tr[data-date]');
        rows.forEach(function(row) {{
            if (row.getAttribute('data-date') === todayStr) {{
                row.classList.add('today-row');
            }}
        }});

        // Highlight today's prayer list sections and show the banner
        var prayerLists = document.querySelectorAll('.prayer-list[data-date]');
        var todayElders = [];
        var todayFamilyCount = 0;
        prayerLists.forEach(function(pl) {{
            if (pl.getAttribute('data-date') === todayStr) {{
                pl.classList.add('today-prayer-list');
                todayElders.push(pl.getAttribute('data-elder'));
                todayFamilyCount += parseInt(pl.getAttribute('data-count') || '0');
            }}
        }});

        // Show the today banner if we found today in the schedule
        if (todayElders.length > 0) {{
            var banner = document.getElementById('todayBanner');
            var elderEl = document.getElementById('todayElder');
            var countEl = document.getElementById('todayCount');
            if (banner && elderEl && countEl) {{
                elderEl.textContent = todayElders.join(' & ');
                countEl.textContent = todayFamilyCount + ' families being prayed for today';
                banner.style.display = 'block';
            }}
        }}
    }})();
    </script>
</body>
</html>
    """
    
    text += "="*60 + "\n"
    text += "-- Crossville Church of Christ Elder Ministry --\n"
    
    return html, text

def archive_previous_schedule():
    """
    Archive previous week's txt file before generating new one.
    Moves the file to an 'archive' subdirectory with date and week number.
    """
    current_txt = os.path.join(DESKTOP_DIR, "Prayer_Schedule_Current_Week.txt")

    if os.path.exists(current_txt):
        try:
            # Create archive directory if it doesn't exist
            archive_dir = os.path.join(DESKTOP_DIR, "archive")
            os.makedirs(archive_dir, exist_ok=True)

            # Use current timestamp for archive filename
            timestamp = datetime.now().strftime('%Y-%m-%d')

            # Try to extract week number from the existing file
            week_num = None
            try:
                with open(current_txt, 'r', encoding='utf-8') as f:
                    content = f.read(300)  # Read first 300 chars
                    # Look for "WEEK XX" pattern
                    match = re.search(r'WEEK (\d+)', content, re.IGNORECASE)
                    if match:
                        week_num = match.group(1)
            except Exception as e:
                print(f"   [INFO] Could not extract week number from file: {e}")

            # Build archive filename
            if week_num:
                archive_name = f"Prayer_Schedule_{timestamp}_Week{week_num}.txt"
            else:
                archive_name = f"Prayer_Schedule_{timestamp}.txt"

            archive_path = os.path.join(archive_dir, archive_name)

            # Move file to archive (use copy + remove for better error handling)
            shutil.copy2(current_txt, archive_path)
            os.remove(current_txt)

            print(f"   [ARCHIVED] Previous schedule moved to: archive/{archive_name}")
            return True

        except Exception as e:
            print(f"   [WARNING] Could not archive previous schedule: {e}")
            print(f"   [INFO] Continuing with schedule generation...")
            return False
    else:
        print(f"   [INFO] No previous schedule to archive (first run or file doesn't exist)")
        return False

def _email_styles():
    """Shared inline CSS styles for HTML emails (email-client compatible).

    Visual design mirrors the website (GitHub Pages) layout:
      - Header: #2c3e50 (dark navy) with church name, schedule title, date range
      - Day nav bar: #1a252f (darker navy) with day pill buttons
      - Today accent: #e67e22 (warm orange) for today's banner and highlights
      - Table headers: #3498db (blue) matching website schedule table
      - Text: #333333 (near-black) on white/#f8f9fa backgrounds

    Email compatibility notes:
      - All styles are inline (no <style> block) for Gmail/Outlook/Apple Mail
      - No CSS opacity (Outlook ignores it) - uses explicit color values instead
      - No box-shadow (Outlook ignores it) - uses borders for depth
      - Day pills use inline-block (widely supported) with table fallback structure
      - border-radius degrades gracefully to square corners in older Outlook
    """
    return {
        'body': 'margin:0;padding:0;background-color:#f5f5f5;font-family:Segoe UI,Arial,Helvetica,sans-serif;',
        'wrapper': 'width:100%;background-color:#f5f5f5;padding:30px 0;',
        'container': 'max-width:620px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;border:1px solid #d0d4d9;',
        'header': 'background:#2c3e50;color:#ffffff;padding:28px 30px 22px 30px;text-align:center;',
        'header_h1': 'margin:0 0 8px 0;font-size:26px;font-weight:700;color:#ffffff;letter-spacing:0.3px;',
        'header_h2': 'margin:0 0 6px 0;font-size:19px;font-weight:600;color:#ffffff;',
        'header_sub': 'margin:0;font-size:14px;font-weight:700;color:#b0bec5;',
        'day_nav': 'background:#1a252f;padding:14px 8px;text-align:center;font-size:0;',
        'day_pill': 'display:inline-block;padding:8px 6px;border-radius:20px;font-size:12px;font-weight:600;color:#8899a6;border:2px solid #2c3e50;text-align:center;width:60px;margin:2px;vertical-align:top;',
        'day_pill_today': 'display:inline-block;padding:8px 6px;border-radius:20px;font-size:12px;font-weight:700;color:#ffffff;background-color:#e67e22;border:2px solid #e67e22;text-align:center;width:60px;margin:2px;vertical-align:top;',
        'day_pill_past': 'display:inline-block;padding:8px 6px;border-radius:20px;font-size:12px;font-weight:600;color:#5a6a7a;border:2px solid #2c3e50;text-align:center;width:60px;margin:2px;vertical-align:top;',
        'day_pill_label': 'display:block;font-size:10px;color:#a0adb8;margin-top:2px;',
        'day_pill_label_today': 'display:block;font-size:10px;color:#ffffff;margin-top:2px;',
        'day_pill_label_past': 'display:block;font-size:10px;color:#6d7d8a;margin-top:2px;',
        'today_banner': 'background-color:#e67e22;padding:22px 30px;text-align:center;',
        'today_banner_h2': 'margin:0 0 6px 0;font-size:18px;font-weight:700;color:#ffffff;',
        'today_elder': 'margin:4px 0;font-size:20px;font-weight:700;color:#ffffff;',
        'today_count': 'margin:4px 0 0 0;font-size:13px;color:#fde8d0;',
        'content': 'padding:24px 30px;color:#333333;font-size:15px;line-height:1.7;',
        'section_label': 'font-size:12px;font-weight:700;color:#555555;text-transform:uppercase;letter-spacing:0.6px;margin:20px 0 10px 0;',
        'table': 'width:100%;border-collapse:collapse;margin:10px 0;border:1px solid #ddd;',
        'th': 'background:#3498db;color:#ffffff;padding:10px 12px;text-align:left;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.3px;',
        'td': 'padding:10px 12px;border-bottom:1px solid #e8eaed;font-size:14px;color:#333333;',
        'td_alt': 'padding:10px 12px;border-bottom:1px solid #e8eaed;font-size:14px;color:#333333;background:#f8f9fa;',
        'td_today': 'padding:10px 12px;border-bottom:1px solid #e8eaed;font-size:14px;color:#d35400;font-weight:700;background:#fef3e2;border-left:4px solid #e67e22;',
        'td_today_inner': 'padding:10px 12px;border-bottom:1px solid #e8eaed;font-size:14px;color:#d35400;font-weight:700;background:#fef3e2;',
        'elder_block': 'margin:12px 0;border-left:4px solid #3498db;padding:12px 16px;background:#f8f9fa;',
        'elder_block_today': 'margin:12px 0;border-left:4px solid #e67e22;padding:14px 18px;background:#fef9f3;',
        'elder_name': 'font-size:15px;font-weight:700;color:#2c3e50;margin:0 0 2px 0;',
        'elder_count': 'font-size:13px;color:#777777;margin:0 0 8px 0;font-style:italic;',
        'family_item': 'padding:3px 0;font-size:14px;color:#444444;',
        'divider': 'height:1px;background:#e0e3e7;margin:20px 0;',
        'footer': 'padding:18px 30px;text-align:center;background:#f7f8f9;border-top:1px solid #e0e3e7;',
        'footer_link': 'display:inline-block;background:#2c3e50;color:#ffffff;text-decoration:none;padding:10px 24px;border-radius:4px;font-size:13px;font-weight:600;',
        'footer_text': 'margin:10px 0 0 0;font-size:12px;color:#999999;',
    }


def _build_combined_email_html(today, today_name, week_num, monday, schedule, elder_assignments):
    """Build a single combined HTML email for the day.

    Layout mirrors the website (GitHub Pages) design:
      1. Header: Church name (large), "Elder Prayer Schedule - Week X", date range
      2. Day navigation bar: Pill buttons for each day, today highlighted orange
      3. Today's Prayer List banner: Orange bar with elder name and family count
      4. Today's families: Elder block(s) with numbered family lists
      5. Week schedule table: All 7 days, today's row highlighted with orange accent
      6. On Mondays only: Full prayer lists for every elder that week
      7. Footer: Link to view full schedule online
    """
    s = _email_styles()
    is_monday = today.weekday() == 0

    todays_elders = schedule.get(today_name, [])
    elder_names_display = " &amp; ".join(todays_elders)

    end_date = monday + timedelta(days=6)
    date_range = f"{monday.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

    # --- Calculate total families being prayed for today ---
    today_family_count = 0
    for elder in todays_elders:
        today_family_count += len(elder_assignments.get(elder, []))

    # --- Day navigation pills (matches website day-nav bar) ---
    day_pills = ""
    current_date = monday
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        is_today_pill = (day == today_name)
        is_past = (current_date < today and not is_today_pill)

        if is_today_pill:
            pill_style = s['day_pill_today']
            label_style = s['day_pill_label_today']
        elif is_past:
            pill_style = s['day_pill_past']
            label_style = s['day_pill_label_past']
        else:
            pill_style = s['day_pill']
            label_style = s['day_pill_label']

        day_pills += f'<div style="{pill_style}">{day[:3]}<span style="{label_style}">{current_date.strftime("%b %d")}</span></div>\n'
        current_date += timedelta(days=1)

    # --- Today's prayer list sections ---
    today_prayer_sections = ""
    for elder in todays_elders:
        families = elder_assignments.get(elder, [])
        family_list = ""
        for j, family in enumerate(families, 1):
            family_escaped = family.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            family_list += f'<div style="{s["family_item"]}">{j}. {family_escaped}</div>\n'

        today_prayer_sections += f"""
        <div style="{s['elder_block_today']}">
            <p style="{s['elder_name']}">{elder}</p>
            <p style="{s['elder_count']}">{len(families)} families</p>
            {family_list}
        </div>"""

    # --- Week schedule table ---
    table_rows = ""
    current_date = monday
    for i, day in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
        elders = schedule[day]
        elder_names_row = " &amp; ".join(elders)
        date_str = current_date.strftime('%b %d')

        is_today = (day == today_name)
        if is_today:
            # First cell gets left border accent; inner cells get same style without border
            td_first = s['td_today']
            td_rest = s['td_today_inner']
        elif i % 2 == 1:
            td_first = s['td_alt']
            td_rest = s['td_alt']
        else:
            td_first = s['td']
            td_rest = s['td']

        arrow = "&#9654; " if is_today else ""
        table_rows += f"""<tr>
            <td style="{td_first}">{arrow}<strong>{day}</strong></td>
            <td style="{td_rest}">{date_str}</td>
            <td style="{td_rest}">{elder_names_row}</td>
        </tr>"""
        current_date += timedelta(days=1)

    # --- Monday-only: full prayer lists for all elders ---
    full_prayer_lists = ""
    if is_monday:
        full_prayer_lists += f'<p style="{s["section_label"]}">All Prayer Lists This Week</p>'
        current_date = monday
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            elders = schedule[day]
            for elder in elders:
                families = elder_assignments.get(elder, [])
                date_str = current_date.strftime('%b %d')
                family_list = ""
                for j, family in enumerate(families, 1):
                    family_escaped = family.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    family_list += f'<div style="{s["family_item"]}">{j}. {family_escaped}</div>\n'

                full_prayer_lists += f"""
                <div style="{s['elder_block']}">
                    <p style="{s['elder_name']}">{elder} &mdash; {day}, {date_str}</p>
                    <p style="{s['elder_count']}">{len(families)} families</p>
                    {family_list}
                </div>"""
            current_date += timedelta(days=1)
        full_prayer_lists += f'<div style="{s["divider"]}"></div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="{s['body']}">
<div style="{s['wrapper']}">
<div style="{s['container']}">

    <!-- Header -->
    <div style="{s['header']}">
        <h1 style="{s['header_h1']}">Crossville Church of Christ</h1>
        <h2 style="{s['header_h2']}">Daily Prayer Reminder</h2>
        <p style="{s['header_sub']}">{today.strftime('%A, %B %d, %Y')}: {elder_names_display} &mdash; Week {week_num}</p>
    </div>

    <!-- Day Navigation Bar -->
    <div style="{s['day_nav']}">
        {day_pills}
    </div>

    <!-- Today's Prayer List Banner -->
    <div style="{s['today_banner']}">
        <h2 style="{s['today_banner_h2']}">Today's Prayer List</h2>
        <p style="{s['today_elder']}">{elder_names_display}</p>
        <p style="{s['today_count']}">{today_family_count} families being prayed for today</p>
    </div>

    <!-- Today's Families -->
    <div style="{s['content']}">
        <p style="{s['section_label']}">Today's Families</p>
        {today_prayer_sections}

        <div style="{s['divider']}"></div>

        <!-- Week Schedule Table -->
        <p style="{s['section_label']}">This Week at a Glance</p>
        <table style="{s['table']}">
            <tr>
                <th style="{s['th']}">Day</th>
                <th style="{s['th']}">Date</th>
                <th style="{s['th']}">Elder(s)</th>
            </tr>
            {table_rows}
        </table>

        {full_prayer_lists}

        <p style="text-align:center;color:#999999;font-size:13px;margin:16px 0 0 0;">
            Thank you for faithfully praying for our church family.
        </p>
    </div>

    <!-- Footer -->
    <div style="{s['footer']}">
        <a href="https://vlcosent.github.io/prayer-schedule-automation/" style="{s['footer_link']}">View Full Schedule Online</a>
        <p style="{s['footer_text']}">Crossville Church of Christ &bull; Elder Prayer List</p>
    </div>

</div>
</div>
</body>
</html>"""
    return html


def send_daily_combined_email(today, week_num, monday, elder_assignments):
    """
    Send ONE combined daily email with today's prayer assignment + week overview.

    Every day (Mon-Sun) this sends a single email containing:
      - Today's day/date and assigned elder(s) prominently at top
      - Today's family prayer list
      - Week-at-a-glance schedule table (today's row highlighted)
      - On Mondays only: full prayer lists for all elders that week

    Replaces the previous two-email system (weekly + daily).
    """
    if not EMAIL_ENABLED:
        print("   [INFO] Email is disabled (EMAIL_ENABLED not set to 'true')")
        return False

    if not SENDER_PASSWORD:
        print("   [WARNING] Email password not configured (SENDER_PASSWORD not set)")
        print("   [INFO] Skipping email delivery")
        return False

    try:
        # Parse recipient emails
        recipients = [email.strip() for email in RECIPIENT_EMAILS.split(',') if email.strip()]

        if not recipients:
            print("   [WARNING] No recipient emails configured")
            return False

        # Verify the date is correct before composing the email
        date_valid, date_msg = verify_email_date(today, monday)
        print(f"   [DATE CHECK] {date_msg}")
        if not date_valid:
            print("   [X] DATE VERIFICATION FAILED - not sending email")
            return False

        # Determine today's day name
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today_name = day_names[today.weekday()]
        today_formatted = today.strftime('%A, %B %d, %Y')

        # Get today's schedule
        schedule = get_week_schedule(week_num)
        todays_elders = schedule.get(today_name, [])

        if not todays_elders:
            print(f"   [INFO] No elders assigned for {today_name} - skipping email")
            return False

        elder_names = " & ".join(todays_elders)

        # Build plain text version
        end_date = monday + timedelta(days=6)
        date_range = f"{monday.strftime('%b %d')}-{end_date.strftime('%d, %Y')}"

        # Today's elder details (plain text)
        elder_details = ""
        for elder in todays_elders:
            families = elder_assignments.get(elder, [])
            elder_details += f"\n{elder} - {len(families)} families:\n"
            elder_details += "-" * 50 + "\n"
            for i, family in enumerate(families, 1):
                elder_details += f"  {i:3}. {family}\n"
            elder_details += "\n"

        # Week overview (plain text)
        week_overview = "\nThis Week's Schedule:\n"
        week_overview += f"{'Day':<12} {'Date':<10} {'Elder(s)'}\n"
        week_overview += "-" * 50 + "\n"
        current_date = monday
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            elders = schedule[day]
            marker = ">>>" if day == today_name else "   "
            week_overview += f"{marker} {day:<9} {current_date.strftime('%b %d'):<10} {' & '.join(elders)}\n"
            current_date += timedelta(days=1)

        # Create email message
        msg = MIMEMultipart('alternative')
        msg['From'] = SENDER_EMAIL
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f"Daily Prayer Reminder- {today_formatted}: {elder_names}"
        msg['Date'] = formatdate(localtime=True)

        # Plain text fallback
        plain_body = f"""Crossville Church of Christ
Daily Prayer Reminder - {today_formatted}: {elder_names}
Week {week_num} ({date_range})

Today's Elder: {elder_names}
{elder_details}
{week_overview}
Please keep these families in your prayers.

View the full schedule online: https://vlcosent.github.io/prayer-schedule-automation/
"""
        msg.attach(MIMEText(plain_body, 'plain'))

        # HTML version
        html_body = _build_combined_email_html(
            today, today_name, week_num, monday, schedule, elder_assignments
        )
        msg.attach(MIMEText(html_body, 'html'))

        # Connect to Gmail SMTP server
        print(f"   [EMAIL] Connecting to {SMTP_SERVER}:{SMTP_PORT}...")
        print(f"   [EMAIL] Email date: {today_formatted}")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
        server.starttls()

        # Login
        print(f"   [EMAIL] Logging in as {SENDER_EMAIL}...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        # Send email
        print(f"   [EMAIL] Sending to: {', '.join(recipients)}")
        server.send_message(msg)
        server.quit()

        print(f"   [OK] Daily email sent for {today_name}, {today.strftime('%B %d, %Y')} to {len(recipients)} recipient(s)")
        log_activity(f"Email sent for {today_name}, {today.strftime('%B %d, %Y')} to {len(recipients)} recipient(s)")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"   [ERROR] Email authentication failed: {e}")
        print(f"   [INFO] Please verify SENDER_PASSWORD is a valid Gmail App Password")
        log_activity(f"Email FAILED (auth error): {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"   [ERROR] SMTP error occurred: {e}")
        log_activity(f"Email FAILED (SMTP error): {e}")
        return False
    except Exception as e:
        print(f"   [ERROR] Failed to send email: {e}")
        traceback.print_exc()
        log_activity(f"Email FAILED (unexpected error): {e}")
        return False

def update_desktop_files(html_content, text_content):
    """Update files on the desktop with ERROR HANDLING"""
    success = True
    
    # Update desktop files
    desktop_html = os.path.join(DESKTOP_DIR, "Prayer_Schedule_Current_Week.html")
    desktop_text = os.path.join(DESKTOP_DIR, "Prayer_Schedule_Current_Week.txt")
    
    # FIXED: Added comprehensive error handling
    try:
        with open(desktop_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"   [OK] Updated: {desktop_html}")
    except Exception as e:
        print(f"   [ERROR] Failed to write HTML file: {e}")
        success = False
    
    try:
        with open(desktop_text, 'w', encoding='utf-8') as f:
            f.write(text_content)
        print(f"   [OK] Updated: {desktop_text}")
    except Exception as e:
        print(f"   [ERROR] Failed to write text file: {e}")
        success = False
    
    return success

def log_activity(message):
    """Log activity - optional logging to file"""
    # Could be enabled if needed
    try:
        log_file = os.path.join(DESKTOP_DIR, "prayer_schedule_log.txt")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception as e:
        print(f"   [WARNING] Logging failed: {e}", file=sys.stderr)

def verify_schedule(assignments):
    """Verify the schedule meets requirements"""
    issues = []
    
    # Check family counts (19-21 is acceptable)
    for elder, families in assignments.items():
        actual = len(families)
        if actual < 19 or actual > 21:
            issues.append(f"{elder}: {actual} families (should be 19-21)")
    
    # Check for elder own families
    for elder, families in assignments.items():
        elder_family = ELDER_FAMILIES.get(elder)
        if elder_family in families:
            issues.append(f"{elder} has their own family in the list!")
    
    # Check for duplicates
    all_assigned = []
    for families in assignments.values():
        all_assigned.extend(families)
    
    # Count occurrences
    family_counts = {}
    for family in all_assigned:
        family_counts[family] = family_counts.get(family, 0) + 1
    
    # Check for families assigned multiple times
    for family, count in family_counts.items():
        if count > 1:
            issues.append(f"{family} assigned {count} times this week")
    
    return len(issues) == 0, issues

def main():
    """Main execution with combined daily email.

    Behavior:
    - Monday: Regenerate weekly schedule files + send combined email
    - Tuesday-Sunday: Refresh HTML/text files + send combined email
    - Every day: exactly 1 email (today's assignment + week overview)
    """
    try:
        today = get_today()
        is_monday = today.weekday() == 0
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today_name = day_names[today.weekday()]

        log_activity(f"Starting prayer schedule system ({today_name}) (VERSION 11 - COMBINED EMAIL)")
        from datetime import timezone
        print(f"\n[DATE] Server UTC time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[DATE] Central Time (church local): {today.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[DATE] Today: {today_name}, {today.strftime('%B %d, %Y')}")

        # First verify the algorithm
        print("\nRunning algorithm verification...")
        if not verify_v10_algorithm():
            print("\n[X] V10 algorithm verification FAILED!")
            print("Aborting to prevent generating incorrect schedules.")
            return False

        print("\n[OK] Algorithm verification PASSED!")

        # Get current week information - always find this week's Monday
        days_back = today.weekday()
        monday = today - timedelta(days=days_back)
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

        # Verify the email date is correct before proceeding
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

        # Generate assignments using continuous week number to avoid
        # year-boundary discontinuities in the 8-week rotation cycle
        elder_assignments = assign_families_for_week_v10(continuous_week_num)

        # Verify assignments
        print("\nVerifying current week assignments...")
        is_valid, issues = verify_schedule(elder_assignments)

        if not is_valid:
            print("\n[X] VALIDATION FAILED:")
            for issue in issues:
                print(f"  - {issue}")
            return False

        print("[OK] All verification checks passed!")

        # Show family counts
        print("\nFamily counts:")
        total_families_assigned = 0
        for elder, families in elder_assignments.items():
            print(f"  {elder}: {len(families)} families")
            total_families_assigned += len(families)

        print(f"\nTotal families assigned this week: {total_families_assigned}")
        print(f"Elders with assignments: {len(elder_assignments)}")

        # Show today's assignment
        schedule = get_week_schedule(week_num)
        todays_elders = schedule.get(today_name, [])
        print(f"\nToday's prayer assignment ({today_name}):")
        for elder in todays_elders:
            families = elder_assignments.get(elder, [])
            print(f"  {elder}: {len(families)} families")

        if is_monday:
            # === MONDAY: Full regeneration ===
            print("\n--- MONDAY: Full schedule regeneration ---")

            # Archive previous week's schedule before generating new one
            print("\nArchiving previous schedule...")
            archive_previous_schedule()
        else:
            print(f"\n--- {today_name.upper()}: Daily update ---")

        # Generate/refresh content every day (for day highlighting on website)
        html_content, text_content = generate_schedule_content(week_num, monday, elder_assignments)

        print("\nUpdating current week files...")
        if not update_desktop_files(html_content, text_content):
            print("\n[WARNING] Some files could not be updated")
            return False

        log_activity(f"{'Generated Week ' + str(week_num) + ' schedule (Monday full run)' if is_monday else 'Daily update for ' + today_name + ', Week ' + str(week_num)}")

        # === EVERY DAY: Send one combined email ===
        if EMAIL_ENABLED:
            print(f"\nSending combined daily email for {today_name}...")
            email_ok = send_daily_combined_email(today, week_num, monday, elder_assignments)
            if not email_ok:
                print("   [ERROR] Email delivery failed - schedule files were still saved")
                return False
        else:
            print("\nEmail delivery is disabled (set EMAIL_ENABLED=true to send)")

        print(f"\n[OK] {'Schedule generation' if is_monday else 'Daily update'} complete!")
        print(f"All files have been saved to: {DESKTOP_DIR}")

        return True

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Unexpected error occurred:")
        print(f"  {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
