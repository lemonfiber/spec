"""How an implementation-status row is read: by column, never by line.

`gate.py` and `status_lint.py` ask the same two questions of a tracker — which
requirements a row claims, and whether that row is done — and each had written
its own answer to the second. Both answered it with `"✅" in line`, which is not
a reading of a row at all. It is a search of the text, and a row's text includes
everything its notes say about work that is *not* done.

That has now gone wrong four times. The tracker's own preamble carries the
work-around — *never write the tick character in a row that is not ticked* — and
records three unmet requirements counted as met before anybody noticed. The
fourth reached a gate run: a `◐` row whose notes ended "this row is ✅ when they
start" moved the release gate from 69 of 72 to 70, on a row a reader can see
says partial. A rule asking an author to avoid a character is not a rule, because
that character is the one the legend tells them to write.

So the reading lives here and is positional. A row's status is the cell under
the column its own table's header names, and a glyph anywhere else on the row is
prose. One copy, because the two gates have to agree: two spellings of *done* is
how one comes to accept what the other refuses, which is why `patterns.py`
exists and is the same reason this does.

What is deliberately *not* fixed here is which identifiers a done row claims.
`gate.py` takes every identifier on a ticked row, prose included, and that is
load-bearing: a deliverable naming what it rests on is ordinary. What guards it
is `status_lint.unclaimed`, which refuses an identifier on a ticked row that no
ticked row claims in its own column.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Header spellings that name a row's requirements column. The tracker uses more
#: than one, and a column found by name is the only way to read both table
#: shapes — a fixed index reads one table's status as another's requirements.
REQUIREMENT_COLUMNS = ("Spec", "Reqs", "Requirements", "Requirement")

#: Header spellings that name a row's status column.
STATUS_COLUMNS = ("Status",)

#: The glyph a status cell carries when the work is finished.
DONE = "✅"

#: Every glyph the tracker's legend gives a status cell: done, partial, not
#: started. Named because the rule that keeps this reading honest is that none
#: of them may appear on a row outside the cell that means it.
GLYPHS = ("✅", "◐", "☐")

#: Columns a table of the older three-column shape carries. Anything wider is
#: expected to name its requirements in a column of its own.
LEGACY_WIDTH = 3

_RULE = re.compile(r":?-{3,}:?")


@dataclass(frozen=True)
class Row:
    """One body row of a tracker table, with the columns its header named."""

    line: str
    cells: tuple[str, ...]
    claim: str
    status_at: int | None

    @property
    def status(self) -> str | None:
        """The status cell, or None where this row has none to read.

        A table naming no status column, and a row with fewer cells than its
        header promised, both answer None — and neither can then be *done*. A
        row that cannot be read is not a row that says yes.
        """
        if self.status_at is None or self.status_at >= len(self.cells):
            return None
        return self.cells[self.status_at]

    @property
    def done(self) -> bool:
        status = self.status
        return status is not None and DONE in status

    @property
    def stray_glyphs(self) -> tuple[str, ...]:
        """Status glyphs written somewhere on this row other than its status cell.

        The failure this whole module exists for, caught where it is written
        rather than where it is read.
        """
        elsewhere = "".join(
            cell for index, cell in enumerate(self.cells) if index != self.status_at
        )
        return tuple(glyph for glyph in GLYPHS if glyph in elsewhere)


def cells(line: str) -> list[str]:
    """A table row's cells, or the empty list for anything that is not one."""
    if not line.lstrip().startswith("|"):
        return []
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_rule(row: list[str]) -> bool:
    """Whether a parsed row is the `|---|---|` rule under a header."""
    return bool(row) and all(_RULE.fullmatch(cell) for cell in row)


def column_named(row: list[str], names: tuple[str, ...]) -> int | None:
    """The index of the first of `names` this header row carries."""
    for name in names:
        if name in row:
            return row.index(name)
    return None


def rows(lines: list[str]) -> list[Row | None]:
    """Each line's row, or None where that line is not a body row of a table.

    Aligned with `lines` so a caller can report a line number without counting
    again. A table's columns are read from its own header and forgotten at the
    blank line after it, because two tables under one heading are shaped
    differently often enough that carrying the first one's columns into the
    second reads its rows wrong.
    """
    found: list[Row | None] = []
    claim_at: int | None = None
    status_at: int | None = None
    heading = True

    for line in lines:
        row = cells(line)
        if not row:
            heading, claim_at, status_at = True, None, None
            found.append(None)
            continue
        if is_rule(row):
            found.append(None)
            continue
        if heading:
            heading = False
            claim_at = column_named(row, REQUIREMENT_COLUMNS)
            status_at = column_named(row, STATUS_COLUMNS)
            found.append(None)
            continue

        # The older three-column shape names its requirements inside the
        # deliverable, where claim and prose cannot be told apart — so there the
        # whole row is the claim, which is what keeps "Form closure (`B1-R4`,
        # `B1-R5`)" from reading as a stray mention of work nobody did.
        claim = row[claim_at] if claim_at is not None and claim_at < len(row) else line
        found.append(Row(line=line, cells=tuple(row), claim=claim, status_at=status_at))

    return found


def statusless(lines: list[str]) -> list[int]:
    """The header line of every table whose rows have no status to read.

    A gate that cannot tell done from not-done in a table does not fail on it —
    it stops looking, and silence reads as a pass. Both callers refuse instead,
    which is why this answers with the header's line number rather than a bool.
    """
    found: list[int] = []
    header: int | None = None
    named = False
    bodies = 0

    def verdict() -> None:
        if header is not None and bodies and not named:
            found.append(header)

    for number, line in enumerate(lines, start=1):
        row = cells(line)
        if not row:
            verdict()
            header, named, bodies = None, False, 0
            continue
        if is_rule(row):
            continue
        if header is None:
            header, named = number, column_named(row, STATUS_COLUMNS) is not None
            continue
        bodies += 1
    verdict()

    return found
