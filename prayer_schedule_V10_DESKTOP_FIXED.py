"""
Crossville Church of Christ - Prayer Schedule System (VERSION 10 - DAILY EMAIL)
==================================================================================
DESKTOP VERSION - All files saved to desktop
DAILY EMAIL EDITION - Sends daily prayer reminder emails

Features:
- 100% new families every week GUARANTEED
- No elder ever prays for their own family
- DAILY email delivery: each day's elder(s) get a prayer reminder sent to all
- Weekly full schedule email on Mondays
- Website highlights current day of the week at the top
- ASCII only output (no Unicode errors)
- Perfect 8-week rotation cycle
- Flexible family counts (18-20 per elder) to ensure perfect rotation
- Automatic archiving of previous schedules
- ALL FILES SAVED TO DESKTOP (or current directory in CI)

DAILY SCHEDULE:
- Monday: Full schedule regeneration + weekly email + daily email
- Tuesday-Sunday: HTML/text file refresh + daily prayer reminder email
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
10. Fixed total_assignments counter to show total families (155) not elder count (8)
11. Added daily email automation - sends prayer reminder each day
12. Added day-of-week highlighting on website (JavaScript-based)
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
except:
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
RECIPIENT_EMAILS = os.environ.get('RECIPIENT_EMAILS', ','.join([
    'elders@crossvillechurchofchrist.org',
    'carolsparks.cs@gmail.com',
    'frankbo72@gmail.com',           # Frank
    'kfair232@gmail.com',            # Kyle
    'laccafox@gmail.com',            # L.A., Jr.
    'alanhjudd@gmail.com',           # Alan
    'lovedayj@frontiernet.net',      # Jonathan
    'larrymcduffee@gmail.com',       # Larry
    'brianmclaughlin423@gmail.com',  # Brian
    'jbw@benlomand.net',             # Jerry
]))

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

# Church Directory CSV - All 155 families
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
Brock,"Philip & Brooke; Olliver (Ollie)"
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
Evans,Janie
Fairman,"Kyle & Leigh Ann; Wyatt, Audrey"
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
Gugler,Ethel
Haga,David & Patty
Hall,Robin
Harris,Jimmy & Donna
Hassler,Rebecca
Hassler,Steve & Barbara
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
Jenkins,Phil & Miriam
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
Parham,"Tom & Jill; Brantley"
Parsons,Charles
Pernell,Jerry & Tammi
Pierce,Chris & Alex
Potter,Rhonda & David
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
Smith,Hazel
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
Young,Mickey & Pat"""

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
REFERENCE_MONDAY = datetime(2025, 12, 29)

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
    days_diff = (monday_date - REFERENCE_MONDAY).days
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
    # - Pools 0, 1 and 2: 20 families each (155 % 8 = 3, so first 3 pools get extra)
    # - Pools 3-7: 19 families each

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
    # Fixed reassignment mapping based on conflict analysis:
    # - Cycle week 0 (Week 1): Kyle Fairman's family filtered
    # - Cycle week 1 (Week 2): Frank Bohannon's and Jerry Wood's families filtered
    # - Cycle week 2 (Week 3): Brian McLaughlin's and Larry McDuffee's families filtered
    # - Cycle week 5 (Week 6): Jonathan Loveday's family filtered
    # - Cycle week 7 (Week 8): Alan Judd's family filtered
    #
    # Reassignments chosen to maintain 18-20 family balance and avoid repeats:
    # Based on analysis: assign to elders with 19 families (to reach 20) or 18 (to reach 19)
    FIXED_REASSIGNMENT_MAP = {
        0: {"Kyle Fairman": "Jerry Wood"},           # Kyle(18) filtered → Jerry(19→20)
        1: {"Frank Bohannon": "Jonathan Loveday",    # Frank(18) → Jonathan(19→20)
            "Jerry Wood": "Kyle Fairman"},           # Jerry(18) → Kyle(19→20)
        2: {"Brian McLaughlin": "Jerry Wood",        # Brian(18) → Jerry(19→20) NOT Frank (has it in cycle 1)
            "Larry McDuffee": "Brian McLaughlin"},   # Larry(19) → Brian(18→19)
        3: {"L.A. Fox": "Alan Judd"},                # L.A.(19) → Alan(19→20)
        5: {"Jonathan Loveday": "Brian McLaughlin"}, # Jonathan(19) → Brian(19→20)
        7: {"Alan Judd": "Jonathan Loveday"}         # Alan(18) → Jonathan(19→20)
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
        # We accept 18-20 families as valid
        if 18 <= actual <= 20:
            print(f"   [OK] {elder}: {actual} families")
        else:
            print(f"   [X] {elder}: {actual} families (should be 18-20)")
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
        print(f"   [OK] All 155 families are included in rotation")
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
<html>
<head>
    <title>Prayer Schedule - Week {week_number}</title>
    <meta charset="UTF-8">
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
                <strong>Note:</strong> Each elder has 18-20 families to ensure complete rotation coverage.
                Monday always has two elders assigned for prayer.
                Daily emails are sent each morning to remind everyone of today's prayer assignment.
            </div>

            <h2>This Week's Prayer Schedule</h2>
            <table class="schedule-table">
                <tr>
                    <th>Day</th>
                    <th>Date</th>
                    <th>Elder(s) Assigned</th>
                </tr>
    """
    
    # Plain text version
    text = f"""============================================================
PRAYER SCHEDULE - WEEK {week_number}
{date_range}
Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}
============================================================

CROSSVILLE CHURCH OF CHRIST
Elder Prayer Schedule - Week {week_number}
{date_range}
============================================================

This Week's Prayer Schedule:
Note: Monday always has two elders assigned for prayer.

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
    
    text += f"\n{'='*60}\nPRAYER LISTS FOR THIS WEEK:\n{'='*60}\n"
    
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
            text += f"{len(prayer_group)} families to pray for:\n\n"
            
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
    text += "Note: Each elder has 18-20 families for complete rotation.\n"
    text += "="*60 + "\n\n"
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

def send_email_schedule(week_num, monday, text_content):
    """
    Send the full weekly prayer schedule via email (used on Mondays).
    Uses Gmail SMTP with credentials from environment variables.
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

        # Calculate date range
        end_date = monday + timedelta(days=6)
        date_range = f"{monday.strftime('%b %d')}-{end_date.strftime('%d, %Y')}"

        # Create email message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f"Weekly Prayer Schedule - Week {week_num} ({date_range})"

        # Email body - include the full text schedule
        email_body = f"""Greetings,

Please find below the prayer schedule for Week {week_num} ({date_range}).

{text_content}

This schedule was automatically generated by the Prayer Schedule System.

Blessings,
Crossville Church of Christ Elder Ministry
"""

        msg.attach(MIMEText(email_body, 'plain'))

        # Connect to Gmail SMTP server
        print(f"   [EMAIL] Connecting to {SMTP_SERVER}:{SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure the connection

        # Login
        print(f"   [EMAIL] Logging in as {SENDER_EMAIL}...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        # Send email
        print(f"   [EMAIL] Sending to: {', '.join(recipients)}")
        server.send_message(msg)
        server.quit()

        print(f"   [OK] Weekly email sent successfully to {len(recipients)} recipient(s)")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"   [ERROR] Email authentication failed: {e}")
        print(f"   [INFO] Please verify SENDER_PASSWORD is a valid Gmail App Password")
        return False
    except smtplib.SMTPException as e:
        print(f"   [ERROR] SMTP error occurred: {e}")
        return False
    except Exception as e:
        print(f"   [ERROR] Failed to send email: {e}")
        traceback.print_exc()
        return False


def send_daily_email(today, week_num, monday, elder_assignments):
    """
    Send a daily prayer reminder email highlighting today's elder(s) and their families.
    This is sent every day (including Monday) so each elder gets a reminder on their day.
    """
    if not EMAIL_ENABLED:
        print("   [INFO] Email is disabled (EMAIL_ENABLED not set to 'true')")
        return False

    if not SENDER_PASSWORD:
        print("   [WARNING] Email password not configured (SENDER_PASSWORD not set)")
        print("   [INFO] Skipping daily email delivery")
        return False

    try:
        # Parse recipient emails
        recipients = [email.strip() for email in RECIPIENT_EMAILS.split(',') if email.strip()]

        if not recipients:
            print("   [WARNING] No recipient emails configured")
            return False

        # Determine today's day name
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today_name = day_names[today.weekday()]

        # Get today's schedule
        schedule = get_week_schedule(week_num)
        todays_elders = schedule.get(today_name, [])

        if not todays_elders:
            print(f"   [INFO] No elders assigned for {today_name} - skipping daily email")
            return False

        # Build the daily prayer details
        elder_details = ""
        for elder in todays_elders:
            families = elder_assignments.get(elder, [])
            elder_details += f"\n{elder} - {len(families)} families to pray for:\n"
            elder_details += "-" * 50 + "\n"
            for i, family in enumerate(families, 1):
                elder_details += f"  {i:3}. {family}\n"
            elder_details += "\n"

        elder_names = " & ".join(todays_elders)
        today_formatted = today.strftime('%A, %B %d, %Y')

        # Calculate date range for subject
        end_date = monday + timedelta(days=6)
        date_range = f"{monday.strftime('%b %d')}-{end_date.strftime('%d, %Y')}"

        # Create email message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f"Daily Prayer Reminder - {today_name}: {elder_names} (Week {week_num})"

        # Email body - today's prayer focus
        email_body = f"""Greetings,

TODAY'S PRAYER FOCUS - {today_formatted}
{'=' * 60}

Today is {today_name} of Week {week_num} ({date_range}).

Elder(s) assigned to pray today: {elder_names}

{elder_details}
Please keep these families in your prayers today.

{'=' * 60}
This daily reminder was automatically generated by the Prayer Schedule System.

Blessings,
Crossville Church of Christ Elder Ministry
"""

        msg.attach(MIMEText(email_body, 'plain'))

        # Connect to Gmail SMTP server
        print(f"   [EMAIL] Connecting to {SMTP_SERVER}:{SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure the connection

        # Login
        print(f"   [EMAIL] Logging in as {SENDER_EMAIL}...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        # Send email
        print(f"   [EMAIL] Sending daily reminder to: {', '.join(recipients)}")
        server.send_message(msg)
        server.quit()

        print(f"   [OK] Daily email sent successfully for {today_name} to {len(recipients)} recipient(s)")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"   [ERROR] Email authentication failed: {e}")
        print(f"   [INFO] Please verify SENDER_PASSWORD is a valid Gmail App Password")
        return False
    except smtplib.SMTPException as e:
        print(f"   [ERROR] SMTP error occurred: {e}")
        return False
    except Exception as e:
        print(f"   [ERROR] Failed to send daily email: {e}")
        traceback.print_exc()
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
    except:
        pass  # Silent fail for logging

def verify_schedule(assignments):
    """Verify the schedule meets requirements"""
    issues = []
    
    # Check family counts (18-20 is acceptable)
    for elder, families in assignments.items():
        actual = len(families)
        if actual < 18 or actual > 20:
            issues.append(f"{elder}: {actual} families (should be 18-20)")
    
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
    """Main execution with daily email support.

    Behavior:
    - Monday: Regenerate weekly schedule files, send full weekly email, send daily email
    - Tuesday-Sunday: Send daily prayer reminder email only (no file regeneration)
    - Always: Regenerate HTML with current-day highlighting data
    """
    try:
        today = datetime.now()
        is_monday = today.weekday() == 0
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today_name = day_names[today.weekday()]

        log_activity(f"Starting prayer schedule system ({today_name}) (VERSION 10 - DAILY EMAIL)")

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

            # Generate content
            html_content, text_content = generate_schedule_content(week_num, monday, elder_assignments)

            # Update desktop files (Current Week files)
            print("\nUpdating current week files...")
            if not update_desktop_files(html_content, text_content):
                print("\n[WARNING] Some files could not be updated")
                return False

            # Send full weekly email
            print("\nSending weekly schedule email...")
            send_email_schedule(week_num, monday, text_content)

            log_activity(f"Generated Week {week_num} schedule successfully (Monday full run)")
        else:
            # === TUESDAY-SUNDAY: Regenerate HTML only (for day highlighting) ===
            print(f"\n--- {today_name.upper()}: Daily update ---")

            # Regenerate HTML so the static file is up-to-date
            html_content, text_content = generate_schedule_content(week_num, monday, elder_assignments)

            print("\nUpdating current week files...")
            if not update_desktop_files(html_content, text_content):
                print("\n[WARNING] Some files could not be updated")
                return False

            log_activity(f"Daily update for {today_name}, Week {week_num}")

        # === EVERY DAY: Send daily prayer reminder email ===
        print(f"\nSending daily prayer reminder for {today_name}...")
        send_daily_email(today, week_num, monday, elder_assignments)

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
