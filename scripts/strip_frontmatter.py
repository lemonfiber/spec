#!/usr/bin/env python3
"""Strip leading YAML frontmatter from Markdown before the docs build.

Feature files carry frontmatter (the machine-readable metadata that tools and
the board read); mdBook would render it as raw text, so the assembled ``src/``
tree is cleaned first. Idempotent, and files without frontmatter are left
untouched. Usage: ``strip_frontmatter.py <dir>``.
"""
import sys
import pathlib

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "src")
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

print(f"strip_frontmatter: cleaned {cleaned} file(s)")
