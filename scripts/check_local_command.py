#!/usr/bin/env python3
"""The command run before a push says what it does not run (Q-R57, OPS-R51).

Every repository has one command that stands for CI locally — `just ci`,
`npm run ci`, `composer ci`. None of them is CI. Between four and seventeen of
the jobs a pull request starts in this organisation are forge-side: the citation
gate, the sign-off, the subject, CodeQL, the secret scan, the label sync. A
machine with a clone cannot run any of them, and no recipe here ever will.

So a recipe describing itself as *everything CI runs* is saying something that
cannot be true, and the cost is specific rather than aesthetic: a contributor who
runs it, pushes, and goes red learns that the local command is not worth running.
One repository's recipe said it covered every check CI runs while running four of
eighteen.

What this holds is the sentence, not the coverage. A recipe may leave out as much
as it likes; what it may not do is claim the opposite. Two shapes pass:

    Everything CI runs bar the image check, which needs the network.
    Every gate CI runs but backward compatibility; run `composer bc` for that one.

and one does not::

    Everything CI runs, in CI's order.

The floor is the entry point itself. A repository with no local command, or one
whose command nobody described, is refused rather than passed over — a command
nobody wrote a sentence about is a command nobody can decide whether to trust,
and it is also the state in which this check has nothing to read and would
otherwise report that every claim here is honest.

Usage, from the root of the repository being checked::

    check_local_command.py --root .

Exit 0 = the local command is described and its description is honest.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

#: Where a repository's one local command lives, and what it is called there.
#: A repository may carry more than one of these — the two sites drive npm from a
#: justfile — and every one of them that defines the entry point is read.
RUNNERS = (
    ("justfile", "just ci"),
    ("package.json", "npm run ci"),
    ("composer.json", "composer ci"),
)

#: The claim. A sentence saying the local command is what CI runs — which is the
#: sentence that has to carry a qualifier, because it is false without one.
#:
#: Deliberately narrow, and the cost of that is stated rather than hidden: a claim
#: phrased outside this shape is not governed. Widening it far enough to catch
#: every possible wording would start rewriting prose that is not making a claim
#: at all, which is how a check comes to be argued with instead of obeyed.
CLAIM = re.compile(
    r"(?:every(?:thing)?|all)\s+(?:the\s+)?"
    r"(?:check|checks|gate|gates|thing|things)?\s*"
    r"(?:\w+\s+){0,3}?CI runs",
    re.IGNORECASE,
)

#: What turns the claim into a true sentence: a clause in it naming what is left
#: out. `after` is here because one of the honest shapes is a step CI runs *first*
#: rather than one it runs instead — installing a browser, fetching a toolchain.
QUALIFIER = re.compile(
    r"\b(?:bar|but|except|excepting|besides|apart from|other than|after|minus)\b",
    re.IGNORECASE,
)

#: The other honest shape: the claim stands and the block around it names the jobs
#: that are not in the recipe. A list is better than a clause where there are six
#: of them, so both are accepted — what is refused is neither.
#:
#: Read over the whole description rather than the one sentence, which is the
#: difference between this and QUALIFIER. It is deliberately a short list of
#: phrases that can only be about an omission: "not the command to run before a
#: push" is a sentence about something else and must not read as one of these.
NAMES_WHAT_IT_OMITS = re.compile(
    r"(?:\b(?:is|are|jobs?|checks?|gates?|steps?)\s+not\s+(?:here|in it|in this)\b"
    r"|\bnot\s+(?:here|in it|in this recipe)\b"
    r"|\bdoes not run\b|\bdo not run\b|\bdoes not cover\b"
    r"|\bleaves? out\b|\bleft out\b|\bcannot run\b)",
    re.IGNORECASE,
)

#: A sentence ends at a full stop followed by a space or a line end, which is
#: enough for prose written in comments and JSON strings and avoids splitting
#: `composer ci` or `0.16.0` in half.
SENTENCE = re.compile(r"(?<=[.!?])(?:\s+|$)")


def sentences(text: str) -> list[str]:
    """The text, split into sentences, with comment and markdown noise removed."""
    flat = re.sub(r"^[#\s>*-]+", "", text, flags=re.MULTILINE)
    flat = re.sub(r"\s+", " ", flat)
    return [one.strip() for one in SENTENCE.split(flat) if one.strip()]


def from_justfile(path: pathlib.Path) -> tuple[bool, str]:
    """The `ci` recipe and the comment block immediately above it.

    `just` reads that block itself — it is what `just --list` prints beside the
    recipe — so it is the description rather than a place one could go, and a
    recipe without one is undescribed in the tool as well as here.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines):
        if not re.match(r"^ci\b\s*[:\w]", line):
            continue
        said = []
        walk = number - 1
        while walk >= 0 and lines[walk].startswith("#"):
            said.append(lines[walk])
            walk -= 1
        return True, "\n".join(reversed(said))
    return False, ""


def from_composer(path: pathlib.Path) -> tuple[bool, str]:
    """The `ci` script and whatever `scripts-descriptions` says about it.

    Composer has a slot for the sentence and prints it in `composer list`, which
    is the same arrangement as a justfile comment.
    """
    read = json.loads(path.read_text(encoding="utf-8"))
    if "ci" not in read.get("scripts", {}):
        return False, ""
    return True, read.get("scripts-descriptions", {}).get("ci", "")


def from_package(path: pathlib.Path) -> tuple[bool, str]:
    """The `ci` script, and nothing describing it.

    `package.json` has no slot for a sentence and npm prints none, so a repository
    driving its gate through npm says what the command covers somewhere else — a
    justfile beside it, which is what the two sites do. Returning no description
    here is therefore not a refusal on its own; it is one only if nothing else in
    the repository describes the command either.
    """
    read = json.loads(path.read_text(encoding="utf-8"))
    return "ci" in read.get("scripts", {}), ""


READERS = {
    "justfile": from_justfile,
    "composer.json": from_composer,
    "package.json": from_package,
}


def described(repo: pathlib.Path) -> tuple[list[str], list[str]]:
    """Every local command this repository defines, and every sentence about them."""
    found, said = [], []
    for name, called in RUNNERS:
        path = repo / name
        if not path.is_file():
            continue
        try:
            here, text = READERS[name](path)
        except (json.JSONDecodeError, UnicodeDecodeError) as unreadable:
            found.append(f"{called} (in an unreadable {name}: {unreadable})")
            continue
        if here:
            found.append(called)
            if text.strip():
                said.append(text)
    return found, said


def check(repo: pathlib.Path) -> tuple[list[str], int]:
    """What is wrong with this repository's description of its local command."""
    found, said = described(repo)
    if not found:
        return [
            ("no local command: this repository defines no `ci` in a justfile, a "
             "package.json or a composer.json, so there is nothing a contributor "
             "can run before a push and nothing here to hold to a description "
             "(OPS-R51)")
        ], 0

    if not said:
        return [
            (f"{', '.join(found)} is defined here and nothing says what it covers. "
             f"Put the sentence where the tool prints it — a comment above the "
             f"`ci` recipe in a justfile, or `scripts-descriptions.ci` in a "
             f"composer.json — and say what it leaves out, because it leaves out "
             f"every forge-side job")
        ], 0

    problems, counted = [], 0
    for text in said:
        omits = bool(NAMES_WHAT_IT_OMITS.search(text))
        for one in sentences(text):
            if not CLAIM.search(one):
                continue
            counted += 1
            if QUALIFIER.search(one) or omits:
                continue
            problems.append(
                f"this sentence says the local command is CI, and it is not: "
                 f"{one!r}. Every pull request here starts jobs no clone can run "
                 f"— the citation gate, the sign-off, the subject, the secret "
                 f"scan — so an unqualified claim is false whatever the recipe "
                 f"grows. Name what it leaves out: in the sentence, the way "
                 f"lemonfiber-media-stack does — \"Everything CI runs bar the "
                 f"image check, which needs the network\" — or as a list beside "
                 f"the recipe, which is better where there are several (Q-R57)"
            )
    return problems, counted


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="root of the repo being checked")
    args = ap.parse_args()
    repo = pathlib.Path(args.root).resolve()

    problems, counted = check(repo)
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        return 1
    found, _ = described(repo)
    print(f"local command: {', '.join(found)}, described, and "
          f"{counted} sentence(s) claiming to be CI name what they leave out")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
