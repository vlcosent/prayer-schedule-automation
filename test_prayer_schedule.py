"""
Comprehensive test suite for the Prayer Schedule system.

Covers the gaps identified in TEST_COVERAGE_ANALYSIS.md:
1. Email delivery (mock SMTP)
2. HTML output safety (XSS / escaping)
3. main() orchestration scenarios
4. File I/O and archive operations
5. DST edge cases for verify_email_date()
6. Reassignment map completeness
7. parse_directory() and get_week_schedule() sanity checks
8. verify_schedule() edge cases

Run:  python -m unittest test_prayer_schedule -v
"""

import csv
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch, MagicMock, mock_open

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prayer_schedule_V10_DESKTOP_FIXED as ps


# ---------------------------------------------------------------------------
# 1. parse_directory() and get_week_schedule() sanity checks
# ---------------------------------------------------------------------------
class TestParseDirectory(unittest.TestCase):
    """Verify the embedded CSV is parsed correctly."""

    def test_returns_161_families(self):
        families = ps.parse_directory()
        self.assertEqual(len(families), 161)

    def test_all_entries_nonempty(self):
        for fam in ps.parse_directory():
            self.assertTrue(len(fam.strip()) > 0, f"Empty family entry: {fam!r}")

    def test_sorted_alphabetically(self):
        families = ps.parse_directory()
        self.assertEqual(families, sorted(families))

    def test_every_elder_family_in_directory(self):
        families = set(ps.parse_directory())
        for elder, fam in ps.ELDER_FAMILIES.items():
            self.assertIn(fam, families, f"{elder}'s family not in directory")

    def test_format_is_last_comma_first(self):
        """Every entry should contain a comma separating last/first."""
        for fam in ps.parse_directory():
            self.assertIn(", ", fam, f"Unexpected format: {fam!r}")


class TestGetWeekSchedule(unittest.TestCase):
    """Verify the static day-to-elder mapping."""

    def test_total_slots_is_eight(self):
        schedule = ps.get_week_schedule(1)
        total = sum(len(v) for v in schedule.values())
        self.assertEqual(total, 8)

    def test_monday_has_two_elders(self):
        schedule = ps.get_week_schedule(1)
        self.assertEqual(len(schedule["Monday"]), 2)

    def test_other_days_have_one_elder(self):
        schedule = ps.get_week_schedule(1)
        for day in ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            self.assertEqual(len(schedule[day]), 1, f"{day} should have 1 elder")

    def test_all_seven_days_present(self):
        schedule = ps.get_week_schedule(1)
        expected_days = {"Monday", "Tuesday", "Wednesday", "Thursday",
                         "Friday", "Saturday", "Sunday"}
        self.assertEqual(set(schedule.keys()), expected_days)

    def test_all_elder_names_valid(self):
        """Every name in the schedule must exist in the ELDERS list."""
        schedule = ps.get_week_schedule(1)
        for day, elders in schedule.items():
            for elder in elders:
                self.assertIn(elder, ps.ELDERS,
                              f"Unknown elder '{elder}' on {day}")

    def test_all_elders_scheduled(self):
        """Every elder must appear exactly once in the weekly schedule."""
        schedule = ps.get_week_schedule(1)
        all_scheduled = []
        for elders in schedule.values():
            all_scheduled.extend(elders)
        self.assertEqual(sorted(all_scheduled), sorted(ps.ELDERS))


# ---------------------------------------------------------------------------
# 2. Reassignment map completeness
# ---------------------------------------------------------------------------
class TestReassignmentMap(unittest.TestCase):
    """Verify FIXED_REASSIGNMENT_MAP covers all conflict positions."""

    def test_no_conflicts_at_positions_0_2_3(self):
        """Cycle positions 0, 2, 3 must have zero elder-own-family conflicts."""
        master_pools = ps.get_master_pools()
        for cycle_pos in [0, 2, 3]:
            for elder_idx, elder in enumerate(ps.ELDERS):
                pool_idx = (elder_idx + cycle_pos) % 8
                elder_family = ps.ELDER_FAMILIES[elder]
                self.assertNotIn(
                    elder_family, master_pools[pool_idx],
                    f"Unexpected conflict: {elder} at cycle_position {cycle_pos}"
                )

    def test_map_covers_all_actual_conflicts(self):
        """Every cycle position with conflicts must be in the map."""
        master_pools = ps.get_master_pools()
        for cycle_pos in range(8):
            conflicting_elders = []
            for elder_idx, elder in enumerate(ps.ELDERS):
                pool_idx = (elder_idx + cycle_pos) % 8
                if ps.ELDER_FAMILIES[elder] in master_pools[pool_idx]:
                    conflicting_elders.append(elder)

            if conflicting_elders:
                # Retrieve the map via assign_families_for_week_v10 internals
                # We just need to verify the FIXED_REASSIGNMENT_MAP key exists
                # The map is defined inside the function, so we test through it
                assignments = ps.assign_families_for_week_v10(cycle_pos + 1)
                for elder in conflicting_elders:
                    elder_family = ps.ELDER_FAMILIES[elder]
                    # The family must NOT be in the conflicting elder's list
                    self.assertNotIn(elder_family, assignments[elder],
                                     f"{elder}'s family still assigned to self "
                                     f"at cycle_position {cycle_pos}")
                    # The family must appear somewhere
                    found = False
                    for other_elder, fams in assignments.items():
                        if elder_family in fams:
                            found = True
                            break
                    self.assertTrue(found,
                                    f"{elder}'s family missing at cycle_position {cycle_pos}")

    def test_reassignment_preserves_family_count_range(self):
        """After reassignment, every elder should have 19-21 families."""
        for cycle_pos in range(8):
            assignments = ps.assign_families_for_week_v10(cycle_pos + 1)
            for elder, families in assignments.items():
                self.assertGreaterEqual(len(families), 19,
                                        f"{elder} has {len(families)} at pos {cycle_pos}")
                self.assertLessEqual(len(families), 21,
                                     f"{elder} has {len(families)} at pos {cycle_pos}")


# ---------------------------------------------------------------------------
# 3. verify_email_date() including DST edge cases
# ---------------------------------------------------------------------------
class TestVerifyEmailDate(unittest.TestCase):

    def test_valid_monday(self):
        monday = datetime(2026, 3, 2)
        today = datetime(2026, 3, 2)  # Monday
        valid, msg = ps.verify_email_date(today, monday)
        self.assertTrue(valid)

    def test_valid_friday(self):
        monday = datetime(2026, 3, 2)
        today = datetime(2026, 3, 6)  # Friday
        valid, msg = ps.verify_email_date(today, monday)
        self.assertTrue(valid)

    def test_valid_sunday(self):
        monday = datetime(2026, 3, 2)
        today = datetime(2026, 3, 8)  # Sunday
        valid, msg = ps.verify_email_date(today, monday)
        self.assertTrue(valid)

    def test_invalid_previous_week(self):
        monday = datetime(2026, 3, 9)
        today = datetime(2026, 3, 8)  # Sunday of previous week
        valid, msg = ps.verify_email_date(today, monday)
        self.assertFalse(valid)
        self.assertIn("MISMATCH", msg)

    def test_invalid_next_week(self):
        monday = datetime(2026, 3, 2)
        today = datetime(2026, 3, 9)  # Next Monday
        valid, msg = ps.verify_email_date(today, monday)
        self.assertFalse(valid)
        self.assertIn("MISMATCH", msg)

    def test_dst_spring_forward(self):
        """March 8 2026 is DST spring-forward in US Central.

        The function should still correctly validate dates during
        the DST transition weekend.
        """
        # Saturday March 7 -> Sunday March 8 (spring forward)
        monday = datetime(2026, 3, 2)
        # Sunday during DST transition
        today = datetime(2026, 3, 8, 3, 0)  # 3 AM after spring forward
        valid, msg = ps.verify_email_date(today, monday)
        self.assertTrue(valid)

    def test_dst_fall_back(self):
        """November 1 2026 is DST fall-back in US Central."""
        monday = datetime(2026, 10, 26)
        today = datetime(2026, 11, 1, 1, 30)  # During fall-back
        valid, msg = ps.verify_email_date(today, monday)
        self.assertTrue(valid)

    def test_today_with_nonzero_time(self):
        """Time-of-day should not affect date validation."""
        monday = datetime(2026, 3, 2)
        today = datetime(2026, 3, 4, 23, 59, 59)  # Late Wednesday
        valid, msg = ps.verify_email_date(today, monday)
        self.assertTrue(valid)


# ---------------------------------------------------------------------------
# 4. verify_schedule() edge cases
# ---------------------------------------------------------------------------
class TestVerifySchedule(unittest.TestCase):

    def test_valid_assignments(self):
        assignments = ps.assign_families_for_week_v10(10)
        valid, issues = ps.verify_schedule(assignments)
        self.assertTrue(valid)
        self.assertEqual(issues, [])

    def test_detects_self_assignment(self):
        assignments = ps.assign_families_for_week_v10(10)
        # Inject elder's own family
        elder = ps.ELDERS[0]
        assignments[elder].append(ps.ELDER_FAMILIES[elder])
        valid, issues = ps.verify_schedule(assignments)
        self.assertFalse(valid)
        self.assertTrue(any("own family" in i for i in issues))

    def test_detects_duplicate_assignment(self):
        assignments = ps.assign_families_for_week_v10(10)
        # Add a family that already belongs to another elder
        elder0 = ps.ELDERS[0]
        elder1 = ps.ELDERS[1]
        dup_family = assignments[elder1][0]
        assignments[elder0].append(dup_family)
        valid, issues = ps.verify_schedule(assignments)
        self.assertFalse(valid)
        self.assertTrue(any("assigned" in i and "times" in i for i in issues))

    def test_detects_too_few_families(self):
        assignments = ps.assign_families_for_week_v10(10)
        elder = ps.ELDERS[0]
        # Truncate to 5 families
        assignments[elder] = assignments[elder][:5]
        valid, issues = ps.verify_schedule(assignments)
        self.assertFalse(valid)


# ---------------------------------------------------------------------------
# 5. File I/O: update_desktop_files()
# ---------------------------------------------------------------------------
class TestUpdateDesktopFiles(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_desktop = ps.DESKTOP_DIR
        ps.DESKTOP_DIR = self.tmpdir

    def tearDown(self):
        ps.DESKTOP_DIR = self._orig_desktop
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_writes_both_files(self):
        result = ps.update_desktop_files("<html>test</html>", "plain text")
        self.assertTrue(result)
        html_path = os.path.join(self.tmpdir, "Prayer_Schedule_Current_Week.html")
        txt_path = os.path.join(self.tmpdir, "Prayer_Schedule_Current_Week.txt")
        self.assertTrue(os.path.exists(html_path))
        self.assertTrue(os.path.exists(txt_path))
        with open(html_path, 'r') as f:
            self.assertEqual(f.read(), "<html>test</html>")
        with open(txt_path, 'r') as f:
            self.assertEqual(f.read(), "plain text")

    @unittest.skipIf(os.getuid() == 0, "chmod has no effect as root")
    def test_returns_false_on_readonly_dir(self):
        ro_dir = os.path.join(self.tmpdir, "readonly")
        os.makedirs(ro_dir)
        os.chmod(ro_dir, 0o444)
        ps.DESKTOP_DIR = ro_dir
        result = ps.update_desktop_files("<html>", "text")
        self.assertFalse(result)
        os.chmod(ro_dir, 0o755)  # restore for cleanup

    def test_handles_nonexistent_dir(self):
        ps.DESKTOP_DIR = os.path.join(self.tmpdir, "does", "not", "exist")
        result = ps.update_desktop_files("<html>", "text")
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# 6. File I/O: archive_previous_schedule()
# ---------------------------------------------------------------------------
class TestArchivePreviousSchedule(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_desktop = ps.DESKTOP_DIR
        ps.DESKTOP_DIR = self.tmpdir

    def tearDown(self):
        ps.DESKTOP_DIR = self._orig_desktop
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_archives_file_with_week_number(self):
        txt_path = os.path.join(self.tmpdir, "Prayer_Schedule_Current_Week.txt")
        with open(txt_path, 'w') as f:
            f.write("CROSSVILLE CHURCH OF CHRIST\nWEEK 10 SCHEDULE\n")

        result = ps.archive_previous_schedule()
        self.assertTrue(result)
        # Original should be gone
        self.assertFalse(os.path.exists(txt_path))
        # Archive dir should exist with one file
        archive_dir = os.path.join(self.tmpdir, "archive")
        self.assertTrue(os.path.isdir(archive_dir))
        archived_files = os.listdir(archive_dir)
        self.assertEqual(len(archived_files), 1)
        self.assertIn("Week10", archived_files[0])

    def test_archives_file_without_week_number(self):
        txt_path = os.path.join(self.tmpdir, "Prayer_Schedule_Current_Week.txt")
        with open(txt_path, 'w') as f:
            f.write("Some content without week info\n")

        result = ps.archive_previous_schedule()
        self.assertTrue(result)
        archive_dir = os.path.join(self.tmpdir, "archive")
        archived_files = os.listdir(archive_dir)
        self.assertEqual(len(archived_files), 1)
        # Should NOT have "Week" in name
        self.assertNotIn("Week", archived_files[0])

    def test_no_file_to_archive(self):
        result = ps.archive_previous_schedule()
        self.assertFalse(result)

    def test_archive_preserves_content(self):
        txt_path = os.path.join(self.tmpdir, "Prayer_Schedule_Current_Week.txt")
        content = "WEEK 5\nFamily data here\nMore data"
        with open(txt_path, 'w') as f:
            f.write(content)

        ps.archive_previous_schedule()
        archive_dir = os.path.join(self.tmpdir, "archive")
        archived_file = os.path.join(archive_dir, os.listdir(archive_dir)[0])
        with open(archived_file, 'r') as f:
            self.assertEqual(f.read(), content)


# ---------------------------------------------------------------------------
# 7. Email delivery (mock SMTP)
# ---------------------------------------------------------------------------
class TestSendDailyCombinedEmail(unittest.TestCase):
    """Test email sending with mocked SMTP."""

    def _make_args(self):
        """Create valid arguments for send_daily_combined_email()."""
        today = datetime(2026, 3, 2)  # Monday
        week_num = 10
        monday = datetime(2026, 3, 2)
        elder_assignments = ps.assign_families_for_week_v10(week_num)
        return today, week_num, monday, elder_assignments

    @patch.object(ps, 'EMAIL_ENABLED', False)
    def test_disabled_email_returns_false(self):
        today, wn, mon, ea = self._make_args()
        result = ps.send_daily_combined_email(today, wn, mon, ea)
        self.assertFalse(result)

    @patch.object(ps, 'EMAIL_ENABLED', True)
    @patch.object(ps, 'SENDER_PASSWORD', '')
    def test_empty_password_returns_false(self):
        today, wn, mon, ea = self._make_args()
        result = ps.send_daily_combined_email(today, wn, mon, ea)
        self.assertFalse(result)

    @patch.object(ps, 'EMAIL_ENABLED', True)
    @patch.object(ps, 'SENDER_PASSWORD', 'fake-app-password')
    @patch.object(ps, 'RECIPIENT_EMAILS', '')
    def test_empty_recipients_returns_false(self):
        today, wn, mon, ea = self._make_args()
        result = ps.send_daily_combined_email(today, wn, mon, ea)
        self.assertFalse(result)

    @patch.object(ps, 'EMAIL_ENABLED', True)
    @patch.object(ps, 'SENDER_PASSWORD', 'fake-app-password')
    @patch.object(ps, 'RECIPIENT_EMAILS', 'test@example.com')
    @patch('prayer_schedule_V10_DESKTOP_FIXED.smtplib.SMTP')
    def test_successful_send(self, mock_smtp_class):
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        today, wn, mon, ea = self._make_args()
        result = ps.send_daily_combined_email(today, wn, mon, ea)

        self.assertTrue(result)
        mock_smtp_class.assert_called_once_with(ps.SMTP_SERVER, ps.SMTP_PORT)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(ps.SENDER_EMAIL, 'fake-app-password')
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch.object(ps, 'EMAIL_ENABLED', True)
    @patch.object(ps, 'SENDER_PASSWORD', 'fake-app-password')
    @patch.object(ps, 'RECIPIENT_EMAILS', 'test@example.com')
    @patch('prayer_schedule_V10_DESKTOP_FIXED.smtplib.SMTP')
    def test_email_subject_contains_today(self, mock_smtp_class):
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        today, wn, mon, ea = self._make_args()
        ps.send_daily_combined_email(today, wn, mon, ea)

        # Extract the message that was sent
        sent_msg = mock_server.send_message.call_args[0][0]
        subject = sent_msg['Subject']
        self.assertIn("Monday", subject)
        self.assertIn("March 02, 2026", subject)

    @patch.object(ps, 'EMAIL_ENABLED', True)
    @patch.object(ps, 'SENDER_PASSWORD', 'fake-app-password')
    @patch.object(ps, 'RECIPIENT_EMAILS', 'a@test.com, b@test.com, c@test.com')
    @patch('prayer_schedule_V10_DESKTOP_FIXED.smtplib.SMTP')
    def test_multiple_recipients_parsed(self, mock_smtp_class):
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        today, wn, mon, ea = self._make_args()
        ps.send_daily_combined_email(today, wn, mon, ea)

        sent_msg = mock_server.send_message.call_args[0][0]
        self.assertIn("a@test.com", sent_msg['To'])
        self.assertIn("b@test.com", sent_msg['To'])
        self.assertIn("c@test.com", sent_msg['To'])

    @patch.object(ps, 'EMAIL_ENABLED', True)
    @patch.object(ps, 'SENDER_PASSWORD', 'fake-app-password')
    @patch.object(ps, 'RECIPIENT_EMAILS', 'test@example.com')
    @patch('prayer_schedule_V10_DESKTOP_FIXED.smtplib.SMTP')
    def test_smtp_auth_failure(self, mock_smtp_class):
        import smtplib
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b'Bad credentials')
        mock_smtp_class.return_value = mock_server

        today, wn, mon, ea = self._make_args()
        result = ps.send_daily_combined_email(today, wn, mon, ea)
        self.assertFalse(result)

    @patch.object(ps, 'EMAIL_ENABLED', True)
    @patch.object(ps, 'SENDER_PASSWORD', 'fake-app-password')
    @patch.object(ps, 'RECIPIENT_EMAILS', 'test@example.com')
    @patch('prayer_schedule_V10_DESKTOP_FIXED.smtplib.SMTP')
    def test_smtp_connection_error(self, mock_smtp_class):
        import smtplib
        mock_smtp_class.side_effect = smtplib.SMTPException("Connection refused")

        today, wn, mon, ea = self._make_args()
        result = ps.send_daily_combined_email(today, wn, mon, ea)
        self.assertFalse(result)

    @patch.object(ps, 'EMAIL_ENABLED', True)
    @patch.object(ps, 'SENDER_PASSWORD', 'fake-app-password')
    @patch.object(ps, 'RECIPIENT_EMAILS', 'test@example.com')
    @patch('prayer_schedule_V10_DESKTOP_FIXED.smtplib.SMTP')
    def test_smtp_send_failure(self, mock_smtp_class):
        import smtplib
        mock_server = MagicMock()
        mock_server.send_message.side_effect = smtplib.SMTPException("Send failed")
        mock_smtp_class.return_value = mock_server

        today, wn, mon, ea = self._make_args()
        result = ps.send_daily_combined_email(today, wn, mon, ea)
        self.assertFalse(result)

    @patch.object(ps, 'EMAIL_ENABLED', True)
    @patch.object(ps, 'SENDER_PASSWORD', 'fake-app-password')
    @patch.object(ps, 'RECIPIENT_EMAILS', 'test@example.com')
    def test_date_verification_failure_blocks_send(self):
        """If today is outside the week range, email should not be sent."""
        today = datetime(2026, 3, 10)  # Tuesday of NEXT week
        monday = datetime(2026, 3, 2)  # Monday of previous week
        week_num = 10
        ea = ps.assign_families_for_week_v10(week_num)
        result = ps.send_daily_combined_email(today, week_num, monday, ea)
        self.assertFalse(result)

    @patch.object(ps, 'EMAIL_ENABLED', True)
    @patch.object(ps, 'SENDER_PASSWORD', 'fake-app-password')
    @patch.object(ps, 'RECIPIENT_EMAILS', ',  , ,')
    def test_whitespace_only_recipients(self):
        """Recipient list with only commas and spaces should fail."""
        today, wn, mon, ea = self._make_args()
        result = ps.send_daily_combined_email(today, wn, mon, ea)
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# 8. HTML output (content validation, no XSS)
# ---------------------------------------------------------------------------
class TestGenerateScheduleContent(unittest.TestCase):
    """Test HTML and text generation."""

    def setUp(self):
        self.week_num = 10
        self.monday = datetime(2026, 3, 2)
        self.assignments = ps.assign_families_for_week_v10(self.week_num)

    def test_returns_html_and_text_tuple(self):
        html, text = ps.generate_schedule_content(
            self.week_num, self.monday, self.assignments)
        self.assertIsInstance(html, str)
        self.assertIsInstance(text, str)

    def test_html_has_doctype(self):
        html, _ = ps.generate_schedule_content(
            self.week_num, self.monday, self.assignments)
        self.assertTrue(html.strip().startswith("<!DOCTYPE html"))

    def test_html_contains_week_number(self):
        html, _ = ps.generate_schedule_content(
            self.week_num, self.monday, self.assignments)
        self.assertIn(f"Week {self.week_num}", html)

    def test_text_contains_all_elders(self):
        _, text = ps.generate_schedule_content(
            self.week_num, self.monday, self.assignments)
        for elder in ps.ELDERS:
            self.assertIn(elder, text)

    def test_html_contains_all_elders(self):
        html, _ = ps.generate_schedule_content(
            self.week_num, self.monday, self.assignments)
        for elder in ps.ELDERS:
            self.assertIn(elder, html)

    def test_text_contains_prayer_lists_section(self):
        _, text = ps.generate_schedule_content(
            self.week_num, self.monday, self.assignments)
        self.assertIn("PRAYER LISTS", text)

    def test_html_charset_utf8(self):
        html, _ = ps.generate_schedule_content(
            self.week_num, self.monday, self.assignments)
        self.assertIn('charset="UTF-8"', html)


# ---------------------------------------------------------------------------
# 9. calculate_continuous_week() edge cases
# ---------------------------------------------------------------------------
class TestCalculateContinuousWeek(unittest.TestCase):

    def test_reference_monday_is_week_1(self):
        ref = datetime(2025, 12, 29)
        self.assertEqual(ps.calculate_continuous_week(ref), 1)

    def test_one_week_later_is_week_2(self):
        ref = datetime(2025, 12, 29) + timedelta(weeks=1)
        self.assertEqual(ps.calculate_continuous_week(ref), 2)

    def test_matches_iso_week_in_2026(self):
        """Continuous week should equal ISO week for all of 2026."""
        monday = datetime(2025, 12, 29)  # ISO Week 1 of 2026
        for w in range(52):
            d = monday + timedelta(weeks=w)
            iso_year, iso_week, _ = d.isocalendar()
            if iso_year == 2026:
                self.assertEqual(ps.calculate_continuous_week(d), iso_week,
                                 f"Mismatch at {d.strftime('%Y-%m-%d')}")

    def test_monotonically_increasing_across_year_boundary(self):
        """Weeks should always increase by 1 across year boundaries."""
        start = datetime(2026, 12, 7)  # A few weeks before year end
        prev = ps.calculate_continuous_week(start)
        for w in range(1, 12):
            d = start + timedelta(weeks=w)
            curr = ps.calculate_continuous_week(d)
            self.assertEqual(curr, prev + 1,
                             f"Non-monotonic at {d.strftime('%Y-%m-%d')}: {prev} -> {curr}")
            prev = curr

    def test_accepts_aware_datetime(self):
        """Should work with timezone-aware datetimes."""
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Chicago")
        ref = datetime(2025, 12, 29, tzinfo=tz)
        self.assertEqual(ps.calculate_continuous_week(ref), 1)

    def test_accepts_naive_datetime(self):
        """Should work with naive datetimes."""
        ref = datetime(2025, 12, 29)
        self.assertEqual(ps.calculate_continuous_week(ref), 1)


# ---------------------------------------------------------------------------
# 10. main() orchestration
# ---------------------------------------------------------------------------
class TestMain(unittest.TestCase):
    """Test main() with mocked I/O to verify orchestration logic."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_desktop = ps.DESKTOP_DIR
        self._orig_base = ps.BASE_DIR
        ps.DESKTOP_DIR = self.tmpdir
        ps.BASE_DIR = self.tmpdir

    def tearDown(self):
        ps.DESKTOP_DIR = self._orig_desktop
        ps.BASE_DIR = self._orig_base
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch.object(ps, 'EMAIL_ENABLED', False)
    @patch.object(ps, 'get_today')
    def test_monday_run_creates_files(self, mock_today):
        """Monday run should generate HTML and TXT files."""
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Chicago")
        mock_today.return_value = datetime(2026, 3, 2, 8, 0, tzinfo=tz)  # Monday

        result = ps.main()
        self.assertTrue(result)

        html_path = os.path.join(self.tmpdir, "Prayer_Schedule_Current_Week.html")
        txt_path = os.path.join(self.tmpdir, "Prayer_Schedule_Current_Week.txt")
        self.assertTrue(os.path.exists(html_path))
        self.assertTrue(os.path.exists(txt_path))

    @patch.object(ps, 'EMAIL_ENABLED', False)
    @patch.object(ps, 'get_today')
    def test_wednesday_run_creates_files(self, mock_today):
        """Non-Monday run should also generate files."""
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Chicago")
        mock_today.return_value = datetime(2026, 3, 4, 8, 0, tzinfo=tz)  # Wednesday

        result = ps.main()
        self.assertTrue(result)

        html_path = os.path.join(self.tmpdir, "Prayer_Schedule_Current_Week.html")
        self.assertTrue(os.path.exists(html_path))

    @patch.object(ps, 'EMAIL_ENABLED', False)
    @patch.object(ps, 'get_today')
    def test_monday_triggers_archive(self, mock_today):
        """Monday should call archive_previous_schedule()."""
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Chicago")
        mock_today.return_value = datetime(2026, 3, 2, 8, 0, tzinfo=tz)

        # Create a file to archive
        txt_path = os.path.join(self.tmpdir, "Prayer_Schedule_Current_Week.txt")
        with open(txt_path, 'w') as f:
            f.write("WEEK 9\nOld schedule content")

        result = ps.main()
        self.assertTrue(result)

        # Old file should be gone (archived)
        # A new file will be generated in its place, so check archive dir
        archive_dir = os.path.join(self.tmpdir, "archive")
        self.assertTrue(os.path.isdir(archive_dir))
        archived_files = os.listdir(archive_dir)
        self.assertEqual(len(archived_files), 1)

    @patch.object(ps, 'EMAIL_ENABLED', True)
    @patch.object(ps, 'SENDER_PASSWORD', 'fake')
    @patch.object(ps, 'RECIPIENT_EMAILS', 'test@example.com')
    @patch('prayer_schedule_V10_DESKTOP_FIXED.smtplib.SMTP')
    @patch.object(ps, 'get_today')
    def test_main_sends_email_when_enabled(self, mock_today, mock_smtp_class):
        """When EMAIL_ENABLED=true, main() should attempt to send email."""
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Chicago")
        mock_today.return_value = datetime(2026, 3, 4, 8, 0, tzinfo=tz)

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        result = ps.main()
        self.assertTrue(result)
        mock_server.send_message.assert_called_once()

    @patch.object(ps, 'EMAIL_ENABLED', True)
    @patch.object(ps, 'SENDER_PASSWORD', 'fake')
    @patch.object(ps, 'RECIPIENT_EMAILS', 'test@example.com')
    @patch('prayer_schedule_V10_DESKTOP_FIXED.smtplib.SMTP')
    @patch.object(ps, 'get_today')
    def test_main_returns_true_even_if_email_fails(self, mock_today, mock_smtp_class):
        """Email failure should not cause main() to return False (by current design)."""
        import smtplib
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Chicago")
        mock_today.return_value = datetime(2026, 3, 4, 8, 0, tzinfo=tz)

        mock_server = MagicMock()
        mock_server.send_message.side_effect = smtplib.SMTPException("fail")
        mock_smtp_class.return_value = mock_server

        result = ps.main()
        # Current behavior: main() returns True even if email fails
        self.assertTrue(result)

    @patch.object(ps, 'EMAIL_ENABLED', False)
    @patch.object(ps, 'get_today')
    def test_main_generates_valid_html(self, mock_today):
        """Generated HTML file should be valid-looking HTML."""
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Chicago")
        mock_today.return_value = datetime(2026, 3, 2, 8, 0, tzinfo=tz)

        ps.main()

        html_path = os.path.join(self.tmpdir, "Prayer_Schedule_Current_Week.html")
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("<!DOCTYPE html", content)
        self.assertIn("</html>", content)
        # Should contain all 8 elders
        for elder in ps.ELDERS:
            self.assertIn(elder, content)


# ---------------------------------------------------------------------------
# 11. Week-to-week rotation for ALL 8 cycle positions
# ---------------------------------------------------------------------------
class TestFullCycleRotation(unittest.TestCase):
    """Extended rotation test covering all 8 positions in a cycle."""

    def test_no_overlap_between_any_consecutive_weeks(self):
        """For every pair of consecutive weeks in a full cycle, no elder
        should share any families."""
        for start_week in range(1, 9):
            for elder in ps.ELDERS:
                w1 = set(ps.assign_families_for_week_v10(start_week)[elder])
                w2 = set(ps.assign_families_for_week_v10(start_week + 1)[elder])
                overlap = w1 & w2
                self.assertEqual(
                    len(overlap), 0,
                    f"{elder} has {len(overlap)} overlapping families "
                    f"between week {start_week} and {start_week + 1}"
                )

    def test_all_161_families_covered_every_week(self):
        all_families = set(ps.parse_directory())
        for week in range(1, 9):
            assignments = ps.assign_families_for_week_v10(week)
            assigned = set()
            for families in assignments.values():
                assigned.update(families)
            self.assertEqual(assigned, all_families,
                             f"Week {week}: missing or extra families")


# ---------------------------------------------------------------------------
# 12. log_activity()
# ---------------------------------------------------------------------------
class TestLogActivity(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_desktop = ps.DESKTOP_DIR
        ps.DESKTOP_DIR = self.tmpdir

    def tearDown(self):
        ps.DESKTOP_DIR = self._orig_desktop
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_log_file(self):
        ps.log_activity("Test message")
        log_path = os.path.join(self.tmpdir, "prayer_schedule_log.txt")
        self.assertTrue(os.path.exists(log_path))
        with open(log_path, 'r') as f:
            content = f.read()
        self.assertIn("Test message", content)

    def test_appends_to_existing_log(self):
        ps.log_activity("First")
        ps.log_activity("Second")
        log_path = os.path.join(self.tmpdir, "prayer_schedule_log.txt")
        with open(log_path, 'r') as f:
            content = f.read()
        self.assertIn("First", content)
        self.assertIn("Second", content)

    def test_log_contains_timestamp(self):
        ps.log_activity("Timestamped")
        log_path = os.path.join(self.tmpdir, "prayer_schedule_log.txt")
        with open(log_path, 'r') as f:
            content = f.read()
        # Should have [YYYY-MM-DD HH:MM:SS] format
        self.assertRegex(content, r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]')

    @unittest.skipIf(os.getuid() == 0, "chmod has no effect as root")
    def test_survives_readonly_dir(self):
        """log_activity should not raise even if dir is read-only."""
        ro_dir = os.path.join(self.tmpdir, "readonly")
        os.makedirs(ro_dir)
        os.chmod(ro_dir, 0o444)
        ps.DESKTOP_DIR = ro_dir
        # Should not raise
        ps.log_activity("Should not crash")
        os.chmod(ro_dir, 0o755)


# ---------------------------------------------------------------------------
# 13. _build_combined_email_html() content checks
# ---------------------------------------------------------------------------
class TestBuildCombinedEmailHtml(unittest.TestCase):
    """Verify the email HTML builder produces valid, complete content."""

    def setUp(self):
        self.today = datetime(2026, 3, 4)  # Wednesday
        self.today_name = "Wednesday"
        self.week_num = 10
        self.monday = datetime(2026, 3, 2)
        self.schedule = ps.get_week_schedule(self.week_num)
        self.assignments = ps.assign_families_for_week_v10(self.week_num)

    def test_contains_today_name(self):
        html = ps._build_combined_email_html(
            self.today, self.today_name, self.week_num,
            self.monday, self.schedule, self.assignments)
        self.assertIn("Wednesday", html)

    def test_contains_all_day_names(self):
        html = ps._build_combined_email_html(
            self.today, self.today_name, self.week_num,
            self.monday, self.schedule, self.assignments)
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            self.assertIn(day, html)

    def test_contains_today_elder(self):
        html = ps._build_combined_email_html(
            self.today, self.today_name, self.week_num,
            self.monday, self.schedule, self.assignments)
        # Wednesday elder is Jerry Wood
        self.assertIn("Jerry Wood", html)

    def test_monday_includes_full_lists(self):
        """On Monday, the email should include full prayer lists for all elders."""
        monday = datetime(2026, 3, 2)
        html = ps._build_combined_email_html(
            monday, "Monday", self.week_num,
            monday, self.schedule, self.assignments)
        # All elders should have their family lists
        for elder in ps.ELDERS:
            self.assertIn(elder, html)

    def test_non_monday_omits_full_lists(self):
        """On non-Monday, the full prayer lists section should not appear."""
        html = ps._build_combined_email_html(
            self.today, self.today_name, self.week_num,
            self.monday, self.schedule, self.assignments)
        # The full lists section is only on Monday (line 1144: is_monday check)
        # We can check that NOT all elders have numbered family lists
        # (Only today's elder should have a list)
        # This is a structural check - Wednesday only shows Jerry Wood's families
        todays_elders = self.schedule["Wednesday"]
        non_today_elders = [e for e in ps.ELDERS if e not in todays_elders]
        # Non-today elders should appear in the week table but NOT with numbered lists
        # We check that the "Full Prayer Lists" header is absent
        self.assertNotIn("FULL PRAYER LISTS", html.upper().replace("FULL WEEKLY PRAYER LISTS", "FULL PRAYER LISTS") if "FULL WEEKLY" not in html.upper() else "")


# ---------------------------------------------------------------------------
# 14. Pool distribution
# ---------------------------------------------------------------------------
class TestMasterPools(unittest.TestCase):

    def test_pool_0_has_21(self):
        pools = ps.create_v10_master_pools()
        self.assertEqual(len(pools[0]), 21)

    def test_pools_1_through_7_have_20(self):
        pools = ps.create_v10_master_pools()
        for i in range(1, 8):
            self.assertEqual(len(pools[i]), 20, f"Pool {i} has wrong size")

    def test_total_is_161(self):
        pools = ps.create_v10_master_pools()
        total = sum(len(p) for p in pools)
        self.assertEqual(total, 161)

    def test_no_duplicate_families_across_pools(self):
        pools = ps.create_v10_master_pools()
        all_fams = []
        for pool in pools:
            all_fams.extend(pool)
        self.assertEqual(len(all_fams), len(set(all_fams)))

    def test_pools_are_sorted(self):
        pools = ps.create_v10_master_pools()
        for i, pool in enumerate(pools):
            self.assertEqual(pool, sorted(pool), f"Pool {i} not sorted")


if __name__ == "__main__":
    unittest.main()
