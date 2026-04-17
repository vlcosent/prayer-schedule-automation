"""Backward-compatible entry point for the Crossville Church of Christ
prayer schedule system.

All business logic now lives in the :mod:`prayer_schedule` package.  This
module exists so that:

* the Windows launcher ``UPDATE_PRAYER_SCHEDULE_FIXED.bat`` continues to run
  ``python prayer_schedule_V10_DESKTOP_FIXED.py`` unchanged,
* the GitHub Actions workflow continues to invoke the same script path, and
* the helper scripts (``comprehensive_verification.py``,
  ``analyze_missing_coverage.py``, ``calc_reassignments.py``) can keep
  importing the previously public symbols directly from this module.
"""

from __future__ import annotations

import sys

from prayer_schedule.algorithm import (
    assign_families_for_week_v10,
    calculate_continuous_week,
    get_master_pools,
)
from prayer_schedule.cli import main
from prayer_schedule.config import REFERENCE_MONDAY
from prayer_schedule.directory import parse_directory
from prayer_schedule.elders import ELDER_FAMILIES, ELDERS

__all__ = [
    "ELDERS",
    "ELDER_FAMILIES",
    "parse_directory",
    "assign_families_for_week_v10",
    "get_master_pools",
    "calculate_continuous_week",
    "REFERENCE_MONDAY",
    "main",
]


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
