"""Small pure-Python helpers used across the prayer schedule package."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterator

from .config import CENTRAL_TZ, DAYS_OF_WEEK


def get_today() -> datetime:
    """Return the current date/time in US Central Time.

    Uses the IANA timezone database so DST transitions are always correct,
    even if US rules change in the future (via tzdata updates).
    """
    return datetime.now(CENTRAL_TZ)


def iter_week(start_date: datetime) -> Iterator[tuple[str, datetime]]:
    """Yield ``(day_name, date)`` tuples for ``Monday..Sunday``.

    ``start_date`` is expected to be the week's Monday. Each yielded ``date``
    is a copy of ``start_date`` plus the day offset in Mon..Sun order.
    """
    for offset, day in enumerate(DAYS_OF_WEEK):
        yield day, start_date + timedelta(days=offset)


def day_name_for(date: datetime) -> str:
    """Return the English day-of-week name (``Monday``..``Sunday``) for ``date``."""
    return DAYS_OF_WEEK[date.weekday()]
