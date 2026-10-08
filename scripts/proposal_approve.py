#!/usr/bin/env python3
"""Approve a proposal pull request — GOV-R41, GOV-R42, GOV-R43.

A maintainer approves a proposal by labelling its pull request
`proposal:approved`; the `proposal-approve` workflow verifies they may write and
runs this. It reads the one proposal the pull request adds, allocates the next
free identifiers with `next_id.py`, and moves the proposal into the
specification as Draft:

  * a proposal that amends a feature or a page appends one row per statement to
    that document's requirements table, each opening with `*Draft:*`, so the
    rest of an Accepted document stays as it was;
  * a proposal that amends nothing becomes a new feature in its area, at
    `status: draft`, listed on the catalogue's page.

The proposal file itself goes, because its text now lives where it belongs, and
the generated board and counts are rewritten. The change is committed, signed,
as the release App: onto the pull request's own branch where that branch is in
this repository, and otherwise onto a branch of its own with a pull request
crediting the author, after which the original is closed with a link to it.

What the proposal says is untrusted. It is read through the forge's API as data
from the pull request's head, held to the shape `integrity.py` checks before
anything is written, and written only as table rows and prose; nothing from it
reaches a shell, and every call to the forge takes its request as a file. A gap
names what the specification does not say and carries no statements, so it is
answered with a comment rather than identifiers.

Usage, from the root of a full-history checkout of spec's main, with REPO,
PR_NUMBER, PR_AUTHOR, PR_AUTHOR_ID, HEAD_REPO, HEAD_REF and HEAD_SHA
set and `gh` authenticated as the release App:
  proposal_approve.py
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import metafm
import next_id
from catalogue import FEATURES_README, features
from catalogue import areas as area_names
from integrity import PROPOSAL_SHAPES, PROPOSALS, proposal_faults, section
from patterns import REQ_DEF

#: One call to the forge's API through `gh`: its arguments and the request
#: body, then the JSON it answers with.
Api = Callable[[list[str], dict | None], Any]

#: The heading of a requirements table, by which the rows are appended to it.
TABLE_HEAD = re.compile(r"^\|\s*ID\s*\|\s*Requirement\s*\|\s*$")
#: Where the features live, by area directory.
FEATURES = pathlib.Path("10-functional/features")
#: What a new feature's audience is until its review says otherwise.
AUDIENCE = "both"
#: The marker an approved row carries until a pull request hardens it.
DRAFT = "*Draft:*"


class Refused(Exception):
    """The proposal cannot be approved as it stands; the message says why."""


@dataclass
class Plan:
    """What approval writes: whole files by path, and the paths it removes."""

    identifiers: list[str]
    where: str
    writes: dict[str, str] = field(default_factory=dict)
    removes: list[str] = field(default_factory=list)


def statements(text: str) -> list[str]:
    """The proposal's statements, one per bullet under `## Proposed behaviour`."""
    found = [line[2:].strip() for line in section(text, "Proposed behaviour").splitlines()
             if line.startswith("- ")]
    return [cell(line) for line in found if line]


def cell(text: str) -> str:
    """Text as one table cell, its pipes escaped."""
    return text.replace("|", r"\|")


def allocate(prefix: str, count: int, families: dict[str, dict[int, object]]) -> list[str]:
    """The next `count` free identifiers under one prefix, max + 1 and never reused."""
    start = max(families.get(prefix, {}) or [0]) + 1
    return [f"{prefix}-R{number}" for number in range(start, start + count)]


def appended(text: str, rows: list[str]) -> str:
    """The document with the rows added after the last row of its last
    requirements table."""
    lines = text.splitlines()
    heads = [at for at, line in enumerate(lines) if TABLE_HEAD.match(line)]
    if not heads:
        raise Refused("the document it amends has no requirements table (`| ID | Requirement |`)")
    last = heads[-1] + 1
    while last + 1 < len(lines) and lines[last + 1].startswith("|"):
        last += 1
    return "\n".join([*lines[: last + 1], *rows, *lines[last + 1:]]) + "\n"


def amendment(root: pathlib.Path, amends: str, said: list[str],
              families: dict[str, dict[int, object]]) -> Plan:
    """Rows appended, marked Draft, to the feature or page the proposal amends."""
    if re.fullmatch(r"[A-N]\d+", amends):
        found = sorted((root / FEATURES).glob(f"*/{amends.lower()}-*.md"))
        path, prefix = found[0], amends
    else:
        path = root / amends
        if path.suffix != ".md" or not path.resolve().is_relative_to(root.resolve()):
            raise Refused(f"{amends} is not a page of this specification")
        prefixes = {ident.rsplit("-R", 1)[0] for ident in REQ_DEF.findall(path.read_text("utf-8"))}
        if len(prefixes) != 1:
            raise Refused(f"{amends} defines {len(prefixes)} identifier prefixes, so which one a "
                          "new requirement takes is the maintainer's to say; name the feature")
        prefix = prefixes.pop()
    identifiers = allocate(prefix, len(said), families)
    rows = [f"| **{ident}** | {DRAFT} {text} |" for ident, text in zip(identifiers, said, strict=True)]
    relative = path.relative_to(root).as_posix()
    return Plan(identifiers, relative, {relative: appended(path.read_text("utf-8"), rows)})


def slug(title: str) -> str:
    """A file name's words, from a title."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48].rstrip("-") or "feature"


def next_feature(area: str, known: dict[str, dict], families: dict[str, dict[int, object]]) -> str:
    """The next free feature identifier in an area, counting the catalogue and
    every branch's requirements."""
    numbers = [int(ident[1:]) for ident in [*known, *families] if re.fullmatch(rf"{area}\d+", ident)]
    return f"{area}{max(numbers or [0]) + 1}"


def new_feature(root: pathlib.Path, front: dict, text: str, said: list[str],
                families: dict[str, dict[int, object]]) -> Plan:
    """A Draft feature in the proposal's area, and its row on the catalogue's page."""
    area, title = front["area"], str(front["title"])
    known = features()
    directory = next(pathlib.Path(fm["path"]).parent.name for fm in known.values() if fm["area"] == area)
    ident = next_feature(area, known, families)
    identifiers = [f"{ident}-R{number}" for number in range(1, len(said) + 1)]
    names = area_names((root / FEATURES_README).read_text("utf-8"))
    problem = section(text, "Problem") or title
    doc = "\n".join([
        "---", f"id: {ident}", f"title: {title}", "kind: feature", f"area: {area}",
        f"audience: {AUDIENCE}", "status: draft", "maturity: planned", "---", "",
        f"# {ident} — {title}", "",
        f"**Status:** Draft · **Audience:** Both · **Area:** {area} — {names.get(area, area)}", "",
        "---", "", "## Purpose", "", problem, "", "## Acceptance criteria", "",
        "| ID | Requirement |", "|----|-------------|",
        *[f"| **{i}** | {s} |" for i, s in zip(identifiers, said, strict=True)], "",
    ])
    relative = (FEATURES / directory / f"{ident.lower()}-{slug(title)}.md").as_posix()
    catalogue = (root / FEATURES_README).read_text("utf-8")
    listed = catalogue_row(catalogue, area, ident, f"{directory}/{pathlib.Path(relative).name}", title)
    return Plan(identifiers, relative, {relative: doc, FEATURES_README: listed})


def catalogue_row(page: str, area: str, ident: str, link: str, title: str) -> str:
    """The catalogue's page with the new feature listed in its area's table."""
    lines = page.splitlines()
    start = next((at for at, line in enumerate(lines) if line.startswith(f"## {area} — ")), None)
    if start is None:
        raise Refused(f"the catalogue's page has no section for area {area}")
    end = next((at for at in range(start + 1, len(lines)) if lines[at].startswith("## ")), len(lines))
    rows = [at for at in range(start, end) if lines[at].startswith("| [")]
    if not rows:
        raise Refused(f"the catalogue's page lists no feature under area {area} to list beside")
    lines.insert(rows[-1] + 1, f"| [{ident}]({link}) | {cell(title)} | Both |")
    return "\n".join(lines) + "\n"


def plan(root: pathlib.Path, name: str, text: str) -> Plan:
    """What approving one proposal writes, or why it cannot."""
    areas = set(area_names((root / FEATURES_README).read_text("utf-8")))
    with tempfile.TemporaryDirectory() as tmp:
        copy = pathlib.Path(tmp) / name
        copy.write_text(text, encoding="utf-8")
        faults = proposal_faults(copy, areas)
    if faults:
        raise Refused("the proposal is not in the shape the RFC process gives: " + "; ".join(faults))
    front = metafm.parse(text) or {}
    if front.get("kind") == "gap":
        raise Refused("a gap names what the specification does not say and carries no statement "
                      "to allocate an identifier to; it is answered by a proposal that does")
    said = statements(text)
    families = next_id.defined()
    amends = front.get("amends")
    made = amendment(root, str(amends), said, families) if amends else new_feature(root, front, text, said, families)
    made.removes.append(f"{PROPOSALS.as_posix()}/{name}")
    return made


def gh(args: list[str], request: dict | None = None) -> Any:
    """One call through `gh api`, the request read from standard input."""
    done = subprocess.run(["gh", "api", *args, *(["--input", "-"] if request is not None else [])],
                          input=json.dumps(request) if request is not None else None,
                          capture_output=True, text=True, check=True)
    return json.loads(done.stdout) if done.stdout.strip() else {}


def proposal_of(env: Mapping[str, str], api: Api) -> tuple[str, str]:
    """The one proposal the pull request adds, its name and text, read from its head."""
    files = api([f"repos/{env['REPO']}/pulls/{env['PR_NUMBER']}/files?per_page=100"], None)
    paths = [str(f["filename"]) for f in files]
    added = [f["filename"] for f in files if f.get("status") == "added"
             and str(f["filename"]).startswith(f"{PROPOSALS.as_posix()}/")
             and pathlib.PurePosixPath(f["filename"]).name not in PROPOSAL_SHAPES]
    if len(added) != 1 or len(paths) != 1:
        raise Refused("a proposal pull request adds one file under 10-functional/proposals/ and "
                      f"changes nothing else; this one changes {len(paths)}")
    path = added[0]
    found = api([f"repos/{env['HEAD_REPO']}/contents/{path}?ref={env['HEAD_SHA']}"], None)
    return pathlib.PurePosixPath(path).name, base64.b64decode(found["content"]).decode("utf-8")


def changed(root: pathlib.Path) -> tuple[list[str], list[str]]:
    """The files the checkout now writes and removes, against its HEAD."""
    done = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                          cwd=root, capture_output=True, text=True, check=True)
    writes, removes = [], []
    for line in done.stdout.splitlines():
        status, path = line[:2], line[3:]
        (removes if "D" in status else writes).append(path)
    return writes, removes


def commit(env: Mapping[str, str], api: Api, branch: str, head: str, root: pathlib.Path,
           made: Plan) -> None:
    """One signed commit of the checkout's changes onto a branch, as the App."""
    writes, removed = changed(root)
    removes = sorted({*removed, *made.removes})
    author = env["PR_AUTHOR"]
    api(["graphql"], {
        "query": ("mutation($input: CreateCommitOnBranchInput!) "
                  "{ createCommitOnBranch(input: $input) { commit { oid } } }"),
        "variables": {"input": {
            "branch": {"repositoryNameWithOwner": env["REPO"], "branchName": branch},
            "expectedHeadOid": head,
            "message": {
                "headline": f"docs(proposals): approve #{env['PR_NUMBER']} as Draft",
                "body": (f"{', '.join(made.identifiers)} in {made.where}, Draft until a reviewed "
                         "pull request hardens them.\n\n"
                         "Spec: GOV-R42\n"
                         f"Co-authored-by: {author} <{env['PR_AUTHOR_ID']}+{author}@users.noreply.github.com>\n"
                         "Signed-off-by: lemonfiber release <release@lemonfiber.app>"),
            },
            "fileChanges": {
                "additions": [{"path": p, "contents": base64.b64encode((root / p).read_bytes()).decode()}
                              for p in sorted(writes)],
                "deletions": [{"path": p} for p in removes],
            },
        }},
    })


def write(root: pathlib.Path, made: Plan) -> None:
    """The plan into the checkout, and the generated board and counts after it."""
    for path, text in made.writes.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for args in (["scripts/gen_board.py"], ["scripts/integrity.py", "--write"]):
        subprocess.run([sys.executable, *args], cwd=root, capture_output=True, check=True)


def land(env: Mapping[str, str], api: Api, root: pathlib.Path, made: Plan) -> str:
    """Commit the approval where it belongs; the address of what carries it."""
    repo, number = env["REPO"], env["PR_NUMBER"]
    if env["HEAD_REPO"] == repo:
        commit(env, api, env["HEAD_REF"], env["HEAD_SHA"], root, made)
        return f"https://github.com/{repo}/pull/{number}"
    # The proposal file was never on `main`, so a branch cut from it has nothing to remove.
    made.removes.clear()
    branch = f"proposal/approved-{number}"
    base = api([f"repos/{repo}/git/ref/heads/main"], None)
    head = base["object"]["sha"]
    api([f"repos/{repo}/git/refs"], {"ref": f"refs/heads/{branch}", "sha": head})
    commit(env, api, branch, head, root, made)
    pull = api([f"repos/{repo}/pulls"], {
        # The commit's subject on `main`, so it says what the commit does, as the
        # approval's own commit does, rather than repeating the proposal's title.
        "title": f"docs(proposals): approve #{number} as Draft",
        "head": branch,
        "base": "main",
        "body": (f"The proposal @{env['PR_AUTHOR']} opened in #{number}, approved: "
                 f"{', '.join(made.identifiers)} in `{made.where}`, Draft until a later pull "
                 "request hardens them. Review it as any spec change.\n\nSpec: GOV-R42"),
    })
    api([f"repos/{repo}/pulls/{number}"], {"state": "closed"})
    return str(pull["html_url"])


def say(env: Mapping[str, str], api: Api, body: str) -> None:
    """A comment on the proposal's pull request."""
    api([f"repos/{env['REPO']}/issues/{env['PR_NUMBER']}/comments"], {"body": body})


def main(env: Mapping[str, str] = os.environ, api: Api = gh, root: pathlib.Path = pathlib.Path(".")) -> int:
    try:
        name, text = proposal_of(env, api)
        made = plan(root, name, text)
    except Refused as refused:
        say(env, api, f"Not approved as it stands: {refused}.")
        print(f"::error::{refused}")
        return 1
    write(root, made)
    where = land(env, api, root, made)
    say(env, api, (f"Approved. {', '.join(made.identifiers)} are allocated in `{made.where}` as "
                   f"Draft, carried by {where}. Merging that puts them on `main`; a later pull "
                   "request that removes the Draft marking hardens them."))
    print(f"approved: {', '.join(made.identifiers)} in {made.where}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
