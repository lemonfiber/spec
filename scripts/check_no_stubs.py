#!/usr/bin/env python3
"""No version ships a requirement it has not finished — OPS-R54.

`gate.py` asks whether every locked goal is *satisfied*: cited by a merged commit
and ticked in the tracker. This asks the prior question about the same goals — is
each of them **built** — and answers it from the feature catalogue, which is where
the project records how far a thing has got.

It reads per requirement rather than per feature, and that is the whole of the
rule's mechanism. The first cut of this gate asked whether every *feature* a
version touches is finished, which is what OPS-R54's sentence used to say. Nothing
could satisfy it: partial locking is the norm here rather than the exception — 24
of 25 manifests lock only part of at least one feature, and `0.1.0` locks two of
B1's fifteen — so a feature spanning two versions can never be finished when the
first of them ships. The rule now asks about what a version actually carries.

Three states answer for the whole feature and one does not:

  built, shipped      every requirement of it is finished, so any subset is
  planned, withdrawn  none of it is, so no subset is
  building            some are and some are not, and the catalogue does not say
                      which — so the tracker is asked, requirement by requirement

That last line is where the two records are held against each other. A `planned`
feature with ticked requirements is refused here even though `gate.py` would pass
them, because a catalogue calling a feature untouched and a tracker calling its
requirements done cannot both be right.

Two silences are refused rather than tolerated, because both would read as a pass:

  * a catalogue that reads as empty — a wrong working directory, a moved tree —
    would find no unfinished requirement and report success about nothing;
  * a `maturity` vocabulary that no longer holds the names this rule is written
    in, which is how a schema rename turns a gate off without touching it.

Usage:
  check_no_stubs.py --version X.Y.Z --status <IMPLEMENTATION-STATUS.md>

Exit 0 = every requirement the version locks is built; 1 = named ones are not;
2 = the question could not be answered.
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib

import catalogue
from gate import done_ids, within_cwd
from manifest_repos import VERSIONS_DIR, manifest_for
from patterns import REQ_DEF

#: Maturities that answer for every requirement the feature defines.
FINISHED = ("built", "shipped")
#: Maturities that answer for none of them.
UNSTARTED = ("planned", "withdrawn")
#: The one that answers for some, and says nothing about which.
PARTWAY = "building"


def vocabulary_holds(known: set[str]) -> str | None:
    """Whether the catalogue still spells the states this rule is written in."""
    wanted = (*FINISHED, *UNSTARTED, PARTWAY)
    missing = [name for name in wanted if name not in known]
    if missing:
        return (
            f"the frontmatter schema's `maturity` no longer offers "
            f"{', '.join(missing)}, so this rule is written in words the "
            "catalogue does not use — OPS-R54 and the schema have to be "
            "reconciled before this can decide anything"
        )
    return None


def requirements_of(path: str) -> set[str]:
    """Every requirement a feature doc defines."""
    with open(path, encoding="utf-8") as doc:
        return set(REQ_DEF.findall(doc.read()))


def locked_everywhere() -> set[str]:
    """Every requirement any manifest in the train locks.

    Read across the whole directory rather than from the one manifest, because the
    question it answers is about the other manifests: a requirement no version
    locks is one no release gate will ever ask about, and the only place anybody
    would notice is a run that is already looking at the feature holding it.
    """
    found: set[str] = set()
    for path in VERSIONS_DIR.glob("*.toml"):
        if path.stem == "TEMPLATE":
            continue
        found.update(tomllib.loads(path.read_text(encoding="utf-8")).get("goals", []))
    return found


def unfinished(goals: list[str], front: dict, done: set[str]) -> list[str]:
    """Which of one feature's locked goals are not built, in the order given."""
    state = front.get("maturity")
    if state in FINISHED:
        return []
    if state == PARTWAY:
        return [goal for goal in goals if goal not in done]
    return list(goals)


def grouped(goals: list[str]) -> dict[str, list[str]]:
    """The goals by the feature each names, in first-seen order."""
    found: dict[str, list[str]] = {}
    for goal in goals:
        found.setdefault(goal.partition("-R")[0], []).append(goal)
    return found


def verdict(goals: list[str], features: dict[str, dict], done: set[str],
            elsewhere_locked: set[str]) -> tuple[int, list[str]]:
    """The gate's exit code and the lines explaining it.

    Identifiers outside the feature namespaces are reported rather than dropped.
    `0.10.0` locks six `ARCH-R` goals, which name no feature and never could; a
    gate that passes over them in silence is one nobody can tell from a gate that
    looked at them and approved.
    """
    is_feature = re.compile(catalogue.id_pattern()).fullmatch
    lines: list[str] = []
    stubs: list[str] = []
    orphans: list[str] = []
    elsewhere: list[str] = []

    for feature, locked in grouped(goals).items():
        if not is_feature(feature):
            elsewhere.append(feature)
            continue
        front = features.get(feature)
        if front is None:
            print(f"::error::goal names {feature}, which the feature catalogue "
                  "does not hold — the manifest and the catalogue disagree")
            return 2, []
        defines = requirements_of(front["path"])
        short = unfinished(locked, front, done)
        stubs.extend(short)
        orphans.extend(sorted(defines - elsewhere_locked,
                              key=lambda one: int(one.partition("-R")[2])))
        scope = f"{len(locked)} of its {len(defines)}"
        built = len(locked) - len(short)
        lines.append(f"  {'✗' if short else '✓'} {feature:4} "
                     f"{front.get('maturity')!s:9} locks {scope:9} requirements, "
                     f"{built} of them built   {front.get('title', '')}")
        if short:
            lines.append(f"      not built: {', '.join(short)}")

    if elsewhere:
        lines.append("  · outside the feature catalogue, not OPS-R54's subject: "
                     + ", ".join(elsewhere))
    if orphans:
        lines.append("")
        lines.append(f"::warning::{len(orphans)} requirement(s) of the features this "
                     "version touches are locked by no manifest in the train, so no "
                     f"release gate will ever ask about them: {', '.join(orphans)}")
    if not stubs:
        lines.append("\nno-stubs: every requirement this version locks is built.")
        return 0, lines
    lines.append(f"\n::error::not releasable — {len(stubs)} requirement(s) this "
                 f"version locks are not built: {', '.join(stubs)}")
    return 1, lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--status", required=True)
    args = ap.parse_args()

    path = manifest_for(args.version)
    if not path.is_file():
        print(f"::error::no manifest at {path}")
        return 2
    goals = tomllib.loads(path.read_text(encoding="utf-8")).get("goals", [])
    if not goals:
        print(f"::error::{path.name} locks no goals")
        return 2

    status = within_cwd(args.status)
    if not status.is_file():
        print(f"::error::no tracker at {status}")
        return 2

    features = catalogue.features()
    if not features:
        print(f"::error::no feature docs under {catalogue.FEATURE_DOCS} — run this "
              "from the specification's root")
        return 2
    if complaint := vocabulary_holds(catalogue.enum("maturity")):
        print(f"::error::{complaint}")
        return 2

    code, lines = verdict(goals, features, done_ids(status), locked_everywhere())
    if lines:
        print(f"no-stubs: {path.name} — the {len(goals)} requirements it locks\n")
        print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
