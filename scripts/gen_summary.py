#!/usr/bin/env python3
"""Generate mdBook SUMMARY.md for an assembled `src/` tree.

The spec is authored as numbered top-level directories. The docs workflow copies
them into `src/` and runs this to emit `src/SUMMARY.md`, so the nav stays in sync
with the files rather than being hand-maintained (Q-R58).

Usage: gen_summary.py <src-dir>
"""
from __future__ import annotations
import pathlib, re, sys

SECTION_ORDER = ["00-overview", "10-functional", "20-architecture",
                 "30-repos", "40-quality", "50-governance", "60-brand",
                 "70-operations", "90-appendix"]


def title_of(p: pathlib.Path) -> str:
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#\s+(.*)", line.strip())
        if m:
            return re.sub(r"[`*]", "", m.group(1).strip())
    return p.stem


def main() -> None:
    src = pathlib.Path(sys.argv[1])
    lines = ["# Summary", ""]
    root_readme = src / "README.md"
    if root_readme.exists():
        lines += [f"[lemonfiber](README.md)", ""]
    for name in SECTION_ORDER:
        sec = src / name
        if not sec.is_dir():
            continue
        readme = sec / "README.md"
        if readme.exists():
            lines.append(f"- [{title_of(readme)}]({name}/README.md)")
        for p in sorted(sec.rglob("*.md")):
            if p.name in ("README.md", "SUMMARY.md"):
                continue
            depth = len(p.relative_to(sec).parts)
            indent = "  " * depth
            lines.append(f"{indent}- [{title_of(p)}]({p.relative_to(src)})")
    (src / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {src / 'SUMMARY.md'}")


if __name__ == "__main__":
    main()
