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
import re
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

# Branch protection is not only a list of checks, and the rest of it blocks just
# as hard while appearing in no check list at all.
#
# Each entry maps a protection setting to the question that decides whether it is
# what is holding this pull request, and to the sentence a maintainer can act on.
# `required_signatures` is here because it is the trap that costs the most time:
# an unsigned commit blocks a pull request with every check green and nothing
# anywhere naming the cause.
RULES = (
    (
        "strict",
        "behind",
        "the branch must be up to date with its base — rebase it and push",
    ),
    (
        "signatures",
        "unsigned",
        "every commit must be signed — re-sign and force-push",
    ),
    (
        "conversation",
        "unresolved",
        "every review conversation must be resolved",
    ),
    (
        "reviews",
        "unapproved",
        "an approving review is required",
    ),
)


# How loudly each state speaks, for deciding which of two reports under one name
# is the one to show. Built once: it never changes, and a dict comprehension per
# call was doing the same work for every check on every pull request.
RANK = {
    **dict.fromkeys(FAILED, 0),
    **dict.fromkeys(WAITING, 1),
    **dict.fromkeys(QUIET, 2),
}


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


def unmet(protection: dict[str, bool], state: dict[str, bool]) -> list[str]:
    """The protection rules holding this pull request that are not checks.

    `protection` says which rules the branch turns on; `state` says which of the
    corresponding conditions this pull request is currently failing. A rule that
    is off, or on and satisfied, is not returned.

    Separate from `blocking` because these are a different kind of answer: a
    failing check has a log, and none of these has anything at all. Reporting
    "every required context is satisfied" while one of them holds the merge is
    the same wrong answer GitHub's own merge box gives.
    """
    return [
        said
        for setting, condition, said in RULES
        if protection.get(setting) and state.get(condition)
    ]


def why_nothing_ran(found: dict[str, list[str]], conclusions: list[str]) -> str | None:
    """Where every required check is missing, the reason they all are.

    Twenty contexts reported as missing, one line each, is twenty statements of
    one fact — and the fact is not about the contexts. Nothing ran. What is worth
    saying is why, and `startup_failure` is the answer that has no other symptom:
    a workflow that could not start produces no check run, no log, and no entry on
    the pull request. On 2026-09-13 every workflow on three branches failed to
    start inside one minute, and each pull request read as twenty missing checks.

    Only where *everything* is missing. A single missing context among reported
    ones is a different question — a `paths:` filter, a failed `needs:` — and this
    would be the wrong answer to it.
    """
    if not found["missing"] or any(found[key] for key in ORDER if key != "missing"):
        return None
    if "startup_failure" in conclusions:
        return (
            "no required check reported because the workflows did not start "
            "(startup_failure). A run that fails to start leaves no check, no log "
            "and nothing on the pull request. Re-running is usually refused; push "
            "the branch again"
        )
    if not conclusions:
        return "no required check reported, and no workflow run exists for this branch at all"
    return "no required check reported yet; the runs that exist have not produced them"


def verdict(found: dict[str, list[str]], rules: list[str] | None = None) -> str:
    """One line saying whether anything is wrong, and where to look if so."""
    if found["missing"]:
        return (
            "blocked on a check that never reported, which appears nowhere in the "
            "pull request's own check list"
        )
    if found["failing"]:
        return "blocked on a check that failed; its log is on the pull request"
    if rules:
        return "every required context is satisfied; a branch protection rule holds it"
    if found["waiting"]:
        return "nothing is wrong; checks are still running"
    return "every required context is satisfied"


def lines(
    repo: str,
    number: int,
    found: dict[str, list[str]],
    rules: list[str] | None = None,
    nothing_ran: str | None = None,
) -> list[str]:
    """The report, worst first, with the empty categories left out."""
    if nothing_ran:
        out = [f"{repo}#{number}: {nothing_ran}"]
        out.extend(f"  {'RULE':>8}: {said}" for said in rules or [])
        out.append(f"  {'missing':>8}: {len(found['missing'])} required contexts, all of them")
        return out
    out = [f"{repo}#{number}: {verdict(found, rules)}"]
    for key in ORDER:
        if key == "passed" or not found[key]:
            continue
        for context in found[key]:
            out.append(f"  {key.upper():>8}: {context}")
    for said in rules or []:
        out.append(f"  {'RULE':>8}: {said}")
    passed = len(found["passed"])
    if passed:
        out.append(f"  {'passed':>8}: {passed}")
    return out


# What a repository and a branch are allowed to be called, checked before either
# reaches `gh`.
#
# Nothing here goes through a shell, so this is not shell injection — it is
# argument injection, which needs no shell. `gh` reads an argument beginning with
# `-` as an option, so a "repository" called `--template` is not a repository
# this fails to find; it is a flag, silently changing what the command does. The
# repository name arrives from the command line and is interpolated into an API
# path besides, where `..` would walk out of it.
#
# Refused rather than escaped. There is no legitimate repository or branch this
# turns away: GitHub allows neither a leading dash nor `..` in either.
_SAFE = re.compile(r"\A[0-9A-Za-z][0-9A-Za-z._/-]{0,254}\Z")
_NAME = re.compile(r"\A[0-9A-Za-z][0-9A-Za-z._-]{0,99}\Z")
_BRANCH = re.compile(r"\A[0-9A-Za-z][0-9A-Za-z._/-]{0,254}\Z")


def safe(value: str) -> str:
    """`value`, or a refusal — applied where it is put into a `gh` argument.

    `look` already turns away a repository or branch that is not one, with a
    sentence a reader can act on, and that is the right place for the message.
    It is the wrong place for the guarantee: it leaves every later caller of the
    helpers below to remember, and it leaves the check far enough from the
    `subprocess` call that a taint analyser cannot see the two connected —
    SonarCloud raised `S8705` here twice for exactly that reason, and was right
    to, because "some caller checks this" is not a property of this function.

    So the values are checked where they are used. Raised rather than returned
    empty: reaching here with an unchecked name is a mistake in this file, not a
    repository somebody cannot read, and the two should not look alike.
    """
    if not _SAFE.match(value):
        raise ValueError(f"refusing to pass {value!r} to gh: not a name or a number")
    return value


def named(repo: str) -> bool:
    """Whether `repo` is `owner/name` and both halves are what they claim."""
    owner, slash, name = repo.partition("/")
    return bool(slash) and bool(_NAME.match(owner)) and bool(_NAME.match(name))


def branched(base: str) -> bool:
    """Whether `base` is a branch name, and not a path walking out of one."""
    return bool(_BRANCH.match(base)) and ".." not in base


def _gh(*args: str) -> str:
    """What `gh` said, or an empty string where it would not answer.

    Empty rather than raised: a repository with no branch protection is a real
    answer to "what is required here", and so is a token that cannot read it.
    Both are reported by the caller as "nothing required", which is true of what
    this was able to see and is said plainly rather than implied.

    No shell, and never one: the arguments are passed as a list, and the two that
    come from outside this script are checked against `named` and `branched`
    before they arrive here.
    """
    done = subprocess.run(
        ("gh", *args), capture_output=True, text=True, check=False, timeout=60
    )
    return done.stdout if done.returncode == 0 else ""


def _protection_of(repo: str, base: str) -> dict:
    """The whole branch protection object for `base`, read once.

    Once, because the two questions asked of it — which contexts are required,
    and which of the other rules are on — are two reads of the same document.
    """
    said = _gh("api", f"repos/{safe(repo)}/branches/{safe(base)}/protection")
    return json.loads(said) if said.strip() else {}


def required_in(protection: dict) -> list[str]:
    """The contexts branch protection insists on."""
    return list((protection.get("required_status_checks") or {}).get("contexts") or [])


def rules_in(protection: dict) -> dict[str, bool]:
    """Which of the non-check rules are turned on."""
    checks = protection.get("required_status_checks") or {}
    reviews = protection.get("required_pull_request_reviews") or {}
    return {
        "strict": bool(checks.get("strict")),
        "signatures": bool((protection.get("required_signatures") or {}).get("enabled")),
        "conversation": bool(
            (protection.get("required_conversation_resolution") or {}).get("enabled")
        ),
        "reviews": (reviews.get("required_approving_review_count") or 0) > 0,
    }


# The `gh pr view --json` fields `_state` asks for. Named here so the suite can
# hand them back to `gh` and check it accepts them.
#
# It has to. `_gh` answers an unreadable repository with an empty string on
# purpose, so one bad repository does not end the run for the others — which
# means a field name `gh` rejects also comes back empty, and the rule it feeds
# silently never fires. `reviewThreads` was exactly that: a plausible name, not a
# real one, and every conversation-resolution block would have gone unreported
# with the script saying nothing was wrong.
FIELDS = ("mergeStateStatus", "reviewDecision")


def _state(repo: str, number: int) -> dict[str, bool]:
    """Which of those conditions this pull request is currently failing.

    `mergeStateStatus` answers "behind" directly. The rest are asked separately
    rather than inferred from `BLOCKED`, which is the single word this whole
    script exists because GitHub gives instead of a reason.
    """
    said = _gh("pr", "view", "-R", safe(repo), safe(str(number)), "--json", ",".join(FIELDS))
    if not said.strip():
        return {}
    pr = json.loads(said)
    return {
        "behind": pr.get("mergeStateStatus") == "BEHIND",
        "unsigned": bool(_unsigned(repo, number)),
        "unresolved": _unresolved(repo, number),
        "unapproved": pr.get("reviewDecision") not in ("APPROVED", None, ""),
    }


# Review threads and their resolution are not on `gh pr view`, only on GraphQL.
THREADS = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) { nodes { isResolved } }
    }
  }
}
"""


def _unresolved(repo: str, number: int) -> bool:
    """Whether any review conversation is still open."""
    owner, name = repo.split("/", 1)
    said = _gh(
        "api", "graphql",
        "-f", f"query={THREADS}",
        "-F", f"owner={safe(owner)}", "-F", f"repo={safe(name)}", "-F", f"number={safe(str(number))}",
        "--jq", "[.data.repository.pullRequest.reviewThreads.nodes[].isResolved]",
    )
    return any(not resolved for resolved in (json.loads(said) if said.strip() else []))


def _unsigned(repo: str, number: int) -> list[str]:
    """Commits on this pull request the forge has not verified a signature for."""
    said = _gh(
        "api",
        f"repos/{safe(repo)}/pulls/{safe(str(number))}/commits",
        "--jq",
        "[.[] | select(.commit.verification.verified | not) | .sha[0:8]]",
    )
    return json.loads(said) if said.strip() else []


def _reported(repo: str, number: int) -> dict[str, str]:
    """Every check the pull request has reported, by name.

    Where a name reports more than once — a re-run, or two workflows using one
    job name — the worst state wins. Reporting the pass and hiding the failure
    beside it is how this tool would become the thing it exists to catch.
    """
    said = _gh(
        "pr", "checks", "-R", safe(repo), safe(str(number)), "--json", "name,state"
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
    return RANK.get(state, 1) < RANK.get(than, 1)


def _conclusions(repo: str, branch: str) -> list[str]:
    """How this branch's recent workflow runs ended.

    Only asked when nothing reported, because that is the only case it answers.
    """
    said = _gh(
        "run", "list", "-R", safe(repo), "--branch", safe(branch), "--limit", "30",
        "--json", "conclusion", "--jq", "[.[].conclusion]",
    )
    return [c for c in (json.loads(said) if said.strip() else []) if c]


def _branch_of(repo: str, number: int) -> str:
    said = _gh(
        "pr", "view", "-R", safe(repo), safe(str(number)), "--json", "headRefName", "--jq", ".headRefName"
    )
    return said.strip()


def _open_prs(repo: str) -> list[int]:
    said = _gh("pr", "list", "-R", safe(repo), "--state", "open", "--json", "number")
    return [pr["number"] for pr in (json.loads(said) if said.strip() else [])]


def _repos(org: str) -> list[str]:
    said = _gh("repo", "list", safe(org), "--limit", "100", "--json", "nameWithOwner")
    return [r["nameWithOwner"] for r in (json.loads(said) if said.strip() else [])]


def _base(repo: str, number: int) -> str:
    said = _gh(
        "pr", "view", "-R", safe(repo), safe(str(number)), "--json", "baseRefName", "--jq", ".baseRefName"
    )
    return said.strip() or "main"


def look(repo: str, number: int) -> list[str]:
    """Read one pull request and report it."""
    if not named(repo):
        return [f"{repo}: not a repository name — expected owner/name"]
    base = _base(repo, number)
    if not branched(base):
        return [f"{repo}#{number}: base branch {base!r} is not a branch name"]
    protection = _protection_of(repo, base)
    required = required_in(protection)
    rules = unmet(rules_in(protection), _state(repo, number)) if protection else []
    if not required and not rules:
        return [f"{repo}#{number}: nothing required, or branch protection is unreadable here"]
    found = blocking(required, _reported(repo, number))
    nothing_ran = None
    if found["missing"] and not any(found[key] for key in ORDER if key != "missing"):
        branch = _branch_of(repo, number)
        if branched(branch):
            nothing_ran = why_nothing_ran(found, _conclusions(repo, branch))
    return lines(repo, number, found, rules, nothing_ran)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", help="owner/repo, or the owner when --org is given")
    parser.add_argument("numbers", nargs="*", type=int, help="pull requests; default all open")
    parser.add_argument("--org", action="store_true", help="read every repository in the org")
    args = parser.parse_args(argv)

    if args.org:
        if not _NAME.match(args.target):
            print(f"{args.target}: not an organisation name")
            return 1
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
