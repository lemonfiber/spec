#!/usr/bin/env python3
"""Move the pins the core's substitute proofs run at — F14-R14, OPS-R87.

`substitutes.toml` in the core names, for each arm of the proof, a first-party plugin's
repository and the commit it is proved at. This asks each repository what its default
branch names now, rewrites each arm's `revision` in place, leaving every comment and
every other line as it is, and writes the commit message the rolling pull request takes.

    substitute_pin.py apply --pins <substitutes.toml> --message <file>

Prints `moved=yes` or `moved=no`. Refuses, naming what, and writes nothing:

- a file that is not TOML, or of a schema other than the one this reads;
- an arm whose origin is not a repository of a first-party plugin of this organisation;
- an arm whose `revision` line this cannot find;
- a repository that does not answer, or answers something other than a full commit.

The pins and the message are paths under the working directory, read and written as
plain files, never through a link; any other path is refused.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib

import paths

#: The schema this reads.
SCHEMA = 1
#: An origin it asks: a first-party plugin's repository, and nothing else.
ORIGIN = re.compile(r"\Ahttps://github\.com/lemonfiber/plugin-[a-z0-9]+(-[a-z0-9]+)*\Z")
#: A commit as git names it in full.
COMMIT = re.compile(r"\A[0-9a-f]{40}\Z")
#: A `revision` line, with what it holds and anything after it.
REVISION = re.compile(r'\A(?P<key>revision\s*=\s*)"[^"]*"(?P<rest>.*)\Z')
#: The most of the pins this reads.
LIMIT = 1 << 20
#: How long a repository is given to answer, in seconds.
PATIENCE = 60
#: What the commit and the pull request cite.
CITED = "Spec: F14-R14, OPS-R87"


class Refused(Exception):
    """What was asked cannot be pinned, and why."""


def arms(text: str) -> list[dict]:
    """Each arm the pins declare, held to what this reads."""
    try:
        pins = tomllib.loads(text)
    except tomllib.TOMLDecodeError as why:
        raise Refused(f"the pins are not TOML: {why}") from why
    if pins.get("schema") != SCHEMA:
        raise Refused(f"the pins are of schema {pins.get('schema')!r}, and this reads {SCHEMA}")
    declared = pins.get("substitute", [])
    for arm in declared:
        if not ORIGIN.match(str(arm.get("origin"))):
            raise Refused(f"{arm.get('arm')!r}: {arm.get('origin')!r} is not a first-party plugin's repository")
    return declared


def head_of(origin: str) -> str:
    """The commit `origin`'s default branch names now."""
    try:
        asked = subprocess.run(
            ["git", "ls-remote", "--", origin, "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=PATIENCE,
        )
    except subprocess.TimeoutExpired as why:
        raise Refused(f"{origin} did not answer within {PATIENCE} seconds") from why
    if asked.returncode != 0:
        raise Refused(f"{origin} did not answer: {asked.stderr.strip()}")
    commit = asked.stdout.split("\t", 1)[0].strip()
    if not COMMIT.match(commit):
        raise Refused(f"{origin} names no commit: {asked.stdout.strip()!r}")
    return commit


def moved(text: str, declared: list[dict], heads: dict[str, str]) -> str:
    """`text` with the `revision` of each arm of `declared` at its origin's commit."""
    lines = text.split("\n")
    tables = [index for index, line in enumerate(lines) if line.strip() == "[[substitute]]"]
    for arm, start, end in zip(declared, tables, [*tables[1:], len(lines)], strict=True):
        found = [at for at in range(start, end) if REVISION.match(lines[at])]
        if len(found) != 1:
            raise Refused(f"{arm.get('arm')!r} holds {len(found)} revision lines, and one is moved")
        line = REVISION.match(lines[found[0]])
        lines[found[0]] = f'{line.group("key")}"{heads[arm["origin"]]}"{line.group("rest")}'
    return "\n".join(lines)


def message(before: list[dict], heads: dict[str, str]) -> str:
    """The commit message, and so the pull request's title and body."""
    changed = [arm for arm in before if heads[arm["origin"]] != arm.get("revision")]
    listed = "\n".join(
        f"- {arm['arm']}: {arm['origin'].rsplit('/', 1)[-1]} at {heads[arm['origin']]}" for arm in changed
    )
    return (
        "chore(substitutes): the substitutes at what their repositories name now\n\n"
        f"Each arm below is proved at its repository's main from here:\n\n{listed}\n\n"
        f"{CITED}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["apply"])
    for name in ("pins", "message"):
        parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args(argv)
    try:
        pins = paths.plain_relative(args.pins)
        message_file = paths.plain_relative(args.message)
        root = paths.plain_directory(".")
        before = paths.plain_read(root, pins, LIMIT).decode("utf-8")
        declared = arms(before)
        heads = {arm["origin"]: head_of(arm["origin"]) for arm in declared}
        after = moved(before, declared, heads)
    except (Refused, OSError, ValueError) as why:
        print(f"::error::{why}", file=sys.stderr)
        return 1
    if after == before:
        print("moved=no")
        return 0
    paths.plain_write(root, pins, after.encode("utf-8"))
    paths.plain_write(root, message_file, message(declared, heads).encode("utf-8"))
    print("moved=yes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
