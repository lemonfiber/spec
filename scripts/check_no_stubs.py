#!/usr/bin/env python3
"""No version ships a feature it has not finished — OPS-R54.

`gate.py` asks whether every locked *goal* is satisfied. This asks the larger
question the no-stub rule is about: whether every **feature** those goals reach
into is finished. A feature is more than its requirements taken one at a time, so
a version can satisfy every goal it locked and still be carrying a feature that is
half-built — which is precisely the stub OPS-R54 exists to refuse.

`built` is the state that makes this checkable. `shipped` means out in a released
version, so demanding it *before* a release would be a gate nothing could pass;
`built` means every requirement is met and merged and the version carrying it is
waiting to go out.

Nothing enforced this. `0.14.0` locked E1–E5 and G8 while four of those catalogue
files still said `building`, and the only thing that corrected them was somebody
reading all six by hand on the day.

Two silences are refused rather than tolerated, because both would read as a pass:

  * a catalogue that reads as empty — a wrong working directory, a moved tree —
    would find no unfinished feature and report success about nothing;
  * a `maturity` vocabulary that no longer holds the two names this rule is
    written in, which is how a schema rename turns a gate off without touching it.

Usage:
  check_no_stubs.py --version X.Y.Z

Exit 0 = every feature the version locks is finished; 1 = named features are not;
2 = the question could not be answered.
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib

import catalogue
from manifest_repos import manifest_for
from patterns import REQ_DEF

#: The two maturities OPS-R54 accepts, in the order the rule names them.
FINISHED = ("built", "shipped")


def unfinished(maturity: str | None) -> bool:
    return maturity not in FINISHED


def goal_features(goals: list[str]) -> list[str]:
    """The feature part of each goal, in first-seen order and without repeats."""
    seen: list[str] = []
    for goal in goals:
        feature = goal.partition("-R")[0]
        if feature not in seen:
            seen.append(feature)
    return seen


def requirement_count(path: str) -> int:
    """How many requirements a feature doc defines."""
    with open(path, encoding="utf-8") as doc:
        return len(REQ_DEF.findall(doc.read()))


def vocabulary_holds(known: set[str]) -> str | None:
    """Whether the catalogue still spells the two states this rule is written in."""
    missing = [name for name in FINISHED if name not in known]
    if missing:
        return (
            f"the frontmatter schema's `maturity` no longer offers "
            f"{', '.join(missing)}, so this rule is written in words the "
            "catalogue does not use — OPS-R54 and the schema have to be "
            "reconciled before this can decide anything"
        )
    return None


def verdict(goals: list[str], features: dict[str, dict]) -> tuple[int, list[str]]:
    """The gate's exit code and the lines explaining it.

    Identifiers outside the feature namespaces are reported rather than dropped.
    `0.10.0` locks six `ARCH-R` goals, which name no feature and never could; a
    gate that passes over them in silence is one nobody can tell from a gate that
    looked at them and approved.
    """
    is_feature = re.compile(catalogue.id_pattern()).fullmatch
    lines: list[str] = []
    stubs: list[str] = []
    elsewhere: list[str] = []

    for feature in goal_features(goals):
        if not is_feature(feature):
            elsewhere.append(feature)
            continue
        front = features.get(feature)
        if front is None:
            print(f"::error::goal names {feature}, which the feature catalogue "
                  "does not hold — the manifest and the catalogue disagree")
            return 2, []
        locked = sum(1 for g in goals if g.startswith(f"{feature}-R"))
        defines = requirement_count(front["path"])
        state = front.get("maturity")
        scope = f"{locked} of its {defines} requirements"
        lines.append(f"  {'✗' if unfinished(state) else '✓'} {feature:4} "
                     f"{state!s:9} locks {scope:26} {front.get('title', '')}")
        if unfinished(state):
            stubs.append(f"{feature} ({state})")

    if elsewhere:
        lines.append("  · outside the feature catalogue, not OPS-R54's subject: "
                     + ", ".join(elsewhere))
    if not stubs:
        lines.append("\nno-stubs: every feature this version locks is finished.")
        return 0, lines
    lines.append(f"\n::error::not releasable — {len(stubs)} feature(s) this version "
                 f"locks are not finished: {', '.join(stubs)}")
    return 1, lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    args = ap.parse_args()

    path = manifest_for(args.version)
    if not path.is_file():
        print(f"::error::no manifest at {path}")
        return 2
    goals = tomllib.loads(path.read_text(encoding="utf-8")).get("goals", [])
    if not goals:
        print(f"::error::{path.name} locks no goals")
        return 2

    features = catalogue.features()
    if not features:
        print(f"::error::no feature docs under {catalogue.FEATURE_DOCS} — run this "
              "from the specification's root")
        return 2
    if complaint := vocabulary_holds(catalogue.enum("maturity")):
        print(f"::error::{complaint}")
        return 2

    code, lines = verdict(goals, features)
    if lines:
        print(f"no-stubs: {path.name} — the features its {len(goals)} goals reach\n")
        print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
