#!/usr/bin/env python3
"""Compute a version manifest's transition — OPS-R32, OPS-R35.

Reads the manifest for a version, rewrites its `status` line, and at release
appends the embedded `[pins]`, then writes the result to **stdout** — the caller
redirects it back to the file. Emitting rather than writing in place keeps the
edit a line rewrite (comments and layout survive) and keeps any filesystem write
out of this script. The manifest path is built from a validated version and a
constant directory, so no free-form input is dereferenced.

Usage:
  set_status.py --version X.Y.Z --status <state> [--pin name=sha ...] > <manifest>
Exit 0 = emitted, 1 = the manifest is missing or misshapen, 2 = usage.
"""
from __future__ import annotations
import argparse, re, sys, pathlib

STATES = {"planned", "staged", "in_progress", "releasable", "released", "yanked"}
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
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
    ap.add_argument("--pin", action="append", default=[], metavar="name=sha")
    a = ap.parse_args()

    path = manifest_for(a.version)
    if not path.is_file():
        print(f"::error::no manifest at {path}", file=sys.stderr)
        return 1
    text, n = re.subn(r"(?m)^status\s*=.*$", f'status  = "{a.status}"',
                      path.read_text(encoding="utf-8"))
    if n != 1:
        print(f"::error::expected exactly one status line in {path}, found {n}", file=sys.stderr)
        return 1
    if a.pin:
        text = with_pins(text, parse_pins(a.pin))

    sys.stdout.write(text)
    print(f"{path.name}: status={a.status}" + (f", pins={len(a.pin)}" if a.pin else ""),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
