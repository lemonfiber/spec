#!/usr/bin/env python3
"""Turn an RFC issue into a proposal pull request — GOV-R40, GOV-R43.

An `rfc` issue is a way in for somebody who will not touch a file. A maintainer
converts it into a proposal pull request before its text is discussed, by
labelling it `rfc:convert`; the `rfc-convert` workflow verifies the maintainer
may write and runs this. It writes the issue's fields into one Draft proposal
under `10-functional/proposals/`, with no identifier, commits it to a branch of
its own as the release App, signed, and opens the pull request crediting the
issue's author. Identifiers are allocated only when the proposal is approved.

The fields are untrusted. They arrive in environment variables and are written
only as Markdown text: the area is checked against the catalogue's areas and
the file name is built from the issue's number alone; a field's line that would
read as a heading is escaped; nothing is interpolated into a shell, and every
call to the forge takes its request as a file.

Usage, from the root of the spec checkout, with ISSUE_BODY, ISSUE_NUMBER,
ISSUE_TITLE, ISSUE_URL, ISSUE_AUTHOR and REPO set and `gh` authenticated:
  rfc_convert.py
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from catalogue import FEATURES_README
from catalogue import areas as area_names
from integrity import PROPOSALS

#: One call to the forge's API through `gh`: its arguments and the request
#: body, then the JSON it answers with.
Api = Callable[[list[str], dict | None], dict]


class Refused(Exception):
    """The issue cannot be converted as it stands; the message says why."""


@dataclass(frozen=True)
class Proposal:
    """The proposal an issue becomes."""

    number: str
    title: str
    path: str
    text: str


def field(body: str, label: str) -> str:
    """The text an issue form wrote under one `### label`."""
    lines = body.splitlines()
    try:
        start = next(n for n, line in enumerate(lines) if line.strip() == f"### {label}")
    except StopIteration:
        return ""
    end = next((n for n in range(start + 1, len(lines)) if lines[n].startswith("### ")), len(lines))
    text = "\n".join(lines[start + 1:end]).strip()
    return "" if text == "_No response_" else text


def text(value: str) -> str:
    """A field as Markdown prose: a line that would open a heading is escaped,
    so the field cannot add a section of the proposal's own."""
    return "\n".join(f"\\{line}" if line.lstrip().startswith("#") else line
                     for line in value.splitlines()) or "(none given)"


def statements(value: str) -> str:
    """The proposed behaviour as bullets, one per line the author wrote."""
    lines = [line.strip().removeprefix("- ").removeprefix("* ").strip() for line in value.splitlines()]
    return "\n".join(f"- {text(line)}" for line in lines if line) or "- (none given)"


def render(env: Mapping[str, str], areas: set[str]) -> Proposal:
    """The proposal, from the issue."""
    number = env.get("ISSUE_NUMBER", "")
    if not number.isdigit():
        raise Refused("the issue number is not a number")
    number = str(int(number))
    body = env.get("ISSUE_BODY", "")
    area = field(body, "Area")[:1].upper()
    if area not in areas:
        raise Refused(f"the area {field(body, 'Area')!r} is not one the catalogue holds")
    title = " ".join((field(body, "Proposal title") or env.get("ISSUE_TITLE", "")).split())
    title = title.removeprefix("RFC:").strip()
    if not title:
        raise Refused("the issue names no title")
    quoted = "'" + title.replace("'", "''") + "'"
    proposal = f"""---
kind: proposal
area: {area}
title: {quoted}
status: draft
---

# {text(title)}

Converted from [#{number}]({env.get("ISSUE_URL", "")}), opened by @{env.get("ISSUE_AUTHOR", "")}.

## Problem

{text(field(body, "The problem"))}

## Proposed behaviour

{statements(field(body, "Proposed behaviour"))}

## Rationale

{text(field(body, "Rationale & alternatives"))}
"""
    return Proposal(number, title, f"{PROPOSALS.as_posix()}/rfc-{number}.md", proposal)


def gh(args: list[str], request: dict | None = None) -> dict:
    """One call through `gh api`, the request read from standard input."""
    done = subprocess.run(["gh", "api", *args, *(["--input", "-"] if request is not None else [])],
                          input=json.dumps(request) if request is not None else None,
                          capture_output=True, text=True, check=True)
    return json.loads(done.stdout) if done.stdout.strip() else {}


def open_proposal(env: Mapping[str, str], proposal: Proposal, api: Api) -> str:
    """Commit the proposal to its own branch, signed, and open the pull request;
    its address."""
    repo, number = env["REPO"], proposal.number
    branch = f"proposal/rfc-{number}"
    base = api([f"repos/{repo}/git/ref/heads/main"], None)["object"]["sha"]
    api([f"repos/{repo}/git/refs"], {"ref": f"refs/heads/{branch}", "sha": base})
    commit = {
        "query": ("mutation($input: CreateCommitOnBranchInput!) "
                  "{ createCommitOnBranch(input: $input) { commit { oid } } }"),
        "variables": {"input": {
            "branch": {"repositoryNameWithOwner": repo, "branchName": branch},
            "expectedHeadOid": base,
            "message": {
                "headline": f"docs(proposal): RFC #{number} as a Draft proposal",
                "body": ("A maintainer converted the issue into a proposal, with no identifier; "
                         "identifiers are allocated when it is approved.\n\n"
                         "Spec: GOV-R40\n"
                         "Signed-off-by: lemonfiber release <release@lemonfiber.app>"),
            },
            "fileChanges": {"additions": [
                {"path": proposal.path, "contents": base64.b64encode(proposal.text.encode()).decode()}
            ]},
        }},
    }
    api(["graphql"], commit)
    pull = api([f"repos/{repo}/pulls"], {
        "title": f"Proposal: {proposal.title}"[:120],
        "head": branch,
        "base": "main",
        "body": (f"Converted from #{number}, opened by @{env.get('ISSUE_AUTHOR', '')}. "
                 "Discuss the proposal here; a maintainer approves it with `proposal:approved`, "
                 "which allocates its identifiers.\n\nCloses #" + number + "\n\nSpec: GOV-R40"),
        "maintainer_can_modify": True,
    })
    api([f"repos/{repo}/issues/{number}/comments"],
        {"body": f"Converted into a proposal pull request: {pull['html_url']}. "
                 "The discussion continues there."})
    return pull["html_url"]


def main(env: Mapping[str, str] = os.environ, api: Api = gh) -> int:
    try:
        areas = set(area_names(pathlib.Path(FEATURES_README).read_text(encoding="utf-8")))
        proposal = render(env, areas)
        print(f"opened {open_proposal(env, proposal, api)} with {proposal.path}")
    except Refused as refused:
        print(f"::error::{refused}")
        return 1
    except (OSError, KeyError, subprocess.CalledProcessError, json.JSONDecodeError) as broken:
        print(f"::error::{broken}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
