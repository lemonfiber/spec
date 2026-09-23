#!/usr/bin/env python3
"""Bring a consumer's stale pins forward, so the bump is opened rather than owed — OPS-R48.

`workflow_pins.py` says a pin is behind. This writes the bump it asks for. They
are two halves of one answer and they read it with one reader: every function
that decides *what is stale* is imported from the gate rather than written again
here, so the fan-out cannot bump something the gate would not have named, and
cannot leave behind something it would.

**Only a pin whose own workflow moved.** The rule the gate measures by is the
rule this rewrites by, for the reason given there: the workflow file is the whole
of what a pin holds, so a repository sitting five tags back with none of its
named files changed is current, and rewriting its pins would be churn that moves
what they point at without moving what they run.

**The comment carries the tag, and that is not decoration.** Dependabot's
`github-actions` updater compares versions; a pin whose trailing comment names no
tag gives it nothing to be newer than. A bump that moved the revision and left
the comment behind would silence the bot that is the second half of keeping these
current.

**The revision is read from the tag, and never from `HEAD`.** The number and the
revision written beside it are one fact, so they are read from one place. Taking
the revision from whatever the spec checkout was sitting on agrees with the tag
in exactly one case — a fan-out fired the moment the tag was cut — and disagrees
silently in the case the dispatch input exists for, which is bringing everything
up to a number published earlier.

Usage:
  fan_out_pins.py --repo <consumer checkout> --spec <spec checkout with tags> --tag vX.Y.Z

Rewrites files in place and prints what it touched. The caller decides what to do
about it by looking at the checkout, which is the one account of what happened
that cannot disagree with itself.

Exit 0 = the question was asked and answered, whether or not anything was
rewritten. Exit 2 = **could not ask** — no spec checkout, a tag this checkout
does not hold, or a pin it cannot resolve. Never 1: a consumer with nothing
stale is the ordinary case and the commonest one, and a script that failed on it
would teach its caller to ignore the code that means something went wrong.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import tomllib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

# `_git` crosses from the gate deliberately, on the same terms as the readers
# below: these two files are one answer in two halves, and a second way to run
# git against a checkout is a second way for them to disagree about one.
from workflow_pins import _git, commits_between, pins_under

#: `v1.0.7` and nothing else. The series carries no meaning beyond order, but it
#: is written into fourteen repositories, so what may be written is closed here
#: rather than trusted to the caller that assembled it.
TAG = re.compile(r"\Av\d+\.\d+\.\d+\Z")

#: The org's own map. `[[repo]]` is what this specification governs; the
#: `[[ungoverned]]` table at its foot is deliberately not read here.
REGISTRY = pathlib.Path("30-repos/repos.toml")

#: This repository calls its own reusable workflows with `./`, so it holds no pin
#: on itself and a fan-out that visited it would open an empty pull request every
#: time a tag was cut.
ITSELF = "spec"


def consumers(registry: pathlib.Path = REGISTRY) -> list[str]:
    """Every governed repository but this one, in the order the map lists them.

    Read from the map rather than kept as a second list beside it. A fan-out with
    its own copy of the org visits fourteen repositories on the day somebody
    creates a fifteenth, and says nothing about the one it missed — which is the
    failure `repos.toml` was written to end for the README and is no better here.
    """
    named = tomllib.loads(registry.read_text(encoding="utf-8"))

    return [
        str(one["name"])
        for one in named.get("repo", [])
        if str(one.get("name", "")) != ITSELF
    ]


def rewritten(text: str, workflow: str, was: str, now: str, tag: str) -> str:
    """One pin on one workflow, moved to `now` and re-labelled `tag`.

    Addressed by the pair rather than by the revision alone. A repository pins
    several workflows at the same commit and only some of their files have moved
    — rewriting by revision would carry the current ones forward too, which is
    the churn the per-file rule exists to avoid.

    The comment is replaced where there is one and added where there is not.
    Both occur: a pin added by hand tends to carry no tag, and it is exactly the
    pin Dependabot is then unable to propose a bump for.
    """
    named = re.escape(f"lemonfiber/spec/.github/workflows/{workflow}@{was}")

    # The comment is whatever follows on the line. It is replaced wholesale
    # rather than edited, because what is there is a tag name, and the tag name
    # is the thing that has changed.
    return re.sub(
        rf"(uses:\s*){named}(?:[ \t]*#[^\n]*)?",
        lambda m: f"{m.group(1)}lemonfiber/spec/.github/workflows/{workflow}@{now} # {tag}",
        text,
    )


def commit_named_by(spec: pathlib.Path, tag: str) -> str | None:
    """The revision `tag` names in this checkout, or `None` where it names none.

    **Read from the tag, never from `HEAD`.** This used to be `head_of(spec)`,
    and the two agree only in the one case the caller happens to run most: a
    fan-out fired by `publish-pin-tag` runs against a checkout of `main` at the
    instant the tag was cut from it. A dispatch naming an older number runs
    against a `main` that has moved, and the pin written there would carry that
    number beside a revision the number does not name — which is the one thing
    `workflow-pins` cannot catch, because the file it compares is the same file.
    """
    asked = _git(spec, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")

    return asked.stdout.strip() if asked.returncode == 0 else None


def bring_forward(
    repo: pathlib.Path, spec: pathlib.Path, tag: str, named: str
) -> tuple[list[str], str] | None:
    """Rewrite every stale pin in `repo`, returning what moved and to where.

    `named` is the revision `tag` names, resolved by the caller so that the
    number and the revision written beside it cannot come from two places.

    `None` where the question could not be asked, which the caller reports rather
    than treating as a repository with nothing to do. The two are indistinguishable
    from the outside and only one of them is good news.
    """
    moved: list[str] = []

    for (workflow, sha), where in sorted(pins_under(repo).items()):
        missed = commits_between(spec, sha, named, workflow)

        if missed is None:
            return None

        if not missed:
            continue

        # Unique, and that is not tidiness. The reader lists a file once per
        # occurrence, so a file calling the same workflow from two jobs is named
        # twice — and the first rewrite replaces both, leaving the second pass
        # with nothing to change and the refusal below to raise about it.
        for name in dict.fromkeys(where):
            path = pathlib.Path(name)
            before = path.read_text(encoding="utf-8")
            after = rewritten(before, workflow, sha, named, tag)

            # A pin the reader found and this could not rewrite is a disagreement
            # between two halves that must agree. Louder than a silent skip,
            # which would ship a branch that does not fix what it claims to.
            if after == before:
                return None

            path.write_text(after, encoding="utf-8")
            moved.append(f"{name}: {workflow} {sha[:8]} -> {named[:8]} ({tag})")

    return moved, named


def main() -> int:
    parsed = argparse.ArgumentParser(description=__doc__)
    parsed.add_argument("--repo", help="the consumer checkout")
    parsed.add_argument("--spec", help="a spec checkout holding the tag")
    parsed.add_argument(
        "--tag", help="the published number; its revision is read from it"
    )
    parsed.add_argument(
        "--consumers",
        action="store_true",
        help="print every governed repository but this one, and do nothing else",
    )
    args = parsed.parse_args()

    if args.consumers:
        print("\n".join(consumers()))
        return 0

    if not (args.repo and args.spec and args.tag):
        print("::error::--repo, --spec and --tag are all required to bump a pin.")
        return 2

    if not TAG.match(args.tag):
        print(
            f"::error::{args.tag!r} is not a pin tag. The comment beside a pin is what "
            "Dependabot compares, so it carries the published `vN.N.N` and nothing else."
        )
        return 2

    spec = pathlib.Path(args.spec)
    repo = pathlib.Path(args.repo)

    # Asked before the tag is, so that "there is no checkout here" is never
    # reported as "that number was never published". They are different faults
    # with different cures, and one sentence covering both sends the reader to
    # the wrong one.
    if not spec.is_dir():
        print(
            f"::error::there is no spec checkout at {spec}. A fan-out that could not "
            "ask must not report a repository as current."
        )
        return 2

    # Refused rather than fallen back from. A fan-out that could not find the
    # number and wrote whatever the checkout was sitting on would put a pin in
    # every consumer whose comment names one revision and whose `@` names
    # another, and both halves would look right on their own.
    named = commit_named_by(spec, args.tag)

    if named is None:
        print(
            f"::error::{args.tag} is not a tag in {spec}. The revision a pin "
            "carries is read from the tag, so a checkout without it — a clone "
            "that fetched no tags, or a number never published — cannot say "
            "what this bump should point at."
        )
        return 2

    brought = bring_forward(repo, spec, args.tag, named)

    if brought is None:
        print(
            f"::error::could not read the pins in {repo} against the spec checkout at "
            f"{spec}. A shallow clone cannot answer how far behind a pin is, and a "
            "fan-out that could not ask must not report a repository as current."
        )
        return 2

    moved, at = brought

    if not moved:
        print(f"{repo}: every pin holds the newest revision of the workflow it names")
        return 0

    print(f"{repo}: brought {len(moved)} pin(s) forward to {at[:8]}")
    for line in moved:
        print(f"    {line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
