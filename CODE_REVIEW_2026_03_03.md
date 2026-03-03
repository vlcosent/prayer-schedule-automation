# Code Review & Improvement Plan - March 3, 2026

## Review Methodology

Full codebase review covering: algorithm correctness, security, reliability,
CI/CD operations, maintainability, and HTML/UX. Each proposed change includes
upstream/downstream impact analysis.

---

## FINDINGS SUMMARY

| Severity | Count | Description |
|----------|-------|-------------|
| BUG      | 3     | DST timezone, email return values, bare except clauses |
| SECURITY | 1     | Hardcoded fallback emails in source code |
| CI/CD    | 3     | git add -A, no failure alerts, no dry-run mode |
| UX       | 1     | HTML missing accessibility attributes |
| MAINT    | 1     | Helper scripts with hardcoded absolute paths |

**Algorithm status:** All 5 verification checks PASS. 8-week cycle, year-boundary,
coverage, self-prayer, and rotation all verified correct across 10+ weeks.

---

## BUG 1: DST Timezone Calculation (MEDIUM-HIGH)

**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 104-118
**Issue:** `CENTRAL_UTC_OFFSET_HOURS = -6` is hardcoded CST. During CDT (Mar 8 - Nov 1),
the actual offset is UTC-5. The script runs at 1 PM UTC (8 AM CDT / 7 AM CST).

**Impact during CDT:** `get_today()` returns a time that is 1 hour behind actual
Central Time. At 1 PM UTC, the script thinks it is 7 AM CST when it is actually 8 AM CDT.
This means `today` is still correct (same calendar date), but the logged time is wrong.

**When it BREAKS:** If the cron job ever ran between midnight and 1 AM UTC, the
wrong date could be computed (UTC midnight = 6 PM CST but 7 PM CDT -- both previous day,
so actually safe at the current 1 PM UTC schedule). However, the comment says "CST
(Nov-Mar)" when March includes DST transition on the 8th.

**Upstream impact:** None - this is a leaf function.
**Downstream impact:** `main()`, `verify_email_date()`, `send_daily_email()` all
depend on `get_today()`. A wrong date would cause date verification to fail and
block email sending entirely (a safe failure mode, but still a service outage).

**Fix:** Replace with `zoneinfo.ZoneInfo("America/Chicago")` from Python 3.9+ stdlib.
Uses IANA timezone database -- automatically correct, even if US DST rules change.

---

## BUG 2: Email Return Values Discarded (MEDIUM)

**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 1446, 1465
**Issue:** `send_email_schedule()` and `send_daily_email()` return bool success/failure,
but `main()` discards these return values. If email fails, the script still exits 0
(success), and CI reports green.

**Upstream impact:** None - `main()` is the caller.
**Downstream impact:** GitHub Actions sees exit 0 regardless of email failure. No one
knows emails failed until elders notice they didn't receive the schedule.

**Fix:** Capture return values, log warnings on failure. Don't make email failure
fatal (schedule files are still valuable), but log clearly.

---

## BUG 3: Bare `except:` Clauses (LOW-MEDIUM)

**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 75, 1306
**Issue:** Line 75 `except:` catches ALL exceptions including `SystemExit` and
`KeyboardInterrupt`. Line 1306 `except: pass` silently swallows all logging errors.

**Upstream impact:** None.
**Downstream impact:** Line 75 could mask import errors or memory errors during startup.
Line 1306 could hide disk-full conditions that would affect file output too.

**Fix:** Line 75 -> `except Exception:`. Line 1306 -> `except Exception:` with stderr note.

---

## SECURITY: Hardcoded Fallback Emails (LOW)

**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 89-100
**Issue:** 8 personal email addresses hardcoded as fallback defaults. These are in
the git history permanently. The `os.environ.get('RECIPIENT_EMAILS', ','.join([...]))`
pattern means if the env var is not set, real emails are used.

**Upstream impact:** None.
**Downstream impact:** If someone forks the repo or the env var isn't set in a new
CI environment, emails go to real people unexpectedly.

**Note:** NOT fixing in this PR to avoid breaking production. The env var IS set in
GitHub Actions secrets. Documenting for future cleanup.

---

## CI/CD 1: `git add -A` Commits Unintended Files (MEDIUM)

**File:** `.github/workflows/weekly-schedule.yml` line 43
**Issue:** `git add -A` stages ALL untracked files. If the script creates unexpected
files (temp files, debug output, .pyc files), they get committed.

**Upstream impact:** None.
**Downstream impact:** Repository bloat, potential secret leakage if a `.env` file
is accidentally created.

**Fix:** Replace with explicit file list matching the known generated outputs.

---

## CI/CD 2: No Failure Notifications (MEDIUM-HIGH)

**File:** `.github/workflows/weekly-schedule.yml`
**Issue:** If the cron job fails, no one is notified. Elders could go days/weeks
without prayer schedules before someone manually checks.

**Upstream impact:** None.
**Downstream impact:** Complete service outage with zero visibility.

**Fix:** Add `if: failure()` step that creates a GitHub issue on failure.

---

## CI/CD 3: No Dry-Run for Manual Trigger (LOW-MEDIUM)

**File:** `.github/workflows/weekly-schedule.yml` line 7
**Issue:** `workflow_dispatch` always sends real emails. Cannot test/preview
without emailing all 10 recipients.

**Upstream impact:** None.
**Downstream impact:** Discourages testing, increases risk of accidental emails.

**Fix:** Add `workflow_dispatch` input `send_emails` (default: false for manual).

---

## UX: HTML Accessibility (LOW)

**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 621-624
**Issue:** Missing `lang="en"` on `<html>`, missing viewport meta tag (partially
addressed on mobile with @media query but no viewport), missing `scope` on `<th>`.

**Upstream impact:** None.
**Downstream impact:** Screen readers and mobile browsers have degraded experience.

**Fix:** Add attributes to HTML template.

---

## MAINT: Hardcoded Absolute Paths in Helper Scripts (LOW)

**Files:** `comprehensive_verification.py:18`, `analyze_missing_coverage.py:6`,
`calc_reassignments.py:5`
**Issue:** `sys.path.insert(0, '/home/user/prayer-schedule-automation')` fails on
any other machine.

**Upstream impact:** None (these are standalone scripts).
**Downstream impact:** Scripts can't run on developer machines or in CI.

**Fix:** Use `os.path.dirname(os.path.abspath(__file__))` for dynamic resolution.

---

## CHANGES NOT MADE (and why)

| Item | Reason |
|------|--------|
| Remove hardcoded emails | Would break production if env vars ever missing; needs coordination |
| Modularize into package | Too large for this PR; requires separate planning phase |
| Externalize CSV directory | Changes how non-developers update the family list; needs UX design |
| Add pytest suite | Valuable but orthogonal; should be its own PR |
| Remove PII from git history | Destructive operation (filter-repo); requires repo admin coordination |
| Parameterize 8-elder count | Algorithm + reassignment map would need full redesign |

---

## IMPLEMENTATION ORDER

Changes ordered by risk (lowest first) with test verification between each:

1. Fix helper script paths (zero risk to production)
2. Fix bare except clauses (minimal risk)
3. Add HTML accessibility attributes (cosmetic only)
4. Capture email return values (additive logging)
5. Fix DST timezone calculation (behavior change - tested)
6. Fix CI workflow: explicit git add, failure alerts, dry-run input
7. Run full verification suite to confirm no regressions
