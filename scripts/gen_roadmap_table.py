#!/usr/bin/env python3
"""Rewrite the roadmap's version table from the manifests that define it.

The table used to be prose maintained beside the manifests, and it drifted:
after the train was renumbered it still named versions that no longer existed.
Anything a manifest already knows — the epoch, the milestone, what it delivers,
where it stands — is read from there, so the two cannot disagree again.
"""

import pathlib
import re
import tomllib

VERSIONS = pathlib.Path("70-operations/versions")
ROADMAP = pathlib.Path("00-overview/roadmap.md")
SHOWN = {
    "released": "Released",
    "releasable": "Releasable",
    "in_progress": "In progress",
    "staged": "Staged",
    "planned": "Planned",
}


def rows() -> list[str]:
    out = ["| Version | Epoch | Milestone | Delivers | Status |",
           "|---------|-------|-----------|----------|--------|"]
    manifests = sorted(
        (p for p in VERSIONS.glob("*.toml") if p.stem != "TEMPLATE"),
        key=lambda p: [int(part) for part in p.stem.split(".")],
    )
    for path in manifests:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        status = data.get("status", "planned")
        out.append(
            f"| `{data['version']}` | {data.get('epoch', '')} | "
            f"{data.get('milestone', '')} | {data.get('delivers', '')} | "
            f"{SHOWN.get(status, status)} |"
        )
    return out


def main() -> None:
    text = ROADMAP.read_text(encoding="utf-8")
    # The header row and every row under it — consecutive lines that start with a
    # pipe. Written as "the header, then more table lines" rather than "anything
    # up to a blank line", which reads as a puzzle and behaves like one.
    table = re.compile(r"^\| Version \| Epoch \|.*(?:\n\|.*)*", re.M)
    if not table.search(text):
        raise SystemExit("::error::no version table found in the roadmap")
    ROADMAP.write_text(table.sub("\n".join(rows()), text, count=1), encoding="utf-8")
    print(f"roadmap: version table regenerated from {len(rows()) - 2} manifests")


if __name__ == "__main__":
    main()
