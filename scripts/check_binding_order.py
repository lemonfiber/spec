#!/usr/bin/env python3
"""Refuse a feature that is binding while something it requires is not.

`change-lifecycle.md` says a Draft is "proposed, not binding" and that
implementation must not cite one, and gives the reason: otherwise anyone could
merge a draft and implement against it in the same breath. That rule was written
about a requirement being cited. It has a second half nothing was holding.

A feature's `requires:` are what it cannot meet its own acceptance criteria
without. So an Accepted feature whose requirement is still Draft is binding on
work that rests on something nobody has agreed — every requirement in it is
citable, and the shape it is written against can still move underneath. The
ordering guarantee collapses the same way, one step further out.

`relates:` is not checked, for the reason `check_order.py` does not check it: it
is worth reading and not needed to build, and conflating the two is what let
sixty-seven links accumulate unnoticed.

Superseded and Withdrawn are refused here too, and not as an afterthought. Both
say "not citable for new work" in as many words, so a live feature resting on one
is a feature resting on something the spec has already moved on from — which is
worth hearing about before the next person cites it.

Exit non-zero listing every one, so a single run shows the whole picture rather
than the first of them.
"""

import pathlib
import re
import sys

FEATURES = pathlib.Path("10-functional/features")
ID = re.compile(r"^id:\s*(\S+)", re.MULTILINE)
STATUS = re.compile(r"^status:\s*(\S+)", re.MULTILINE)
REQUIRES = re.compile(r"^requires:\s*\[(.*?)\]\s*$", re.MULTILINE)

# The one status that may be depended on. Named rather than inferred from "not
# draft", so a status added later is refused until somebody decides what it means
# here rather than being quietly allowed by a negation.
BINDING = "accepted"


def _features() -> tuple[dict[str, str], dict[str, list[str]]]:
    """Every feature's status, and what each says it requires."""
    status: dict[str, str] = {}
    wants: dict[str, list[str]] = {}
    for path in sorted(FEATURES.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        found, said = ID.search(text), STATUS.search(text)
        if not (found and said):
            continue
        feature = found.group(1)
        status[feature] = said.group(1)
        needs = REQUIRES.search(text)
        wants[feature] = [part.strip() for part in needs.group(1).split(",") if part.strip()] if needs else []
    return status, wants


def _unmet(feature: str, need: str, status: dict[str, str]) -> str | None:
    """What is wrong with this one requirement, where anything is."""
    theirs = status.get(need)
    if theirs is None:
        return f"{feature} is {BINDING} and requires {need}, which is not a feature here"
    if theirs != BINDING:
        return f"{feature} is {BINDING} and requires {need}, which is {theirs}"
    return None


def main() -> None:
    status, wants = _features()
    problems = [
        said
        for feature, needs in sorted(wants.items())
        if status.get(feature) == BINDING
        for need in needs
        if (said := _unmet(feature, need, status))
    ]
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        sys.exit(f"{len(problems)} feature(s) binding on something that is not agreed")
    binding = sum(1 for said in status.values() if said == BINDING)
    print(f"binding order ok: {binding} accepted features, none resting on a draft")


if __name__ == "__main__":
    main()
