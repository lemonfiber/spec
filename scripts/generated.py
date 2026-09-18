#!/usr/bin/env python3
"""Regenerate every generated file and say who owns the one that moved.

Four surfaces here are written by a script and compared against what is
committed. The comparison was four bare `git diff --exit-code` lines, so a
contributor who edited one of them by hand saw a diff of their own change and no
statement of what had happened: not which of the four generators owns the file,
not the command that rewrites it, not that editing it was the mistake. The
number in the diff is the answer; what a refusal has to add is where the answer
comes from.

So the pairing of a file to its generator lives here, once, and both the local
recipe and the CI job read it. A banner check can read the same table, which is
the reason it is a table and not four lines of shell: a file can be generated in
exactly one place, and two lists of which files those are is one list that goes
wrong.

The same table answers the other question a maintainer has when they open one of
these files: whether they may edit it. Only `BOARD.md` and `index.json` said so;
the other three said nothing, and all three are only *partly* generated, which is
worse than saying nothing about a file written whole — a reader cannot tell which
paragraphs are theirs. So every registered file has to name its generator near the
top, and that is checked here rather than remembered.

What this does not do is decide whether the generated content is right. Each
generator refuses on its own when its anchor is missing — `gen_repos.py` alone
has three such refusals — and this runs them and reads the tree afterwards.

Run:  python3 scripts/generated.py
      python3 scripts/generated.py --list
      python3 scripts/generated.py --banners
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Generated:
    """One generator, the files it writes, and the region it owns in each."""

    generator: str
    """The script, relative to the repository root."""

    recipe: str
    """The one command a contributor runs to rewrite the files."""

    paths: tuple[str, ...]
    """What it writes, relative to the repository root."""

    owns: str
    """The region of each file it writes, for a file it does not write whole."""


# Every file in this repository that a script writes. `gen_redirects.py` is not
# here: it writes a site into a build directory rather than a file in the tree,
# so there is nothing committed for a diff to compare.
GENERATED = (
    Generated(
        generator="scripts/gen_roadmap_table.py",
        recipe="python3 scripts/gen_roadmap_table.py",
        paths=("00-overview/roadmap.md",),
        owns="the version table; the milestone prose around it is hand-written",
    ),
    Generated(
        generator="scripts/gen_board.py",
        recipe="python3 scripts/gen_board.py",
        paths=(
            "10-functional/features/index.json",
            "10-functional/features/BOARD.md",
        ),
        owns="the whole of both files",
    ),
    Generated(
        generator="scripts/gen_repos.py",
        recipe="python3 scripts/gen_repos.py",
        paths=("30-repos/README.md",),
        owns="the diagram, the repository table and the counting sentence",
    ),
    Generated(
        generator="scripts/gen_contrast.py",
        recipe="python3 scripts/gen_contrast.py",
        paths=("60-brand/accessibility.md",),
        owns="the contrast table",
    ),
)


# How far into a file the banner has to be. A statement that a page is generated
# is worth nothing where a reader has already started editing, so it goes above
# the first thing anybody reads past the title — and a window rather than a line
# number leaves the files free to differ in how they open.
BANNER_LINES = 12


def owner_of(path: str) -> Generated | None:
    """The generator that writes one path, or None where nothing does."""
    for entry in GENERATED:
        if path in entry.paths:
            return entry
    return None


def refusal(entry: Generated, path: str) -> str:
    """What one moved file says: the file, the owner, the command, and why."""
    return "\n".join(
        [
            f"{path} does not match what {entry.generator} writes.",
            "",
            "  This file is generated; edit the source, not the file. What is",
            f"  generated in it: {entry.owns}.",
            "",
            "  If you edited it by hand, undo that and change the source the",
            f"  generator reads. If you changed the source, run `{entry.recipe}`",
            "  and commit what it writes.",
            "",
            "  Why it is generated rather than written: a number derived from",
            "  something beside it is a number that drifts, and nothing would say",
            "  so. See 40-quality/ci-cd.md.",
        ]
    )


def unbannered(entry: Generated) -> list[str]:
    """Which of an entry's files do not say, near the top, who writes them.

    The rule is deliberately one thing: the generator's own path appears in the
    opening of the file. It is narrow because a banner is prose a maintainer
    should be able to word for their own page, and what cannot be left to
    wording is the one fact a reader needs — which script to go and look at.
    `index.json` satisfies it through the `generated_by` key it already carries,
    which is the same fact in the only form JSON has for it.
    """
    missing = []
    for path in entry.paths:
        head = (ROOT / path).read_text(encoding="utf-8").splitlines()[:BANNER_LINES]
        if not any(entry.generator in line for line in head):
            missing.append(path)
    return missing


def banner_refusal(entry: Generated, path: str) -> str:
    """What one unbannered file says."""
    return "\n".join(
        [
            (
                f"{path} is written by {entry.generator} and does not say so in "
                f"its first {BANNER_LINES} lines."
            ),
            "",
            "  A maintainer opening it cannot tell that editing it is the",
            f"  mistake. What is generated in it: {entry.owns}.",
            "",
            f"  Add a line near the top naming `{entry.generator}`, what it reads,",
            f"  and that `{entry.recipe}` rewrites it. The wording is yours; the",
            "  path is the part a reader needs.",
            "",
            "  Why: the three kinds of document here — generated, checked, free —",
            "  are only a promise if a document says which it is.",
        ]
    )


def banners(out) -> int:
    """Every generated file says, near the top, which script writes it."""
    if not GENERATED:
        print(
            "no generated file is registered, so no banner was looked for — a "
            "pass here would be an account of every generated surface having "
            "opened none of them.",
            file=out,
        )
        return 1

    refused = 0
    for entry in GENERATED:
        for path in unbannered(entry):
            print(banner_refusal(entry, path), file=out)
            print(file=out)
            refused += 1

    if refused:
        return 1

    counted = sum(len(entry.paths) for entry in GENERATED)
    print(f"{counted} generated file(s) name the generator that writes them")
    return 0


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def moved(paths: list[str]) -> list[str] | None:
    """Which of `paths` differ from what is committed, or None if git could not say.

    A comparison that did not happen is not a comparison that found nothing. The
    caller refuses on `None` rather than reporting a clean tree, because a git
    that cannot answer and a tree that matches look identical from the exit code
    of the thing that asked.
    """
    asked = _git("diff", "--name-only", "--", *paths)
    if asked.returncode != 0:
        return None
    return [line for line in asked.stdout.splitlines() if line.strip()]


def run(entry: Generated) -> str | None:
    """Run one generator. The reason it refused, or None where it did not."""
    done = subprocess.run(
        [sys.executable, str(ROOT / entry.generator)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode == 0:
        return None
    return (done.stderr or done.stdout).strip() or f"exit {done.returncode}"


def check(out) -> int:
    """Regenerate everything and refuse what moved, naming who owns it."""
    # The table is what every other answer here is about. Empty, this would run
    # no generator, compare no file and report a clean tree — an account of all
    # four surfaces that had looked at none of them.
    if not GENERATED:
        print(
            "no generated file is registered, so nothing was regenerated and "
            "nothing was compared — this check would pass over a repository whose "
            "four generated surfaces had all been hand-edited.",
            file=out,
        )
        return 1

    for entry in GENERATED:
        missing = [
            name
            for name in (entry.generator, *entry.paths)
            if not (ROOT / name).exists()
        ]
        if missing:
            print(
                f"{entry.generator} is registered as writing {', '.join(entry.paths)} "
                f"and these are not here: {', '.join(missing)}. A registered pair "
                "that does not exist is a comparison this check silently stops "
                "making — move the entry with the file, or take it out.",
                file=out,
            )
            return 1

    for entry in GENERATED:
        why = run(entry)
        if why is not None:
            print(f"{entry.generator} refused to write its output:\n{why}", file=out)
            return 1

    every = [path for entry in GENERATED for path in entry.paths]
    differs = moved(every)
    if differs is None:
        print(
            "git could not be asked which generated files differ, so this check "
            "compared nothing — which is not the same as finding nothing.",
            file=out,
        )
        return 1

    if not differs:
        print(f"{len(every)} generated file(s) match what their generators write")
        return banners(out)

    for path in differs:
        entry = owner_of(path)
        # Unreachable while the diff is scoped to the registered paths, and the
        # answer is here rather than an index error because the scoping is one
        # argument away from being widened.
        if entry is None:  # pragma: no cover
            print(f"{path} differs and no generator here claims it.", file=out)
            continue
        print(refusal(entry, path), file=out)
        print(file=out)

    return 1


def listing(out) -> int:
    """The table, for a human and for the banner check that reads it."""
    for entry in GENERATED:
        for path in entry.paths:
            print(f"{path}\t{entry.generator}\t{entry.recipe}", file=out)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the file/generator/recipe table and do nothing else",
    )
    parser.add_argument(
        "--banners",
        action="store_true",
        help="check only that each generated file names its generator",
    )
    args = parser.parse_args(argv)

    if args.list:
        return listing(sys.stdout)
    if args.banners:
        return banners(sys.stderr)
    return check(sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
