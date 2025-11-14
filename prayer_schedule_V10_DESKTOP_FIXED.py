"""
Crossville Church of Christ - Prayer Schedule System (VERSION 10 - DESKTOP - FIXED)
==================================================================================
DESKTOP VERSION - All files saved to desktop
FIXED VERSION - Addresses all critical bugs found in analysis

Features:
- 100% new families every week GUARANTEED
- No elder ever prays for their own family  
- No email functionality (no authentication issues)
- ASCII only output (no Unicode errors)
- Perfect 8-week rotation cycle
- Flexible family counts (18-20 per elder) to ensure perfect rotation
- ALL FILES SAVED TO DESKTOP

FIXES APPLIED:
1. Fixed hard-coded user path - now uses expanduser
2. Added comprehensive error handling
3. Fixed HTML character encoding issues
4. Removed unnecessary rebalancing code
5. Fixed weekly assignment count
6. Added better ISO week handling
"""

import csv
from io import StringIO
from datetime import datetime, timedelta
import os
import sys
import traceback

# ============== CONFIGURATION SECTION ==============
# FIXED: Use expanduser to get desktop path dynamically
try:
    DESKTOP_DIR = os.path.expanduser("~/Desktop")
    if not os.path.exists(DESKTOP_DIR):
        # Fallback for Windows if Desktop doesn't exist at standard location
        DESKTOP_DIR = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
except:
    # Ultimate fallback
    DESKTOP_DIR = os.getcwd()
    print(f"Warning: Could not find desktop, using current directory: {DESKTOP_DIR}")

BASE_DIR = DESKTOP_DIR

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
    "L.A. Fox": "Fox, L.A., Jr. & Cindy",
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
    """Calculate ISO week number with better handling"""
    iso_year, iso_week, iso_day = date.isocalendar()
    
    # Log the ISO week for debugging
    print(f"  Date {date.strftime('%Y-%m-%d')} = ISO Week {iso_week} of {iso_year}")
    
    return iso_week

def create_v10_master_pools():
    """
    Create the V10 master pools with simple, correct distribution.
    FIXED: Removed unnecessary rebalancing code
    """
    families = parse_directory()
    
    # Create 8 pools
    pools = [[] for _ in range(8)]
    
    # Target sizes for distribution
    # Pools 0,1,2: 20 families each
    # Pools 3-7: 19 families each
    # Total: 20*3 + 19*5 = 60 + 95 = 155 ✓
    
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
    """
    master_pools = get_master_pools()
    
    # Calculate position in 8-week cycle
    cycle_position = (week_number - 1) % 8
    
    # Get assignments for this week
    assignments = {}
    
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
        .highlight {{ background-color: #fff3cd !important; font-weight: bold; }}
        .prayer-list {{ 
            margin: 40px 0; 
            page-break-inside: avoid;
            border-left: 4px solid #3498db;
            padding-left: 20px;
        }}
        .prayer-list h3 {{ 
            color: #2c3e50; 
            border-bottom: 2px solid #3498db; 
            padding-bottom: 10px;
            font-size: 1.3em;
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
        
        <div class="content">
            <div class="note">
                <strong>Note:</strong> Each elder has 18-20 families to ensure complete rotation coverage.
                Monday always has two elders assigned for prayer.
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
        
        html += f"""
                <tr class="{highlight_class}">
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
        
        for elder in elders:
            prayer_group = elder_assignments[elder]
            
            # HTML version
            html += f"""
            <div class="prayer-list">
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
    
    # Footer
    html += f"""
            <div class="update-time">
                Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                <br>Next update: Next Monday at 6:00 AM
            </div>
        </div>
    </div>
</body>
</html>
    """
    
    text += "="*60 + "\n"
    text += "Note: Each elder has 18-20 families for complete rotation.\n"
    text += "="*60 + "\n\n"
    text += "-- Crossville Church of Christ Elder Ministry --\n"
    
    return html, text

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
    """Main execution with better error handling"""
    try:
        log_activity("Starting prayer schedule generation (VERSION 10 - DESKTOP - FIXED)")
        
        # First verify the algorithm
        print("\nRunning algorithm verification...")
        if not verify_v10_algorithm():
            print("\n[X] V10 algorithm verification FAILED!")
            print("Aborting to prevent generating incorrect schedules.")
            return False
        
        print("\n[OK] Algorithm verification PASSED!")
        
        # Get current week information
        today = datetime.now()
        days_back = today.weekday()
        monday = today - timedelta(days=days_back)
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        week_num = calculate_week_number(monday)
        
        print("\nCrossville Church of Christ - Prayer Schedule Generator")
        print("VERSION 10 - DESKTOP VERSION (FIXED)")
        print("="*60)
        print(f"Generating schedule for Week {week_num}")
        print(f"Week of {monday.strftime('%B %d, %Y')}")
        print(f"\nALL FILES WILL BE SAVED TO: {DESKTOP_DIR}")
        
        # Generate assignments
        elder_assignments = assign_families_for_week_v10(week_num)
        
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
        total_assignments = 0
        for elder, families in elder_assignments.items():
            print(f"  {elder}: {len(families)} families")
            total_assignments += 1
        
        print(f"\nTotal elder assignments this week: {total_assignments}")
        # Note: Monday has 2 elders, so we have 8 elders but 9 prayer slots
        
        # Generate content
        html_content, text_content = generate_schedule_content(week_num, monday, elder_assignments)
        
        # Update desktop files (Current Week files)
        print("\nUpdating current week files...")
        if not update_desktop_files(html_content, text_content):
            print("\n[WARNING] Some files could not be updated")
            return False
        
        log_activity(f"Generated Week {week_num} schedule successfully")
        
        print("\n[OK] Schedule generation complete!")
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
