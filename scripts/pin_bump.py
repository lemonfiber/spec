#!/usr/bin/env python3
"""A pin moved in a `plugin.toml` with every recording taken again from it — ARCH-R121, ARCH-R285, OPS-R87.

Two workflows move a pin this way: `upstream-pin`, moving an upstream's image to the
newest release of its major (`REPO-R98`), and `manifest-pin`, moving lemonfiber's own
image to what its repository published (`OPS-R91`). A moved digest leaves every
recording naming the old one refused (`ARCH-R121`), so each takes them again in the
same change. Each runs in two jobs. The job holding no secret builds lemonfiber and
runs the image; the job holding the release App's token commits, and trusts none of
what the first wrote. What both do alike is here; how each works its move out is
`upstream_pins.py`'s and `manifest_pin.py`'s.

    pin_bump.py reader    --workflow first-party-plugin.yml             the reader's repository and revision
    pin_bump.py record    --manifest plugin.toml --reader <dir>         every recording taken again; proofs.json written
    pin_bump.py stage     --manifest plugin.toml --main <main's plugin.toml> --move <move.json> --out <dir>
    pin_bump.py pins-only --before <commit> --after <commit> [--directory .]

`reader` prints `repository=` and `revision=` lines for `$GITHUB_OUTPUT`, read from the
workflow that runs the reader everywhere else, so the revision is written once.

`record` puts that reader, checked out from plugin-template, into the plugin, refusing a
plugin that carries one of its own. It asks `lemonfiber plugin record`, at the
lemonfiber `targets.toml` names, for every recording the manifest names, then has the
reader write `proofs.json` from them as the plugin's own check does (`ARCH-R285`). What
either says decides nothing: a failure is warned of, and the committing job reads which
recordings were taken from the files. The reader and the lemonfiber it fetched or built
are removed after.

`stage` copies the manifest, `proofs.json` and every recording of the new pin into a
directory that travels to the committing job as an artifact. There, `admitted_files`
refuses the bump unless every entry is a plain file, the manifest is main's with
exactly the move that job worked out itself, and every other file is `proofs.json` or a
recording the manifest names taken from exactly that pin.

`pins-only` prints `yes` where every path the push changed is one a pin moves, at the
plugin's root: `plugin.toml`, `proofs.json`, `targets.toml` and anything under
`recordings/`. Otherwise it prints `no`, and so it does where nothing changed or the
commit before cannot be read. A push that moves only a pin publishes no image, so
merging a pin's pull request never starts the next one (`OPS-R90`).

Every path named on the command line must lie inside the working directory, and no file
is read or written through a link (`paths.plain_read`, `paths.plain_write`).

Exit 0 = done, 1 = refused or unreadable (named on standard error), 2 = usage.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable

import paths
import plugin_pin
import registry
from check_bundle_pins import TARGETS

#: What a staged bump holds, and the most of each file read.
MANIFEST_FILE, PROOFS_FILE = "plugin.toml", "proofs.json"
MOVE_LIMIT, RECORDING_LIMIT = 64 * 1024, 1024 * 1024
MANIFEST_LIMIT = plugin_pin.MANIFEST_LIMIT
#: A contract as `speaks` names one, and a conformance case's file.
CONTRACT = re.compile(r"\A[a-z0-9][a-z0-9.-]*@\d+\Z")
CASE = re.compile(r"\A[a-z0-9][a-z0-9_-]*\.json\Z")
#: How many recordings left naming the old image a pull request lists by name.
STALE_LISTED = 20
#: What a bump that cannot be committed as it stands raises.
Refused = plugin_pin.Refused
#: Who signs a bump's commit off.
SIGNED = "Signed-off-by: lemonfiber release <info@nightworks.io>"
#: How the reader's repository and revision are written in the workflow that runs it.
READER = re.compile(r"(?m)^\s+READER_(REPOSITORY|REVISION):\s*(\S+)\s*$")
READER_REVISION = re.compile(r"\A[0-9a-f]{40}\Z")
READER_REPOSITORY = re.compile(r"\A[A-Za-z0-9-]+/[A-Za-z0-9._-]+\Z")
#: Where the reader sits in a plugin, and where the lemonfiber it fetches or builds is kept.
READER_HOME, READER_FILE, CACHE = ".github/reader", "reader.py", ".lemonfiber"
#: The files at a plugin's root a pin moves, and the directory its recordings sit under.
PIN_FILES, RECORDINGS = (MANIFEST_FILE, PROOFS_FILE, TARGETS), "recordings/"
#: A commit git has not got, as a push from nothing names its commit before.
NO_COMMIT = re.compile(r"\A0*\Z")


def recording_of(body: bytes) -> str:
    """What a recording says it was taken from, or nothing where it is not one."""
    try:
        read = json.loads(body)
    except ValueError:
        return ""
    return str(read.get("recorded_from", "")) if isinstance(read, dict) else ""


def stale(root: pathlib.Path, image: str, digest: str) -> list[str]:
    """Every plain recording under `root` taken from `image` at a digest other than `digest`.

    Read from the files rather than from what recorded them, so a recorder that left a
    recording behind, whatever it said of itself, cannot let a bump call itself clean.
    A directory whose name begins with a dot is the harness's, not the plugin's, and a
    link is never followed.
    """
    found = []
    for relative in paths.plain_files(root)[0]:
        if not relative.endswith(".json") or any(part.startswith(".") for part in relative.split("/")[:-1]):
            continue
        taken, _, at = recording_of(paths.plain_read(root, relative, RECORDING_LIMIT)).partition("@")
        if taken == image and at != digest:
            found.append(relative)
    return found


def fixtures(value: object) -> set[str]:
    """Every `fixture` a parsed manifest names, wherever it names one."""
    if isinstance(value, dict):
        named = {value["fixture"]} if isinstance(value.get("fixture"), str) else set()
        return named.union(*(fixtures(one) for one in value.values()))
    if isinstance(value, list):
        return set().union(*(fixtures(one) for one in value))
    return set()


def conformance_of(manifest: dict, image: str) -> set[str]:
    """The conformance directories of every contract an adapter fronting a service that
    runs `image` speaks, as `conformance/<capability>@<major>`."""
    services = manifest.get("service", [])
    running = {one.get("id") for one in services if one.get("image") == image}
    spoken = {str(contract) for one in services if one.get("fronts") in running for contract in one.get("speaks", [])}
    return {f"conformance/{contract}" for contract in spoken if CONTRACT.match(contract)}


def recordings_named(manifest: dict, image: str, relative: str) -> bool:
    """Whether `relative` is a recording a bump of `image` may write: a `.json` file
    outside every dot-directory, which the manifest names or a conformance case is."""
    folder, _, name = relative.rpartition("/")
    if not name.endswith(".json") or any(part.startswith(".") for part in relative.split("/")):
        return False
    return relative in fixtures(manifest) or (folder in conformance_of(manifest, image) and CASE.match(name) is not None)


def stage(root: pathlib.Path, main_text: str, move: dict, out: pathlib.Path) -> list[str]:
    """Copy what a bump changed into `out` for the job that commits it, and name each file.

    That is the manifest, `proofs.json`, and every recording the manifest names that now
    names the new pin. A recording the run wrote of anything else stays behind.
    """
    manifest = tomllib.loads(main_text)
    pinned = f"{move['image']}@{move['to']['digest']}"
    out.mkdir(exist_ok=True)
    staged = [MANIFEST_FILE]
    paths.plain_write(out, MANIFEST_FILE, paths.plain_read(root, MANIFEST_FILE, MANIFEST_LIMIT))
    for relative in paths.plain_files(root)[0]:
        if relative == PROOFS_FILE or (recordings_named(manifest, move["image"], relative)
                                       and recording_of(paths.plain_read(root, relative, RECORDING_LIMIT)) == pinned):
            paths.plain_write(out, relative, paths.plain_read(root, relative, RECORDING_LIMIT))
            staged.append(relative)
    return staged


def admitted_files(main_text: str, move: dict, bump: pathlib.Path) -> dict[str, bytes]:
    """The files a staged bump may commit for `move`, or `Refused` naming why.

    `move` is the committing job's own, worked out without reading `bump`. Every entry
    of `bump` must be a plain file, its manifest must be main's with exactly that move
    and nothing else, and every other file must be `proofs.json` or a recording the
    manifest names, taken from exactly the new pin.
    """
    files, other = paths.plain_files(bump)
    if other:
        raise Refused(f"the bump holds what is not a plain file: {', '.join(other)}")
    if MANIFEST_FILE not in files:
        raise Refused(f"the bump holds no {MANIFEST_FILE}")
    image, to = move["image"], move["to"]
    written, _ = plugin_pin.pinned(main_text, image, to["tag"], to["digest"])
    admitted = {MANIFEST_FILE: paths.plain_read(bump, MANIFEST_FILE, MANIFEST_LIMIT)}
    if admitted[MANIFEST_FILE] != written.encode():
        raise Refused(f"{MANIFEST_FILE} is not main's with {image} moved to {to['tag']} at {to['digest']} "
                      "and nothing else")
    manifest = tomllib.loads(main_text)
    pinned = f"{image}@{to['digest']}"
    for relative in files:
        if relative == MANIFEST_FILE:
            continue
        body = paths.plain_read(bump, relative, RECORDING_LIMIT)
        if relative == PROOFS_FILE:
            if not isinstance(json.loads(body), dict):
                raise Refused(f"{PROOFS_FILE} is not a report")
        elif not recordings_named(manifest, image, relative):
            raise Refused(f"{relative} is not a recording the manifest names")
        elif recording_of(body) != pinned:
            raise Refused(f"{relative} is not a recording taken from {pinned}")
        admitted[relative] = body
    return admitted


def body_of(said: str, left: list[str], log: str, cited: str) -> tuple[str, bool]:
    """A bump's pull request body, and whether it came out clean.

    Decided only from what the committing job read itself: clean where no recording
    still names the image the bump replaces, and the required checks then judge the
    rest. One that left a recording behind names each, and is not armed to merge
    (`OPS-R87`).
    """
    lines = [said, ""]
    if not left:
        lines.append("Every recording of it the manifest names is recorded again from it by `lemonfiber plugin "
                     "record`, at the lemonfiber `targets.toml` names; the plugin check judges every claim, proof "
                     "and check against them.")
    else:
        lines.append("Not every recording was taken again from it, so these still name the image this replaces "
                     f"and are refused (ARCH-R121); the record job's log says why: {log}")
        lines += [f"- `{path}`" for path in left[:STALE_LISTED]]
        if len(left) > STALE_LISTED:
            lines.append(f"- and {len(left) - STALE_LISTED} more")
        lines += ["", "It stays open and is not armed to merge until that is put right on this branch."]
    lines += ["", cited, SIGNED]
    return "\n".join(lines), not left


def reader_of(workflow: str) -> dict[str, str]:
    """The reader's repository and revision, as the workflow that runs it pins them."""
    found = {key.lower(): value for key, value in READER.findall(workflow)}
    if not READER_REPOSITORY.match(found.get("repository", "")) or not READER_REVISION.match(found.get("revision", "")):
        raise ValueError("the workflow pins no reader repository and full revision")
    return found


def recorded(root: pathlib.Path, taken: pathlib.Path) -> None:
    """Every recording the manifest at `root` names, taken again by the reader `taken`
    from plugin-template, and `proofs.json` written from them; the reader and the
    lemonfiber it fetched or built are removed after.

    A failure is warned of and decides nothing. The plugin check on the pull request
    judges what was written, and the committing job reads which recordings were taken.
    """
    github = root / ".github"
    if github.is_symlink() or (github.exists() and not github.is_dir()):
        raise Refused(".github in the plugin is not a plain directory")
    held = root / READER_HOME
    if os.path.lexists(held):
        raise Refused(f"{READER_HOME} is in the plugin. A first-party plugin carries no Python of its own; "
                      "the reader is this workflow's.")
    github.mkdir(exist_ok=True)
    shutil.copytree(taken, held, symlinks=True)
    try:
        loaded = importlib.util.spec_from_file_location("reader", held / READER_FILE)
        reader = importlib.util.module_from_spec(loaded)
        loaded.loader.exec_module(reader)
        try:
            done = reader.plugin("record")
            print(done.stdout + done.stderr)
            code = done.returncode
        except (reader.Unasked, OSError) as why:
            print(why)
            code = 1
        if code != 0:
            print(f"::warning::lemonfiber plugin record exited {code}; the recordings it did not take are named "
                  "on the pull request")
        if subprocess.run([sys.executable, str(held / READER_FILE), "proofs"], check=False).returncode != 0:
            print("::warning::not every assertion holds on the new recordings; the plugin check on the pull "
                  "request names which")
    finally:
        shutil.rmtree(held)
        shutil.rmtree(root / CACHE, ignore_errors=True)


def pins_only(changed: list[str], directory: str) -> bool:
    """Whether a push that changed `changed`, at least one path, changed only what a pin
    moves in the plugin at `directory`."""
    at = "" if directory in ("", ".") else f"{directory.strip('/')}/"
    moved = {f"{at}{name}" for name in PIN_FILES}
    return bool(changed) and all(path in moved or path.startswith(f"{at}{RECORDINGS}") for path in changed)


def changed_between(before: str, after: str) -> list[str] | None:
    """Every path the working directory's repository changed from `before` to `after`,
    or None where `before` is no commit it holds."""
    if NO_COMMIT.match(before) or subprocess.run(["git", "cat-file", "-e", f"{before}^{{commit}}"],
                                                 capture_output=True, check=False).returncode != 0:
        return None
    named = subprocess.run(["git", "diff", "--no-renames", "--name-only", "-z", before, after, "--"],
                           capture_output=True, text=True, check=True).stdout
    return [path for path in named.split("\0") if path]


def output(lines: dict[str, str]) -> None:
    """Values for the step's outputs, each multi-line one behind a delimiter no line holds."""
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
        for key, value in lines.items():
            delimiter = f"value_{secrets.token_hex(16)}"
            handle.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def read(raw: str, limit: int) -> bytes:
    """A file named on the command line, read as a plain file under the working directory."""
    return paths.plain_read(pathlib.Path.cwd().resolve(), paths.plain_relative(raw), limit)


def write(raw: str, body: bytes) -> None:
    """A file named on the command line, written as a plain file under the working directory."""
    paths.plain_write(pathlib.Path.cwd().resolve(), paths.plain_relative(raw), body)


def plugin_root(raw: str) -> pathlib.Path:
    """The directory a manifest named on the command line sits in, every step of it a
    real directory under the working directory."""
    folder, _, name = paths.plain_relative(raw).rpartition("/")
    if name != MANIFEST_FILE:
        raise Refused(f"{raw} is not a {MANIFEST_FILE}")
    return paths.plain_directory(folder or ".")


def manifest_text(raw: str) -> tuple[pathlib.Path, str]:
    """The plugin's root and its manifest, for a manifest named on the command line."""
    root = plugin_root(raw)
    return root, paths.plain_read(root, MANIFEST_FILE, MANIFEST_LIMIT).decode("utf-8")


def admit_into(root: pathlib.Path, files: dict[str, bytes], move: dict, move_out: str) -> None:
    """Write what was admitted into the plugin at `root`, naming each file, and the move."""
    for relative, body in files.items():
        paths.plain_write(root, relative, body)
        print(relative)
    write(move_out, json.dumps(move, indent=2).encode())


def message(args: argparse.Namespace, described: Callable[[dict, list[str], str], tuple[str, str, bool]]) -> int:
    """The commit message on standard output, and the pull request's title, body and
    whether it came out clean for the step's outputs, as `described` words them from the
    move and the recordings in the checkout."""
    move = json.loads(read(args.move, MOVE_LIMIT))
    left = stale(paths.plain_directory(args.root), move["image"], move["to"]["digest"])
    title, body, clean = described(move, left, registry.printable(args.log))
    print(f"{title}\n\n{body}")
    output({"title": title, "body": body, "clean": "yes" if clean else "no"})
    return 0


def asked_reader(args: argparse.Namespace) -> int:
    for key, value in reader_of(read(args.workflow, MANIFEST_LIMIT).decode("utf-8")).items():
        print(f"{key}={value}")
    return 0


def asked_record(args: argparse.Namespace) -> int:
    recorded(plugin_root(args.manifest), paths.plain_directory(args.reader))
    return 0


def asked_stage(args: argparse.Namespace) -> int:
    move = json.loads(read(args.move, MOVE_LIMIT))
    main_text = read(args.main, MANIFEST_LIMIT).decode("utf-8")
    out = paths.plain_directory(args.out, make=True)
    print("\n".join(stage(plugin_root(args.manifest), main_text, move, out)))
    return 0


def asked_pins_only(args: argparse.Namespace) -> int:
    changed = changed_between(args.before, args.after)
    print("yes" if changed is not None and pins_only(changed, args.directory) else "no")
    return 0


ASKED = {"reader": asked_reader, "record": asked_record, "stage": asked_stage, "pins-only": asked_pins_only}
OPTIONS = {
    "reader": ("--workflow",), "record": ("--manifest", "--reader"),
    "stage": ("--manifest", "--main", "--move", "--out"), "pins-only": ("--before", "--after"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    asked = parser.add_subparsers(dest="asked", required=True)
    for name, options in OPTIONS.items():
        one = asked.add_parser(name)
        for option in options:
            one.add_argument(option, required=True)
    asked.choices["pins-only"].add_argument("--directory", default=".")
    args = parser.parse_args(argv)
    try:
        return ASKED[args.asked](args)
    except (OSError, ValueError, subprocess.CalledProcessError) as why:
        print(f"::error::{why}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
