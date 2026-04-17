"""The Crossville Church of Christ prayer schedule package.

Public API (re-exported for helper scripts such as
``comprehensive_verification.py`` and ``analyze_missing_coverage.py``):

    - :data:`ELDERS`
    - :data:`ELDER_FAMILIES`
    - :func:`parse_directory`
    - :func:`assign_families_for_week_v10`
    - :func:`get_master_pools`
    - :func:`calculate_continuous_week`
    - :data:`REFERENCE_MONDAY`
"""

from __future__ import annotations

from .algorithm import (
    assign_families_for_week_v10,
    calculate_continuous_week,
    get_master_pools,
)
from .config import REFERENCE_MONDAY
from .directory import parse_directory
from .elders import ELDER_FAMILIES, ELDERS

__all__ = [
    "ELDERS",
    "ELDER_FAMILIES",
    "parse_directory",
    "assign_families_for_week_v10",
    "get_master_pools",
    "calculate_continuous_week",
    "REFERENCE_MONDAY",
]
