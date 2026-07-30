#!/usr/bin/env python3
"""Strip leading YAML frontmatter from the assembled docs tree before mdBook.

Feature docs carry frontmatter (the machine-readable metadata that tools and the
board read); mdBook would render it as raw text, so the assembled ``src/`` tree
is cleaned first. The root is fixed to ``src/`` on purpose — the docs pipeline
always assembles there — so no path is constructed from external input. Idempotent,
and files without frontmatter are left untouched.
"""
import pathlib

# Fixed root: the docs pipeline assembles the site into ./src before building.
SRC = pathlib.Path("src")


def strip_tree(root: pathlib.Path) -> int:
    cleaned = 0
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        end = text.find("\n---\n", 4)
        if end == -1:
            continue
        path.write_text(text[end + 5:].lstrip("\n"), encoding="utf-8")
        cleaned += 1
    return cleaned


if __name__ == "__main__":
    print(f"strip_frontmatter: cleaned {strip_tree(SRC)} file(s)")
