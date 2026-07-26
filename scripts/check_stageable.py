#!/usr/bin/env python3
"""Validate a version is stageable — OPS-R30, OPS-R52.

Refuses unless the version's manifest exists and is `planned`, no other version
is already `staged`/`releasable` (the train is serial), and every goal is a
requirement ID the spec actually defines. On success, prints the target repos,
one per line, for the workflow to iterate.

Usage:  check_stageable.py X.Y.Z
Exit 0 = stageable, non-zero with a named reason otherwise.
"""
from __future__ import annotations
import re, sys, tomllib, pathlib

VERSIONS = pathlib.Path("70-operations/versions")
REQ_DEF = re.compile(r"^\|\s*\*\*([A-Z]+\d*-R\d+)\*\*\s*\|", re.M)
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def defined_ids() -> set[str]:
    ids: set[str] = set()
    for md in pathlib.Path(".").rglob("*.md"):
        if ".git" in md.parts:
            continue
        ids.update(REQ_DEF.findall(md.read_text(encoding="utf-8", errors="ignore")))
    return ids


def in_flight(exclude: str) -> str | None:
    for other in VERSIONS.glob("*.toml"):
        if other.name == exclude:
            continue
        status = tomllib.loads(other.read_text(encoding="utf-8")).get("status")
        if status in ("staged", "releasable"):
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
    unknown = [g for g in data.get("goals", []) if g not in defined_ids()]
    if unknown:
        sys.exit(f"::error::goals not defined in the spec: {', '.join(unknown)}")

    print("\n".join(data.get("repos", [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
