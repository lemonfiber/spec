#!/usr/bin/env python3
"""The comment on a pull request that takes its repository past the cap —
GOV-R58.

The cap is held softly: the developer command line refuses a fourth claim, and a
pull request opened anyway is told, here, which others are open and what to do.
Nothing is refused. A pull request a bot opened is not counted and is told
nothing.

Usage:
  pr_cap.py --pulls pulls.json --number N > comment.md

`--pulls` is the repository's open pull requests as the forge's REST API lists
them. The comment is written to standard output, and nothing at all where the
repository is within the cap or the pull request is a bot's, so the caller
removes a comment that has stopped being true. Exit 0 having answered; 2 where
the file cannot be read or the pull request is not among the open ones.
"""

from __future__ import annotations

import argparse
import json
import sys

from claims import CAP, counted, is_bot
from paths import within_cwd

#: The first line of the comment, by which the caller finds it to replace it.
MARKER = "<!-- pr-cap -->"
#: Where the cap is written.
RULE = ("https://github.com/lemonfiber/spec/blob/main/50-governance/"
        "working-in-the-repositories.md#at-most-three-open-pull-requests")


def listed(pr: dict) -> str:
    """One other open pull request, as the comment names it."""
    login = (pr.get("user") or {}).get("login", "?")
    title = pr.get("title") or ""
    return f"- #{pr['number']} {title} (@{login})".replace("  (", " (")


def comment(pulls: list[dict], number: int) -> str:
    """The comment for one pull request, or nothing where none is owed."""
    this = next((pr for pr in pulls if pr["number"] == number), None)
    if this is None:
        raise LookupError(f"#{number} is not an open pull request here")
    held = counted(pulls)
    if is_bot(this) or held <= CAP:
        return ""
    others = [pr for pr in pulls if pr["number"] != number and not is_bot(pr)]
    held_line = (f"This repository now holds {held} open pull requests from people and "
                 f"agents. The cap is {CAP}, the organisation's bots not counted "
                 f"([GOV-R58]({RULE})).")
    advice = ("Merge or close one of these, or this one, before opening another. "
              "Nothing is refused: this comment changes no check.")
    lines = [MARKER, held_line, "", "The others open now:", "",
             *[listed(pr) for pr in others], "", advice]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pulls", required=True)
    parser.add_argument("--number", type=int, required=True)
    args = parser.parse_args()
    try:
        pulls = json.loads(within_cwd(args.pulls).read_text(encoding="utf-8"))
        print(comment(pulls, args.number), end="")
    except (OSError, json.JSONDecodeError, LookupError) as broken:
        print(f"::error::{broken}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
