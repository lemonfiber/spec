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
        if ".git" in md.parts:
            continue
        text = md.read_text(encoding="utf-8", errors="ignore")
        defined.update(REQ_DEF.findall(text))
        retired.update(REQ_RETIRED_ROW.findall(text))
    return defined, retired


def in_flight(exclude: str) -> str | None:
    for other in VERSIONS.glob("*.toml"):
        if other.name == exclude:
            continue
        status = tomllib.loads(other.read_text(encoding="utf-8")).get("status")
        if status in IN_FLIGHT:
            return f"{other.name} is already {status}"
    return None


def main() -> int:
    if len(sys.argv) != 2 or not VERSION_RE.match(sys.argv[1]):
        sys.exit("::error::usage: check_stageable.py X.Y.Z")
    manifest = VERSIONS / f"{sys.argv[1]}.toml"
    if not manifest.is_file():
        sys.exit(f"::error::no manifest at {manifest}")
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))

    if data.get("status") != "planned":
        sys.exit(f"::error::{manifest.name} is '{data.get('status')}', not planned")
    clash = in_flight(manifest.name)
    if clash:
        sys.exit(f"::error::{clash}; one version at a time (OPS-R52)")
    # Read once. It walks every page in the repository, and asking it inside the
    # comprehension walked them all again for every goal the manifest locks.
    defined, retired = defined_ids()
    goals = data.get("goals", [])
    unknown = [g for g in goals if g not in defined]
    if unknown:
        sys.exit(f"::error::goals not defined in the spec: {', '.join(unknown)}")
    withdrawn = [g for g in goals if g in retired]
    if withdrawn:
        sys.exit(
            "::error::withdrawn or superseded, so not lockable as a goal "
            f"(OPS-R30): {', '.join(withdrawn)}"
        )

    # Where the gate will look, checked at staging rather than discovered at
    # release (OPS-R58). A manifest naming a repository nobody can search is a
    # gate that reports goals unmet for a reason that is not about the work, and
    # staging is the last moment anybody is looking at this file on purpose.
    if not searched(data):
        sys.exit(f"::error::{manifest.name} names nowhere for the gate to search")

    print("\n".join(cut(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
