#!/usr/bin/env python3
"""Say what a `BLOCKED` pull request is blocked on, including what never reported.

Usage: what_is_blocking.py <owner/repo> [<number> ...]
       what_is_blocking.py --org <owner>

GitHub will tell you a pull request is blocked. It will not reliably tell you by
what. A required check that failed is on the page with a link to its log; a
required check that *never reported* is on no page at all — the merge box says
"Required statuses must pass" and the check list simply does not mention it.
There is nothing to click, because nothing ran.

That is not a corner case. A workflow with a `paths:` filter that does not match,
a job whose `needs:` dependency failed, a reusable workflow the caller granted
too few permissions to, a third-party app having an outage: all four block a pull
request forever and all four look identical, which is to say they look like
nothing at all. On 2026-09-13 every open pull request in this organisation sat on
a missing `SonarCloud Code Analysis` and a missing `gate / gate`, and finding
that out took reading branch protection and the check list side by side by hand.

So that is what this does. It reads the contexts branch protection requires and
the checks the pull request reported, and names the difference. Two halves, split
the way `dco_check.py` splits: `_read` shells out to `gh`, `blocking` is handed
what `gh` said and decides. The decisions are the part worth testing, and a suite
that had to stand up a repository and a branch protection rule to reach them
would be testing GitHub.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

# What a reported check's state means for the merge.
#
# `SKIPPED` and `NEUTRAL` are deliberately neither: GitHub does not treat them as
# failures, and this does not claim they are passes. A skipped required check is
# worth a maintainer's eye — it is how a gate goes quiet without going red — so it
# is named rather than folded into either column.
PASSED = frozenset({"SUCCESS"})
FAILED = frozenset({"FAILURE", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"})
WAITING = frozenset({"PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "REQUESTED"})
QUIET = frozenset({"SKIPPED", "NEUTRAL", "CANCELLED", "STALE"})

# The order findings are printed in, worst first. `missing` leads because it is
# the one with nowhere to look.
ORDER = ("missing", "failing", "quiet", "waiting", "passed")


def blocking(required: list[str], reported: dict[str, str]) -> dict[str, list[str]]:
    """Sort every required context by what it is doing.

    `required` is what branch protection insists on; `reported` maps a check name
    to its state. A context in the first and not the second is `missing` — the
    whole reason this exists. A check that reported and is not required is not
    this function's business: it cannot block the merge, so it is not returned.

    An unrecognised state counts as `waiting` rather than as a pass. A new state
    GitHub adds should read as "not finished" until somebody looks, because the
    alternative is a gate that quietly widens every time the forge does.
    """
    found: dict[str, list[str]] = {key: [] for key in ORDER}
    for context in required:
        state = reported.get(context)
        if state is None:
            found["missing"].append(context)
        elif state in PASSED:
            found["passed"].append(context)
        elif state in FAILED:
            found["failing"].append(context)
        elif state in QUIET:
            found["quiet"].append(context)
        else:
            found["waiting"].append(context)
    return found


def verdict(found: dict[str, list[str]]) -> str:
    """One line saying whether anything is wrong, and where to look if so."""
    if found["missing"]:
        return (
            "blocked on a check that never reported, which appears nowhere in the "
            "pull request's own check list"
        )
    if found["failing"]:
        return "blocked on a check that failed; its log is on the pull request"
    if found["waiting"]:
        return "nothing is wrong; checks are still running"
    return "every required context is satisfied"


def lines(repo: str, number: int, found: dict[str, list[str]]) -> list[str]:
    """The report, worst first, with the empty categories left out."""
    out = [f"{repo}#{number}: {verdict(found)}"]
    for key in ORDER:
        if key == "passed" or not found[key]:
            continue
        for context in found[key]:
            out.append(f"  {key.upper():>8}: {context}")
    passed = len(found["passed"])
    if passed:
        out.append(f"  {'passed':>8}: {passed}")
    return out


def _gh(*args: str) -> str:
    """What `gh` said, or an empty string where it would not answer.

    Empty rather than raised: a repository with no branch protection is a real
    answer to "what is required here", and so is a token that cannot read it.
    Both are reported by the caller as "nothing required", which is true of what
    this was able to see and is said plainly rather than implied.
    """
    done = subprocess.run(
        ("gh", *args), capture_output=True, text=True, check=False, timeout=60
    )
    return done.stdout if done.returncode == 0 else ""


def _required(repo: str, base: str) -> list[str]:
    """The contexts branch protection insists on for `base`."""
    said = _gh(
        "api",
        f"repos/{repo}/branches/{base}/protection",
        "--jq",
        "[.required_status_checks.contexts[]?]",
    )
    return json.loads(said) if said.strip() else []


def _reported(repo: str, number: int) -> dict[str, str]:
    """Every check the pull request has reported, by name.

    Where a name reports more than once — a re-run, or two workflows using one
    job name — the worst state wins. Reporting the pass and hiding the failure
    beside it is how this tool would become the thing it exists to catch.
    """
    said = _gh(
        "pr", "checks", "-R", repo, str(number), "--json", "name,state"
    )
    checks: dict[str, str] = {}
    for check in json.loads(said) if said.strip() else []:
        name, state = check["name"], check["state"]
        seen = checks.get(name)
        if seen is None or _worse(state, seen):
            checks[name] = state
    return checks


def _worse(state: str, than: str) -> bool:
    """Whether `state` is the one a maintainer needs to hear about."""
    rank = {**{s: 0 for s in FAILED}, **{s: 1 for s in WAITING}, **{s: 2 for s in QUIET}}
    return rank.get(state, 1) < rank.get(than, 1)


def _open_prs(repo: str) -> list[int]:
    said = _gh("pr", "list", "-R", repo, "--state", "open", "--json", "number")
    return [pr["number"] for pr in (json.loads(said) if said.strip() else [])]


def _repos(org: str) -> list[str]:
    said = _gh("repo", "list", org, "--limit", "100", "--json", "nameWithOwner")
    return [r["nameWithOwner"] for r in (json.loads(said) if said.strip() else [])]


def _base(repo: str, number: int) -> str:
    said = _gh(
        "pr", "view", "-R", repo, str(number), "--json", "baseRefName", "--jq", ".baseRefName"
    )
    return said.strip() or "main"


def look(repo: str, number: int) -> list[str]:
    """Read one pull request and report it."""
    required = _required(repo, _base(repo, number))
    if not required:
        return [f"{repo}#{number}: nothing required, or branch protection is unreadable here"]
    return lines(repo, number, blocking(required, _reported(repo, number)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", help="owner/repo, or the owner when --org is given")
    parser.add_argument("numbers", nargs="*", type=int, help="pull requests; default all open")
    parser.add_argument("--org", action="store_true", help="read every repository in the org")
    args = parser.parse_args(argv)

    if args.org:
        pairs = [(repo, n) for repo in _repos(args.target) for n in _open_prs(repo)]
    elif args.numbers:
        pairs = [(args.target, n) for n in args.numbers]
    else:
        pairs = [(args.target, n) for n in _open_prs(args.target)]

    for repo, number in pairs:
        print("\n".join(look(repo, number)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
