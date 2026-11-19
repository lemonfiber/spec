#!/usr/bin/env python3
"""Merge each of the release train's pull requests once every check on its head is green — OPS-R87.

GitHub's auto-merge merges once the checks branch protection requires have
passed, and a check nothing requires can still be running, or red, when it does.
The train therefore arms nothing on the forge. A rolling pull request it means
to merge carries the label `LABEL`, and this merges each one whose every check
on its head has settled green:

- every check run, the latest of each name, has completed as one of `PASSING`;
- every commit status, the latest of each context, is `success`.

A check still queued or running, or a status still pending, leaves the pull
request open for the next run. One red, one still unsettled once its head is
older than `BOUND`, or one whose checks or statuses cannot be read, holds it: the pull request carries one comment saying which
checks and why, edited in place on each run rather than repeated, and waits for
a person. A new head the train pushes is judged afresh.

A pull request is merged squashing, at the head this run judged, with its own
title and body as the commit, so a push landing after the judgement is never
what merges.

Usage:
  settle_train.py --owner <org> --author <app-slug>

Exit 0 having judged every labelled pull request, whatever each came to; 1 where
the checks of any could not be read, each such one held; 2 where the arguments
are malformed or the labelled pull requests could not be listed.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field

#: The label a rolling pull request carries where the train is to merge it.
LABEL = "train-merges"

#: How a pull request is merged, as the REST API names it.
MERGE_METHOD = "squash"

#: The conclusions a completed check run passes with. `neutral` is GitHub's
#: conclusion for a check that gave no verdict, such as code scanning with no
#: configuration to compare against.
PASSING = frozenset({"success", "skipped", "neutral"})

#: How long a head may stay unsettled before the train stops waiting for it.
BOUND = datetime.timedelta(hours=6)

#: The first line of the comment that says why a pull request is held, by which
#: a later run finds it again.
MARKER = "<!-- settle-train -->"

#: The most items one page is asked for.
PER_PAGE = 100

OWNER = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9-]*\Z")
SLUG = re.compile(r"\A[a-z0-9][a-z0-9-]*\Z")

#: One call to the forge: the method, the path and the JSON payload, if any.
Api = Callable[[str, str, dict | None], object]


@dataclass
class Verdict:
    """What one head's checks come to: merge it, wait for it, or hold it, and why."""

    unsettled: list[str] = field(default_factory=list)
    red: list[str] = field(default_factory=list)

    def merges(self) -> bool:
        return not self.unsettled and not self.red


def gh(method: str, path: str, payload: dict | None = None) -> object:
    """One call through `gh api`, the payload as JSON on its standard input."""
    args = ["gh", "api", "--method", method, path]
    if payload is not None:
        args += ["--input", "-"]
    done = subprocess.run(
        args,
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(done.stdout) if done.stdout.strip() else {}


def latest(items: list[dict], name: str, at: Callable[[dict], tuple]) -> dict[str, dict]:
    """The latest of each name, so a run superseded by its rerun no longer counts."""
    kept: dict[str, dict] = {}
    for item in items:
        held = kept.get(item[name])
        if held is None or at(item) > at(held):
            kept[item[name]] = item
    return kept


def judged(runs: list[dict], statuses: list[dict]) -> Verdict:
    """What every check run and commit status on one head comes to."""
    verdict = Verdict()
    for name, run in sorted(
        latest(runs, "name", lambda run: (run.get("started_at") or "", run["id"])).items()
    ):
        if run["status"] != "completed":
            verdict.unsettled.append(f"{name} is {run['status']}")
        elif run["conclusion"] not in PASSING:
            verdict.red.append(f"{name} ended {run['conclusion']}")
    for context, status in sorted(
        latest(statuses, "context", lambda status: (status["updated_at"], status["id"])).items()
    ):
        if status["state"] == "pending":
            verdict.unsettled.append(f"{context} is pending")
        elif status["state"] != "success":
            verdict.red.append(f"{context} is {status['state']}")
    return verdict


def paged(api: Api, path: str, key: str | None) -> list[dict]:
    """Every item a listing holds, page by page."""
    items: list[dict] = []
    page = 1
    while True:
        answer = api("GET", f"{path}{'&' if '?' in path else '?'}per_page={PER_PAGE}&page={page}", None)
        found = answer[key] if key else answer
        items.extend(found)
        if len(found) < PER_PAGE:
            return items
        page += 1


class Unread(Exception):
    """A head whose checks or statuses could not be read; it is held, never merged."""


def held_reason(verdict: Verdict, head: str, stale: bool) -> str:
    """The comment a held pull request carries, naming what holds it."""
    lines = [MARKER, f"The release train is not merging this at `{head}`:", ""]
    lines += [f"- {one}" for one in verdict.red]
    if stale:
        lines += [f"- {one}, and the head is older than {BOUND}" for one in verdict.unsettled]
    lines += ["", "It merges once every check on a head it pushes is green."]
    return "\n".join(lines)


def said(api: Api, repo: str, number: int, body: str) -> None:
    """Put `body` in the train's one comment on the pull request, editing it where it is there."""
    comments = paged(api, f"repos/{repo}/issues/{number}/comments", None)
    mine = next((one for one in comments if one["body"].startswith(MARKER)), None)
    if mine is None:
        api("POST", f"repos/{repo}/issues/{number}/comments", {"body": body})
    elif mine["body"] != body:
        api("PATCH", f"repos/{repo}/issues/comments/{mine['id']}", {"body": body})


def settled(api: Api, repo: str, number: int, now: datetime.datetime) -> str:
    """Judge one pull request and merge or hold it; what it came to, said in one line."""
    pull = api("GET", f"repos/{repo}/pulls/{number}", None)
    head = pull["head"]["sha"]
    try:
        runs = paged(api, f"repos/{repo}/commits/{head}/check-runs?filter=all", "check_runs")
        statuses = paged(api, f"repos/{repo}/commits/{head}/statuses", None)
    except subprocess.CalledProcessError as failed:
        unread = Verdict(red=[f"its checks or statuses could not be read: {(failed.stderr or '').strip()}"])
        said(api, repo, number, held_reason(unread, head, stale=False))
        raise Unread(f"{repo}#{number} held at {head}: {unread.red[0]}") from failed
    verdict = judged(runs, statuses)
    if verdict.merges():
        api(
            "PUT",
            f"repos/{repo}/pulls/{number}/merge",
            {
                "merge_method": MERGE_METHOD,
                "sha": head,
                "commit_title": f"{pull['title']} (#{number})",
                "commit_message": pull["body"] or "",
            },
        )
        return f"{repo}#{number} merged at {head}"
    committed = api("GET", f"repos/{repo}/commits/{head}", None)["commit"]["committer"]["date"]
    stale = now - datetime.datetime.fromisoformat(committed) > BOUND
    if verdict.red or stale:
        said(api, repo, number, held_reason(verdict, head, stale))
        return f"{repo}#{number} held at {head}: {'; '.join(verdict.red + verdict.unsettled)}"
    return f"{repo}#{number} waits at {head}: {'; '.join(verdict.unsettled)}"


def labelled(api: Api, owner: str, author: str) -> list[tuple[str, int]]:
    """Every open pull request the train opened in `owner` and means to merge."""
    query = f"is:pr is:open org:{owner} author:app/{author} label:{LABEL}"
    found = paged(api, f"search/issues?q={query.replace(' ', '+')}", "items")
    return [(one["repository_url"].split("/repos/", 1)[1], one["number"]) for one in found]


def main(argv: list[str], api: Api = gh, now: datetime.datetime | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--owner", required=True)
    parser.add_argument("--author", required=True)
    args = parser.parse_args(argv)
    if not OWNER.match(args.owner) or not SLUG.match(args.author):
        print("::error::--owner or --author is not a name GitHub gives", file=sys.stderr)
        return 2
    moment = now or datetime.datetime.now(datetime.UTC)
    try:
        marked = labelled(api, args.owner, args.author)
    except subprocess.CalledProcessError as failed:
        print(f"::error::the train's pull requests could not be listed: {failed.stderr}", file=sys.stderr)
        return 2
    verdict = 0
    for repo, number in marked:
        try:
            print(settled(api, repo, number, moment))
        except Unread as unread:
            print(f"::error::{unread}", file=sys.stderr)
            verdict = 1
        except subprocess.CalledProcessError as failed:
            print(f"::error::{repo}#{number} was not merged: {failed.stderr}", file=sys.stderr)
            verdict = 1
    return verdict


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
