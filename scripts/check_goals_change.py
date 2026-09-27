#!/usr/bin/env python3
"""A staged version's goals change only under review, and the change is told — OPS-R31.

Staging freezes a version's goals: they are the promise a release makes, and
`staging.md` says changing them needs a `goals-change` label and is logged to
the maintainer channel. Nothing held either half. Two pull requests changed
0.17.0's goals after it was staged, and neither carried the label nor told
anybody — the sentence was the only thing standing between a release and a
scope that drifts in silence.

This reads every version manifest a change touches and compares the goals at
the base with the goals at the head. A manifest whose base is past `planned` is
frozen: a released one included, because a release that stops claiming a goal
is a change to what was promised. A frozen manifest whose goals moved refuses
the change unless the label is on it, and names the version and every goal
added and taken out. `--summary` prints the same change as one line per
version, which is what the maintainer channel is sent once it merges.

**No revision it is given reaches git as an argument.** Each is handed to
`git cat-file` on its standard input and resolved to the commit it names, and
only the object names git answers with, held to the shape of one, are passed
on. A value git could read as an option has nowhere to be read as one.

A manifest the base does not have is new, and a new one is `planned` or is
being staged by `stage-version`, which is the lock itself rather than a change
to it. A manifest that cannot be read at either end refuses: a comparison that
did not happen is not one that found nothing.

Run:  python3 scripts/check_goals_change.py --base <sha> --head <sha> --labels a,b
      python3 scripts/check_goals_change.py --base <sha> --head <sha> --summary
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERSIONS = "70-operations/versions"
LABEL = "goals-change"

# What is not a version: the template a new manifest is copied from, and the
# page that explains them.
NOT_A_VERSION = ("TEMPLATE.toml",)


# An object name as git writes one: SHA-1 or SHA-256, in hex.
OBJECT = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")


class Unreadable(Exception):
    """A manifest could not be read at a revision. Never the same as unchanged."""


def _git(*args: str, given: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], input=given, capture_output=True, text=True, check=False
    )


def _named(asked: str) -> str | None:
    """The object `git cat-file --batch-check` resolved one line to, or None where it named none."""
    answered = _git("cat-file", "--batch-check", given=f"{asked}\n")
    found = answered.stdout.split(" ", 1)[0] if answered.returncode == 0 else ""
    return found if OBJECT.fullmatch(found) else None


def commit(revision: str) -> str:
    """The commit a revision names, resolved by git from its standard input."""
    found = _named(f"{revision}^{{commit}}")
    if found is None:
        raise Unreadable(f"{revision!r} names no commit here")
    return found


def touched(base: str, head: str) -> list[str]:
    """The version manifests that differ between two commits git resolved."""
    asked = _git("diff", "--name-only", base, head, "--", VERSIONS)
    if asked.returncode != 0:
        raise Unreadable(f"git could not compare {base} with {head}: {asked.stderr.strip()}")
    return sorted(
        path
        for path in asked.stdout.splitlines()
        if path.endswith(".toml") and pathlib.PurePosixPath(path).name not in NOT_A_VERSION
    )


def manifest(revision: str, path: str) -> dict | None:
    """The manifest at a commit git resolved, or None where that commit does not have it."""
    blob = _named(f"{revision}:{path}")
    if blob is None:
        return None
    shown = _git("cat-file", "blob", blob)
    if shown.returncode != 0:
        raise Unreadable(f"git could not read {path} at {revision}: {shown.stderr.strip()}")
    try:
        return tomllib.loads(shown.stdout)
    except tomllib.TOMLDecodeError as why:
        raise Unreadable(f"{path} at {revision} is not TOML: {why}") from why


def changes(base: str, head: str) -> list[tuple[str, list[str], list[str]]]:
    """Each frozen version whose goals moved: the version, what was added, what was taken out."""
    moved = []
    for path in touched(base, head):
        before = manifest(base, path)
        if before is None or before.get("status", "planned") == "planned":
            continue
        after = manifest(head, path) or {}
        was, now = before.get("goals", []), after.get("goals", [])
        added = [goal for goal in now if goal not in was]
        removed = [goal for goal in was if goal not in now]
        if added or removed:
            moved.append((str(before.get("version", pathlib.PurePosixPath(path).stem)), added, removed))
    return moved


def said(version: str, added: list[str], removed: list[str]) -> str:
    """One version's change, as a line a person reads."""
    parts = [*(f"+{goal}" for goal in added), *(f"-{goal}" for goal in removed)]
    return f"{version}: {', '.join(parts)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--labels", default="", help="the pull request's labels, comma-separated")
    parser.add_argument("--summary", action="store_true", help="print the change and refuse nothing")
    args = parser.parse_args(argv)

    try:
        moved = changes(commit(args.base), commit(args.head))
    except Unreadable as why:
        print(f"::error::{why}")
        return 1

    if args.summary:
        for change in moved:
            print(said(*change))
        return 0

    if not moved:
        print("goals-change: no staged or released version's goals move here.")
        return 0

    labelled = LABEL in {label.strip() for label in args.labels.split(",")}
    for change in moved:
        kind = "notice" if labelled else "error"
        print(f"::{kind}::the locked goals move — {said(*change)}")
    if labelled:
        print(f"goals-change: labelled `{LABEL}`; the maintainer channel is told when this merges (OPS-R31).")
        return 0
    print(
        f"\nA staged or released version's goals are frozen (OPS-R30). Changing them needs "
        f"review: label this pull request `{LABEL}`, and the change is told to the maintainer "
        f"channel when it merges (OPS-R31)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
