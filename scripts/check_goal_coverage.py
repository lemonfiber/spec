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

from patterns import REQ_DEF, REQ_RETIRED_ROW

FEATURES = "10-functional"
VERSIONS = "70-operations/versions"
STATUS = re.compile(r"^status:\s*(\S+)", re.MULTILINE)

# Requirements that predate this check and have no version yet, against where the
# rest of their feature is locked — which is what somebody deciding needs.
#
# Keyed by feature, because that is what the note is a fact about. Written per
# requirement it was the same sentence four times over for F3 and again for G8,
# and four copies of a sentence are four things to correct when one of those
# versions moves.
#
# Not a licence to leave one here. An entry is a debt with a name on it, and the
# check refuses an entry that has stopped being true: one that some version has
# since locked, or that no accepted feature defines any more. So the list empties
# itself as the train picks these up, and cannot quietly outlive them.
#
# None of these is assigned here, deliberately. Which version carries a
# requirement is a decision about what ships when, and a gate is the wrong place
# to make one — every feature below has its siblings in a *released* manifest,
# whose goals are frozen (OPS-R30), so they cannot simply be added to where the
# rest sit.
AWAITING_A_VERSION = {
    "A7": ("the other fourteen A7 goals are locked by 0.13.0, released", ["A7-R15"]),
    "C1": ("C1 is split across 0.1.0, 0.2.0 and 0.8.0, all released", ["C1-R15"]),
    "C4": ("the other fourteen C4 goals are locked by 0.7.0, released", ["C4-R15"]),
    "C6": ("C6 is split across 0.9.0 and 0.10.0, both released", ["C6-R18", "C6-R19"]),
    "D6": (
        "the other D6 goals are locked by 0.11.0, released; D6-R15 and D6-R16 are the decline address",
        ["D6-R15", "D6-R16"],
    ),
    "E3": ("E3 is split across 0.3.0 and 0.14.0, both released", ["E3-R16"]),
    # The one entry here that was locked and came back. 0.15.0 shipped without it,
    # by a lane that never ran the gate, and the manifest records why. It closes on
    # a hand-run with a real VPN provider on the owner's own hardware — not on a
    # decision, and not on anything a runner can reach.
    "F1": ("the other thirteen F1 goals are locked by 0.15.0, released", ["F1-R1"]),
    "G2": ("the other thirteen G2 goals are locked by 0.9.0, released", ["G2-R14"]),
    "G3": ("G3 is split across 0.9.0 and 0.10.0, both released", ["G3-R16"]),
    "G5": (
        "the other G5 goals are locked by 0.10.0 and 0.11.0, released; G5-R14 supersedes G5-R6",
        ["G5-R14"],
    ),
    "G7": ("the other thirteen G7 goals are locked by 0.5.0, released", ["G7-R14"]),
    "G8": (
        "G8 is split across 0.10.0, 0.11.0 and 0.14.0, all released",
        ["G8-R15", "G8-R16", "G8-R17", "G8-R18"],
    ),
    "G10": (
        "no version schedules G10; what it requires, D4, D6 and G1, is locked by 0.11.0 at the latest, all released",
        [f"G10-R{n}" for n in range(1, 14)],
    ),
    # The companion app takes no release of its own yet (30-repos/lemonfiber-companion.md),
    # so nothing schedules N1, and nothing that requires N1 can be scheduled before it.
    "N1": (
        "what N1 requires is locked by 0.11.0 at the latest, all released; the app takes no release",
        [f"N1-R{n}" for n in range(1, 73)],
    ),
    "N11": (
        "N11 requires N1, which no version schedules, and E4, locked by 0.14.0, released",
        [f"N11-R{n}" for n in range(1, 11)],
    ),
    "N15": (
        "N15 requires N1, which no version schedules, and G2, locked by 0.9.0, released",
        [f"N15-R{n}" for n in range(1, 11)],
    ),
    "N18": (
        "N18 requires N1, which no version schedules, and B1, whose last goals 0.17.0 locks",
        [f"N18-R{n}" for n in range(1, 10)],
    ),
    "N2": (
        "N2 requires N1, which no version schedules, and C1, C3 and G7, locked by 0.8.0 at the latest, all released",
        [f"N2-R{n}" for n in range(1, 23)],
    ),
    # N3-R8 is withdrawn, and a withdrawn row is never a goal.
    "N3": (
        "N3 requires N1, which no version schedules, and D4 and D6, locked by 0.11.0, released",
        [f"N3-R{n}" for n in range(1, 17) if n != 8],
    ),
    "N4": (
        "N4 requires N1, which no version schedules, and G3, locked by 0.10.0 at the latest, released",
        [f"N4-R{n}" for n in range(1, 25)],
    ),
    "N5": (
        "N5 requires N1, which no version schedules, F4, locked by 0.16.0, released, and F5, locked by 0.17.0",
        [f"N5-R{n}" for n in range(1, 14)],
    ),
    "N6": (
        "N6 requires N1, which no version schedules, and E3, locked by 0.14.0 at the latest, released",
        [f"N6-R{n}" for n in range(1, 12)],
    ),
    "N8": (
        "N8 requires N1, which no version schedules, and D2, locked by 0.4.0, released",
        [f"N8-R{n}" for n in range(1, 10)],
    ),
    "N9": (
        "N9 requires N1, which no version schedules, and D6, locked by 0.11.0, released",
        [f"N9-R{n}" for n in range(1, 12)],
    ),
    "N10": (
        "N10 requires N1, which no version schedules, and G8, locked by 0.14.0 at the latest, released",
        [f"N10-R{n}" for n in range(1, 13)],
    ),
    "N12": (
        "N12 requires N1, which no version schedules, and D5, locked by 0.12.0, released",
        [f"N12-R{n}" for n in range(1, 11)],
    ),
    "N14": (
        "N14 requires N1, which no version schedules, and E2, locked by 0.14.0, released",
        [f"N14-R{n}" for n in range(1, 9)],
    ),
    "N16": (
        "N16 requires N1, which no version schedules, and K2, locked by 0.22.0",
        [f"N16-R{n}" for n in range(1, 15)],
    ),
    "N17": (
        "N17 requires N1, which no version schedules, and B9, locked by 0.22.0",
        [f"N17-R{n}" for n in range(1, 12)],
    ),
    "N19": (
        "N19 requires N1, which no version schedules, and F1, locked by 0.15.0, released",
        [f"N19-R{n}" for n in range(1, 11)],
    ),
    "N20": (
        "N20 requires N1, which no version schedules, and F8, locked by 0.18.0",
        [f"N20-R{n}" for n in range(1, 11)],
    ),
}


def declared() -> dict[str, str]:
    """The table flattened to one entry per requirement, against its note."""
    return {
        rid: note
        for note, ids in AWAITING_A_VERSION.values()
        for rid in ids
    }


def accepted_requirements(root: pathlib.Path) -> dict[str, str]:
    """Every requirement an accepted feature defines, against the file defining it.

    Less the rows a feature keeps only to retire a number. A withdrawn row is not
    a requirement waiting for a version — OPS-R30 forbids it ever being a goal —
    so counting it here asks for a lock the same rule refuses to allow.
    """
    found: dict[str, str] = {}
    for md in sorted((root / FEATURES).rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        status = STATUS.search(text)
        if status is None or status.group(1) != "accepted":
            continue
        retired = set(REQ_RETIRED_ROW.findall(text))
        for rid in REQ_DEF.findall(text):
            if rid not in retired:
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
        if rid not in locked and rid not in declared()
    )


def stale(defined: dict[str, str], locked: set[str]) -> list[str]:
    """Declared entries that have stopped being true, so the list cannot outlive them."""
    gone = []
    for rid in sorted(declared()):
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
        f"{len(defined)} accepted requirements, {len(declared())} awaiting a version"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
