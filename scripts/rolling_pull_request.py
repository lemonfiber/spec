#!/usr/bin/env python3
"""Open a bump's rolling pull request, or edit it, only where it is the bump's own — OPS-R87.

An automated bump keeps one branch and one pull request on it (OPS-R85), and
each run finds that pull request again to retitle it and arm it to merge. Found
by branch name alone, it is not the bump's: `gh pr list --head <branch>` also
lists a fork's pull request whose branch has the same name, and a bump that
then edits it and arms auto-merge merges the fork's code once its checks pass.

So the pull request is found by the repository and the branch together, and
only one that is the bump's own is touched:

- the commit given must be the branch's tip, authored by the account the bump
  writes as and verified, so a caller cannot point this at a branch or a
  commit somebody else made;
- open pull requests are listed by `head=<owner>:<branch>`, and one whose head
  is not this repository's own branch is not the bump's;
- the bump's must be open and unmerged and have been opened by the account the
  bump writes as, the bot of the app whose token runs this, and one opened by
  anybody else is refused;
- its head must be the commit given, so a commit somebody else pushed there is
  never what is armed to merge.

Where none is open, one is opened from the branch, and checked the same way
once it exists. Auto-merge is armed at the given commit only, squashing, and
only where the caller asks for it, pinned to that commit so a push landing
after these checks is never what merges. `--disarm` switches off arming the
pull request already carries, for a run whose change wants reading: an armed
pull request stays armed across the app's own pushes, so without it a change
nobody has read would merge. Asking for neither leaves auto-merge as it is, a
maintainer's arming included.
Anything else edits nothing and fails, naming what it found.

Usage:
  rolling_pull_request.py --repo <owner/name> --branch <branch> --head <commit>
                          --author <login> --title=<title>
                          [--labels=<label>,<label>] [--auto-merge | --disarm] < body.md

`--author` is the login the bump's pull request was opened by, `<app>[bot]` for
an app. The body is read from standard input, so no file needs to be named and
none can be read but the one the caller hands over. The pull request's number is
printed on standard output; everything else is said on standard error.

Exit 0 having opened or edited the pull request, and armed or disarmed it where
asked; 1
where what is open on the branch is not the bump's own, or a head is not the
commit given, and nothing was edited; 2 where the arguments are malformed or the
forge could not be read or written.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
from collections.abc import Callable

#: The branch every rolling pull request merges into.
BASE = "main"

#: How the pull request is merged once armed, as the GraphQL enum names it.
MERGE_METHOD = "SQUASH"

#: The most open pull requests one `head` filter is asked for. One repository's
#: branch has at most one open pull request per base, so a page is plenty.
PER_PAGE = 100

#: The shapes a repository's name, a branch's and a commit's take. Each is held
#: before it reaches a URL, so none can be read there as a path out of the API's
#: repository and branch namespaces.
SLUG = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._][A-Za-z0-9._-]*\Z")
BRANCH = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*\Z")
COMMIT = re.compile(r"\A[0-9a-f]{40}\Z")

ARM = (
    "mutation($id: ID!, $method: PullRequestMergeMethod!, $head: GitObjectID!) "
    "{ enablePullRequestAutoMerge(input: {pullRequestId: $id, mergeMethod: $method, "
    "expectedHeadOid: $head}) { clientMutationId } }"
)

DISARM = (
    "mutation($id: ID!) "
    "{ disablePullRequestAutoMerge(input: {pullRequestId: $id}) { clientMutationId } }"
)

#: One call to the forge through `gh api`: the method, the path and the JSON
#: payload, if any, answered as JSON.
Api = Callable[[str, str, dict | None], object]


class Refused(Exception):
    """What is on the branch is not the bump's own; nothing was edited."""


def gh(method: str, path: str, payload: dict | None = None) -> object:
    """One call through `gh api`, the payload as JSON on its standard input."""
    args = ["gh", "api", "--method", method, path]
    if payload is not None:
        args += ["--input", "-"]
    done = subprocess.run(args, input=json.dumps(payload) if payload is not None else None,
                          capture_output=True, text=True, check=True)
    return json.loads(done.stdout) if done.stdout.strip() else {}


def quoted(branch: str) -> str:
    """A branch as it sits in a URL: its slashes kept, everything else escaped."""
    return urllib.parse.quote(branch, safe="/")


def graphql(api: Api, query: str, variables: dict) -> None:
    """One mutation, refused where the forge answered it with errors."""
    answer = api("POST", "graphql", {"query": query, "variables": variables})
    errors = answer.get("errors") if isinstance(answer, dict) else None
    if errors:
        raise subprocess.CalledProcessError(1, "gh api graphql", stderr=json.dumps(errors))


def wrong_with(pull: dict, author: str, head: str) -> str | None:
    """Why a pull request is not the bump's own at the given commit, or None."""
    number = pull["number"]
    user = pull.get("user") or {}
    login = user.get("login")
    if login != author or user.get("type") != "Bot":
        return f"#{number} was opened by {login or 'nobody known'}, not {author}, so it is not the bump's"
    if pull.get("state") != "open" or pull.get("merged_at") or pull.get("merged"):
        return f"#{number} is not open, and a closed or merged pull request is never edited"
    if pull["base"]["ref"] != BASE:
        return f"#{number} merges into {pull['base']['ref']}, not {BASE}"
    if pull["head"]["sha"] != head:
        return f"#{number} is at {pull['head']['sha']}, not {head}, the commit this run put on the branch"
    return None


def own(pulls: list[dict], repo: str, branch: str) -> list[dict]:
    """The open pull requests whose head is this repository's own branch."""
    found = []
    for pull in pulls:
        at = (pull["head"].get("repo") or {}).get("full_name")
        if at == repo and pull["head"]["ref"] == branch:
            found.append(pull)
        else:
            print(f"#{pull['number']} is from {at or 'a deleted repository'}:{pull['head']['ref']}, "
                  f"not {repo}:{branch}; it is not the bump's and is left alone", file=sys.stderr)
    return found


def the_bumps_commit(repo: str, branch: str, head: str, author: str, api: Api) -> None:
    """Refuse a head that is not the branch's tip, made and signed as the bump."""
    at = api("GET", f"repos/{repo}/git/ref/heads/{quoted(branch)}", None)["object"]["sha"]
    if at != head:
        raise Refused(f"{branch} is at {at}, not {head}, the commit this run put on it; nothing was edited")
    made = api("GET", f"repos/{repo}/commits/{head}", None)
    by = (made.get("author") or {}).get("login")
    if by != author or made["commit"]["verification"]["verified"] is not True:
        raise Refused(f"{head} was not made and signed as {author} (its author is {by or 'nobody known'}), "
                      "so it is not the bump's commit; nothing was edited")


def edited_or_opened(repo: str, branch: str, head: str, author: str, title: str, body: str,
                     labels: list[str], api: Api) -> dict:
    """The bump's own open pull request, edited, or one opened where none is; anything else refused."""
    owner = repo.split("/")[0]
    query = urllib.parse.urlencode({"head": f"{owner}:{branch}", "state": "open", "per_page": PER_PAGE})
    found = own(api("GET", f"repos/{repo}/pulls?{query}", None), repo, branch)
    if len(found) > 1:
        raise Refused(f"{len(found)} pull requests are open on {branch}: "
                      f"{', '.join('#' + str(p['number']) for p in found)}; nothing was edited")
    if found:
        pull = found[0]
        wrong = wrong_with(pull, author, head)
        if wrong:
            raise Refused(f"{wrong}; nothing was edited")
        api("PATCH", f"repos/{repo}/pulls/{pull['number']}", {"title": title, "body": body})
        print(f"::notice::#{pull['number']} retitled and its body replaced, at {head}", file=sys.stderr)
        return pull
    pull = api("POST", f"repos/{repo}/pulls", {"title": title, "head": branch, "base": BASE, "body": body})
    wrong = wrong_with(pull, author, head)
    if wrong:
        raise Refused(f"the pull request just opened is not as asked: {wrong}; it is neither labelled nor armed")
    if labels:
        api("POST", f"repos/{repo}/issues/{pull['number']}/labels", {"labels": labels})
    print(f"::notice::opened #{pull['number']} from {branch}, at {head}", file=sys.stderr)
    return pull


def armed(pull: dict, head: str, auto_merge: bool, disarm: bool, api: Api) -> None:
    """Arm the pull request at `head`, or switch its arming off, where asked; else leave it."""
    if auto_merge:
        graphql(api, ARM, {"id": pull["node_id"], "method": MERGE_METHOD, "head": head})
        print(f"::notice::#{pull['number']} merges itself at {head} once its required checks pass",
              file=sys.stderr)
    elif disarm and pull.get("auto_merge"):
        graphql(api, DISARM, {"id": pull["node_id"]})
        print(f"::notice::#{pull['number']} no longer merges itself: its change wants reading",
              file=sys.stderr)


def rolled(repo: str, branch: str, head: str, author: str, title: str, body: str,
           labels: list[str], auto_merge: bool, api: Api, disarm: bool = False) -> int:
    """Open or edit the bump's pull request, arm or disarm it where asked, and return its number."""
    the_bumps_commit(repo, branch, head, author, api)
    pull = edited_or_opened(repo, branch, head, author, title, body, labels, api)
    armed(pull, head, auto_merge, disarm, api)
    return pull["number"]


def malformed(args: argparse.Namespace) -> str | None:
    """What is wrong with the arguments, or None."""
    if not SLUG.match(args.repo):
        return f"--repo {args.repo!r} is not owner/name"
    if not BRANCH.match(args.branch) or args.branch == BASE:
        return f"--branch {args.branch!r} is not a bump's branch"
    if not COMMIT.match(args.head):
        return f"--head {args.head!r} is not a commit"
    if not args.author.strip():
        return "--author is empty, so nobody's pull request could be the bump's"
    if not args.title.strip():
        return "--title is empty"
    if args.auto_merge and args.disarm:
        return "--auto-merge and --disarm ask for opposite things"
    return None


def main(argv: list[str] | None = None, api: Api = gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--head", required=True, help="the commit the bump has just put on the branch")
    parser.add_argument("--author", required=True, help="the login the bump's pull request is opened by")
    parser.add_argument("--title", required=True)
    parser.add_argument("--labels", default="", help="comma-separated, given to a pull request this opens")
    parser.add_argument("--auto-merge", action="store_true", help="arm it to merge itself at --head")
    parser.add_argument("--disarm", action="store_true", help="switch off the arming it already carries")
    args = parser.parse_args(argv)

    wrong = malformed(args)
    if wrong:
        print(f"::error::{wrong}", file=sys.stderr)
        return 2
    try:
        body = sys.stdin.read()
        number = rolled(args.repo, args.branch, args.head, args.author, args.title, body,
                        [label.strip() for label in args.labels.split(",") if label.strip()], args.auto_merge, api,
                        disarm=args.disarm)
    except Refused as refused:
        print(f"::error::{refused}.", file=sys.stderr)
        return 1
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, KeyError, TypeError) as broken:
        detail = getattr(broken, "stderr", "") or broken
        print(f"::error::The forge could not be read or written, so the pull request was left as it was: {detail}",
              file=sys.stderr)
        return 2
    print(number)
    return 0


if __name__ == "__main__":
    sys.exit(main())
