#!/usr/bin/env python3
"""The community is addressed by name, not by invite code (OPS-R56).

An invite code can be revoked, and every published link carrying it dies at once,
so every tracked file addresses the community as https://discord.nightworks.io.
Every tracked text file is searched, with `git grep`, for a Discord invite link.

The pattern escapes its dots, so this file does not match its own text.

Usage, from the root of the repository being checked::

    check_invite.py --root .

Exit 0 = no tracked file carries an invite link, 1 = at least one does, or the
tree could not be searched.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

#: A Discord invite link, in either of the forms Discord hands out.
INVITE = r"discord\.gg/|discord(app)?\.com/invite/"

#: Where the community is addressed instead.
COMMUNITY = "https://discord.nightworks.io"


def found(root: pathlib.Path) -> list[str] | None:
    """Every `path:line:text` an invite link is on, or None where git could not search."""
    searched = subprocess.run(
        ["git", "-C", str(root), "grep", "-nIE", INVITE, "--", "."],
        capture_output=True,
        text=True,
        check=False,
    )
    if searched.returncode == 1:
        return []
    if searched.returncode != 0:
        return None
    return searched.stdout.splitlines()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    args = parser.parse_args(argv)
    hits = found(args.root)
    if hits is None:
        print("::error::git grep could not search the tracked files, so no invite code was looked for.")
        return 1
    for hit in hits:
        print(hit)
    if hits:
        print(
            f"::error::Address the community as {COMMUNITY} (OPS-R56). An invite code can be revoked, "
            "and every published link carrying it dies at once."
        )
        return 1
    print("no invite codes in tracked files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
