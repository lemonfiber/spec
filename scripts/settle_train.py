#!/usr/bin/env python3
"""Merge each of the release train's pull requests once every check on its head is green — OPS-R96.

GitHub's auto-merge merges once the checks branch protection requires have
passed, and a check nothing requires can still be running, or red, when it does.
The train therefore arms nothing on the forge. A rolling pull request it means
to merge carries the label `LABEL`, and this merges each one that is the train's
own and whose head has settled green.

The train's own, read from the pull request itself and never from the search
that found it: opened by the train's bot, from a branch of the repository it
merges into, not a draft, into that repository's default branch, its head a
verified commit the train's bot authored, and `LABEL` put on it by the train's
bot. A pull request that is not is held, whatever its checks say.

Settled green:

- every context the base branch's protection requires has reported on the head;
- the latest check run of each name has completed as one of `PASSING`;
- the latest commit status of each context is `success`;
- nothing has moved on the head for `QUIET`: no push and no check run started,
  finished or status set, so a workflow that starts late is not stepped over.

A head where a check is still queued, running or pending, a required one has not
reported, or something moved within `QUIET`, is left for a later look. One red,
one still unsettled once its head is older than `BOUND`, and one whose protection,
checks or statuses cannot be read are held: the pull request carries one comment
saying why, edited in place on each look rather than repeated, and waits for a
person. A new head the train pushes is judged afresh.

A pull request is merged squashing, at the head this look judged, with its own
title and body as the commit, so a push landing after the judgement is never
what merges.

Which pull request is judged is one the workflow's search for the train's marked
pull requests listed; whose it is, is then read again here.

Usage:
  settle_train.py --owner <org> --author <app-slug> --repo <owner/name> --number <n>

Exit 0 having merged the pull request, left it for a later look, or held it for a
check; 1 where it was held for being unreadable or not the train's own, or the
merge was refused; 2 where the arguments are malformed.
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

#: How long nothing may have moved on a head before it is merged.
QUIET = datetime.timedelta(minutes=10)

#: How long a head may stay unsettled before the train stops waiting for it.
BOUND = datetime.timedelta(hours=6)

#: The committer GitHub records on a commit it signed for an API call, which is
#: how the train's commits are made.
SIGNED_BY_GITHUB = "web-flow"

#: The first line of the comment that says why a pull request is held, by which
#: a later look finds it again.
MARKER = "<!-- settle-train -->"

#: The most items one page is asked for.
PER_PAGE = 100

OWNER = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9-]*\Z")
SLUG = re.compile(r"\A[a-z0-9][a-z0-9-]*\Z")
REPO = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._][A-Za-z0-9._-]*\Z")
NUMBER = re.compile(r"\A[1-9][0-9]{0,9}\Z")

#: One call to the forge: the method, the path and the JSON payload, if any.
Api = Callable[[str, str, dict | None], object]


@dataclass
class Verdict:
    """What one head's checks come to: merge it, wait for it, or hold it, and why."""

    unsettled: list[str] = field(default_factory=list)
    red: list[str] = field(default_factory=list)

    def merges(self) -> bool:
        return not self.unsettled and not self.red


class Held(Exception):
    """A pull request held for a reason no later look clears by itself; never merged."""


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


def moment(text: str) -> datetime.datetime:
    """A timestamp as the API writes it."""
    return datetime.datetime.fromisoformat(text)


def latest(items: list[dict], name: str, at: Callable[[dict], tuple]) -> dict[str, dict]:
    """The latest of each name, so a run superseded by its rerun no longer counts."""
    kept: dict[str, dict] = {}
    for item in items:
        held = kept.get(item[name])
        if held is None or at(item) > at(held):
            kept[item[name]] = item
    return kept


def judged(
    runs: list[dict],
    statuses: list[dict],
    required: set[str],
    pushed: datetime.datetime,
    now: datetime.datetime,
) -> Verdict:
    """What every check run and commit status on one head comes to."""
    verdict = Verdict()
    ran = latest(runs, "name", lambda run: (run.get("started_at") or "", run["id"]))
    set_ = latest(statuses, "context", lambda status: (status["updated_at"], status["id"]))
    if not ran and not set_:
        verdict.unsettled.append("no check has reported on it")
    for context in sorted(required - ran.keys() - set_.keys()):
        verdict.unsettled.append(f"{context}, which the branch requires, has not reported")
    for name, run in sorted(ran.items()):
        if run["status"] != "completed":
            verdict.unsettled.append(f"{name} is {run['status']}")
        elif run["conclusion"] not in PASSING:
            verdict.red.append(f"{name} ended {run['conclusion']}")
    for context, status in sorted(set_.items()):
        if status["state"] == "pending":
            verdict.unsettled.append(f"{context} is pending")
        elif status["state"] != "success":
            verdict.red.append(f"{context} is {status['state']}")
    moved = [pushed]
    moved += [moment(run[key]) for run in runs for key in ("started_at", "completed_at") if run.get(key)]
    moved += [moment(status["updated_at"]) for status in statuses]
    if now - max(moved) < QUIET:
        verdict.unsettled.append(f"something moved on it within the last {QUIET}")
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


def strangers(api: Api, repo: str, pull: dict, bot: str) -> list[str]:
    """Every way the pull request is not the train's own, read from the forge."""
    found = []
    if pull["user"]["login"] != bot or pull["user"].get("type") != "Bot":
        found.append(f"it was opened by {pull['user']['login']}, not {bot}")
    if pull["state"] != "open" or pull.get("merged_at"):
        found.append("it is not open")
    if pull.get("draft"):
        found.append("it is a draft")
    if (pull["head"].get("repo") or {}).get("full_name") != repo:
        found.append("its branch is not this repository's own")
    if (
        pull["base"]["repo"]["full_name"] != repo
        or pull["base"]["ref"] != pull["base"]["repo"]["default_branch"]
    ):
        found.append(f"it is not into {repo}'s default branch")
    if LABEL not in {label["name"] for label in pull.get("labels", [])}:
        found.append(f"it does not carry {LABEL}")
    commit = api("GET", f"repos/{repo}/commits/{pull['head']['sha']}", None)
    if (commit.get("author") or {}).get("login") != bot:
        found.append(f"its head was not authored by {bot}")
    if (commit.get("committer") or {}).get("login") not in {bot, SIGNED_BY_GITHUB}:
        found.append(f"its head was not committed by {bot}")
    if not commit["commit"]["verification"]["verified"]:
        found.append("its head is not a verified commit")
    labelled_by = [
        event["actor"]["login"]
        for event in paged(api, f"repos/{repo}/issues/{pull['number']}/events", None)
        if event["event"] == "labeled" and event.get("label", {}).get("name") == LABEL
    ]
    if not labelled_by or labelled_by[-1] != bot:
        found.append(
            f"{LABEL} was put on it by {labelled_by[-1] if labelled_by else 'nobody it could see'}, not {bot}"
        )
    return found


def required_contexts(api: Api, repo: str, branch: str) -> set[str]:
    """Every context the branch's protection will refuse a merge over."""
    held = api("GET", f"repos/{repo}/branches/{branch}/protection/required_status_checks", None)
    return set(held.get("contexts", [])) | {check["context"] for check in held.get("checks", [])}


def reason(lines: list[str], head: str) -> str:
    """The comment a held pull request carries, naming what holds it."""
    return "\n".join(
        [MARKER, f"The release train is not merging this at `{head}`:", ""]
        + [f"- {one}" for one in lines]
        + ["", "It merges once every check on a head it pushes is green."]
    )


def said(api: Api, repo: str, number: int, body: str) -> None:
    """Put `body` in the train's one comment on the pull request, editing it where it is there."""
    comments = paged(api, f"repos/{repo}/issues/{number}/comments", None)
    mine = next((one for one in comments if one["body"].startswith(MARKER)), None)
    if mine is None:
        api("POST", f"repos/{repo}/issues/{number}/comments", {"body": body})
    elif mine["body"] != body:
        api("PATCH", f"repos/{repo}/issues/comments/{mine['id']}", {"body": body})


def held(api: Api, repo: str, number: int, head: str, lines: list[str]) -> Held:
    """Say why on the pull request, and the exception that fails the look for it."""
    said(api, repo, number, reason(lines, head))
    return Held(f"{repo}#{number} held at {head}: {'; '.join(lines)}")


def settled(api: Api, repo: str, number: int, bot: str, now: datetime.datetime) -> str:
    """Judge one pull request and merge or hold it; what it came to, said in one line."""
    pull = api("GET", f"repos/{repo}/pulls/{number}", None)
    head = pull["head"]["sha"]
    try:
        found = strangers(api, repo, pull, bot)
    except subprocess.CalledProcessError as failed:
        found = [f"whose it is could not be read: {(failed.stderr or '').strip()}"]
    if found:
        raise held(api, repo, number, head, found)
    try:
        required = required_contexts(api, repo, pull["base"]["ref"])
        runs = paged(api, f"repos/{repo}/commits/{head}/check-runs?filter=all", "check_runs")
        statuses = paged(api, f"repos/{repo}/commits/{head}/statuses", None)
        pushed = moment(api("GET", f"repos/{repo}/commits/{head}", None)["commit"]["committer"]["date"])
    except subprocess.CalledProcessError as failed:
        raise held(
            api,
            repo,
            number,
            head,
            [f"its protection, checks or statuses could not be read: {(failed.stderr or '').strip()}"],
        ) from failed
    verdict = judged(runs, statuses, required, pushed, now)
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
    stale = now - pushed > BOUND
    if verdict.red or stale:
        lines = verdict.red + (
            [f"{one}, and the head is older than {BOUND}" for one in verdict.unsettled] if stale else []
        )
        said(api, repo, number, reason(lines, head))
        return f"{repo}#{number} held at {head}: {'; '.join(lines)}"
    return f"{repo}#{number} waits at {head}: {'; '.join(verdict.unsettled)}"


def main(argv: list[str], api: Api = gh, now: datetime.datetime | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--owner", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--number", required=True)
    args = parser.parse_args(argv)
    if (
        not OWNER.match(args.owner)
        or not SLUG.match(args.author)
        or not REPO.match(args.repo)
        or not args.repo.startswith(f"{args.owner}/")
        or not NUMBER.match(args.number)
    ):
        print("::error::--owner, --author, --repo or --number is not one GitHub gives here", file=sys.stderr)
        return 2
    at = now or datetime.datetime.now(datetime.UTC)
    try:
        print(settled(api, args.repo, int(args.number), f"{args.author}[bot]", at))
    except Held as why:
        print(f"::error::{why}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as failed:
        print(f"::error::{args.repo}#{args.number} was not merged: {failed.stderr}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
