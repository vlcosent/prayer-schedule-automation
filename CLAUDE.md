# CLAUDE.md - Project Guide

## What This Project Does

Automated prayer schedule system for Crossville Church of Christ. Rotates 8 elders through 161 church families on an 8-week cycle. Runs daily via GitHub Actions at 1 PM UTC. Sends email reminders and publishes to GitHub Pages.

## Quick Reference

| Item | Value |
|------|-------|
| Main script | `prayer_schedule_V10_DESKTOP_FIXED.py` (1704 lines, single file) |
| Workflow | `.github/workflows/weekly-schedule.yml` |
| Python version | 3.11 (stdlib only, no pip dependencies) |
| Families | 161 (embedded in `DIRECTORY_CSV` constant, line ~170) |
| Elders | 8 (in `ELDERS` list, line ~146) |
| Cron schedule | Daily 1 PM UTC = 8 AM CDT / 7 AM CST |
| Email sender | `churchprayerlistelders@gmail.com` via Gmail SMTP |
| GitHub Pages | Deployed from `index.html` + generated HTML |

## Repository File Map

```
prayer_schedule_V10_DESKTOP_FIXED.py   # THE application (all logic in one file)
.github/workflows/weekly-schedule.yml  # CI: daily cron + manual dispatch
.github/workflows/deploy-pages.yml     # GitHub Pages deploy (on push to main)
index.html                             # GitHub Pages landing page
.nojekyll                              # Tells GitHub Pages to skip Jekyll
UPDATE_PRAYER_SCHEDULE_FIXED.bat       # Windows launcher (double-click to run locally)

# Documentation
README.md                              # User-facing project overview
EMAIL_SETUP_GUIDE.md                   # Gmail App Password + GitHub Secrets setup
CLAUDE.md                              # This file (AI/developer reference)

# Helper scripts (for development/debugging only)
comprehensive_verification.py          # Extended test suite: coverage + year-boundary
analyze_missing_coverage.py            # Shows which elder families land in which pools
calc_reassignments.py                  # Calculates safe reassignment targets

# Generated files (auto-committed by CI)
Prayer_Schedule_Current_Week.html      # Current week schedule (web viewable)
Prayer_Schedule_Current_Week.txt       # Current week schedule (plain text)
prayer_schedule_log.txt                # Activity log with timestamps
archive/                               # Historical weekly schedules (.txt files)
```

## How the Algorithm Works

### Pool Distribution
1. Parse 161 families from `DIRECTORY_CSV` (sorted alphabetically)
2. Distribute round-robin into 8 pools: Pool 0 = 21 families, Pools 1-7 = 20 each
3. Each week, elder `i` gets pool `(i + cycle_position) % 8`
4. `cycle_position = (continuous_week - 1) % 8` advances by 1 each week

### Elder-Own-Family Handling
When an elder's pool contains their own family, it's filtered out and reassigned to another elder via `FIXED_REASSIGNMENT_MAP` (line ~480). The map covers cycle positions [1, 4, 5, 6, 7]. Each target is verified "adjacency-safe" (no week-to-week repeats).

### Year-Boundary Fix
ISO week numbers reset at year boundaries (52→1), breaking `cycle_position`. Fixed with `calculate_continuous_week()` using `REFERENCE_MONDAY = 2025-12-29`. Within 2026, continuous week == ISO week.

### Key Invariants (verified every run)
- Each elder gets 19-21 families per week
- No elder prays for their own family
- 100% new families every consecutive week
- 8-week cycle repeats exactly
- All 161 families covered

## Main Script Structure (prayer_schedule_V10_DESKTOP_FIXED.py)

| Lines | Section | Purpose |
|-------|---------|---------|
| 1-39 | Module docstring | Feature list and version history |
| 40-53 | Imports | All stdlib: csv, datetime, smtplib, zoneinfo, etc. |
| 54-78 | `DESKTOP_DIR` setup | Auto-detects CI vs desktop environment |
| 82-100 | Email config | SMTP settings, credentials from env vars |
| 103-116 | Timezone | `CENTRAL_TZ` via `zoneinfo.ZoneInfo("America/Chicago")` |
| 118-142 | `verify_email_date()` | Date sanity check before sending email |
| 145-167 | Elder data | `ELDERS` list, `ELDER_FAMILIES` dict |
| 169-331 | `DIRECTORY_CSV` | All 161 families as embedded CSV string |
| 333-340 | `parse_directory()` | CSV → sorted list of "Last, First" strings |
| 342-352 | `get_week_schedule()` | Static day→elder mapping (Mon=2 elders, Tue-Sun=1) |
| 354-388 | Week calculation | `calculate_week_number()`, `calculate_continuous_week()` |
| 390-418 | `create_v10_master_pools()` | Round-robin pool distribution |
| 420-504 | `assign_families_for_week_v10()` | Core assignment + `FIXED_REASSIGNMENT_MAP` |
| 506-612 | `verify_v10_algorithm()` | 16-week verification (5 checks) |
| 614-1017 | `generate_schedule_content()` | HTML + text output generation |
| 1024-1073 | `archive_previous_schedule()` | Move old .txt to `archive/` directory |
| 1075-1211 | Email HTML builders | `_email_styles()`, `_build_weekly_email_html()` |
| 1214-1271 | `_build_daily_email_html()` | Daily reminder email template |
| 1274-1369 | `send_email_schedule()` | Weekly email via Gmail SMTP |
| 1372-1486 | `send_daily_email()` | Daily reminder email via Gmail SMTP |
| 1488-1523 | File I/O + logging | `update_desktop_files()`, `log_activity()` |
| 1525-1556 | `verify_schedule()` | Runtime validation of current week |
| 1558-1704 | `main()` | Orchestrator: verify → assign → generate → email |

## Common Tasks

### Adding/Removing a Family
1. Edit `DIRECTORY_CSV` in `prayer_schedule_V10_DESKTOP_FIXED.py` (line ~170)
2. Recalculate `FIXED_REASSIGNMENT_MAP` (line ~480) using `calc_reassignments.py`
3. Update family count comments (search for old count, e.g. "161")
4. Run `python comprehensive_verification.py` to confirm all checks pass
5. Update pool size comments if distribution changes

### Adding/Removing an Elder
Elder data is spread across 6 locations (all in the main script):
1. `ELDERS` list (line ~146)
2. `ELDER_FAMILIES` dict (line ~158)
3. `get_week_schedule()` function (line ~342)
4. `FIXED_REASSIGNMENT_MAP` (line ~480)
5. Email config `RECIPIENT_EMAILS` (line ~89, plus GitHub Secrets)
6. README.md documentation

### Changing the Schedule Time
Edit cron in `.github/workflows/weekly-schedule.yml` line 6:
```yaml
- cron: '0 13 * * *'  # minute hour * * * (UTC)
```

### Testing Without Sending Emails
Use manual workflow dispatch with `send_emails: false` (the default for manual runs).
Or locally: just run `python prayer_schedule_V10_DESKTOP_FIXED.py` without setting `EMAIL_ENABLED=true`.

### Running Verification
```bash
python comprehensive_verification.py       # Full test suite
python prayer_schedule_V10_DESKTOP_FIXED.py # Also runs verify_v10_algorithm() internally
```

## CI/CD Workflow Behavior

**Scheduled runs (daily cron):**
- Emails always enabled
- Monday: archive old schedule → regenerate files → send weekly email → send daily email
- Tue-Sun: regenerate HTML/text → send daily email
- Commits generated files → pushes to main → deploys to GitHub Pages

**Manual runs (workflow_dispatch):**
- Emails disabled by default (selectable via `send_emails` input)
- Same generation logic as scheduled runs

**On failure (scheduled runs only):**
- Creates or comments on a GitHub issue labeled "bug"

## Environment Variables

| Variable | Required | Source | Purpose |
|----------|----------|--------|---------|
| `CI` / `GITHUB_ACTIONS` | Auto-set | GitHub | Detect CI environment |
| `EMAIL_ENABLED` | Set in workflow | Workflow env | Enable/disable email sending |
| `SENDER_EMAIL` | Yes (for email) | GitHub Secret | Gmail sender address |
| `SENDER_PASSWORD` | Yes (for email) | GitHub Secret | Gmail App Password |
| `RECIPIENT_EMAILS` | Yes (for email) | GitHub Secret | Comma-separated recipient list |

## Known Limitations

- **Single-file architecture**: All 1700+ lines in one script. Works fine but harder to navigate.
- **Hardcoded fallback emails**: Lines 89-100 have real email addresses as defaults if env var is missing.
- **Static reassignment map**: `FIXED_REASSIGNMENT_MAP` must be manually recalculated when families or elders change.
- **Locked to 8 elders**: Pool count, rotation, and reassignment map all assume exactly 8.
- **No unit test framework**: Verification is built-in but not pytest-based.
