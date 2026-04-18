# CLAUDE.md - Project Guide

## What This Project Does

Automated prayer schedule system for Crossville Church of Christ. Rotates 8 elders through 161 church families on an 8-week cycle. Runs daily via GitHub Actions at 1 PM UTC. Sends email reminders and publishes to GitHub Pages.

## Quick Reference

| Item | Value |
|------|-------|
| Entry point | `prayer_schedule_V10_DESKTOP_FIXED.py` (42-line shim → `prayer_schedule.cli.main`) |
| Application | `prayer_schedule/` package (config, elders, directory, algorithm, validation, output, email_service, file_io, utils, cli) |
| Tests | `tests/` (pytest — 100+ tests, covers algorithm invariants, year boundaries, validators, landing page) |
| Workflow | `.github/workflows/weekly-schedule.yml` (cron + deploy) and `.github/workflows/ci.yml` (PR tests) |
| Python version | 3.11 (stdlib only, pytest only in CI) |
| Families | 161 (embedded in `DIRECTORY_CSV`, `prayer_schedule/directory.py`) |
| Elders | 8 (single-source-of-truth in `ELDER_DATA`, `prayer_schedule/elders.py`) |
| Cron schedule | 12:17 UTC (CDT) / 13:17 UTC (CST) — gated by DST-aware step |
| GitHub Pages | Built fresh by deploy job: `build_landing_page.py` + current files (from artifact) + `archive/` |

## Repository File Map

```
prayer_schedule_V10_DESKTOP_FIXED.py   # Thin backward-compat shim (42 lines)
prayer_schedule/                        # Main application package
    __init__.py                         # Public API re-exports
    config.py                           # SMTP, timezone, paths, tuning constants
    elders.py                           # ELDER_DATA SSOT → ELDERS, ELDER_FAMILIES, schedule
    directory.py                        # DIRECTORY_CSV + validated parse_directory()
    algorithm.py                        # Pool distribution, assignment, FIXED_REASSIGNMENT_MAP
    validation.py                       # Startup + runtime validators
    output.py                           # HTML + text schedule generators
    email_service.py                    # Gmail SMTP + combined-email builder
    file_io.py                          # Atomic file writes, archiving, logging
    utils.py                            # get_today, iter_week, day_name_for
    cli.py                              # main() orchestrator

tests/                                  # pytest suite
    conftest.py                         # Shared fixtures
    test_directory.py                   # CSV parsing + validation
    test_algorithm.py                   # All invariants across many weeks
    test_year_boundary.py               # ISO-week reset regression tests
    test_validation.py                  # Startup validators
    test_landing_page.py                # build_landing_page.py logic

build_landing_page.py                   # Generates index.html from archive/
.github/workflows/
    weekly-schedule.yml                 # Daily cron + Pages deploy
    ci.yml                              # PR tests (pytest + smoke run)
.nojekyll                               # Tells GitHub Pages to skip Jekyll
UPDATE_PRAYER_SCHEDULE_FIXED.bat        # Windows launcher (calls shim)

# Documentation
README.md                               # User-facing project overview
EMAIL_SETUP_GUIDE.md                    # Gmail App Password + GitHub Secrets setup
CLAUDE.md                               # This file (AI/developer reference)

# Helper scripts (legacy — now duplicate of tests/ for debugging)
comprehensive_verification.py           # Coverage + year-boundary quick check
analyze_missing_coverage.py             # Shows which elder families land in which pools
calc_reassignments.py                   # Recompute FIXED_REASSIGNMENT_MAP targets

# Generated files (NOT committed — .gitignored)
Prayer_Schedule_Current_Week.html       # Rebuilt every run, flows via workflow artifact
Prayer_Schedule_Current_Week.txt        # Rebuilt every run, flows via workflow artifact
prayer_schedule_log.txt                 # Activity log; kept locally only
index.html                              # Landing page; rebuilt each deploy
archive/                                # Historical weekly schedules (committed — Monday rollover only)
```

## How the Algorithm Works

### Pool Distribution
1. Parse 161 families from `DIRECTORY_CSV` (sorted alphabetically)
2. Distribute round-robin into 8 pools: Pool 0 = 21 families, Pools 1-7 = 20 each
3. Each week, elder `i` gets pool `(i + cycle_position) % 8`
4. `cycle_position = (continuous_week - 1) % 8` advances by 1 each week

### Elder-Own-Family Handling
When an elder's pool contains their own family, it's filtered out and reassigned to another elder via `FIXED_REASSIGNMENT_MAP` (module-level constant in `prayer_schedule/algorithm.py`). The map covers cycle positions [1, 4, 5, 6, 7]. Each target is verified "adjacency-safe" (no week-to-week repeats). Validated at startup by `validate_reassignment_map()` in `prayer_schedule/validation.py`.

### Year-Boundary Fix
ISO week numbers reset at year boundaries (52→1), breaking `cycle_position`. Fixed with `calculate_continuous_week()` using `REFERENCE_MONDAY = 2025-12-29`. Within 2026, continuous week == ISO week.

### Key Invariants (verified every run)
- Each elder gets 19-21 families per week
- No elder prays for their own family
- 100% new families every consecutive week
- 8-week cycle repeats exactly
- All 161 families covered

## Package Structure (prayer_schedule/)

| Module | Responsibility |
|--------|----------------|
| `config.py` | SMTP settings, `CENTRAL_TZ`, `REFERENCE_MONDAY`, `DAYS_OF_WEEK`, `DESKTOP_DIR`, env-var reads, tuning constants (`ELDER_COUNT`, `POOL_COUNT`, `FAMILIES_PER_ELDER_MIN/MAX`) |
| `elders.py` | `ELDER_DATA` single-source-of-truth → derived `ELDERS`, `ELDER_FAMILIES`, and `get_week_schedule()` |
| `directory.py` | `DIRECTORY_CSV` constant + `parse_directory(csv_content=None)` with row-numbered validation and duplicate detection |
| `algorithm.py` | `create_v10_master_pools`, `get_master_pools`, `assign_families_for_week_v10`, module-level `FIXED_REASSIGNMENT_MAP`, `calculate_week_number`, `calculate_continuous_week` |
| `validation.py` | Structured validators returning `(ok, issues)` tuples: `validate_elder_data`, `validate_reassignment_map`, `validate_email_config`, `verify_today_elder_assignment`, `verify_schedule`, `verify_v10_algorithm`, `verify_email_date` |
| `output.py` | `generate_html_schedule`, `generate_text_schedule`, `generate_schedule_content` orchestrator |
| `email_service.py` | `_email_styles`, `_build_combined_email_html`, `send_daily_combined_email` (with `List-Unsubscribe` header per RFC 8058) |
| `file_io.py` | Atomic writes via `<path>.tmp` + `os.replace`, pre-write permission checks, `archive_previous_schedule`, `log_activity` |
| `utils.py` | `get_today`, `iter_week`, `day_name_for` |
| `cli.py` | `main()` orchestrator: validators → algorithm → generate → write → email |

All public symbols are re-exported from the top-level `prayer_schedule` package and from the backward-compat shim `prayer_schedule_V10_DESKTOP_FIXED.py`.

## Common Tasks

### Adding/Removing a Family
1. Edit `DIRECTORY_CSV` in `prayer_schedule/directory.py`
2. Recalculate `FIXED_REASSIGNMENT_MAP` in `prayer_schedule/algorithm.py` using `calc_reassignments.py`
3. Run `python -m pytest tests/` — several tests hard-assert the count (161); update them if the total changes
4. Run `python comprehensive_verification.py` as a second sanity check

### Adding/Removing an Elder
Only TWO edits needed (down from 6 in the old monolith):
1. Update `ELDER_DATA` in `prayer_schedule/elders.py` (name, family, days).
2. Update `FIXED_REASSIGNMENT_MAP` in `prayer_schedule/algorithm.py` (use `calc_reassignments.py` to compute safe targets).
3. Update `RECIPIENT_EMAILS` GitHub secret.
4. Run `python -m pytest tests/` — the validation suite catches most drift automatically.

### Changing the Schedule Time
Edit cron in `.github/workflows/weekly-schedule.yml` (the DST-aware gate picks the right entry automatically).

### Testing Without Sending Emails
Use manual workflow dispatch with `send_emails: false` (default for manual runs), or locally: `EMAIL_ENABLED=false python prayer_schedule_V10_DESKTOP_FIXED.py`.

### Running Verification
```bash
python -m pytest tests/                     # Primary test suite (100+ tests)
python comprehensive_verification.py        # Legacy quick check
python prayer_schedule_V10_DESKTOP_FIXED.py # Full run (needs EMAIL_ENABLED=false)
```

## CI/CD Workflow Behavior

**`.github/workflows/weekly-schedule.yml` — scheduled + dispatch:**
- Runs pytest first; aborts if any test fails.
- Generates schedule files into the runner, uploads as artifact, sends combined daily email.
- Commits only `archive/` rollovers (Mondays). Current-week files and the log are NEVER committed.
- Deploy job downloads the artifact, runs `build_landing_page.py`, and publishes to GitHub Pages (index + current + archive).

**`.github/workflows/ci.yml` — push/PR:**
- Runs pytest + smoke-runs the main script (no email).

**Manual runs (workflow_dispatch):**
- Emails disabled by default (opt-in via `send_emails` input).

**On failure (scheduled runs only):**
- Creates or comments on a GitHub issue labeled "bug".

## Environment Variables

| Variable | Required | Source | Purpose |
|----------|----------|--------|---------|
| `CI` / `GITHUB_ACTIONS` | Auto-set | GitHub | Detect CI environment |
| `EMAIL_ENABLED` | Set in workflow | Workflow env | Enable/disable email sending |
| `SENDER_EMAIL` | Yes (for email) | GitHub Secret | Gmail sender address |
| `SENDER_PASSWORD` | Yes (for email) | GitHub Secret | Gmail App Password |
| `RECIPIENT_EMAILS` | Yes (for email) | GitHub Secret | Comma-separated recipient list |

## Known Limitations

- **Static reassignment map**: `FIXED_REASSIGNMENT_MAP` must be manually recalculated when families or elders change. Use `calc_reassignments.py` and the test suite catches drift.
- **Locked to 8 elders**: Pool count, rotation, and reassignment map all assume exactly 8 (`ELDER_COUNT = POOL_COUNT = 8` in `config.py`).
- **Directory PII in source**: Family names live in `DIRECTORY_CSV` (`prayer_schedule/directory.py`) and elder family identities in `ELDER_DATA` (`prayer_schedule/elders.py`). Treat the repo as sensitive and keep it private.
