#!/usr/bin/env python3
"""The implementation tracker says only things the spec can back — OPS-R34.

`gate.py` asks whether a version's goals are met. This asks the prior question:
whether the tracker's *claims* correspond to anything. Three ways they can stop
doing so, each found in the field rather than imagined:

  1. A range that overshoots. `G7-R1..R14` read as met a requirement nobody
     wrote — G7 has thirteen. The gate expands ranges, so an off-by-one there
     mints a requirement and marks it done in one stroke, and nothing complains
     because no version locks it either.

  2. A milestone heading naming the wrong version. A milestone spans several
     versions and the boundaries do not line up, so `Mn` is not `0.n.0`. A
     heading that guesses makes a released version look like it shipped with
     unfinished deliverables — or hides that it did.

  3. A tick on a requirement no version locks. Work that cannot be released,
     recorded as though it had been.

  4. A tick a row's own column never claimed. Both this and `gate.py` take
     every identifier on a done row, so a sentence in one explaining that
     something was deferred is what marks that something done. `E3-R5` was
     counted as met that way while two of its three triggers had nothing at all.
     A cross-reference to work that is genuinely done elsewhere is ordinary and
     stays legal; what is refused is an identifier no ticked row claims in its
     column.

  5. The tick character written on a row that is not ticked. Both gates used to
     decide a row by whether its *line* held the glyph, which made a `◐` row
     explaining "this is ✅ when they start" read as done — three requirements
     were counted as met that way and a fourth reached a gate run. The reading
     is by column now (`tracker.py`), and this refuses the glyph in the prose
     that used to cause it, so the shape cannot come back by a different route.

  6. A table nothing can be read as done in. A header naming no status column
     leaves every row in it undecidable, and a gate that stops looking reports
     success about the rows it could read.

Usage:
  status_lint.py --status <IMPLEMENTATION-STATUS.md> --spec <spec repo root>

Exit 0 = every claim backed; 1 = claims that are not (named); 2 = usage.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import tomllib

# The pattern for a requirement *definition* has one home, `integrity.py`, and is
# imported rather than restated: a second copy is a second thing to change, and
# the ceiling below is exactly what goes wrong when a reader of definitions is
# spelled as a reader of mentions.
import tracker
from integrity import REQ_DEF
from patterns import CITE, RANGE
from tracker import DONE, LEGACY_WIDTH, REQUIREMENT_COLUMNS, STATUS_COLUMNS

HEADING = re.compile(r"^##\s+(M[0-9.]+)\b")
VERSION = re.compile(r"`(\d+\.\d+\.\d+)`")
# How far a heading's prose reaches. A milestone names its versions in the
# sentence under the heading, not twelve rows into the table.
PREAMBLE = 9


def within_cwd(raw: str) -> pathlib.Path:
    """Resolve a CLI-supplied path, refusing anything outside the working tree.

    The same guard `gate.py` applies, for the same reason: these paths come from a
    workflow's inputs, and a check that will read any file it is pointed at is a
    way to read any file.
    """
    path = pathlib.Path(raw).resolve()
    if not path.is_relative_to(pathlib.Path.cwd().resolve()):
        print(f"::error::path escapes the working directory: {raw}")
        raise SystemExit(2)
    return path


def defined(spec: pathlib.Path) -> dict[str, int]:
    """The highest requirement number each feature actually defines.

    Definitions, not mentions. A requirement exists where a table row declares it;
    everywhere else the identifier is a citation. Reading citations here raised the
    ceiling to whatever the spec happened to *say* — one line of prose naming
    `G7-R20` lifted G7 from thirteen to twenty and took the overshoot check with
    it, silently, for every number in between. `integrity.py` catches stray
    citations in this repository, so the two gates held each other up; they were
    never meant to, and `.git` is outside what `integrity.py` reads at all.
    """
    highest: dict[str, int] = {}
    # Read each ID whole, then split it: the feature prefix is not a fixed width.
    for doc in spec.rglob("*.md"):
        if ".git" in doc.parts:
            continue
        for ident in REQ_DEF.findall(doc.read_text(encoding="utf-8")):
            feature, _, number = ident.partition("-R")
            highest[feature] = max(highest.get(feature, 0), int(number))
    return highest


def manifests(spec: pathlib.Path) -> tuple[dict[str, set[str]], set[str]]:
    """Which versions each milestone ships in, and every goal any of them locks."""
    milestones: dict[str, set[str]] = {}
    locked: set[str] = set()
    for path in (spec / "70-operations" / "versions").glob("*.toml"):
        if path.stem == "TEMPLATE":
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if milestone := data.get("milestone"):
            milestones.setdefault(milestone, set()).add(path.stem)
        locked.update(data.get("goals", []))
    return milestones, locked


def claimed_ranges(lines: list[str]) -> list[tuple[int, str, int]]:
    """Every range endpoint the tracker claims, with the line it is on."""
    found = []
    for number, line in enumerate(lines, start=1):
        for feature, _, last in RANGE.findall(line):
            found.append((number, feature, int(last)))
    return found


def mentions(text: str) -> set[str]:
    """Every requirement an extent of text names, ranges expanded.

    One reading, because the two callers below must agree: what counts as done and
    what a row claims are the same grammar asked of different extents, and two
    spellings of it is how one comes to accept what the other refuses.
    """
    found: set[str] = set(CITE.findall(text))
    for feature, first, last in RANGE.findall(text):
        found.update(f"{feature}-R{n}" for n in range(int(first), int(last) + 1))
    return found


def ticked(lines: list[str]) -> set[str]:
    """Every requirement the tracker marks done — the same reading `gate.py` takes.

    Literally the same: both read a row's status from the column its table names
    it in, out of `tracker.py`, because two spellings of *done* is how one gate
    comes to accept what the other refuses.
    """
    done: set[str] = set()
    for row in tracker.rows(lines):
        if row is not None and row.done:
            done.update(mentions(row.line))
    return done


def headings(lines: list[str]) -> list[tuple[int, str, set[str]]]:
    """Each milestone heading and the versions its opening prose claims."""
    found = []
    for index, line in enumerate(lines):
        if match := HEADING.match(line):
            prose = "\n".join(lines[index : index + PREAMBLE])
            found.append((index + 1, match.group(1), set(VERSION.findall(prose))))
    return found


def overshooting(status, lines, highest) -> list[str]:
    """Ranges that claim past the last requirement their feature defines."""
    return [
        f"{status}:{number}: claims {feature}-R{last}, but {feature} defines up to "
        f"R{highest[feature]}"
        for number, feature, last in claimed_ranges(lines)
        if feature in highest and last > highest[feature]
    ]


def misnamed(status, lines, by_milestone) -> list[str]:
    """Headings that leave out a version their milestone ships in.

    Omission is the failure to catch. Every heading that misled named one version
    and left the rest out — a milestone that ships in two and admits to one reads
    as though the other's work were somebody else's. Naming an extra version is
    not an error: a milestone whose groundwork shipped early under another's
    version should be free to say so.
    """
    faults = []
    for number, milestone, claims in headings(lines):
        ships_in = by_milestone.get(milestone)
        if ships_in and (missing := ships_in - claims):
            faults.append(
                f"{status}:{number}: {milestone} ships in "
                f"{', '.join(sorted(ships_in))} but does not name "
                f"{', '.join(sorted(missing))}"
            )
    return faults


def unlocked(status, lines, locked) -> list[str]:
    """Ticks on requirements no version manifest locks."""
    orphans = sorted(ticked(lines) - locked)
    return (
        [f"{status}: marked done but locked by no version: {', '.join(orphans)}"]
        if orphans
        else []
    )


def miscolumned(status, lines) -> list[str]:
    """Tables whose rows are read as a shape that checks nothing.

    `tracker.rows()` finds the requirements column by its header, and a header it
    does not know reads as the older three-column shape: the whole row becomes the
    claim, and `unclaimed()` then skips every row in that table. The check does not
    fail, it stops looking — which is the shape worth refusing outright, because a
    tracker table is where a requirement gets marked done.

    Reported only where rows would actually be skipped. A table of the legacy width
    names its requirements inside the deliverable and is meant to read this way,
    and a header with no rows under it is skipping nothing.
    """
    found = []
    header: tuple[int, list[str]] | None = None
    rows = 0

    def verdict() -> None:
        if header is None or rows == 0:
            return
        number, row = header
        if len(row) <= LEGACY_WIDTH or tracker.column_named(row, REQUIREMENT_COLUMNS) is not None:
            return
        found.append(
            f"{status}:{number}: this table has {len(row)} columns and none is named "
            f"{' or '.join(REQUIREMENT_COLUMNS)}, so its {rows} row(s) are read as the "
            "older three-column shape and checked for nothing. Name the requirements "
            "column, or add its heading to REQUIREMENT_COLUMNS."
        )

    for number, line in enumerate(lines, start=1):
        row = tracker.cells(line)
        if not row:
            verdict()
            header, rows = None, 0
            continue
        if tracker.is_rule(row):
            continue
        if header is None:
            header = (number, row)
            continue
        rows += 1
    verdict()
    return found


def unclaimed(status, lines) -> list[str]:
    """Requirements a done row marks done in its prose rather than in its column.

    Naming another requirement in a row's prose is ordinary — a deliverable
    explains what it rests on — and stays legal wherever some done row claims
    that requirement in its own column. What this refuses is the identifier no
    done row ever claims: it is done in the reading and undone in the tree, and
    the sentence carrying it is usually one saying so.
    """
    read = tracker.rows(lines)
    claimed: set[str] = set()
    for row in read:
        if row is not None and row.done:
            claimed.update(mentions(row.claim))

    faults = []
    for number, row in enumerate(read, start=1):
        if row is None or not row.done or row.claim == row.line:
            continue
        stray = sorted(mentions(row.line) - mentions(row.claim) - claimed)
        if stray:
            faults.append(
                f"{status}:{number}: marks {', '.join(stray)} done by naming it in a "
                "ticked row that does not claim it, and no ticked row claims it"
            )
    return faults


def misplaced_glyph(status, lines) -> list[str]:
    """The tick character written somewhere on a row other than its status cell.

    The rule the tracker's preamble had to ask authors to follow, enforced. Both
    gates once decided a row by whether its line held the glyph, so a `◐` row
    whose notes read "this is ✅ when they start" was read as done — three
    requirements were counted as met that way, and a fourth moved a release gate
    from 69 of 72 to 70 before anybody looked.

    Reading by column fixed that, and this keeps the shape from coming back by
    another route: a glyph in the prose is a trap for whoever next edits the
    status cell and leaves the sentence behind.

    Only the *done* glyph. `◐` and `☐` in a sentence cannot mark anything done,
    and refusing them would be a stricter rule than the harm asks for — two rows
    of the tracker use `◐` in prose to name the state rather than to claim it.
    """
    return [
        f"{status}:{number}: writes {DONE} outside the "
        f"{' or '.join(STATUS_COLUMNS)} column, where it says nothing and misleads "
        "everyone. Write \"ticked\" — the word is safe, the character is not."
        for number, row in enumerate(tracker.rows(lines), start=1)
        if row is not None and DONE in row.stray_glyphs
    ]


def unreadable(status, lines) -> list[str]:
    """Tables in which no row can be told done from not done.

    The same refusal `miscolumned` makes about the requirements column, for the
    other column a row is read by. A gate that cannot decide does not fail on
    such a table — it skips it, and silence reads as a pass.
    """
    return [
        f"{status}:{number}: this table names no {' or '.join(STATUS_COLUMNS)} column, "
        "so no row in it can be read as done or not done. Name the status column, or "
        "add its heading to STATUS_COLUMNS."
        for number in tracker.statusless(lines)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True)
    parser.add_argument("--spec", required=True)
    args = parser.parse_args()

    status = within_cwd(args.status)
    spec = within_cwd(args.spec)
    if not status.is_file():
        print(f"::error::no tracker at {status}")
        return 2
    if not (spec / "70-operations" / "versions").is_dir():
        print(f"::error::no version manifests under {spec}")
        return 2

    lines = status.read_text(encoding="utf-8").splitlines()
    faults = [
        *overshooting(status, lines, defined(spec)),
        *misnamed(status, lines, manifests(spec)[0]),
        *unlocked(status, lines, manifests(spec)[1]),
        *unclaimed(status, lines),
        *misplaced_glyph(status, lines),
        *miscolumned(status, lines),
        *unreadable(status, lines),
    ]

    for fault in faults:
        print(f"::error::{fault}")
    if faults:
        print(f"\nstatus-lint: {len(faults)} claim(s) the spec does not back.")
        return 1
    print("status-lint: every claim in the tracker is backed by the spec.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
