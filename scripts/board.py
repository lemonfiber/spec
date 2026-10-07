#!/usr/bin/env python3
"""The board snapshot: everything the frontpage's roadmap and board render.

`goals.py` says where every goal stands. The frontpage asks more than that of
the same sources: the catalogue with every requirement's text, each tracker row,
each open pull request with its title and author, the repositories, the releases
and the proposals. This writes all of it as one `board.json`, in the shape
`70-operations/board-format.md` documents, reading the manifests, the trackers
and the citations through `goals.py`, so a verdict on the board cannot differ
from the report's or the gate's.

Run from the root of the spec checkout. `--checkout`, `--ref` and `--prs` are
`goals.py`'s. `--issues` is a JSON list of the spec's open `rfc` issues, as the
forge's REST API lists them. The core's changelog is read from the `lemonfiber`
checkout at `--ref`.

Usage:
  board.py --checkout <name>=<path> [...] [--ref origin/main] [--prs prs.json]
           [--issues issues.json] --json board.json [--hash board.sha256]

`--hash` writes the SHA-256 of the snapshot with `generated_at` removed, so a
run can tell whether the content changed since the last one. Exit 0 having
written it, a repository that could not be read included; 2 where the spec, an
argument or an input file could not be read.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import sys
import tomllib

import gen_board
import goals
from catalogue import features as load_features
from integrity import elsewhere
from paths import within_cwd
from patterns import CITE, REQ_DEF_ROW, SPEC_TRAILER, ordered

#: The shape of `board.json`. A field removed, renamed or given another meaning
#: raises it; a field added does not.
FORMAT = 1
#: Where the core keeps one JSON file per release.
CHANGELOG = "reference/changelog"
#: The repository whose changelog the releases are read from.
CORE = "lemonfiber"
#: Every repository in the organisation, the map's and the ungoverned ones.
REPOS = "30-repos/repos.toml"
#: The group a repository outside the map is listed under.
UNGOVERNED = "ungoverned"
#: The catalogue's page, whose section headings name the areas.
FEATURES_README = "10-functional/features/README.md"
#: `## A — Getting started`: an area's letter and name, as the catalogue's page
#: heads each section.
AREA_HEADING = re.compile(r"^## ([A-Z]) — (.+)$", re.MULTILINE)
#: The keywords of RFC 2119 a requirement can carry, strongest first.
KEYWORDS = ("MUST", "SHOULD", "MAY")
#: A retired row starts with one of these, in italics.
RETIRED = re.compile(r"^\*(Withdrawn|Superseded)\b")
#: A feature's identifier, which is also how its requirements are prefixed.
FEATURE_ID = re.compile(r"^[A-Z]\d+$")


def areas(features: dict[str, dict]) -> list[dict]:
    """Each area in use: its letter, the name the catalogue's page gives it, and
    the directory its features live in."""
    names = dict(AREA_HEADING.findall(pathlib.Path(FEATURES_README).read_text(encoding="utf-8")))
    directories = {fm["area"]: fm["path"].split("/")[2] for fm in features.values()}
    return [{"id": area, "name": names.get(area), "directory": directory}
            for area, directory in sorted(directories.items())]


def keyword(text: str) -> str | None:
    """The strongest RFC 2119 keyword a requirement uses."""
    return next((word for word in KEYWORDS if re.search(rf"\b{word}\b", text)), None)


def status_of(text: str, draft: bool) -> str:
    """`withdrawn` or `superseded` where the row says so, `draft` where its
    feature is, otherwise `accepted`."""
    retired = RETIRED.match(text)
    if retired:
        return retired.group(1).lower()
    return "draft" if draft else "accepted"


def requirement(ident: str, raw: str, owner: str, draft: bool, versions: list[str]) -> dict:
    """One row of a requirements table, as the snapshot holds it."""
    text = raw.strip()
    status = status_of(text, draft)
    replaced = CITE.findall(text) if status == "superseded" else []
    prefix = ident.rsplit("-R", 1)[0]
    return {"id": ident, "owner": owner,
            "namespace": "feature" if FEATURE_ID.match(prefix) else prefix,
            "keyword": keyword(text), "text": text, "status": status,
            "replaced_by": replaced[0] if replaced else None, "versions": versions}


def requirements(features: dict[str, dict], locked_by: dict[str, list[str]]) -> list[dict]:
    """Every requirement the specification defines, with its text and status."""
    by_path = {fm["path"]: fid for fid, fm in features.items()}
    root = pathlib.Path(".")
    found = []
    for doc in sorted(d for d in root.rglob("*.md") if not elsewhere(d, root)):
        owner = by_path.get(doc.as_posix(), doc.as_posix())
        draft = owner in features and features[owner]["status"] == "draft"
        found += [requirement(ident, raw, owner, draft, locked_by.get(ident, []))
                  for ident, raw in REQ_DEF_ROW.findall(doc.read_text(encoding="utf-8"))]
    return sorted(found, key=lambda r: (r["owner"], ordered_id(r["id"])))


def ordered_id(ident: str) -> tuple[str, int]:
    prefix, _, number = ident.rpartition("-R")
    return prefix, int(number)


def versions(reading: goals.Reading) -> list[dict]:
    """Each manifest in train order, with the verdict on each goal."""
    fields = ("milestone", "delivers", "released_on", "released_as")
    return [{"version": m["version"], "status": m.get("status", "planned"),
             **{name: m.get(name) for name in fields},
             "repos": m.get("repos", []),
             "satisfied_in": m.get("satisfied_in", m.get("repos", [])),
             "prereleases": m.get("prerelease", []),
             "goals": [g.as_json() for g in standing]}
            for m, standing in reading.report]


def trackers(reading: goals.Reading, ref: str) -> list[dict]:
    """Each repository a version is satisfied in, and the rows its tracker holds."""
    searched = sorted({name for m, _ in reading.report
                       for name in m.get("satisfied_in", m.get("repos", []))})
    out = []
    for name in searched:
        if name in reading.unread:
            out.append({"repo": name, "present": False, "rows": []})
            continue
        rows = goals.tracker(name, reading.checkouts[name], ref)
        out.append({"repo": name, "present": True,
                    "rows": [{"id": r.id, "state": r.state, "evidence": list(r.evidence),
                              "landed": r.landed} for r in rows]})
    return out


def cites(pr: dict) -> list[str]:
    """The identifiers a pull request cites in `Spec:` lines, body and commits."""
    texts = [pr.get("body") or ""] + [c.get("message", "") for c in pr.get("commits") or []]
    found = {ident for text in texts for trailer in SPEC_TRAILER.findall(text)
             for ident in CITE.findall(trailer)}
    return sorted(found, key=ordered_id)


def pulls(prs: dict[str, list[dict]]) -> list[dict]:
    """Each open pull request, with what it cites."""
    out = []
    for repo, listed in sorted(prs.items()):
        for pr in listed:
            author = (pr.get("author") or {}).get("login")
            out.append({
                "repo": repo, "number": pr["number"], "url": pr["url"],
                "title": pr.get("title"), "author": author,
                "bot": (pr.get("author") or {}).get("__typename") == "Bot",
                "draft": bool(pr.get("isDraft")), "created_at": pr.get("createdAt"),
                "updated_at": pr.get("updatedAt"), "head": pr.get("headRefName"),
                "cites": cites(pr),
            })
    return out


def tracker_state(name: str, present: dict[str, bool], unread: dict[str, str]) -> str | None:
    """Whether a repository's tracker was read, or null where no version is
    satisfied in it and so none is asked of it."""
    if name in unread:
        return "unread"
    if name not in present:
        return None
    return "present" if present[name] else "absent"


def repos(listed: list[dict], trackers_: list[dict], unread: dict[str, str]) -> list[dict]:
    """Every repository in the organisation, the map's and the ungoverned ones,
    with its open pull requests and its tracker."""
    data = tomllib.loads(pathlib.Path(REPOS).read_text(encoding="utf-8"))
    present = {t["repo"]: t["present"] for t in trackers_}
    rows = data.get("repo", []) + [{**r, "group": UNGOVERNED} for r in data.get("ungoverned", [])]
    return [{"name": repo["name"], "group": repo.get("group"), "lang": repo.get("lang"),
             "note": repo.get("note"), "pages": repo.get("spec", []),
             "open_pulls": sum(p["repo"] == repo["name"] for p in listed),
             "tracker": tracker_state(repo["name"], present, unread)}
            for repo in rows]


def releases(reading: goals.Reading, ref: str) -> list[dict]:
    """Each release the core's changelog records, newest last, as the core wrote it."""
    if CORE in reading.unread or CORE not in reading.checkouts:
        return []
    path = reading.checkouts[CORE]
    listed = goals.git(path, "ls-tree", "--name-only", f"{ref}:{CHANGELOG}")
    out = []
    for name in listed.stdout.split():
        if not name.endswith(".json"):
            continue
        shown = goals.git(path, "show", f"{ref}:{CHANGELOG}/{name}").stdout
        try:
            entry = json.loads(shown)
        except json.JSONDecodeError as broken:
            raise goals.Unread(f"{CORE}: {CHANGELOG}/{name} is not JSON: {broken}") from broken
        out.append({"version": entry["version"], "tag": entry.get("tag"),
                    "released_on": entry.get("released_on"), "delivers": entry.get("delivers"),
                    "groups": [{"title": g.get("title"),
                                "entries": [{"summary": e.get("summary"),
                                             "requirements": e.get("requirements", []),
                                             "reference": e.get("reference")}
                                            for e in g.get("entries", [])]}
                               for g in entry.get("groups") or []]})
    return sorted(out, key=lambda r: ordered(r["version"]))


def proposals(features: dict[str, dict], requirements_: list[dict],
              issues: list[dict]) -> list[dict]:
    """The pre-approval feed: Draft features, Draft requirements, open `rfc` issues."""
    out = [{"kind": "feature", "id": fid, "title": fm["title"], "url": None}
           for fid, fm in sorted(features.items(), key=lambda kv: (kv[0][0], int(kv[0][1:])))
           if fm["status"] == "draft"]
    out += [{"kind": "requirement", "id": r["id"], "title": r["text"], "url": None}
            for r in requirements_ if r["status"] == "draft"]
    out += [{"kind": "rfc", "id": issue["number"], "title": issue["title"],
             "url": issue["html_url"]} for issue in issues if "pull_request" not in issue]
    return out


def snapshot(reading: goals.Reading, ref: str, issues: list[dict],
             now: datetime.datetime) -> dict:
    """The whole snapshot, in the documented shape."""
    feats = load_features()
    locked_by: dict[str, list[str]] = {}
    for manifest, _ in reading.report:
        for goal in manifest.get("goals", []):
            locked_by.setdefault(goal, []).append(manifest["version"])
    rows = gen_board.build_rows(feats, gen_board.load_versions())
    reqs = requirements(feats, locked_by)
    trackers_ = trackers(reading, ref)
    listed = pulls(reading.prs)
    return {
        "format": FORMAT,
        "generated_at": now.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ref": ref,
        "sources": reading.sources,
        "unread": [{"repo": repo, "reason": reason}
                   for repo, reason in sorted(reading.unread.items())],
        "areas": areas(feats),
        "features": rows,
        "requirements": reqs,
        "versions": versions(reading),
        "trackers": trackers_,
        "pulls": listed,
        "repos": repos(listed, trackers_, reading.unread),
        "releases": releases(reading, ref),
        "proposals": proposals(feats, reqs, issues),
    }


def content_hash(data: dict) -> str:
    """The SHA-256 of the snapshot without the time it was written, so two runs
    over the same sources agree."""
    kept = {key: value for key, value in data.items() if key != "generated_at"}
    return hashlib.sha256(json.dumps(kept, sort_keys=True).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--checkout", action="append", default=[], metavar="name=path")
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--prs")
    parser.add_argument("--issues")
    parser.add_argument("--json", dest="json_out", required=True)
    parser.add_argument("--hash")
    args = parser.parse_args()
    try:
        reading = goals.read(".", args.checkout, args.ref, args.prs, [])
        issues = (json.loads(within_cwd(args.issues).read_text(encoding="utf-8"))
                  if args.issues else [])
        data = snapshot(reading, args.ref, issues, datetime.datetime.now(datetime.UTC))
    except (goals.Unread, OSError, json.JSONDecodeError) as broken:
        print(f"::error::{broken}")
        return 2
    goals.warn(reading.unread)
    within_cwd(args.json_out).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    if args.hash:
        within_cwd(args.hash).write_text(content_hash(data) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
