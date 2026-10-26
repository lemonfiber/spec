#!/usr/bin/env python3
"""When a claim is stale, and whether a bot opened a pull request.

A draft pull request is a claim on the work it cites; one that goes without a
commit for `STALE_AFTER` is shown as stale. A bot's pull request claims nothing.
A pull request is read in the shape `open_prs.sh` lists it, GraphQL's, whose
author carries `__typename`.
"""

from __future__ import annotations

import datetime

#: How long a draft pull request goes without a commit before its claim is shown
#: as stale.
STALE_AFTER = datetime.timedelta(days=14)


def is_bot(pr: dict) -> bool:
    """Whether a bot opened the pull request."""
    return (pr.get("author") or {}).get("__typename") == "Bot"
