#!/usr/bin/env python3
"""Ask of a pull request's title and body what its squash commit will hold (GOV-R62).

A squash merge writes the pull request's title as the commit's subject and its
body as the commit's message, and the branch's own commit messages do not reach
`main`. So what `main`'s history is read for is asked of those two fields:

  1. the title is a conventional subject, as `commit_lint.py` holds a commit's
     (OPS-R21), because the changelog is written from `main`'s subjects;
  2. the body cites identifiers that resolve, on a `Spec:` line, read the way
     `spec_check.py` reads a trailer (GOV-R3, GOV-R47, GOV-R48), because
     `gate.py` reads `main`'s log to decide that a goal landed;
  3. the body carries a sign-off for each human author of the commits, the rule
     `dco_check.py` holds each commit to (GOV-R29).

A pull request a bot opened is exempt: nobody stands behind it to sign it off.

Usage:
  squash_message.py --spec-dir <spec checkout> --pull <pull.json> --commits <commits.jsonl>

`pull.json` is `{"title", "body", "bot"}` and `commits.jsonl` one
`{"name", "email", "parents"}` per commit. The workflow writes both from the
forge's API, so nothing of the pull request's code is read. What is missing is
printed as Markdown, the lines to add included.

Exit 0 = the squash will hold it, 1 = it will not, 2 = the check could not run.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from commit_lint import TYPES, conventional
from dco_check import SIGNED_OFF, is_bot
from spec_check import Refused, cited_ids, defined_ids, draft_ids, retired_ids, within_cwd

PASSED = "The squash commit will carry a conventional subject, a citation that resolves and each author's sign-off."


def title_problem(title: str) -> list[str]:
    """What is wrong with the title as `main`'s subject, if anything."""
    if conventional(title):
        return []
    return [(
        f"The title `{title}` is not a conventional subject. It becomes the commit's subject "
        f"on `main`. Start it with a type, `type: what it does` or `type(scope): what it does`, "
        f"where the type is one of {TYPES.replace('|', ', ')}."
    )]


def citation_problems(body: str, spec_dir: pathlib.Path) -> list[str]:
    """What is wrong with the body's citation, read against this spec."""
    defined = defined_ids(spec_dir)
    if not defined:
        raise Refused(2, "::error::no identifiers found in the spec checkout, so nothing can be resolved")
    cited = cited_ids(body)
    if not cited:
        return [(
            "The body has no `Spec:` line. Add one on its own line, naming what the change "
            "serves, e.g. `Spec: OPS-R1`; routine maintenance cites `GOV-R12`. It is the "
            "citation `main` keeps."
        )]
    retired = retired_ids(spec_dir)
    drafts = draft_ids(spec_dir)
    problems = []
    for rid in sorted(cited):
        if rid not in defined:
            problems.append(f"`{rid}` is not defined on `spec@main`.")
        elif rid in retired:
            problems.append(f"`{rid}` is retired: {retired[rid]}")
        elif rid in drafts:
            problems.append(f"`{rid}` is Draft ({drafts[rid]}) and cannot be cited until it is Accepted.")
    return problems


def missing_signoffs(body: str, commits: list[dict]) -> list[str]:
    """The sign-off line to add for each human author the body does not sign off."""
    signed = {email.lower() for email in SIGNED_OFF.findall(body)}
    lines: dict[str, str] = {}
    for commit in commits:
        name, email = commit["name"], commit["email"]
        if commit["parents"] > 1 or is_bot(name, email) or email.lower() in signed:
            continue
        lines.setdefault(email.lower(), f"Signed-off-by: {name} <{email}>")
    return list(lines.values())


def verdict(pull: dict, commits: list[dict], spec_dir: pathlib.Path) -> list[str]:
    """Every problem with the squash this pull request would make, in Markdown."""
    if pull["bot"]:
        return []
    body = pull["body"] or ""
    problems = title_problem(pull["title"]) + citation_problems(body, spec_dir)
    lines = missing_signoffs(body, commits)
    if lines:
        problems.append(
            "The body does not sign off for every author of the commits. Add, each on its own line:\n\n"
            "```\n" + "\n".join(lines) + "\n```"
        )
    return problems


def read(arg: str, what: str) -> str:
    """A file the workflow wrote beside the checkout."""
    path = within_cwd(arg, what)
    if not path.is_file():
        raise Refused(2, f"::error::{what} not found: {arg}")
    return path.read_text(encoding="utf-8")


def gate() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", required=True)
    ap.add_argument("--pull", required=True)
    ap.add_argument("--commits", required=True)
    a = ap.parse_args()
    spec_dir = pathlib.Path(a.spec_dir)
    if not spec_dir.is_dir():
        raise Refused(2, f"::error::spec dir not found: {spec_dir}")
    pull = json.loads(read(a.pull, "pull"))
    commits = [json.loads(line) for line in read(a.commits, "commits").splitlines() if line.strip()]
    problems = verdict(pull, commits, spec_dir)
    if not problems:
        print(PASSED)
        return 0
    print("The squash merge writes this pull request's title and body to `main` as one commit, "
          "and the branch's commit messages do not reach it. Edit the title or body; there is "
          "nothing to push, and this check runs again on the edit.\n")
    # A problem running to several lines stays inside its bullet.
    print("\n".join("- " + problem.replace("\n", "\n  ") for problem in problems))
    return 1


def main() -> int:
    try:
        return gate()
    except Refused as refused:
        print(refused)
        return refused.code


if __name__ == "__main__":
    sys.exit(main())
