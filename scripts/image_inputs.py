#!/usr/bin/env python3
"""Whether a push changed what an image is built from — OPS-R93.

    image_inputs.py --before <commit> --after <commit> [--directory .]

An image a first-party plugin runs as its upstream and lemonfiber builds in a
repository of its own is published from a commit on that repository's `main` only
where the commit changed what the image is built from: the `Dockerfile` in the build
context `--directory` names, its `.dockerignore`, or a path one of the `Dockerfile`'s
`COPY` or `ADD` instructions takes from that context. A source naming the context
itself, `.`, takes every path in it. A `COPY --from` takes from a stage or an image,
not the context, and an `ADD` of a URL takes nothing from it.

Each commit is named in full, forty hexadecimal digits, the commit before by nothing
where the push has none, and the build context is a relative path of plain names; any
other is refused before git is asked.

It prints `yes` where the push changed one of them, and where the commit before cannot
be read, since nothing then says the image is the one already published. Otherwise it
prints `no`, and so it does where nothing changed.

Exit 0 = answered, 1 = a commit or the `Dockerfile` that cannot be read (named on
standard error), 2 = usage.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shlex
import subprocess
import sys

from pin_bump import changed_between

#: The file the build reads its instructions from, and the one that leaves paths out.
DOCKERFILE, IGNORE = "Dockerfile", ".dockerignore"
#: The instructions that take paths from the build context.
TAKES = ("COPY", "ADD")
#: The most of the `Dockerfile` read.
LIMIT = 256 * 1024
#: A commit as the push names it, and a build context as the caller names it.
COMMIT = re.compile(r"\A[0-9a-f]{40}\Z")
CONTEXT = re.compile(r"\A(?:\.|\w[\w.-]*(?:/\w[\w.-]*)*)/?\Z", re.ASCII)


def instructions(text: str) -> list[str]:
    """Each instruction of a `Dockerfile`, its continued lines joined and its comments left out."""
    joined, held = [], ""
    for line in text.splitlines():
        stripped = line.strip()
        if not held and (not stripped or stripped.startswith("#")):
            continue
        if stripped.endswith("\\"):
            held += stripped[:-1] + " "
            continue
        joined.append(held + stripped)
        held = ""
    if held.strip():
        joined.append(held.strip())
    return joined


def sources(text: str) -> list[str]:
    """Every path a `COPY` or `ADD` of `text` takes from the build context."""
    taken = []
    for instruction in instructions(text):
        keyword, _, rest = instruction.partition(" ")
        if keyword.upper() not in TAKES:
            continue
        rest = rest.strip()
        words = json.loads(rest) if rest.startswith("[") else shlex.split(rest)
        flags = [word for word in words if word.startswith("--")]
        named = [word for word in words if not word.startswith("--")]
        if any(flag.startswith("--from=") for flag in flags) or len(named) < 2:
            continue
        taken += [source for source in named[:-1] if "://" not in source]
    return taken


def taken(path: str, source: str) -> bool:
    """Whether `path`, relative to the build context, is one `source` takes."""
    source = source.removeprefix("./").rstrip("/") or "."
    if source == ".":
        return True
    return path == source or path.startswith(f"{source}/") or fnmatch.fnmatchcase(path, source)


def changed_inputs(changed: list[str], dockerfile: str, directory: str) -> bool:
    """Whether any of `changed`, paths from the repository's root, is something the image
    built from `dockerfile` in the context at `directory` is built from."""
    at = context(directory)
    taken_from = sources(dockerfile)
    for path in changed:
        if not path.startswith(at):
            continue
        relative = path.removeprefix(at)
        if relative in (DOCKERFILE, IGNORE) or any(taken(relative, source) for source in taken_from):
            return True
    return False


def context(directory: str) -> str:
    """The build context `directory` names as a prefix of the paths under it, or the
    reason it is refused: a relative path of plain names, with no step out of it and
    nothing git could read as an option."""
    if not CONTEXT.match(directory) or ".." in directory.split("/"):
        raise ValueError(f"{directory!r} is not a build context: a relative path of plain names")
    return "" if directory.rstrip("/") in ("", ".") else f"{directory.strip('/')}/"


def commit(named: str) -> str:
    """`named`, where it is a commit written as git writes one in full."""
    if not COMMIT.match(named):
        raise ValueError(f"{named!r} is not a commit: forty lower-case hexadecimal digits")
    return named


def dockerfile_at(after: str, directory: str) -> str:
    """The `Dockerfile` of the context at `directory`, as commit `after` holds it."""
    shown = subprocess.run(["git", "show", "--end-of-options", f"{commit(after)}:{context(directory)}{DOCKERFILE}"],
                           capture_output=True, check=True).stdout
    if len(shown) > LIMIT:
        raise ValueError(f"{context(directory)}{DOCKERFILE} is larger than {LIMIT} bytes")
    return shown.decode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--directory", default=".")
    args = parser.parse_args(argv)
    try:
        context(args.directory)
        before = commit(args.before) if args.before else ""
        changed = changed_between(before, commit(args.after))
        if changed is None:
            print("yes")
            return 0
        print("yes" if changed_inputs(changed, dockerfile_at(args.after, args.directory), args.directory) else "no")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as why:
        print(f"::error::{why}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
