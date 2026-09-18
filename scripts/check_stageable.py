#!/usr/bin/env python3
"""Validate a version is stageable — OPS-R30, OPS-R52, OPS-R58.

Refuses unless the version's manifest exists and is `planned`, no other version
is already `staged`/`releasable` (the train is serial), and every goal is a
requirement ID the spec actually defines and has not withdrawn. On success,
prints the target repos, one per line, for the workflow to iterate.

Usage:  check_stageable.py X.Y.Z
Exit 0 = stageable, non-zero with a named reason otherwise.
"""
from __future__ import annotations

import pathlib
import sys
import tomllib

from integrity import elsewhere
from manifest_repos import cut, searched
from patterns import IN_FLIGHT, REQ_DEF, REQ_RETIRED_ROW
from patterns import VERSION as VERSION_RE

VERSIONS = pathlib.Path("70-operations/versions")


def defined_ids() -> tuple[set[str], set[str]]:
    """Every identifier the spec defines, and the subset kept only to retire a number.

    The two are returned together because a goal can fail on either and the
    refusals say different things. An identifier the spec never defined is a typo;
    one whose row reads *Withdrawn* is a number held open so nothing reuses it, and
    locking it is the thing OPS-R30 names outright.
    """
    defined: set[str] = set()
    retired: set[str] = set()
    for md in pathlib.Path(".").rglob("*.md"):
        if elsewhere(md, pathlib.Path(".")):
            continue
        text = md.read_text(encoding="utf-8", errors="ignore")
        defined.update(REQ_DEF.findall(text))
        retired.update(REQ_RETIRED_ROW.findall(text))
    return defined, retired


def in_flight(exclude: str) -> str | None:
    """Another version already in flight, which is what keeps the train serial.

    Past the template, which is a file meant to be read as an example: a real
    status written into it to document the lifecycle would refuse every staging
    attempt, naming a version that is not one.
    """
    for other in VERSIONS.glob("*.toml"):
        if other.name == exclude or other.stem == "TEMPLATE":
            continue
        status = tomllib.loads(other.read_text(encoding="utf-8")).get("status")
        if status in IN_FLIGHT:
            return f"{other.name} is already {status}"
    return None


def unstageable(manifest: pathlib.Path, data: dict) -> list[str]:
    """Every reason this version is not stageable, rather than the first of them.

    Four independent questions, and a manifest can fail several at once. Asked
    together because each answer costs a CI round trip: a version that is still
    draft, clashes with one in flight, locks a withdrawn goal and names nowhere to
    search used to report one of those four, and the author found the rest one push
    at a time.
    """
    problems: list[str] = []
    if data.get("status") != "planned":
        problems.append(f"{manifest.name} is '{data.get('status')}', not planned")
    clash = in_flight(manifest.name)
    if clash:
        problems.append(f"{clash}; one version at a time (OPS-R52)")

    # A version locking nothing is the shape every gate downstream refuses, and
    # staging is where it is cheapest to say so. The release gate and the no-stub
    # gate both stop on an empty goal set; staging let one through, so the answer
    # arrived at the end of the train rather than at the start of it.
    goals = data.get("goals", [])
    if not goals:
        problems.append(
            f"{manifest.name} locks no goal, so staging it would put a version on the "
            "train with nothing to prove and nothing to fail"
        )
    else:
        # Read once. It walks every page in the repository, and asking it inside the
        # comprehension walked them all again for every goal the manifest locks.
        defined, retired = defined_ids()
        unknown = [g for g in goals if g not in defined]
        if unknown:
            problems.append(f"goals not defined in the spec: {', '.join(unknown)}")
        withdrawn = [g for g in goals if g in retired]
        if withdrawn:
            problems.append(
                "withdrawn or superseded, so not lockable as a goal "
                f"(OPS-R30): {', '.join(withdrawn)}"
            )

    # Where the gate will look, checked at staging rather than discovered at
    # release (OPS-R58). A manifest naming a repository nobody can search is a
    # gate that reports goals unmet for a reason that is not about the work, and
    # staging is the last moment anybody is looking at this file on purpose.
    if not searched(data):
        problems.append(f"{manifest.name} names nowhere for the gate to search")
    return problems


def main() -> int:
    if len(sys.argv) != 2 or not VERSION_RE.match(sys.argv[1]):
        sys.exit("::error::usage: check_stageable.py X.Y.Z")
    manifest = VERSIONS / f"{sys.argv[1]}.toml"
    if not manifest.is_file():
        sys.exit(f"::error::no manifest at {manifest}")
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))

    problems = unstageable(manifest, data)
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        return 1

    print("\n".join(cut(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
