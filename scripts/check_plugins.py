#!/usr/bin/env python3
"""Every registered plugin still validates against the version going out — OPS-R68, OPS-R72.

A plugin rides the train version-pinned. It declares the manifest generation it is
written in, the registry declares where to look, and every run that would cut a tag
proves each plugin riding that version itself: with the candidate build of the core
commit it is about to tag, in its own checkout of the plugin, through the reader the
registry pins to a commit of `plugin-template`. One that no longer validates blocks
the run.

The report a plugin commits is its record against the release it targets, and that
release is published. The version being cut is not, so no plugin can have proved
against it, and the gate does not ask one to. It puts the candidate where the reader
keeps the release it fetched, `.lemonfiber/<version>/<build>/lemonfiber`, points the
checkout's `targets.toml` at the version being cut, removes the committed report,
and runs `reader.py proofs`. The reader finds the release already there, asks it,
and writes a fresh report naming the version. That report is what the gate reads.

Nothing from a plugin's repository runs. What the gate reads there is data — the
manifest, the recordings, what it targets — and the reader that asks the candidate
about it is the pinned one. The directory the plugin's own reader sits in, `.github/`,
is removed from the checkout before the pinned reader is put where a reader sits, and
Python runs it isolated, so nothing in the plugin can stand in for a module it imports.

The hard part is not the check, it is the silence. A registry that could not be read,
a repository that was never created, a manifest that is absent, a reader that wrote
nothing — each of those is a question this could decline to answer, and a gate that
declines reports success about the part it could read. So every one of them fails by
name, and the only pass is a plugin that was found, parsed, matched and proven. A
reader that fetched a release of its own rather than using the candidate has proved
something other than what is being cut, and fails by name too.

A proof may also come back failing as declared: it fails on a recording its manifest
says it fails on, on the constraint the manifest names, for the reason it gives, and
nowhere else (`F10-R13`). That is not a pass and is never counted as one, and it is
not a failure either. The gate names each one, with what the report says failed and
why, and fails nothing on it. A declaration that no longer holds is already a failed
proof in the report (`F10-R14`), and fails the run as any other failed proof does.

Every number compared here is the plugin's own. `plugin.toml` says which manifest
generation it is written in; `targets.toml`, as committed, says which release it is
validated and proved against. The registry says only where to look, because a pin
held in two places is two statements of one fact and they disagree the day one is
edited.

What a plugin targets is also what keeps this from being retroactive: a release
below it is not that plugin's business and the plugin is not proved. At or above
it, nothing about it may be missing.

Usage:
  check_plugins.py --version X.Y.Z --schema N \\
                   --candidate <path to the built lemonfiber> --build <triple> \\
                   --reader <path to the pinned reader> \\
                   [--registry 70-operations/plugins.toml] \\
                   [--checkout <repo>=<path> ...]

`--build` is the name the release gives the build the candidate is, which is the
name the reader looks for on the machine it runs on.

Exit 0 = every plugin that rides this version validates, or none rides it;
1 = named plugins do not; 2 = the question could not be answered.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import tomllib
from typing import NamedTuple

from patterns import VERSION as VERSION_RE

REGISTRY = "70-operations/plugins.toml"

#: The outcome a proof report gives a proof failing where its manifest declares it
#: does. The one outcome besides passed that the gate does not fail on.
AS_DECLARED = "failing-as-declared"

#: What each declaration a proof failing as declared was held to must say: the
#: constraint that failed, what the answer held there, and why. A report that
#: leaves one out has named a failure without the reason that excuses it.
DECLARED = ("fixture", "constraint", "held", "reason")

#: Every field a registry entry must carry. Absent ones are named together rather
#: than one per run, because a registry is edited by hand and a half-written entry
#: usually has more than one thing wrong with it.
FIELDS = ("id", "repo", "manifest", "targets", "report")

#: What the registry's `[reader]` table must say: the repository the reader is
#: taken from, the commit it is pinned to, and where it sits in that repository —
#: which is also where it sits in a plugin, since it finds the plugin from there.
READER_FIELDS = ("repo", "commit", "path")

#: A commit as git names one in full. A branch or a short hash names whatever the
#: repository holds on the day, which is not a pin.
COMMIT_RE = re.compile(r"\A[0-9a-f]{40}\Z")

#: Where a plugin's reader keeps the release it fetched, beside the manifest, as
#: `<version>/<build>/lemonfiber`. A release already there is the one it asks.
CACHE = ".lemonfiber"

#: The file the release's binary is, inside that layout.
BINARY = "lemonfiber"

#: How long one plugin's proofs may take. They run against recordings, so a reader
#: still going after this is one that will not finish.
PROOFS_TIMEOUT_S = 600

#: A build name as a release names one: a target triple. It becomes a directory in
#: the plugin's checkout, so nothing that could climb out of one passes.
BUILD_RE = re.compile(r"\A[a-z0-9_]+(?:-[a-z0-9_]+)+\Z")


class Sources(NamedTuple):
    """What the gate brings to every plugin it proves."""

    #: The binary built from the core commit the run cuts.
    candidate: pathlib.Path
    #: The name the release gives that build.
    build: str
    #: The pinned reader, as fetched.
    reader: pathlib.Path
    #: Where a reader sits in a plugin, as the registry says.
    at: str


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


def read_registry(path: pathlib.Path) -> dict:
    """The registry as parsed, or a refusal. An unreadable one is never an empty one."""
    if not path.is_file():
        print(f"::error::no plugin registry at {path}")
        raise SystemExit(2)
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as broken:
        print(f"::error::{path} cannot be read: {broken}")
        raise SystemExit(2) from broken


def load_reader(path: pathlib.Path) -> dict:
    """The reader the registry pins, or a refusal naming what the pin leaves out."""
    pin = read_registry(path).get("reader")
    if not isinstance(pin, dict):
        print(f"::error::{path} pins no [reader]; the gate proves every plugin through one")
        raise SystemExit(2)
    missing = [field for field in READER_FIELDS if not isinstance(pin.get(field), str) or not pin[field]]
    if missing:
        print(f"::error::{path}'s [reader] declares no {', '.join(missing)}")
        raise SystemExit(2)
    if not COMMIT_RE.match(pin["commit"]):
        print(f"::error::{path}'s [reader] pins {pin['commit']!r}, which is not a full commit")
        raise SystemExit(2)
    where = pathlib.PurePosixPath(pin["path"])
    if where.is_absolute() or ".." in where.parts or len(where.parts) < 2:
        print(f"::error::{path}'s [reader] path {pin['path']!r} is not a file inside a repository")
        raise SystemExit(2)
    return pin


def load_registry(path: pathlib.Path) -> list[dict]:
    """The registered plugins, or a refusal."""
    entries = read_registry(path).get("plugin")
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
    """A JSON document the plugin's reader wrote, or why it could not be read.

    Only asked once `prove` has seen the file there, so its absence is already named.
    """
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


def declared(plugin: str, proof: dict) -> tuple[list[str], list[str]]:
    """What a proof failing as declared says, or what it leaves out.

    Named rather than counted: the gate says every time which proof fails, where, on
    what, and why, so a reader of the run never takes the count for a pass.
    """
    named = proof.get("id", "(unnamed)")
    entries = proof.get("declared")
    if not isinstance(entries, list) or not entries:
        return [f"{plugin}'s proof {named} is {AS_DECLARED} and names no declaration"], []
    problems: list[str] = []
    lines: list[str] = []
    for entry in entries:
        entry = entry if isinstance(entry, dict) else {}
        missing = [field for field in DECLARED if entry.get(field) in (None, "")]
        if missing:
            problems.append(
                f"{plugin}'s proof {named} is {AS_DECLARED} and its declaration "
                f"names no {', '.join(missing)}"
            )
            continue
        place = f" at {entry['place']}" if entry.get("place") else ""
        lines.append(
            f"{plugin}'s proof {named} fails as declared on {entry['fixture']}: "
            f"{entry['constraint']}{place} held {entry['held']}. {entry['reason']}"
        )
    return problems, lines


def remove(path: pathlib.Path) -> None:
    """Whatever the checkout holds at this path, gone without following a link in it."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def install(root: pathlib.Path, reader: pathlib.Path, at: str) -> pathlib.Path:
    """The pinned reader, put where a reader sits in the plugin, with the plugin's own
    harness gone. Returns where it now is.

    The harness is the top-level directory the reader sits in, `.github/`, and the
    plugin's own reader is in it. It is removed whole, whether it is a directory, a
    file or a link, because a link left in place would carry the reader out of the
    checkout and point it at whatever the link names.
    """
    remove(root / pathlib.PurePosixPath(at).parts[0])
    placed = root / at
    placed.parent.mkdir(parents=True)
    shutil.copyfile(reader, placed)
    return placed


def stage(root: pathlib.Path, entry: dict, version: str, candidate: pathlib.Path, build: str) -> pathlib.Path:
    """The checkout made to prove against the candidate, and where the candidate now is.

    The candidate goes where the reader keeps a release it fetched, `targets.toml`
    names the version being cut, and the committed report is removed, so a reader
    that writes nothing leaves nothing behind that could be read in its place. Each
    path written is cleared first, so a link the plugin committed there is replaced
    rather than written through.
    """
    remove(root / CACHE)
    held = root / CACHE / version / build / BINARY
    held.parent.mkdir(parents=True)
    shutil.copy2(candidate, held)
    targets = root / entry["targets"]
    remove(targets)
    targets.write_text(f'lemonfiber = "{version}"\n', encoding="utf-8")
    remove(root / entry["report"])
    return held


def transcript(plugin: str, said: str) -> None:
    """What the reader printed, shown as text rather than acted on.

    Its own error and notice lines would otherwise become annotations beside the
    gate's, saying the same thing twice in two voices. The token that turns command
    processing back on is one the reader cannot guess.
    """
    resume = secrets.token_hex(16)
    print(f"::group::{plugin}'s proofs against the candidate")
    print(f"::stop-commands::{resume}")
    print(said, end="" if said.endswith("\n") else "\n")
    print(f"::{resume}::")
    print("::endgroup::")


def why_unrun(ran: subprocess.CompletedProcess) -> str:
    """The reader's own account of why it wrote no report."""
    errors = [line.removeprefix("::error::") for line in ran.stdout.splitlines()
              if line.startswith("::error::")]
    if errors:
        return "; ".join(errors)
    last = ran.stderr.strip().splitlines()
    return last[-1] if last else f"it exited {ran.returncode} and said nothing"


def prove(root: pathlib.Path, entry: dict, version: str, sources: Sources) -> tuple[list[str], int]:
    """Run the plugin's proofs through the pinned reader with the candidate, or say
    why they did not run.

    The second value is the reader's exit status, for the report to be read against.
    """
    plugin = entry["id"]
    reader = install(root, sources.reader, sources.at)
    held = stage(root, entry, version, sources.candidate, sources.build)
    try:
        ran = subprocess.run(
            # Isolated: neither the reader's directory nor the environment's Python
            # settings decide what it imports.
            [sys.executable, "-I", str(reader), "proofs"],
            cwd=root, capture_output=True, text=True, timeout=PROOFS_TIMEOUT_S, check=False,
        )
    except subprocess.TimeoutExpired:
        return [f"{plugin}'s proofs did not finish within {PROOFS_TIMEOUT_S} seconds"], 1
    transcript(plugin, ran.stdout + ran.stderr)
    fetched = sorted(
        str(path.relative_to(root)) for path in (root / CACHE).rglob(BINARY)
        if path.is_file() and path != held
    )
    if fetched:
        elsewhere = (
            f"{plugin}'s reader fetched {', '.join(fetched)} rather than proving the "
            f"candidate at {held.relative_to(root)}"
        )
        return [elsewhere], ran.returncode
    if not (root / entry["report"]).is_file():
        return [f"{plugin}'s proofs could not be run against the candidate: {why_unrun(ran)}"], ran.returncode
    return [], ran.returncode


def check_report(root: pathlib.Path, entry: dict, version: str) -> tuple[list[str], list[str]]:
    """The report the plugin's proofs wrote: every proof passed or failing as declared.

    The second list names each proof failing as declared. None of them is a pass.
    """
    plugin = entry["id"]
    report, why = read_json(root / entry["report"], "proof report", plugin)
    if why:
        return [why], []
    against = report.get("lemonfiber")
    if against != version:
        elsewhere = (
            f"{plugin}'s proofs were run against {against or 'nothing stated'}, "
            f"not {version}"
        )
        return [elsewhere], []
    proofs = report.get("proofs")
    if not proofs:
        nothing = (
            f"{plugin}'s report names no proof; a plugin that proved nothing is not "
            "a plugin whose proofs passed"
        )
        return [nothing], []
    problems: list[str] = []
    named: list[str] = []
    for proof in proofs:
        outcome = proof.get("outcome")
        if outcome == "passed":
            continue
        if outcome == AS_DECLARED:
            wrong, lines = declared(plugin, proof)
            problems.extend(wrong)
            named.extend(lines)
            continue
        problems.append(
            f"{plugin}'s proof {proof.get('id', '(unnamed)')} is {outcome or 'not stated'}"
        )
    return problems, named


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


def evaluate(
    entries: list[dict], version: str, schema: int, where: dict[str, pathlib.Path], sources: Sources
) -> tuple[list[str], list[str], int]:
    """Every problem across every plugin that rides this version, every proof failing
    as declared, and how many plugins ride."""
    problems: list[str] = []
    named: list[str] = []
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
        unproved, exited = prove(root, entry, version, sources)
        if unproved:
            problems.extend(unproved)
            continue
        wrong, lines = check_report(root, entry, version)
        if exited != 0 and not wrong:
            wrong = [f"{entry['id']}'s reader exited {exited} over a report naming no failure"]
        problems.extend(wrong)
        named.extend(lines)
    return problems, named, gated


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", required=True)
    ap.add_argument("--schema", required=True, type=int)
    ap.add_argument("--candidate", required=True, metavar="path")
    ap.add_argument("--build", required=True, metavar="triple")
    ap.add_argument("--reader", required=True, metavar="path")
    ap.add_argument("--registry", default=REGISTRY)
    ap.add_argument("--checkout", action="append", default=[], metavar="repo=path")
    a = ap.parse_args()

    if not VERSION_RE.match(a.version):
        print(f"::error::--version wants X.Y.Z, got {a.version!r}")
        return 2
    if not BUILD_RE.match(a.build):
        print(f"::error::--build wants a target triple, got {a.build!r}")
        return 2
    candidate = within_cwd(a.candidate)
    if not candidate.is_file():
        print(f"::error::no candidate build at {a.candidate}")
        return 2
    reader = within_cwd(a.reader)
    if not reader.is_file():
        print(f"::error::no reader at {a.reader}")
        return 2

    registry = within_cwd(a.registry)
    entries = load_registry(registry)
    sources = Sources(candidate, a.build, reader, load_reader(registry)["path"])
    problems, named, gated = evaluate(entries, a.version, a.schema, checkouts(a.checkout), sources)

    # Named before anything is decided, so a run that fails for another reason still
    # says which proofs fail as declared.
    for line in named:
        print(f"::notice::{line}")
    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        print(
            f"::error::{len(problems)} plugin problem(s); a plugin that no longer "
            "validates blocks the release (OPS-R68)."
        )
        return 1
    print(f"plugins ok: {gated} of {len(entries)} ride {a.version}, all proved with the candidate.")
    if named:
        print(
            f"{len(named)} proof(s) fail as declared, named above; "
            "none is counted as passed (OPS-R72)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
