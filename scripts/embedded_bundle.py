#!/usr/bin/env python3
"""The bundle a core checkout embeds, and whether that core reads it — OPS-R35, OPS-R86.

The core embeds the catalogue, `lemonfiber-plugins`, as a submodule, and builds the
stack it ships from the catalogue's `bundle/bundle.toml` and the copy of each plugin
pinned beside it (ADR-0042). The catalogue is found as the submodule of the core
whose URL names `lemonfiber-plugins`, read from the core's own `.gitmodules`, so no
path is assumed, and is checked out at the commit the core pins.

The train reads the bundle before it tags the core: the bundle's pins
(`check_bundle_pins.py`), the images the copies pin (`check_image_pins.py`), and
here, whether the core reads the bundle's schema at all. The schemas the core reads
are `lemonfiber-bundle`'s `SCHEMAS`, read from its source as text and never run.

Usage:
  embedded_bundle.py --core <core checkout>

Exit 0 = the core reads the schema its embedded bundle is written in, 1 = it does
not, or the catalogue, the bundle or the core's schemas cannot be read, 2 = usage.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import tomllib

import submodule_pins
from manifest_repos import SERVICE_ID

#: The catalogue the core embeds the bundle from (ADR-0042).
CATALOGUE = "lemonfiber-plugins"
#: Where the bundle sits inside the catalogue (REPO-R91).
BUNDLE = pathlib.Path("bundle/bundle.toml")
#: Where each pinned plugin's copy sits inside the catalogue, by the bundle's schema.
COPIES = {1: "bundle/plugins/{id}.toml", 2: "bundle/plugins/{id}/plugin.toml"}
#: The core's source declaring which bundle schemas it reads.
READER = pathlib.Path("crates/lemonfiber-bundle/src/lib.rs")
#: That declaration: `pub const SCHEMAS: [u32; 2] = [1, 2];`.
SCHEMAS = re.compile(r"^pub const SCHEMAS: \[u32; \d+\] = \[([\d, ]*)\];", re.MULTILINE)
#: An organisation's name, as it reaches a URL.
OWNER = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9-]{0,38}\Z")


class Unread(Exception):
    """What could not be read; the message says what and why."""


def catalogue_in(core: pathlib.Path) -> pathlib.Path:
    """The catalogue's checkout inside the core, checked out at the commit the core pins."""
    gitmodules = core / ".gitmodules"
    if not gitmodules.is_file():
        raise Unread(f"the core embeds no submodule, so not {CATALOGUE}")
    paths = [path for name, path in submodule_pins.declared(gitmodules.read_text(encoding="utf-8"))
             if name == CATALOGUE]
    if len(paths) != 1:
        raise Unread(f"the core embeds {CATALOGUE} {len(paths)} times, not once")
    where = (core / paths[0]).resolve()
    if where == core.resolve() or not where.is_relative_to(core.resolve()):
        raise Unread(f"the core's {CATALOGUE} submodule does not sit inside it, at {paths[0]}")
    done = subprocess.run(
        ["git", "-C", str(core), "submodule", "update", "--init", "--depth", "1", "--", paths[0]],
        capture_output=True, text=True, check=False,
    )
    if done.returncode != 0:
        lines = done.stderr.strip().splitlines()
        raise Unread(f"the core's {CATALOGUE} could not be checked out: {lines[-1] if lines else 'no output'}")
    return where


def read(core: pathlib.Path) -> tuple[pathlib.Path, dict]:
    """The catalogue's checkout inside the core, and the bundle it holds."""
    catalogue = catalogue_in(core)
    bundle = catalogue / BUNDLE
    if not bundle.is_file():
        raise Unread(f"the embedded {CATALOGUE} holds no {BUNDLE}")
    try:
        return catalogue, tomllib.loads(bundle.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as broken:
        raise Unread(f"the embedded bundle cannot be read: {broken}") from broken


def copy(catalogue: pathlib.Path, bundle: dict, plugin: str) -> dict:
    """The manifest of the copy the bundle holds of `plugin`."""
    layout = COPIES.get(bundle.get("schema"))
    if layout is None:
        raise Unread(f"the embedded bundle is schema {bundle.get('schema')!r}, which keeps no copy this reads")
    if not SERVICE_ID.match(plugin):
        raise Unread(f"{plugin!r} is not a plugin id")
    path = catalogue / layout.format(id=plugin)
    if not path.resolve().is_relative_to(catalogue.resolve()):
        raise Unread(f"{plugin}: its copy at {layout.format(id=plugin)} leads out of the catalogue")
    if not path.is_file():
        raise Unread(f"{plugin}: the embedded bundle holds no copy of it at {layout.format(id=plugin)}")
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as broken:
        raise Unread(f"{plugin}: its copy cannot be read: {broken}") from broken


def origin(owner: str, repo: str) -> str:
    """The address a pin from `owner`'s repository `repo` names as its origin."""
    return f"https://github.com/{owner}/{repo}"


def pinned_once(bundle: dict, plugin: str, origin: str) -> tuple[dict | None, list[str]]:
    """The bundle's one pin of `plugin`, and every way it fails to be one pin from `origin`."""
    pins = [pin for pin in bundle.get("plugin", []) if isinstance(pin, dict) and pin.get("id") == plugin]
    if len(pins) != 1:
        return None, [f"{plugin}: the bundle pins it {len(pins)} times, not once"]
    pin = pins[0]
    if str(pin.get("origin", "")).rstrip("/").removesuffix(".git") != origin:
        return pin, [f"{plugin}: pinned from {pin.get('origin')!r}, not {origin!r}, which the train tagged"]
    return pin, []


def reads(core: pathlib.Path) -> list[int]:
    """The bundle schemas the core reads."""
    source = core / READER
    found = SCHEMAS.search(source.read_text(encoding="utf-8")) if source.is_file() else None
    schemas = [int(one) for one in re.findall(r"\d+", found.group(1))] if found else []
    if not schemas:
        raise Unread(f"the core declares no bundle schema it reads in {READER}")
    return schemas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True, type=pathlib.Path)
    a = ap.parse_args()

    core = a.core.resolve()
    if not core.is_relative_to(pathlib.Path.cwd().resolve()):
        sys.exit(f"::error::path escapes the working directory: {a.core}")
    try:
        _, bundle = read(core)
        schemas = reads(core)
    except Unread as why:
        print(f"::error::{why}")
        return 1
    written = bundle.get("schema")
    listed = ", ".join(map(str, schemas))
    if written not in schemas:
        print(f"::error::the embedded bundle is schema {written!r}, and the core reads {listed}")
        return 1
    print(f"compat ok: the embedded bundle is schema {written}, and the core reads {listed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
