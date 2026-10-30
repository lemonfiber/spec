"""How long a commit may sit on a dependency's default branch before a pin's absence of it is a fault — Q-R68.

`workflow-pins` and `upstream-drift` both hold a pin to what its dependency's
default branch has, and both let a commit wait this long first: long enough for
the automated bump that takes it to open, pass and merge itself, short enough that
a stalled one is red the next day. One constant for both, so the number either
gate applies and the number a reader is told cannot differ.

A commit's time is its committer time. A squash merge sets it to the moment the
commit reached the default branch, which is when the window starts. A commit
dated later than the run is counted as past the window, so a date written by hand
can only make a gate stricter.
"""

from __future__ import annotations

import datetime

#: Hours a commit may sit on the default branch before a pin without it is refused.
HOURS = 24

#: The same window in seconds, which is what a committer time is counted in.
SECONDS = HOURS * 3600


def waits(committed: int, now: int) -> bool:
    """Whether a commit made at `committed` is still inside the window at `now`."""
    return 0 <= now - committed < SECONDS


def refused_at(committed: int) -> str:
    """When a commit made at `committed` leaves the window, in UTC, as a reader reads it."""
    moment = datetime.datetime.fromtimestamp(committed + SECONDS, tz=datetime.UTC)
    return moment.strftime("%Y-%m-%d %H:%M UTC")
