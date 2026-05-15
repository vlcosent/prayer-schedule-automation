# Prayer Schedule Automation

Automated prayer schedule generator for Crossville Church of Christ. Rotates 7 elders through 161 church families on a perfect 7-week cycle. Runs daily via GitHub Actions, sends email reminders, and publishes to [GitHub Pages](https://vlcosent.github.io/prayer-schedule-automation/).

## How It Works

- **7 elders** rotate through **161 families** across **7 pools**
- Each elder gets a different pool each week (22-24 families per elder)
- After 7 weeks, every elder has prayed for every family exactly once
- No elder ever prays for their own family
- Each day of the week has one elder assigned

### Weekly Elder Schedule

| Day | Elder |
|-----|-------|
| Monday | Brian McLaughlin |
| Tuesday | Frank Bohannon |
| Wednesday | Jerry Wood |
| Thursday | Jonathan Loveday |
| Friday | Kyle Fairman |
| Saturday | L.A. Fox |
| Sunday | Larry McDuffee |

## Daily Automation

The system checks repeatedly every morning beginning just after **7:00 AM Central**
and sends at most one email per Central date. A committed send-state file prevents
duplicate emails if GitHub Actions delivers delayed retry runs later in the day:

- **Monday**: Archives previous schedule, generates new weekly schedule, sends a combined daily email (today's assignment + week overview + full prayer lists for every elder)
- **Tuesday-Sunday**: Refreshes output files, sends a combined daily email (today's assignment + week overview)

All emails go to 9 configured recipients (elder group list + individual elders + church staff).

### Manual Trigger

1. Go to **Actions** tab on GitHub
2. Select **"Daily Prayer Schedule Email"**
3. Click **"Run workflow"** (emails are off by default for manual runs)

## Generated Files

| File | Purpose |
|------|---------|
| `Prayer_Schedule_Current_Week.html` | Web-viewable schedule with day highlighting |
| `Prayer_Schedule_Current_Week.txt` | Plain text version for printing |
| `prayer_schedule_log.txt` | Activity log with timestamps |
| `.github/prayer-email-state.json` | Last successful email date used by the scheduled retry gate |
| `archive/` | Historical weekly schedules |

## Local Usage

### Windows
1. Ensure Python 3.11+ is installed
2. Double-click `UPDATE_PRAYER_SCHEDULE_FIXED.bat`
3. Files appear on your Desktop

### Any Platform
```bash
python prayer_schedule_V10_DESKTOP_FIXED.py
```

The script auto-detects CI vs. desktop and saves files accordingly. Email sending requires environment variables (see below).

## Email Setup

Email requires three **GitHub Secrets** (Settings > Secrets and variables > Actions):

| Secret | Value |
|--------|-------|
| `SENDER_EMAIL` | `churchprayerlistelders@gmail.com` |
| `SENDER_PASSWORD` | Gmail App Password (16 characters, requires 2FA) |
| `RECIPIENT_EMAILS` | Comma-separated list of all recipient emails |

For detailed setup instructions, see [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md).

To temporarily disable emails, set `EMAIL_ENABLED: 'false'` in `.github/workflows/weekly-schedule.yml`.

## Updating the Church Directory

To add or remove a family:

1. Edit `DIRECTORY_CSV` in `prayer_schedule/directory.py`
2. Recalculate `FIXED_REASSIGNMENT_MAP` in `prayer_schedule/algorithm.py` using `calc_reassignments.py`
3. Run `python -m pytest tests/` to confirm all invariants still hold

To change an elder, update `ELDER_DATA` in `prayer_schedule/elders.py`, regenerate `FIXED_REASSIGNMENT_MAP` in `prayer_schedule/algorithm.py`, and update the `RECIPIENT_EMAILS` GitHub secret. See [CLAUDE.md](CLAUDE.md) for the full checklist.

## Verification

The system verifies 5 invariants on every run:
1. **Family count**: 22-24 families per elder
2. **Self-prayer**: No elder has their own family
3. **Rotation**: 100% new families every consecutive week
4. **Cycle**: Assignments repeat exactly after 7 weeks
5. **Coverage**: All 161 families included

Run the full test suite:
```bash
python comprehensive_verification.py
```

## Technical Details

- **Python 3.11**, stdlib only (no pip dependencies)
- **Timezone**: US Central via `zoneinfo.ZoneInfo("America/Chicago")` (auto-handles DST)
- **Year boundaries**: Continuous week counter from reference date (Dec 29, 2025) prevents ISO week reset bugs
- **CI/CD**: GitHub Actions with failure alerting via auto-created issues

## File Reference

| File | Description |
|------|-------------|
| `prayer_schedule_V10_DESKTOP_FIXED.py` | Main application (all logic) |
| `.github/workflows/weekly-schedule.yml` | CI workflow (daily cron + manual) |
| `comprehensive_verification.py` | Extended verification test suite |
| `calc_reassignments.py` | Reassignment map calculator |
| `analyze_missing_coverage.py` | Pool distribution analyzer |
| `CLAUDE.md` | Developer/AI reference guide |
| `EMAIL_SETUP_GUIDE.md` | Email configuration walkthrough |
| `index.html` | GitHub Pages landing page |
| `UPDATE_PRAYER_SCHEDULE_FIXED.bat` | Windows launcher |
