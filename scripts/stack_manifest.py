#!/usr/bin/env python3
"""The stack manifest read the way lemonfiber reads it (ARCH-R171).

The stack repository's `stack.toml` is a root: its `include` list names a file
per service, `services/<id>.toml`, and that list alone decides what the stack
holds. lemonfiber joins the root and each named file, in the list's order, into
the manifest it reads (`lemonfiber_manifest::assemble` in the core, `joined` in
the stack's own `scripts/stack_manifest.py`). This is the same join for the
scripts here that read a stack.

A manifest from before the split declares its services inline, as `[[service]]`
tables in the one file, and names no `include`. It is read as it is.
"""
from __future__ import annotations

import pathlib
import re
import tomllib
from collections.abc import Callable

#: The only shape an `include` entry takes. Held before anything is read, so an
#: entry cannot name a file outside the stack's own `services/` directory.
ENTRY = re.compile(r"\Aservices/[a-z0-9][a-z0-9-]*\.toml\Z")


def included(root: dict) -> list[str]:
    """The root's `include` entries, in order, or nothing for a flat manifest."""
    listed = root.get("include", [])
    return [str(entry) for entry in listed] if isinstance(listed, list) else []


def members(root: dict) -> int:
    """How many services the manifest holds: its `include` entries, which alone
    decide membership, or for a flat manifest its `[[service]]` tables."""
    return len(included(root)) or len(root.get("service", []))


def joined(root: str, read: Callable[[str], str | None]) -> tuple[str, list[str]]:
    """The root and each file it includes as one TOML text, and what could not be read.

    `read` answers an entry, a path relative to the stack's root, with that file's
    text, or None where there is no such file. An entry of another shape is never
    handed to it.
    """
    parts, unread = [root], []
    for entry in included(tomllib.loads(root)):
        text = read(entry) if ENTRY.match(entry) else None
        if text is None:
            unread.append(entry)
        else:
            parts.append(f"\n# {entry}\n{text}")
    return "".join(parts), unread


def on_disk(stack_dir: pathlib.Path) -> Callable[[str], str | None]:
    """A reader of the files beside a root on disk, for `joined`."""

    def read(entry: str) -> str | None:
        path = stack_dir / entry
        return path.read_text(encoding="utf-8") if path.is_file() else None

    return read
