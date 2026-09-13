#!/usr/bin/env python3
"""Every requirement an accepted feature defines is locked by some version — OPS-R30.

A version manifest's `goals` is what puts a requirement on the release train. A
requirement defined in a feature that no manifest names is not scheduled, not
tracked, and not refused by anything: `check_order` reads what is scheduled
against what it depends on, `check_binding_order` reads what is binding against
what is agreed, and `status_lint` reads ticks against citations. All three are
silent about a requirement no version claims, because none of them is looking at
the gap between the features and the train.

That gap is filled the same way every time. A feature is written, a version locks
its requirements, and a requirement is appended afterwards — `A7-R15` after
`0.13.0` locked the other fourteen, `C4-R15` after `0.7.0` locked the other
fourteen. The manifest is somewhere else and nothing asks.

Draft and withdrawn features are exempt by their own frontmatter rather than by a
list here. A draft feature is one nobody has agreed to yet, so scheduling it would
be the error; `n1`–`n4` are the companion's, which takes no version at all, and
they leave this check by being accepted rather than by being named.

Usage:  check_goal_coverage.py [--root PATH]
Exit 0 = every accepted requirement is locked or declared below, 1 = one is neither.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import tomllib

from patterns import REQ_DEF

FEATURES = "10-functional"
VERSIONS = "70-operations/versions"
STATUS = re.compile(r"^status:\s*(\S+)", re.MULTILINE)

# Requirements that predate this check and have no version yet, against where the
# rest of their feature is locked — which is what somebody deciding needs.
#
# Not a licence to leave one here. An entry is a debt with a name on it, and the
# check refuses an entry that has stopped being true: one that some version has
# since locked, or that no accepted feature defines any more. So the list empties
# itself as the train picks these up, and cannot quietly outlive them.
#
# None of these is assigned here, deliberately. Which version carries a
# requirement is a decision about what ships when, and a gate is the wrong place
# to make one — five of the eight features below have their siblings in a
# *released* manifest, whose goals are frozen (OPS-R30), so those cannot simply
# be added to where the rest sit.
AWAITING_A_VERSION = {
    "A7-R15": "the other fourteen A7 goals are locked by 0.13.0, released",
    "C1-R15": "C1 is split across 0.1.0, 0.2.0 and 0.8.0, all released",
    "C4-R15": "the other fourteen C4 goals are locked by 0.7.0, released",
    "C6-R18": "C6 is split across 0.9.0 and 0.10.0, both released",
    "E3-R16": "E3 is split across 0.3.0 and 0.14.0, both released",
    "F3-R15": "F3's other twenty-one goals are locked by 0.16.0, planned",
    "F3-R16": "F3's other twenty-one goals are locked by 0.16.0, planned",
    "F3-R19": "F3's other twenty-one goals are locked by 0.16.0, planned",
    "F3-R20": "F3's other twenty-one goals are locked by 0.16.0, planned",
    "F4-R5": "F4's other thirteen goals are locked by 0.16.0, planned",
    "G8-R15": "G8 is split across 0.10.0, 0.11.0 and 0.14.0, all released",
    "G8-R16": "G8 is split across 0.10.0, 0.11.0 and 0.14.0, all released",
    "G8-R17": "G8 is split across 0.10.0, 0.11.0 and 0.14.0, all released",
    "G8-R18": "G8 is split across 0.10.0, 0.11.0 and 0.14.0, all released",
}


def accepted_requirements(root: pathlib.Path) -> dict[str, str]:
    """Every requirement an accepted feature defines, against the file defining it."""
    found: dict[str, str] = {}
    for md in sorted((root / FEATURES).rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        status = STATUS.search(text)
        if status is None or status.group(1) != "accepted":
            continue
        for rid in REQ_DEF.findall(text):
            found[rid] = str(md.relative_to(root))
    return found


def locked_goals(root: pathlib.Path) -> set[str]:
    """Every requirement any manifest names, whatever that version's status."""
    goals: set[str] = set()
    for manifest in sorted((root / VERSIONS).glob("*.toml")):
        if manifest.name == "TEMPLATE.toml":
            continue
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
        goals.update(data.get("goals", []))
    return goals


def unscheduled(defined: dict[str, str], locked: set[str]) -> list[str]:
    """Accepted requirements no version locks and this file does not declare."""
    return sorted(
        f"{rid} is defined in {where} and no version locks it"
        for rid, where in defined.items()
        if rid not in locked and rid not in AWAITING_A_VERSION
    )


def stale(defined: dict[str, str], locked: set[str]) -> list[str]:
    """Declared entries that have stopped being true, so the list cannot outlive them."""
    gone = []
    for rid in sorted(AWAITING_A_VERSION):
        if rid in locked:
            gone.append(f"{rid} is locked by a version now — delete its line")
        elif rid not in defined:
            gone.append(f"{rid} is defined by no accepted feature — delete its line")
    return gone


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="the spec checkout to read")
    root = pathlib.Path(ap.parse_args().root).resolve()

    defined = accepted_requirements(root)
    if not defined:
        print(f"::error::no accepted feature was found under {root / FEATURES}")
        return 1

    locked = locked_goals(root)
    problems = unscheduled(defined, locked) + stale(defined, locked)

    for problem in problems:
        print(f"::error::{problem}")

    if problems:
        print(
            "::error::A requirement no version locks is scheduled by nothing and "
            "refused by nothing. Lock it in a manifest's `goals`, or declare it in "
            "AWAITING_A_VERSION with where the rest of its feature sits (OPS-R30)."
        )
        return 1

    print(
        f"{len(defined)} accepted requirements, {len(AWAITING_A_VERSION)} awaiting a version"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
