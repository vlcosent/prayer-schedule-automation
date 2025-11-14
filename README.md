# Prayer Schedule Automation

Automated weekly prayer schedule generator for Crossville Church of Christ. This system automatically generates prayer schedules every Monday, rotating 8 elders through 155 church families with a perfect 8-week cycle.

## Features

- **Automatic Weekly Generation**: Runs every Monday at 6:00 AM UTC (1:00 AM EST / 2:00 AM EDT)
- **Email Delivery**: Automatically emails schedule to configured recipients
- **Perfect Rotation**: 100% new families every week - no repeats until the 8-week cycle completes
- **Smart Assignments**: No elder ever prays for their own family
- **Balanced Distribution**: 18-20 families per elder for complete coverage
- **Multiple Formats**: Generates both professional HTML and plain text schedules
- **Dual Environment Support**: Works in both CI/CD (GitHub Actions) and local desktop environments
- **Automatic Archive**: Previous week's schedule automatically archived with date and week number
- **Secure Configuration**: Email credentials stored safely in GitHub Secrets

## System Overview

### Schedule Pattern
- **8 Elders** rotate through **155 church families**
- **8-week rotation cycle** ensures complete coverage
- **Monday**: 2 elders assigned (Alan Judd & Brian McLaughlin)
- **Tuesday-Sunday**: 1 elder per day

### Algorithm Verification
The system performs 5 verification checks on every run:
1. **Family Count Check**: Ensures 18-20 families per elder
2. **Elder Own Family Check**: Verifies no elder has their own family
3. **Week-to-Week Rotation**: Confirms 100% new families each week
4. **8-Week Cycle Check**: Validates the rotation repeats correctly
5. **Family Coverage**: Ensures all 155 families are included

## Automatic Execution (GitHub Actions)

### Schedule
The workflow automatically runs **every Monday at 6:00 AM UTC**:
- **EST**: 1:00 AM Monday
- **EDT**: 2:00 AM Monday

### Workflow Process
1. GitHub Actions triggers on schedule: `cron: '0 6 * * 1'`
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
1. Go to **GitHub Repository** → **Actions** tab
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
    ├── Prayer_Schedule_2025-11-10_Week46.txt
    ├── Prayer_Schedule_2025-11-03_Week45.txt
    ├── Prayer_Schedule_2025-10-27_Week44.txt
    └── ... (historical schedules)
```

### Archive File Naming
- **Format**: `Prayer_Schedule_YYYY-MM-DD_WeekNN.txt`
- **Date**: Monday of the archived week (YYYY-MM-DD)
- **Week Number**: Extracted from file content (e.g., Week46)
- **Example**: `Prayer_Schedule_2025-11-10_Week46.txt`

### Benefits
- **Historical Record**: Complete history of all generated schedules
- **Audit Trail**: Review past elder assignments
- **No Data Loss**: Previous schedules preserved automatically
- **Easy Retrieval**: Chronologically sortable filenames
- **Automatic Management**: No manual intervention required

### Location
- **CI/GitHub Actions**: Archives stored in `archive/` in repository root
- **Desktop Mode**: Archives stored in `~/Desktop/archive/` or Windows Desktop
- **Auto-Created**: Archive directory is created automatically if it doesn't exist

## Email Configuration

The system automatically emails the prayer schedule to configured recipients each week.

### Email Details
- **Sender**: churchprayerlistelders@gmail.com
- **Recipients**:
  - elders@crossvillechurchofchrist.org
  - carolsparks.cs@gmail.com
- **Service**: Gmail SMTP (smtp.gmail.com:587)
- **Format**: Full schedule text included in email body
- **Subject Line**: "Weekly Prayer Schedule - Week XX (Date Range)"

### Setup Requirements

**Important:** Email functionality requires three GitHub Secrets to be configured:

1. **SENDER_EMAIL**: The Gmail address sending the emails
2. **SENDER_PASSWORD**: Gmail App Password (not your regular password)
3. **RECIPIENT_EMAILS**: Comma-separated list of recipient emails

### Quick Setup Guide

1. **Create Gmail App Password**:
   - Enable 2-Factor Authentication on the Gmail account
   - Go to Google Account → Security → 2-Step Verification → App passwords
   - Generate an App Password for "Prayer Schedule Automation"
   - Copy the 16-character password

2. **Configure GitHub Secrets**:
   - Go to repository Settings → Secrets and variables → Actions
   - Add three secrets:
     - `SENDER_EMAIL`: `churchprayerlistelders@gmail.com`
     - `SENDER_PASSWORD`: (the 16-character App Password)
     - `RECIPIENT_EMAILS`: `elders@crossvillechurchofchrist.org,carolsparks.cs@gmail.com`

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

✅ Credentials stored securely in GitHub Secrets (encrypted)
✅ Uses Gmail App Passwords (not account password)
✅ Requires 2-Factor Authentication
✅ Never exposed in code or logs
✅ SMTP connection secured with TLS

## Files in Repository

### Core Files
- **`prayer_schedule_V10_DESKTOP_FIXED.py`** - Main Python script that generates schedules
- **`UPDATE_PRAYER_SCHEDULE_FIXED.bat`** - Windows batch file for local execution
- **`.github/workflows/weekly-schedule.yml`** - GitHub Actions workflow configuration

### Generated Files (Auto-updated)
- **`Prayer_Schedule_Current_Week.html`** - Current week's HTML schedule
- **`Prayer_Schedule_Current_Week.txt`** - Current week's text schedule
- **`prayer_schedule_log.txt`** - Generation activity log
- **`archive/`** - Directory containing historical schedules (auto-created)

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
- **Total Families**: 155 from church directory
- **Distribution**: Round-robin across 8 pools
  - Pools 0-2: 20 families each
  - Pools 3-7: 19 families each
- **Rotation**: Each elder gets a different pool each week

### ISO Week Calculation
The system uses ISO week numbers to ensure consistent scheduling:
- Calculates the Monday of the current week
- Uses Python's `isocalendar()` for accurate week numbers
- Handles year boundaries correctly

## Workflow Configuration

### GitHub Actions Workflow
Location: `.github/workflows/weekly-schedule.yml`

```yaml
on:
  schedule:
    - cron: '0 6 * * 1'  # Every Monday at 6:00 AM UTC
  workflow_dispatch:      # Allow manual trigger
```

### Permissions
The workflow has `contents: write` permission to commit and push generated files.

### Dependencies
- **Python Version**: 3.11
- **Python Packages**: All standard library (no external dependencies)
  - `csv`
  - `datetime`
  - `os`
  - `sys`
  - `traceback`

## Verification & Testing

### Algorithm Verification
Run the built-in verification:
```python
verify_v10_algorithm()
```

This tests 16 weeks of assignments and verifies:
- Correct family counts
- No elder has own family
- 100% new families each week
- 8-week cycle repeats correctly
- All 155 families covered

### Test Results
All verification checks pass:
- ✅ Family Count: 18-20 per elder
- ✅ Elder Own Family: Never included
- ✅ Week Rotation: 100% new families
- ✅ 8-Week Cycle: Perfect repetition
- ✅ Coverage: All 155 families included

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
- ✅ Fixed hard-coded user paths
- ✅ Added CI environment auto-detection
- ✅ Comprehensive error handling
- ✅ Fixed HTML character encoding
- ✅ Removed unnecessary rebalancing code
- ✅ Fixed weekly assignment counting
- ✅ Improved ISO week handling
- ✅ GitHub Actions integration

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

3. **Test Workflow**:
   - Push changes to trigger workflow
   - Or use manual workflow dispatch
   - Check Actions tab for execution logs

---

**Status**: ✅ Fully Operational
**Next Scheduled Run**: Every Monday at 6:00 AM UTC
**Confidence Level**: 100%
