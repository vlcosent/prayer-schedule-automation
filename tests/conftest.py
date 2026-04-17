"""Shared pytest fixtures.

Every test uses `EMAIL_ENABLED=false` so no accidental SMTP is possible.
"""
from __future__ import annotations

import os
import sys

import pytest


# Ensure the repo root is on sys.path so `import prayer_schedule` works
# without installing the package.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# Force-disable email before any prayer_schedule import reads the env.
os.environ.setdefault("EMAIL_ENABLED", "false")


@pytest.fixture(scope="session")
def directory_families() -> list[str]:
    """Parsed DIRECTORY_CSV — sorted list of 'Last, First' strings."""
    from prayer_schedule.directory import parse_directory
    return parse_directory()


@pytest.fixture(scope="session")
def elders() -> list[str]:
    from prayer_schedule.elders import ELDERS
    return list(ELDERS)


@pytest.fixture(scope="session")
def elder_families() -> dict[str, str]:
    from prayer_schedule.elders import ELDER_FAMILIES
    return dict(ELDER_FAMILIES)
