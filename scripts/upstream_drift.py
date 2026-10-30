#!/usr/bin/env python3
"""What this repository takes from another lemonfiber repository, held against what that one's main ships — Q-R68, Q-R70.

Every repository that builds against another one's commit asks the same
question: is what it holds the one the other repository's default branch would
give it now? What differs is where the commit is written, so there is one
reader per lock shape and one comparison behind them:

- `composer`: every `composer.lock` package whose source is a lemonfiber
  repository, at the `source.reference` the lock pins. What counts is what
  Composer installs, which is the repository's archive: a path the default
  branch marks `export-ignore`, or under a directory it marks so, ships nothing.
- `npm`: every `package.json` dependency whose specifier names a lemonfiber
  repository, at the revision after `#`, which `package-lock.json` has to name
  in both places it keeps one. What counts is what npm installs: for a package
  built at install, its whole tree but its workflows and its `*.test.ts`; for
  one installed as it stands, what its `files` lists plus what npm always packs.
- `vendored`: a copy committed here, with the commit it was taken at written in
  a file beside it. Each copy is held to that commit's tree byte for byte, and
  what counts is what the copies hold.

A pin is current when it is the default branch's head, or when no file that
counts changed since it. A pin behind only by commits that have been on the
default branch for less than the window `pin_window.py` holds is a warning,
naming the hour it becomes a refusal, so the automated bump that takes them has
that long to merge (Q-R68). Anything else fails, naming the files and the commits
not taken and the command that takes them (Q-R70).

    upstream_drift.py composer [--remedy TEXT]
    upstream_drift.py npm [--remedy TEXT]
    upstream_drift.py vendored --upstream REPO --revision PATH --copy FROM:TO [--copy ...] --remedy TEXT

`{head}` in a remedy is the revision to take, `{name}` the package and `{repo}` its repository.

Exit 0 when every pin is current, 1 when one is not or cannot be compared.
"""

from __future__ import annotations

import argparse
import dataclasses
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterable

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import pin_window

ORG = "lemonfiber"

#: Where a repository of the organisation is cloned from. Tests point it at a directory.
ORIGIN = "https://github.com/" + ORG + "/{}.git"

COMMIT = re.compile(r"\A[0-9a-f]{40}\Z")

#: A lemonfiber repository on CloneHub, in any spelling npm or Composer write one.
REPOSITORY = re.compile(
    r"\A(?:github:|git\+ssh://git@github\.com[:/]|git\+https://github\.com/|git://github\.com/|https://github\.com/)?"
    + ORG
    + r"/([\w.-]+?)(?:\.git)?(?:#(.*))?\Z"
)

#: The manifest fields npm installs from. Peers are the consumer's to provide.
FIELDS = ("dependencies", "devDependencies", "optionalDependencies")

#: Scripts that make npm build a git dependency from its own tree when it installs it.
BUILDS = ("preinstall", "install", "postinstall", "prepack", "prepare", "build")

#: What npm packs whatever `files` says.
ALWAYS = re.compile(r"\A(?:package\.json|(?:readme|copying|licen[cs]e)(?:\..*)?)\Z", re.IGNORECASE)

#: How many changed paths a verdict lists before it counts the rest.
LISTED = 20


class Unreadable(Exception):
    """What was to be compared could not be read."""


@dataclasses.dataclass(frozen=True)
class Pin:
    """One revision of one repository this tree takes, and how it is taken."""

    name: str
    repo: str
    revision: str
    remedy: str
    sources: tuple[str, ...] = ()


def say(*lines: str) -> None:
    """Print, and on a CI run write to the run's summary as well."""
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    for line in lines:
        print(line)
        if summary:
            with open(summary, "a", encoding="utf-8") as out:
                out.write(line + "\n")


def annotate(message: str) -> None:
    print(f"::error::{message}")


def clock() -> int:
    """The time a run measures the window against, in seconds since the epoch."""
    return int(time.time())


class Clone:
    """A bare clone of one repository, asked through git."""

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path

    def __call__(self, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
        """Run git here, as text."""
        return subprocess.run(
            ["git", "-c", "gc.auto=0", "-C", str(self.path), *args],
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )


def read_json(path: pathlib.Path) -> dict:
    try:
        found = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise Unreadable(f"{path.name} could not be read: {error}") from error
    if not isinstance(found, dict):
        raise Unreadable(f"{path.name} is not a JSON object.")
    return found


def composer_pins(root: pathlib.Path, remedy: str) -> list[Pin]:
    """Every package `composer.lock` takes from a lemonfiber repository, at the reference it pins."""
    lock = read_json(root / "composer.lock")
    pins = []
    for package in [*lock.get("packages", []), *lock.get("packages-dev", [])]:
        source = package.get("source") or {}
        match = REPOSITORY.match(str(source.get("url", "")))
        if match is None:
            continue
        name = str(package.get("name", ""))
        pins.append(
            Pin(name, match.group(1), str(source.get("reference", "")), remedy or f"composer update {name}")
        )
    return pins


def locked_as(lock: dict, field: str, name: str, spec: str, revision: str) -> bool:
    """Whether the lockfile names the pin in both places it keeps one: its copy of the declaration, and what it resolved."""
    packages = lock.get("packages") or {}
    declared = (packages.get("") or {}).get(field, {}).get(name)
    resolved = str((packages.get(f"node_modules/{name}") or {}).get("resolved", ""))
    return declared == spec and resolved.partition("#")[2] == revision


def npm_pins(root: pathlib.Path, remedy: str) -> tuple[list[Pin], list[str]]:
    """Every dependency `package.json` takes from a lemonfiber repository, and where the lockfile disagrees."""
    manifest = read_json(root / "package.json")
    lock = read_json(root / "package-lock.json")
    fallback = f"point {{name}} at github:{ORG}/{{repo}}#{{head}} in package.json and run npm install"
    declared = [
        (field, name, str(spec), REPOSITORY.match(str(spec)))
        for field in FIELDS
        for name, spec in (manifest.get(field) or {}).items()
    ]
    pins, faults = [], []
    for field, name, spec, match in declared:
        if match is None:
            continue
        revision = match.group(2) or ""
        pins.append(Pin(name, match.group(1), revision, remedy or fallback))
        if not locked_as(lock, field, name, spec, revision):
            faults.append(name)
    return pins, faults


def vendored_pin(root: pathlib.Path, upstream: str, revision: str, copies: list[str], remedy: str) -> Pin:
    """The one commit a vendored copy records, with the upstream paths it copies."""
    path = root / revision
    try:
        commit = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError) as error:
        raise Unreadable(f"{revision} could not be read, so the copy names no commit: {error}") from error
    sources = tuple(one.partition(":")[0] for one in copies)
    return Pin(upstream, upstream, commit, remedy, sources)


def expand(remedy: str, pin: Pin, head: str) -> str:
    return remedy.replace("{head}", head).replace("{name}", pin.name).replace("{repo}", pin.repo)


def object_id(data: bytes) -> str:
    """The name git gives a file of these bytes, so a copy is compared without fetching what it copies."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def held(root: pathlib.Path, where: str, revision: pathlib.Path) -> dict[str, str]:
    """Every file under one path of this tree, by its path inside it and its object name, leaving out the record and caches."""
    base = root / where
    if base.is_file():
        return {"": object_id(base.read_bytes())}
    return {
        one.relative_to(base).as_posix(): object_id(one.read_bytes())
        for one in sorted(base.rglob("*"))
        if one.is_file() and one != revision and "__pycache__" not in one.parts
    }


def tree(git: Clone, commit: str, source: str) -> dict[str, str] | None:
    """Every file under one upstream path at a commit, by its path inside it and its object name; `None` where it has no such path."""
    listing = git("ls-tree", "-r", "-z", "--full-tree", commit, "--", source).stdout
    files = {}
    for entry in filter(None, listing.split("\0")):
        meta, path = entry.split("\t", 1)
        if path == source:
            files[""] = meta.split()[2]
        elif path.startswith(source + "/"):
            files[path.removeprefix(source + "/")] = meta.split()[2]
    return files or None


def copy_faults(root: pathlib.Path, git: Clone, pin: Pin, copies: list[str], revision: str) -> list[str]:
    """Each way a copy is not its recorded commit's tree."""
    faults = []
    record = root / revision
    for one in copies:
        source, _, target = one.partition(":")
        expected = tree(git, pin.revision, source)
        if expected is None:
            faults.append(f"{pin.repo} {pin.revision} has no {source}")
            continue
        found = held(root, target, record) if (root / target).exists() else {}
        faults += [f"{inside(target, path)} is missing" for path in sorted(expected.keys() - found.keys())]
        faults += [
            f"{inside(target, path)} is not in {pin.repo}" for path in sorted(found.keys() - expected.keys())
        ]
        faults += [
            f"{inside(target, path)} differs"
            for path in sorted(expected.keys() & found.keys())
            if expected[path] != found[path]
        ]
    return faults


def inside(target: str, path: str) -> str:
    """A file of a copy, named from the root of this tree."""
    return f"{target}/{path}" if path else target


def ancestors(path: str) -> Iterable[str]:
    while True:
        yield path
        if "/" not in path:
            return
        path = path.rsplit("/", 1)[0]


def archived(git: Clone, head: str) -> Callable[[str], bool]:
    """Whether a path is in the archive Composer installs: neither it nor a directory above it is `export-ignore` at `head`."""

    def ships(path: str) -> bool:
        asked = "\0".join(ancestors(path)) + "\0"
        answer = git("check-attr", f"--source={head}", "-z", "--stdin", "export-ignore", stdin=asked).stdout
        fields = answer.split("\0")
        return not any(value == "set" for value in fields[2::3])

    return ships


def packed(git: Clone, head: str) -> Callable[[str], bool]:
    """Whether a path can change what npm installs from the package at `head`."""
    shown = git("show", f"{head}:package.json")
    try:
        manifest = json.loads(shown.stdout) if shown.returncode == 0 else None
    except ValueError:
        manifest = None
    if not isinstance(manifest, dict):
        return lambda _path: True
    scripts = manifest.get("scripts") or {}
    if "workspaces" in manifest or any(name in scripts for name in BUILDS):
        return lambda path: not path.startswith(".github/") and not path.endswith(".test.ts")
    files = manifest.get("files")
    if not isinstance(files, list):
        return lambda _path: True

    def bare(pattern: str) -> str:
        return re.sub(r"/\Z", "", re.sub(r"\A\.?/", "", pattern.removeprefix("!")))

    def matches(pattern: str, path: str) -> bool:
        return path == pattern or path.startswith(pattern + "/") or fnmatch.fnmatchcase(path, pattern)

    bins = manifest.get("bin")
    named = {
        bare(one)
        for one in [manifest.get("main"), *([bins] if isinstance(bins, str) else (bins or {}).values())]
        if isinstance(one, str)
    }
    patterns = [one for one in files if isinstance(one, str)]
    included = [bare(one) for one in patterns if not one.startswith("!")]
    excluded = [bare(one) for one in patterns if one.startswith("!")]
    return lambda path: (
        bool(ALWAYS.match(path))
        or path in named
        or (any(matches(one, path) for one in included) and not any(matches(one, path) for one in excluded))
    )


def within(sources: tuple[str, ...]) -> Callable[[str], bool]:
    """Whether a path is one of the copied upstream paths or under one."""
    return lambda path: any(path == one or path.startswith(one + "/") for one in sources)


def compare(
    git: Clone,
    pin: Pin,
    counts: Callable[[str, str], Callable[[str], bool]],
    extra: Callable[[str], list[str]],
) -> bool:
    """Hold one pin against the default branch of its repository. True when it is current."""
    head = git("rev-parse", "HEAD").stdout.strip()
    branch = git("symbolic-ref", "--short", "HEAD").stdout.strip() or "main"
    fix = expand(pin.remedy, pin, head)
    facts = [f"- pinned: `{pin.revision}`", f"- {pin.repo} {branch}: `{head}`"]

    if git("cat-file", "-e", f"{pin.revision}^{{commit}}").returncode != 0:
        say(f"## The pinned `{pin.name}` is not a commit in {pin.repo}", "", *facts, "", f"To fix it: {fix}.")
        annotate(f"{pin.name}: {pin.revision} is not a commit in {ORG}/{pin.repo} — {fix}")
        return False

    faults = extra(pin.revision)
    if faults:
        say(
            f"## `{pin.name}` is not the commit it records",
            "",
            *facts,
            "",
            *(f"- {one}" for one in faults),
            "",
            f"To fix it: {fix}.",
        )
        annotate(f"{pin.name}: the copy is not {pin.repo} {pin.revision} — {fix}")
        return False

    if pin.revision == head:
        say(
            f"## `{pin.name}` is current",
            "",
            f"It is pinned at `{head}`, which is what {pin.repo} {branch} is.",
        )
        return True

    behind = git("log", "--oneline", f"{pin.revision}..{head}").stdout.strip()
    if not behind or git("merge-base", "--is-ancestor", pin.revision, head).returncode != 0:
        say(f"## The pinned `{pin.name}` is not on {pin.repo} {branch}", "", *facts, "", f"To fix it: {fix}.")
        annotate(f"{pin.name}: {pin.revision} is not on {ORG}/{pin.repo} {branch} — {fix}")
        return False

    ships = counts(git, head)
    changed = [
        path
        for path in git("diff", "--name-only", pin.revision, head).stdout.split("\n")
        if path and ships(path)
    ]
    if not changed:
        say(
            f"## `{pin.name}` is current",
            "",
            f"It is pinned at `{pin.revision}`. {pin.repo} {branch} is at `{head}`, and no file changed since is one this takes.",
        )
        return True

    report = [
        *facts,
        "",
        "Not taken:",
        "",
        "```",
        behind,
        "```",
        "",
        "Of what this takes from it, these changed:",
        "",
        *(f"- `{path}`" for path in changed[:LISTED]),
        *([f"- and {len(changed) - LISTED} more"] if len(changed) > LISTED else []),
        "",
    ]
    touched = [
        int(when)
        for when in git("log", "--format=%ct", f"{pin.revision}..{head}", "--", *changed).stdout.split()
    ]
    now = clock()
    if touched and all(pin_window.waits(when, now) for when in touched):
        refused = pin_window.refused_at(min(touched))
        say(
            f"## `{pin.name}` is behind {pin.repo} {branch}, for less than {pin_window.HOURS} hours",
            "",
            *report,
            f"Each of these changes has been on {branch} for less than {pin_window.HOURS} hours, so this "
            f"is a warning until {refused}, when it becomes a refusal (Q-R68). To catch up: {fix}.",
        )
        print(f"::warning::{pin.name} is behind {ORG}/{pin.repo} {branch}, refused from {refused} — {fix}")
        return True

    say(f"## `{pin.name}` is behind {pin.repo} {branch}", "", *report, f"To catch up: {fix}.")
    annotate(f"{pin.name} is behind {ORG}/{pin.repo} {branch} — {fix}")
    return False


def cloned(scratch: pathlib.Path, repo: str, origin: str) -> Clone:
    clone = scratch / f"{repo}.git"
    done = subprocess.run(
        ["git", "clone", "--bare", "--quiet", "--filter=blob:none", "--", origin.format(repo), str(clone)],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise Unreadable(f"{ORG}/{repo} could not be cloned: {done.stderr.strip()}")
    return Clone(clone)


def parser() -> argparse.ArgumentParser:
    asked = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    asked.add_argument("lock", choices=("composer", "npm", "vendored"))
    asked.add_argument(
        "--remedy",
        default="",
        help="the command that takes the default branch; {head}, {name} and {repo} are filled in",
    )
    asked.add_argument("--upstream", default="", help="vendored: the repository the copy is taken from")
    asked.add_argument(
        "--revision", default="", help="vendored: the file recording the commit the copy was taken at"
    )
    asked.add_argument(
        "--copy",
        action="append",
        default=[],
        help="vendored: FROM:TO, an upstream path and where it is copied here",
    )
    return asked


@dataclasses.dataclass(frozen=True)
class Reading:
    """What one lock shape takes, and how its pins are judged."""

    pins: list[Pin]
    counts: Callable[[Clone, str], Callable[[str], bool]]
    faults: list[str] = dataclasses.field(default_factory=list)
    extra: Callable[[Pin, Clone], Callable[[str], list[str]]] = lambda _pin, _git: lambda _revision: []


def vendored(asked: argparse.Namespace, root: pathlib.Path) -> Reading:
    """A committed copy, held to the commit it records."""
    if not (asked.upstream and asked.revision and asked.copy and asked.remedy):
        raise Unreadable("vendored takes --upstream, --revision, at least one --copy FROM:TO and --remedy.")
    if any(not re.fullmatch(r"[^:]+:[^:]+", one) for one in asked.copy):
        raise Unreadable("each --copy is FROM:TO, an upstream path and where it is copied here.")
    pin = vendored_pin(root, asked.upstream, asked.revision, asked.copy, asked.remedy)
    return Reading(
        [pin],
        lambda _git, _head: within(pin.sources),
        extra=lambda one, git: lambda _revision: copy_faults(root, git, one, asked.copy, asked.revision),
    )


def reading(asked: argparse.Namespace, root: pathlib.Path) -> Reading:
    """What the lock shape asked for takes."""
    if asked.lock == "composer":
        return Reading(composer_pins(root, asked.remedy), archived)
    if asked.lock == "npm":
        pins, faults = npm_pins(root, asked.remedy)
        return Reading(pins, packed, faults)
    return vendored(asked, root)


def disagreed(name: str) -> None:
    say(
        f"## The lockfile disagrees with the manifest on `{name}`",
        "",
        "`npm ci` installs the manifest's revision and says nothing, so the lockfile is a record of a build",
        "that did not happen. Run `npm install` so it names the revision the manifest does, and commit both.",
    )
    annotate(
        f"{name}: package-lock.json does not name the revision package.json pins — run npm install and commit package-lock.json"
    )


def judged(scratch: pathlib.Path, pin: Pin, read: Reading, origin: str) -> bool:
    """Whether one pin is current. False when it is not, or could not be compared."""
    if not COMMIT.match(pin.revision):
        say(
            f"## The pinned `{pin.name}` is not a commit",
            "",
            f"It names `{pin.revision or '(nothing)'}`, not a full 40-character commit hash.",
        )
        annotate(f"{pin.name} is not pinned to a full commit hash")
        return False
    try:
        git = cloned(scratch, pin.repo, origin)
    except Unreadable as error:
        say(f"## `{pin.name}` could not be compared", "", str(error))
        annotate(f"{pin.name}: {error} — rerun this check")
        return False
    current = compare(git, pin, read.counts, read.extra(pin, git))
    say("")
    return current


def run(arguments: list[str], root: pathlib.Path, origin: str = ORIGIN) -> int:
    asked = parser().parse_args(arguments)
    try:
        read = reading(asked, root)
    except Unreadable as error:
        say("## What this takes could not be read", "", str(error))
        annotate(f"{error} Nothing was compared.")
        return 1

    if not read.pins:
        say(
            "## Nothing taken from the organisation was found",
            "",
            f"No pin names a {ORG} repository, so nothing was compared.",
        )
        annotate(f"no pin names a {ORG} repository, so nothing was compared")
        return 1

    for name in read.faults:
        disagreed(name)

    current = not read.faults
    with tempfile.TemporaryDirectory() as scratch:
        for pin in read.pins:
            current = judged(pathlib.Path(scratch), pin, read, origin) and current
    return 0 if current else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:], pathlib.Path.cwd()))
