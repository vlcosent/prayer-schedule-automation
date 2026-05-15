"""Email-service tests: recipient parsing rejects malformed addresses."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from prayer_schedule import config, email_service
from prayer_schedule.algorithm import assign_families_for_week_v10, calculate_continuous_week
from prayer_schedule.config import CENTRAL_TZ


def _fixture_today_and_assignments() -> tuple[datetime, datetime, int, dict[str, list[str]]]:
    """Return (today, monday, week_num, elder_assignments) for a known good Friday."""
    today = datetime(2026, 4, 17, 9, 0, tzinfo=CENTRAL_TZ)  # Friday
    monday = (today - timedelta(days=today.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_num = calculate_continuous_week(monday)
    elder_assignments = assign_families_for_week_v10(week_num)
    return today, monday, week_num, elder_assignments


def _make_smtp_factory() -> tuple[MagicMock, list[object]]:
    """Build a fake smtplib.SMTP factory that records every send_message call.

    Returns ``(factory, sent_messages)`` so tests can introspect what
    actually reached the server.
    """
    sent_messages: list[object] = []
    server = MagicMock()
    server.send_message.side_effect = lambda msg: sent_messages.append(msg)
    factory = MagicMock(return_value=server)
    return factory, sent_messages


def test_recipient_parsing_skips_malformed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed addresses must be skipped before SMTP is contacted; only
    well-formed addresses should reach send_message().
    """
    monkeypatch.setattr(config, "EMAIL_ENABLED", True)
    monkeypatch.setattr(config, "SENDER_PASSWORD", "fake-app-password")
    monkeypatch.setattr(
        config,
        "RECIPIENT_EMAILS",
        "a@b.com, not-an-email, c@d.com,  ,@bad.com,good@example.org",
    )

    factory, sent_messages = _make_smtp_factory()
    monkeypatch.setattr(email_service.smtplib, "SMTP", factory)

    today, monday, week_num, assignments = _fixture_today_and_assignments()
    result = email_service.send_daily_combined_email(today, week_num, monday, assignments)
    assert result is True

    recipients = sorted(msg["To"] for msg in sent_messages)
    assert recipients == ["a@b.com", "c@d.com", "good@example.org"], recipients


def test_send_returns_false_with_no_valid_recipients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If every configured recipient is malformed, the function must abort
    before opening any SMTP connection and return False.
    """
    monkeypatch.setattr(config, "EMAIL_ENABLED", True)
    monkeypatch.setattr(config, "SENDER_PASSWORD", "fake-app-password")
    monkeypatch.setattr(config, "RECIPIENT_EMAILS", "not-an-email, @bad.com, foo")

    factory, _sent_messages = _make_smtp_factory()
    monkeypatch.setattr(email_service.smtplib, "SMTP", factory)

    today, monday, week_num, assignments = _fixture_today_and_assignments()
    result = email_service.send_daily_combined_email(today, week_num, monday, assignments)
    assert result is False
    assert factory.call_count == 0, "SMTP should not be opened when no recipients are valid"


def test_email_html_escapes_elder_and_family_names() -> None:
    """The email HTML builder must escape HTML-hostile characters in both
    elder names and family names — never emit raw ``<``, ``>``, or ``&``
    that came from configuration into element-content position.
    """
    monday = datetime(2026, 5, 11, 0, 0, tzinfo=CENTRAL_TZ)
    today = datetime(2026, 5, 11, 9, 0, tzinfo=CENTRAL_TZ)  # Monday so the
    # Monday-only "all elders" section also exercises the escape paths.
    schedule = {
        "Monday": ['Evil <Elder> & Co'],
        "Tuesday": ["Sam"],
        "Wednesday": ["Sam"],
        "Thursday": ["Sam"],
        "Friday": ["Sam"],
        "Saturday": ["Sam"],
        "Sunday": ["Sam"],
    }
    elder_assignments = {
        'Evil <Elder> & Co': ['Family <script>, A & B'],
        "Sam": ["Smith, John"],
    }

    html = email_service._build_combined_email_html(
        today, "Monday", 19, monday, schedule, elder_assignments
    )

    # Elder name escaping: literal ``<Elder>`` must not appear in the HTML.
    assert "&lt;Elder&gt;" in html
    assert "<Elder>" not in html

    # Family name escaping: literal ``<script>`` must not appear.
    assert "&lt;script&gt;" in html
    assert "<script>, A" not in html

    # The raw ``&`` joining the elder name with ``Co`` must be escaped.
    assert "Elder&gt; & Co" not in html
    assert "Elder&gt; &amp; Co" in html


def test_send_attaches_utf8_mime_parts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both MIMEText parts must declare charset=utf-8 so non-ASCII names in a
    future roster don't trip the default us-ascii encoder."""
    monkeypatch.setattr(config, "EMAIL_ENABLED", True)
    monkeypatch.setattr(config, "SENDER_PASSWORD", "fake-app-password")
    monkeypatch.setattr(config, "RECIPIENT_EMAILS", "a@b.com")

    factory, sent_messages = _make_smtp_factory()
    monkeypatch.setattr(email_service.smtplib, "SMTP", factory)

    today, monday, week_num, assignments = _fixture_today_and_assignments()
    assert email_service.send_daily_combined_email(today, week_num, monday, assignments) is True

    assert sent_messages, "no message captured"
    msg = sent_messages[0]
    parts = msg.get_payload()
    assert len(parts) == 2, "expected plain + html alternative parts"
    charsets = {part.get_content_charset() for part in parts}
    assert charsets == {"utf-8"}, charsets


def test_send_rejects_elder_name_with_crlf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A CR/LF in today's elder list must abort the send before SMTP is opened
    so a header-injection attempt can never reach the wire."""
    monkeypatch.setattr(config, "EMAIL_ENABLED", True)
    monkeypatch.setattr(config, "SENDER_PASSWORD", "fake-app-password")
    monkeypatch.setattr(config, "RECIPIENT_EMAILS", "a@b.com")

    factory, _sent_messages = _make_smtp_factory()
    monkeypatch.setattr(email_service.smtplib, "SMTP", factory)

    today, monday, week_num, assignments = _fixture_today_and_assignments()

    # Today is a Friday in the fixture; replace the Friday entry with a
    # CR/LF-poisoned elder name. The function should refuse to construct the
    # subject and return False without contacting SMTP.
    poisoned_schedule = {
        "Monday": ["Sam"], "Tuesday": ["Sam"], "Wednesday": ["Sam"],
        "Thursday": ["Sam"],
        "Friday": ["Bad\r\nBcc: evil@example.com"],
        "Saturday": ["Sam"], "Sunday": ["Sam"],
    }
    monkeypatch.setattr(email_service, "get_week_schedule", lambda _w: poisoned_schedule)

    result = email_service.send_daily_combined_email(today, week_num, monday, assignments)
    assert result is False
    assert factory.call_count == 0, "SMTP must not be opened when the subject is poisoned"
