#!/usr/bin/env python3
"""Which repositories a version cuts, and which its goal gate searches — OPS-R58.

Two questions that used to be one list, and were not the same question. `repos`
is what a version *cuts*: execute tags every one of them, so a name in it is a
release. The gate asks something else — where the work satisfying the goals
landed — and read `repos` for want of anywhere better to look.

It costs both ways round. `0.10.0` names only `lemonfiber`, and `ARCH-R55` is
cited only in `lemonfiber-web`: its gate calls that goal unmet for a reason that
has nothing to do with the work. `0.9.0` avoided that by putting `lemonfiber-web`
in `repos` — and so declared a release stream it cuts nothing from. Nobody has
been hurt by that yet only because the last version to go through
`execute-version` was `0.7.0` and everything since was tagged by hand; the first
one that does not will tag `lemonfiber-web`, whose `publish.yml` fires on a
version tag and would publish a build nobody asked for.

So a manifest may say `satisfied_in`, and where it does not, the streams it cuts
are searched: the two coincide for every version so far, and a default that keeps
them coinciding is the one that needs no migration.

Usage:
  manifest_repos.py --version X.Y.Z --for cut|searched
Prints one repository per line. Exit 0 = printed, 1 = no such manifest, 2 = usage.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import tomllib

from patterns import VERSION as VERSION_RE

VERSIONS_DIR = pathlib.Path("70-operations/versions")

#: What a version cuts. Every name here is tagged at execute.
CUT = "repos"
#: Where its goals were satisfied. Naming one here tags nothing.
SEARCHED = "satisfied_in"


def cut(data: dict) -> list[str]:
    """The release streams this version tags."""
    return [str(name) for name in data.get(CUT, [])]


def searched(data: dict) -> list[str]:
    """The repositories the goal gate reads commit messages from.

    Falls back to the streams rather than to nothing: a manifest that says
    nothing is every manifest written before this existed, and searching none of
    them would report every goal unmet — a gate that fails loudly for a reason
    that is not true is no better than one that passes quietly for a reason that
    is not either.
    """
    named = data.get(SEARCHED)
    if not named:
        return cut(data)
    return [str(name) for name in named]


def manifest_for(version: str) -> pathlib.Path:
    """The manifest path for a validated version, built from a constant base."""
    if not VERSION_RE.match(version):
        sys.exit(f"::error::version must be X.Y.Z, got {version!r}")
    path = (VERSIONS_DIR / f"{version}.toml").resolve()
    if not path.is_relative_to(VERSIONS_DIR.resolve()):
        sys.exit(f"::error::path escapes {VERSIONS_DIR}")  # pragma: no cover
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--for", dest="asked", required=True, choices=("cut", "searched"))
    a = ap.parse_args()

    path = manifest_for(a.version)
    if not path.is_file():
        print(f"::error::no manifest at {path}", file=sys.stderr)
        return 1
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    names = cut(data) if a.asked == "cut" else searched(data)
    # A version that cuts nothing is a manifest somebody has not finished. Said
    # here rather than left for whichever `while read` loop iterates over an
    # empty file and reports success for having done nothing.
    if not names:
        print(f"::error::{path.name} names no repositories to {a.asked}", file=sys.stderr)
        return 1
    print("\n".join(names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
