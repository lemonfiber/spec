#!/usr/bin/env python3
"""Compute a version manifest's transition — OPS-R32, OPS-R35, OPS-R57.

Reads the manifest for a version, rewrites its `status` line, and at release
stamps `released_on` and appends the embedded `[pins]`, then writes the result to
**stdout** — the caller redirects it back to the file. Emitting rather than
writing in place keeps the edit a line rewrite (comments and layout survive) and
keeps any filesystem write out of this script. The manifest path is built from a
validated version and a constant directory, so no free-form input is
dereferenced.

Usage:
  set_status.py --version X.Y.Z --status <state> [--released-on YYYY-MM-DD]
                [--pin name=sha ...] > <manifest>
Exit 0 = emitted, 1 = the manifest is missing or misshapen, 2 = usage.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

STATES = {"planned", "staged", "in_progress", "releasable", "released", "yanked"}
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VERSIONS_DIR = pathlib.Path("70-operations/versions")


def manifest_for(version: str) -> pathlib.Path:
    """The manifest path for a validated version, built from a constant base."""
    if not VERSION_RE.match(version):
        sys.exit(f"::error::version must be X.Y.Z, got {version!r}")
    path = (VERSIONS_DIR / f"{version}.toml").resolve()
    if not path.is_relative_to(VERSIONS_DIR.resolve()):
        sys.exit(f"::error::path escapes {VERSIONS_DIR}")  # pragma: no cover
    return path


def parse_pins(specs: list[str]) -> list[str]:
    pairs: list[str] = []
    for spec in specs:
        if "=" not in spec:
            sys.exit(f"::error::--pin wants name=sha, got {spec!r}")
        name, _, sha = spec.partition("=")
        pairs.append(f'{name} = "{sha}"')
    return pairs


def with_released_on(text: str, date: str) -> str:
    """Stamp the release date under `status`, replacing one already there.

    Placed beneath `status` rather than appended, so it stays above the `[pins]`
    table a release also writes — a scalar under a table header belongs to the
    table, and readers that parse by line would file the date as a pin.
    """
    if not DATE_RE.match(date):
        sys.exit(f"::error::--released-on wants YYYY-MM-DD, got {date!r}")
    stamped = f'released_on = "{date}"'
    text, n = re.subn(r"(?m)^released_on\s*=.*$", stamped, text)
    if n:
        return text
    return re.sub(r"(?m)^(status\s*=.*)$", lambda m: f"{m.group(1)}\n{stamped}",
                  text, count=1)


def with_pins(text: str, pairs: list[str]) -> str:
    """Replace the trailing [pins] table (or append one)."""
    kept: list[str] = []
    for line in text.splitlines():
        if line.strip() == "[pins]":
            break
        kept.append(line)
    block = "[pins]\n" + "\n".join(pairs) + "\n"
    return "\n".join(kept).rstrip() + "\n\n" + block


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--status", required=True, choices=sorted(STATES))
    ap.add_argument("--released-on", metavar="YYYY-MM-DD")
    ap.add_argument("--pin", action="append", default=[], metavar="name=sha")
    a = ap.parse_args()

    if a.released_on and a.status != "released":
        sys.exit(f"::error::--released-on belongs to a released manifest, not {a.status!r}")

    path = manifest_for(a.version)
    if not path.is_file():
        print(f"::error::no manifest at {path}", file=sys.stderr)
        return 1
    text, n = re.subn(r"(?m)^status\s*=.*$", f'status  = "{a.status}"',
                      path.read_text(encoding="utf-8"))
    if n != 1:
        print(f"::error::expected exactly one status line in {path}, found {n}", file=sys.stderr)
        return 1
    if a.released_on:
        text = with_released_on(text, a.released_on)
    if a.pin:
        text = with_pins(text, parse_pins(a.pin))

    sys.stdout.write(text)
    print(f"{path.name}: status={a.status}"
          + (f", released_on={a.released_on}" if a.released_on else "")
          + (f", pins={len(a.pin)}" if a.pin else ""),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
