#!/usr/bin/env python3
"""Every submodule a `.gitmodules` declares, named as a manifest pins it — OPS-R35.

OPS-R35 asks execute to "record the embedded submodule pins in the manifest",
plural. `lemonfiber` embedded one submodule when `release-finalize` was written,
so the workflow named it — `assets/media-stack`, spelled out in a `gh api` path.
ADR-0012 added a second, `assets/web`, and the workflow went on recording the one
it knew: `0.10.0` shipped a manifest that pinned the stack and said nothing about
which build of the web app went out with it.

So the caller enumerates rather than names, and this is what it enumerates from.
Whatever the release tag's own `.gitmodules` declares is what the manifest
records, and the next submodule to be added is recorded by having been added.

A pin is named for the repository, not for the path it is mounted at. That is the
naming the manifests already use — `lemonfiber-media-stack`, not
`assets/media-stack` — and it is the name a reader needs in order to go and look
the commit up. It is the last segment of the submodule's URL with any `.git`
removed.

Only the parsing is here. Fetching the file and reading each path's commit are
the caller's, which keeps every request to the forge in the one place the
workflow already made them, and leaves this with nothing to hand a command and no
path to open.

Usage:
  gh api ... .gitmodules | submodule_pins.py

Reads a `.gitmodules` on stdin and prints `<name><TAB><path>` per declared
submodule, in declaration order. Exit 0 = printed, 1 = it declares nothing or a
stanza is missing half of itself, 2 = usage.
"""
from __future__ import annotations

import argparse
import re
import sys

# A `.gitmodules` stanza and the two settings that matter in it. Git writes the
# section name and the path identically today, but they are separate fields and
# only `path` is the tree entry, so the path is read rather than assumed.
#
# The value runs to the end of the line and is trimmed in code. A lazy `\S.*?`
# closed by `\s*$` says the same thing and backtracks super-linearly on a long
# line, and there is no reason for a parser to be able to.
SECTION = re.compile(r'^\s*\[submodule\s+"[^"]*"\]\s*$')
SETTING = re.compile(r"^\s*(?P<key>path|url)\s*=(?P<value>.*)$")


def named(url: str) -> str:
    """The repository a submodule URL points at, which is what a pin is called."""
    return url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")


def declared(gitmodules: str) -> list[tuple[str, str]]:
    """Every submodule the file declares, as (name, path), in declaration order."""
    stanzas: list[dict[str, str]] = []
    for line in gitmodules.splitlines():
        if SECTION.match(line):
            stanzas.append({})
            continue
        setting = SETTING.match(line)
        if setting and stanzas:
            stanzas[-1][setting["key"]] = setting["value"].strip()
    modules = []
    for stanza in stanzas:
        if not stanza.get("path") or not stanza.get("url"):
            sys.exit(f"::error::a submodule wants a path and a url, got {stanza!r}")
        modules.append((named(stanza["url"]), stanza["path"]))
    return modules


def main() -> int:
    argparse.ArgumentParser(
        description="Read a .gitmodules on stdin; print <name><TAB><path> per submodule.",
    ).parse_args()

    modules = declared(sys.stdin.read())
    # Recording no pins at all is the failure this exists to end, so it is said
    # here rather than left for a `while read` over an empty file to report
    # success for having done nothing.
    if not modules:
        print("::error::this .gitmodules declares no submodules", file=sys.stderr)
        return 1
    for name, where in modules:
        print(f"{name}\t{where}")
    print(f"{len(modules)} embedded submodules", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
