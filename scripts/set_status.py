#!/usr/bin/env python3
"""Record a version manifest's transition — OPS-R32, OPS-R35.

Rewrites the `status` line, and at release appends the embedded `[pins]`. Kept to
a line edit rather than a re-serialise so the file's comments and layout survive.

Usage:
  set_status.py --manifest <versions/X.toml> --status <state> [--pin name=sha ...]
Exit 0 = written, 1 = the manifest wasn't shaped as expected, 2 = usage.
"""
from __future__ import annotations
import argparse, re, sys, pathlib

STATES = {"planned", "staged", "releasable", "released", "yanked"}


def within_cwd(raw: str) -> pathlib.Path:
    """Resolve a CLI-supplied path, refusing anything outside the working tree."""
    path = pathlib.Path(raw).resolve()
    if not path.is_relative_to(pathlib.Path.cwd().resolve()):
        print(f"::error::path escapes the working directory: {raw}")
        raise SystemExit(2)
    return path


def parse_pins(specs: list[str]) -> list[str]:
    pairs: list[str] = []
    for spec in specs:
        if "=" not in spec:
            print(f"::error::--pin wants name=sha, got {spec!r}")
            raise SystemExit(2)
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
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--status", required=True, choices=sorted(STATES))
    ap.add_argument("--pin", action="append", default=[], metavar="name=sha")
    a = ap.parse_args()

    path = within_cwd(a.manifest)
    text, n = re.subn(r"(?m)^status\s*=.*$", f'status  = "{a.status}"',
                      path.read_text(encoding="utf-8"))
    if n != 1:
        print(f"::error::expected exactly one status line in {path}, found {n}")
        return 1
    if a.pin:
        text = with_pins(text, parse_pins(a.pin))

    path.write_text(text, encoding="utf-8")
    print(f"{path.name}: status={a.status}" + (f", pins={len(a.pin)}" if a.pin else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
