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
           [--previous published.sha256 --changed changed.txt]

`--hash` writes the SHA-256 of the snapshot with `generated_at` removed, so a
run can tell whether the content changed since the last one. `--previous` names
the hash the last published snapshot carried, and `--changed` the file to write
`true` or `false` to: true where the content differs, or where nothing was
published before, since a snapshot nobody has seen is news. Exit 0 having
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
import status_check
from catalogue import FEATURES_README
from catalogue import areas as area_names
from catalogue import features as load_features
from claims import CAP, STALE_AFTER, is_bot
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
#: The keywords of RFC 2119 a requirement can carry, strongest first.
KEYWORDS = ("MUST", "SHOULD", "MAY")
#: A retired row starts with one of these, in italics.
RETIRED = re.compile(r"^\*(Withdrawn|Superseded)\b")
#: A row marked Draft in place, ahead of the review that hardens it (GOV-R42).
DRAFT_ROW = re.compile(r"^\*Draft:\*")
#: A feature's identifier, which is also how its requirements are prefixed.
FEATURE_ID = re.compile(r"^[A-Z]\d+$")
#: How the forge writes a time.
STAMP = "%Y-%m-%dT%H:%M:%SZ"


def areas(features: dict[str, dict]) -> list[dict]:
    """Each area in use: its letter, the name the catalogue's page gives it, and
    the directory its features live in."""
    names = area_names(pathlib.Path(FEATURES_README).read_text(encoding="utf-8"))
    directories = {fm["area"]: fm["path"].split("/")[2] for fm in features.values()}
    return [{"id": area, "name": names.get(area), "directory": directory}
            for area, directory in sorted(directories.items())]


def keyword(text: str) -> str | None:
    """The strongest RFC 2119 keyword a requirement uses."""
    return next((word for word in KEYWORDS if re.search(rf"\b{word}\b", text)), None)


def status_of(text: str, draft: bool) -> str:
    """`withdrawn` or `superseded` where the row says so, `draft` where its
    feature is or the row is marked `*Draft:*`, otherwise `accepted`."""
    retired = RETIRED.match(text)
    if retired:
        return retired.group(1).lower()
    return "draft" if draft or DRAFT_ROW.match(text) else "accepted"


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


def tracker_file(name: str, checkout: pathlib.Path, ref: str) -> str | None:
    """The one file a repository's tracker rows are read from, or None for a
    tracker split by feature, where each row is in its feature's own file."""
    split = goals.git(checkout, "ls-tree", "--name-only", f"{ref}:{status_check.DIRECTORY}")
    if split.returncode == 0:
        return None
    shown = goals.git(checkout, "show", f"{ref}:{status_check.FILE}").stdout
    kept = status_check.parse(shown, f"{name}:{status_check.FILE}", name)
    return status_check.FILE if kept is not None else goals.LEGACY


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
        kept_in = tracker_file(name, reading.checkouts[name], ref)
        out.append({"repo": name, "present": True,
                    "rows": [{"id": r.id, "state": r.state, "evidence": list(r.evidence),
                              "landed": r.landed,
                              "path": kept_in or f"{status_check.DIRECTORY}/"
                                                 f"{status_check.family(r.id)}.toml"}
                             for r in rows]})
    return out


def cites(pr: dict) -> list[str]:
    """The identifiers a pull request cites in `Spec:` lines, body and commits."""
    texts = [pr.get("body") or ""] + [c.get("message", "") for c in pr.get("commits") or []]
    found = {ident for text in texts for trailer in SPEC_TRAILER.findall(text)
             for ident in CITE.findall(trailer)}
    return sorted(found, key=ordered_id)


def last_commit(pr: dict) -> str | None:
    """When the newest commit of a pull request was made, as the forge lists them
    oldest first."""
    commits = pr.get("commits") or []
    return commits[-1].get("committedDate") if commits else None


def stale(draft: bool, since: str | None, now: datetime.datetime) -> bool:
    """Whether a draft's claim has gone without a commit for longer than
    `STALE_AFTER`. A pull request ready for review is not a claim waiting on work."""
    if not draft or since is None:
        return False
    then = datetime.datetime.strptime(since, STAMP).replace(tzinfo=datetime.UTC)
    return now - then > STALE_AFTER


def pulls(prs: dict[str, list[dict]], now: datetime.datetime) -> list[dict]:
    """Each open pull request, with what it cites and whether its claim is stale."""
    out = []
    for repo, listed in sorted(prs.items()):
        for pr in listed:
            author = (pr.get("author") or {}).get("login")
            draft = bool(pr.get("isDraft"))
            committed = last_commit(pr)
            out.append({
                "repo": repo, "number": pr["number"], "url": pr["url"],
                "title": pr.get("title"), "author": author,
                "bot": is_bot(pr),
                "draft": draft, "created_at": pr.get("createdAt"),
                "updated_at": pr.get("updatedAt"), "head": pr.get("headRefName"),
                "last_commit_at": committed,
                "stale": stale(draft, committed or pr.get("createdAt"), now),
                "cites": cites(pr),
            })
    return out


def contested(reading: goals.Reading, listed: list[dict]) -> list[dict]:
    """Each goal of a version not yet out that more than one open pull request
    from people or agents cites, with those pull requests as `repo#number`."""
    open_goals = {goal for manifest, _ in reading.report
                  if manifest.get("status") not in goals.FINISHED
                  for goal in manifest.get("goals", [])}
    claims: dict[str, list[str]] = {}
    for pr in listed:
        if pr["bot"]:
            continue
        for ident in pr["cites"]:
            if ident in open_goals:
                claims.setdefault(ident, []).append(f"{pr['repo']}#{pr['number']}")
    return [{"id": ident, "pulls": claims[ident]}
            for ident in sorted(claims, key=ordered_id) if len(claims[ident]) > 1]


def tracker_state(name: str, present: dict[str, bool], unread: dict[str, str]) -> str | None:
    """Whether a repository's tracker was read, or null where no version is
    satisfied in it and so none is asked of it."""
    if name in unread:
        return "unread"
    if name not in present:
        return None
    return "present" if present[name] else "absent"


def repos(listed: list[dict], read: set[str], trackers_: list[dict],
          unread: dict[str, str]) -> list[dict]:
    """Every repository in the organisation, the map's and the ungoverned ones,
    with its open pull requests, how many of them the cap counts, and its tracker.
    The counts are null for a repository whose pull requests were not read, since
    nought would say that it holds none."""
    data = tomllib.loads(pathlib.Path(REPOS).read_text(encoding="utf-8"))
    present = {t["repo"]: t["present"] for t in trackers_}
    rows = data.get("repo", []) + [{**r, "group": UNGOVERNED} for r in data.get("ungoverned", [])]
    out = []
    for repo in rows:
        own = [p for p in listed if p["repo"] == repo["name"]]
        counted = sum(not p["bot"] for p in own) if repo["name"] in read else None
        out.append({"name": repo["name"], "group": repo.get("group"),
                    "lang": repo.get("lang"), "note": repo.get("note"),
                    "pages": repo.get("spec", []),
                    "open_pulls": len(own) if counted is not None else None,
                    "counted_pulls": counted,
                    "over_cap": counted > CAP if counted is not None else None,
                    "tracker": tracker_state(repo["name"], present, unread)})
    return out


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
    listed = pulls(reading.prs, now)
    return {
        "format": FORMAT,
        "generated_at": now.astimezone(datetime.UTC).strftime(STAMP),
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
        "claims": {"cap": CAP, "stale_days": STALE_AFTER.days},
        "contested": contested(reading, listed),
        "repos": repos(listed, set(reading.prs), trackers_, reading.unread),
        "releases": releases(reading, ref),
        "proposals": proposals(feats, reqs, issues),
    }


def content_hash(data: dict) -> str:
    """The SHA-256 of the snapshot without the time it was written, so two runs
    over the same sources agree."""
    kept = {key: value for key, value in data.items() if key != "generated_at"}
    return hashlib.sha256(json.dumps(kept, sort_keys=True).encode("utf-8")).hexdigest()


def changed(previous: str | None, current: str) -> bool:
    """Whether the content moved since the hash the last published snapshot
    carried; anything that is not a hash, or no hash at all, counts as moved."""
    return previous is None or previous.strip() != current


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--checkout", action="append", default=[], metavar="name=path")
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--prs")
    parser.add_argument("--issues")
    parser.add_argument("--json", dest="json_out", required=True)
    parser.add_argument("--hash")
    parser.add_argument("--previous")
    parser.add_argument("--changed")
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
    digest = content_hash(data)
    if args.hash:
        within_cwd(args.hash).write_text(digest + "\n", encoding="utf-8")
    if args.changed:
        before = within_cwd(args.previous) if args.previous else None
        published = before.read_text(encoding="utf-8") if before and before.is_file() else None
        moved = changed(published, digest)
        within_cwd(args.changed).write_text(f"{str(moved).lower()}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
