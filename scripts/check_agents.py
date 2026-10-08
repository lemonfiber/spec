#!/usr/bin/env python3
"""A repository's AGENTS.md points first at the board and the shared rules, and
stays short (GOV-R26, GOV-R50).

The file a coding agent reads first is the one most tempted to grow into a
second copy of the organisation's rules. So the first thing after its title has
to be a quoted block that points at the roadmap and board on lemonfiber.app and
then at working in the repositories, and the whole file has to fit within a cap
a reader takes in at once. What the shared pages hold is read there, not here.

Usage, from the root of the repository being checked::

    check_agents.py --root .

Exit 0 = the file is there, opens with the pointer and fits the cap; 1 = it does
not, each reason named.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

#: The file, at a repository's root.
FILE = "AGENTS.md"
#: The most lines it may hold.
CAP = 120
#: Where the roadmap and board are published, which the block names first.
BOARD = "https://lemonfiber.app"
#: The shared rules, which the block names after the board.
RULES = "50-governance/working-in-the-repositories.md"


def pointer(lines: list[str]) -> str:
    """The quoted block that follows the title, joined, or nothing."""
    rest = lines[1:] if lines and lines[0].startswith("# ") else lines
    at = next((n for n, line in enumerate(rest) if line.strip()), len(rest))
    block = []
    for line in rest[at:]:
        if not line.startswith(">"):
            break
        block.append(line.lstrip("> ").rstrip())
    return " ".join(block)


def faults(text: str | None) -> list[str]:
    """What is wrong with one AGENTS.md, or nothing."""
    if text is None:
        return [f"there is no {FILE}; every repository carries one (GOV-R26)"]
    lines = text.splitlines()
    found = []
    block = pointer(lines)
    board, rules = block.find(BOARD), block.find(RULES)
    if board < 0 or rules < 0 or rules < board:
        found.append(
            f"{FILE} does not open with the pointer: a quoted block after the title naming "
            f"{BOARD} and then {RULES} (GOV-R50)"
        )
    if len(lines) > CAP:
        found.append(f"{FILE} holds {len(lines)} lines; the cap is {CAP} (GOV-R50)")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    path = pathlib.Path(args.root) / FILE
    found = faults(path.read_text(encoding="utf-8") if path.is_file() else None)
    for fault in found:
        print(f"::error file={FILE}::{fault}")
    if not found:
        print(f"{FILE} opens with the pointer and holds no more than {CAP} lines")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
