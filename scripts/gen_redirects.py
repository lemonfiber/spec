#!/usr/bin/env python3
"""Emit the redirect site that stands where the specification's book stood.

Every URL the mdBook published gets one page, which sends a reader to the same
document on docs.lemonfiber.app and tells a crawler that is where it lives now
(REPO-R53). GitHub Pages serves no 301, so a refresh and a canonical link are
what a static host can say; both are honoured, and the page also says it in
words for anyone whose browser does not follow the refresh.

Usage: gen_redirects.py <output directory>
"""
from __future__ import annotations

import html
import pathlib
import sys

SECTIONS = [
    "00-overview",
    "10-functional",
    "20-architecture",
    "30-repos",
    "40-quality",
    "50-governance",
    "60-brand",
    "70-operations",
    "90-appendix",
]

SITE = "https://docs.lemonfiber.app/spec/"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Moved — the lemonfiber specification</title>
<link rel="canonical" href="{target}">
<meta name="robots" content="noindex, follow">
<meta http-equiv="refresh" content="0; url={target}">
<style>
  body {{ margin: 0; padding: 3rem 1.5rem; font: 16px/1.6 system-ui, sans-serif; }}
  main {{ max-width: 34rem; margin: 0 auto; }}
</style>
</head>
<body>
<main>
<h1>The specification moved</h1>
<p>It is published at <a href="{target}">{shown}</a>, alongside the rest of the
documentation and in the same search index.</p>
</main>
</body>
</html>
"""


def route_of(relative: pathlib.PurePosixPath) -> str:
    """The path docs.lemonfiber.app serves for a specification file."""
    without = relative.with_suffix("")
    parts = [part for part in without.parts if part != "README"]
    return "/".join(part.lower() for part in parts)


def pages(root: pathlib.Path) -> dict[str, str]:
    """Every URL the book published, mapped to the route that replaced it."""
    found: dict[str, str] = {
        "index.html": "",
        "print.html": "",
    }
    for section in SECTIONS:
        directory = root / section
        if not directory.is_dir():
            continue
        for source in sorted(directory.rglob("*.md")):
            relative = pathlib.PurePosixPath(source.relative_to(root).as_posix())
            route = route_of(relative)
            if source.name == "README.md":
                found[f"{relative.parent}/index.html"] = route
            else:
                found[str(relative.with_suffix(".html"))] = route
    return found


def within(directory: pathlib.Path, name: str) -> pathlib.Path | None:
    """The path ``name`` names inside ``directory``, or None if it leaves it.

    Every name comes from this repository's own tree, so nothing should ever
    leave; a name that does is a fault worth stopping on rather than a file
    worth writing somewhere else.
    """
    root = directory.resolve()
    target = (root / name).resolve()
    return target if target.is_relative_to(root) else None


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: gen_redirects.py <output directory>", file=sys.stderr)
        return 2
    root = pathlib.Path(".").resolve()
    out = pathlib.Path(sys.argv[1])
    written = 0
    for name, route in pages(root).items():
        target = f"{SITE}{route}/" if route else SITE
        page = within(out, name)
        if page is None:
            print(f"::error::{name} would be written outside {out}", file=sys.stderr)
            return 1
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            PAGE.format(target=html.escape(target), shown=html.escape(target)),
            encoding="utf-8",
        )
        written += 1
    print(f"wrote {written} redirect pages to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
