#!/usr/bin/env python3
"""Where every goal of every version stands, and who is working on it.

The release gate answers one question about one version: is every goal met. A
person or an agent picking up work asks more of each goal than that, and asked it
of the repositories by hand until this: is it met, is it built and not yet
recorded, is somebody already working on it, or is nobody. This answers all four
for every version on the train, released ones included, from the same sources the
gate reads, so its
verdicts and the gate's cannot differ (OPS-R76):

  met        cited by a merged commit, or landed where a row names it, and
             recorded done in a searched repository's tracker
  unmarked   cited by a merged commit and recorded done in no tracker: built,
             or at least worked on, and nobody has checked and ticked it
  uncited    recorded done, and no merged commit cites it and no row names
             where it landed
  unknown    not met in the repositories that could be read, and searched in
             one that could not
  claimed    not met, and an open pull request cites it — a draft one
             included, which is how a claim is taken (OPS-R77)
  open       none of those

A repository whose history or tracker cannot be read, or for which no checkout
was given, is named under `unread` with the reason, and the rest of the report is
still written. The release gate refuses a version it cannot judge; this answers
more questions than the gate, and one absent tracker would otherwise hide every
fact the others hold.

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

With no `--version`, every manifest. `state.json` holds every goal of each; the page
gives a released or yanked version one line, since nothing on it is left to pick
up. Exit 0
having written what was asked, a repository that could not be read included; 2
where the spec, an argument or the pull request file could not be read.

`state.json` is what a script reads, and its shape is documented in
`70-operations/staging.md`: `format` says which shape it is, `sources` the commit
of the spec and of every repository it was read from, and `generated_at` when.
"""

from __future__ import annotations

import argparse
import datetime
import functools
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass, field

import status_check
import tracker as markdown_tracker
from claims import CAP, over_cap
from gate import claimed as row_claims
from paths import within_cwd
from patterns import CITE, LANDED, SPEC_TRAILER, ordered

#: A revision as git names one, and never something git would read as an option.
REVISION = re.compile(r"^[A-Za-z0-9_.@^~/][A-Za-z0-9_.@^~/-]*$")
#: The shape of `state.json`. A field removed, renamed or given another meaning
#: raises it; a field added does not, so a reader checks it and ignores the rest.
FORMAT = 1
#: The states a manifest has once it has shipped, which the page gives one line.
FINISHED = ("released", "yanked")
#: The order verdicts are reported in: what somebody can act on first.
VERDICTS = ("claimed", "unmarked", "uncited", "unknown", "open", "met")
HEADINGS = {
    "claimed": "In flight — an open pull request cites it",
    "unmarked": "Cited and recorded done nowhere — check it and record it",
    "uncited": "Recorded done and cited by no merged commit",
    "unknown": "Unknown — searched in a repository that could not be read",
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
    #: Whether a repository it is searched in could not be read.
    unread: bool = False

    @property
    def verdict(self) -> str:
        cited = bool(self.cited_in or self.landed_in)
        if cited and self.done_in:
            return "met"
        if self.unread:
            return "unknown"
        if self.claims:
            return "claimed"
        if self.cited_in:
            return "unmarked"
        if self.done_in:
            return "uncited"
        return "open"

    def record(self, name: str, path: pathlib.Path, row, ref: str) -> None:
        """What one repository's tracker row says of this goal."""
        if row.state == "partial":
            self.partial_in.append(name)
        if not row.done:
            return
        if name not in self.done_in:
            self.done_in.append(name)
        if row.landed and landed(path, row.landed, ref):
            self.landed_in.append(f"{name}@{row.landed[:10]}")

    def as_json(self) -> dict:
        return {"id": self.id, "verdict": self.verdict, "cited_in": self.cited_in,
                "done_in": self.done_in, "partial_in": self.partial_in,
                "landed_in": self.landed_in, "claims": self.claims}


def git(path: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(path), *args], capture_output=True,
                          text=True, check=False)


@functools.cache
def citations(name: str, path: pathlib.Path, ref: str) -> dict[str, list[str]]:
    """Each requirement a merged commit cites, with where: `repo@sha`."""
    if git(path, "rev-parse", "--is-shallow-repository").stdout.strip() != "false":
        raise Unread(f"{name} is a shallow clone, so its oldest citations are missing")
    # The exit status goes unread: `revision()` has already refused a ref that
    # names no commit, and the log of one that does has nothing left to fail on.
    log = git(path, "log", ref, "--format=%H%x1f%B%x1e")
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


@functools.cache
def tracker(name: str, path: pathlib.Path, ref: str) -> list[status_check.Row]:
    """A repository's tracker as it stands at `ref`, refusing one that is not there.

    `status.toml`, or a `status/` directory split by feature. A tracker still in
    the milestone shape is read through its Markdown page the way the gate reads
    it, a done row standing for each requirement it names.
    """
    listed = git(path, "ls-tree", "--name-only", f"{ref}:{status_check.DIRECTORY}")
    try:
        if listed.returncode == 0:
            files = [(f, git(path, "show", f"{ref}:{status_check.DIRECTORY}/{f}").stdout)
                     for f in listed.stdout.split() if f.endswith(".toml")]
            return status_check.gathered(files, name)
        shown = git(path, "show", f"{ref}:{status_check.FILE}")
        if shown.returncode != 0:
            raise Unread(f"{name} keeps no tracker at {ref} (OPS-R74), and a tracker "
                         "that was not read is not one that records nothing")
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


def revision(name: str, path: pathlib.Path, ref: str) -> str:
    """The commit `ref` names in one checkout, in full, so a reader can fetch it."""
    found = git(path, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")
    if found.returncode != 0:
        raise Unread(f"{name}: `{ref}` names no commit: {found.stderr.strip()}")
    return found.stdout.strip()


def as_data(report: list[tuple[dict, list[Standing]]], ref: str, sources: dict[str, str],
            unread: dict[str, str], now: datetime.datetime) -> dict:
    """The report for a script: its format, what it was read from and when, and each goal."""
    return {
        "format": FORMAT,
        "generated_at": now.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ref": ref,
        "sources": sources,
        "unread": [{"repo": repo, "reason": reason} for repo, reason in sorted(unread.items())],
        "versions": [
            {"version": m["version"], "status": m.get("status", "planned"),
             "milestone": m.get("milestone"), "delivers": m.get("delivers"),
             "goals": [g.as_json() for g in goals]}
            for m, goals in report],
    }


def manifests(spec: pathlib.Path, wanted: list[str]) -> list[dict]:
    """The manifests asked for, or every one, in train order."""
    found = [data for data in status_check.manifests(spec)
             if not wanted or data["version"] in wanted]
    missing = set(wanted) - {data["version"] for data in found}
    if missing:
        raise Unread(f"no manifest for {', '.join(sorted(missing))}")
    return sorted(found, key=lambda data: ordered(data["version"]))


def standing(manifest: dict, checkouts: dict[str, pathlib.Path], ref: str,
             claimed: dict[str, list[dict]], unread: dict[str, str]) -> list[Standing]:
    """Each goal of one version, read where that version is satisfied.

    A repository that cannot be read is added to `unread` with the reason, once
    for every version, and marks each goal of this one as searched where it was
    not read."""
    searched = manifest.get("satisfied_in", manifest.get("repos", []))
    goals = {ident: Standing(ident) for ident in manifest.get("goals", [])}
    for name in searched:
        if not read_where(goals, name, checkouts, ref, unread):
            for goal in goals.values():
                goal.unread = True
    for ident, found in claimed.items():
        if ident in goals:
            goals[ident].claims = found
    return list(goals.values())


def read_where(goals: dict[str, Standing], name: str, checkouts: dict[str, pathlib.Path],
               ref: str, unread: dict[str, str]) -> bool:
    """Read one repository into `goals`, or record in `unread` why it could not
    be; whether it was read. A repository already found unreadable is not tried
    again."""
    if name not in unread and name not in checkouts:
        unread[name] = f"{name}: no checkout of it was given"
    if name in unread:
        return False
    try:
        read_repository(goals, name, checkouts[name], ref)
    except Unread as broken:
        unread[name] = str(broken)
        return False
    return True


def read_repository(goals: dict[str, Standing], name: str, path: pathlib.Path,
                    ref: str) -> None:
    """What one repository's history and tracker say of each goal.

    Both are read before either is applied, so a repository whose tracker
    cannot be read adds no citation either."""
    cited = citations(name, path, ref)
    rows = tracker(name, path, ref)
    for ident, where in cited.items():
        if ident in goals:
            goals[ident].cited_in += where
    for row in rows:
        if row.id in goals:
            goals[row.id].record(name, path, row, ref)


def markdown(report: list[tuple[dict, list[Standing]]], ref: str,
             unread: dict[str, str], crowded: dict[str, int] | None = None) -> str:
    """The report as a page a person reads: what could not be read, what is still
    to do, then what shipped."""
    source = (f"Read from each repository at `{ref}`. Written by `scripts/goals.py`; "
              "`just goals <version>` writes the same from local checkouts (OPS-R76).")
    out = ["# Where every version stands", "", source, ""]
    if unread:
        note = ("A goal searched in one of these reads unknown unless another "
                "repository shows it met.")
        out += ["## Not read", "", note, ""]
        out += [f"- **{repo}**: {reason}" for repo, reason in sorted(unread.items())]
        out += [""]
    if crowded:
        note = (f"Each holds more than {CAP} open pull requests from people and agents, "
                "the organisation's bots not counted (GOV-R58). Merge or close one before "
                "opening another.")
        out += ["## Over the cap", "", note, ""]
        out += [f"- **{repo}**: {n}" for repo, n in sorted(crowded.items())]
        out += [""]
    for manifest, goals in report:
        if manifest.get("status", "planned") not in FINISHED:
            out += standing_page(manifest, goals)
    finished = [(m, goals) for m, goals in report if m.get("status", "planned") in FINISHED]
    if finished:
        out += ["## Released", "", "| Version | Status | Goals met |", "|---|---|---|"]
        out += [f"| {m['version']} | {m['status']} | "
                f"{sum(g.verdict == 'met' for g in goals)} of {len(goals)} |"
                for m, goals in finished]
    return "\n".join(out).rstrip("\n") + "\n"


def standing_page(manifest: dict, goals: list[Standing]) -> list[str]:
    """One version still on the train: its counts, then its goals by verdict."""
    counts = {verdict: sum(g.verdict == verdict for g in goals) for verdict in VERDICTS}
    summary = ", ".join(f"{counts[v]} {v}" for v in VERDICTS if counts[v])
    out = [f"## {manifest['version']} — {manifest.get('status', 'planned')}", "",
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
    return out


def pairs(specs: list[str]) -> dict[str, pathlib.Path]:
    found = {}
    for spec in specs:
        name, sep, raw = spec.partition("=")
        if not sep or not name or not raw:
            raise Unread(f"--checkout wants name=path, got {spec!r}")
        found[name] = within_cwd(raw)
    return found


@dataclass
class Reading:
    """Everything one run reads: each version with its goals, the commit of every
    source, what could not be read, the checkouts and the open pull requests."""

    report: list[tuple[dict, list[Standing]]]
    sources: dict[str, str]
    unread: dict[str, str]
    checkouts: dict[str, pathlib.Path]
    prs: dict[str, list[dict]]


def read(spec_arg: str, checkout_args: list[str], ref: str, prs_arg: str | None,
         versions: list[str]) -> Reading:
    """Read every source once, raising `Unread` only for what stops the whole
    report: the spec, an argument or the pull request file.

    Every version reads the same repositories at the same revision, so each is
    read once per run; a run starts from nothing, whatever ran before it."""
    citations.cache_clear()
    tracker.cache_clear()
    if not REVISION.match(ref):
        raise Unread(f"`{ref}` is not a revision")
    unread: dict[str, str] = {}
    checkouts = pairs(checkout_args)
    spec = within_cwd(spec_arg)
    sources = {"spec": revision("spec", spec, "HEAD")}
    for name, path in checkouts.items():
        try:
            sources[name] = revision(name, path, ref)
        except Unread as broken:
            unread[name] = str(broken)
    prs = json.loads(within_cwd(prs_arg).read_text(encoding="utf-8")) if prs_arg else {}
    claimed = claims(prs)
    report = [(m, standing(m, checkouts, ref, claimed, unread))
              for m in manifests(spec, versions)]
    return Reading(report, sources, unread, checkouts, prs)


def warn(unread: dict[str, str]) -> None:
    """One annotation per repository that could not be read."""
    for repo, reason in sorted(unread.items()):
        print(f"::warning::{repo} was not read, and the goals searched there read unknown: {reason}")


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
    try:
        reading = read(args.spec, args.checkout, args.ref, args.prs, args.version)
    except (Unread, OSError, json.JSONDecodeError) as broken:
        print(f"::error::{broken}")
        return 2
    warn(reading.unread)
    page = markdown(reading.report, args.ref, reading.unread, over_cap(reading.prs))
    data = as_data(reading.report, args.ref, reading.sources, reading.unread,
                   datetime.datetime.now(datetime.UTC))
    if args.markdown:
        within_cwd(args.markdown).write_text(page, encoding="utf-8")
    if args.json_out:
        within_cwd(args.json_out).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    if not (args.markdown or args.json_out):
        print(page, end="")
    return 0

if __name__ == "__main__":
    sys.exit(main())
