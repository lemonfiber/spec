#!/usr/bin/env python3
"""Compute a version manifest's transition — OPS-R32, OPS-R35, OPS-R57.

Reads the manifest for a version, rewrites its `status` line, and at release
stamps `released_on` and appends the embedded `[pins]`, then writes the result to
**stdout** — the caller redirects it back to the file. Emitting rather than
writing in place keeps the edit a line rewrite (comments and layout survive) and
keeps any filesystem write out of this script. The manifest path is built from a
validated version and a constant directory, so no free-form input is
dereferenced.

A version's goals do not always ship under that version's own tag. A minor whose
release run fails part-way is finished by a patch, and the patch is the artefact
people actually get — so `--released-as` records which tag carried the goals this
manifest locked. There is no manifest per patch: a patch delivers no goals of its
own, and one would be a version the train has to walk past.

Usage:
  set_status.py --version X.Y.Z --status <state> [--released-on YYYY-MM-DD]
                [--released-as X.Y.Z] [--pin name=sha ...] > <manifest>
Exit 0 = emitted, 1 = the manifest is missing or misshapen, 2 = usage.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

from patterns import VERSION as VERSION_RE

STATES = {"planned", "staged", "in_progress", "releasable", "released", "yanked"}
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


def stamped(text: str, key: str, value: str, beneath: str) -> str:
    """Write `key = "value"` under an existing line, replacing one already there.

    Placed beneath a named line rather than appended, so it stays above the
    `[pins]` table a release also writes — a scalar under a table header belongs
    to the table, and readers that parse by line would file it as a pin.

    One function for both scalars a release stamps, because the placement rule is
    the thing that is easy to get wrong and there is no reason for two copies of
    it to be able to disagree.
    """
    line = f'{key} = "{value}"'
    text, n = re.subn(rf"(?m)^{key}\s*=.*$", line, text)
    if n:
        return text
    return re.sub(rf"(?m)^({beneath}\s*=.*)$", lambda m: f"{m.group(1)}\n{line}",
                  text, count=1)


def with_released_on(text: str, date: str) -> str:
    """Stamp the release date under `status`, replacing one already there."""
    if not DATE_RE.match(date):
        sys.exit(f"::error::--released-on wants YYYY-MM-DD, got {date!r}")
    return stamped(text, "released_on", date, "status")


def with_released_as(text: str, tag: str) -> str:
    """Stamp the tag the goals actually went out under, beneath the date.

    Beneath the date where there is one, so the three lines read in the order the
    events happened: what state this is in, when it went out, and what it went out
    as. A manifest carrying no date is one being corrected by hand, and the tag
    still belongs under `status` rather than at the end of the goals.
    """
    if not VERSION_RE.match(tag):
        sys.exit(f"::error::--released-as wants X.Y.Z, got {tag!r}")
    dated = re.search(r"(?m)^released_on\s*=", text)
    return stamped(text, "released_as", tag, "released_on" if dated else "status")


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
    ap.add_argument("--released-as", metavar="X.Y.Z")
    ap.add_argument("--pin", action="append", default=[], metavar="name=sha")
    a = ap.parse_args()

    if a.released_on and a.status != "released":
        sys.exit(f"::error::--released-on belongs to a released manifest, not {a.status!r}")
    if a.released_as and a.status != "released":
        sys.exit(f"::error::--released-as belongs to a released manifest, not {a.status!r}")
    # A manifest whose goals went out under its own tag says so by being that
    # version. Stamping the name twice would read as though something had been
    # decided, and the caller that passed it computed the wrong tag.
    if a.released_as == a.version:
        sys.exit(f"::error::--released-as {a.version} is this manifest's own version")

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
    if a.released_as:
        text = with_released_as(text, a.released_as)
    if a.pin:
        text = with_pins(text, parse_pins(a.pin))

    sys.stdout.write(text)
    print(f"{path.name}: status={a.status}"
          + (f", released_on={a.released_on}" if a.released_on else "")
          + (f", released_as={a.released_as}" if a.released_as else "")
          + (f", pins={len(a.pin)}" if a.pin else ""),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
