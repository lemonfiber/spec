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
  pin_only.py --repo <owner/name> --number <pull request> --head <the event's head commit>

Exit 0 when the head changes no workflow, or moves only spec's pins forward;
1 when it changes a workflow otherwise, or the pull request's head is no longer
that commit; 2 when the forge could not be read or the head is not a commit.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable

import yaml

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


#: A whole `uses:` value naming one of spec's workflows at a commit.
USES = re.compile(r"\Alemonfiber/spec/(?P<path>\S+)@(?P<sha>[0-9a-f]{40})\Z")

#: The files read as YAML, where a pin may move. Any other file under the
#: guarded directories may not change at all.
YAML_FILES = (".yml", ".yaml")


class Unsafe(ValueError):
    """YAML whose meaning two readers could disagree about."""


class Strict(yaml.SafeLoader):
    """A loader that refuses what lets one text mean two things: an anchor, an
    alias, a merge key, a key given twice and an explicit tag."""

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise Unsafe("an alias")
        event = self.peek_event()
        if getattr(event, "anchor", None):
            raise Unsafe(f"the anchor &{event.anchor}")
        if getattr(event, "tag", None) not in (None, "!"):
            raise Unsafe(f"the tag {event.tag}")
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        seen = []
        for key, _ in node.value:
            if key.tag == "tag:yaml.org,2002:merge":
                raise Unsafe("a merge key")
            name = self.construct_object(key, deep=True)
            if name in seen:
                raise Unsafe(f"the key {name!r} twice")
            seen.append(name)
        return super().construct_mapping(node, deep)


def strict(text: str) -> object:
    """One YAML document, read by `Strict`."""
    loader = Strict(text)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def at_uses(where: tuple) -> bool:
    """Whether a place in a workflow is a job's `uses` or a step's."""
    return (len(where) == 3 and where[0] == "jobs" and where[2] == "uses") or (
        len(where) == 5 and where[0] == "jobs" and where[2] == "steps" and isinstance(where[3], int)
        and where[4] == "uses")


def differences(before: object, after: object, where: tuple = ()) -> tuple[list[tuple], list[tuple[str, str, str]]]:
    """Where two parsed workflows differ, other than a spec pin at a `uses`, and the pins that moved."""
    if isinstance(before, dict) and isinstance(after, dict):
        if list(before) != list(after):
            return [where], []
        found: tuple[list[tuple], list[tuple[str, str, str]]] = ([], [])
        for key in before:
            more = differences(before[key], after[key], (*where, key))
            found[0].extend(more[0])
            found[1].extend(more[1])
        return found
    if isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            return [where], []
        found = ([], [])
        for index, pair in enumerate(zip(before, after, strict=True)):
            more = differences(*pair, (*where, index))
            found[0].extend(more[0])
            found[1].extend(more[1])
        return found
    if type(before) is type(after) and before == after:
        return [], []
    old = USES.match(before) if isinstance(before, str) else None
    new = USES.match(after) if isinstance(after, str) else None
    if at_uses(where) and old and new and old["path"] == new["path"]:
        return [], [(f"lemonfiber/spec/{old['path']}", old["sha"], new["sha"])]
    return [where], []


def judged(path: str, before: str, after: str, api: Api) -> list[str]:
    """What, in one changed file, is not a spec pin moving forward.

    Two readings, and both must agree. The text, with each pin's commit and
    version taken out, must be the same, so nothing a reader could parse
    differently has changed. And the two documents, each read by `Strict`, must
    differ only in a spec pin at a job's or a step's `uses`, so no commit that
    moved sits in a script, a string or anywhere else Actions reads as other
    than a workflow to call.
    """
    if not path.endswith(YAML_FILES):
        return [f"{path} changes, and only a workflow's spec pins may"]
    (shape_before, pinned_before), (shape_after, pinned_after) = pins(before), pins(after)
    if shape_before != shape_after or [p for p, _ in pinned_before] != [p for p, _ in pinned_after]:
        return [f"{path} changes more than spec's pins"]
    written = sorted((p, was, now) for (p, was), (_, now) in zip(pinned_before, pinned_after, strict=True)
                     if was != now)
    try:
        old, new = strict(before), strict(after)
    except (Unsafe, yaml.YAMLError) as unsafe:
        return [f"{path} holds YAML two readers could take differently ({unsafe}), so no change to it is judged a pin"]
    elsewhere, moved = differences(old, new)
    if elsewhere:
        places = ", ".join(".".join(str(part) for part in place) or "the document" for place in elsewhere)
        return [f"{path} changes more than spec's pins, at {places}"]
    if sorted(moved) != written:
        # A commit that moved in the text and at no `uses`, in a comment say.
        return [f"{path} moves a spec commit somewhere Actions does not read as a workflow to call"]
    problems = []
    for workflow, was, now in moved:
        why = forward(was, now, api)
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


class Moved(ValueError):
    """The pull request's head is no longer the commit this run was started for."""


def current(repo: str, number: int, head: str, api: Api) -> dict:
    """The pull request, refused where its head has moved past the commit being judged."""
    pull = api([f"repos/{repo}/pulls/{number}"], False)
    if pull["head"]["sha"] != head:
        raise Moved(f"the pull request's head is {pull['head']['sha'][:8]}, not {head[:8]}, the commit this run "
                    "was started for; the run started for its head judges it")
    return pull


def problems(repo: str, number: int, head: str, api: Api) -> tuple[list[str], int]:
    """What the head commit changes that is not a spec pin moving forward, and how many files it moves.

    Every read names `head`, the commit the event this run answers was for, and
    never a branch, so what is judged is that commit whatever is pushed while
    the run reads. The verdict is a check on that commit, and branch protection
    asks for the check on the head it would merge: a push after a pass starts
    a run for the new head, and the old pass is on a commit that is no longer
    the head.
    """
    pull = current(repo, number, head, api)
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
    current(repo, number, head, api)
    return found, moved


def main(argv: list[str] | None = None, api: Api = gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--number", required=True, type=int)
    parser.add_argument("--head", required=True, help="the head commit the event was for")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{40}", args.head):
        print(f"::error::--head {args.head!r} is not a commit, so there is nothing to judge")
        return 2
    try:
        found, moved = problems(args.repo, args.number, args.head, api)
    except Moved as moved_on:
        print(f"::error::{moved_on}.")
        return 1
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
