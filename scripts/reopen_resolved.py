#!/usr/bin/env python3
"""Reopen a pull request `spec-check` closed once what it cited resolves —
GOV-R56.

`spec-check` closes a pull request that cites an identifier spec does not yet
define: the work is sequenced, not refused, and waits on that definition. When
a push to spec's main defines identifiers, this finds each closed, unmerged pull
request in the organisation whose closing comment names one of them, and
reopens it with a comment saying the citation now resolves. `spec-check` runs
again on the reopen.

A pull request is reopened only where every identifier its closing comment
named now resolves the way `spec-check` resolves one: defined, neither retired
nor Draft. One closed since by somebody else, or merged, is left alone.

Usage:
  reopen_resolved.py --spec-dir . --diff-file push.diff --sha <commit> [--owner lemonfiber] [--dry-run]

`--diff-file` is the push's diff of the specification's Markdown. Exit 0 having
reopened whatever was owed, a pull request that could not be reopened included,
each named; 2 where the spec, the diff or the forge could not be read.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from collections.abc import Callable

from paths import within_cwd
from patterns import REQ_DEF
from spec_check import defined_ids, draft_ids, retired_ids

#: How `spec-check` begins the comment it closes a pull request with.
CLOSED_BY = "**`spec-check` closed this.**"
#: The identifiers that comment names as not yet defined.
UNKNOWN = re.compile(r"cited identifiers do not exist on spec@main: ([A-Z0-9, -]+)")
#: The account a workflow's own token acts as, which is who `spec-check` closes as.
CLOSER = "github-actions[bot]"

#: One call to the forge's REST API through `gh`: its arguments, then the JSON.
Api = Callable[[list[str]], object]


def newly_defined(diff: str) -> set[str]:
    """The identifiers a diff's added definition rows define and its removed
    rows did not: a row moved or reworded defines nothing new."""
    added = {m for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
             for m in REQ_DEF.findall(line[1:])}
    removed = {m for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")
               for m in REQ_DEF.findall(line[1:])}
    return added - removed


def unknown_in(comment: str) -> list[str]:
    """The identifiers a `spec-check` closing comment names as undefined."""
    if not comment.startswith(CLOSED_BY):
        return []
    found = UNKNOWN.search(comment)
    return [i.strip() for i in found.group(1).split(",") if i.strip()] if found else []


def resolves(ids: list[str], spec_dir: pathlib.Path) -> bool:
    """Whether every identifier resolves now, as `spec-check` resolves one."""
    defined, retired, drafts = defined_ids(spec_dir), retired_ids(spec_dir), draft_ids(spec_dir)
    return bool(ids) and all(i in defined and i not in retired and i not in drafts for i in ids)


def gh(args: list[str]) -> object:
    """One REST call through `gh`, as JSON."""
    done = subprocess.run(["gh", "api", *args], capture_output=True, text=True, check=True)
    return json.loads(done.stdout) if done.stdout.strip() else None


def candidates(ids: set[str], owner: str, api: Api) -> set[tuple[str, int]]:
    """Each closed, unmerged pull request whose comments name one of the ids
    beside `spec-check`'s closing words, as `(repo, number)`."""
    found: set[tuple[str, int]] = set()
    for ident in sorted(ids):
        query = f'org:{owner} is:pr is:closed is:unmerged "{ident}" "spec-check closed this"'
        result = api(["-X", "GET", "search/issues", "-f", f"q={query}", "-f", "per_page=100"])
        for item in result["items"]:
            repo = item["repository_url"].rsplit("/", 2)
            found.add((f"{repo[-2]}/{repo[-1]}", item["number"]))
    return found


def owed(repo: str, number: int, spec_dir: pathlib.Path, api: Api) -> list[str] | None:
    """The identifiers to name in the reopening comment, or None where the pull
    request is not this one's to reopen: merged, closed by somebody else since,
    or closed for something that still does not resolve."""
    pull = api([f"repos/{repo}/pulls/{number}"])
    if pull["state"] != "closed" or pull["merged"]:
        return None
    events = api([f"repos/{repo}/issues/{number}/events?per_page=100"])
    closes = [e for e in events if e["event"] == "closed"]
    if not closes or (closes[-1].get("actor") or {}).get("login") != CLOSER:
        return None
    comments = api([f"repos/{repo}/issues/{number}/comments?per_page=100"])
    closing = [c["body"] for c in comments if unknown_in(c["body"])]
    if not closing:
        return None
    last = unknown_in(closing[-1])  # the newest closing comment decides
    return last if resolves(last, spec_dir) else None


def reopen(repo: str, number: int, ids: list[str], sha: str, api: Api) -> None:
    """Reopen the pull request and say why."""
    api(["-X", "PATCH", f"repos/{repo}/pulls/{number}", "-f", "state=open"])
    body = (f"Reopened: {', '.join(ids)} {'is' if len(ids) == 1 else 'are'} defined on "
            f"spec@main as of {sha[:7]}, so the citation `spec-check` closed this for now "
            "resolves and it runs again on this reopen (GOV-R56).")
    api(["-X", "POST", f"repos/{repo}/issues/{number}/comments", "-f", f"body={body}"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec-dir", required=True)
    parser.add_argument("--diff-file", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--owner", default="lemonfiber")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        ids = newly_defined(within_cwd(args.diff_file).read_text(encoding="utf-8"))
        spec_dir = within_cwd(args.spec_dir)
        if not ids:
            print("the push defines no identifier; nothing waits on it")
            return 0
        print(f"defined by this push: {', '.join(sorted(ids))}")
        for repo, number in sorted(candidates(ids, args.owner, gh)):
            due = owed(repo, number, spec_dir, gh)
            if due is None:
                print(f"{repo}#{number}: left alone")
                continue
            if args.dry_run:
                print(f"{repo}#{number}: would reopen, {', '.join(due)} now resolving")
                continue
            try:
                reopen(repo, number, due, args.sha, gh)
                print(f"{repo}#{number}: reopened, {', '.join(due)} now resolving")
            except subprocess.CalledProcessError as refused:
                print(f"::warning::{repo}#{number} could not be reopened: {refused.stderr.strip()}")
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as broken:
        print(f"::error::{broken}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
