#!/usr/bin/env python3
"""A pin on a shared workflow says how far behind it is — Q-R68.

Every repository that runs one of this repository's reusable workflows pins it
to an exact commit. Q-R68 has a check fail a pull request where such a pin is
behind, naming the commits it has not taken.

**What is pinned and what is not.** The workflow file is pinned; the scripts it
runs are not. Every one of these workflows checks this repository out at `main`
and runs the script from there, so a change to `spec_check.py` reaches every
consumer on their next run. What a stale pin holds back is the *workflow* — the
arguments it passes, the steps it adds — and so a pin is measured against the
history of the one file it names. Measured against the default branch instead,
every pin in the organisation is behind for most of every day, and a check that
is always red is a check that stops being required.

**Dependabot needs a version to compare.** Its `github-actions` updater proposes
a bump when a newer tag exists; a pin whose trailing comment names no tag gives
it nothing to be newer than. `publish-pin-tag.yml` cuts the tag that makes the
comparison possible, and the comment beside each pin is what carries it.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

# `uses: lemonfiber/spec/.github/workflows/<name>.yml@<sha>`, with whatever
# comment follows. Only this repository's workflows: a pin on somebody else's
# action is Dependabot's business and it can do that one.
PIN = re.compile(
    r"uses:\s*lemonfiber/spec/\.github/workflows/(?P<workflow>[\w.-]+\.yml)@(?P<sha>[0-9a-f]{40})"
)

# A commit, as a revision this hands to `git`: forty hex characters and the whole
# of the string.
#
# Nothing today can reach `git` failing it — the pattern above matches only such
# a string, and `rev-parse` answers only with one. It is here because an argument
# beginning with `-` is an *option* to git rather than a revision, and the
# distance between "no caller does that" and "no caller can" is one line.
REVISION = re.compile(r"\A[0-9a-f]{40}\Z")

# How many commit subjects a refusal prints before it stops. A pin fifty-seven
# behind would otherwise bury its own message, and the point of naming them is
# that somebody reads them.
NAMED = 10


def pins_in(text: str) -> list[tuple[str, str]]:
    """Every pin on one of this repository's workflows, as (workflow, sha)."""
    return [(m.group("workflow"), m.group("sha")) for m in PIN.finditer(text)]


def pins_under(root: pathlib.Path) -> dict[tuple[str, str], list[str]]:
    """The same across a repository's workflows, against the files naming each.

    Keyed by the pin rather than by the file, because a repository pins the same
    revision in several places and a refusal repeating itself once per file is
    one somebody stops reading.
    """
    found: dict[tuple[str, str], list[str]] = {}

    for path in sorted(root.glob(".github/workflows/*.yml")):
        for pin in pins_in(path.read_text(encoding="utf-8")):
            found.setdefault(pin, []).append(str(path))

    return found


def _git(spec: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    """One read-only git command inside a checkout, addressed by absolute path.

    Resolved rather than passed through. A relative path is the ordinary case and
    fine either way; one beginning with `-` is an option to git rather than a
    directory, and resolving it makes it neither. The arguments after it are this
    file's own words and the revisions `REVISION` has already vouched for.
    """
    return subprocess.run(
        ["git", "-C", str(spec.resolve()), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def commits_between(
    spec: pathlib.Path, pin: str, head: str, workflow: str
) -> list[str] | None:
    """The commits `head` has and `pin` does not that changed `workflow`.

    Narrowed to the one file, because the one file is the whole of what a pin
    holds. The scripts these workflows run are checked out at `main` on every
    run and reach a consumer whatever its pin says; only the steps and the
    arguments travel with the revision. A pin behind by commits that cannot
    reach it is current, and a check that called it stale would be red on every
    pull request in the organisation for most of every day — which is how a
    check stops being required.

    `None` where the question could not be asked — a shallow checkout, a pin that
    is not a commit in this repository at all, or a pair that are not revisions.
    A gate that cannot ask is not a gate that passed, and the caller says so
    rather than reporting nothing.
    """
    if not (REVISION.match(pin) and REVISION.match(head)):
        return None

    asked = _git(
        spec,
        "log",
        "--no-color",
        "--format=%h %s",
        f"{pin}..{head}",
        "--",
        f".github/workflows/{workflow}",
    )

    if asked.returncode != 0:
        return None

    return [line for line in asked.stdout.splitlines() if line.strip()]


def refusal(workflow: str, where: list[str], missed: list[str]) -> str:
    """What one stale pin says, including what it is holding back."""
    named = missed[:NAMED]
    more = len(missed) - len(named)

    behind = (
        f"::error::{workflow} has changed {len(missed)} time(s) since the commit "
        f"pinned in {', '.join(where)}."
    )

    said = [behind, "  It has not taken:", *(f"    {line}" for line in named)]

    if more:
        said.append(f"    … and {more} more, not listed here.")

    return "\n".join(said)


def head_of(spec: pathlib.Path) -> str | None:
    """The commit this repository's default branch is at, as the checkout has it.

    `None` where there is no checkout to ask, which is the first thing this runs
    and the first way it can be unable to answer.
    """
    if not spec.is_dir():
        return None

    asked = _git(spec, "rev-parse", "HEAD")

    return asked.stdout.strip() if asked.returncode == 0 else None


def main() -> int:
    root = pathlib.Path(".")
    spec = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".spec-canonical")

    head = head_of(spec)
    if head is None:
        print(f"::error::no spec checkout at {spec}, so no pin was checked.")
        return 2

    pinned = pins_under(root)
    if not pinned:
        print("no reusable workflow of this repository is pinned here; nothing to check")
        return 0

    stale = []
    for (workflow, sha), where in sorted(pinned.items()):
        missed = commits_between(spec, sha, head, workflow)

        if missed is None:
            # A pin this checkout cannot resolve. Loud, and code 2: it is a
            # shallow clone or a commit that was rewritten away, and either is
            # this side's fault rather than the contributor's.
            print(
                f"::error::cannot resolve {sha[:8]} against the spec checkout at {spec}. "
                "A shallow clone cannot answer how far behind a pin is, and a gate "
                "that could not ask must not report that it asked."
            )
            return 2

        if missed:
            stale.append(refusal(workflow, where, missed))

    if stale:
        print("\n".join(stale))
        print(
            f"\nBump each pin named above to {head}, and set the trailing comment to "
            "the tag that revision carries. The workflow file is the whole of what a "
            "pin holds — the scripts it runs are checked out at `main` on every run — "
            "so only a pin whose own workflow has moved is named here (Q-R68)."
        )
        return 1

    print(f"every pin holds the newest revision of the workflow it names ({head[:8]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
