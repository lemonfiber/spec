#!/usr/bin/env python3
"""Release readiness gate — OPS-R34, OPS-R74.

A version is releasable only when every locked goal is satisfied, and a goal is
satisfied only when BOTH hold:

  1. a merged commit in a searched repository cites its ID in a `Spec:` trailer,
     or the row recording it names the commit it landed in, and
  2. a searched repository's tracker records it done: a `[[requirement]]` row in
     the `status.toml` at that repository's root whose state is `done`
     (`status_check.py` has the format).

Citation without a tick is work in flight; a tick without a citation is an
unauditable claim. Requiring both is the defence in depth OPS-R34 specifies.

Each searched repository's tracker is read from its checkout, so naming the
repositories is naming the trackers. `--status` reads a tracker still kept as
Markdown tables, which the binary's was until it moved to one row per
requirement; a done row there names its requirements in a column or a range like
`C1-R1..R12`, and may name its commit as ``landed in `<sha>` ``.

Usage:
  gate.py --manifest <versions/X.toml> \\
          --repo <name>=<path> [--repo <name>=<path> ...] \\
          [--status <path to IMPLEMENTATION-STATUS.md>]

Exit 0 = every goal satisfied (releasable); 1 = goals unmet (named); 2 = usage,
or a tracker that cannot be read.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tomllib

import status_check
import tracker
from paths import within_cwd
from patterns import CITE, LANDED, RANGE
from patterns import SPEC_TRAILER as TRAILER


def git(path: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True, text=True, check=True,
    ).stdout


def cited_ids(repo_paths: dict[str, pathlib.Path]) -> set[str]:
    """Every requirement ID cited in a `Spec:` trailer on any target repo."""
    found: set[str] = set()
    for name, path in repo_paths.items():
        # A truncated history can only lose citations, and it loses the oldest
        # first — so the verdict would drift as commits land, and a goal proven
        # once would come undone by unrelated work.
        if git(path, "rev-parse", "--is-shallow-repository").strip() != "false":
            print(f"::error::{name} is a shallow clone — its oldest citations are missing")
            raise SystemExit(2)
        for trailer in TRAILER.findall(git(path, "log", "--format=%B")):
            found.update(CITE.findall(trailer))
    return found


def done_rows(status: pathlib.Path) -> list[tracker.Row]:
    """Every tracker row whose status column says finished.

    By column, because by line is a search of the text rather than a reading of
    the row: a `◐` row explaining that something is not done yet holds the tick
    character, and read that way it marks that something done. `tracker.py` has
    the four times this went wrong.

    A table with no status column is refused rather than skipped. Nothing in it
    can be told done from not-done, and a gate that stops looking reports
    success about the part it could read.
    """
    lines = status.read_text(encoding="utf-8").splitlines()

    for number in tracker.statusless(lines):
        print(f"::error::{status}:{number}: this table names no "
              f"{' or '.join(tracker.STATUS_COLUMNS)} column, so no row in it can be "
              "read as done or not done")
        raise SystemExit(2)

    return [row for row in tracker.rows(lines) if row is not None and row.done]


def claimed(row: tracker.Row) -> set[str]:
    """Every ID a done row names, ranges expanded.

    The whole row, prose included, which is deliberate: a deliverable naming
    what it rests on is ordinary. `status_lint.unclaimed` is what refuses an ID
    on a ticked row that no ticked row claims in a column of its own.
    """
    found: set[str] = set(CITE.findall(row.line))
    for prefix, lo, hi in RANGE.findall(row.line):
        found.update(f"{prefix}-R{n}" for n in range(int(lo), int(hi) + 1))
    return found


def done_ids(status: pathlib.Path) -> set[str]:
    """IDs the tracker marks done — named directly or spanned by a range."""
    done: set[str] = set()
    for row in done_rows(status):
        done.update(claimed(row))
    return done


def trackers(repo_paths: dict[str, pathlib.Path]) -> list[status_check.Row]:
    """Every row of every searched repository's tracker.

    A repository keeping none contributes nothing and is named, so a run that
    found no tracker where one was expected says so. One that cannot be read
    stops the gate rather than being read as empty: a tracker nobody could read
    reports success about nothing.
    """
    rows: list[status_check.Row] = []
    for name, path in repo_paths.items():
        try:
            found = status_check.load(path, name)
        except status_check.Unreadable as broken:
            for line in str(broken).splitlines():
                print(f"::error::{line}")
            raise SystemExit(2) from broken
        if found is None:
            print(f"{name}: no tracker in the per-requirement shape")
            continue
        rows += found
    return rows


def tracked_done(rows: list[status_check.Row]) -> set[str]:
    """Requirements a per-requirement tracker records done."""
    return {row.id for row in rows if row.done}


def tracked_landed(rows: list[status_check.Row], repo_paths: dict[str, pathlib.Path]) -> set[str]:
    """Done requirements whose row names a commit in its own repository's history.

    Checked against the repository the row sits in, which is the only one a
    commit it names can be in: the same rule `landed_ids` applies to a Markdown
    row, scoped to where the row was written.
    """
    landed: set[str] = set()
    for row in rows:
        if not (row.done and row.landed):
            continue
        if reachable(repo_paths[row.repo], row.landed):
            landed.add(row.id)
        else:
            print(f"::warning::{row.repo} records {row.id} as landed in {row.landed} "
                  "and its history has no such commit, so it counts for nothing")
    return landed


def landed_ids(status: pathlib.Path, repo_paths: dict[str, pathlib.Path]) -> set[str]:
    """IDs on a done row that names the merged commit which finished them.

    The narrow way out of a real dead end. A merged commit cannot gain a `Spec:`
    trailer, so a change that closed several requirements under one trailer leaves
    the rest uncitable for ever — and a later commit citing them without advancing
    them is precisely the unauditable claim the two arms exist to refuse.

    So a row may name the commit instead, and the naming is **checked**: the sha has
    to resolve to a commit that is an ancestor of a searched repository's head. A row
    naming something that is not in the history counts for nothing, which is what
    keeps this from becoming a way to tick anything by writing eight characters.

    `git show <sha>` is the audit. That is the whole of why it is a commit rather
    than a pull request number: one can be checked here, offline, against the
    artefact itself; the other is a question for the forge.
    """
    landed: set[str] = set()
    for row in done_rows(status):
        shas = LANDED.findall(row.line)
        if not shas:
            continue
        if not any(reachable(path, sha) for sha in shas for path in repo_paths.values()):
            print(f"::warning::a row names {shas} as where its goals landed and no "
                  "searched repository has that commit, so it counts for nothing")
            continue
        landed.update(claimed(row))
    return landed


def reachable(path: pathlib.Path, sha: str) -> bool:
    """Whether this repository holds that commit, in the history it has now."""
    try:
        git(path, "merge-base", "--is-ancestor", sha, "HEAD")
    except subprocess.CalledProcessError:
        return False
    return True


def load_goals(manifest: pathlib.Path) -> list[str]:
    goals = tomllib.loads(manifest.read_text(encoding="utf-8")).get("goals", [])
    if not goals:
        print(f"::error::{manifest} locks no goals")
        raise SystemExit(2)
    return goals


def parse_repos(specs: list[str]) -> dict[str, pathlib.Path]:
    """Where citations are read from, refusing a run that names nowhere.

    A gate handed no repository finds no trailer anywhere and calls every goal
    uncited — a full sheet of refusals that reads as work nobody has done, from a
    run that never looked. `load_goals` refuses an empty goal set for the same
    reason, and the asymmetry was the hole: a manifest locking nothing could not
    be answered, and a search of nothing could.
    """
    if not specs:
        print("::error::no --repo given, so there is nowhere to read citations from "
              "and every goal would be called unmet for want of looking")
        raise SystemExit(2)
    repos: dict[str, pathlib.Path] = {}
    for spec in specs:
        if "=" not in spec:
            print(f"::error::--repo wants name=path, got {spec!r}")
            raise SystemExit(2)
        name, _, raw = spec.partition("=")
        repos[name] = within_cwd(raw)
    return repos


def evaluate(
    goals: list[str], cited: set[str], done: set[str], landed: set[str] | None = None
) -> list[dict]:
    """Each goal's two arms, and which way the first of them was satisfied.

    `landed` is kept apart from `cited` in the result rather than folded into it, so
    a reader can see which goals rest on the exception. An exception nobody can count
    is one that spreads.
    """
    landed = landed or set()
    return [
        {
            "id": g,
            "cited": g in cited or g in landed,
            "by": "trailer" if g in cited else ("landed" if g in landed else None),
            "done": g in done,
        }
        for g in goals
    ]


def render_human(name: str, repos: list[str], results: list[dict]) -> None:
    print(f"gate: {name} — {len(results)} goals across {', '.join(repos)}\n")
    for r in results:
        ok = r["cited"] and r["done"]
        how = {"trailer": "yes    ", "landed": "landed ", None: "NO     "}[r.get("by")]
        print(f"  {'✓' if ok else '✗'} {r['id']:12}  cited={how} tracked-done={'yes' if r['done'] else 'NO '}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--repo", action="append", default=[], metavar="name=path")
    ap.add_argument("--status")
    ap.add_argument("--format", choices=("human", "json"), default="human")
    a = ap.parse_args()

    manifest = within_cwd(a.manifest)
    repos = parse_repos(a.repo)
    rows = trackers(repos)
    done, landed = tracked_done(rows), tracked_landed(rows, repos)
    if a.status:
        status = within_cwd(a.status)
        done |= done_ids(status)
        landed |= landed_ids(status, repos)
    results = evaluate(load_goals(manifest), cited_ids(repos), done, landed)
    unmet = [r["id"] for r in results if not (r["cited"] and r["done"])]

    if a.format == "json":
        print(json.dumps({"version": manifest.stem, "releasable": not unmet, "goals": results}))
        return 1 if unmet else 0

    render_human(manifest.name, list(repos), results)
    if unmet:
        print(f"\n::error::not releasable — {len(unmet)} goal(s) unmet: {', '.join(unmet)}")
        return 1
    print("\ngate: releasable — every goal satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
