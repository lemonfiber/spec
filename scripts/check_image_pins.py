#!/usr/bin/env python3
"""The embedded bundle pins each image the train tagged, at that tag — ADR-0033 §4.

A version that cuts a repository building one of the stack's own images tags it
first. The tag publishes the image, the repository's own `plugin.toml` pins it, the
catalogue's bundle takes that manifest, and the core's submodule takes that
catalogue. Only then may the core be tagged, and this is the check that says
whether that point has arrived: for every image the version cuts, the bundle the
core embeds pins the service from the repository the train tagged, and the copy
beside that pin runs lemonfiber's image at the tag being cut, without its `v`, by
the digest the registry holds for that tag.

It runs before a release tag only: a pre-release tags none of these repositories
(OPS-R86), and `check_bundle_pins.py` holds the same pins to the release.

The registry is asked through `docker buildx imagetools inspect`, which reads the
index without pulling anything. A tag the registry does not hold is refused as
unpublished.

Usage:
  check_image_pins.py --version X.Y.Z --tag <tag> --core <core checkout> --owner <org>

Exit 0 = every image the version cuts is pinned at the tag and its digest, or it
cuts none, 1 = one is not, or the bundle or the registry cannot be read, 2 = usage.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tomllib

import embedded_bundle
import manifest_repos
from patterns import DIGEST, PRERELEASE_ID, PRERELEASE_SEPARATOR, VERSION

#: What may be handed to docker as a reference: letters or digits first, so
#: nothing beginning with a dash arrives as a flag. Kept beside the call it
#: guards, where an analysis of that call can see it.
_REFERENCE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._/:-]{0,255}\Z")


def cut_by_train(tag: str, version: str) -> bool:
    """Whether a tag is one the train cuts for `version`: `v<version>`, or that with a
    pre-release identifier (OPS-R61). It becomes part of a reference handed to
    docker, so it is held to this before anything else reads it."""
    named, dash, identifier = tag.removeprefix("v").partition(PRERELEASE_SEPARATOR)
    return (
        tag.startswith("v")
        and named == version
        and bool(VERSION.match(version))
        and (not dash or bool(PRERELEASE_ID.match(identifier)))
    )


def digest_of(reference: str) -> tuple[str, str]:
    """The digest the registry holds for a reference, or why there is none."""
    if not _REFERENCE.match(reference):
        return "", f"{reference!r} is not a reference this hands to docker"
    result = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", reference, "--format", "{{json .Manifest}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        lines = result.stderr.strip().splitlines()
        return "", f"{reference} is not published ({lines[-1] if lines else 'inspect failed'})"
    try:
        digest = json.loads(result.stdout).get("digest", "")
    except (json.JSONDecodeError, AttributeError):
        return "", f"the registry's answer for {reference} is not a descriptor"
    if not DIGEST.match(str(digest)):
        return "", f"the registry names {reference}'s digest {digest!r}, which is not one"
    return digest, ""


def problems(copy: dict, image: str, tag: str, digest: str) -> list[str]:
    """Every way a copy's manifest fails to run `image` at `tag`, without its `v`, and `digest`."""
    pinned = tag.removeprefix("v")
    running = [one for one in copy.get("service", []) if isinstance(one, dict) and one.get("image") == image]
    if not running:
        return [f"no service of its copy runs {image}"]
    said = []
    for service in running:
        name = service.get("id")
        if service.get("tag") != pinned:
            said.append(f"{name}: pinned at tag {service.get('tag')!r}, not {pinned!r}")
        if service.get("digest") != digest:
            said.append(
                f"{name}: pinned at digest {service.get('digest')!r}, "
                f"not {digest!r}, which {image}:{tag} published"
            )
    return said


def tabled(table: dict, image: str, tag: str, digest: str) -> list[str]:
    """Every way the bundle's own table for an image fails to pin `image` at `tag`, without
    its `v`, and `digest` (OPS-R94)."""
    pinned = tag.removeprefix("v")
    said = []
    if table.get("image") != image:
        said.append(f"its table pins {table.get('image')!r}, not {image!r}")
    if table.get("tag") != pinned:
        said.append(f"its table pins tag {table.get('tag')!r}, not {pinned!r}")
    if table.get("digest") != digest:
        said.append(f"its table pins digest {table.get('digest')!r}, not {digest!r}, which {image}:{tag} published")
    return said


def unpinned(
    core: pathlib.Path, owner: str, tag: str, cut: list[tuple[str, str, str]]
) -> tuple[list[str], list[str]]:
    """Every way the bundle the core embeds fails to pin what `tag` published, and the
    services it pins."""
    try:
        catalogue, bundle = embedded_bundle.read(core)
    except embedded_bundle.Unread as why:
        return [str(why)], []
    said, pinned = [], []
    for repo, service, image in cut:
        digest, missing = digest_of(f"{image}:{tag}")
        if missing:
            said.append(missing)
            continue
        table = embedded_bundle.own_table(bundle, service)
        if table is not None:
            wrong = [f"{service}: {problem}" for problem in tabled(table, image, tag, digest)]
            said += wrong
            if not wrong:
                pinned.append(f"{service} is pinned at {tag}, {digest}.")
            continue
        _, wrong = embedded_bundle.pinned_once(bundle, service, embedded_bundle.origin(owner, repo))
        if wrong:
            said += wrong
            continue
        try:
            copy = embedded_bundle.copy(catalogue, bundle, service)
        except embedded_bundle.Unread as why:
            said.append(str(why))
            continue
        wrong = [f"{service}: {problem}" for problem in problems(copy, image, tag, digest)]
        said += wrong
        if not wrong:
            pinned.append(f"{service} is pinned at {tag}, {digest}.")
    return said, pinned


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
    cut = manifest_repos.images(data, registry)
    if not cut:
        print(f"{a.version} cuts no image the bundle has to pin.")
        return 0
    core = a.core.resolve()
    if not core.is_relative_to(pathlib.Path.cwd().resolve()):
        sys.exit(f"::error::path escapes the working directory: {a.core}")

    said, pinned = unpinned(core, a.owner, a.tag, cut)
    for problem in said:
        print(f"::error::{problem}")
    if said:
        print(
            f"::error::the embedded bundle does not pin what {a.tag} published; "
            "nothing else is tagged until it does"
        )
        return 1
    print("\n".join(pinned))
    return 0


if __name__ == "__main__":
    sys.exit(main())
