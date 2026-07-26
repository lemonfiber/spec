#!/usr/bin/env python3
"""Release readiness gate — OPS-R34.

A version is releasable only when every locked goal is satisfied, and a goal is
satisfied only when BOTH hold:

  1. a merged commit in a target repo cites its ID in a `Spec:` trailer, and
  2. the implementation-status tracker marks it done — a row bearing ✅ that
     names the ID, directly or via a range like `C1-R1..R12`.

Citation without a tick is work in flight; a tick without a citation is an
unauditable claim. Requiring both is the defence in depth OPS-R34 specifies.

Usage:
  gate.py --manifest <versions/X.toml> \\
          --repo <name>=<path> [--repo <name>=<path> ...] \\
          --status <path to IMPLEMENTATION-STATUS.md>

Exit 0 = every goal satisfied (releasable); 1 = goals unmet (named); 2 = usage.
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys, tomllib, pathlib

# Same citation grammar the spec's own checks use (spec_check.py).
CITE = re.compile(r"\b([A-Z]+\d*-R\d+)\b")
TRAILER = re.compile(r"(?im)^[ \t]*Spec:[ \t]*(\S.*)$")
# A done-marking status row, with an explicit ID range: C1-R1..R12 or C1-R1..C1-R12.
RANGE = re.compile(r"\b([A-Z]+\d*)-R(\d+)\.\.(?:[A-Z]+\d*-)?R?(\d+)\b")


def within_cwd(raw: str) -> pathlib.Path:
    """Resolve a CLI-supplied path, refusing anything outside the working tree."""
    path = pathlib.Path(raw).resolve()
    if not path.is_relative_to(pathlib.Path.cwd().resolve()):
        print(f"::error::path escapes the working directory: {raw}")
        raise SystemExit(2)
    return path


def cited_ids(repo_paths: dict[str, pathlib.Path]) -> set[str]:
    """Every requirement ID cited in a `Spec:` trailer on any target repo."""
    found: set[str] = set()
    for path in repo_paths.values():
        log = subprocess.run(
            ["git", "-C", str(path), "log", "--format=%B"],
            capture_output=True, text=True, check=True,
        ).stdout
        for trailer in TRAILER.findall(log):
            found.update(CITE.findall(trailer))
    return found


def done_ids(status: pathlib.Path) -> set[str]:
    """IDs the tracker marks ✅ — named directly or spanned by a range."""
    done: set[str] = set()
    for line in status.read_text(encoding="utf-8").splitlines():
        if "✅" not in line:
            continue
        for prefix, lo, hi in RANGE.findall(line):
            done.update(f"{prefix}-R{n}" for n in range(int(lo), int(hi) + 1))
        done.update(CITE.findall(line))
    return done


def load_goals(manifest: pathlib.Path) -> list[str]:
    goals = tomllib.loads(manifest.read_text(encoding="utf-8")).get("goals", [])
    if not goals:
        print(f"::error::{manifest} locks no goals")
        raise SystemExit(2)
    return goals


def parse_repos(specs: list[str]) -> dict[str, pathlib.Path]:
    repos: dict[str, pathlib.Path] = {}
    for spec in specs:
        if "=" not in spec:
            print(f"::error::--repo wants name=path, got {spec!r}")
            raise SystemExit(2)
        name, _, raw = spec.partition("=")
        repos[name] = within_cwd(raw)
    return repos


def evaluate(goals: list[str], cited: set[str], done: set[str]) -> list[dict]:
    return [{"id": g, "cited": g in cited, "done": g in done} for g in goals]


def render_human(name: str, repos: list[str], results: list[dict]) -> None:
    print(f"gate: {name} — {len(results)} goals across {', '.join(repos) or 'no repos'}\n")
    for r in results:
        ok = r["cited"] and r["done"]
        print(f"  {'✓' if ok else '✗'} {r['id']:12}  cited={'yes' if r['cited'] else 'NO '}  tracked-done={'yes' if r['done'] else 'NO '}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--repo", action="append", default=[], metavar="name=path")
    ap.add_argument("--status", required=True)
    ap.add_argument("--format", choices=("human", "json"), default="human")
    a = ap.parse_args()

    manifest = within_cwd(a.manifest)
    repos = parse_repos(a.repo)
    results = evaluate(load_goals(manifest), cited_ids(repos), done_ids(within_cwd(a.status)))
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
