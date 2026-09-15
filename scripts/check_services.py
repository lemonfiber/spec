#!/usr/bin/env python3
"""The bundled-service count this repository states, against the stack that holds them.

Ten pages said "nineteen services" and a twentieth had shipped. Nothing here read
`stack.toml`, so nothing went red, and correcting them by hand only reset the clock:
the stack repository guards its own prose against its own manifest, and the spec held
no copy to guard against.

So the number is computed, and the prose that states it is held to one shape —
`<word> bundled services` — which is the whole of what this reads. A sentence that
says it differently is not governed here, and that is deliberate: a pattern loose
enough to catch every phrasing catches sentences about other things, and a gate that
rewrites the wrong sentence is worse than one that never ran.

**Two silences are refused rather than tolerated**, because both would read as a pass:
a manifest that could not be read, and a tree in which no governed sentence was found.
The second is the one that matters. A checker that finds no prose to compare passes in
exactly the case where the format changed under it, which is the shape this repository
has found in four rules and keeps finding.

**Decision records are left alone.** An ADR is immutable — superseded, never edited —
and what it says about nineteen services was true when it was written. Rewriting one to
match today would be falsifying the record this section exists to keep.

**Which stack, and why not the pinned one.** This reads the stack repository's default
branch rather than the commit a release embedded. The spec describes the product as it
stands; what each release shipped is already recorded, per release, in the `[pins]` of
its version manifest. Reading a pin here would have made this demand "nineteen" today —
`0.14.0` embeds nineteen services and the stack now holds twenty — so the gate would
have been green against a stale input and red against the correct prose, which is the
failure it exists to prevent rather than a version of it.

Usage:
  check_services.py [--stack PATH|URL] [--root PATH] [--write]

Exit 0 = every governed sentence agrees with the stack; 1 = named ones do not;
2 = the question could not be answered.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import tomllib
import urllib.error
import urllib.request

#: Where the stack says what it composes, when nobody names a copy.
STACK = "https://raw.githubusercontent.com/lemonfiber/lemonfiber-media-stack/main/stack.toml"

#: Counting words, because the prose counts in words. Shared shape with
#: `gen_repos.py`'s, and deliberately its own copy: that one counts repositories
#: and stops where an org past twenty has a different problem, and this one counts
#: services and would go on past it.
WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
    8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
    14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
    19: "nineteen", 20: "twenty", 21: "twenty-one", 22: "twenty-two",
    23: "twenty-three", 24: "twenty-four", 25: "twenty-five",
}

#: Where the record of a decision lives, which this never edits.
DECISIONS = "00-overview/decisions"

#: The one shape a governed sentence takes: a counting word, then the phrase.
#:
#: A counting word rather than any word, which is the difference between a gate and
#: a hazard. `\w+` here matched "the bundled services" and "on bundled services" and
#: offered to rewrite both — a pattern loose enough to catch every phrasing catches
#: sentences about other things, and rewriting the wrong sentence is worse than
#: never running. Longest first, so "twenty-one" is not read as "twenty".
SENTENCE = re.compile(
    r"\b(" + "|".join(sorted(WORDS.values(), key=len, reverse=True)) + r") bundled services\b"
)


def word(count: int) -> str:
    if count not in WORDS:
        print(
            f"::error::{count} services, which is past the counting words this gate "
            f"knows. Add it to WORDS in {__file__}."
        )
        raise SystemExit(2)
    return WORDS[count]


def within_cwd(raw: str) -> pathlib.Path:
    """Resolve a path the command line supplied, refusing anything outside the tree.

    The same guard `gate.py` holds its arguments to. A gate that will read a file
    anywhere on the machine is a gate somebody can point at one — and the ordinary
    way to read a stack that lives elsewhere is the address, which is the default.
    """
    path = pathlib.Path(raw).resolve()
    if not path.is_relative_to(pathlib.Path.cwd().resolve()):
        print(
            f"::error::path escapes the working directory: {raw}. Read the stack over "
            "the wire, or from a copy inside this checkout."
        )
        raise SystemExit(2)
    return path


def read_stack(where: str) -> str:
    """The manifest, from a path or over the wire. Unreadable is never empty."""
    if not where.startswith("https://"):
        local = within_cwd(where)
        if local.is_file():
            return local.read_text(encoding="utf-8")
        print(f"::error::no stack manifest at {where}")
        raise SystemExit(2)
    try:
        with urllib.request.urlopen(where, timeout=30) as answer:
            return answer.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, ValueError) as unreachable:
        print(f"::error::could not read {where}: {unreachable}")
        raise SystemExit(2) from unreachable


def services(text: str) -> int:
    """How many services the manifest composes, refusing a manifest that holds none."""
    try:
        composed = tomllib.loads(text).get("service", [])
    except tomllib.TOMLDecodeError as broken:
        print(f"::error::the stack manifest cannot be read: {broken}")
        raise SystemExit(2) from broken
    if not composed:
        print("::error::the stack manifest composes no service; this read the wrong file")
        raise SystemExit(2)
    return len(composed)


def governed(root: pathlib.Path) -> list[pathlib.Path]:
    """Every page holding a governed sentence, decision records excepted."""
    found = []
    for page in sorted(root.rglob("*.md")):
        if DECISIONS in page.as_posix() or ".git" in page.parts:
            continue
        if SENTENCE.search(page.read_text(encoding="utf-8", errors="ignore")):
            found.append(page)
    return found


def disagreements(pages: list[pathlib.Path], root: pathlib.Path, said: str) -> list[str]:
    """Each governed sentence that states something other than what the stack holds."""
    wrong = []
    for page in pages:
        for stated in SENTENCE.findall(page.read_text(encoding="utf-8", errors="ignore")):
            if stated != said:
                wrong.append(
                    f"{page.relative_to(root)} says '{stated} bundled services'; "
                    f"the stack composes {said}"
                )
    return wrong


def rewrite(pages: list[pathlib.Path], said: str) -> int:
    """Put the computed word into every governed sentence, and say how many moved."""
    moved = 0
    for page in pages:
        text = page.read_text(encoding="utf-8")
        fixed = SENTENCE.sub(f"{said} bundled services", text)
        if fixed != text:
            page.write_text(fixed, encoding="utf-8")
            moved += 1
    return moved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stack", default=STACK, help="the stack manifest, as a path or a URL")
    ap.add_argument("--root", default=".", help="the spec checkout to read")
    ap.add_argument("--write", action="store_true", help="rewrite rather than refuse")
    a = ap.parse_args()

    root = within_cwd(a.root)
    said = word(services(read_stack(a.stack)))
    pages = governed(root)
    if not pages:
        print(
            f"::error::no sentence under {root} states a bundled-service count in the "
            "shape this reads, so there was nothing to check. Either the prose moved "
            "or this gate did, and both are faults rather than a pass."
        )
        return 2

    if a.write:
        print(f"services: {said} — rewrote {rewrite(pages, said)} of {len(pages)} page(s)")
        return 0

    wrong = disagreements(pages, root, said)
    for one in wrong:
        print(f"::error::{one}")
    if wrong:
        print(
            "::error::the stack is the source of this number; run "
            "`just services` rather than editing the prose."
        )
        return 1
    print(f"services: {said} — {len(pages)} page(s) agree with the stack")
    return 0


if __name__ == "__main__":
    sys.exit(main())
