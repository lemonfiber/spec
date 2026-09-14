#!/usr/bin/env python3
"""Refuse assistant attribution in the permanent record (GOV-R46).

The guide says it in one line — no AI attribution anywhere, not in commits, not
in pull request bodies, not in squash messages — and until now nothing read it.
A written rule nothing enforces is a rule that is broken by whoever has not read
that paragraph this week, which in practice is every assistant whose own default
is to add a trailer.

Usage: attribution_check.py <base_sha> <head_sha> [--body-on-stdin]

Two halves, split the way `dco_check.py` splits: `_read` shells out to git and
`attributed` is handed text and decides. What is worth holding is which shapes
count, and building real commits to reach that would be testing git as much as
this.

**Anchored to the line, never to the prose.** Every pattern below requires the
line to begin with the shape — no leading whitespace — because this file, the
guide that states the rule and any commit message explaining it all have to be
able to name what is forbidden without becoming forbidden. A rule that fires on
its own documentation is a rule somebody switches off, and the switching off
takes the real coverage with it.
"""
import re
import subprocess
import sys

# Kept here rather than shared. The line below is a validation, and a scanner
# that cannot see it reports the call it guards as unguarded.
_REF = re.compile(r"\A[0-9A-Za-z._/-]{1,255}\Z")

# One record per commit, fields NUL-separated and records ending in \x01, so a
# body containing newlines — which every body does — cannot be mistaken for the
# end of a commit. `dco_check.py`'s shape, for its reason.
FORMAT = "%H%x00%s%x00%B%x01"

# The assistants whose attribution this has actually had to remove, plus the
# domains their trailers carry. Names rather than a catch-all, because a
# co-author trailer is a legitimate thing between two people and refusing every
# one of them would refuse pair programming to enforce a rule about robots.
ASSISTANTS = (
    "claude",
    "copilot",
    "chatgpt",
    "openai",
    "anthropic",
    "cursor",
    "devin",
    "codex",
    "gemini",
    "aider",
)

_NAMES = "|".join(ASSISTANTS)

# A co-author trailer naming one of them, or carrying one of their addresses.
# `^` with no leading whitespace allowed: prose quoting a trailer indents it,
# and a trailer git will read does not.
TRAILER = re.compile(
    rf"^Co-authored-by:[^\n]*(?:{_NAMES})[^\n]*$",
    re.IGNORECASE | re.MULTILINE,
)

# The badge form, which arrives as a line of its own at the foot of a body.
BADGE = re.compile(
    rf"^[^\w\n]*(?:generated|written|authored|created)\s+(?:with|by)\s+[^\n]*(?:{_NAMES})[^\n]*$",
    re.IGNORECASE | re.MULTILINE,
)


def attributed(text: str) -> list[str]:
    """Every line of this text that credits an assistant."""
    found = []
    for pattern in (TRAILER, BADGE):
        found.extend(match.strip() for match in pattern.findall(text))
    return found


def problems(out: str, body: str) -> list[str]:
    """Every commit in what git said, and the pull request body, that credits one.

    The body is checked as well as the commits because a squash merge writes the
    pull request title and body into the commit that lands on the default
    branch. A repository whose commits are clean and whose bodies are not gets
    exactly the history this rule exists to prevent, one merge later.
    """
    said = []

    for rec in filter(None, out.split("\x01\n")):
        parts = rec.strip("\x01\n").split("\x00")
        if len(parts) < 3:
            continue
        sha, subject, message = parts[0], parts[1], parts[2]
        for line in attributed(message):
            said.append(f"{sha[:8]} {subject}\n      {line}")

    for line in attributed(body):
        said.append(f"the pull request body\n      {line}")

    return said


def _read(base: str, head: str) -> str:
    """What git says about the commits between these two."""
    return subprocess.run(
        ["git", "log", f"--format={FORMAT}", f"{base}..{head}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _body(argv: list[str]) -> str:
    """The pull request body, when the caller piped one in.

    Down a pipe rather than named as a path. A body is untrusted text whichever
    way it arrives, but a filename on the command line is a second untrusted
    thing, and a check with exactly one thing to read has no reason to accept
    the name of anything else.
    """
    return sys.stdin.read() if "--body-on-stdin" in argv[3:] else ""


def main(argv: list[str]) -> int:
    base, head = argv[1], argv[2]
    if not (_REF.match(base) and _REF.match(head)):
        print("::error::attribution_check: base and head must be valid git refs")
        return 1

    said = problems(_read(base, head), _body(argv))

    if said:
        print("::error::Assistant attribution in the permanent record:")
        for one in said:
            print(f"  {one}")
        print(
            "\nThe work is the author's own and the record says so (GOV-R46)."
            "\nRemove the trailer or the badge line and say it again."
        )
        return 1
    print("attribution: the record credits nobody it should not")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
