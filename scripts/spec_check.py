#!/usr/bin/env python3
"""Governance gate: verify a PR cites spec identifiers that actually exist.

Canonical here in the spec repo; every implementation repo runs it via the
reusable workflow (.github/workflows/spec-check.yml). See 50-governance/.

Enforces:
  GOV-R2  a citation is present
  GOV-R3  every cited identifier exists on spec@main

Ordering (GOV-R4) — that a behavioural change's spec PR merged first — is not
machine-checked here yet; it is verified in review. Hardening this is tracked in
the spec repo, and any change to this script cites GOV-R11.

Usage:
  spec_check.py --spec-dir <path to spec checkout> --text-file <PR body+commits>
Exit 0 = pass, 1 = fail (with guidance), 2 = usage error.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

# Identifiers the spec defines.
REQ_DEF = re.compile(r"^\|\s*\*\*([A-Z]+\d*-R\d+)\*\*\s*\|", re.MULTILINE)
ADR_FILE = re.compile(r"^0*(\d{3,4})-.*\.md$")
CITE_ANY = re.compile(r"\b([A-Z]+\d*-R\d+|ADR-\d{3,4})\b")
SPEC_TRAILER = re.compile(r"^[ \t]*Spec:[ \t]*(\S.*)$", re.MULTILINE | re.IGNORECASE)


def defined_ids(spec_dir: pathlib.Path) -> set[str]:
    ids: set[str] = set()
    for p in spec_dir.rglob("*.md"):
        if ".git" in p.parts:
            continue
        ids.update(REQ_DEF.findall(p.read_text(encoding="utf-8", errors="ignore")))
    dec = spec_dir / "00-overview" / "decisions"
    if dec.is_dir():
        for f in dec.iterdir():
            m = ADR_FILE.match(f.name)
            if m:
                ids.add(f"ADR-{int(m.group(1)):04d}")
    return ids


def cited_ids(text: str) -> set[str]:
    ids: set[str] = set()
    for line in SPEC_TRAILER.findall(text):
        ids.update(CITE_ANY.findall(line))
    return ids


GUIDANCE = """
This change does not cite a spec identifier that exists on spec@main.

The lemonfiber spec is canonical: every change references something already in
https://github.com/lemonfiber/spec

Add a `Spec:` trailer to a commit AND the PR body, for example:

    Spec: B2-R1

  - Implementing something specified?  Cite the requirement.
  - Changing behaviour?  Open a spec PR first, then cite the new ID.
  - Routine maintenance (deps, formatting, CI)?  Cite GOV-R12.

Guide: https://github.com/lemonfiber/spec/blob/main/50-governance/contributing.md
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", required=True)
    ap.add_argument("--text-file", required=True)
    a = ap.parse_args()

    spec_dir = pathlib.Path(a.spec_dir)
    if not spec_dir.is_dir():
        print(f"::error::spec dir not found: {spec_dir}")
        return 2

    cwd = pathlib.Path.cwd().resolve()
    text_path = pathlib.Path(a.text_file).resolve()
    if not text_path.is_relative_to(cwd):
        print("::error::text-file must be within the working directory")
        return 2
    text = text_path.read_text(encoding="utf-8", errors="ignore")
    defined = defined_ids(spec_dir)
    if not defined:
        print("::error::no identifiers found in spec checkout — cannot verify")
        return 2

    cited = cited_ids(text)
    if not cited:
        print("::error::no `Spec:` citation found")
        print(GUIDANCE)
        return 1

    unknown = sorted(i for i in cited if i not in defined)
    if unknown:
        print(f"::error::cited identifiers do not exist on spec@main: {', '.join(unknown)}")
        print(GUIDANCE)
        return 1

    print(f"spec-check: OK — cites {', '.join(sorted(cited))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
