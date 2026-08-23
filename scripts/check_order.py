#!/usr/bin/env python3
"""Refuse a schedule that ships a feature before something it requires.

A feature's `requires:` are the features it cannot meet its own acceptance
criteria without — a notification channel to notify through, a dashboard to
surface on, an error model to express a remedy in. Scheduling one before its
requirements is not a judgement call that might be fine; it is a version that
cannot be finished, discovered months later by whoever tries.

`relates:` is the other kind of link — worth reading, not needed to build. It is
deliberately not checked here, because conflating the two is what let sixty-seven
of these accumulate unnoticed.

Exit non-zero listing every inversion, so one run shows the whole picture rather
than the first of them.
"""

import pathlib
import re
import sys
import tomllib

FEATURES = pathlib.Path("10-functional/features")
VERSIONS = pathlib.Path("70-operations/versions")
ID = re.compile(r"^id:\s*(\S+)", re.MULTILINE)
REQUIRES = re.compile(r"^requires:\s*\[(.*?)\]\s*$", re.MULTILINE)


def _released_in() -> tuple[dict[str, str], dict[str, int], set[str]]:
    """Which version each feature is scheduled in, their order, and which shipped.

    A released version is history rather than a plan: nothing can be moved into or
    out of it, so an inversion it carries is a fact to record and not a fault to
    fix. Those are reported once, as a note, and never fail the check.
    """
    order, schedule, shipped = [], {}, set()
    for path in sorted(VERSIONS.glob("*.toml")):
        if path.stem == "TEMPLATE":
            continue
        order.append(path.stem)
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if data.get("status") == "released":
            shipped.add(path.stem)
        for goal in data.get("goals", []):
            schedule.setdefault(goal.split("-R")[0], path.stem)
    order.sort(key=lambda v: [int(part) for part in v.split(".")])
    return schedule, {version: i for i, version in enumerate(order)}, shipped


def _requirements() -> dict[str, list[str]]:
    """Each feature's hard dependencies."""
    wants = {}
    for path in FEATURES.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        found, needs = ID.search(text), REQUIRES.search(text)
        if found and needs:
            wants[found.group(1)] = [
                part.strip() for part in needs.group(1).split(",") if part.strip()
            ]
    return wants


def _inversion(feature, mine, need, schedule, rank) -> str | None:
    """What is wrong with this one requirement, where anything is."""
    theirs = schedule.get(need)
    if theirs is None:
        return f"{feature} requires {need}, which no version schedules"
    if rank[theirs] > rank[mine]:
        return (
            f"{feature} ships in {mine} but requires {need}, which lands in {theirs}"
        )
    return None


def _gather(schedule, rank, shipped) -> tuple[list[str], list[str]]:
    """Every inversion, split into what must be fixed and what merely happened."""
    problems, historical = [], []
    for feature, needs in sorted(_requirements().items()):
        mine = schedule.get(feature)
        if mine is None:
            continue
        for need in needs:
            said = _inversion(feature, mine, need, schedule, rank)
            if said:
                (historical if mine in shipped else problems).append(said)
    return problems, historical


def main() -> None:
    schedule, rank, shipped = _released_in()
    problems, historical = _gather(schedule, rank, shipped)
    for note in historical:
        print(f"::notice::already shipped, recorded not enforced — {note}")
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        sys.exit(f"{len(problems)} feature(s) scheduled before something they require")
    print(f"order ok: {len(schedule)} scheduled features, none before what it requires")


if __name__ == "__main__":
    main()
