#!/usr/bin/env python3
"""Verify every commit in base..head carries a Signed-off-by matching its author.

Implements GOV-R29/GOV-R30. Usage: dco_check.py <base_sha> <head_sha>

Two halves, split so the second can be tested without a repository. `_read`
shells out to git; `unsigned` is handed what git said and decides. The decisions
are where the subtlety is — whose sign-off counts, who is exempt and why — and a
suite that had to build real commits to reach them would test git as much as
this.
"""
import re
import subprocess
import sys

# Kept here rather than shared. The line below is a validation, and a scanner
# that cannot see it reports the call it guards as unguarded — which it did.
# A guard worth having is worth keeping where the thing it guards can see it.
_REF = re.compile(r"\A[0-9A-Za-z._/-]{1,255}\Z")

# One record per commit, fields NUL-separated and records ending in \x01, so a
# body containing newlines — which every body does — cannot be mistaken for the
# end of a commit.
FORMAT = "%H%x00%an%x00%ae%x00%P%x00%b%x01"

SIGNED_OFF = re.compile(r"^Signed-off-by:[^<]*<([^>]+)>\s*$", re.MULTILINE)


def is_bot(name: str, email: str) -> bool:
    """Whether this commit was authored by something with nobody behind it."""
    return name.endswith("[bot]") or "[bot]@" in email or email == "noreply@github.com"


def unsigned(out: str) -> list[str]:
    """Every commit in what git said that carries no sign-off of its author's.

    Merge commits (more than one parent) and bot-authored commits carry no
    sign-off by design — GitHub authors them (branch updates, auto-merges), so
    there is no human to attest. Exempt both rather than block on the
    unattestable.

    The match is on the email and is case-insensitive, because an address is and
    a name is not: two people share a name and nobody shares an inbox.
    """
    problems = []
    for rec in filter(None, out.split("\x01\n")):
        parts = rec.strip("\x01\n").split("\x00")
        if len(parts) < 5:
            continue
        sha, an, ae, parents, body = parts[0], parts[1], parts[2], parts[3], parts[4]
        if " " in parents.strip() or is_bot(an, ae):
            continue
        signoffs = SIGNED_OFF.findall(body)
        if not any(email.lower() == ae.lower() for email in signoffs):
            problems.append(f"{sha[:8]} by {an} <{ae}> lacks a matching Signed-off-by")
    return problems


def _read(base: str, head: str) -> str:
    """What git says about the commits between these two."""
    return subprocess.run(
        ["git", "log", f"--format={FORMAT}", f"{base}..{head}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def main(argv: list[str]) -> int:
    base, head = argv[1], argv[2]
    if not (_REF.match(base) and _REF.match(head)):
        print("::error::dco_check: base and head must be valid git refs")
        return 1

    problems = unsigned(_read(base, head))

    if problems:
        print("::error::DCO sign-off missing:")
        for problem in problems:
            print(f"  {problem}")
        print("\nAdd it with: git commit -s   (see spec 50-governance/dco.md)")
        return 1
    print("DCO: all commits signed off")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
