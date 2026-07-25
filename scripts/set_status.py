#!/usr/bin/env python3
"""Record a version manifest's transition — OPS-R32, OPS-R35.

Rewrites the `status` line, and at release appends the embedded `[pins]`. Kept to
a line edit rather than a re-serialise so the file's comments and layout survive.

Usage:
  set_status.py --manifest <versions/X.toml> --status <state> [--pin name=sha ...]
Exit 0 = written, 1 = the manifest wasn't shaped as expected.
"""
from __future__ import annotations
import argparse, re, sys, pathlib

STATES = {"planned", "staged", "releasable", "released", "yanked"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--status", required=True, choices=sorted(STATES))
    ap.add_argument("--pin", action="append", default=[], metavar="name=sha")
    a = ap.parse_args()

    path = pathlib.Path(a.manifest)
    if not path.is_file():
        print(f"::error::manifest not found: {path}")
        return 1
    text = path.read_text(encoding="utf-8")

    text, n = re.subn(r"(?m)^status\s*=.*$", f'status  = "{a.status}"', text)
    if n != 1:
        print(f"::error::expected exactly one status line in {path}, found {n}")
        return 1

    if a.pin:
        pairs = []
        for spec in a.pin:
            if "=" not in spec:
                print(f"::error::--pin wants name=sha, got {spec!r}")
                return 1
            name, _, sha = spec.partition("=")
            pairs.append(f'{name} = "{sha}"')
        # Replace any existing [pins] block, else append one.
        block = "[pins]\n" + "\n".join(pairs) + "\n"
        if re.search(r"(?m)^\[pins\]\s*$", text):
            text = re.sub(r"(?ms)^\[pins\].*?(?=^\[|\Z)", block, text)
        else:
            text = text.rstrip() + "\n\n" + block

    path.write_text(text, encoding="utf-8")
    print(f"{path.name}: status={a.status}" + (f", pins={len(a.pin)}" if a.pin else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
