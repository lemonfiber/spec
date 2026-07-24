#!/usr/bin/env python3
"""Build a PR comment linking each cited spec identifier to its defining file.

Companion to spec_check.py: spec-check *enforces* that citations exist; this
*surfaces* them as clickable links (with the requirement text) for a sticky PR
comment that the workflow updates in place on every push. See 50-governance/.
Any change to this script cites GOV-R32.

Usage:
  spec_refs.py --spec-dir <spec checkout> --text-file <PR body+commits> \
               --spec-url https://github.com/lemonfiber/spec/blob/main
Prints the comment markdown (with a stable marker) to stdout.
"""
from __future__ import annotations
import argparse, re, sys, pathlib

# A requirement is defined by a table row `| **ID** | text |`; capture the text.
REQ_DEF_ROW = re.compile(r"^\|\s*\*\*([A-Z]+[0-9]*-R[0-9]+)\*\*\s*\|\s*(.*?)\s*\|", re.M)
ADR_FILE = re.compile(r"^0*(\d{3,4})-.*\.md$")
CITE_ANY = re.compile(r"\b([A-Z]+[0-9]*-R[0-9]+|ADR-\d{3,4})\b")
SPEC_TRAILER = re.compile(r"^\s*Spec:\s*(.+)$", re.M | re.I)
MARKER = "<!-- spec-references -->"


def index(spec_dir: pathlib.Path) -> dict[str, tuple[str, str]]:
    """Map every defined identifier to (relative_path, description)."""
    idx: dict[str, tuple[str, str]] = {}
    for p in spec_dir.rglob("*.md"):
        if ".git" in p.parts:
            continue
        rel = p.relative_to(spec_dir).as_posix()
        for m in REQ_DEF_ROW.finditer(p.read_text(encoding="utf-8", errors="ignore")):
            idx.setdefault(m.group(1), (rel, m.group(2).strip()))
    dec = spec_dir / "00-overview" / "decisions"
    if dec.is_dir():
        for f in sorted(dec.iterdir()):
            m = ADR_FILE.match(f.name)
            if not m:
                continue
            title = ""
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                hm = re.match(r"^#\s+(.*)", line)
                if hm:
                    title = hm.group(1).strip()
                    break
            idx[f"ADR-{int(m.group(1)):04d}"] = (f"00-overview/decisions/{f.name}", title)
    return idx


def cited(text: str) -> list[str]:
    ids: list[str] = []
    for line in SPEC_TRAILER.findall(text):
        for i in CITE_ANY.findall(line):
            if i not in ids:
                ids.append(i)
    return ids


def build(ids: list[str], idx: dict[str, tuple[str, str]], base_url: str) -> str:
    out = [MARKER, "### 📎 Spec references", ""]
    if not ids:
        out.append(
            "_No `Spec:` citation found yet. Add one to a commit trailer **and** the "
            "PR body — see the [contributing guide]"
            "(https://github.com/lemonfiber/spec/blob/main/50-governance/contributing.md)._"
        )
    else:
        out += ["This PR cites the following spec identifiers:", ""]
        for i in ids:
            if i in idx:
                rel, desc = idx[i]
                desc = (desc[:137] + "…") if len(desc) > 140 else (desc or "—")
                out.append(f"- [`{i}`]({base_url}/{rel}) — {desc}")
            else:
                out.append(f"- `{i}` — ⚠️ not found on spec@main (`spec-check` will flag this)")
    out += ["", "<sub>Updated automatically on each push.</sub>"]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", required=True)
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--spec-url", required=True)
    a = ap.parse_args()

    cwd = pathlib.Path.cwd().resolve()
    text_path = pathlib.Path(a.text_file).resolve()
    if not text_path.is_relative_to(cwd):
        print(MARKER + "\n\n_spec-references: text path outside the workspace._")
        return 0
    text = text_path.read_text(encoding="utf-8", errors="ignore")
    print(build(cited(text), index(pathlib.Path(a.spec_dir)), a.spec_url.rstrip("/")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
