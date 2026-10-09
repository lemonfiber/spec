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
which a maintainer approves by choice: such a pull request passes once it
carries the `workflows-approved` label, added after its last push.

The approval is read from the forge's own records and never from a commit:
the label is on the pull request now; the newest time it was added is later
than every force push of its branch; and every run of this check, from the
newest one at or before that time onward, was for the head being judged. A
push, a force push or a removal of the label after it voids the approval, and
this fails again until the label is added again. A commit's dates are the
pusher's to write, so none is read.

The change is read against the merge base, so a pull request is judged on what
it changes and not on what `main` has changed since it branched, and it is read
from git's trees at both commits, not from the pull request's file list, which
the forge stops at 3,000 files. Those two directories are what decides which
checks run and from where; everything else a workflow runs out of the tree is
the change under review, run by checks the base branch chose.

Usage:
  pin_only.py --repo <owner/name> --number <pull request> --head <the event's head commit>
              --workflow <the calling workflow's ref, as `github.workflow_ref` gives it>

Exit 0 when the head changes no workflow, moves only spec's pins forward, or
carries the approval; 1 when it changes a workflow otherwise, or the pull
request's head is no longer that commit; 2 when the forge could not be read,
the head is not a commit, or the calling workflow is not named.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
from collections.abc import Callable

import yaml

#: Where what a repository's checks run is written.
GUARDED = (".github/workflows/", ".github/actions/")

#: The repository whose workflows a pin names, and its branch a pin moves along.
SPEC, MAIN = "lemonfiber/spec", "main"

#: A pin of one of spec's workflows, with the version a tag names beside it.
PIN = re.compile(r"(?P<path>lemonfiber/spec/\S+?)@(?P<sha>[0-9a-f]{40})(?P<version>[ \t]*#[ \t]*v\d+(?:\.\d+)*)?")

#: The label a maintainer adds, after the last push, to approve a change to the checks.
APPROVED = "workflows-approved"

#: The most pages of a list read before the list is called too long to judge.
PAGES = 10

#: Items in one page of a list.
PER_PAGE = 100

#: The calling workflow as `github.workflow_ref` names it: the repository, the file, the ref.
WORKFLOW_REF = re.compile(r"\A(?P<repo>[\w.-]+/[\w.-]+)/\.github/workflows/(?P<file>[\w.-]+\.ya?ml)@\S+\Z")

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


Differences = tuple[list[tuple], list[tuple[str, str, str]]]


def children(before: object, after: object) -> list[tuple[object, object, object]] | None:
    """The matching parts of two mappings or two lists, each as (key, before, after),
    or None where the two are not containers of the same shape."""
    if isinstance(before, dict) and isinstance(after, dict) and list(before) == list(after):
        return [(key, before[key], after[key]) for key in before]
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [(index, *pair) for index, pair in enumerate(zip(before, after, strict=True))]
    return None


def differences(before: object, after: object, where: tuple = ()) -> Differences:
    """Where two parsed workflows differ, other than a spec pin at a `uses`, and the pins that moved."""
    parts = children(before, after)
    if parts is not None:
        found: Differences = ([], [])
        for key, old_part, new_part in parts:
            elsewhere, moved = differences(old_part, new_part, (*where, key))
            found[0].extend(elsewhere)
            found[1].extend(moved)
        return found
    if isinstance(before, dict | list):
        # Two containers of another shape, which `children` would have paired.
        return [where], []
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


def listed(path: str, api: Api, key: str | None = None) -> list[dict]:
    """Every item of a list the forge pages, refused where it runs past `PAGES` pages."""
    joined = "&" if "?" in path else "?"
    items: list[dict] = []
    for page in range(1, PAGES + 1):
        answer = api([f"{path}{joined}per_page={PER_PAGE}&page={page}"], False)
        got = answer[key] if key else answer
        items += got
        if len(got) < PER_PAGE:
            return items
    raise Incomplete(f"{path} runs past {PAGES * PER_PAGE} items")


def approval(repo: str, pull: dict, head: str, workflow: str, api: Api) -> str | None:
    """Why the pull request carries no approval for `head`, or None where it does.

    `workflow` is the calling workflow's file. Its runs for the pull request's
    branch are the forge's record of each head the branch had: a push starts
    one, and so does every other event this check is called for.
    """
    if APPROVED not in [label["name"] for label in pull["labels"]]:
        return f"it carries no `{APPROVED}` label"
    number = pull["number"]
    events = listed(f"repos/{repo}/issues/{number}/timeline", api)
    added = [e["created_at"] for e in events if e["event"] == "labeled" and e["label"]["name"] == APPROVED]
    if not added:
        return f"no event on it says when `{APPROVED}` was added"
    at = max(added)
    forced = sorted(e["created_at"] for e in events if e["event"] == "head_ref_force_pushed" and e["created_at"] >= at)
    if forced:
        return f"its branch was force-pushed at {forced[-1]}, after `{APPROVED}` was added at {at}"
    source = pull["head"]["repo"]["full_name"]
    branch = urllib.parse.quote(pull["head"]["ref"], safe="")
    runs = [r for r in listed(f"repos/{repo}/actions/workflows/{workflow}/runs?event=pull_request_target"
                              f"&branch={branch}", api, "workflow_runs")
            if r["head_repository"]["full_name"] == source]
    before = [r["created_at"] for r in runs if r["created_at"] <= at]
    if not before:
        return f"no run of this check shows what its head was when `{APPROVED}` was added at {at}"
    since = sorted((r for r in runs if r["created_at"] >= max(before)), key=lambda r: r["created_at"])
    pushed = [r for r in since if r["head_sha"] != head]
    if pushed:
        return (f"its head was {pushed[-1]['head_sha'][:8]} at {pushed[-1]['created_at']}, so {head[:8]} was "
                f"pushed after `{APPROVED}` was added at {at}")
    return None


def main(argv: list[str] | None = None, api: Api = gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--number", required=True, type=int)
    parser.add_argument("--head", required=True, help="the head commit the event was for")
    parser.add_argument("--workflow", required=True, help="the calling workflow, as `github.workflow_ref` names it")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{40}", args.head):
        print(f"::error::--head {args.head!r} is not a commit, so there is nothing to judge")
        return 2
    calling = WORKFLOW_REF.fullmatch(args.workflow)
    if not calling or calling["repo"] != args.repo:
        print(f"::error::--workflow {args.workflow!r} is not a workflow of {args.repo}, so its runs cannot be read")
        return 2
    try:
        found, moved = problems(args.repo, args.number, args.head, api)
        unapproved = approval(args.repo, current(args.repo, args.number, args.head, api), args.head,
                              calling["file"], api) if found else None
        if found:
            current(args.repo, args.number, args.head, api)
    except Moved as moved_on:
        print(f"::error::{moved_on}.")
        return 1
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, TypeError, Incomplete) as broken:
        detail = getattr(broken, "stderr", "") or broken
        print(f"::error::The pull request could not be read, so nothing says its checks are its base's: {detail}")
        return 2
    if found and unapproved is None:
        for said in found:
            print(f"::notice::{said}, and a maintainer approved it with `{APPROVED}` after its last push (Q-R83).")
        return 0
    for said in found:
        print(f"::error::{said}. A change to what the checks run is merged by a maintainer, not by this check (Q-R83).")
    if found:
        print(f"::error::A maintainer approves it by adding `{APPROVED}` after its last push, and that has not "
              f"happened: {unapproved}.")
        return 1
    if moved:
        print(f"{moved} workflow file(s) change only spec's pins, each moving forward along {SPEC} {MAIN}.")
    else:
        print("No workflow or action changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
