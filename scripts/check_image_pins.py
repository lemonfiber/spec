#!/usr/bin/env python3
"""The embedded stack pins each image the train tagged, at that tag — ADR-0033 §4.

A version that cuts a repository building one of the stack's own images tags it
first. The tag publishes the image, the stack pins it, and the core's submodule
takes that stack. Only then may the core be tagged, and this is the check that
says whether that point has arrived: for every image the version cuts, the stack
the core embeds names lemonfiber's image, at the tag being cut, by the digest the
registry holds for that tag.

The registry is asked through `docker buildx imagetools inspect`, which reads the
index without pulling anything. A tag the registry does not hold is refused as
unpublished.

The stack is read as lemonfiber reads it: the root and each file its `include`
names, joined in order (ARCH-R171), or a manifest from before the split as it is.

Usage:
  check_image_pins.py --version X.Y.Z --tag <tag> --stack <stack.toml>

Exit 0 = every image the version cuts is pinned at the tag and its digest, or it
cuts none, 1 = one is not, or the stack or the registry cannot be read, 2 = usage.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tomllib

import manifest_repos
import stack_manifest
from manifest_repos import IMAGE_HOME
from patterns import PRERELEASE_ID, PRERELEASE_SEPARATOR, VERSION

#: The digest of a multi-architecture index, as a stack pin writes it (ADR-0023).
DIGEST = re.compile(r"\Asha256:[0-9a-f]{64}\Z")

#: What may be handed to docker as a reference: letters or digits first, so
#: nothing beginning with a dash arrives as a flag. Kept beside the call it
#: guards, where an analysis of that call can see it.
_REFERENCE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._/:-]{0,255}\Z")


def cut_by_train(tag: str, version: str) -> bool:
    """Whether a tag is one the train cuts for `version`: `v<version>`, or that with a
    pre-release identifier (OPS-R61). It becomes part of a reference handed to
    docker, so it is held to this before anything else reads it."""
    named, dash, identifier = tag.removeprefix("v").partition(PRERELEASE_SEPARATOR)
    return (tag.startswith("v") and named == version and bool(VERSION.match(version))
            and (not dash or bool(PRERELEASE_ID.match(identifier))))


def digest_of(reference: str) -> tuple[str, str]:
    """The digest the registry holds for a reference, or why there is none."""
    if not _REFERENCE.match(reference):
        return "", f"{reference!r} is not a reference this hands to docker"
    result = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", reference, "--format", "{{json .Manifest}}"],
        capture_output=True, text=True, check=False,
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


def problems(stack: dict, tag: str, wanted: dict[str, str]) -> list[str]:
    """Every way the stack fails to pin a wanted service at `tag` and its digest."""
    declared: dict[str, list[dict]] = {}
    for entry in stack.get("service", []):
        declared.setdefault(str(entry.get("id", "")), []).append(entry)

    said = []
    for service, digest in wanted.items():
        entries = declared.get(service, [])
        if len(entries) != 1:
            said.append(f"{service}: the stack declares it {len(entries)} times, not once")
            continue
        entry = entries[0]
        image = f"{IMAGE_HOME}/{service}"
        if entry.get("image") != image:
            said.append(f"{service}: image is {entry.get('image')!r}, not {image!r}")
        if entry.get("tag") != tag:
            said.append(f"{service}: pinned at tag {entry.get('tag')!r}, not {tag!r}")
        if entry.get("digest") != digest:
            said.append(f"{service}: pinned at digest {entry.get('digest')!r}, "
                        f"not {digest!r}, which {image}:{tag} published")
    return said


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--stack", required=True, type=pathlib.Path)
    a = ap.parse_args()

    if not cut_by_train(a.tag, a.version):
        sys.exit(f"::error::{a.tag!r} is not a tag the train cuts for {a.version!r}")
    path = manifest_repos.manifest_for(a.version)
    if not path.is_file():
        print(f"::error::no manifest at {path}", file=sys.stderr)
        return 1
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    registry = tomllib.loads(manifest_repos.REGISTRY.read_text(encoding="utf-8"))
    cut = manifest_repos.images(data, registry)
    if not cut:
        print(f"{a.version} cuts no image the stack has to pin.")
        return 0
    stack = a.stack.resolve()
    if not stack.is_relative_to(pathlib.Path.cwd().resolve()):
        sys.exit(f"::error::path escapes the working directory: {a.stack}")
    if not stack.is_file():
        print(f"::error::no stack manifest at {a.stack}", file=sys.stderr)
        return 1

    try:
        text, unread = stack_manifest.joined(stack.read_text(encoding="utf-8"),
                                             stack_manifest.on_disk(stack.parent))
        declared = tomllib.loads(text)
    except tomllib.TOMLDecodeError as broken:
        print(f"::error::the stack manifest cannot be read: {broken}")
        return 1
    said = [f"the stack includes {entry}, which is not a service file beside it" for entry in unread]
    wanted = {}
    for _, service, image in cut:
        digest, missing = digest_of(f"{image}:{a.tag}")
        if missing:
            said.append(missing)
        else:
            wanted[service] = digest
    said += problems(declared, a.tag, wanted)
    for problem in said:
        print(f"::error::{problem}")
    if said:
        print(f"::error::the embedded stack does not pin what {a.tag} published; "
              "nothing else is tagged until it does")
        return 1
    for service, digest in wanted.items():
        print(f"{service} is pinned at {a.tag}, {digest}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
