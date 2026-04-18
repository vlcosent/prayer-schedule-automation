"""Elder data and the static weekly day-to-elder schedule.

``ELDER_DATA`` is the single source of truth for the 8 church elders. The
derived ``ELDERS`` list, ``ELDER_FAMILIES`` mapping, and ``get_week_schedule``
function are all built from this list, so adding or removing an elder only
requires editing ``ELDER_DATA`` (and the reassignment map in ``algorithm.py``).
"""

from __future__ import annotations

from typing import TypedDict

from .config import DAYS_OF_WEEK


class ElderRecord(TypedDict):
    """Shape of each entry in :data:`ELDER_DATA`."""

    name: str
    family: str
    days: list[str]


# Elder roster: name, their own family string, and the day(s) of the week they
# are assigned to pray. Monday historically has two elders (Alan Judd and
# Brian McLaughlin); all other days have exactly one.
ELDER_DATA: list[ElderRecord] = [
    {"name": "Alan Judd",         "family": "Judd, Alan & Amy; Anderson, Adrian, Adam",       "days": ["Monday"]},
    {"name": "Brian McLaughlin",  "family": "McLaughlin, Brian & Heather",                    "days": ["Monday"]},
    {"name": "Frank Bohannon",    "family": "Bohannon, Frank & Paula",                        "days": ["Tuesday"]},
    {"name": "Jerry Wood",        "family": "Wood, Jerry & Rebecca",                          "days": ["Wednesday"]},
    {"name": "Jonathan Loveday",  "family": "Loveday, Jonathan & Sylvia; Jabin",              "days": ["Thursday"]},
    {"name": "Kyle Fairman",      "family": "Fairman, Kyle & Leigh Ann; Wyatt, Audrey",       "days": ["Friday"]},
    {"name": "L.A. Fox",          "family": "Fox, L.A. & Cindy",                              "days": ["Saturday"]},
    {"name": "Larry McDuffee",    "family": "McDuffee, Larry & Linda",                        "days": ["Sunday"]},
]


# Ordered list of elder names, in the rotation order used by the algorithm.
ELDERS: list[str] = [e["name"] for e in ELDER_DATA]


# Map of elder name to their own family string.  The assignment algorithm
# uses this to ensure no elder ever prays for their own family.
ELDER_FAMILIES: dict[str, str] = {e["name"]: e["family"] for e in ELDER_DATA}


def get_week_schedule(week_number: int) -> dict[str, list[str]]:
    """Return the static day-to-elder mapping.

    Although ``week_number`` is accepted for forward compatibility, the
    schedule is currently fixed (Monday gets Alan Judd & Brian McLaughlin,
    each other weekday has a single elder). The result is a mapping from
    day name ("Monday".."Sunday") to an ordered list of elder names.
    """
    schedule: dict[str, list[str]] = {day: [] for day in DAYS_OF_WEEK}
    for elder in ELDER_DATA:
        for day in elder["days"]:
            schedule[day].append(elder["name"])
    return schedule
