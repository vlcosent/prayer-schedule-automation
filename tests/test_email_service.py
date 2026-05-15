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
