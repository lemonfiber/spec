#!/usr/bin/env python3
"""A check that runs on a pull request and is not required is a defect — Q-R68.

Branch protection is the only thing that can refuse a merge. A check that runs
and is not a required context cannot: it goes red, it is read as a verdict, and
the merge happens anyway. Eight pull requests merged red in one afternoon that
way, and the estate could not tell, because nothing anywhere compares what runs
against what blocks.

This does. For every repository in the organisation it reads the required
contexts and the check names recent pull requests actually produced, and refuses
a name that ran, does not block, and is not in the register beside this file.

**It is the register, not this file, that carries the judgement.** Which jobs
report rather than judge is a decision somebody made about a workflow, and it
belongs where a maintainer can read the reason. What belongs here is the
arithmetic, and the refusal when a register entry stops being true: an exemption
matching nothing is a mute wearing a register's clothes.

Four ways to answer about nothing, all refused:

- no repository was listed, so no protection was read;
- a repository's protection could not be read, which is not a repository with
  nothing unrequired;
- a repository produced no check names at all, so what runs there is unknown
  rather than covered;
- an exemption matched no check anywhere, so it is holding open a door that is
  no longer there.

Run:  python3 scripts/check_required.py
      python3 scripts/check_required.py --repo lemonfiber/spec
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTER = ROOT / "70-operations" / "required-checks.toml"

# How many recent pull requests each repository is asked about. Enough that a
# path-filtered workflow which ran on one of them is seen, few enough that the
# answer is about the repository as it is now.
SAMPLED = 6


class Unanswerable(Exception):
    """The question could not be asked. Never the same as a clean answer."""


def register(path: pathlib.Path = REGISTER) -> tuple[list[dict], list[dict]]:
    """The exempt names and prefixes, each with the reason it is there."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as gone:
        raise Unanswerable(
            f"{path} is not here, so every check in the organisation would be "
            "read as unexempt and this check would refuse all of them"
        ) from gone

    entries = data.get("exempt", [])
    if not entries:
        raise Unanswerable(
            f"{path} exempts nothing, so either every notification job in the "
            "organisation is now required or this register has been emptied"
        )

    names, prefixes = [], []
    for entry in entries:
        if not entry.get("why"):
            raise Unanswerable(
                f"an exemption for {entry.get('name') or entry.get('prefix')!r} "
                "carries no reason. An exemption without one cannot be reviewed, "
                "which is how a mute outlives the thing it was for"
            )
        if "name" in entry:
            names.append(entry)
        elif "prefix" in entry:
            prefixes.append(entry)
        else:
            raise Unanswerable(
                f"an exemption in {path} names neither a check nor a prefix"
            )
    return names, prefixes


def _gh(*args: str) -> str:
    done = subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        raise Unanswerable(f"`gh {' '.join(args)}` failed: {done.stderr.strip()}")
    return done.stdout


def repositories(owner: str) -> list[str]:
    """Every repository in the organisation, read live rather than from a list.

    A registry would answer about the repositories somebody remembered to add,
    and a repository nothing surveys is exactly the one this check exists for.
    """
    raw = _gh(
        "api", "--paginate", f"orgs/{owner}/repos?per_page=100",
        "--jq", ".[] | select(.archived | not) | .name",
    )
    names = [line.strip() for line in raw.splitlines() if line.strip()]
    if not names:
        raise Unanswerable(
            f"no repository was listed for {owner}, so no protection was read "
            "and this run says nothing about any of them"
        )
    return sorted(names)


def required_in(repo: str) -> set[str]:
    """The contexts branch protection will refuse a merge over."""
    raw = _gh("api", f"repos/{repo}/branches/main/protection/required_status_checks")
    return {c["context"] for c in json.loads(raw).get("checks", [])}


def observed_in(repo: str, sampled: int = SAMPLED) -> set[str]:
    """Every check name recent pull requests in `repo` produced."""
    raw = _gh(
        "pr", "list", "-R", repo, "--state", "all", "--limit", str(sampled),
        "--json", "statusCheckRollup",
    )
    names: set[str] = set()
    for pull in json.loads(raw):
        for run in pull.get("statusCheckRollup") or []:
            name = run.get("name") or run.get("context")
            if name:
                names.add(name)
    if not names:
        raise Unanswerable(
            f"{repo} produced no check name on any of its last {sampled} pull "
            "requests, so what runs there is unknown rather than covered"
        )
    return names


def exempt(name: str, names: list[dict], prefixes: list[dict]) -> dict | None:
    """The register entry covering `name`, or None."""
    for entry in names:
        if entry["name"] == name:
            return entry
    for entry in prefixes:
        if name.startswith(entry["prefix"]):
            return entry
    return None


def refusal(repo: str, unrequired: list[str]) -> str:
    """What one repository's unrequired checks say."""
    return "\n".join(
        [
            (
                f"{repo}: {len(unrequired)} check(s) run on a pull request and "
                "cannot refuse one."
            ),
            *(f"    {name}" for name in unrequired),
            "",
            (
                "  A check that runs and is not a required context goes red, is "
                "read as a verdict, and the merge happens anyway."
            ),
            "",
            (
                "  Either add each to this repository's required contexts, or "
                f"name it in {REGISTER.relative_to(ROOT)} with the reason it "
                "reports rather than judges."
            ),
            "",
            (
                "  Do not name a leg of a run-time matrix: the set of names "
                "moves, and a rule holding one silently stops covering anything."
            ),
        ]
    )


def look(owner: str, only: str | None, out) -> int:
    names, prefixes = register()
    matched: set[int] = set()
    refused = 0
    looked = 0

    repos = [only.split("/", 1)[1]] if only else repositories(owner)

    for name in repos:
        repo = f"{owner}/{name}"
        required = required_in(repo)
        observed = observed_in(repo)
        looked += 1

        unrequired = []
        for check in sorted(observed):
            if check in required:
                continue
            entry = exempt(check, names, prefixes)
            if entry is None:
                unrequired.append(check)
            else:
                matched.add(id(entry))

        if unrequired:
            print(refusal(repo, unrequired), file=out)
            print(file=out)
            refused += 1

    unused = [
        entry.get("name") or entry.get("prefix")
        for entry in (*names, *prefixes)
        if id(entry) not in matched
    ]
    if unused:
        print(
            "these exemptions matched no check in any repository: "
            + ", ".join(sorted(unused))
            + f".\n  An exemption is a claim that a check exists and reports "
            "rather than judges. One that matches nothing holds a door open that "
            f"is no longer there — take it out of "
            f"{REGISTER.relative_to(ROOT)}, or find out why the check stopped "
            "running.",
            file=out,
        )
        refused += 1

    if refused:
        return 1

    print(
        f"every check running in {looked} repositories is required or registered",
        file=out,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default="lemonfiber")
    parser.add_argument("--repo", default=None, help="one repository, as owner/name")
    args = parser.parse_args(argv)

    try:
        return look(args.owner, args.repo, sys.stderr)
    except Unanswerable as why:
        print(f"::error::{why}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
