#!/usr/bin/env python3
"""The embedded bundle pins each first-party plugin the train tagged, at that tag — OPS-R86.

A version that cuts a first-party plugin's repository tags it first, a repository
building a stack service's image among them, pinned by its service's id. The tag
publishes the plugin's image, the plugin's pin pull request names it in the
manifest, the train moves the plugin's pin in the catalogue's bundle, and the core's
submodule takes that catalogue. Only then may the core be tagged, and this is the
check that says whether that point has arrived: for every plugin the version cuts,
the bundle the core embeds pins it from the repository the train tagged, at the
release that tag names.

The catalogue is found and read as `embedded_bundle.py` finds it. That the copy
beside each pin is the manifest at the pinned revision is the catalogue's own CI to
hold (REPO-R92).

A plugin written against what the core had on `main` before a release carried it
names a commit in its `targets.toml` rather than a release. The bundle may pin such a
revision only where the core commit being tagged holds that commit, so everything the
plugin was proved against is inside the release that embeds it. Each pinned
revision's `targets.toml` is fetched from its origin and read as data, and a commit
the core's checkout does not hold is refused by name.

Usage:
  check_bundle_pins.py --version X.Y.Z --tag <tag> --core <core checkout> --owner <org>

Exit 0 = every plugin the version cuts is pinned at the tag, or it cuts none, 1 = one
is not, or the core, its catalogue or the bundle cannot be read, 2 = usage.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import tempfile
import tomllib

import check_plugins
import embedded_bundle
import manifest_repos
from check_image_pins import cut_by_train
from patterns import COMMIT_IMAGE, PRERELEASE_SEPARATOR

#: Where a plugin says which lemonfiber it targets, unless the plugin registry
#: names another place for it.
TARGETS = "targets.toml"


def problems(bundle: dict, release: str, owner: str, wanted: list[tuple[str, str]]) -> list[str]:
    """Every way the bundle fails to pin a wanted (repo, id) at `release`: as a part, or in
    a table of the bundle's own, as it pins the fence, until a release a commit (OPS-R94)."""
    said = []
    for repo, plugin in wanted:
        table = embedded_bundle.own_table(bundle, plugin)
        if table is not None:
            tag = str(table.get("tag"))
            early = PRERELEASE_SEPARATOR in release and COMMIT_IMAGE.match(tag)
            if tag != release and not early:
                said.append(f"{plugin}: its table pins tag {tag!r}, not {release!r}")
            continue
        pin, wrong = embedded_bundle.pinned_once(bundle, plugin, embedded_bundle.origin(owner, repo))
        said += wrong
        if pin is not None and pin.get("release") != release:
            said.append(f"{plugin}: pinned at release {pin.get('release')!r}, not {release!r}")
    return said


def git(*args: str, at: pathlib.Path) -> subprocess.CompletedProcess:
    """One git command, its output kept, its failure left to the caller."""
    return subprocess.run(["git", "-C", str(at), *args], capture_output=True, text=True, check=False)


def last_word(done: subprocess.CompletedProcess) -> str:
    lines = done.stderr.strip().splitlines()
    return lines[-1] if lines else f"git exited {done.returncode}"


def target_at(pin: dict, path: str, plugin: str) -> tuple[str | None, str | None]:
    """What the plugin's `targets.toml` names at the pinned revision, or why it cannot be read.

    Only that one file is read out of the revision, and nothing in it runs.
    """
    revision = str(pin.get("revision", ""))
    if not check_plugins.COMMIT_RE.match(revision):
        return (
            None,
            f"{plugin}: the bundle pins it at {revision or 'no revision'!r}, which is not a full commit",
        )
    with tempfile.TemporaryDirectory() as box:
        root = pathlib.Path(box)
        for step in (
            ("init", "--quiet"),
            (
                "-c",
                "core.hooksPath=/dev/null",
                "fetch",
                "--quiet",
                "--depth",
                "1",
                "--no-tags",
                str(pin["origin"]),
                revision,
            ),
        ):
            done = git(*step, at=root)
            if done.returncode != 0:
                return (
                    None,
                    f"{plugin}: {revision[:12]} could not be fetched from {pin['origin']}: {last_word(done)}",
                )
        shown = git("show", f"FETCH_HEAD:{path}", at=root)
        if shown.returncode == 0:
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(shown.stdout, encoding="utf-8")
        return check_plugins.targeted(root, {"id": plugin, "targets": path})


def unheld(
    core: pathlib.Path, bundle: dict, wanted: list[tuple[str, str]], places: dict[str, str]
) -> list[str]:
    """Every pinned revision whose `targets.toml` names a commit the core being tagged
    does not hold, or that cannot say what it targets."""
    pinned = {str(pin.get("id")): pin for pin in bundle.get("plugin", []) if isinstance(pin, dict)}
    said = []
    for repo, plugin in wanted:
        if embedded_bundle.own_table(bundle, plugin) is not None:
            continue
        target, why = target_at(pinned[plugin], places.get(repo, TARGETS), plugin)
        if why is not None:
            said.append(why)
            continue
        if not check_plugins.COMMIT_RE.match(str(target)):
            continue
        if git("merge-base", "--is-ancestor", str(target), "HEAD", at=core).returncode != 0:
            said.append(
                f"{plugin}: the pinned revision {pinned[plugin]['revision'][:12]} targets lemonfiber at "
                f"{target}, which the core commit being tagged does not hold"
            )
    return said


def targets_places(path: pathlib.Path) -> dict[str, str]:
    """Where each registered plugin's repository keeps what it targets, by repository."""
    if not path.is_file():
        return {}
    entries = tomllib.loads(path.read_text(encoding="utf-8")).get("plugin", [])
    return {
        entry["repo"]: entry["targets"]
        for entry in entries
        if isinstance(entry, dict) and "repo" in entry and "targets" in entry
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--core", required=True, type=pathlib.Path)
    ap.add_argument("--owner", required=True)
    a = ap.parse_args()

    if not cut_by_train(a.tag, a.version):
        sys.exit(f"::error::{a.tag!r} is not a tag the train cuts for {a.version!r}")
    if not embedded_bundle.OWNER.match(a.owner):
        sys.exit(f"::error::{a.owner!r} is not an organisation")
    path = manifest_repos.manifest_for(a.version)
    if not path.is_file():
        print(f"::error::no manifest at {path}", file=sys.stderr)
        return 1
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    registry = tomllib.loads(manifest_repos.REGISTRY.read_text(encoding="utf-8"))
    wanted = manifest_repos.plugins(data, registry)
    if not wanted:
        print(f"{a.version} cuts no first-party plugin the bundle has to pin.")
        return 0
    core = a.core.resolve()
    if not core.is_relative_to(pathlib.Path.cwd().resolve()):
        sys.exit(f"::error::path escapes the working directory: {a.core}")

    try:
        _, read = embedded_bundle.read(core)
    except embedded_bundle.Unread as why:
        print(f"::error::{why}")
        return 1

    release = a.tag.removeprefix("v")
    said = problems(read, release, a.owner, wanted)
    if not said:
        said = unheld(core, read, wanted, targets_places(pathlib.Path(check_plugins.REGISTRY)))
    for problem in said:
        print(f"::error::{problem}")
    if said:
        print(
            f"::error::the embedded bundle does not pin what {a.tag} published; "
            "nothing else is tagged until it does"
        )
        return 1
    for _, plugin in wanted:
        print(f"{plugin} is pinned at {release}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
