# Prayer Schedule Automation - Improvement Plan

**Generated:** 2026-02-09 by Team Swarm Analysis (6 specialized agents)
**Project:** Crossville Church of Christ - Prayer Schedule System V10

---

## Executive Summary

Six specialized analysis agents reviewed the entire codebase across these dimensions:
1. **Architecture & Code Organization**
2. **Testing & Reliability**
3. **Algorithm Correctness**
4. **Security & Configuration**
5. **CI/CD & Operations**
6. **Maintainability & User Experience**

**Total issues found: 76** across all categories.

Below is a prioritized, actionable improvement plan organized by severity.

---

## P0 - CRITICAL (Fix Immediately)

### 1. PII (Personal Information) Exposed in Git Repository
**Category:** Security | **Files:** Multiple

The repository currently tracks files containing real personal information:
- `Prayer_Schedule_Current_Week.txt` and `.html` contain **155 family names** with spouse/children details
- `archive/` directory contains **multiple weeks** of historical schedules with the same data
- **Lines 75-86** of the main script hard-code **8 real personal email addresses** as fallback defaults

**Action Items:**
- [ ] Add generated files and archive to `.gitignore`
- [ ] Remove hard-coded email addresses from source code (use env vars only, no fallback)
- [ ] Run `git rm --cached` on schedule files to stop tracking them
- [ ] Consider scrubbing git history of PII using `git filter-repo`

---

### 2. ISO Week 53 Year-Boundary Bug
**Category:** Algorithm | **File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 291-298, 347

The 8-week rotation cycle breaks at year boundaries when ISO week 53 exists (occurs in 2026, 2032, 2037, etc.):
```
Week 53: cycle_position = (53-1) % 8 = 4
Week 1 (next year): cycle_position = (1-1) % 8 = 0  // Should be 5!
```

This causes the rotation to **jump from cycle 4 to cycle 0**, breaking the guarantee of 100% new families every week during the transition.

**Action Items:**
- [ ] Replace ISO week modulo with a continuous week counter from a fixed reference date
- [ ] Add year-boundary unit tests covering weeks 52-53-1 transitions
- [ ] Test specifically for years 2026, 2032, 2037 where week 53 exists

---

### 3. No Failure Notification in CI/CD
**Category:** Operations | **File:** `.github/workflows/weekly-schedule.yml`

The weekly cron job has **zero failure alerting**. If it fails:
- Elders receive no prayer schedule
- Nobody is notified
- Could fail silently for weeks

**Action Items:**
- [ ] Add `if: failure()` step to workflow with email/Slack notification
- [ ] Add health monitoring (e.g., check if last successful run was within 9 days)
- [ ] Create GitHub issue on failure via `gh` CLI in workflow

---

### 4. `.gitignore` is Severely Incomplete
**Category:** Security | **File:** `.gitignore` (currently only ignores `__pycache__/`)

**Action Items:**
- [ ] Add to `.gitignore`:
  ```
  Prayer_Schedule_*.txt
  Prayer_Schedule_*.html
  archive/
  prayer_schedule_log.txt
  .env
  .env.local
  *.pyc
  .DS_Store
  ```

---

## P1 - HIGH (Fix Soon)

### 5. Monolithic 1041-Line Script Needs Modular Refactoring
**Category:** Architecture | **File:** `prayer_schedule_V10_DESKTOP_FIXED.py`

The entire application (config, data, algorithm, email, HTML/text generation, verification, orchestration) lives in one file.

**Recommended Module Structure:**
```
prayer_schedule/
  __init__.py
  config.py          # All configuration, elder data, email settings
  data.py            # CSV parsing, family directory management
  algorithm.py       # Pool creation, assignment logic, reassignment map
  output.py          # HTML and text schedule generation
  email_sender.py    # SMTP email delivery
  verification.py    # All verification/validation logic
  main.py            # CLI orchestration
```

**Action Items:**
- [ ] Create Python package structure with `__init__.py`
- [ ] Extract configuration to `config.py`
- [ ] Extract algorithm to `algorithm.py`
- [ ] Split `generate_schedule_content()` (233 lines) into separate HTML and text generators
- [ ] Move verification logic to dedicated module

---

### 6. Zero Unit Tests
**Category:** Testing | **File:** Project-wide (no test files exist)

The only "testing" is `verify_v10_algorithm()` which runs inside production code on every execution. There are no pytest/unittest files.

**Action Items:**
- [ ] Create `tests/` directory with pytest infrastructure
- [ ] Write unit tests for: pool distribution, family assignment, rotation guarantee
- [ ] Write unit tests for: year boundary handling, reassignment map coverage
- [ ] Write integration tests for: schedule generation, file archiving
- [ ] Add test stage to GitHub Actions workflow

---

### 7. Embedded 155-Family CSV Should Be Externalized
**Category:** Architecture | **File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 113-268

The complete church directory is a 156-line string literal embedded in the Python source code. Adding/removing a family requires editing Python source.

**Action Items:**
- [ ] Extract to `data/church_directory.csv`
- [ ] Update `parse_directory()` to load from file
- [ ] Add CSV schema validation (check required columns exist)
- [ ] Document how non-developers can update the family list

---

### 8. Elder Configuration Scattered Across 6+ Locations
**Category:** Maintainability | **File:** `prayer_schedule_V10_DESKTOP_FIXED.py`

Adding or removing an elder requires changes in **6 different places**:
1. `ELDERS` list (line 89)
2. `ELDER_FAMILIES` dict (line 101)
3. `get_week_schedule()` function (line 279)
4. `FIXED_REASSIGNMENT_MAP` (line 389)
5. `RECIPIENT_EMAILS` (line 75)
6. `README.md` documentation

**Action Items:**
- [ ] Create single `ELDERS_CONFIG` dictionary as source of truth
- [ ] Derive all other elder data structures from this single config
- [ ] Add startup validation that all elder config is consistent

---

### 9. Global Mutable State (`MASTER_POOLS`)
**Category:** Architecture | **File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 328-335

`MASTER_POOLS = None` is a global variable mutated lazily. This prevents isolated testing, creates hidden dependencies, and is not thread-safe.

**Action Items:**
- [ ] Replace global with dependency injection or class-based design
- [ ] Pass pools explicitly to functions that need them
- [ ] Enable isolated test cases with independent pool instances

---

### 10. Email Return Value Ignored; No Retry Logic
**Category:** Reliability | **File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 1023, 808-882

Line 1023 calls `send_email_schedule()` but **discards the return value**. If email fails, `main()` still returns `True` (success). No retry mechanism exists for transient SMTP failures.

**Action Items:**
- [ ] Capture and check email return value
- [ ] Add retry with exponential backoff for transient failures (3 retries)
- [ ] Distinguish credential errors (fail fast) from network errors (retry)
- [ ] Log email delivery status

---

### 11. `git add -A` in Workflow Commits Unintended Files
**Category:** Operations | **File:** `.github/workflows/weekly-schedule.yml` line 38

**Action Items:**
- [ ] Replace with explicit file list: `git add Prayer_Schedule_Current_Week.html Prayer_Schedule_Current_Week.txt`
- [ ] Or better: stop committing generated files entirely (see P0 item #4)

---

### 12. Manual Workflow Trigger Always Sends Emails
**Category:** Operations | **File:** `.github/workflows/weekly-schedule.yml` lines 7, 27

Cannot preview or test schedule generation without emailing all recipients.

**Action Items:**
- [ ] Add `workflow_dispatch` input for `email_enabled` (default: false for manual runs)
- [ ] Add `--dry-run` CLI flag to the Python script
- [ ] Support preview mode that generates files but skips email

---

## P2 - MEDIUM (Fix When Possible)

### 13. Bare `except:` Clauses and Silent Failures
**File:** `prayer_schedule_V10_DESKTOP_FIXED.py`

| Line | Issue |
|------|-------|
| 61 | `except:` catches ALL exceptions including KeyboardInterrupt, SystemExit |
| 918 | `except: pass` silently swallows all logging errors |

**Action Items:**
- [ ] Change line 61 to `except (OSError, KeyError) as e:`
- [ ] Change line 918 to `except Exception as e:` with stderr warning
- [ ] Audit all exception handlers for specificity

---

### 14. Incomplete Reassignment Map (Cycles 4 and 6)
**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 389-398

The `FIXED_REASSIGNMENT_MAP` covers cycles {0,1,2,3,5,7} but **omits {4,6}**. Currently cycles 4 and 6 have no filtering issues, so the fallback (line 408: `ELDERS[(owner_idx + 4) % 8]`) never triggers. This is a **latent bug** if data changes.

**Action Items:**
- [ ] Add explicit comments documenting why cycles 4 and 6 are omitted
- [ ] Or add empty entries: `4: {}, 6: {}` for clarity
- [ ] Or refactor to compute reassignment dynamically instead of using a static map

---

### 15. Helper Scripts Use Hard-Coded Absolute Paths
**Files:** `comprehensive_verification.py` line 17, `analyze_missing_coverage.py` line 6, `calc_reassignments.py` line 5

All use `sys.path.insert(0, '/home/user/prayer-schedule-automation')` which fails on any other system.

**Action Items:**
- [ ] Replace with relative imports via proper package structure
- [ ] Or use `os.path.dirname(os.path.abspath(__file__))` for dynamic path resolution

---

### 16. HTML Output Missing Mobile Responsiveness and Accessibility
**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 531-748

Missing:
- Viewport meta tag (`<meta name="viewport" ...>`)
- `lang="en"` attribute on `<html>` tag
- `scope="col"` on table headers
- Mobile breakpoints for small screens (2-column layout breaks on phones)
- Colorblind-friendly indicators (Monday uses only color highlighting)

**Action Items:**
- [ ] Add viewport meta tag
- [ ] Add `lang="en"` to html element
- [ ] Add table header scopes
- [ ] Add CSS media queries for mobile (< 768px: single column)
- [ ] Add text indicator for Monday: "Monday (2 Elders)"

---

### 17. Archive and Log Files Grow Unbounded
**Files:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 757-806 (archive), 911-919 (log)

No retention/cleanup policy exists for either.

**Action Items:**
- [ ] Add archive cleanup: delete files older than 1 year
- [ ] Implement log rotation (or use Python's `logging` module with `RotatingFileHandler`)

---

### 18. `main()` Function Does Too Much (10+ Responsibilities)
**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 954-1036

`main()` handles: verification, date calculation, assignment, validation, display, archiving, generation, file I/O, email, and logging.

**Action Items:**
- [ ] Break into: `verify_prerequisites()`, `generate_assignments()`, `output_schedule()`, `notify_elders()`
- [ ] Each sub-function should have single responsibility

---

### 19. Verification Runs Every Execution (Performance)
**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` line 961

Full 16-week verification runs every Monday before generating the schedule. If verification fails, no schedule is generated and no one is alerted.

**Action Items:**
- [ ] Move verification to CI test stage (separate workflow step)
- [ ] Or cache verification result with code hash
- [ ] Add alert if verification fails in production

---

### 20. Algorithm Locked to Exactly 8 Elders
**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 308-398

The pool creation, rotation, and reassignment map all assume exactly 8 elders. If the church gains or loses an elder, the entire algorithm breaks.

**Action Items:**
- [ ] Parameterize pool count based on `len(ELDERS)`
- [ ] Auto-compute reassignment map instead of hard-coding
- [ ] Document limitations and requirements for elder count changes

---

## P3 - LOW (Nice to Have)

### 21. Unused `week_number` Parameter
**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` line 279

`get_week_schedule(week_number)` ignores the parameter entirely. Same schedule every week.

**Action Items:**
- [ ] Remove parameter or document why it exists (future feature?)

---

### 22. Misleading `total_assignments` Variable
**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` lines 1000-1003

Counts elders (always 8) but name implies it counts family assignments (should be ~155).

**Action Items:**
- [ ] Rename to `num_elders` or change to sum family counts

---

### 23. No `requirements.txt` or `.env.example`
**Category:** Developer Experience

**Action Items:**
- [ ] Create `requirements.txt` documenting Python 3.11+ stdlib-only requirement
- [ ] Create `.env.example` with all required environment variables

---

### 24. HTML Auto-Refresh Doesn't Match Update Schedule
**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` line 536

Auto-refreshes every hour but schedule only changes weekly.

**Action Items:**
- [ ] Remove `meta http-equiv="refresh"` or set to weekly interval

---

### 25. Only `.txt` File Is Archived (Not `.html`)
**File:** `prayer_schedule_V10_DESKTOP_FIXED.py` line 762

`archive_previous_schedule()` only moves the `.txt` file. The HTML file is silently overwritten.

**Action Items:**
- [ ] Archive both `.txt` and `.html` formats

---

### 26. No CI Linting or Code Quality Checks
**File:** `.github/workflows/weekly-schedule.yml`

**Action Items:**
- [ ] Add pylint/flake8 step
- [ ] Add black formatting check
- [ ] Add mypy type checking (optional)

---

### 27. No Execution Summary in GitHub Actions
**File:** `.github/workflows/weekly-schedule.yml`

**Action Items:**
- [ ] Add `$GITHUB_STEP_SUMMARY` output showing: week number, families covered, email status

---

### 28. No Disaster Recovery Documentation
**Category:** Operations

**Action Items:**
- [ ] Document manual schedule creation process if system fails
- [ ] Document how to restore from archive
- [ ] Create succession plan for developer handoff

---

## Improvement Roadmap

### Phase 1: Critical Security & Bugs (Week 1)
- Fix `.gitignore` and remove PII from git tracking
- Fix ISO week 53 boundary bug
- Add CI failure notifications
- Remove hard-coded email addresses

### Phase 2: Architecture & Testing (Weeks 2-3)
- Refactor into Python package modules
- Externalize CSV directory
- Create unified elder configuration
- Build pytest test suite
- Add `--dry-run` flag

### Phase 3: Operations & UX (Week 4)
- Add mobile responsive CSS
- Fix accessibility issues
- Implement log rotation and archive cleanup
- Add workflow execution summaries

### Phase 4: Future-Proofing (Ongoing)
- Parameterize algorithm for variable elder count
- Auto-compute reassignment map
- Create admin guide for non-developers
- Implement email retry logic

---

## Agent Analysis Credits

| Agent | Focus Area | Issues Found |
|-------|-----------|-------------|
| Agent 1 | Architecture & Code Organization | 22 issues |
| Agent 2 | Testing & Reliability | 20 issues |
| Agent 3 | Algorithm Correctness | 8 issues (2 verified correct) |
| Agent 4 | Security & Configuration | 14 issues |
| Agent 5 | CI/CD & Operations | 11 issues |
| Agent 6 | Maintainability & UX | 15 issues |
