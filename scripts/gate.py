#!/usr/bin/env python3
"""Release readiness gate — OPS-R34.

A version is releasable only when every locked goal is satisfied, and a goal is
satisfied only when BOTH hold:

  1. a merged commit in a target repo cites its ID in a `Spec:` trailer, and
  2. the implementation-status tracker marks it done — a row whose **status
     column** bears ✅ and which names the ID, directly or via a range like
     `C1-R1..R12`.

Citation without a tick is work in flight; a tick without a citation is an
unauditable claim. Requiring both is the defence in depth OPS-R34 specifies.

Usage:
  gate.py --manifest <versions/X.toml> \\
          --repo <name>=<path> [--repo <name>=<path> ...] \\
          --status <path to IMPLEMENTATION-STATUS.md>

Exit 0 = every goal satisfied (releasable); 1 = goals unmet (named); 2 = usage.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tomllib

import tracker
from patterns import CITE, LANDED, RANGE
from patterns import SPEC_TRAILER as TRAILER


def within_cwd(raw: str) -> pathlib.Path:
    """Resolve a CLI-supplied path, refusing anything outside the working tree."""
    path = pathlib.Path(raw).resolve()
    if not path.is_relative_to(pathlib.Path.cwd().resolve()):
        print(f"::error::path escapes the working directory: {raw}")
        raise SystemExit(2)
    return path


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
    ap.add_argument("--status", required=True)
    ap.add_argument("--format", choices=("human", "json"), default="human")
    a = ap.parse_args()

    manifest = within_cwd(a.manifest)
    repos = parse_repos(a.repo)
    status = within_cwd(a.status)
    results = evaluate(
        load_goals(manifest),
        cited_ids(repos),
        done_ids(status),
        landed_ids(status, repos),
    )
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
