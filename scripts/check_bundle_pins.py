#!/usr/bin/env python3
"""The embedded bundle pins each first-party plugin the train tagged, at that tag — OPS-R86.

A version that cuts a first-party plugin's repository tags it first. The tag
publishes the plugin's adapter image, the plugin's pin pull request names it in the
manifest, the train moves the plugin's pin in the catalogue's bundle, and the core's
submodule takes that catalogue. Only then may the core be tagged, and this is the
check that says whether that point has arrived: for every plugin the version cuts,
the bundle the core embeds pins it from the repository the train tagged, at the
release that tag names.

The catalogue is found as the submodule of the core whose URL names
`lemonfiber-plugins`, read from the core's own `.gitmodules`, so no path is assumed,
and is checked out at the commit the core pins.
That the copy beside each pin is the manifest at the pinned revision is the
catalogue's own CI to hold (REPO-R92).

Usage:
  check_bundle_pins.py --version X.Y.Z --tag <tag> --core <core checkout> --owner <org>

Exit 0 = every plugin the version cuts is pinned at the tag, or it cuts none, 1 = one
is not, or the core, its catalogue or the bundle cannot be read, 2 = usage.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import tomllib

import manifest_repos
import submodule_pins
from check_image_pins import cut_by_train

#: The catalogue the core embeds the bundle from (ADR-0042).
CATALOGUE = "lemonfiber-plugins"
#: Where the bundle sits inside the catalogue (REPO-R91).
BUNDLE = pathlib.Path("bundle/bundle.toml")
#: An organisation's name, as it reaches a URL.
OWNER = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9-]{0,38}\Z")


def catalogue_in(core: pathlib.Path) -> tuple[pathlib.Path | None, str]:
    """The catalogue's checkout inside the core, or why there is none."""
    gitmodules = core / ".gitmodules"
    if not gitmodules.is_file():
        return None, f"the core embeds no submodule, so not {CATALOGUE}"
    paths = [path for name, path in submodule_pins.declared(gitmodules.read_text(encoding="utf-8"))
             if name == CATALOGUE]
    if len(paths) != 1:
        return None, f"the core embeds {CATALOGUE} {len(paths)} times, not once"
    where = (core / paths[0]).resolve()
    if where == core.resolve() or not where.is_relative_to(core.resolve()):
        return None, f"the core's {CATALOGUE} submodule does not sit inside it, at {paths[0]}"
    done = subprocess.run(
        ["git", "-C", str(core), "submodule", "update", "--init", "--depth", "1", "--", paths[0]],
        capture_output=True, text=True, check=False,
    )
    if done.returncode != 0:
        lines = done.stderr.strip().splitlines()
        return None, f"the core's {CATALOGUE} could not be checked out: {lines[-1] if lines else 'no output'}"
    return where, ""


def problems(bundle: dict, release: str, owner: str, wanted: list[tuple[str, str]]) -> list[str]:
    """Every way the bundle fails to pin a wanted (repo, id) at `release`."""
    pinned: dict[str, list[dict]] = {}
    for pin in bundle.get("plugin", []):
        if isinstance(pin, dict):
            pinned.setdefault(str(pin.get("id", "")), []).append(pin)
    said = []
    for repo, plugin in wanted:
        pins = pinned.get(plugin, [])
        if len(pins) != 1:
            said.append(f"{plugin}: the bundle pins it {len(pins)} times, not once")
            continue
        pin = pins[0]
        origin = f"https://github.com/{owner}/{repo}"
        if str(pin.get("origin", "")).rstrip("/").removesuffix(".git") != origin:
            said.append(f"{plugin}: pinned from {pin.get('origin')!r}, not {origin!r}, which the train tagged")
        if pin.get("release") != release:
            said.append(f"{plugin}: pinned at release {pin.get('release')!r}, not {release!r}")
    return said


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--core", required=True, type=pathlib.Path)
    ap.add_argument("--owner", required=True)
    a = ap.parse_args()

    if not cut_by_train(a.tag, a.version):
        sys.exit(f"::error::{a.tag!r} is not a tag the train cuts for {a.version!r}")
    if not OWNER.match(a.owner):
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

    catalogue, missing = catalogue_in(core)
    if catalogue is None:
        print(f"::error::{missing}")
        return 1
    bundle = catalogue / BUNDLE
    if not bundle.is_file():
        print(f"::error::the embedded {CATALOGUE} holds no {BUNDLE}")
        return 1
    try:
        read = tomllib.loads(bundle.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as broken:
        print(f"::error::the embedded bundle cannot be read: {broken}")
        return 1

    release = a.tag.removeprefix("v")
    said = problems(read, release, a.owner, wanted)
    for problem in said:
        print(f"::error::{problem}")
    if said:
        print(f"::error::the embedded bundle does not pin what {a.tag} published; "
              "nothing else is tagged until it does")
        return 1
    for _, plugin in wanted:
        print(f"{plugin} is pinned at {release}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
