#!/usr/bin/env python3
"""A pull request pushed again cancels the run it supersedes, and nothing else is cancelled (Q-R75).

The organisation's repositories share twenty runners. A run on a head its pull
request has moved past is read by nobody and holds runners that every other
repository's checks queue behind. So every workflow a pull request runs carries
the group in ``shared/concurrency.yml``: a pull request's runs share one group
and the newer cancels the older, and every other event is grouped by its own run,
so a push to ``main`` or a tag is never cancelled and never cancels.

``check_shared_files.py`` runs this against the calling repository, which is how
it reaches every repository that calls the hygiene gate without moving a pin.
What it refuses, file by file under ``.github/workflows/``:

- a workflow triggered by ``pull_request`` whose own group is not that one;
- a group that cancels and is not that one. Keyed on the ref alone, a push to
  ``main`` cancels the one before it. A workflow that only a dispatch or a
  schedule starts is let through: no push and no tag reaches it, and a bump bot
  is asked to cancel its stale run there (Q-R78);
- a workflow ``pull_request_target`` starts at all. It runs the base branch's
  copy with a token that can write on a pull request's event, and a privileged
  follow-up is a ``workflow_run`` from the default branch instead (Q-R84);
- a workflow that calls ``pin-only.yml`` without ``VERDICT_BLOCK``. One verdict
  runs at a time for a branch, so an older verdict is never posted over a
  newer, and a newer waiting replaces the one waiting before it (Q-R83);
- a job's own group that cancels, and any job's own group in a workflow a pull
  request runs. A job waiting in a group is replaced by the next to arrive
  whatever ``cancel-in-progress`` says, so a push's job can be cancelled by one;
- two such workflows sharing a name. The group is keyed on the name, so each
  would cancel the other's run on the same pull request;
- a reusable workflow that cancels. A group declared in one is evaluated in each
  caller's context, where it is the caller's own group;
- a reusable workflow a pull request also runs directly, in a repository with no
  ``cancel-superseded.yml``. That workflow cancels such a workflow's superseded
  runs from outside, because it cannot carry the group itself.

The files are read by a reader of the few shapes a workflow's ``on``,
``concurrency`` and ``jobs`` take, not by a YAML parser: the hygiene gate runs
this on an interpreter with no packages installed. A shape the reader does not
know is refused as unread rather than passed.
"""

from __future__ import annotations

import pathlib
import re

#: Where the one block lives, relative to a spec checkout.
HOME = "shared/concurrency.yml"

#: The workflow that cancels a reusable workflow's superseded runs by the API.
CANCELLER = "cancel-superseded.yml"

#: The events a workflow can be started by that are neither a push nor a tag nor
#: a pull request. A group of its own that cancels cannot reach a protected
#: branch's run or a release's from a workflow started only by these.
DISPATCHED = frozenset({"workflow_dispatch", "repository_dispatch", "schedule"})

#: The event no workflow may be started by (Q-R84).
TARGET = "pull_request_target"

#: `pin-only`'s verdict block, as (group, cancel-in-progress): one verdict at a time for a branch
#: of a repository, never cancelled, so the newest posted is the newest read (Q-R83).
VERDICT_BLOCK = (
    (
        "${{ github.workflow }}-${{ github.event.workflow_run.head_repository.full_name }}"
        "-${{ github.event.workflow_run.head_branch }}"
    ),
    "false",
)

#: A job's `uses` naming `pin-only.yml`, spec's own copy or one pinned from spec.
PIN_ONLY_CALL = re.compile(r"\A(?:lemonfiber/spec|\.)/\.github/workflows/pin-only\.yml(?:@\S+)?\Z")

# `key: value`, `key:`, and a quoted key, which is how `"on":` is written by
# anyone whose YAML reads a bare `on` as `true`.
ENTRY = re.compile(r"""^(?P<key>"[^"]*"|'[^']*'|[\w.-]+)[ \t]*:(?P<value>.*)$""")


class Unread(ValueError):
    """A shape the reader does not know, with the line it stopped on."""


def unquote(value: str) -> str:
    """A scalar's text: quotes taken off, and a trailing comment off a plain one."""
    value = value.strip()
    if value[:1] in {'"', "'"}:
        mark = value[0]
        end = value.find(mark, 1)
        if end < 0:
            raise Unread(f"an unclosed quote in {value!r}")
        inner = value[1:end]
        return inner.replace("''", "'") if mark == "'" else inner
    return re.split(r"\s#", value, maxsplit=1)[0].strip()


def lines_of(text: str) -> list[tuple[int, str]]:
    """Each line that says something, with its indent. Comments and blanks say nothing."""
    kept = []
    for raw in text.splitlines():
        body = raw.strip()
        if not body or body.startswith("#") or body == "---":
            continue
        kept.append((len(raw) - len(raw.lstrip(" ")), body))
    return kept


def entries(lines: list[tuple[int, str]]) -> list[tuple[str | None, str, list]]:
    """One level of a block: each entry's key, inline value, and the lines under it.

    A list item has no key, and its value is the text after the dash.
    """
    if not lines:
        return []
    level = lines[0][0]
    found: list[tuple[str | None, str, list]] = []
    for indent, body in lines:
        if indent > level:
            found[-1][2].append((indent, body))
            continue
        if indent < level:
            raise Unread(f"{body!r} is indented less than the block it sits in")
        if body == "-" or body.startswith("- "):
            found.append((None, body[1:].strip(), []))
            continue
        matched = ENTRY.match(body)
        if matched is None or matched["value"][:1] not in {"", " ", "\t"}:
            raise Unread(f"{body!r} is not a key this reader knows")
        found.append((unquote(matched["key"]), matched["value"].strip(), []))
    return found


def events(value: str, children: list) -> list[str]:
    """The events an `on:` names, in any of the three ways it can name them."""
    flow = re.split(r"\s#", value, maxsplit=1)[0].strip()
    if flow.startswith("{"):
        raise Unread(f"on: {flow} is a flow mapping")
    if flow.startswith("["):
        if not flow.endswith("]"):
            raise Unread(f"on: {flow} is a list that does not close on its line")
        return [unquote(one) for one in flow[1:-1].split(",") if one.strip()]
    if flow:
        return [unquote(value)]
    return [key if key is not None else unquote(item) for key, item, _ in entries(children)]


def group_of(value: str, children: list) -> tuple[str, str | None]:
    """A `concurrency:` block's group and its cancel-in-progress, as written."""
    if value.strip().startswith("{"):
        raise Unread(f"concurrency: {value.strip()} is a flow mapping")
    if value.strip():
        # The short form is a group alone, which cancels nothing.
        return unquote(value), None
    said = {key: unquote(item) for key, item, _ in entries(children)}
    return said.get("group", ""), said.get("cancel-in-progress")


def workflow(text: str) -> dict:
    """What this check needs from one workflow file."""
    listed = entries(lines_of(text))
    if any(key is None for key, _, _ in listed):
        raise Unread("a list item at the top level, where only keys belong")
    top = {key: (value, children) for key, value, children in listed}
    read: dict = {"events": [], "group": None, "jobs": {}, "calls": {}, "name": None}
    if "on" in top:
        read["events"] = events(*top["on"])
    if "name" in top:
        read["name"] = unquote(top["name"][0])
    if "concurrency" in top:
        read["group"] = group_of(*top["concurrency"])
    for job, _, body in entries(top.get("jobs", ("", []))[1]):
        said = {key: (value, children) for key, value, children in entries(body)}
        if "concurrency" in said:
            read["jobs"][job] = group_of(*said["concurrency"])
        if "uses" in said:
            read["calls"][job] = (unquote(said["uses"][0]), unquote(said["if"][0]) if "if" in said else None)
    return read


def cancels(cancel: str | None) -> bool:
    """Whether a cancel-in-progress can be true. Only an absent or literal false cannot."""
    return cancel is not None and cancel.strip().lower() != "false"


def dispatched_only(named: list[str]) -> bool:
    """Whether every event a workflow names is a dispatch or a schedule."""
    return bool(named) and set(named) <= DISPATCHED


def home(canonical: pathlib.Path) -> tuple[str, list[str]]:
    """The one group, read from its home, or why it could not be."""
    path = canonical / HOME
    if not path.is_file():
        return "", [
            (
                f"{HOME} is not here, so no workflow's concurrency group was compared "
                f"against the one that cancels only a pull request's superseded run (Q-R75)"
            )
        ]
    try:
        group, cancel = workflow(path.read_text(encoding="utf-8"))["group"] or ("", None)
    except Unread as unread:
        return "", [f"{HOME} could not be read: {unread}"]
    if not group or cancel != "true":
        return "", [
            (
                f"{HOME} holds no group that cancels, so every workflow would be held "
                f"to a block that replaces nothing (Q-R75)"
            )
        ]
    return group, []


def findings(repo: pathlib.Path, group: str) -> list[str]:
    """Everything in this repository's workflows that Q-R75 refuses."""
    folder = repo / ".github" / "workflows"
    if not folder.is_dir():
        return []
    paths = sorted(p for p in folder.iterdir() if p.suffix in {".yml", ".yaml"})
    wanted = f"concurrency:\n  group: {group}\n  cancel-in-progress: true"
    read = {}
    said = []
    for path in paths:
        where = f".github/workflows/{path.name}"
        try:
            read[where] = workflow(path.read_text(encoding="utf-8"))
        except Unread as unread:
            said.append(
                f"{where} could not be read here ({unread}), so whether a pull "
                f"request's superseded run is cancelled is unknown. It is refused "
                f"rather than passed (Q-R75)"
            )
    runs_directly = {
        where
        for where, one in read.items()
        if "pull_request" in one["events"] and "workflow_call" in one["events"]
    }
    for where, one in read.items():
        said += refused(where, one, group, wanted)
    canceller = read.get(f".github/workflows/{CANCELLER}", {"events": []})
    if "pull_request" not in canceller["events"]:
        said += [
            f"{where} is a reusable workflow a pull request also runs directly. It "
            f"cannot carry the group, which a caller would share, so its superseded "
            f"runs are cancelled from outside by .github/workflows/{CANCELLER}, "
            f"and no such workflow runs on a pull request here (Q-R75)"
            for where in sorted(runs_directly)
        ]
    said += shared_names(read, group)
    return said


def refused(where: str, one: dict, group: str, wanted: str) -> list[str]:
    """What one workflow file does that Q-R75 refuses."""
    said = []
    own, cancel = one["group"] or ("", None)
    reusable = "workflow_call" in one["events"]
    if reusable and cancels(cancel):
        said.append(
            f"{where} is a reusable workflow with a group that cancels. A caller "
            f"evaluates it in its own context, where it is the caller's own group, "
            f"and the two cancel or wait on each other. Take it out (Q-R75)"
        )
    elif "pull_request" in one["events"] and not reusable and (own, cancel) != (group, "true"):
        said.append(
            f"{where} runs on a pull request, and its concurrency is not the block "
            f"in lemonfiber/spec {HOME}, which cancels the run a push to it "
            f"supersedes and nothing else. Give it that block:\n{wanted}"
        )
    elif cancels(cancel) and own != group and not dispatched_only(one["events"]):
        said.append(
            f"{where} cancels by the group {own!r}, which can cancel a run for a push "
            f"to a protected branch or a tag. Use the block in lemonfiber/spec "
            f"{HOME}, which cancels only a pull request's run:\n{wanted}"
        )
    if TARGET in one["events"]:
        said.append(
            f"{where} runs on {TARGET}, which runs the base branch's copy with a token that "
            f"can write on a pull request's event. Run the pull request's half on "
            f"pull_request with no token, and what needs one on workflow_run from the "
            f"default branch, reading only what the forge set on the run (Q-R84)"
        )
    said += [
        f"{where} job {job!r} calls pin-only's verdict, which runs one at a time for a branch "
        f"and is never cancelled, so an older verdict is never posted over a newer (Q-R83). "
        f"Give it the block spec's pin-only.yml documents:\n"
        f"concurrency:\n  group: {VERDICT_BLOCK[0]}\n  cancel-in-progress: {VERDICT_BLOCK[1]}"
        for job, (uses, _) in one["calls"].items()
        if PIN_ONLY_CALL.match(uses) and (own, (cancel or "").strip().lower()) != VERDICT_BLOCK
    ]
    said += [
        f"{where} job {job!r} has a group of its own. A job waiting in a group is "
        f"replaced by the next one to arrive whatever cancel-in-progress says, so "
        f"it can cancel a job of a run for a push or a tag. Cancelling belongs to "
        f"the workflow's group in {HOME} (Q-R75)"
        for job, (_, job_cancel) in one["jobs"].items()
        if cancels(job_cancel) or "pull_request" in one["events"]
    ]
    return said


def shared_names(read: dict, group: str) -> list[str]:
    """Workflows grouped by the same name, which cancel each other's runs."""
    named: dict[tuple[str, str], list[str]] = {}
    for where, one in read.items():
        own = (one["group"] or ("", None))[0]
        if own == group:
            named.setdefault((own, one["name"] or where), []).append(where)
    return [
        f"{' and '.join(files)} are both named {name!r}, and the group is keyed on "
        f"the name: each cancels the other's run on the same pull request. Name "
        f"them apart (Q-R75)"
        for (_, name), files in sorted(named.items())
        if len(files) > 1
    ]


def superseded(repo: pathlib.Path, canonical: pathlib.Path) -> list[str]:
    """This repository's workflows against Q-R75, as problems for the shared-files run."""
    group, refusal = home(canonical)
    if refusal:
        return refusal
    return findings(repo, group)
