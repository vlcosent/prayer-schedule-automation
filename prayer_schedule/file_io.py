"""File system I/O helpers: atomic writes, schedule archiving, and logging."""

from __future__ import annotations

import os
import re
import shutil
import sys
from datetime import datetime

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


def archive_previous_schedule() -> bool:
    """Archive the previous week's text file before a Monday regeneration.

    Moves ``Prayer_Schedule_Current_Week.txt`` to
    ``archive/Prayer_Schedule_<date>[_WeekNN].txt``. Returns ``True`` on a
    successful archive, ``False`` when there is nothing to archive or when
    an error occurs (a diagnostic is printed either way so the CI log tells
    the story).
    """
    current_txt = os.path.join(DESKTOP_DIR, _CURRENT_TEXT_NAME)

    if not os.path.exists(current_txt):
        print("   [INFO] No previous schedule to archive (first run or file doesn't exist)")
        return False

    try:
        archive_dir = os.path.join(DESKTOP_DIR, _ARCHIVE_SUBDIR)
        os.makedirs(archive_dir, exist_ok=True)

        # Use Central time so the archive filename always reflects the
        # church-local calendar day, never the server's UTC date.
        timestamp = datetime.now(CENTRAL_TZ).strftime("%Y-%m-%d")

        # Try to extract the week number from the existing file so the
        # archive filename is self-describing.
        week_num: str | None = None
        try:
            with open(current_txt, "r", encoding="utf-8") as handle:
                content = handle.read(300)  # First 300 chars is enough.
            match = re.search(r"WEEK (\d+)", content, re.IGNORECASE)
            if match:
                week_num = match.group(1)
        except OSError as exc:
            print(f"   [INFO] Could not extract week number from file: {exc}")

        if week_num:
            base_name = f"Prayer_Schedule_{timestamp}_Week{week_num}"
        else:
            base_name = f"Prayer_Schedule_{timestamp}"

        archive_path = os.path.join(archive_dir, f"{base_name}.txt")

        # If a same-day archive already exists, append a numeric suffix so
        # the prior copy is never silently overwritten.
        suffix = 1
        while os.path.exists(archive_path):
            archive_path = os.path.join(archive_dir, f"{base_name}_{suffix}.txt")
            suffix += 1

        archive_name = os.path.basename(archive_path)

        # Copy-then-remove pattern gives a cleaner error story than shutil.move.
        shutil.copy2(current_txt, archive_path)
        os.remove(current_txt)

        print(f"   [ARCHIVED] Previous schedule moved to: archive/{archive_name}")
        return True

    except (OSError, shutil.Error) as exc:
        print(f"   [WARNING] Could not archive previous schedule: {exc}")
        print("   [INFO] Continuing with schedule generation...")
        return False


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
