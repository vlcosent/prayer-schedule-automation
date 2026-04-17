"""Configuration constants and environment detection for the prayer schedule system.

This module centralises:
  - SMTP settings
  - Timezone configuration (US Central via IANA tzdata)
  - Reference date used for continuous week calculations
  - Common schedule constants (days of week, elder/pool counts)
  - Email delivery tuning parameters
  - DESKTOP_DIR / BASE_DIR auto-detection for CI vs. Desktop runs
  - Email credential / recipient configuration loaded from environment
"""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo


# ============== SMTP ==============
SMTP_SERVER: str = "smtp.gmail.com"
SMTP_PORT: int = 587


# ============== Timezone ==============
# US Central Time via IANA timezone database (stdlib since Python 3.9).
# Automatically handles CST (UTC-6) and CDT (UTC-5) transitions.
CENTRAL_TZ: ZoneInfo = ZoneInfo("America/Chicago")


# ============== Week rotation reference ==============
# Reference Monday for continuous week counting.
# This is the Monday of ISO Week 1 of 2026, chosen so that within 2026,
# continuous week numbers match ISO week numbers exactly. This avoids the
# bug where ISO week numbers reset from 52 (or 53) to 1 at year boundaries,
# which caused cycle_position discontinuities and duplicate family assignments.
REFERENCE_MONDAY: datetime = datetime(2025, 12, 29, tzinfo=CENTRAL_TZ)


# ============== Schedule constants ==============
DAYS_OF_WEEK: tuple[str, ...] = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

ELDER_COUNT: int = 8
POOL_COUNT: int = ELDER_COUNT
ROTATION_WEEKS: int = 8
FAMILIES_PER_ELDER_MIN: int = 19
FAMILIES_PER_ELDER_MAX: int = 21


# ============== Email delivery tuning ==============
EMAIL_CONNECT_TIMEOUT: int = 30
EMAIL_RETRY_MAX: int = 3


# ============== Output directory auto-detection ==============
def _detect_desktop_dir() -> str:
    """Return the best-effort output directory.

    In CI (GitHub Actions) the current working directory is used so generated
    files are picked up and committed. On a regular desktop machine the user's
    Desktop folder is preferred, falling back to Windows ``USERPROFILE`` and
    finally the current working directory.
    """
    try:
        is_ci = (
            os.environ.get("CI") == "true"
            or os.environ.get("GITHUB_ACTIONS") == "true"
        )

        if is_ci:
            desktop_dir = os.getcwd()
            print(f"CI environment detected. Using current directory: {desktop_dir}")
            return desktop_dir

        desktop_dir = os.path.expanduser("~/Desktop")
        if not os.path.exists(desktop_dir):
            desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
            if not os.path.exists(desktop_dir):
                desktop_dir = os.getcwd()
                print(
                    f"Warning: Could not find desktop, using current directory: {desktop_dir}"
                )
        return desktop_dir
    except Exception:
        fallback = os.getcwd()
        print(f"Warning: Could not find desktop, using current directory: {fallback}")
        return fallback


DESKTOP_DIR: str = _detect_desktop_dir()
BASE_DIR: str = DESKTOP_DIR


# ============== Email credentials (from environment) ==============
EMAIL_ENABLED: bool = os.environ.get("EMAIL_ENABLED", "false").lower() == "true"
SENDER_EMAIL: str = os.environ.get("SENDER_EMAIL", "churchprayerlistelders@gmail.com")
SENDER_PASSWORD: str = os.environ.get("SENDER_PASSWORD", "")
RECIPIENT_EMAILS: str = os.environ.get("RECIPIENT_EMAILS", "")
