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
be the error.

The architecture is read too. An `ARCH-R` row in an accepted document under
`20-architecture/` is a requirement like any other, and one no version locks is
reached by no release gate. Some are not deliverables at all, and those are
exempted by name below with one of three reasons: the row restates functional
requirements some version locks, it is a principle the design is held to rather
than something to build, or it is dormant until a named trigger.

Usage:  check_goal_coverage.py [--root PATH]
Exit 0 = every accepted requirement is locked, declared or exempted below,
1 = one is none of those, or an entry below has stopped being true.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import tomllib

from patterns import REQ_DEF, REQ_RETIRED_ROW

FEATURES = "10-functional"
ARCHITECTURE = "20-architecture"
VERSIONS = "70-operations/versions"
STATUS = re.compile(r"^status:\s*(\S+)", re.MULTILINE)
# An architecture document states its standing in its body rather than in frontmatter.
DOCUMENT_STATUS = re.compile(r"^\*\*Status:\*\*\s*(\w+)", re.MULTILINE)

# Requirements that predate this check and have no version yet, against where the
# rest of their feature is locked — which is what somebody deciding needs.
#
# Keyed by feature, because that is what the note is a fact about, and architecture
# rows under `ARCH`. Written per requirement it was the same sentence four times
# over for F3 and again for G8, and four copies of a sentence are four things to
# correct when one of those versions moves.
#
# Not a licence to leave one here. An entry is a debt with a name on it, and the
# check refuses an entry that has stopped being true: one that some version has
# since locked, or that no accepted document defines any more. So the list empties
# itself as the train picks these up, and cannot quietly outlive them.
#
# None of these is assigned here, deliberately. Which version carries a
# requirement is a decision about what ships when, and a gate is the wrong place
# to make one.
AWAITING_A_VERSION = {
    # The one entry here that was locked and came back. 0.15.0 shipped without it,
    # by a lane that never ran the gate, and the manifest records why. It closes on
    # a hand-run with a real VPN provider on the owner's own hardware — not on a
    # decision, and not on anything a runner can reach.
    "F1": ("the other thirteen F1 goals are locked by 0.15.0, released", ["F1-R1"]),
    # The companion keeps these two, as it keeps N1's app side, and takes no release.
    # Its tests/Arch/TheNamesThisProductGivesTest.php holds G2-R14 and
    # tests/Templates/EveryTargetIsBigEnoughToHitTest.php holds G3-R16, and
    # app-modules/operator/tests/View/Components/ScreenClosesTest.php holds G3-R17.
    "G2": (
        "the companion keeps G2-R14 and takes no release; G2-R15 binds every surface and no version schedules it yet; the other thirteen G2 goals are locked by 0.9.0, released",
        ["G2-R14", "G2-R15"],
    ),
    "G3": (
        "the companion keeps G3-R16 and G3-R17 and takes no release; the rest of G3 is split across 0.9.0 and 0.10.0, both released",
        ["G3-R16", "G3-R17"],
    ),
    "G10": (
        "0.18.0 locks the G10 goals the core answers for; playback and the door a member faces wait on the core",
        ["G10-R4", "G10-R7", "G10-R8", "G10-R12", "G10-R13"],
    ),
    # The companion app takes no release of its own yet (30-repos/lemonfiber-companion.md),
    # so nothing schedules N1's app side. Its stack side, the pairing material the stack
    # produces and the certificate it announces, is locked by 0.17.0.
    "N1": (
        "what N1 requires is locked by 0.11.0 at the latest, all released; the app takes no release, and 0.17.0 locks the stack's side of pairing",
        [f"N1-R{n}" for n in range(1, 73) if n not in (18, 47, 48, 49, 62)],
    ),
    "N11": (
        "N11 requires N1, whose app side no version schedules, and E4, locked by 0.14.0, released",
        [f"N11-R{n}" for n in range(1, 11)],
    ),
    "N15": (
        "N15 requires N1, whose app side no version schedules, and G2, locked by 0.9.0, released",
        [f"N15-R{n}" for n in range(1, 12)],
    ),
    "N18": (
        "N18 requires N1, whose app side no version schedules, and B1, whose last goal 0.18.0 locks",
        [f"N18-R{n}" for n in range(1, 11)],
    ),
    "N2": (
        "N2 requires N1, whose app side no version schedules, and C1, C3 and G7, locked by 0.8.0 at the latest, all released",
        [f"N2-R{n}" for n in range(1, 25)],
    ),
    # N3-R8 is withdrawn, and a withdrawn row is never a goal.
    "N3": (
        "N3 requires N1, whose app side no version schedules, and D4 and D6, locked by 0.11.0, released",
        [f"N3-R{n}" for n in range(1, 17) if n != 8],
    ),
    "N4": (
        "N4 requires N1, whose app side no version schedules, and G3, locked by 0.10.0 at the latest, released",
        [f"N4-R{n}" for n in range(1, 25)],
    ),
    "N5": (
        "N5 requires N1, whose app side no version schedules, F4, whose last goals 0.18.0 locks, and F5, whose last goals 0.17.0 locks",
        [f"N5-R{n}" for n in range(1, 14)],
    ),
    "N6": (
        "N6 requires N1, whose app side no version schedules, and E3, locked by 0.14.0 at the latest, released",
        [f"N6-R{n}" for n in range(1, 12)],
    ),
    "N8": (
        "N8 requires N1, whose app side no version schedules, and D2, locked by 0.4.0, released",
        [f"N8-R{n}" for n in range(1, 10)],
    ),
    "N9": (
        "N9 requires N1, whose app side no version schedules, and D6, locked by 0.11.0, released",
        [f"N9-R{n}" for n in range(1, 12)],
    ),
    "N10": (
        "N10 requires N1, whose app side no version schedules, and G8, locked by 0.14.0 at the latest, released",
        [f"N10-R{n}" for n in range(1, 13)],
    ),
    "N12": (
        "N12 requires N1, whose app side no version schedules, and D5, locked by 0.12.0, released",
        [f"N12-R{n}" for n in range(1, 11)],
    ),
    # N13-R8 is withdrawn, and a withdrawn row is never a goal.
    "N13": (
        "N13 requires N1, whose app side no version schedules, and A6, locked by 0.13.0, released",
        [f"N13-R{n}" for n in range(1, 21) if n != 8],
    ),
    "N14": (
        "N14 requires N1, whose app side no version schedules, and E2, locked by 0.14.0, released",
        [f"N14-R{n}" for n in range(1, 9)],
    ),
    "N16": (
        "N16 requires N1, whose app side no version schedules, and K2, locked by 0.22.0",
        [f"N16-R{n}" for n in range(1, 15)],
    ),
    "N17": (
        "N17 requires N1, whose app side no version schedules, and B9, locked by 0.22.0",
        [f"N17-R{n}" for n in range(1, 12)],
    ),
    "N19": (
        "N19 requires N1, whose app side no version schedules, and F1, locked by 0.15.0, released",
        [f"N19-R{n}" for n in range(1, 11)],
    ),
    "N20": (
        "N20 requires N1, whose app side no version schedules, and F8, locked by 0.18.0",
        [f"N20-R{n}" for n in range(1, 11)],
    ),
    "N21": (
        "N21 requires N1, whose app side no version schedules, and D6, whose last goals 0.17.0 locks",
        [f"N21-R{n}" for n in range(1, 11)],
    ),
    "N22": (
        "N22 requires N1, whose app side no version schedules, and C4, locked by 0.7.0, released",
        [f"N22-R{n}" for n in range(1, 11)],
    ),
    "N23": (
        "N23 requires N1, whose app side no version schedules, B10, locked by 0.15.0, released, and C7, locked by 0.6.0, released",
        [f"N23-R{n}" for n in range(1, 14)],
    ),
    "N24": (
        "N24 requires N1, whose app side no version schedules, and D2 and D3, locked by 0.4.0, released",
        [f"N24-R{n}" for n in range(1, 11)],
    ),
    "N25": (
        "N25 requires N1, whose app side no version schedules, N5, which awaits a version itself, F5, whose last goals 0.17.0 locks, and F6, whose last goals 0.18.0 locks",
        [f"N25-R{n}" for n in range(1, 11)],
    ),
    "N26": (
        "N26 requires N1, whose app side no version schedules, H1, H2 and H3, locked by 0.19.0, H6 and H8, locked by 0.20.0, and K1, locked by 0.22.0",
        [f"N26-R{n}" for n in range(1, 20)],
    ),
    "N27": (
        "N27 requires N1 and N4, whose app side no version schedules; what they require is locked by 0.11.0 at the latest, released",
        [f"N27-R{n}" for n in range(1, 23)],
    ),
    "N28": (
        "N28 requires N1 and N2, whose app side no version schedules, and N27; what N1 and N2 require is locked by 0.11.0 at the latest, released",
        [f"N28-R{n}" for n in range(1, 13)],
    ),
    "N7": (
        "N7 requires N1, whose app side no version schedules, and A5, locked by 0.13.0, released",
        [f"N7-R{n}" for n in range(1, 19)],
    ),
}

# Architecture rows no version locks, each with why none needs to.
#
# Keyed by requirement, because the reason is a fact about the row. There are three
# reasons and no others:
#
#   `restates <IDs>`        the row says again what functional requirements say,
#                           every one of which a version locks, so the train reaches
#                           it through them
#   `principle`             a rule every change is held to, which no one change
#                           delivers
#   `dormant until <what>`  a rule with nothing to act on until the named trigger
#
# The terms are AWAITING_A_VERSION's. The check refuses an exemption that has
# stopped being true: one a version has since locked, one no accepted architecture
# document defines, one whose reason is none of the three, and a restatement naming
# a requirement no version locks. A row that is none of these is work, and work is
# locked by a version.
EXEMPT_FROM_A_VERSION = {
    "ARCH-R1": "principle",
    "ARCH-R7": "dormant until a second schema generation exists, which ARCH-R43 forbids before the first release candidate",
    "ARCH-R8": "dormant until the first release candidate, before which ARCH-R43 holds the schema in place",
    "ARCH-R16": "principle",
    "ARCH-R17": "restates C1-R3",
    "ARCH-R21": "restates C5-R1, C5-R3, C5-R11, C5-R13",
    "ARCH-R22": "restates D9-R5",
    "ARCH-R24": "principle",
    "ARCH-R26": "restates D1-R4, D1-R5, C9-R3",
    "ARCH-R29": "restates A2-R7",
    "ARCH-R31": "restates A2-R7",
    "ARCH-R32": "restates B8-R2, B8-R3",
    "ARCH-R33": "restates A2-R6",
    "ARCH-R37": "principle",
    "ARCH-R39": "principle",
}

REQUIREMENT = re.compile(r"^[A-Z]+\d*-R\d+$")
RESTATES = "restates "
DORMANT = "dormant until "


def restated_by(reason: str) -> list[str] | None:
    """What an exemption's reason restates, `[]` for one that restates nothing.

    `None` for a reason that is none of the three: `restates <IDs>` with the IDs
    comma-separated, `principle`, or `dormant until <trigger>` with a trigger.
    """
    if reason == "principle":
        return []
    if reason.startswith(DORMANT):
        return [] if reason[len(DORMANT):].strip() else None
    if not reason.startswith(RESTATES):
        return None
    ids = reason[len(RESTATES):].split(", ")
    return ids if all(REQUIREMENT.match(rid) for rid in ids) else None


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


def architecture_requirements(root: pathlib.Path) -> dict[str, str]:
    """Every requirement an accepted architecture document defines, against its file.

    Accepted by the document's own `**Status:**` line, and less its retired rows,
    on the same terms as a feature.
    """
    found: dict[str, str] = {}
    for md in sorted((root / ARCHITECTURE).rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        status = DOCUMENT_STATUS.search(text)
        if status is None or status.group(1) != "Accepted":
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
    """Accepted requirements no version locks and this file neither declares nor exempts."""
    return sorted(
        f"{rid} is defined in {where} and no version locks it"
        for rid, where in defined.items()
        if rid not in locked and rid not in declared() and rid not in EXEMPT_FROM_A_VERSION
    )


def stale(defined: dict[str, str], locked: set[str]) -> list[str]:
    """Declared entries that have stopped being true, so the list cannot outlive them."""
    gone = []
    for rid in sorted(declared()):
        if rid in locked:
            gone.append(f"{rid} is locked by a version now — delete its line")
        elif rid not in defined:
            gone.append(f"{rid} is defined by no accepted document — delete its line")
    return gone


def unreached(rid: str, ids: list[str], everything: dict[str, str], locked: set[str]) -> list[str]:
    """What a restatement names that no version reaches."""
    gone = []
    for restated in ids:
        if restated not in everything:
            gone.append(f"{rid} restates {restated}, which no accepted document defines")
        elif restated not in locked:
            gone.append(f"{rid} restates {restated}, which no version locks — lock one of them")
    return gone


def stale_exemptions(
    architecture: dict[str, str], everything: dict[str, str], locked: set[str]
) -> list[str]:
    """Exemptions that have stopped being true, on AWAITING_A_VERSION's terms.

    A restatement is held to what it restates: the row is exempt because a version
    reaches it through the requirements it names, so each of them has to be defined
    and locked. One that is not leaves the row reached by nothing.
    """
    gone = []
    for rid, reason in sorted(EXEMPT_FROM_A_VERSION.items()):
        if rid in locked:
            gone.append(f"{rid} is locked by a version now — delete its exemption")
            continue
        if rid not in architecture:
            gone.append(f"{rid} is defined by no accepted architecture document — delete its exemption")
            continue
        ids = restated_by(reason)
        if ids is None:
            gone.append(
                f"{rid} is exempted as {reason!r}, which is not `restates <IDs>`, "
                "`principle` or `dormant until <trigger>`"
            )
            continue
        gone.extend(unreached(rid, ids, everything, locked))
    return gone


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="the spec checkout to read")
    root = pathlib.Path(ap.parse_args().root).resolve()

    defined = accepted_requirements(root)
    if not defined:
        print(f"::error::no accepted feature was found under {root / FEATURES}")
        return 1

    # A tree with an architecture and nothing read out of it is a reading that
    # failed, and reporting every row locked from it would be a pass over nothing.
    architecture = architecture_requirements(root)
    if (root / ARCHITECTURE).is_dir() and not architecture:
        print(f"::error::no accepted architecture document under {root / ARCHITECTURE} defines a requirement")
        return 1

    everything = {**defined, **architecture}
    locked = locked_goals(root)
    problems = (
        unscheduled(everything, locked)
        + stale(everything, locked)
        + stale_exemptions(architecture, everything, locked)
    )

    for problem in problems:
        print(f"::error::{problem}")

    if problems:
        print(
            "::error::A requirement no version locks is scheduled by nothing and "
            "refused by nothing. Lock it in a manifest's `goals`, declare a feature's "
            "in AWAITING_A_VERSION with where the rest of its feature sits, or exempt "
            "an architecture row in EXEMPT_FROM_A_VERSION with one of its three "
            "reasons (OPS-R30)."
        )
        return 1

    print(
        f"{len(defined)} accepted requirements and {len(architecture)} architecture "
        f"requirements, {len(declared())} awaiting a version and "
        f"{len(EXEMPT_FROM_A_VERSION)} exempt from one"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
