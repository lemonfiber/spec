#!/usr/bin/env python3
"""Enforce conventional-commit subjects on PR commits (OPS-R11), so the
generated changelog stays clean. Usage: commit_lint.py <base_sha> <head_sha>

Two halves, split so the second can be tested without a repository. `_read`
shells out to git; `unconventional` is handed what git said and decides. What is
worth holding is which subjects the changelog generator can read and which it
cannot, and building real commits to reach that would be testing git as much as
this.
"""
import re
import subprocess
import sys

# Kept here rather than shared. The line below is a validation, and a scanner
# that cannot see it reports the call it guards as unguarded — which it did.
# A guard worth having is worth keeping where the thing it guards can see it.
_REF = re.compile(r"\A[0-9A-Za-z._/-]{1,255}\Z")

TYPES = "feat|fix|docs|refactor|test|chore|ci|perf|build|style|revert"

# A type, an optional scope, an optional `!` for a breaking change, then a colon,
# a space, and something. The something is what the changelog prints, so a
# subject that is only a type is refused along with one that is not a type at all.
SUBJECT = re.compile(rf"^(?:{TYPES})(?:\([a-z0-9.\-]+\))?!?: .+")

# One record per commit, the sha and the subject NUL-separated. A subject holds
# no newline, so a line is a commit here in a way it is not in `dco_check.py`.
FORMAT = "%H%x00%s"


def unconventional(out: str) -> list[str]:
    """Every commit in what git said whose subject the changelog cannot read.

    A merge and a revert are written by git, in git's words, and rewriting them
    to pass would be editing what git recorded about what happened.
    """
    bad = []
    for line in filter(None, out.splitlines()):
        sha, _, subject = line.partition("\x00")
        if subject.startswith(("Merge ", "Revert ")):
            continue
        if not SUBJECT.match(subject):
            bad.append(f"{sha[:8]} {subject}")
    return bad


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
        print("::error::commit_lint: base and head must be valid git refs")
        return 1

    bad = unconventional(_read(base, head))

    if bad:
        print("::error::commit subjects must be conventional (type: subject):")
        for subject in bad:
            print(f"  {subject}")
        print(f"\n  types: {TYPES.replace('|', ', ')}")
        print("  e.g.  feat: health-gate service startup")
        return 1
    print("commit-lint: all subjects conventional")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
