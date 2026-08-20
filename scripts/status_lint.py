#!/usr/bin/env python3
"""The implementation tracker says only things the spec can back — OPS-R34.

`gate.py` asks whether a version's goals are met. This asks the prior question:
whether the tracker's *claims* correspond to anything. Three ways they can stop
doing so, each found in the field rather than imagined:

  1. A range that overshoots. `G7-R1..R14` read as met a requirement nobody
     wrote — G7 has thirteen. The gate expands ranges, so an off-by-one there
     mints a requirement and marks it done in one stroke, and nothing complains
     because no version locks it either.

  2. A milestone heading naming the wrong version. A milestone spans several
     versions and the boundaries do not line up, so `Mn` is not `0.n.0`. A
     heading that guesses makes a released version look like it shipped with
     unfinished deliverables — or hides that it did.

  3. A tick on a requirement no version locks. Work that cannot be released,
     recorded as though it had been.

Usage:
  status_lint.py --status <IMPLEMENTATION-STATUS.md> --spec <spec repo root>

Exit 0 = every claim backed; 1 = claims that are not (named); 2 = usage.
"""
from __future__ import annotations
import argparse, pathlib, re, sys, tomllib

CITE = re.compile(r"\b([A-Z]+\d*-R\d+)\b")
RANGE = re.compile(r"\b([A-Z]+\d*)-R(\d+)\.\.(?:[A-Z]+\d*-)?R?(\d+)\b")
HEADING = re.compile(r"^##\s+(M[0-9.]+)\b")
VERSION = re.compile(r"`(\d+\.\d+\.\d+)`")
# How far a heading's prose reaches. A milestone names its versions in the
# sentence under the heading, not twelve rows into the table.
PREAMBLE = 9


def defined(spec: pathlib.Path) -> dict[str, int]:
    """The highest requirement number each feature actually defines."""
    highest: dict[str, int] = {}
    # Read each ID whole, then split it: the feature prefix is not a fixed width.
    for doc in spec.rglob("*.md"):
        for ident in CITE.findall(doc.read_text(encoding="utf-8")):
            feature, _, number = ident.partition("-R")
            highest[feature] = max(highest.get(feature, 0), int(number))
    return highest


def manifests(spec: pathlib.Path) -> tuple[dict[str, set[str]], set[str]]:
    """Which versions each milestone ships in, and every goal any of them locks."""
    milestones: dict[str, set[str]] = {}
    locked: set[str] = set()
    for path in (spec / "70-operations" / "versions").glob("*.toml"):
        if path.stem == "TEMPLATE":
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if milestone := data.get("milestone"):
            milestones.setdefault(milestone, set()).add(path.stem)
        locked.update(data.get("goals", []))
    return milestones, locked


def claimed_ranges(lines: list[str]) -> list[tuple[int, str, int]]:
    """Every range endpoint the tracker claims, with the line it is on."""
    found = []
    for number, line in enumerate(lines, start=1):
        for feature, _, last in RANGE.findall(line):
            found.append((number, feature, int(last)))
    return found


def ticked(lines: list[str]) -> set[str]:
    """Every requirement the tracker marks done — the same reading `gate.py` takes."""
    done: set[str] = set()
    for line in lines:
        if "✅" not in line:
            continue
        for feature, first, last in RANGE.findall(line):
            done.update(f"{feature}-R{n}" for n in range(int(first), int(last) + 1))
        done.update(CITE.findall(line))
    return done


def headings(lines: list[str]) -> list[tuple[int, str, set[str]]]:
    """Each milestone heading and the versions its opening prose claims."""
    found = []
    for index, line in enumerate(lines):
        if match := HEADING.match(line):
            prose = "\n".join(lines[index : index + PREAMBLE])
            found.append((index + 1, match.group(1), set(VERSION.findall(prose))))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True)
    parser.add_argument("--spec", required=True)
    args = parser.parse_args()

    status = pathlib.Path(args.status)
    spec = pathlib.Path(args.spec)
    if not status.is_file():
        print(f"::error::no tracker at {status}")
        return 2
    if not (spec / "70-operations" / "versions").is_dir():
        print(f"::error::no version manifests under {spec}")
        return 2

    lines = status.read_text(encoding="utf-8").splitlines()
    highest = defined(spec)
    by_milestone, locked = manifests(spec)
    faults: list[str] = []

    for line_number, feature, last in claimed_ranges(lines):
        top = highest.get(feature)
        if top is not None and last > top:
            faults.append(
                f"{status}:{line_number}: claims {feature}-R{last}, but {feature} "
                f"defines up to R{top}"
            )

    for line_number, milestone, claims in headings(lines):
        ships_in = by_milestone.get(milestone)
        if not ships_in:
            continue
        # Omission is the failure to catch. Every heading that misled named one
        # version and left the rest out — a milestone that ships in two and admits
        # to one reads as though the other's work were somebody else's. Naming an
        # extra version is not an error: a milestone whose groundwork shipped early
        # under another's version should be free to say so.
        if missing := ships_in - claims:
            faults.append(
                f"{status}:{line_number}: {milestone} ships in "
                f"{', '.join(sorted(ships_in))} but does not name "
                f"{', '.join(sorted(missing))}"
            )

    if orphans := sorted(ticked(lines) - locked):
        faults.append(
            f"{status}: marked done but locked by no version: {', '.join(orphans)}"
        )

    for fault in faults:
        print(f"::error::{fault}")
    if faults:
        print(f"\nstatus-lint: {len(faults)} claim(s) the spec does not back.")
        return 1
    print("status-lint: every claim in the tracker is backed by the spec.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
