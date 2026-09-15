#!/usr/bin/env python3
"""Governance gate: verify a PR cites spec identifiers that actually exist.

Canonical here in the spec repo; every implementation repo runs it via the
reusable workflow (.github/workflows/spec-check.yml). See 50-governance/.

Enforces:
  GOV-R2  a citation is present
  GOV-R3  every cited identifier exists on spec@main

`--citation-optional` drops the first of those and keeps the second. It is for
the one event that carries no pull request to read a citation from; see the
comment over the flag.

One author cannot write a trailer, and the gate cites on its behalf: see
`by_dependabot` below (Q-R55).

Ordering (GOV-R4) — that a behavioural change's spec PR merged first — is not
machine-checked here yet; it is verified in review. Hardening this is tracked in
the spec repo, and any change to this script cites GOV-R11.

Usage:
  spec_check.py --spec-dir <path to spec checkout> --text-file <PR body+commits>
                [--pr-author <login of whoever opened the pull request>]
                [--citation-optional]
Exit 0 = pass, 1 = fail (with guidance), 2 = usage error.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from patterns import ADR_FILE, CITE_ANY, REQ_DEF, REQ_DEF_ROW, SPEC_TRAILER


# Identifiers the spec defines.
def defined_ids(spec_dir: pathlib.Path) -> set[str]:
    ids: set[str] = set()
    for p in spec_dir.rglob("*.md"):
        if ".git" in p.parts:
            continue
        ids.update(REQ_DEF.findall(p.read_text(encoding="utf-8", errors="ignore")))
    dec = spec_dir / "00-overview" / "decisions"
    if dec.is_dir():
        for f in dec.iterdir():
            m = ADR_FILE.match(f.name)
            if m:
                ids.add(f"ADR-{int(m.group(1)):04d}")
    return ids


# A requirement whose row says it is gone, against what its row says about where.
RETIRED = ("*Withdrawn", "*Superseded")


def retired_ids(spec_dir: pathlib.Path) -> dict[str, str]:
    """Identifiers the spec still defines and no longer offers, against why.

    `defined_ids` finds these, because a withdrawal is recorded **in place** — the
    row stays so the number is visibly retired rather than missing, which is what
    stops it being reused. That is the right shape for the spec and the wrong
    answer for a citation: `GOV-R8` retires the number permanently, and the status
    vocabulary says a Superseded one is not citable for new work.

    So the gate has to tell the two apart, and the row already says which it is
    and where the work went. Carrying that sentence into the refusal is the whole
    value: an author who cited `F3-R20` is told it moved to `F8-R12`, rather than
    being told a number that plainly exists does not.
    """
    found: dict[str, str] = {}
    for p in spec_dir.rglob("*.md"):
        if ".git" in p.parts:
            continue
        for rid, cell in REQ_DEF_ROW.findall(p.read_text(encoding="utf-8", errors="ignore")):
            if cell.strip().startswith(RETIRED):
                found[rid] = " ".join(cell.split())
    return found


def cited_ids(text: str) -> set[str]:
    ids: set[str] = set()
    for line in SPEC_TRAILER.findall(text):
        ids.update(CITE_ANY.findall(line))
    return ids


# The account whose pull requests carry no trailer, and the identifier the gate
# writes for them. Dependabot composes its own commit message and pull request
# body and offers no way to add a line to either, so its pull requests cite
# nothing. GOV-R12 is the identifier that governs a dependency update, and the
# gate supplies it here rather than in the text (Q-R55, ADR-0016).
#
# Supplied, not skipped: GOV-R3 still runs, so GOV-R12 must exist on spec@main
# and the run still prints what it accepted.
#
# The trap, for whoever edits this next: this keys on GitHub's record of who
# opened the pull request, and on nothing else. A label, a title, a branch name
# and a commit's author are all writable by whoever opened the pull request;
# `pull_request.user.login` is not. Widening this to any of them turns the gate
# off for anyone who can type.
DEPENDABOT = "dependabot[bot]"
ROUTINE = "GOV-R12"


def by_dependabot(pr_author: str) -> bool:
    """Whether GitHub says Dependabot opened this pull request."""
    return pr_author == DEPENDABOT


# The event that carries no pull request, and what this gate can still ask of it.
#
# A merge queue tests a batch on a branch of its own — the default branch's tip
# with every queued pull request applied — and the event asking for those checks
# carries no pull request at all: no body, no author, nothing to close. Two of
# the three things GOV-R2 reads are therefore missing, and demanding a trailer
# of what is left would refuse two changes that are not at fault: one whose
# citation sits in its pull request body, which is where GOV-R2 allows it, and
# any batch of Dependabot's, whose allowance keys on an author the event does
# not carry.
#
# So presence stops being required there, and GOV-R3 does not: every identifier
# the batch's commits do cite is still resolved against the spec. That is the
# half of the rule a queue can change — a pull request can wait in one while the
# identifier it cited is withdrawn — and the half GOV-R2 covers was settled
# before the queue accepted it, because a pull request cannot be queued until
# this gate has passed on it.
#
# The trap, for whoever edits this next: what selects this is the *event*, which
# the workflow reads from GitHub's own payload. Nothing a contributor writes can
# reach it. Wire it to a label, a title or a branch name instead and the
# citation rule becomes optional for anyone who can type.
NOTHING_CITED = (
    "spec-check: OK — nothing cited, and presence is not asked on this event. "
    "GOV-R2 was asked of every pull request in this batch before the queue took it."
)


GUIDANCE = """
This change does not cite a spec identifier that exists on spec@main.

The lemonfiber spec is canonical: every change references something already in
https://github.com/lemonfiber/spec

Add a `Spec:` trailer to a commit AND the PR body, for example:

    Spec: B2-R1

  - Implementing something specified?  Cite the requirement.
  - Changing behaviour?  Open a spec PR first, then cite the new ID.
  - Routine maintenance (deps, formatting, CI)?  Cite GOV-R12.

Guide: https://github.com/lemonfiber/spec/blob/main/50-governance/contributing.md
"""


RETIRED_GUIDANCE = """
A retired identifier still appears in the spec, and that is deliberate: the row
stays so the number is visibly gone rather than missing, which is what stops it
being reused. It is not something to build against.

Cite the identifier the row names in its place. Where it names none, the work it
described is gone rather than moved, and what you are doing needs a requirement
that exists.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", required=True)
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--pr-author", default="", help="login that opened the PR")
    ap.add_argument(
        "--citation-optional",
        action="store_true",
        help="citing nothing is not a refusal; GOV-R3 still runs on what is cited",
    )
    a = ap.parse_args()

    spec_dir = pathlib.Path(a.spec_dir)
    if not spec_dir.is_dir():
        print(f"::error::spec dir not found: {spec_dir}")
        return 2

    cwd = pathlib.Path.cwd().resolve()
    text_path = pathlib.Path(a.text_file).resolve()
    if not text_path.is_relative_to(cwd):
        print("::error::text-file must be within the working directory")
        return 2
    text = text_path.read_text(encoding="utf-8", errors="ignore")
    defined = defined_ids(spec_dir)
    if not defined:
        print("::error::no identifiers found in spec checkout — cannot verify")
        return 2

    cited = cited_ids(text)
    if by_dependabot(a.pr_author):
        cited.add(ROUTINE)
    if not cited:
        if a.citation_optional:
            print(NOTHING_CITED)
            return 0
        print("::error::no `Spec:` citation found")
        print(GUIDANCE)
        return 1

    unknown = sorted(i for i in cited if i not in defined)
    if unknown:
        print(f"::error::cited identifiers do not exist on spec@main: {', '.join(unknown)}")
        print(GUIDANCE)
        return 1

    retired = retired_ids(spec_dir)
    gone = sorted(i for i in cited if i in retired)
    if gone:
        for rid in gone:
            print(f"::error::{rid} is retired: {retired[rid]}")
        print(RETIRED_GUIDANCE)
        return 1

    print(f"spec-check: OK — cites {', '.join(sorted(cited))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
