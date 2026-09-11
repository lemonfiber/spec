#!/usr/bin/env python3
"""Spec-side integrity checks. Run in CI on the spec repo itself (GOV-R11).

Verifies:
  - every cited requirement/ADR identifier resolves to a definition
  - no requirement ID is defined twice (IDs are permanent and unique, GOV-R8)
  - every internal Markdown link resolves to a real file
  - the counts this repository's own prose states match what it contains

Exit 0 = clean, 1 = problems found.
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

from patterns import ADR_CITE, ADR_FILE, REQ_DEF
from patterns import CITE as REQ_CITE

ROOT = pathlib.Path(__file__).resolve().parent.parent

LINK = re.compile(r"\[[^\]]*\]\((?!https?://|mailto:)([^)#]+)(?:#[^)]*)?\)")


def md_files():
    return [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]


def defined_reqs():
    defined = collections.Counter()
    for p in md_files():
        for m in REQ_DEF.findall(p.read_text(encoding="utf-8")):
            defined[m] += 1
    return defined


def defined_adrs():
    dec = ROOT / "00-overview" / "decisions"
    adrs = set()
    if dec.is_dir():
        for f in dec.iterdir():
            m = ADR_FILE.match(f.name)
            if m:
                adrs.add(int(m.group(1)))
    return adrs


def undefined_citations(defset, adrs):
    problems = []
    for p in md_files():
        text = p.read_text(encoding="utf-8")
        # Only report the first stray citation per file; the rest is noise.
        for rid in REQ_CITE.findall(text):
            if rid not in defset:
                problems.append(f"{p.relative_to(ROOT)}: cites undefined {rid}")
                break
        for a in ADR_CITE.findall(text):
            if int(a) not in adrs:
                problems.append(f"{p.relative_to(ROOT)}: cites undefined ADR-{a}")
                break
    return problems


def check_ids():
    defined = defined_reqs()
    problems = [f"duplicate requirement id defined {n}x: {i}"
                for i, n in sorted(defined.items()) if n > 1]
    problems += undefined_citations(set(defined), defined_adrs())
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


#: Prose that states a number about this repository, and how to count the real
#: one. The documentation site guards its own transcriptions of these; nothing
#: guarded the spec's own, so its README drifted to a feature count nine short
#: and an ADR count five short.
def stated_counts() -> list[str]:
    """Numbers the repository states about itself that no longer match it."""
    index = ROOT / "10-functional" / "features" / "index.json"
    if not index.is_file():
        return [f"{index.relative_to(ROOT)} is missing, so no stated count can be checked"]

    counts = json.loads(index.read_text(encoding="utf-8"))["counts"]
    features = int(counts["features"])
    adrs = len([p for p in (ROOT / "00-overview" / "decisions").glob("*.md")
                if ADR_FILE.match(p.name)])

    expected = {
        r"(\d+)-feature catalogue": (features, "features"),
        r"(\d+) ADRs": (adrs, "architecture decision records"),
    }

    faults = []
    for path in md_files():
        text = path.read_text(encoding="utf-8")
        for pattern, (actual, what) in expected.items():
            for found in re.finditer(pattern, text):
                stated = int(found.group(1))
                if stated != actual:
                    line = text[: found.start()].count("\n") + 1
                    faults.append(
                        f"{path.relative_to(ROOT)}:{line}: says {stated} "
                        f"{what} where this repository has {actual}"
                    )
    return faults


def main() -> int:
    problems = []
    # De-dup the "cites undefined" one-per-file noise into unique messages.
    seen = set()
    for msg in check_ids() + check_links() + stated_counts():
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
