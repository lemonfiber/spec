#!/usr/bin/env python3
"""Spec-side integrity checks. Run in CI on the spec repo itself (GOV-R11).

Verifies:
  - every cited requirement/ADR identifier resolves to a definition
  - no requirement ID is defined twice (IDs are permanent and unique, GOV-R8)
  - every internal Markdown link resolves to a real file

Exit 0 = clean, 1 = problems found.
"""
from __future__ import annotations
import re, sys, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent

REQ_DEF = re.compile(r"^\|\s*\*\*([A-Z]+[0-9]*-R[0-9]+)\*\*\s*\|", re.M)
REQ_CITE = re.compile(r"\b([A-Z]+[0-9]*-R[0-9]+)\b")
ADR_FILE = re.compile(r"^0*(\d{3,4})-.*\.md$")
ADR_CITE = re.compile(r"\bADR-(\d{3,4})\b")
LINK = re.compile(r"\[[^\]]*\]\((?!https?://|mailto:)([^)#]+)(?:#[^)]*)?\)")


def md_files():
    return [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]


def check_ids():
    defined = collections.Counter()
    for p in md_files():
        for m in REQ_DEF.findall(p.read_text(encoding="utf-8")):
            defined[m] += 1
    dec = ROOT / "00-overview" / "decisions"
    adrs = set()
    if dec.is_dir():
        for f in dec.iterdir():
            m = ADR_FILE.match(f.name)
            if m:
                adrs.add(int(m.group(1)))
    problems = []
    dups = [i for i, n in defined.items() if n > 1]
    for d in sorted(dups):
        problems.append(f"duplicate requirement id defined {defined[d]}x: {d}")
    defset = set(defined)
    for p in md_files():
        text = p.read_text(encoding="utf-8")
        # Only treat as a citation outside its own definition table row.
        for rid in REQ_CITE.findall(text):
            if rid not in defset:
                problems.append(f"{p.relative_to(ROOT)}: cites undefined {rid}")
                break
        for a in ADR_CITE.findall(text):
            if int(a) not in adrs:
                problems.append(f"{p.relative_to(ROOT)}: cites undefined ADR-{a}")
                break
    return problems


def check_links():
    problems = []
    for p in md_files():
        for target in LINK.findall(p.read_text(encoding="utf-8")):
            target = target.strip()
            if not target or target.startswith(".docs/") or "/.docs/" in target:
                continue  # repo-local .docs live in cli, not here
            resolved = (p.parent / target).resolve()
            if not resolved.exists():
                problems.append(f"{p.relative_to(ROOT)}: broken link -> {target}")
    return problems


def main() -> int:
    problems = []
    # De-dup the "cites undefined" one-per-file noise into unique messages.
    seen = set()
    for msg in check_ids() + check_links():
        if msg not in seen:
            seen.add(msg)
            problems.append(msg)
    if problems:
        for m in problems:
            print(f"::error::{m}")
        print(f"\n{len(problems)} integrity problem(s).")
        return 1
    print("spec integrity: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
