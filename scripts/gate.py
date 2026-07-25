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
import argparse, re, subprocess, sys, tomllib, pathlib

# Same citation grammar the spec's own checks use (spec_check.py).
CITE = re.compile(r"\b([A-Z]+[0-9]*-R[0-9]+)\b")
TRAILER = re.compile(r"^\s*Spec:\s*(.+)$", re.M | re.I)
# A done-marking status row, with an explicit ID range: C1-R1..R12 or C1-R1..C1-R12.
RANGE = re.compile(r"\b([A-Z]+[0-9]*)-R([0-9]+)\.\.(?:[A-Z]+[0-9]*-)?R?([0-9]+)\b")


def cited_ids(repo_paths: dict[str, pathlib.Path]) -> set[str]:
    """Every requirement ID cited in a `Spec:` trailer on any target repo's main."""
    found: set[str] = set()
    for name, path in repo_paths.items():
        try:
            log = subprocess.run(
                ["git", "-C", str(path), "log", "--format=%B"],
                capture_output=True, text=True, check=True,
            ).stdout
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"::error::cannot read git log for {name} at {path}: {exc}")
            raise
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
        # A range also matches CITE for its first ID; the explicit adds do no harm.
        done.update(CITE.findall(line))
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--repo", action="append", default=[], metavar="name=path")
    ap.add_argument("--status", required=True)
    a = ap.parse_args()

    manifest = pathlib.Path(a.manifest)
    if not manifest.is_file():
        print(f"::error::manifest not found: {manifest}")
        return 2
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    goals: list[str] = data.get("goals", [])
    if not goals:
        print(f"::error::{manifest} locks no goals")
        return 2

    repo_paths: dict[str, pathlib.Path] = {}
    for spec in a.repo:
        if "=" not in spec:
            print(f"::error::--repo wants name=path, got {spec!r}")
            return 2
        name, _, path = spec.partition("=")
        repo_paths[name] = pathlib.Path(path)

    status = pathlib.Path(a.status)
    if not status.is_file():
        print(f"::error::status file not found: {status}")
        return 2

    cited = cited_ids(repo_paths)
    done = done_ids(status)

    unmet: list[str] = []
    print(f"gate: {manifest.name} — {len(goals)} goals across {', '.join(repo_paths) or 'no repos'}\n")
    for goal in goals:
        c, d = goal in cited, goal in done
        mark = "✓" if (c and d) else "✗"
        print(f"  {mark} {goal:12}  cited={'yes' if c else 'NO '}  tracked-done={'yes' if d else 'NO '}")
        if not (c and d):
            unmet.append(goal)

    if unmet:
        print(f"\n::error::not releasable — {len(unmet)} goal(s) unmet: {', '.join(unmet)}")
        return 1
    print(f"\ngate: releasable — every goal satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
