#!/usr/bin/env python3
"""Render a release tracker issue body from gate JSON on stdin — OPS-R43.

Reads `gate.py --format json` and emits a goal checklist with a coverage count,
so the tracking issue is a live view of when the version can lock.
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    data = json.load(sys.stdin)
    goals = data["goals"]
    met = sum(1 for g in goals if g["cited"] and g["done"])
    lines = [f"## Release {data['version']} — {met}/{len(goals)} goals", ""]
    for g in goals:
        if g["cited"] and g["done"]:
            lines.append(f"- [x] `{g['id']}`")
        else:
            missing = ", ".join(m for m, ok in (("citation", g["cited"]), ("tracker ✅", g["done"])) if not ok)
            lines.append(f"- [ ] `{g['id']}` — missing {missing}")
    state = "✅ releasable" if data["releasable"] else "not yet releasable"
    lines += ["", f"_{state} — maintained by the release train (OPS-R43)._"]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
