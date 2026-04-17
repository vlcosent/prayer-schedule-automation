# CLAUDE.md - Project Guide

## What This Project Does

Automated prayer schedule system for Crossville Church of Christ. Rotates 8 elders through 161 church families on an 8-week cycle. Runs daily via GitHub Actions at 1 PM UTC. Sends email reminders and publishes to GitHub Pages.

## Quick Reference

| Item | Value |
|------|-------|
| Main script | `prayer_schedule_V10_DESKTOP_FIXED.py` (1671 lines, single file) |
| Workflow | `.github/workflows/weekly-schedule.yml` |
| Python version | 3.11 (stdlib only, no pip dependencies) |
| Families | 161 (embedded in `DIRECTORY_CSV` constant, line ~160) |
| Elders | 8 (in `ELDERS` list, line ~136) |
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
When an elder's pool contains their own family, it's filtered out and reassigned to another elder via `FIXED_REASSIGNMENT_MAP` (defined inside `assign_families_for_week_v10()` at line ~470). The map covers cycle positions [1, 4, 5, 6, 7]. Each target is verified "adjacency-safe" (no week-to-week repeats).

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
| 41-53 | Imports | All stdlib: csv, datetime, smtplib, zoneinfo, etc. |
| 55-81 | `DESKTOP_DIR` setup | Auto-detects CI vs desktop environment |
| 83-90 | Email config | SMTP settings, credentials from env vars |
| 93-105 | Timezone + `get_today()` | `CENTRAL_TZ` via `zoneinfo.ZoneInfo("America/Chicago")` |
| 108-132 | `verify_email_date()` | Date sanity check before sending email |
| 136-158 | Elder data | `ELDERS` list (136), `ELDER_FAMILIES` dict (148) |
| 160-322 | `DIRECTORY_CSV` | All 161 families as embedded CSV string |
| 323-330 | `parse_directory()` | CSV → sorted list of "Last, First" strings |
| 332-342 | `get_week_schedule()` | Static day→elder mapping (Mon=2 elders, Tue-Sun=1) |
| 344-378 | Week calculation | `calculate_week_number()`, `calculate_continuous_week()` |
| 380-415 | `create_v10_master_pools()` | Round-robin pool distribution (+ `get_master_pools()`) |
| 417-494 | `assign_families_for_week_v10()` | Core assignment; defines `FIXED_REASSIGNMENT_MAP` (line ~470) as a local inside this function |
| 496-602 | `verify_v10_algorithm()` | 16-week verification (5 checks) |
| 604-1012 | `generate_schedule_content()` | HTML + text output generation |
| 1014-1063 | `archive_previous_schedule()` | Move old .txt to `archive/` directory |
| 1065-1118 | `_email_styles()` | Shared inline CSS for HTML emails |
| 1121-1296 | `_build_combined_email_html()` | Combined daily email template (today + week overview) |
| 1299-1470 | `send_daily_combined_email()` | Combined daily email via Gmail SMTP |
| 1472-1507 | File I/O + logging | `update_desktop_files()`, `log_activity()` |
| 1509-1540 | `verify_schedule()` | Runtime validation of current week |
| 1542-1667 | `main()` | Orchestrator: verify → assign → generate → email |

## Common Tasks

### Adding/Removing a Family
1. Edit `DIRECTORY_CSV` in `prayer_schedule_V10_DESKTOP_FIXED.py` (line ~160)
2. Recalculate `FIXED_REASSIGNMENT_MAP` (line ~470, inside `assign_families_for_week_v10()`) using `calc_reassignments.py`
3. Update family count comments (search for old count, e.g. "161")
4. Run `python comprehensive_verification.py` to confirm all checks pass
5. Update pool size comments if distribution changes

### Adding/Removing an Elder
Elder data is spread across 6 locations (all in the main script):
1. `ELDERS` list (line ~136)
2. `ELDER_FAMILIES` dict (line ~148)
3. `get_week_schedule()` function (line ~332)
4. `FIXED_REASSIGNMENT_MAP` (line ~470, inside `assign_families_for_week_v10()`)
5. Email config `RECIPIENT_EMAILS` (line ~90, plus GitHub Secrets)
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
- Monday: archive old schedule → regenerate files → send combined daily email (today's assignment + full week overview + all elders' prayer lists)
- Tue-Sun: regenerate HTML/text → send combined daily email (today's assignment + week overview)
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

- **Single-file architecture**: All 1600+ lines in one script. Works fine but harder to navigate.
- **Hardcoded fallback emails**: Lines 88-90 have real email addresses as defaults if env var is missing.
- **Static reassignment map**: `FIXED_REASSIGNMENT_MAP` must be manually recalculated when families or elders change.
- **Locked to 8 elders**: Pool count, rotation, and reassignment map all assume exactly 8.
- **No unit test framework**: Verification is built-in but not pytest-based.
