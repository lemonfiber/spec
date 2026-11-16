#!/usr/bin/env python3
"""The pull request a `workflow_run` was started for, read from the forge — Q-R84.

A privileged follow-up runs on `workflow_run`, from the default branch, after an
unprivileged relay ran on `pull_request`. Everything the relay's run carries
that the pull request could have written, an artifact, a run name, a job's
output, is the pull request's to say. What the forge sets on the run is not:
the repository and branch the head came from and the head commit. So the pull
request is found from those alone, through the API: the open pull request into
this repository whose head is that commit on that branch of that repository.
A label a follow-up acts on is read the same way, from the pull request's
timeline, and bound to the head it was added on: on it now, last added by an
account holding one of the roles named, on the head being acted on, which the
branch had held for `--quiet` seconds, read from the relay's runs, and before
the run that started this was created.

Usage, writing the pull request's fields to `GITHUB_OUTPUT` for a later step:
  run_pull.py --repo <owner/name> --source <owner/name> --branch <head branch>
              --head <head commit> [--label <name> --relay <the relay's path>
              [--roles <permission,...>] [--quiet <seconds>] [--started <time>]]

`approved=true` is written only where `--label` approves the head as above. Exit 0 whether
or not a pull request or an approval was found, since the run that started this
may be for a head that has moved on; 2 where the forge could not be read or the
arguments are not the shapes the forge gives them.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.parse
from collections.abc import Callable

#: One call to the forge's REST API through `gh`: the arguments, the answer as JSON.
Api = Callable[[list[str]], object]

#: The permissions whose label approves a proposal, as the collaborator API names them.
WRITERS = ("admin", "write")

#: A repository as the forge names it.
REPOSITORY = re.compile(r"\A[\w.-]+/[\w.-]+\Z")

#: The relay's path in the repository, as `--relay` and `github.event.workflow_run.path` give it.
RELAY_PATH = re.compile(r"\A\.github/workflows/(?P<file>[\w.-]+\.ya?ml)\Z")

#: A commit as the forge names it.
COMMIT = re.compile(r"\A[0-9a-f]{40}\Z")

#: Seconds the branch must have held a head before a label approves it. A push landing moments
#: before the label is a head the maintainer may not have read.
QUIET = 60

#: The events whose runs of the relay record each head a pull request's branch had: its own, and
#: the one the relay ran on before it, whose runs a label added then was read against.
RELAY_EVENTS = ("pull_request", "pull_request_target")

#: The most pages of a list read before the list is called too long to judge.
PAGES = 10

#: Items in one page of a list.
PER_PAGE = 100


class Ambiguous(ValueError):
    """More than one open pull request has the same head, so which one a run was for is unknown."""


class Incomplete(ValueError):
    """An answer the forge gave only in part."""


def gh(args: list[str]) -> object:
    """One REST call through `gh`."""
    done = subprocess.run(["gh", "api", *args], capture_output=True, text=True, check=True)
    return json.loads(done.stdout) if done.stdout.strip() else None


def listed(path: str, api: Api, key: str | None = None) -> list[dict]:
    """Every item of a list the forge pages, refused where it runs past `PAGES` pages."""
    joined = "&" if "?" in path else "?"
    items: list[dict] = []
    for page in range(1, PAGES + 1):
        answer = api([f"{path}{joined}per_page={PER_PAGE}&page={page}"])
        got = answer[key] if key else answer
        items += got
        if len(got) < PER_PAGE:
            return items
    raise Incomplete(f"{path} runs past {PAGES * PER_PAGE} items")


def pull_of_run(repo: str, source: str, branch: str, head: str, api: Api) -> dict | None:
    """The open pull request into `repo` whose head is `head` on `branch` of `source`, or None."""
    owner = source.split("/", 1)[0]
    query = urllib.parse.quote(f"{owner}:{branch}", safe="")
    found = [
        pull
        for pull in listed(f"repos/{repo}/pulls?state=open&head={query}", api)
        if pull["head"]["sha"] == head
        and (pull["head"].get("repo") or {}).get("full_name") == source
        and pull["head"]["ref"] == branch
        and pull["base"]["repo"]["full_name"] == repo
    ]
    if len(found) > 1:
        numbers = " and ".join(f"#{pull['number']}" for pull in found)
        raise Ambiguous(
            f"{numbers} are open with the head {head[:8]}, so which one this run was for is unknown"
        )
    return found[0] if found else None


def relay_runs(repo: str, workflow: str, source: str, branch: str, api: Api) -> list[dict]:
    """The relay's runs for a branch of `source`: the forge's record of each head the branch had."""
    quoted = urllib.parse.quote(branch, safe="")
    return [
        r
        for r in listed(
            f"repos/{repo}/actions/workflows/{workflow}/runs?branch={quoted}", api, "workflow_runs"
        )
        if r["head_repository"]["full_name"] == source and r["event"] in RELAY_EVENTS
    ]


def moment(stamp: str) -> datetime.datetime:
    """A time the forge recorded."""
    return datetime.datetime.fromisoformat(stamp)


def labelled_head(
    runs: list[dict], events: list[dict], at: str, label: str, quiet: int = QUIET
) -> tuple[str, str] | str:
    """The head the approval label was added on at `at` and the time the branch took it, or why it is unknown.

    The head of the newest run at or before the label; held for `quiet` seconds
    before it; and the head of the first run at or after it, the run the label
    started, so a push racing the label is never what is approved. A base changed
    after the label leaves nothing approved.
    """
    before = [r for r in runs if r["created_at"] <= at]
    if not before:
        return f"no run of this check shows what its head was when `{label}` was added at {at}"
    retargeted = sorted(
        e["created_at"] for e in events if e["event"] == "base_ref_changed" and e["created_at"] >= at
    )
    if retargeted:
        return f"its base was changed at {retargeted[-1]}, after `{label}` was added at {at}"
    newest = max(r["created_at"] for r in before)
    heads = sorted({r["head_sha"] for r in before if r["created_at"] == newest})
    if len(heads) > 1:
        return f"the runs at {newest} name {' and '.join(h[:8] for h in heads)}, so which head `{label}` was added on is unknown"
    approved = heads[0]
    held = [r["created_at"] for r in before if r["head_sha"] != approved]
    since = min(
        r["created_at"]
        for r in before
        if r["head_sha"] == approved and (not held or r["created_at"] > max(held))
    )
    if (moment(at) - moment(since)).total_seconds() < quiet:
        return (
            f"its head became {approved[:8]} at {since}, less than {quiet} seconds before `{label}` was "
            f"added at {at}, so the head the maintainer read is unknown"
        )
    started = sorted((r for r in runs if r["created_at"] >= at), key=lambda r: r["created_at"])
    if not started:
        return f"no run of this check started when `{label}` was added at {at}, so what it was added on is unconfirmed"
    if started[0]["head_sha"] != approved:
        return (
            f"the run `{label}` started at {at} is for {started[0]['head_sha'][:8]}, not {approved[:8]}, "
            f"so a push landed as it was added"
        )
    return approved, since


def last_added(repo: str, pull: dict, label: str, api: Api) -> tuple[dict, list[dict]] | None:
    """The event that last added `label`, where the pull request carries it now, and its timeline; None otherwise."""
    if label not in [one["name"] for one in pull["labels"]]:
        return None
    events = listed(f"repos/{repo}/issues/{pull['number']}/timeline", api)
    moves = [e for e in events if e["event"] in ("labeled", "unlabeled") and e["label"]["name"] == label]
    if not moves or moves[-1]["event"] != "labeled":
        return None
    return moves[-1], events


def unapproved(repo: str, pull: dict, head: str, rules: argparse.Namespace, api: Api) -> str | None:
    """Why `rules.label` does not approve `head`, or None where it does.

    The label is on the pull request now, last added by an account holding one
    of `rules.roles`; the head the branch held then, read from the relay's runs
    as `labelled_head` reads it, is `head`; and the run that started this was
    created at or after the label, so it answers the label and not an event
    before it.
    """
    added = last_added(repo, pull, rules.label, api)
    if added is None:
        return f"it does not carry `{rules.label}` as last added by anyone"
    event, events = added
    who = (event.get("actor") or {}).get("login")
    if not who or permission(repo, who, api) not in rules.roles:
        return f"`{rules.label}` was last added by {who or 'nobody the forge names'}, who holds none of {', '.join(rules.roles)}"
    at = event["created_at"]
    if rules.started and moment(rules.started) < moment(at):
        return f"the run that started this was created at {rules.started}, before `{rules.label}` was added at {at}"
    runs = relay_runs(repo, RELAY_PATH.fullmatch(rules.relay)["file"], rules.source, rules.branch, api)
    bound = labelled_head(runs, events, at, rules.label, rules.quiet)
    if isinstance(bound, str):
        return bound
    if bound[0] != head:
        return f"`{rules.label}` was added at {at} on {bound[0][:8]}, and the head is now {head[:8]}"
    print(
        f"#{pull['number']}: `{rules.label}` was last added by {who} at {at}, on {head}, which may approve it."
    )
    return None


def permission(repo: str, login: str, api: Api) -> str:
    """The account's permission on the repository, as the collaborator API names it."""
    answer = api([f"repos/{repo}/collaborators/{urllib.parse.quote(login, safe='')}/permission"])
    return answer.get("permission") or "none"


def shaped(args: argparse.Namespace) -> str | None:
    """Why the arguments are not the shapes the forge gives them, or None."""
    for name in ("repo", "source"):
        if not REPOSITORY.fullmatch(getattr(args, name)):
            return f"--{name} {getattr(args, name)!r} is not a repository"
    if not COMMIT.fullmatch(args.head):
        return f"--head {args.head!r} is not a commit"
    if not args.branch or "\n" in args.branch:
        return f"--branch {args.branch!r} is not a branch"
    if args.label and (not args.relay or not RELAY_PATH.fullmatch(args.relay)):
        return f"--relay {args.relay!r} is not a workflow's path, so the head `--label` was added on cannot be read"
    return None


def written(fields: dict[str, str]) -> None:
    """The fields, one `key=value` line each, to `GITHUB_OUTPUT` where Actions names one, else to stdout."""
    lines = "".join(f"{key}={value}\n" for key, value in fields.items())
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as out:
            out.write(lines)
    else:
        sys.stdout.write(lines)


def main(argv: list[str] | None = None, api: Api = gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--source", required=True, help="the repository the head came from")
    parser.add_argument("--branch", required=True, help="the branch the head came from")
    parser.add_argument("--head", required=True, help="the head commit the run was started for")
    parser.add_argument("--label", help="the label whose approval is read")
    parser.add_argument("--roles", default=",".join(WRITERS), help="the permissions whose label approves")
    parser.add_argument("--relay", help="the relay's path, whose runs record each head; with --label")
    parser.add_argument(
        "--quiet", type=int, default=QUIET, help="seconds a head is held before a label approves it"
    )
    parser.add_argument(
        "--started", help="when the run that started this was created, as the forge stamps it"
    )
    args = parser.parse_args(argv)
    wrong = shaped(args)
    if wrong:
        print(f"::error::{wrong}, so no pull request is read")
        return 2
    args.roles = tuple(role.strip() for role in args.roles.split(",") if role.strip())
    try:
        pull = pull_of_run(args.repo, args.source, args.branch, args.head, api)
        if pull is None:
            print(f"No open pull request has the head {args.head[:8]} on {args.source} {args.branch}.")
            written({"found": "false", "approved": "false"})
            return 0
        why = unapproved(args.repo, pull, args.head, args, api) if args.label else "no label was asked about"
    except (
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as broken:
        detail = getattr(broken, "stderr", "") or broken
        print(f"::error::The pull request this run was for could not be read: {detail}")
        return 2
    if args.label and why:
        print(f"#{pull['number']} is not approved: {why}.")
    written(
        {
            "found": "true",
            "approved": str(why is None).lower(),
            "number": str(pull["number"]),
            "author": pull["user"]["login"],
            "author_id": str(pull["user"]["id"]),
            "head_repo": args.source,
            "head_ref": args.branch,
            "head_sha": args.head,
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
