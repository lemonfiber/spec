#!/usr/bin/env python3
"""Every registered plugin still validates against the version going out — OPS-R68.

A plugin rides the train version-pinned. It declares the manifest generation it is
written in, the registry declares the version the train holds it to, and every run
that would cut a tag re-reads both and re-reads the report its proofs left. One that
no longer validates blocks the run.

The hard part is not the check, it is the silence. A registry that could not be read,
a repository that was never created, a manifest that is absent, a report that is
missing — each of those is a question this could decline to answer, and a gate that
declines reports success about the part it could read. So every one of them fails by
name, and the only pass is a plugin that was found, parsed, matched and proven.

Every number compared here is the plugin's own. `plugin.toml` says which manifest
generation it is written in; `targets.toml` says which release it is validated and
proved against. The registry says only where to look, because a pin held in two
places is two statements of one fact and they disagree the day one is edited.

What a plugin targets is also what keeps this from being retroactive: a release
below it is not that plugin's business and the plugin is not even cloned. At or
above it, nothing about it may be missing.

Usage:
  check_plugins.py --version X.Y.Z --schema N \\
                   [--registry 70-operations/plugins.toml] \\
                   [--checkout <repo>=<path> ...]

Exit 0 = every plugin that rides this version validates, or none rides it;
1 = named plugins do not; 2 = the question could not be answered.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tomllib

from patterns import VERSION as VERSION_RE

REGISTRY = "70-operations/plugins.toml"

#: Every field a registry entry must carry. Absent ones are named together rather
#: than one per run, because a registry is edited by hand and a half-written entry
#: usually has more than one thing wrong with it.
FIELDS = ("id", "repo", "manifest", "targets", "report")


def within_cwd(raw: str) -> pathlib.Path:
    """Resolve a path the command line supplied, refusing anything outside the tree.

    The same guard `gate.py` holds its `--repo` arguments to, for the same reason:
    every path this reads arrives as an argument, and a gate that will read a file
    anywhere on the machine is a gate somebody can point at one.
    """
    path = pathlib.Path(raw).resolve()
    if not path.is_relative_to(pathlib.Path.cwd().resolve()):
        print(f"::error::path escapes the working directory: {raw}")
        raise SystemExit(2)
    return path


def ordered(version: str) -> tuple[int, ...]:
    """A version as numbers, because as text 0.10.0 sorts below 0.9.0."""
    return tuple(int(part) for part in version.split("."))


def load_registry(path: pathlib.Path) -> list[dict]:
    """The registry, or a refusal. An unreadable one is never an empty one."""
    if not path.is_file():
        print(f"::error::no plugin registry at {path}")
        raise SystemExit(2)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as broken:
        print(f"::error::{path} cannot be read: {broken}")
        raise SystemExit(2) from broken
    entries = data.get("plugin")
    if entries is None:
        print(
            f"::error::{path} declares no [[plugin]]; a registry holding none says so "
            "with an empty list rather than by omitting it"
        )
        raise SystemExit(2)
    return entries


def malformed(entry: dict, index: int) -> list[str]:
    """What this entry is missing, named against its position in the file."""
    missing = [field for field in FIELDS if field not in entry]
    if missing:
        named = entry.get("id", f"entry {index}")
        return [f"{named} declares no {', '.join(missing)}"]
    return []


def targeted(root: pathlib.Path, entry: dict) -> tuple[str | None, str | None]:
    """Which release this plugin says it is validated against, or why that is unreadable."""
    path = root / entry["targets"]
    plugin = entry["id"]
    if not path.is_file():
        return None, f"{plugin} has no {entry['targets']} at {path}"
    try:
        declared = tomllib.loads(path.read_text(encoding="utf-8")).get("lemonfiber")
    except tomllib.TOMLDecodeError as broken:
        return None, f"{plugin}'s {entry['targets']} cannot be read: {broken}"
    if declared is None:
        return None, f"{plugin}'s {entry['targets']} names no lemonfiber release"
    if not VERSION_RE.match(str(declared)):
        return None, f"{plugin} targets {declared!r}, which is not X.Y.Z"
    return str(declared), None


def rides(targets: str, version: str) -> bool:
    """Whether this plugin is gated on the version being cut."""
    return ordered(version) >= ordered(targets)


def read_json(path: pathlib.Path, what: str, plugin: str) -> tuple[dict | None, str | None]:
    """A JSON document the plugin's own CI left, or why it could not be read."""
    if not path.is_file():
        return None, f"{plugin} has no {what} at {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as broken:
        return None, f"{plugin}'s {what} at {path} cannot be read: {broken}"


def check_manifest(root: pathlib.Path, entry: dict, schema: int) -> list[str]:
    """The plugin's own manifest, against the generation this release carries."""
    path = root / entry["manifest"]
    plugin = entry["id"]
    if not path.is_file():
        return [f"{plugin} has no manifest at {path}"]
    try:
        manifest = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as broken:
        return [f"{plugin}'s manifest at {path} cannot be read: {broken}"]
    declared = manifest.get("schema_version")
    if declared is None:
        return [f"{plugin}'s manifest declares no schema_version"]
    if declared != schema:
        return [f"{plugin} pins manifest schema {declared}; this release carries {schema}"]
    return []


def check_report(root: pathlib.Path, entry: dict, version: str) -> list[str]:
    """The report the plugin's proofs left, which has to exist and has to say passed."""
    plugin = entry["id"]
    report, why = read_json(root / entry["report"], "proof report", plugin)
    if why:
        return [why]
    against = report.get("lemonfiber")
    if against != version:
        elsewhere = (
            f"{plugin}'s proofs were run against {against or 'nothing stated'}, "
            f"not {version}"
        )
        return [elsewhere]
    proofs = report.get("proofs")
    if not proofs:
        nothing = (
            f"{plugin}'s report names no proof; a plugin that proved nothing is not "
            "a plugin whose proofs passed"
        )
        return [nothing]
    failed = [
        f"{plugin}'s proof {proof.get('id', '(unnamed)')} is "
        f"{proof.get('outcome', 'not stated')}"
        for proof in proofs
        if proof.get("outcome") != "passed"
    ]
    return failed


def checkouts(specs: list[str]) -> dict[str, pathlib.Path]:
    """Where each plugin repository was cloned, as the workflow arranges them."""
    found: dict[str, pathlib.Path] = {}
    for spec in specs:
        if "=" not in spec:
            print(f"::error::--checkout wants repo=path, got {spec!r}")
            raise SystemExit(2)
        name, _, raw = spec.partition("=")
        found[name] = within_cwd(raw)
    return found


def evaluate(entries: list[dict], version: str, schema: int, where: dict[str, pathlib.Path]) -> tuple[list[str], int]:
    """Every problem across every plugin that rides this version, and how many did."""
    problems: list[str] = []
    gated = 0
    for index, entry in enumerate(entries):
        broken = malformed(entry, index)
        if broken:
            problems.extend(broken)
            continue
        root = where.get(entry["repo"])
        if root is None or not root.is_dir():
            unreachable = (
                f"{entry['id']} is registered as {entry['repo']} and no checkout of it "
                "was supplied — a plugin the gate cannot reach is not a plugin that passed"
            )
            problems.append(unreachable)
            continue
        # Read before the question of whether this plugin rides at all, because
        # the answer lives in the plugin. A registered repository that cannot say
        # what it targets is a fault at every version rather than one that starts
        # mattering later.
        targets, why = targeted(root, entry)
        if why is not None:
            problems.append(why)
            continue
        if not rides(str(targets), version):
            print(f"{entry['id']} targets {targets}; {version} predates it.")
            continue
        gated += 1
        problems.extend(check_manifest(root, entry, schema))
        problems.extend(check_report(root, entry, version))
    return problems, gated


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", required=True)
    ap.add_argument("--schema", required=True, type=int)
    ap.add_argument("--registry", default=REGISTRY)
    ap.add_argument("--checkout", action="append", default=[], metavar="repo=path")
    a = ap.parse_args()

    if not VERSION_RE.match(a.version):
        print(f"::error::--version wants X.Y.Z, got {a.version!r}")
        return 2

    entries = load_registry(within_cwd(a.registry))
    problems, gated = evaluate(entries, a.version, a.schema, checkouts(a.checkout))

    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        print(
            f"::error::{len(problems)} plugin problem(s); a plugin that no longer "
            "validates blocks the release (OPS-R68)."
        )
        return 1
    print(f"plugins ok: {gated} of {len(entries)} ride {a.version}, all validating.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
