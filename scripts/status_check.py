#!/usr/bin/env python3
"""A repository's implementation status, one row per requirement — OPS-R74, OPS-R75.

Every repository a version is satisfied in keeps `status.toml` at its root, and
changes it in the pull request that changes what it says. One table per
requirement the repository has worked on:

    [[requirement]]
    id = "F8-R6"
    state = "done"
    evidence = [
      "crates/lemonfiber-plugin/src/refusing/recipes.rs",
      "crates/lemonfiber-plugin/src/refusing/recipes/tests.rs::a_flow_no_pair_declares_is_refused",
    ]
    landed = "64097060028ada772e859b1139db31b9e41cb0da"

`state` is `done`, `partial` or `open`. `evidence` names the code and the test
that hold the requirement, each as one of:

    path              a file or directory in this repository
    path::text        that file, which has to contain `text` (a test's name)
    repo:path         a file in another repository, checked where its checkout
                      is given with `--sibling`

`landed` is the commit that finished the requirement, for the case where no
commit cites it and none can: a merged commit cannot gain a trailer. It has to
be in this repository's history.

The release gate reads these files (`gate.py`), and so does the no-stubs gate.
This checks one of them against the specification and against the repository
it sits in:

  * the file has the shape above, and nothing else;
  * every identifier is a requirement the specification defines, and none
    appears twice; a retired one only where a version locked it before it was
    retired, because what that version shipped is still a fact;
  * a `done` row names evidence, and every path it names exists, and every
    `::text` occurs in its file;
  * a `done` row is locked by some version, because work no version carries is
    work no release can ship;
  * a `landed` commit is in this repository's history.

`catalogue` asks the question the specification's own CI asks of every tracker
at once: whether a feature the catalogue calls finished has every requirement it
defines done in one of them (OPS-R73). `repos` names the repositories whose
trackers that is, read from every version manifest's `satisfied_in`.

Usage:
  status_check.py check --status status.toml --spec <spec root> [--repo-root .]
                        [--sibling name=path ...]
  status_check.py catalogue --spec <spec root> --tracker name=path [...]
                            [--legacy IMPLEMENTATION-STATUS.md]
  status_check.py repos --spec <spec root>

Exit 0 = every claim is backed; 1 = claims that are not, named; 2 = the question
could not be asked.
"""

from __future__ import annotations

import argparse
import glob
import pathlib
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass

import metafm
from catalogue import FEATURE_DOCS
from integrity import elsewhere
from patterns import REQ_DEF, REQ_RETIRED_ROW

#: Where a repository keeps its tracker.
FILE = "status.toml"

#: The states a row may be in. Only the first counts towards a release.
STATES = ("done", "partial", "open")
DONE = STATES[0]

#: The keys a row may carry.
REQUIRED = ("id", "state")
OPTIONAL = ("evidence", "landed")

#: The maturities that say every requirement of a feature is met.
FINISHED = ("built", "shipped")

IDENTIFIER = re.compile(r"^[A-Z]+\d*-R\d+$")
SHA = re.compile(r"^[0-9a-f]{7,40}$")
# `repo:path`, and never `path::text`: one colon after a repository's name.
ELSEWHERE = re.compile(r"^([a-z0-9][a-z0-9.-]*):(?!:)(.+)$")


class Unreadable(Exception):
    """The tracker could not be read as one, so nothing in it can be judged."""


@dataclass(frozen=True)
class Row:
    """One requirement as one repository records it."""

    id: str
    state: str
    evidence: tuple[str, ...]
    landed: str | None
    repo: str

    @property
    def done(self) -> bool:
        return self.state == DONE


def shape(data: dict, where: str) -> list[str]:
    """What is wrong with the file's shape, before anything it says is read."""
    faults = [f"{where}: `{key}` is not something a tracker holds; only "
              "`[[requirement]]` tables are" for key in data if key != "requirement"]
    tables = data.get("requirement", [])
    if not isinstance(tables, list):
        return [*faults, f"{where}: `requirement` has to be an array of tables"]
    seen: set[str] = set()
    for number, table in enumerate(tables, start=1):
        here = f"{where}, requirement {number}"
        if not isinstance(table, dict):
            faults.append(f"{here}: is not a table")
            continue
        faults += [f"{here}: carries `{key}`, which is not one of "
                   f"{', '.join(REQUIRED + OPTIONAL)}"
                   for key in table if key not in REQUIRED + OPTIONAL]
        faults += [f"{here}: has no `{key}`" for key in REQUIRED if key not in table]
        ident, state = table.get("id"), table.get("state")
        if ident is not None:
            if not isinstance(ident, str) or not IDENTIFIER.match(ident):
                faults.append(f"{here}: `{ident}` is not a requirement identifier")
            elif ident in seen:
                faults.append(f"{here}: {ident} is recorded twice; one row says "
                              "where a requirement stands")
            else:
                seen.add(ident)
        if state is not None and state not in STATES:
            faults.append(f"{here}: `{state}` is not one of {', '.join(STATES)}")
        evidence = table.get("evidence", [])
        if not isinstance(evidence, list) or not all(isinstance(e, str) and e
                                                     for e in evidence):
            faults.append(f"{here}: `evidence` has to be a list of paths")
        elif state == DONE and not evidence:
            faults.append(f"{here}: {ident} is done and names no evidence; name "
                          "the code and the test that hold it")
        landed = table.get("landed")
        if landed is not None and (not isinstance(landed, str) or not SHA.match(landed)):
            faults.append(f"{here}: `landed` has to be a commit's hexadecimal name")
    return faults


def read(path: pathlib.Path, repo: str) -> list[Row] | None:
    """The rows of a repository's tracker, or None where it keeps none.

    A tracker in the milestone shape the binary kept before this one is read as
    none: `gate.py` reads that one through its Markdown rendering. Anything else
    that does not parse is refused rather than read as empty, because a tracker
    nobody could read reports success about nothing.
    """
    if not path.is_file():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as broken:
        raise Unreadable(f"{path}: {broken}") from broken
    if "milestone" in data:
        return None
    faults = shape(data, str(path))
    if faults:
        raise Unreadable("\n".join(faults))
    return [
        Row(t["id"], t["state"], tuple(t.get("evidence", [])), t.get("landed"), repo)
        for t in data.get("requirement", [])
    ]


def requirements(spec: pathlib.Path) -> tuple[set[str], set[str]]:
    """Every requirement the specification defines, and those it has retired."""
    defined: set[str] = set()
    retired: set[str] = set()
    for doc in spec.rglob("*.md"):
        if elsewhere(doc, spec):
            continue
        text = doc.read_text(encoding="utf-8")
        defined.update(REQ_DEF.findall(text))
        retired.update(REQ_RETIRED_ROW.findall(text))
    return defined, retired


def locked(spec: pathlib.Path) -> set[str]:
    """Every requirement some version manifest locks."""
    found: set[str] = set()
    for path in (spec / "70-operations" / "versions").glob("*.toml"):
        if path.stem != "TEMPLATE":
            found.update(tomllib.loads(path.read_text(encoding="utf-8")).get("goals", []))
    return found


def searched(spec: pathlib.Path) -> list[str]:
    """Every repository some version is satisfied in, which is every tracker."""
    found: set[str] = set()
    for path in (spec / "70-operations" / "versions").glob("*.toml"):
        if path.stem == "TEMPLATE":
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        found.update(data.get("satisfied_in", data.get("repos", [])))
    return sorted(found)


def reachable(root: pathlib.Path, sha: str) -> bool:
    """Whether the repository at `root` holds that commit in its history."""
    done = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", sha, "HEAD"],
                          capture_output=True, check=False)
    return done.returncode == 0


def located(entry: str, root: pathlib.Path,
            siblings: dict[str, pathlib.Path]) -> tuple[pathlib.Path | None, str | None]:
    """The file an evidence entry names and the text it promises, or no file
    where it names another repository whose checkout was not given."""
    if match := ELSEWHERE.match(entry):
        name, entry = match.groups()
        if name not in siblings:
            return None, None
        root = siblings[name]
    path, _, text = entry.partition("::")
    return root / path, text or None


def evidence_faults(row: Row, where: str, root: pathlib.Path,
                    siblings: dict[str, pathlib.Path]) -> list[str]:
    """Each evidence entry that names something that is not there."""
    faults = []
    for entry in row.evidence:
        path, text = located(entry, root, siblings)
        if path is None:
            continue
        if not path.exists():
            faults.append(f"{where}: {row.id} names `{entry}` as evidence and there "
                          "is no such path")
        elif text is not None and (path.is_dir()
                                   or text not in path.read_text(encoding="utf-8",
                                                                 errors="ignore")):
            faults.append(f"{where}: {row.id} names `{entry}` as evidence and the "
                          f"file does not contain `{text}`")
    return faults


def check(rows: list[Row], where: str, spec: pathlib.Path, root: pathlib.Path,
          siblings: dict[str, pathlib.Path]) -> list[str]:
    """Every claim in one tracker that the specification or the tree does not back."""
    defined, retired = requirements(spec)
    carried = locked(spec)
    faults = []
    for row in rows:
        if row.id not in defined:
            faults.append(f"{where}: {row.id} is defined nowhere in the specification")
            continue
        if row.id in retired and row.id not in carried:
            faults.append(f"{where}: {row.id} is withdrawn or superseded and no version "
                          "locked it, so nothing was built against it")
        if row.done and row.id not in carried:
            faults.append(f"{where}: {row.id} is done and no version locks it, so no "
                          "release would carry it; a version has to lock it first")
        faults += evidence_faults(row, where, root, siblings)
        if row.landed and not reachable(root, row.landed):
            faults.append(f"{where}: {row.id} names `{row.landed}` as where it landed, "
                          "and this repository's history has no such commit")
    return faults


def done_in(trackers: list[list[Row]]) -> set[str]:
    """Every requirement done in at least one tracker."""
    return {row.id for rows in trackers for row in rows if row.done}


def legacy_done(path: pathlib.Path) -> set[str]:
    """What a tracker still kept as Markdown tables marks done, read as the gate reads it."""
    import gate

    return gate.done_ids(path)


def reopened(spec: pathlib.Path, done: set[str]) -> list[str]:
    """Finished features holding a requirement no tracker records as done.

    Asked of every requirement the feature defines, headstones left out, rather
    than of the ones a version locks: the claim `built` makes is about all of
    them (OPS-R73).
    """
    faults = []
    for path in sorted(glob.glob(str(spec / FEATURE_DOCS))):
        front = metafm.load(path) or {}
        if front.get("maturity") not in FINISHED:
            continue
        text = pathlib.Path(path).read_text(encoding="utf-8")
        missing = sorted(
            set(REQ_DEF.findall(text)) - set(REQ_RETIRED_ROW.findall(text)) - done,
            key=lambda one: int(one.partition("-R")[2]),
        )
        if missing:
            faults.append(
                f"{front.get('id')} is `{front['maturity']}` in the catalogue, and no "
                f"repository's tracker records {', '.join(missing)} as done. A "
                "requirement added to a finished feature reopens it: set it "
                "`building` until each is done (OPS-R73)."
            )
    return faults


def pairs(specs: list[str], flag: str) -> dict[str, pathlib.Path]:
    """`name=path` arguments as a mapping, refusing one that is not."""
    found = {}
    for spec in specs:
        name, sep, raw = spec.partition("=")
        if not sep or not name or not raw:
            raise Unreadable(f"{flag} wants name=path, got {spec!r}")
        found[name] = pathlib.Path(raw)
    return found


def report(faults: list[str], ok: str) -> int:
    for fault in faults:
        print(f"::error::{fault}")
    if faults:
        print(f"\nstatus-check: {len(faults)} claim(s) nothing backs.")
        return 1
    print(f"status-check: {ok}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("check")
    one.add_argument("--status", default=FILE)
    one.add_argument("--spec", required=True)
    one.add_argument("--repo-root", default=".")
    one.add_argument("--sibling", action="append", default=[], metavar="name=path")
    every = commands.add_parser("catalogue")
    every.add_argument("--spec", required=True)
    every.add_argument("--tracker", action="append", default=[], metavar="name=path")
    every.add_argument("--legacy", help="a tracker still kept as Markdown tables")
    names = commands.add_parser("repos")
    names.add_argument("--spec", required=True)
    args = parser.parse_args()

    spec = pathlib.Path(args.spec)
    if not (spec / "70-operations" / "versions").is_dir():
        print(f"::error::no version manifests under {spec}")
        return 2
    try:
        if args.command == "repos":
            print("\n".join(searched(spec)))
            return 0
        if args.command == "catalogue":
            trackers = [read(path, name) or []
                        for name, path in pairs(args.tracker, "--tracker").items()]
            done = done_in(trackers)
            if args.legacy:
                done |= legacy_done(pathlib.Path(args.legacy))
            return report(reopened(spec, done),
                          "every finished feature is done whole across the trackers.")
        status = pathlib.Path(args.status)
        rows = read(status, pathlib.Path(args.repo_root).resolve().name)
        if rows is None:
            print(f"status-check: no tracker in this shape at {status} — nothing to check")
            return 0
        siblings = pairs(args.sibling, "--sibling")
        return report(check(rows, str(status), spec, pathlib.Path(args.repo_root), siblings),
                      f"every row of {status} is backed.")
    except Unreadable as refused:
        for line in str(refused).splitlines():
            print(f"::error::{line}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
