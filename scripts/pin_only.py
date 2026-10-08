#!/usr/bin/env python3
"""Refuse a pull request that changes how its checks run, unless it only moves spec's pins — Q-R83.

A repository's checks are its workflows, and the workflows a pull request runs
are the pull request's own: it can rewrite what its checks do, or which it runs,
and still report each one green. So this runs from the base branch, on
`pull_request_target`, reads the pull request through the API as data and
checks nothing out of it. It fails a pull request that changes anything under
`.github/workflows/` or `.github/actions/`, unless the only change in each such
file is a pin of a lemonfiber/spec workflow moving forward along spec's `main`,
with the version written beside it. Anything else is a change to the checks,
which a maintainer merges by choice.

The change is read against the merge base, so a pull request is judged on what
it changes and not on what `main` has changed since it branched, and it is read
from git's trees at both commits, not from the pull request's file list, which
the forge stops at 3,000 files. Those two directories are what decides which
checks run and from where; everything else a workflow runs out of the tree is
the change under review, run by checks the base branch chose.

Usage:
  pin_only.py --repo <owner/name> --number <pull request>

Exit 0 when the pull request changes no workflow, or moves only spec's pins
forward; 1 when it changes a workflow otherwise; 2 when the forge could not be
read.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable

#: Where what a repository's checks run is written.
GUARDED = (".github/workflows/", ".github/actions/")

#: The repository whose workflows a pin names, and its branch a pin moves along.
SPEC, MAIN = "lemonfiber/spec", "main"

#: A pin of one of spec's workflows, with the version a tag names beside it.
PIN = re.compile(r"(?P<path>lemonfiber/spec/\S+?)@(?P<sha>[0-9a-f]{40})(?P<version>[ \t]*#[ \t]*v[0-9]+(?:\.[0-9]+)*)?")

#: One call to the forge's REST API through `gh`: the arguments, and the answer
#: as JSON, or as text where `raw` is asked for.
Api = Callable[[list[str], bool], object]


def gh(args: list[str], raw: bool = False) -> object:
    """One REST call through `gh`."""
    accept = ["-H", "Accept: application/vnd.github.raw"] if raw else []
    done = subprocess.run(["gh", "api", *accept, *args], capture_output=True, text=True, check=True)
    return done.stdout if raw else json.loads(done.stdout)


def guarded(path: str) -> bool:
    """Whether a path is one that decides what the checks run: in either directory, or either itself."""
    return path.startswith(GUARDED) or f"{path}/" in GUARDED


def pins(text: str) -> tuple[str, list[tuple[str, str]]]:
    """A file with each spec pin replaced by its workflow's path alone, and the pins in order."""
    found: list[tuple[str, str]] = []

    def strip(match: re.Match) -> str:
        found.append((match["path"], match["sha"]))
        return f"{match['path']}@"

    return PIN.sub(strip, text), found


def forward(old: str, new: str, api: Api) -> str | None:
    """Why moving a pin from `old` to `new` is not a move forward along spec's main, or None."""
    behind = api([f"repos/{SPEC}/compare/{old}...{new}"], False)
    if behind["status"] != "ahead":
        return f"{new[:8]} is not ahead of {old[:8]} ({behind['status']})"
    landed = api([f"repos/{SPEC}/compare/{new}...{MAIN}"], False)
    if landed["status"] not in ("ahead", "identical"):
        return f"{new[:8]} is not on {SPEC} {MAIN} ({landed['status']})"
    return None


def judged(path: str, before: str, after: str, api: Api) -> list[str]:
    """What, in one changed file, is not a spec pin moving forward."""
    shape_before, pinned_before = pins(before)
    shape_after, pinned_after = pins(after)
    if shape_before != shape_after or [p for p, _ in pinned_before] != [p for p, _ in pinned_after]:
        return [f"{path} changes more than spec's pins"]
    problems = []
    for (workflow, old), (_, new) in zip(pinned_before, pinned_after, strict=True):
        if old != new:
            why = forward(old, new, api)
            if why:
                problems.append(f"{path} moves {workflow}: {why}")
    return problems


class Incomplete(ValueError):
    """An answer the forge gave only in part."""


def guarded_tree(repo: str, commit: str, api: Api) -> dict[str, tuple[str, str]]:
    """Every entry under the guarded directories at a commit: path to (mode, object).

    Read from git's own trees rather than the pull request's file list, which
    the forge stops at 3,000 files: a change listed past that would never be
    looked at. A tree the forge answers only in part is refused, never read as
    whole.
    """
    root = api([f"repos/{repo}/git/trees/{commit}"], False)
    if root.get("truncated"):
        raise Incomplete(f"the tree at {commit[:8]} came back truncated")
    github = next((one for one in root["tree"] if one["path"] == ".github"), None)
    if github is None:
        return {}
    if github["type"] != "tree":
        return {".github": (github["mode"], github["sha"])}
    below = api([f"repos/{repo}/git/trees/{github['sha']}?recursive=1"], False)
    if below.get("truncated"):
        raise Incomplete(f".github at {commit[:8]} came back truncated")
    return {f".github/{one['path']}": (one["mode"], one["sha"]) for one in below["tree"]
            if guarded(f".github/{one['path']}") and one["type"] != "tree"}


#: The modes of a file git checks out as a file, rather than a link or a submodule.
FILE_MODES = ("100644", "100755")


def problems(repo: str, number: int, api: Api) -> tuple[list[str], int]:
    """What the pull request changes that is not a spec pin moving forward, and how many files it moves."""
    pull = api([f"repos/{repo}/pulls/{number}"], False)
    head = pull["head"]["sha"]
    base = api([f"repos/{repo}/compare/{pull['base']['sha']}...{head}"], False)["merge_base_commit"]["sha"]
    before, after = guarded_tree(repo, base, api), guarded_tree(repo, head, api)
    found: list[str] = []
    moved = 0
    for path in sorted(set(before) | set(after)):
        if path not in after:
            found.append(f"{path} is removed")
        elif path not in before:
            found.append(f"{path} is added")
        elif before[path] == after[path]:
            continue
        elif before[path][0] != after[path][0] or after[path][0] not in FILE_MODES:
            found.append(f"{path} changes its mode from {before[path][0]} to {after[path][0]}")
        else:
            old = api([f"repos/{repo}/git/blobs/{before[path][1]}"], True)
            new = api([f"repos/{repo}/git/blobs/{after[path][1]}"], True)
            said = judged(path, str(old), str(new), api)
            found += said
            moved += not said
    return found, moved


def main(argv: list[str] | None = None, api: Api = gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--number", required=True, type=int)
    args = parser.parse_args(argv)
    try:
        found, moved = problems(args.repo, args.number, api)
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, TypeError, Incomplete) as broken:
        detail = getattr(broken, "stderr", "") or broken
        print(f"::error::The pull request could not be read, so nothing says its checks are its base's: {detail}")
        return 2
    for said in found:
        print(f"::error::{said}. A change to what the checks run is merged by a maintainer, not by this check (Q-R83).")
    if found:
        return 1
    if moved:
        print(f"{moved} workflow file(s) change only spec's pins, each moving forward along {SPEC} {MAIN}.")
    else:
        print("No workflow or action changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
