"""Output-rendering tests: HTML escaping for elders/families and Central-TZ stamp.

Validates that the website HTML generator does not emit raw user-controlled
characters into element content or attribute values, and that the
"Last updated" timestamp is rendered in the church-local (Central) calendar
clock — not the runner's UTC.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from prayer_schedule import output
from prayer_schedule.config import CENTRAL_TZ


def _crafted_assignments() -> tuple[int, datetime, dict[str, list[str]], dict[str, list[str]]]:
    """Build a minimal schedule + assignments dict containing HTML-hostile names.

    Returns ``(week_number, monday, schedule_override, elder_assignments)``.
    The ``schedule_override`` is monkeypatched into get_week_schedule so we
    don't need to mutate ELDER_DATA.
    """
    monday = datetime(2026, 5, 11, 0, 0, tzinfo=CENTRAL_TZ)  # arbitrary Monday
    week_num = 19
    schedule = {
        "Monday": ['Evil <Elder> "Quote" & Co'],
        "Tuesday": ["Sam"],
        "Wednesday": ["Sam"],
        "Thursday": ["Sam"],
        "Friday": ["Sam"],
        "Saturday": ["Sam"],
        "Sunday": ["Sam"],
    }
    elder_assignments = {
        'Evil <Elder> "Quote" & Co': ['O\'Hara <script>, Family & Friends'],
        "Sam": ["Smith, John"],
    }
    return week_num, monday, schedule, elder_assignments


def test_elder_names_are_html_escaped_in_website(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An elder name containing ``<``, ``>``, ``&``, ``"`` must never reach
    the HTML as literal characters in either content or attribute position.
    """
    week_num, monday, schedule, elder_assignments = _crafted_assignments()
    monkeypatch.setattr(output, "get_week_schedule", lambda _w: schedule)

    html = output.generate_html_schedule(week_num, monday, elder_assignments)

    # Element-content escaping: the literal ``<Elder>`` must appear escaped,
    # and the raw ``<Elder>`` must NOT appear anywhere (would parse as a tag).
    assert "&lt;Elder&gt;" in html
    assert "<Elder>" not in html

    # The ``&`` in the elder name must be escaped as ``&amp;``. We can't
    # simply count ``&`` because legitimate entities (``&amp;``) also start
    # with ``&``; instead, assert the original sequence is gone.
    assert "Quote\" & Co" not in html  # raw ampersand in content is forbidden

    # The family name containing ``<script>`` must be escaped, not active.
    assert "&lt;script&gt;" in html
    assert "<script>, Family" not in html  # raw ``<script>`` would be injected


def test_data_elder_attribute_is_attr_escaped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``data-elder="..."`` must escape ``"`` so a name with a literal quote
    cannot break out of the attribute boundary.
    """
    week_num, monday, schedule, elder_assignments = _crafted_assignments()
    monkeypatch.setattr(output, "get_week_schedule", lambda _w: schedule)

    html = output.generate_html_schedule(week_num, monday, elder_assignments)

    # The data-elder attribute must contain the escaped form (``&quot;``),
    # and the raw double-quote breakout pattern must not appear.
    assert 'data-elder="Evil &lt;Elder&gt; &quot;Quote&quot; &amp; Co"' in html


def test_last_updated_uses_central_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """The "Last updated" stamp must render the Central calendar/clock, not UTC.

    Choose an instant where UTC and Central fall on different *days*; the
    stamp must reflect the Central side.
    """
    # 2026-05-15 03:00 UTC = 2026-05-14 22:00 Central (CDT, UTC-5).
    fixed_utc = datetime(2026, 5, 15, 3, 0, tzinfo=timezone.utc)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:  # type: ignore[override]
            if tz is None:
                return fixed_utc.replace(tzinfo=None)
            return fixed_utc.astimezone(tz)

    monkeypatch.setattr(output, "datetime", FrozenDateTime)

    week_num, monday, schedule, elder_assignments = _crafted_assignments()
    monkeypatch.setattr(output, "get_week_schedule", lambda _w: schedule)

    html = output.generate_html_schedule(week_num, monday, elder_assignments)

    # The Central-local date is May 14, 2026 at 10:00 PM.
    assert "Last updated: May 14, 2026 at 10:00 PM" in html
    # The naive-UTC rendering would have been May 15 — make sure it's gone.
    assert "Last updated: May 15, 2026" not in html
