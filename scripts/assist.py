#!/usr/bin/env python3
"""The advice `explain.yml` adds to a pull request: which citation to use, where
a mirrored page is edited, and which cited goals the tracker has not caught up
with (GOV-R33).

Each answer is a static rule over what the pull request touches and says; none
reads its code. Each prints its advice to standard output, and nothing where
none is owed, so the caller removes an explainer that has stopped being true.

  citation  A first-time contributor's pull request with no `Spec:` line is told
            which identifier fits: `GOV-R40` for a proposal, `GOV-R12` for a fix
            to prose.
  mirrors   A first-time contributor editing a page a site mirrors is told the
            repository and the file to edit instead, from the site's
            `mirrors.json`.
  status    A pull request citing a version's goal, in a repository whose
            tracker it does not touch, is told each goal's state in the tracker
            (OPS-R74).

Usage:
  assist.py citation --paths paths.txt --text text.txt --association A
  assist.py mirrors  --paths paths.txt --mirrors mirrors.json --association A
  assist.py status   --paths paths.txt --text text.txt --spec <spec root>
                     --repo-root <checkout> --repo <name>

`--paths` is the files the pull request changes, one to a line; `--text` its body
and commit messages. Exit 0 having answered; 2 where an input cannot be read.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import status_check
from paths import within_cwd
from patterns import SPEC_TRAILER
from spec_check import cited_ids

#: The associations the forge gives an author with no merged pull request here.
FIRST_TIME = ("FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER")
#: Where a proposal is added, in the specification.
PROPOSALS = "10-functional/proposals/"
#: What a proposal cites: the RFC process.
PROPOSAL_CITE = "GOV-R40"
#: What a fix to prose cites: routine maintenance.
PROSE_CITE = "GOV-R12"
#: Prose, by its extension.
PROSE = (".md", ".mdx")
#: Where a site keeps the routes `mirrors.json` names, from its root.
CONTENT = "src/content/docs"


def lines(path: str) -> list[str]:
    """The non-empty lines of a file named on the command line."""
    return [line for line in within_cwd(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def citation(paths: list[str], text: str, association: str) -> str:
    """Which identifier to cite, or nothing."""
    if association not in FIRST_TIME or SPEC_TRAILER.search(text) or not paths:
        return ""
    if any(path.startswith(PROPOSALS) for path in paths):
        return (f"This adds a proposal, so it cites the RFC process: add `Spec: {PROPOSAL_CITE}` "
                "on its own line to the pull request's description or a commit.")
    if all(path.endswith(PROSE) for path in paths):
        return ("This changes prose only. Where it fixes wording and changes no rule, it is routine "
                f"maintenance: add `Spec: {PROSE_CITE}` on its own line to the pull request's "
                "description or a commit. Where it changes what a requirement says, cite that one.")
    return ""


def upstream(path: str, mirrors: list[dict]) -> str | None:
    """The repository and file a mirrored path is rendered from, or None."""
    for mirror in mirrors:
        route = f"{CONTENT}/{mirror['route']}"
        if path == route or path.startswith(f"{route}/"):
            rest = path[len(route):]
            return f"{mirror['remote']}/blob/{mirror['branch']}/{mirror['path']}{rest}"
    return None


def mirrored(paths: list[str], mirrors: list[dict], association: str) -> str:
    """Where to edit each mirrored page instead, or nothing."""
    if association not in FIRST_TIME:
        return ""
    found = [(path, source) for path in paths if (source := upstream(path, mirrors))]
    if not found:
        return ""
    listed = [f"- `{path}` is rendered from {source}" for path, source in found]
    lead = ("This site mirrors these pages from the repositories that own them, so an "
            "edit here is overwritten by the next pin bump. Edit them there instead:")
    return "\n".join([lead, "", *listed])


def touches_tracker(paths: list[str]) -> bool:
    """Whether the pull request changes the repository's tracker."""
    return any(path == status_check.FILE or path.startswith(f"{status_check.DIRECTORY}/")
               for path in paths)


def reminder(paths: list[str], text: str, spec: pathlib.Path, root: pathlib.Path, repo: str) -> str:
    """Each cited goal and its state in the tracker, or nothing."""
    if repo not in status_check.searched(spec) or touches_tracker(paths):
        return ""
    goals = sorted(cited_ids(text) & status_check.locked(spec))
    if not goals:
        return ""
    rows = {row.id: row.state for row in status_check.load(root, repo) or []}
    table = [f"| `{goal}` | {rows.get(goal, 'not recorded')} |" for goal in goals]
    lead = ("This cites a version's goals and leaves the tracker as it was. Where it "
            "finishes or advances one, record it in the same pull request, with "
            "`lfdev status <id> <state>` or by editing the row (OPS-R74):")
    return "\n".join([lead, "", "| Goal | In the tracker |", "|---|---|", *table])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    asked = parser.add_subparsers(dest="rule", required=True)
    for rule in ("citation", "mirrors", "status"):
        sub = asked.add_parser(rule)
        sub.add_argument("--paths", required=True)
        if rule != "mirrors":
            sub.add_argument("--text", required=True)
        if rule != "status":
            sub.add_argument("--association", required=True)
    asked.choices["mirrors"].add_argument("--mirrors", required=True)
    for name in ("--spec", "--repo-root", "--repo"):
        asked.choices["status"].add_argument(name, required=True)
    args = parser.parse_args()
    try:
        paths = lines(args.paths)
        if args.rule == "mirrors":
            listed = json.loads(within_cwd(args.mirrors).read_text(encoding="utf-8"))["mirrors"]
            said = mirrored(paths, listed, args.association)
        else:
            text = within_cwd(args.text).read_text(encoding="utf-8")
            said = (citation(paths, text, args.association) if args.rule == "citation" else
                    reminder(paths, text, within_cwd(args.spec), within_cwd(args.repo_root), args.repo))
    except (OSError, ValueError, KeyError, TypeError, status_check.Unreadable) as broken:
        print(f"::error::{broken}", file=sys.stderr)
        return 2
    if said:
        print(said)
    return 0


if __name__ == "__main__":
    sys.exit(main())
