# Prayer Schedule Automation

Automated weekly prayer schedule generator for Crossville Church of Christ. This system generates prayer schedules every Monday, rotating 8 elders through 154 church families with a perfect 8-week cycle.

## Features

- **Automatic Weekly Generation**: Runs every Monday at 1:00 PM UTC (8:00 AM CDT / 7:00 AM CST)
- **Email Delivery**: Automatically emails schedule to 10 configured recipients
- **Perfect Rotation**: 100% new families every week - no repeats until the 8-week cycle completes
- **Smart Assignments**: No elder ever prays for their own family
- **Balanced Distribution**: 18-20 families per elder for complete coverage
- **Multiple Formats**: Generates both professional HTML and plain text schedules
- **Dual Environment Support**: Works in both CI/CD (GitHub Actions) and local desktop environments
- **Automatic Archive**: Previous week's schedule automatically archived with date and week number
- **Secure Configuration**: Email credentials stored safely in GitHub Secrets
- **Year-Boundary Safe**: Continuous week counting prevents rotation errors at year transitions

## System Overview

### Schedule Pattern
- **8 Elders** rotate through **154 church families**
- **8-week rotation cycle** ensures complete coverage
- **Monday**: 2 elders assigned (Alan Judd & Brian McLaughlin)
- **Tuesday-Sunday**: 1 elder per day

### Algorithm Verification
The system performs 5 verification checks on every run:
1. **Family Count Check**: Ensures 18-20 families per elder
2. **Elder Own Family Check**: Verifies no elder has their own family
3. **Week-to-Week Rotation**: Confirms 100% new families each week
4. **8-Week Cycle Check**: Validates the rotation repeats correctly
5. **Family Coverage**: Ensures all 154 families are included

### Rotation Algorithm

Families are distributed round-robin from a sorted directory into 8 pools:

| Pools 0-1 | Pools 2-7 |
|-----------|-----------|
| 20 families each | 19 families each |

Each week, every elder is assigned a different pool via:
```
pool_index = (elder_index + cycle_position) % 8
```

The `cycle_position` advances by 1 each week, cycling through 0-7. After 8 weeks, each elder has prayed for every family exactly once.

### Elder-Own-Family Reassignment

When an elder's pool contains their own family, that family is filtered out and reassigned to a different elder to maintain balanced counts (18-20 per elder). This is handled by `FIXED_REASSIGNMENT_MAP` which covers cycle positions [0, 1, 3, 4, 6].

## Year-Boundary Fix (2026-02-06)

### The Bug
Python's `date.isocalendar()` returns ISO week numbers that reset from 52 (or 53) to 1 at the start of each ISO year. The original code used:
```python
cycle_position = (iso_week - 1) % 8
```
This caused a **discontinuity at year boundaries** -- the cycle position would jump (e.g., from 3 to 0 instead of advancing to 4), producing **duplicate family assignments**. Weeks 1-4 of 2026 were confirmed identical to Weeks 49-52 of 2025 in archived production schedules.

### The Fix
A continuous week counter that never resets:
```python
REFERENCE_MONDAY = datetime(2025, 12, 29)  # Monday of ISO Week 1 of 2026

def calculate_continuous_week(monday_date):
    days_diff = (monday_date - REFERENCE_MONDAY).days
    return (days_diff // 7) + 1  # 1-based
```

The reference date was chosen so that within 2026, `continuous_week == ISO week`, ensuring zero disruption to current-year behavior while fixing all future year boundaries.

### Verification
- Tested 520 consecutive weeks (10 years, 9 year boundaries)
- All cycle positions advance by exactly 1 each week
- Zero family overlap between any consecutive weeks
- 2026 ISO week alignment confirmed for all 53 weeks

## Automatic Execution (GitHub Actions)

### Schedule
The workflow automatically runs **every Monday at 1:00 PM UTC**:
- **CST**: 7:00 AM Monday
- **CDT**: 8:00 AM Monday

### Workflow Process
1. GitHub Actions triggers on schedule: `cron: '0 13 * * 1'`
2. Checks out repository code
3. Sets up Python 3.11
4. Executes prayer schedule generator
   - Runs algorithm verification (5 checks)
   - Archives previous week's schedule
   - Generates new schedule for current week
   - Sends email to configured recipients
5. Commits generated files to repository
6. Pushes changes to main branch
7. Uploads artifacts (90-day retention)

### Manual Trigger
You can also run the workflow manually:
1. Go to **GitHub Repository** > **Actions** tab
2. Select **"Weekly Prayer Schedule Generation"**
3. Click **"Run workflow"** button
4. Select branch (usually main)
5. Click **"Run workflow"** to execute

## Generated Files

Each run produces three files:

### 1. Prayer_Schedule_Current_Week.html
- Professional web-viewable schedule
- Responsive design with CSS styling
- Auto-refresh every 60 minutes
- UTF-8 encoding for special characters
- Print-friendly layout

### 2. Prayer_Schedule_Current_Week.txt
- Plain text version for easy printing
- Complete elder assignments
- All family prayer lists
- Family counts per elder

### 3. prayer_schedule_log.txt
- Activity log with timestamps
- Tracks schedule generation events
- Useful for debugging and audit trail

## Archive System

The system automatically archives previous week's schedules before generating new ones, preserving a complete history.

### How It Works
1. **Before Generation**: On each run, the system checks for an existing `Prayer_Schedule_Current_Week.txt` file
2. **Archive Creation**: If found, it moves the file to an `archive/` subdirectory
3. **Smart Naming**: Archives are named with date and week number: `Prayer_Schedule_YYYY-MM-DD_WeekNN.txt`
4. **New Generation**: After archiving, generates the fresh schedule for the current week

### Archive Directory Structure
```
/repository_root/ (or Desktop in local mode)
├── Prayer_Schedule_Current_Week.html (current week)
├── Prayer_Schedule_Current_Week.txt (current week)
├── prayer_schedule_log.txt
└── archive/
    ├── Prayer_Schedule_2025-11-14_Week46.txt
    ├── Prayer_Schedule_2025-11-17_Week46.txt
    ├── Prayer_Schedule_2025-11-24_Week47.txt
    ├── Prayer_Schedule_2025-12-01_Week48.txt
    ├── Prayer_Schedule_2025-12-08_Week49.txt
    ├── Prayer_Schedule_2025-12-15_Week50.txt
    ├── Prayer_Schedule_2025-12-19_Week51.txt
    ├── Prayer_Schedule_2025-12-22_Week51.txt
    ├── Prayer_Schedule_2025-12-29_Week52.txt
    ├── Prayer_Schedule_2026-01-05_Week1.txt
    ├── Prayer_Schedule_2026-01-12_Week2.txt
    ├── Prayer_Schedule_2026-01-19_Week3.txt
    ├── Prayer_Schedule_2026-01-26_Week4.txt
    ├── Prayer_Schedule_2026-02-02_Week5.txt
    ├── Prayer_Schedule_2026-02-06_Week6.txt
    └── Prayer_Schedule_2026-02-09_Week6.txt  (16 files total)
```

### Archive File Naming
- **Format**: `Prayer_Schedule_YYYY-MM-DD_WeekNN.txt`
- **Date**: Monday of the archived week (YYYY-MM-DD)
- **Week Number**: Extracted from file content (e.g., Week46)

### Location
- **CI/GitHub Actions**: Archives stored in `archive/` in repository root
- **Desktop Mode**: Archives stored in `~/Desktop/archive/` or Windows Desktop
- **Auto-Created**: Archive directory is created automatically if it doesn't exist

## Email Configuration

The system automatically emails the prayer schedule to configured recipients each week.

### Email Details
- **Sender**: `churchprayerlistelders@gmail.com`
- **Service**: Gmail SMTP (`smtp.gmail.com:587`, TLS)
- **Format**: Full schedule text included in email body
- **Subject Line**: "Weekly Prayer Schedule - Week XX (Date Range)"

### Recipients (10 Total)
| Recipient | Email | Role |
|-----------|-------|------|
| Elder Group List | `elders@crossvillechurchofchrist.org` | Group distribution list |
| Carol Sparks | `carolsparks.cs@gmail.com` | Church staff |
| Frank Bohannon | `frankbo72@gmail.com` | Elder |
| Kyle Fairman | `kfair232@gmail.com` | Elder |
| L.A. Fox | `laccafox@gmail.com` | Elder |
| Alan Judd | `alanhjudd@gmail.com` | Elder |
| Jonathan Loveday | `lovedayj@frontiernet.net` | Elder |
| Larry McDuffee | `larrymcduffee@gmail.com` | Elder |
| Brian McLaughlin | `brianmclaughlin423@gmail.com` | Elder |
| Jerry Wood | `jbw@benlomand.net` | Elder |

### Setup Requirements

**Important:** Email functionality requires three GitHub Secrets to be configured:

1. **SENDER_EMAIL**: The Gmail address sending the emails
2. **SENDER_PASSWORD**: Gmail App Password (not your regular password)
3. **RECIPIENT_EMAILS**: Comma-separated list of recipient emails

### Quick Setup Guide

1. **Create Gmail App Password**:
   - Enable 2-Factor Authentication on the Gmail account
   - Go to Google Account > Security > 2-Step Verification > App passwords
   - Generate an App Password for "Prayer Schedule Automation"
   - Copy the 16-character password

2. **Configure GitHub Secrets**:
   - Go to repository Settings > Secrets and variables > Actions
   - Add three secrets:
     - `SENDER_EMAIL`: `churchprayerlistelders@gmail.com`
     - `SENDER_PASSWORD`: (the 16-character App Password)
     - `RECIPIENT_EMAILS`: (comma-separated list of all recipient emails)

3. **Test Email Delivery**:
   - Manually trigger the workflow via Actions tab
   - Check workflow logs for email confirmation
   - Verify recipients received the email

### Detailed Setup Instructions

For complete step-by-step instructions, see **[EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md)** which includes:
- Detailed Gmail App Password creation steps
- GitHub Secrets configuration
- Testing procedures
- Troubleshooting common issues
- Security best practices

### Email Sample

```
Subject: Weekly Prayer Schedule - Week 46 (Nov 10-16, 2025)

Greetings,

Please find below the prayer schedule for Week 46 (Nov 10-16, 2025).

[Full text schedule content]

This schedule was automatically generated by the Prayer Schedule System.

Blessings,
Crossville Church of Christ Elder Ministry
```

### Disabling Email (Optional)

To temporarily disable email sending:
1. Edit `.github/workflows/weekly-schedule.yml`
2. Change `EMAIL_ENABLED: 'true'` to `EMAIL_ENABLED: 'false'`
3. Commit and push

### Email Security

- Credentials stored securely in GitHub Secrets (encrypted)
- Uses Gmail App Passwords (not account password)
- Requires 2-Factor Authentication
- Never exposed in code or logs
- SMTP connection secured with TLS

## Files in Repository

### Core Files
| File | Description | Lines |
|------|-------------|-------|
| `prayer_schedule_V10_DESKTOP_FIXED.py` | Main schedule generator | ~1070 |
| `comprehensive_verification.py` | Verification test suite | ~332 |
| `analyze_missing_coverage.py` | Coverage analysis tool | - |
| `calc_reassignments.py` | Reassignment calculator | - |
| `UPDATE_PRAYER_SCHEDULE_FIXED.bat` | Windows batch launcher | - |
| `.github/workflows/weekly-schedule.yml` | GitHub Actions workflow | ~52 |

### Documentation
| File | Description |
|------|-------------|
| `README.md` | This file |
| `EMAIL_SETUP_GUIDE.md` | Email configuration guide |
| `VERIFICATION_COMPLETE.md` | Verification report |
| `IMPROVEMENT_PLAN.md` | Development roadmap |

### Generated Files (Auto-updated)
- **`Prayer_Schedule_Current_Week.html`** - Current week's HTML schedule
- **`Prayer_Schedule_Current_Week.txt`** - Current week's text schedule
- **`prayer_schedule_log.txt`** - Generation activity log
- **`archive/`** - Directory containing 16 historical schedules

### Dependencies
- **Python Version**: 3.11
- **External Packages**: None - all standard library
  - `csv`, `datetime`, `os`, `sys`, `traceback`, `shutil`, `re`, `smtplib`, `email.mime`

## Local Desktop Usage

You can also run the script locally on your computer:

### Windows Users
1. Ensure Python 3.11+ is installed
2. Copy both files to your Desktop:
   - `prayer_schedule_V10_DESKTOP_FIXED.py`
   - `UPDATE_PRAYER_SCHEDULE_FIXED.bat`
3. Double-click `UPDATE_PRAYER_SCHEDULE_FIXED.bat`
4. Files will be generated on your Desktop

### Manual Python Execution
```bash
python prayer_schedule_V10_DESKTOP_FIXED.py
```

The script automatically detects whether it's running:
- **In GitHub Actions**: Saves files to repository directory
- **On Desktop**: Saves files to `~/Desktop` or `%USERPROFILE%\Desktop`

## Technical Details

### Environment Detection
The script uses smart environment detection:
```python
is_ci = os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'
```

- **CI Environment**: Uses current working directory
- **Desktop Environment**: Uses `~/Desktop` or Windows Desktop folder
- **Fallback**: Uses current working directory if Desktop not found

### Church Configuration

#### Elders (8 Total)
1. Alan Judd
2. Brian McLaughlin
3. Frank Bohannon
4. Jerry Wood
5. Jonathan Loveday
6. Kyle Fairman
7. L.A. Fox
8. Larry McDuffee

#### Weekly Prayer Schedule
- **Monday**: Alan Judd & Brian McLaughlin (2 elders)
- **Tuesday**: Frank Bohannon
- **Wednesday**: Jerry Wood
- **Thursday**: Jonathan Loveday
- **Friday**: Kyle Fairman
- **Saturday**: L.A. Fox
- **Sunday**: Larry McDuffee

### Family Distribution
- **Total Families**: 154 from church directory
- **Distribution**: Round-robin across 8 pools
  - Pools 0-1: 20 families each (40 total)
  - Pools 2-7: 19 families each (114 total)
- **Rotation**: Each elder gets a different pool each week
- **Cycle**: Full rotation completes every 8 weeks

### Week Calculation
The system uses **continuous week counting** to ensure consistent scheduling across year boundaries:

```python
REFERENCE_MONDAY = datetime(2025, 12, 29)  # ISO Week 1 of 2026

def calculate_continuous_week(monday_date):
    days_diff = (monday_date - REFERENCE_MONDAY).days
    return (days_diff // 7) + 1
```

- Monotonically increasing week numbers (never resets)
- Within 2026: continuous week == ISO week (backward compatible)
- Handles ISO Week 53 years (e.g., 2026) automatically
- See [Year-Boundary Fix](#year-boundary-fix-2026-02-06) for details

## Workflow Configuration

### GitHub Actions Workflow
Location: `.github/workflows/weekly-schedule.yml`

```yaml
on:
  schedule:
    - cron: '0 13 * * 1'  # Every Monday at 1:00 PM UTC (8 AM CDT / 7 AM CST)
  workflow_dispatch:      # Allow manual trigger
```

### Permissions
The workflow has `contents: write` permission to commit and push generated files.

## Verification & Testing

### Built-in Algorithm Verification
Run the built-in verification:
```python
verify_v10_algorithm()
```

This tests 16 weeks of assignments and verifies:
- Correct family counts (18-20 per elder)
- No elder has own family
- 100% new families each week
- 8-week cycle repeats correctly
- All 154 families covered

### Comprehensive Verification Suite
Run the full test suite:
```bash
python comprehensive_verification.py
```

This performs two sets of tests:

**Coverage Verification** (`verify_complete_coverage`):
- Tests 10 consecutive weeks (weeks 46-55)
- Verifies every family is assigned every week
- Checks no family is assigned to multiple elders
- Validates no elder has their own family
- Confirms 8-week cycle repeats identically
- Checks week-to-week rotation (0% overlap)

**Year-Boundary Verification** (`verify_year_boundary`):
- Tests 4 year boundaries: 2025-2026, 2026-2027, 2027-2028, 2028-2029
- Verifies cycle positions advance by exactly 1 across boundaries
- Checks zero family overlap between consecutive weeks at boundaries
- Confirms continuous_week == ISO week for all of 2026

### Test Results
All verification checks pass:
- Family Count: 18-20 per elder
- Elder Own Family: Never included
- Week Rotation: 100% new families
- 8-Week Cycle: Perfect repetition
- Coverage: All 154 families included
- Year Boundaries: Continuous rotation across all tested boundaries

## Troubleshooting

### Workflow Not Running
1. Check GitHub Actions is enabled for the repository
2. Verify workflow file exists: `.github/workflows/weekly-schedule.yml`
3. Check repository permissions allow workflow execution
4. Review Actions tab for any error messages

### Script Errors
1. Ensure Python 3.11+ is installed
2. Check file permissions
3. Review `prayer_schedule_log.txt` for error details
4. Verify all required files are present

### File Not Generated
1. Check script output for error messages
2. Verify write permissions to target directory
3. Ensure Desktop folder exists (for local execution)
4. Check disk space availability

## Support & Maintenance

### Updating Church Directory
To update the family list, edit the `DIRECTORY_CSV` constant in `prayer_schedule_V10_DESKTOP_FIXED.py`:
```python
DIRECTORY_CSV = """Last Name,First Names
...
"""
```

### Changing Elder Assignments
Edit the `ELDERS` list and `ELDER_FAMILIES` dictionary in the configuration section.

### Modifying Schedule Times
To change when the workflow runs, edit the cron expression in `.github/workflows/weekly-schedule.yml`:
```yaml
- cron: '0 6 * * 1'  # minute hour day month day-of-week
```

## Version History

### Version 10 - DESKTOP - FIXED (Current)
1. Fixed hard-coded user paths - now uses `expanduser`
2. Added CI environment auto-detection
3. Comprehensive error handling
4. Fixed HTML character encoding
5. Removed unnecessary rebalancing code
6. Fixed weekly assignment counting
7. Added secure email delivery (Gmail SMTP)
8. Added automatic schedule archiving
9. **Fixed year-boundary rotation bug** (2026-02-06): ISO week numbers reset from 52/53 to 1 at year boundaries, causing `cycle_position` to jump and duplicate family assignments. Fixed with continuous week counting from a fixed reference date (`REFERENCE_MONDAY = Dec 29, 2025`).
10. **Fixed total_assignments counter** (2026-02-06): Previously counted elders (always 8) instead of total families (154). Now correctly sums family counts across all elders.

### Previous Versions
- Version 9 and earlier: Desktop-only implementations

## License & Credits

**Organization**: Crossville Church of Christ
**System**: Elder Prayer Schedule Automation
**Version**: 10 (DESKTOP - FIXED)

---

## Quick Start Guide

### For Church Administrators

1. **View Current Schedule**:
   - Visit repository on GitHub
   - Open `Prayer_Schedule_Current_Week.html` to view in browser
   - Or download `Prayer_Schedule_Current_Week.txt` for printing

2. **Manual Generation**:
   - Go to Actions tab on GitHub
   - Select "Weekly Prayer Schedule Generation"
   - Click "Run workflow"

3. **Local Execution** (Windows):
   - Copy files to Desktop
   - Run `UPDATE_PRAYER_SCHEDULE_FIXED.bat`
   - View generated HTML file

### For Developers

1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd prayer-schedule-automation
   ```

2. **Run Locally**:
   ```bash
   python prayer_schedule_V10_DESKTOP_FIXED.py
   ```

3. **Run Verification**:
   ```bash
   python comprehensive_verification.py
   ```

4. **Test Workflow**:
   - Push changes to trigger workflow
   - Or use manual workflow dispatch
   - Check Actions tab for execution logs

---

**Status**: Fully Operational
**Next Scheduled Run**: Every Monday at 1:00 PM UTC (8:00 AM CDT / 7:00 AM CST)
