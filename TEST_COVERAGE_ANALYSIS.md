# Test Coverage Analysis

## Current State

The project has two layers of verification:

1. **Built-in verification** (`verify_v10_algorithm()` at line 506 of the main script) - runs on every execution
2. **External verification** (`comprehensive_verification.py`) - a standalone test suite

Both focus exclusively on the **core scheduling algorithm**. Everything else - email delivery, file I/O, HTML generation, CI/CD workflows - has zero automated test coverage.

**Estimated overall coverage: ~40% of code paths**

---

## What IS Well Tested

| Area | What's Verified | Where |
|------|----------------|-------|
| Pool distribution | 161 families split into 8 pools (21/20/20/..) | `comprehensive_verification.py:43-55` |
| Family count per elder | 19-21 families per elder, every week | `comprehensive_verification.py:143-152` |
| No self-assignment | No elder prays for their own family | `comprehensive_verification.py:134-141` |
| No duplicates | Each family assigned to exactly 1 elder per week | `comprehensive_verification.py:116-131` |
| 100% coverage | All 161 families assigned every week | `comprehensive_verification.py:78-114` |
| Week-to-week rotation | 100% new families for each elder every consecutive week | `comprehensive_verification.py:191-217` |
| 8-week cycle | Assignments repeat exactly after 8 weeks | `comprehensive_verification.py:166-189` |
| Year boundaries | Continuous rotation across 4 year transitions (2025-2029) | `comprehensive_verification.py:235-324` |

These tests are solid and cover the algorithm thoroughly across 10+ weeks and multiple year boundaries.

---

## Coverage Gaps (Ranked by Severity)

### 1. CRITICAL: Email Delivery System (0% coverage)

**Functions:** `send_daily_combined_email()` (line 1309), `_build_combined_email_html()` (line 1131)

This is the primary output of the system - if emails don't send, the project fails its purpose. Yet nothing is tested:

- **SMTP connection/auth** (lines 1415-1420): No test for connection failure, auth failure, TLS errors, or timeouts
- **Recipient parsing** (line 1332): `RECIPIENT_EMAILS.split(',')` is untested with malformed input (trailing commas, whitespace, empty string)
- **Email content assembly** (lines 1385-1410): MIMEMultipart message construction is never validated
- **Error handling paths** (lines 1430-1440): `SMTPAuthenticationError`, `SMTPException`, and generic `Exception` handlers are never exercised
- **Date verification gate** (lines 1339-1343): `verify_email_date()` blocks sending on date mismatch, but this interaction is untested

**Recommendation:** Add mock-based tests using `unittest.mock.patch` on `smtplib.SMTP`. Test the happy path (email sends successfully), auth failure, network error, empty recipient list, and date verification rejection. No live Gmail account needed.

### 2. HIGH: HTML Output Has No XSS Protection

**Function:** `generate_schedule_content()` (line 614)

Family names from `DIRECTORY_CSV` are interpolated directly into HTML without escaping. If a name contained `<script>` or `"onclick=`, it would render as live HTML on the GitHub Pages site.

- Lines 614-1022 generate raw HTML with f-strings; no `html.escape()` is used
- The email HTML builder (`_build_combined_email_html()`, line 1131) also lacks escaping

**Current risk is low** since the directory data is hardcoded by a trusted admin, but this is a latent vulnerability if the data source ever changes.

**Recommendation:** Add a test that verifies `generate_schedule_content()` properly handles special characters (`<`, `>`, `&`, `"`, `'`) in family names. Then add `html.escape()` calls to the generation functions.

### 3. HIGH: `main()` Orchestration Logic (0% coverage)

**Function:** `main()` (line 1512)

The ~190-line `main()` function is the orchestrator but is never tested in isolation:

- **Monday vs. non-Monday branching** (line 1603): Archive is only called on Monday, but this path is untested
- **Return value inconsistency**: Line 1612 returns `False` on warning, but line 1622 returns `True` even if email sending fails - this inconsistency is never caught by tests
- **Graceful degradation**: What happens if `assign_families_for_week_v10()` returns an empty dict? If `generate_schedule_content()` raises? These error paths are unverified

**Recommendation:** Create scenario tests that call `main()` with mocked I/O and verify correct behavior for: normal Monday run, normal weekday run, email failure, file write failure.

### 4. HIGH: File I/O and Archive Operations (0% coverage)

**Functions:** `update_desktop_files()` (line 1442), `archive_previous_schedule()` (line 1024)

- **`update_desktop_files()`**: Write failures are caught by try/except (lines 1451-1467) but never tested. Permission errors, missing directories, and disk-full scenarios are unverified
- **`archive_previous_schedule()`**: Regex extraction of week number from filename (line 1041, pattern `r'WEEK (\d+)'`) is never tested. Race conditions between file existence check and file copy/remove are possible but untested

**Recommendation:** Use `tempfile` and mocked file systems to test write success, write failure, archive with valid/invalid filenames, and missing source files.

### 5. MEDIUM: `verify_email_date()` DST Edge Cases

**Function:** `verify_email_date()` (line 118)

The function compares today's date against expected email dates but:

- **DST spring-forward/fall-back transitions** are untested. During the spring-forward transition (e.g., 2 AM CDT skip), a midnight comparison could yield unexpected results
- The function uses `CENTRAL_TZ` via `zoneinfo`, which handles DST correctly in theory, but no test confirms this behavior at transition boundaries

**Recommendation:** Add tests with dates at DST boundaries: March second Sunday (spring forward) and November first Sunday (fall back), specifically testing times near the 2 AM transition.

### 6. MEDIUM: Reassignment Map Completeness

**Function:** `assign_families_for_week_v10()` (line 420), specifically `FIXED_REASSIGNMENT_MAP` (line 480)

Current tests verify that reassignments work correctly for all 8 cycle positions, but:

- **No explicit test** that cycle positions 0, 2, and 3 genuinely have zero conflicts (the map intentionally excludes them, but this invariant isn't asserted)
- **Fallback logic** at line 498-499 (`best_elder = ELDERS[(owner_idx + 4) % len(ELDERS)]`) is dead code under normal operation. If it ever triggers, there's no test to verify it maintains the 19-21 family count and no-repeat constraints
- **Family count sensitivity**: If families are added/removed from `DIRECTORY_CSV`, the map could become invalid. No test checks the map against the actual directory

**Recommendation:** Add an explicit test that: (a) confirms cycle positions 0, 2, 3 have no elder-own-family conflicts, (b) validates the reassignment map against the current family directory, and (c) exercises the fallback path with a deliberately incomplete map.

### 7. MEDIUM: CI Workflow Behavior

**File:** `.github/workflows/weekly-schedule.yml`

- **Secret propagation**: If `SENDER_PASSWORD` is unset, the script falls back to hardcoded emails (lines 87-100 of main script). This fallback is never tested in CI
- **Failure issue creation** (workflow lines 71-85): The `if: failure()` step creates/comments on GitHub issues, but this path is never validated
- **Manual dispatch**: `send_emails` input defaults to `false` but the interaction between this input and `EMAIL_ENABLED` env var is untested

**Recommendation:** Add a workflow that runs on PRs in `--dry-run` mode (no emails, no file commits) to validate the script executes without errors on every change.

### 8. LOW: `parse_directory()` Robustness

**Function:** `parse_directory()` (line 333)

Since `DIRECTORY_CSV` is a hardcoded string constant, parsing is unlikely to fail. However:

- Empty CSV, missing columns, or whitespace-only names are never tested
- The sort order assumption (alphabetical) is verified implicitly but never explicitly asserted

**Recommendation:** Low priority. Add a simple assertion that `parse_directory()` returns exactly 161 sorted, non-empty strings.

### 9. LOW: `get_week_schedule()` Static Mapping

**Function:** `get_week_schedule()` (line 342)

- Returns a fixed day-to-elder mapping. No test verifies the mapping has exactly 8 elder slots (Monday=2, Tue-Sun=1 each)
- If an elder name is misspelled in this function vs. the `ELDERS` list, assignments would silently fail

**Recommendation:** Add a test that verifies every elder name in `get_week_schedule()` output exists in the `ELDERS` list, and that exactly 8 slots are filled per week.

---

## Summary of Recommended Actions

| Priority | Action | Effort |
|----------|--------|--------|
| Critical | Add mock SMTP tests for `send_daily_combined_email()` | Medium |
| High | Add HTML escaping + tests for `generate_schedule_content()` | Low |
| High | Add scenario tests for `main()` with mocked I/O | Medium |
| High | Add file I/O tests for `update_desktop_files()` and `archive_previous_schedule()` | Medium |
| Medium | Add DST boundary tests for `verify_email_date()` | Low |
| Medium | Add reassignment map completeness assertions | Low |
| Medium | Add CI dry-run workflow for PR validation | Low |
| Low | Add `parse_directory()` and `get_week_schedule()` sanity checks | Trivial |

The core algorithm is well-tested. The biggest risk is in the **untested delivery pipeline** (email + file I/O + CI) - the parts that actually get the schedule to people.
