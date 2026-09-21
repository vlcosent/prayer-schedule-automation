"""File system I/O helpers: atomic writes, schedule archiving, and logging."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from .config import CENTRAL_TZ, DESKTOP_DIR


_CURRENT_HTML_NAME: str = "Prayer_Schedule_Current_Week.html"
_CURRENT_TEXT_NAME: str = "Prayer_Schedule_Current_Week.txt"
_LOG_FILE_NAME: str = "prayer_schedule_log.txt"
_ARCHIVE_SUBDIR: str = "archive"


def _atomic_write(path: str, content: str) -> None:
    """Write ``content`` to ``path`` atomically via a ``<path>.tmp`` intermediate.

    Raises :class:`FileNotFoundError` / :class:`PermissionError` / :class:`OSError`
    on failure rather than swallowing them. If any step fails after the tmp
    file is created, the tmp file is unlinked so it doesn't accumulate or
    shadow the next attempt.
    """
    tmp_path = f"{path}.tmp"
    try:
        # Write to the temp file first; on success, atomically rename over the
        # target. ``os.replace`` is atomic on POSIX and overwrites on Windows.
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def update_desktop_files(html_content: str, text_content: str) -> bool:
    """Write the current HTML and text schedule files to :data:`DESKTOP_DIR`.

    Pre-checks ``DESKTOP_DIR`` exists and is writable; each file is written
    to a temporary path and then atomically renamed. Returns ``True`` on
    success, ``False`` on any failure (and prints a diagnostic message).
    """
    success = True

    desktop_html = os.path.join(DESKTOP_DIR, _CURRENT_HTML_NAME)
    desktop_text = os.path.join(DESKTOP_DIR, _CURRENT_TEXT_NAME)

    # Pre-check: the output directory must exist and be writable.
    if not os.path.isdir(DESKTOP_DIR):
        print(f"   [ERROR] Output directory does not exist: {DESKTOP_DIR}")
        return False
    if not os.access(DESKTOP_DIR, os.W_OK):
        print(f"   [ERROR] Output directory is not writable: {DESKTOP_DIR}")
        return False

    try:
        _atomic_write(desktop_html, html_content)
        print(f"   [OK] Updated: {desktop_html}")
    except FileNotFoundError as exc:
        print(f"   [ERROR] Failed to write HTML file (not found): {exc}")
        success = False
    except PermissionError as exc:
        print(f"   [ERROR] Failed to write HTML file (permission denied): {exc}")
        success = False
    except OSError as exc:
        print(f"   [ERROR] Failed to write HTML file: {exc}")
        success = False

    try:
        _atomic_write(desktop_text, text_content)
        print(f"   [OK] Updated: {desktop_text}")
    except FileNotFoundError as exc:
        print(f"   [ERROR] Failed to write text file (not found): {exc}")
        success = False
    except PermissionError as exc:
        print(f"   [ERROR] Failed to write text file (permission denied): {exc}")
        success = False
    except OSError as exc:
        print(f"   [ERROR] Failed to write text file: {exc}")
        success = False

    return success


def archive_file_name(week_number: int, week_monday: datetime) -> str:
    """Return the archive filename for the week that starts on ``week_monday``.

    The date in the name is the *following* Monday, i.e. the day the weekly
    rollover happens, which keeps the convention every archive file has used
    since 2025::

        Prayer_Schedule_<following Monday>_Week<N>.txt
    """
    if week_monday.weekday() != 0:
        raise ValueError(
            f"week_monday must be a Monday, got {week_monday:%Y-%m-%d} ({week_monday:%A})"
        )
    following_monday = week_monday + timedelta(days=7)
    return f"Prayer_Schedule_{following_monday:%Y-%m-%d}_Week{week_number}.txt"


def archive_week_schedule(
    text_content: str,
    week_number: int,
    week_monday: datetime,
) -> bool:
    """Write one week's text schedule into ``archive/`` unless it is already there.

    A week's schedule is deterministic, so this is idempotent: an existing
    file is left untouched and ``False`` is returned. ``True`` means a new
    archive file was written. I/O errors are reported but never raised,
    because a failed archive must not block the daily email.
    """
    archive_dir = os.path.join(DESKTOP_DIR, _ARCHIVE_SUBDIR)
    archive_name = archive_file_name(week_number, week_monday)
    archive_path = os.path.join(archive_dir, archive_name)

    if os.path.exists(archive_path):
        print(f"   [INFO] Already archived: archive/{archive_name}")
        return False

    try:
        os.makedirs(archive_dir, exist_ok=True)
        _atomic_write(archive_path, text_content)
    except OSError as exc:
        print(f"   [WARNING] Could not archive previous week: {exc}")
        print("   [INFO] Continuing with schedule generation...")
        return False

    print(f"   [ARCHIVED] Week {week_number} saved to: archive/{archive_name}")
    return True


_LOG_MAX_BYTES: int = 1_048_576  # 1 MB; rotates to <log>.1 above this size.


def log_activity(message: str) -> None:
    """Append ``message`` to the activity log file with a UTC-less timestamp.

    Matches the original line format exactly::

        [YYYY-MM-DD HH:MM:SS] <message>

    Rotates the log to ``<log>.1`` (single generation, overwritten each time)
    once it exceeds ``_LOG_MAX_BYTES`` so desktop installs don't accumulate an
    unbounded file. CI doesn't hit this path because each run starts fresh.
    """
    try:
        log_file = os.path.join(DESKTOP_DIR, _LOG_FILE_NAME)
        try:
            if os.path.getsize(log_file) > _LOG_MAX_BYTES:
                os.replace(log_file, f"{log_file}.1")
        except FileNotFoundError:
            pass  # First write — nothing to rotate.
        with open(log_file, "a", encoding="utf-8") as handle:
            handle.write(
                f"[{datetime.now(CENTRAL_TZ).strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"
            )
    except OSError as exc:
        print(f"   [WARNING] Logging failed: {exc}", file=sys.stderr)
