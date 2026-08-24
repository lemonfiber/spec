#!/usr/bin/env python3
"""Classify a PR against the staged version's goals — OPS-R39, OPS-R40, OPS-R42.

Reads the PR text (body plus commit messages) and, against whichever version is
in flight, reports which cited requirement IDs are locked goals of that version
(in scope) and which are not. The workflow turns that into a version label, a
goal-advance comment, or an out-of-scope advisory.

Usage:  pr_goals.py --pr-text <file>
Prints a JSON object; exit 0 always (classification, not a gate).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tomllib

from patterns import CITE
from patterns import SPEC_TRAILER as TRAILER

VERSIONS = pathlib.Path("70-operations/versions")
def within_cwd(raw: str) -> pathlib.Path:
    path = pathlib.Path(raw).resolve()
    if not path.is_relative_to(pathlib.Path.cwd().resolve()):
        sys.exit(f"::error::path escapes the working directory: {raw}")
    return path


def staged_manifest() -> dict | None:
    for manifest in sorted(VERSIONS.glob("*.toml")):
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
        if data.get("status") in ("staged", "in_progress", "releasable"):
            return data
    return None


def cited_ids(text: str) -> set[str]:
    ids: set[str] = set()
    for trailer in TRAILER.findall(text):
        ids.update(CITE.findall(trailer))
    return ids


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pr-text", required=True)
    a = ap.parse_args()

    ids = cited_ids(within_cwd(a.pr_text).read_text(encoding="utf-8"))
    version = staged_manifest()
    if version is None:
        print(json.dumps({"staged": None, "cited": sorted(ids)}))
        return

    goals = set(version["goals"])
    in_scope = sorted(ids & goals)
    print(json.dumps({
        "staged": version["version"],
        "cited": sorted(ids),
        "in_scope": in_scope,
        "out_of_scope": sorted(ids - goals),
        "advisory": bool(ids) and not in_scope,  # cites requirements, none in scope
    }))


if __name__ == "__main__":
    main()
