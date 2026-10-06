#!/usr/bin/env python3
"""A version manifest's comments say why a goal is in it, never how far it has got.

Where a goal stands is the trackers' to say, and the release gate reads it there
(OPS-R74). A comment that says it as well is a second record of the same fact,
typed by hand into a file nothing compares with the work, and it goes stale the
day the work moves: 0.18.0's comment listed which architecture rows were built,
cited, part met and not met, and by the time anyone read it most of the list
was wrong.

So a comment is refused for a sentence that names a requirement and says it is
built, met, done or partial, or that names where one landed. The list is narrow
on purpose, because the same words have other uses a manifest needs:

  * `built on`, `built against`, `built from` and `built upon` say what a thing
    rests on, not whether it is finished;
  * a sentence that names no requirement is about something else — "the web
    surface is where these are built" says where work happens.

Usage:  check_manifest_comments.py [--root PATH]
Exit 0 = no manifest comment states a goal's progress; 1 = named ones do.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

from patterns import CITE

VERSIONS = "70-operations/versions"

#: A requirement said to be in a state: `is built`, `are not met`, `is part met`.
STATE = re.compile(
    r"\b(?:is|are|was|were)\s+(?:(?:not|now|already|all|both|part|partly|partially)\s+)*"
    r"(?P<word>built|met|done|partial)\b(?!\s+(?:on|against|from|upon)\b)",
    re.IGNORECASE,
)
#: Where a requirement landed, which is a tracker row's `landed`.
LANDED = re.compile(r"\blanded\s+in\b", re.IGNORECASE)
#: How much of a sentence a refusal quotes.
QUOTED = 160
#: Where one sentence ends and the next begins, inside a comment block.
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z`(])")


def blocks(text: str) -> list[list[tuple[int, str]]]:
    """Each run of comment lines, as (line number, the comment's words) pairs."""
    found: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for number, line in enumerate([*text.splitlines(), ""], start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            current.append((number, stripped.lstrip("#").strip()))
        elif current:
            found.append(current)
            current = []
    return found


def claims(text: str) -> list[tuple[int, str, str]]:
    """Each sentence stating a goal's progress: the line its words are on, the words,
    and the sentence."""
    found = []
    for block in blocks(text):
        joined, starts = "", []
        for number, words in block:
            starts.append((len(joined), number))
            joined += words + " "
        offset = 0
        for sentence in SENTENCE.split(joined.strip()):
            at = joined.index(sentence, offset)
            offset = at + len(sentence)
            if not CITE.search(sentence):
                continue
            match = STATE.search(sentence) or LANDED.search(sentence)
            if match:
                where = at + match.start()
                line = max(number for start, number in starts if start <= where)
                quoted = sentence if len(sentence) <= QUOTED else sentence[:QUOTED].rstrip() + "…"
                found.append((line, match.group(0), quoted))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = pathlib.Path(args.root)
    manifests = sorted((root / VERSIONS).glob("*.toml"))
    if not manifests:
        print(f"::error::no manifests under {root / VERSIONS}")
        return 2
    faults = []
    for path in manifests:
        for line, words, sentence in claims(path.read_text(encoding="utf-8")):
            faults.append(f"{path.relative_to(root)}:{line}: \"{words}\" says how far a goal "
                          f"has got, in \"{sentence}\". A manifest comment says why a goal "
                          "is in the version; where it stands is its repository's "
                          "status.toml (OPS-R79).")
    for fault in faults:
        print(f"::error::{fault}")
    if faults:
        return 1
    print(f"manifest comments: {len(manifests)} manifests say why, not how far.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
