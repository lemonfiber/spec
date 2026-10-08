#!/usr/bin/env python3
"""What counts against the cap on open pull requests, and when a claim is stale
— GOV-R58.

A repository holds at most `CAP` open pull requests opened by people and agents;
the organisation's bots are not counted. The report flags a repository over it,
the board shows the flag, and `pr_cap.py` comments on the pull request that
takes a repository past it. All three count here, so none can count differently.

A pull request is read in either shape the forge gives it: GraphQL's, whose
author carries `__typename`, and REST's, whose user carries `type`.
"""

from __future__ import annotations

import datetime

#: The open pull requests a repository may hold from people and agents.
CAP = 3
#: How long a draft pull request goes without a commit before its claim is shown
#: as stale.
STALE_AFTER = datetime.timedelta(days=14)


def is_bot(pr: dict) -> bool:
    """Whether a bot opened the pull request, in either of the forge's shapes."""
    author = pr.get("author") or {}
    user = pr.get("user") or {}
    return author.get("__typename") == "Bot" or user.get("type") == "Bot"


def counted(listed: list[dict]) -> int:
    """How many of a repository's open pull requests the cap counts."""
    return sum(not is_bot(pr) for pr in listed)


def over_cap(prs: dict[str, list[dict]]) -> dict[str, int]:
    """Each repository holding more than the cap, with how many it holds."""
    return {repo: n for repo, listed in sorted(prs.items()) if (n := counted(listed)) > CAP}
