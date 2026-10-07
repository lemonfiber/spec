#!/usr/bin/env python3
"""The version in flight, and what blocks it — OPS-R44, OPS-R83.

Every run of the report asks the release gate about one version: the first in
train order that is `staged` or `in_progress`, whose goals are locked and not yet
all met. A version already `releasable` waits on execute, and one `planned` has no
locked goals to judge. A version moves to `releasable` only when no blocker is
listed in its manifest, each as a table naming `what` blocks it and `where` it is
being dealt with.

Usage:
  in_flight.py version                 print the version in flight, or nothing
  in_flight.py blockers --version X    print each blocker; exit 1 where one is listed

Run from the spec checkout. Exit 0 = answered (and, for `blockers`, nothing
blocks); 1 = a blocker is listed; 2 = no such manifest, or one that cannot be
read.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import tomllib

from patterns import ordered

VERSIONS = pathlib.Path("70-operations/versions")
#: The states a version is judged in: goals locked, not yet releasable.
JUDGED = ("staged", "in_progress")


def manifests() -> list[dict]:
    """Every version manifest, the template apart, in train order."""
    found = [tomllib.loads(path.read_text(encoding="utf-8"))
             for path in VERSIONS.glob("*.toml") if path.stem != "TEMPLATE"]
    return sorted(found, key=lambda data: ordered(data["version"]))


def in_flight() -> str | None:
    """The first version in train order whose goals are locked and judged."""
    return next((data["version"] for data in manifests()
                 if data.get("status") in JUDGED), None)


def blockers(version: str) -> list[str]:
    """Each blocker a version's manifest lists, as one line."""
    data = tomllib.loads((VERSIONS / f"{version}.toml").read_text(encoding="utf-8"))
    return [f"{entry.get('what', '(unnamed)')} — {entry.get('where', 'nowhere named')}"
            for entry in data.get("blockers", [])]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("version")
    asked = sub.add_parser("blockers")
    asked.add_argument("--version", required=True)
    args = parser.parse_args()
    try:
        if args.command == "version":
            print(in_flight() or "")
            return 0
        listed = blockers(args.version)
    except (OSError, tomllib.TOMLDecodeError, KeyError) as broken:
        print(f"::error::{broken}")
        return 2
    for line in listed:
        print(f"::error::{args.version} is blocked: {line}")
    return 1 if listed else 0


if __name__ == "__main__":
    sys.exit(main())
