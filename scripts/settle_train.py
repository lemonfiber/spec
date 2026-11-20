#!/usr/bin/env python3
"""Merge each of the release train's pull requests once every check on its head is green — OPS-R96.

GitHub's auto-merge merges once the checks branch protection requires have
passed, and a check nothing requires can still be running, or red, when it does.
The train therefore arms nothing on the forge. A rolling pull request it means
to merge carries the label `LABEL`, and this merges each one that is the train's
own and whose head has settled green.

The train's own, read from the pull request itself and never from the search
that found it: opened by the train's bot, from a branch of the repository it
merges into, not a draft, into that repository's default branch; every commit
between that branch and the head verified, authored by the bot and committed by
it or by GitHub signing for it; the head carrying `RECORD`, the check run only
the train's App can create, which it creates on each head it pushes, with no
push to the branch by anyone else since; and `LABEL` put on it by the bot. A
commit's author and committer are claims anyone can write, so it is the record
that ties the head to the train. A pull request that is not the train's own is
held, whatever its checks say.

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
import urllib.parse
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

#: The check run the train creates on each head it pushes, which only its App can
#: put its name to, so a head it did not push is never taken for one it did.
RECORD = "train / pushed"

#: The app GitHub Actions reports its jobs' check runs as.
ACTIONS = "github-actions"

#: The timeline events that move a pull request's branch other than by a commit.
PUSHES = frozenset({"head_ref_force_pushed", "head_ref_deleted", "head_ref_restored"})

#: The first line of the comment that says why a pull request is held, by which
#: a later look finds it again.
MARKER = "<!-- settle-train -->"

#: The most items one page is asked for.
PER_PAGE = 100

OWNER = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9-]*\Z")
SLUG = re.compile(r"\A[a-z0-9][a-z0-9-]*\Z")
REPO = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._][A-Za-z0-9._-]*\Z")
NUMBER = re.compile(r"\A[1-9]\d{0,9}\Z")

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


def quote(branch: str) -> str:
    """A branch as it sits in a URL: its slashes kept, everything else escaped."""
    return urllib.parse.quote(branch, safe="/")


def moment(text: str) -> datetime.datetime:
    """A timestamp as the API writes it."""
    return datetime.datetime.fromisoformat(text)


def latest(items: list[dict], key: Callable[[dict], tuple], at: Callable[[dict], tuple]) -> dict[tuple, dict]:
    """The latest of each check, so a run superseded by a later one of the same check no longer counts."""
    kept: dict[tuple, dict] = {}
    for item in items:
        held = kept.get(key(item))
        if held is None or at(item) > at(held):
            kept[key(item)] = item
    return kept


def workflows(api: Api, repo: str, runs: list[dict]) -> dict[int, str]:
    """Which workflow each Actions check suite on the head belongs to.

    Two workflows can each have a job of the same name, and those are two checks: a
    run supersedes another only within the same workflow. A suite whose workflow
    cannot be found is a check of its own.
    """
    found: dict[int, str] = {}
    for suite in sorted({run["check_suite"]["id"] for run in runs if run["app"]["slug"] == ACTIONS}):
        listed = api("GET", f"repos/{repo}/actions/runs?check_suite_id={suite}", None)["workflow_runs"]
        found[suite] = f"workflow {listed[0]['workflow_id']}" if listed else f"suite {suite}"
    return found


def judged(
    runs: list[dict],
    statuses: list[dict],
    required: set[str],
    owners: dict[int, str],
    times: tuple[datetime.datetime, datetime.datetime],
) -> Verdict:
    """What every check run and commit status on one head comes to, `times` being its push and now."""
    pushed, now = times

    def owner(run: dict) -> str:
        return owners.get(run["check_suite"]["id"], run["app"]["slug"])

    verdict = Verdict()
    ran = latest(
        runs, lambda run: (owner(run), run["name"]), lambda run: (run.get("started_at") or "", run["id"])
    )
    set_ = latest(
        statuses, lambda status: (status["context"],), lambda status: (status["updated_at"], status["id"])
    )
    reported = {name for _, name in ran} | {context for (context,) in set_}
    if not reported - {RECORD}:
        verdict.unsettled.append("no check has reported on it")
    verdict.unsettled += [
        f"{context}, which the branch requires, has not reported" for context in sorted(required - reported)
    ]
    for (_, name), run in sorted(ran.items()):
        if run["status"] != "completed":
            verdict.unsettled.append(f"{name} is {run['status']}")
        elif run["conclusion"] not in PASSING:
            verdict.red.append(f"{name} ended {run['conclusion']}")
    for (context,), status in sorted(set_.items()):
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


def strangers(api: Api, repo: str, pull: dict, slug: str, runs: list[dict]) -> list[str]:
    """Every way the pull request is not the train's own, read from the forge."""
    bot = f"{slug}[bot]"
    timeline = paged(api, f"repos/{repo}/issues/{pull['number']}/timeline", None)
    return (
        unlike(pull, repo, bot)
        + foreign_commits(api, repo, pull["base"]["ref"], pull["head"]["sha"], bot)
        + unrecorded(runs, timeline, slug)
        + unlabelled(timeline, bot)
    )


def unlike(pull: dict, repo: str, bot: str) -> list[str]:
    """Every way the pull request itself is not one the train opened into the default branch."""
    base = pull["base"]
    checks = [
        (
            pull["user"]["login"] == bot and pull["user"].get("type") == "Bot",
            f"it was opened by {pull['user']['login']}, not {bot}",
        ),
        (pull["state"] == "open" and not pull.get("merged_at"), "it is not open"),
        (not pull.get("draft"), "it is a draft"),
        (
            (pull["head"].get("repo") or {}).get("full_name") == repo,
            "its branch is not this repository's own",
        ),
        (
            base["repo"]["full_name"] == repo and base["ref"] == base["repo"]["default_branch"],
            f"it is not into {repo}'s default branch",
        ),
        (LABEL in {label["name"] for label in pull.get("labels", [])}, f"it does not carry {LABEL}"),
    ]
    return [why for holds, why in checks if not holds]


def unrecorded(runs: list[dict], timeline: list[dict], slug: str) -> list[str]:
    """Whether the head is not one the train recorded pushing, or was moved by somebody else since."""
    bot = f"{slug}[bot]"
    records = [
        run
        for run in runs
        if run["name"] == RECORD and run["app"]["slug"] == slug and run["conclusion"] == "success"
    ]
    if not records:
        return [f"{slug} recorded no push of this head as {RECORD}"]
    recorded = min(moment(run["started_at"]) for run in records)
    return [
        f"{(event.get('actor') or {}).get('login')} moved its branch ({event['event']}) after the train pushed it"
        for event in timeline
        if event.get("event") in PUSHES
        and (event.get("actor") or {}).get("login") != bot
        and moment(event["created_at"]) >= recorded
    ]


def unlabelled(timeline: list[dict], bot: str) -> list[str]:
    """Whether the mark was last put on by somebody other than the train."""
    labelled_by = [
        (event.get("actor") or {}).get("login")
        for event in timeline
        if event.get("event") == "labeled" and (event.get("label") or {}).get("name") == LABEL
    ]
    if labelled_by and labelled_by[-1] == bot:
        return []
    return [
        f"{LABEL} was put on it by {labelled_by[-1] if labelled_by else 'nobody it could see'}, not {bot}"
    ]


def foreign_commits(api: Api, repo: str, branch: str, head: str, bot: str) -> list[str]:
    """Every commit between the base branch and the head that the train did not make."""
    found = []
    commits: list[dict] = []
    total = None
    page = 1
    while True:
        compared = api(
            "GET", f"repos/{repo}/compare/{quote(branch)}...{head}?per_page={PER_PAGE}&page={page}", None
        )
        total = compared["total_commits"]
        commits += compared["commits"]
        if len(compared["commits"]) < PER_PAGE:
            break
        page += 1
    if not commits or len(commits) != total:
        found.append(f"its {total} commit(s) past {branch} could not all be read")
    for commit in commits:
        sha = commit["sha"][:12]
        if (commit.get("author") or {}).get("login") != bot:
            found.append(f"{sha} was not authored by {bot}")
        if (commit.get("committer") or {}).get("login") not in {bot, SIGNED_BY_GITHUB}:
            found.append(f"{sha} was not committed by {bot}")
        if not commit["commit"]["verification"]["verified"]:
            found.append(f"{sha} is not a verified commit")
    return found


def required_contexts(api: Api, repo: str, branch: str) -> set[str]:
    """Every context the branch's protection and its rulesets will refuse a merge over.

    Either may be where a repository states them, and one may hold some and the other
    the rest, so both are read and the union taken. Only where neither can be read is
    the pull request held.
    """
    contexts: set[str] = set()
    failures: list[subprocess.CalledProcessError] = []
    try:
        held = api("GET", f"repos/{repo}/branches/{quote(branch)}/protection/required_status_checks", None)
        contexts |= set(held.get("contexts", [])) | {check["context"] for check in held.get("checks", [])}
    except subprocess.CalledProcessError as failed:
        failures.append(failed)
    try:
        rules = paged(api, f"repos/{repo}/rules/branches/{quote(branch)}", None)
        contexts |= {
            check["context"]
            for rule in rules
            if rule["type"] == "required_status_checks"
            for check in rule["parameters"]["required_status_checks"]
        }
    except subprocess.CalledProcessError as failed:
        failures.append(failed)
    if len(failures) == 2:
        raise failures[0]
    return contexts


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


def settled(api: Api, repo: str, number: int, slug: str, now: datetime.datetime) -> str:
    """Judge one pull request and merge or hold it; what it came to, said in one line."""
    pull = api("GET", f"repos/{repo}/pulls/{number}", None)
    head = pull["head"]["sha"]
    try:
        required = required_contexts(api, repo, pull["base"]["ref"])
        runs = paged(api, f"repos/{repo}/commits/{head}/check-runs?filter=all", "check_runs")
        statuses = paged(api, f"repos/{repo}/commits/{head}/statuses", None)
        pushed = moment(api("GET", f"repos/{repo}/commits/{head}", None)["commit"]["committer"]["date"])
        owners = workflows(api, repo, runs)
    except subprocess.CalledProcessError as failed:
        raise held(
            api,
            repo,
            number,
            head,
            [f"its protection, checks or statuses could not be read: {(failed.stderr or '').strip()}"],
        ) from failed
    try:
        found = strangers(api, repo, pull, slug, runs)
    except subprocess.CalledProcessError as failed:
        found = [f"whose it is could not be read: {(failed.stderr or '').strip()}"]
    if found:
        raise held(api, repo, number, head, found)
    verdict = judged(runs, statuses, required, owners, (pushed, now))
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
        print(settled(api, args.repo, int(args.number), args.author, at))
    except Held as why:
        print(f"::error::{why}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as failed:
        print(f"::error::{args.repo}#{args.number} was not merged: {failed.stderr}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
