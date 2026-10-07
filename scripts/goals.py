#!/usr/bin/env python3
"""Where every goal of every unreleased version stands, and who is working on it.

The release gate answers one question about one version: is every goal met. A
person or an agent picking up work asks more of each goal than that, and asked it
of the repositories by hand until this: is it met, is it built and not yet
recorded, is somebody already working on it, or is nobody. This answers all four
for every version not yet released, from the same sources the gate reads, so its
verdicts and the gate's cannot differ (OPS-R76):

  met        cited by a merged commit, or landed where a row names it, and
             recorded done in a searched repository's tracker
  unmarked   cited by a merged commit and recorded done in no tracker: built,
             or at least worked on, and nobody has checked and ticked it
  uncited    recorded done, and no merged commit cites it and no row names
             where it landed
  claimed    not met, and an open pull request cites it — a draft one
             included, which is how a claim is taken (OPS-R77)
  open       none of those

A goal recorded `partial` somewhere says where, whichever of these it is.

Everything is read from git at one revision of each checkout (`--ref`), never from
a working tree, so a sibling checkout sitting on a feature branch reports its
default branch rather than whatever happened to be checked out. Open pull
requests come from a file `open_prs.sh` wrote: one object keyed by repository,
each holding that repository's open pull requests with their number, address,
whether they are drafts, their body and their commits' messages.

Usage:
  goals.py --checkout <name>=<path> [...] [--ref origin/main] [--prs prs.json]
           [--version X.Y.Z ...] [--markdown STATE.md] [--json state.json]

With no `--version`, every manifest that is neither released nor yanked. Exit 0
having written what was asked; 2 where something could not be read.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field

import status_check
import tracker as markdown_tracker
from gate import claimed as row_claims
from paths import within_cwd
from patterns import CITE, LANDED, SPEC_TRAILER, ordered

VERSIONS = pathlib.Path("70-operations/versions")
#: A revision as git names one, and never something git would read as an option.
REVISION = re.compile(r"^[A-Za-z0-9_.@^~/][A-Za-z0-9_.@^~/-]*$")
#: The states a manifest leaves the train in.
FINISHED = ("released", "yanked")
#: The order verdicts are reported in: what somebody can act on first.
VERDICTS = ("claimed", "unmarked", "uncited", "open", "met")
HEADINGS = {
    "claimed": "In flight — an open pull request cites it",
    "unmarked": "Cited and recorded done nowhere — check it and record it",
    "uncited": "Recorded done and cited by no merged commit",
    "open": "Open — nobody has started",
    "met": "Met",
}


class Unread(Exception):
    """Something this reads could not be read, so no verdict is given."""


@dataclass
class Standing:
    """What the sources say about one goal."""

    id: str
    cited_in: list[str] = field(default_factory=list)
    done_in: list[str] = field(default_factory=list)
    partial_in: list[str] = field(default_factory=list)
    landed_in: list[str] = field(default_factory=list)
    claims: list[dict] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        cited = bool(self.cited_in or self.landed_in)
        if cited and self.done_in:
            return "met"
        if self.claims:
            return "claimed"
        if self.cited_in:
            return "unmarked"
        if self.done_in:
            return "uncited"
        return "open"

    def as_json(self) -> dict:
        return {"id": self.id, "verdict": self.verdict, "cited_in": self.cited_in,
                "done_in": self.done_in, "partial_in": self.partial_in,
                "landed_in": self.landed_in, "claims": self.claims}


def git(path: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(path), *args], capture_output=True,
                          text=True, check=False)


def citations(name: str, path: pathlib.Path, ref: str) -> dict[str, list[str]]:
    """Each requirement a merged commit cites, with where: `repo@sha`."""
    if git(path, "rev-parse", "--is-shallow-repository").stdout.strip() != "false":
        raise Unread(f"{name} is a shallow clone, so its oldest citations are missing")
    log = git(path, "log", ref, "--format=%H%x1f%B%x1e")
    if log.returncode != 0:
        raise Unread(f"{name}: no history at {ref}: {log.stderr.strip()}")
    found: dict[str, list[str]] = {}
    for record in log.stdout.split("\x1e"):
        if "\x1f" not in record:
            continue
        sha, body = record.strip().split("\x1f", 1)
        for trailer in SPEC_TRAILER.findall(body):
            for ident in set(CITE.findall(trailer)):
                where = found.setdefault(ident, [])
                if f"{name}@{sha[:10]}" not in where:
                    where.append(f"{name}@{sha[:10]}")
    return found


#: The binary's tracker while it is still kept as Markdown tables.
LEGACY = "IMPLEMENTATION-STATUS.md"


def tracker(name: str, path: pathlib.Path, ref: str) -> list[status_check.Row]:
    """A repository's tracker as it stands at `ref`, refusing one that is not there.

    A tracker still in the milestone shape is read through its Markdown page the
    way the gate reads it, a done row standing for each requirement it names.
    """
    shown = git(path, "show", f"{ref}:{status_check.FILE}")
    if shown.returncode != 0:
        raise Unread(f"{name} keeps no {status_check.FILE} at {ref} (OPS-R74), and a "
                     "tracker that was not read is not one that records nothing")
    try:
        rows = status_check.parse(shown.stdout, f"{name}:{status_check.FILE}", name)
    except status_check.Unreadable as broken:
        raise Unread(str(broken)) from broken
    if rows is not None:
        return rows
    page = git(path, "show", f"{ref}:{LEGACY}").stdout.splitlines()
    found = []
    for row in markdown_tracker.rows(page):
        if row is None or not row.done:
            continue
        shas = LANDED.findall(row.line)
        for ident in sorted(row_claims(row)):
            found.append(status_check.Row(ident, status_check.DONE, (), shas[0] if shas else None, name))
    return found


def landed(path: pathlib.Path, sha: str, ref: str) -> bool:
    return git(path, "merge-base", "--is-ancestor", sha, ref).returncode == 0


def claims(prs: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Each requirement an open pull request cites, in its body or its commits."""
    found: dict[str, list[dict]] = {}
    for repo, listed in prs.items():
        for pr in listed:
            texts = [pr.get("body") or ""] + [c.get("message", "") for c in pr.get("commits") or []]
            cited = {ident for text in texts for trailer in SPEC_TRAILER.findall(text)
                     for ident in CITE.findall(trailer)}
            claim = {"repo": repo, "number": pr["number"], "url": pr["url"],
                     "draft": bool(pr.get("isDraft"))}
            for ident in cited:
                found.setdefault(ident, []).append(claim)
    return found


def manifests(spec: pathlib.Path, wanted: list[str]) -> list[dict]:
    """The manifests asked for, or every one still on the train, in train order."""
    found = []
    for path in (spec / VERSIONS).glob("*.toml"):
        if path.stem == "TEMPLATE":
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if wanted and data["version"] not in wanted:
            continue
        if not wanted and data.get("status", "planned") in FINISHED:
            continue
        found.append(data)
    missing = set(wanted) - {data["version"] for data in found}
    if missing:
        raise Unread(f"no manifest for {', '.join(sorted(missing))}")
    return sorted(found, key=lambda data: ordered(data["version"]))


def standing(manifest: dict, checkouts: dict[str, pathlib.Path], ref: str,
             claimed: dict[str, list[dict]]) -> list[Standing]:
    """Each goal of one version, read where that version is satisfied."""
    searched = manifest.get("satisfied_in", manifest.get("repos", []))
    absent = [name for name in searched if name not in checkouts]
    if absent:
        raise Unread(f"{manifest['version']} is satisfied in {', '.join(absent)}, "
                     "and no checkout of it was given")
    goals = {ident: Standing(ident) for ident in manifest.get("goals", [])}
    for name in searched:
        path = checkouts[name]
        for ident, where in citations(name, path, ref).items():
            if ident in goals:
                goals[ident].cited_in += where
        for row in tracker(name, path, ref):
            if row.id not in goals:
                continue
            if row.done:
                if name not in goals[row.id].done_in:
                    goals[row.id].done_in.append(name)
                if row.landed and landed(path, row.landed, ref):
                    goals[row.id].landed_in.append(f"{name}@{row.landed[:10]}")
            elif row.state == "partial":
                goals[row.id].partial_in.append(name)
    for ident, found in claimed.items():
        if ident in goals:
            goals[ident].claims = found
    return list(goals.values())


def markdown(report: list[tuple[dict, list[Standing]]], ref: str) -> str:
    """The report as a page a person reads."""
    source = (f"Read from each repository at `{ref}`. Written by `scripts/goals.py`; "
              "`just goals <version>` writes the same from local checkouts (OPS-R76).")
    out = ["# Where every unreleased version stands", "", source, ""]
    for manifest, goals in report:
        counts = {verdict: sum(g.verdict == verdict for g in goals) for verdict in VERDICTS}
        summary = ", ".join(f"{counts[v]} {v}" for v in VERDICTS if counts[v])
        out += [f"## {manifest['version']} — {manifest.get('status', 'planned')}", "",
                f"{len(goals)} goals: {summary}.", ""]
        for verdict in VERDICTS:
            rows = [g for g in goals if g.verdict == verdict]
            if not rows:
                continue
            fold = verdict == "met"
            out += (["<details><summary>Met</summary>", ""] if fold
                    else [f"### {HEADINGS[verdict]}", ""])
            out += ["| Goal | Done in | Partial in | Cited in | Claimed by |",
                    "|---|---|---|---|---|"]
            for g in rows:
                claimed = ", ".join(
                    f"[{c['repo']}#{c['number']}]({c['url']}){' (draft)' if c['draft'] else ''}"
                    for c in g.claims)
                cited = ", ".join(g.cited_in[:3] + g.landed_in[:1])
                if len(g.cited_in) > 3:
                    cited += f" and {len(g.cited_in) - 3} more"
                out.append(f"| {g.id} | {', '.join(g.done_in)} | {', '.join(g.partial_in)} | "
                           f"{cited} | {claimed} |")
            out += ["", "</details>", ""] if fold else [""]
    return "\n".join(out).rstrip("\n") + "\n"


def pairs(specs: list[str]) -> dict[str, pathlib.Path]:
    found = {}
    for spec in specs:
        name, sep, raw = spec.partition("=")
        if not sep or not name or not raw:
            raise Unread(f"--checkout wants name=path, got {spec!r}")
        found[name] = within_cwd(raw)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec", default=".")
    parser.add_argument("--checkout", action="append", default=[], metavar="name=path")
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--prs")
    parser.add_argument("--version", action="append", default=[])
    parser.add_argument("--markdown")
    parser.add_argument("--json", dest="json_out")
    args = parser.parse_args()
    if not REVISION.match(args.ref):
        print(f"::error::`{args.ref}` is not a revision")
        return 2
    try:
        checkouts = pairs(args.checkout)
        prs = json.loads(within_cwd(args.prs).read_text(encoding="utf-8")) if args.prs else {}
        claimed = claims(prs)
        report = [(m, standing(m, checkouts, args.ref, claimed))
                  for m in manifests(within_cwd(args.spec), args.version)]
    except (Unread, OSError, json.JSONDecodeError) as unread:
        print(f"::error::{unread}")
        return 2
    page = markdown(report, args.ref)
    data = {"ref": args.ref, "versions": [
        {"version": m["version"], "status": m.get("status", "planned"),
         "goals": [g.as_json() for g in goals]} for m, goals in report]}
    if args.markdown:
        within_cwd(args.markdown).write_text(page, encoding="utf-8")
    if args.json_out:
        within_cwd(args.json_out).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    if not (args.markdown or args.json_out):
        print(page, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
