#!/usr/bin/env python3
"""A feature's maturity is what the trackers and the manifests say — OPS-R73, OPS-R78.

`maturity:` in a feature's frontmatter was written by hand, and nothing compared
it with what was built. Six features said `planned` while the trackers recorded
their requirements done, and the no-stubs gate read them as untouched. So it is
derived here, from every repository's tracker and every version manifest:

  planned   no requirement the feature defines is done
  building  some are done and some are not
  built     every one is done
  shipped   every one is done, and every one is locked by a released version;
            `shipped:` names the latest of those versions

Retired requirements are left out of all four. `withdrawn` is the one maturity a
person sets, because it is a decision rather than a measurement, and it is left
as it is.

`--check` refuses a catalogue that says anything else, naming each feature, what
it says and what the trackers say. `--write` rewrites the frontmatter lines, and
the maturity workflow runs it hourly and opens the pull request that carries it.

Usage:
  maturity.py --spec <spec root> --tracker name=<checkout> [...]
              [--legacy IMPLEMENTATION-STATUS.md] (--check | --write)

Every input has to have been read: a repository some version is satisfied in
with no tracker given, a tracker that is not there or cannot be parsed, and a
Markdown page that records nothing each stop the run rather than lower what the
catalogue says.

Exit 0 = every feature says what the trackers say (or was rewritten to);
1 = some do not, named; 2 = an input was not read, so no derivation is given.
"""

from __future__ import annotations

import argparse
import glob
import pathlib
import re
import sys
from dataclasses import dataclass

import metafm
import status_check
from catalogue import FEATURE_DOCS
from paths import within_cwd
from patterns import REQ_DEF, REQ_RETIRED_ROW, ordered

#: The maturity a person sets, and which nothing here derives or changes.
DECIDED = "withdrawn"
#: The manifest state that puts what a version locks in somebody's hands.
RELEASED = "released"
LINE = re.compile(r"^maturity:[ \t]*\S+[ \t]*$", re.MULTILINE)
SHIPPED_LINE = re.compile(r"^shipped:[ \t]*\S+[ \t]*\n", re.MULTILINE)


@dataclass(frozen=True)
class Feature:
    """One feature: what the catalogue says, and what the trackers make it."""

    id: str
    path: pathlib.Path
    says: str
    derived: str
    done: int
    defined: int
    says_shipped: str | None = None
    shipped_in: str | None = None

    @property
    def moved(self) -> bool:
        return self.says != self.derived or self.says_shipped != self.shipped_in


def released(spec: pathlib.Path) -> dict[str, str]:
    """Every requirement a released version locked, with the latest such version."""
    found: dict[str, str] = {}
    for data in status_check.manifests(spec):
        if data.get("status") != RELEASED:
            continue
        for goal in data.get("goals", []):
            if goal not in found or ordered(data["version"]) > ordered(found[goal]):
                found[goal] = data["version"]
    return found


def derive(requirements: set[str], done: set[str], shipped: set[str] | dict[str, str]) -> str:
    finished = requirements & done
    if not finished:
        return "planned"
    if finished != requirements:
        return "building"
    return "shipped" if requirements <= set(shipped) else "built"


def features(spec: pathlib.Path, done: set[str]) -> list[Feature]:
    """Every catalogued feature a person did not withdraw, with its derived maturity."""
    shipped = released(spec)
    found = []
    for path in sorted(glob.glob(str(spec / FEATURE_DOCS))):
        front = metafm.load(path) or {}
        if not front.get("id") or front.get("maturity") == DECIDED:
            continue
        text = pathlib.Path(path).read_text(encoding="utf-8")
        defined = set(REQ_DEF.findall(text)) - set(REQ_RETIRED_ROW.findall(text))
        derived = derive(defined, done, shipped)
        version = (max((shipped[r] for r in defined), key=ordered) if derived == "shipped"
                   else None)
        found.append(Feature(front["id"], pathlib.Path(path), front.get("maturity", ""),
                             derived, len(defined & done), len(defined),
                             front.get("shipped"), version))
    return found


def done_across(spec: pathlib.Path, trackers: dict[str, pathlib.Path],
                legacy: pathlib.Path | None) -> set[str]:
    """Every requirement some tracker records done, refusing any input that was not read.

    Fails closed in every direction. A derivation from fewer trackers than there are
    reads fewer requirements done, and `--write` would then carry a catalogue that
    says less was built than was, into a pull request that merges itself. So a
    repository some version is satisfied in with no tracker given, a tracker path
    that is not there, a tracker in the old milestone shape with no Markdown page
    beside it, and a Markdown page with no done row in it are each refused rather
    than read as recording nothing.
    """
    missing = [name for name in status_check.searched(spec) if name not in trackers]
    if missing:
        raise status_check.Unreadable(
            f"no tracker given for {', '.join(missing)}: every repository a version is "
            "satisfied in keeps one (OPS-R74), and one that was not read is not one that "
            "records nothing")
    done: set[str] = set()
    for name, path in trackers.items():
        rows = status_check.load(path, name)
        if rows is None and not (path / status_check.FILE).is_file():
            raise status_check.Unreadable(f"{name}: no tracker under {path}")
        if rows is None and legacy is None:
            raise status_check.Unreadable(
                f"{name}: its tracker is in the milestone shape, and no --legacy page was "
                "given to read it through")
        done |= {row.id for row in rows or [] if row.done}
    if legacy is not None:
        import gate

        if not legacy.is_file():
            raise status_check.Unreadable(f"no Markdown tracker at {legacy}")
        page = gate.done_ids(legacy)
        if not page:
            raise status_check.Unreadable(f"{legacy} records nothing done, which is a page "
                                          "that was not read rather than a project with "
                                          "nothing built")
        done |= page
    return done


def rewrite(feature: Feature) -> None:
    """The maturity line, and the `shipped:` line beside it where there is one."""
    text = SHIPPED_LINE.sub("", feature.path.read_text(encoding="utf-8"), count=1)
    line = f"maturity: {feature.derived}"
    if feature.shipped_in:
        line += f"\nshipped: {feature.shipped_in}"
    feature.path.write_text(LINE.sub(line, text, count=1), encoding="utf-8")


def shown(maturity: str, version: str | None) -> str:
    return f"{maturity} {version}" if version else maturity


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec", required=True)
    parser.add_argument("--tracker", action="append", default=[], metavar="name=checkout")
    parser.add_argument("--legacy")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()

    spec = within_cwd(args.spec)
    if not (spec / "70-operations" / "versions").is_dir():
        print(f"::error::no version manifests under {spec}")
        return 2
    try:
        trackers = status_check.pairs(args.tracker, "--tracker")
        done = done_across(spec, trackers, within_cwd(args.legacy) if args.legacy else None)
    except status_check.Unreadable as unread:
        print(f"::error::{unread}")
        return 2
    moved = [f for f in features(spec, done) if f.moved]
    if args.write:
        for feature in moved:
            rewrite(feature)
            print(f"{feature.id}: {shown(feature.says, feature.says_shipped)} → "
                  f"{shown(feature.derived, feature.shipped_in)}")
        return 0
    for f in moved:
        print(f"::error::{f.id} is `{shown(f.says, f.says_shipped)}` in the catalogue, and "
              f"the trackers and manifests make it `{shown(f.derived, f.shipped_in)}`: "
              f"{f.done} of its {f.defined} requirements are done. "
              "`maturity.py --write` rewrites it, and the maturity workflow opens that "
              "pull request hourly (OPS-R78).")
    if moved:
        return 1
    print("maturity: every feature says what the trackers say.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
