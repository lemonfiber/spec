#!/usr/bin/env python3
"""No tracked file is longer than a reviewer can read (Q-R81).

Every tracked file is counted, whoever or whatever wrote it. A generated file is
read as often as a written one: in a diff, by the reader of a vendored copy, and by
the generator of the next thing downstream. One that outgrows a reader has to be
split where it is generated.

Two kinds of file are not counted, and the list is written here and nowhere else:
the lockfiles a package manager writes and nobody reads line by line, and the
images and fonts that are binary or, in an SVG's case, drawn rather than read.

Usage, from the root of the repository being checked::

    check_line_cap.py --root .

Exit 0 = every counted file is within the cap, 1 = at least one is over it, or the
tree could not be listed.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

#: The most lines a tracked file may hold.
CAP = 1000

#: Lockfiles, by the name a package manager gives them. `*.lock` covers
#: `Cargo.lock`, `composer.lock` and `uv.lock`; npm's is the one that ends otherwise.
LOCK_SUFFIX = ".lock"
LOCKFILES = frozenset({"package-lock.json"})

#: Images and fonts, by extension.
ASSETS = frozenset(
    {
        ".apng", ".avif", ".bmp", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".svg",
        ".tif", ".tiff", ".webp",
        ".eot", ".otf", ".ttf", ".woff", ".woff2",
    }
)

#: The `git ls-files --stage` modes of what is not a file's own text: a submodule
#: and a symbolic link. Neither has lines of its own to count.
NOT_TEXT = frozenset({"160000", "120000"})


def exempt(path: str) -> bool:
    """Whether `path` is a lockfile, an image or a font."""
    name = os.path.basename(path)
    if name in LOCKFILES or name.endswith(LOCK_SUFFIX):
        return True
    return os.path.splitext(name)[1].lower() in ASSETS


def lines_in(data: bytes) -> int:
    """How many lines `data` holds, the last one counted whether it ends or not."""
    count = data.count(b"\n")
    if data and not data.endswith(b"\n"):
        count += 1
    return count


def tracked(root: pathlib.Path) -> list[str] | None:
    """Every tracked path whose own text can be counted, or None where git could not say.

    A listing that did not happen is not a listing of nothing, and the caller
    refuses rather than reporting a clean tree.
    """
    # The root is the working directory rather than an argument, so no path given on
    # the command line reaches git's own arguments.
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--stage", "-z"],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if listed.returncode != 0:
        return None
    paths = []
    for entry in listed.stdout.decode("utf-8", "surrogateescape").split("\0"):
        if not entry:
            continue
        meta, path = entry.split("\t", 1)
        if meta.split(" ", 1)[0] not in NOT_TEXT:
            paths.append(path)
    return paths


def over(root: pathlib.Path, paths: list[str]) -> list[tuple[str, int]]:
    """Every counted path over the cap, with its line count, longest first."""
    found = []
    for path in paths:
        if exempt(path):
            continue
        target = root / path
        if not target.is_file():
            continue
        count = lines_in(target.read_bytes())
        if count > CAP:
            found.append((path, count))
    return sorted(found, key=lambda pair: (-pair[1], pair[0]))


def refusal(path: str, count: int) -> str:
    """What one file over the cap is told."""
    return (
        f"{path} is {count} lines, over the cap of {CAP}. Split it by what it holds; "
        f"a generated file is split where it is generated."
    )


def main(argv: list[str] | None = None, out=sys.stdout) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    args = parser.parse_args(argv)

    paths = tracked(args.root)
    if paths is None:
        print(f"::error::git could not list the files tracked under {args.root}.", file=out)
        return 1
    if not paths:
        print(
            f"::error::{args.root} tracks no file this could count, so nothing was "
            "measured — a check that read nothing has not passed.",
            file=out,
        )
        return 1

    found = over(args.root, paths)
    for path, count in found:
        print(f"::error file={path}::{refusal(path, count)}", file=out)
    if found:
        print(f"{len(found)} of {len(paths)} tracked file(s) are over {CAP} lines.", file=out)
        return 1
    print(f"{len(paths)} tracked file(s), none over {CAP} lines.", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
