#!/usr/bin/env python3
"""Which repositories a version cuts, and which its goal gate searches — OPS-R58.

Two questions that used to be one list, and were not the same question. `repos`
is what a version *cuts*: execute tags every one of them, so a name in it is a
release. The gate asks something else — where the work satisfying the goals
landed — and read `repos` for want of anywhere better to look.

It costs both ways round. `0.10.0` names only `lemonfiber`, and `ARCH-R55` is
cited only in `lemonfiber-web`: its gate calls that goal unmet for a reason that
has nothing to do with the work. `0.9.0` avoided that by putting `lemonfiber-web`
in `repos` — and so declared a release stream it cuts nothing from. Nobody has
been hurt by that yet only because the last version to go through
`execute-version` was `0.7.0` and everything since was tagged by hand; the first
one that does not will tag `lemonfiber-web`, whose `publish.yml` fires on a
version tag and would publish a build nobody asked for.

So a manifest may say `satisfied_in`, and where it does not, the streams it cuts
are searched: the two coincide for every version so far, and a default that keeps
them coinciding is the one that needs no migration.

A version that cuts a repository building one of the stack's own images is cut
in two steps (ADR-0033 §4): those repositories are tagged first, and the rest once
the stack the core embeds pins what those tags published. The registry, not the
manifest, says which repositories those are: a `[[repo]]` entry in
`30-repos/repos.toml` carrying `service` builds the image of that stack service.
Whether a repository builds an image is a fact about the repository, and every
version that cuts it reads the same answer.

A first-party plugin's repository is tagged in that first step too (OPS-R86): a
`[[repo]]` entry carrying `plugin` is `plugin-<id>`, and its tag publishes the
adapter image the bundle pins. Every version that cuts the core cuts each of
them, so a manifest not yet released that names the core and leaves one out is
refused.

Usage:
  manifest_repos.py --version X.Y.Z --for cut|searched|images|plugins|others
Prints one repository per line; `images` prints `<repo>\t<service>\t<image>`,
`plugins` prints `<repo>\t<id>`. `images`, `plugins` and `others` together are
`cut`, and any of them may be empty. Exit 0 = printed, 1 = no such manifest, a
registry entry that breaks ADR-0033 §1 or OPS-R86, or a manifest that cuts the
core without a first-party plugin, 2 = usage.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import tomllib

from patterns import STATES
from patterns import VERSION as VERSION_RE

VERSIONS_DIR = pathlib.Path("70-operations/versions")
REGISTRY = pathlib.Path("30-repos/repos.toml")

#: What a version cuts. Every name here is tagged at execute.
CUT = "repos"
#: Where its goals were satisfied. Naming one here tags nothing.
SEARCHED = "satisfied_in"

#: The registry field naming the stack service a repository builds the image of.
SERVICE = "service"
#: Where every image lemonfiber builds is published (ADR-0033 §1).
IMAGE_HOME = "ghcr.io/lemonfiber"
#: What a repository building a service's image is called (ADR-0033 §1).
REPO_PREFIX = "lemonfiber-"
#: A stack service id. It becomes part of an image reference handed to docker,
#: so it is held to lowercase words joined by single dashes.
SERVICE_ID = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z")

#: The registry field naming the first-party plugin a repository publishes.
PLUGIN = "plugin"
#: What a first-party plugin's repository is called.
PLUGIN_PREFIX = "plugin-"
#: A plugin id, as a plugin's manifest and the catalogue write it.
PLUGIN_ID = re.compile(r"\A[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")

#: The core's repository: the one whose releases carry the changelog, and whose
#: every version cuts each first-party plugin.
CORE = "lemonfiber"
#: The states after which a manifest is a record rather than a plan.
SETTLED = STATES[STATES.index("released"):]


def cut(data: dict) -> list[str]:
    """The release streams this version tags."""
    return [str(name) for name in data.get(CUT, [])]


def searched(data: dict) -> list[str]:
    """The repositories the goal gate reads commit messages from.

    Falls back to the streams rather than to nothing: a manifest that says
    nothing is every manifest written before this existed, and searching none of
    them would report every goal unmet — a gate that fails loudly for a reason
    that is not true is no better than one that passes quietly for a reason that
    is not either.
    """
    named = data.get(SEARCHED)
    if not named:
        return cut(data)
    return [str(name) for name in named]


def image_repos(registry: dict) -> dict[str, str]:
    """Every governed repository that builds a stack image, mapped to its service.

    An entry whose name is not `lemonfiber-<service>`, or whose service is not a
    service id, is refused rather than skipped: skipped, it would be cut with the
    core in one step, which is the release ADR-0033 §4 rules out.
    """
    found = {}
    for entry in registry.get("repo", []):
        if SERVICE not in entry:
            continue
        name, service = str(entry.get("name", "")), str(entry[SERVICE])
        if not SERVICE_ID.match(service):
            sys.exit(f"::error::{REGISTRY}: {name}'s {SERVICE} {service!r} is not a service id")
        if name != f"{REPO_PREFIX}{service}":
            sys.exit(f"::error::{REGISTRY}: {name} builds {service!r}, so ADR-0033 §1 names it "
                     f"{REPO_PREFIX}{service}")
        found[name] = service
    return found


def plugin_repos(registry: dict) -> dict[str, str]:
    """Every governed repository that publishes a first-party plugin, mapped to its id.

    Refused rather than skipped where the name is not `plugin-<id>`, the id is not a
    plugin id, or the entry also builds a stack service: skipped, it would be cut
    with the core in one step, and the bundle would pin a release not yet tagged.
    """
    found = {}
    for entry in registry.get("repo", []):
        if PLUGIN not in entry:
            continue
        name, plugin = str(entry.get("name", "")), str(entry[PLUGIN])
        if not PLUGIN_ID.match(plugin):
            sys.exit(f"::error::{REGISTRY}: {name}'s {PLUGIN} {plugin!r} is not a plugin id")
        if name != f"{PLUGIN_PREFIX}{plugin}":
            sys.exit(f"::error::{REGISTRY}: {name} publishes {plugin!r}, so it is named "
                     f"{PLUGIN_PREFIX}{plugin}")
        if SERVICE in entry:
            sys.exit(f"::error::{REGISTRY}: {name} carries both {SERVICE} and {PLUGIN}")
        found[name] = plugin
    return found


def images(data: dict, registry: dict) -> list[tuple[str, str, str]]:
    """The stack images this version tags first, as (repo, service, image)."""
    built = image_repos(registry)
    return [(name, built[name], f"{IMAGE_HOME}/{built[name]}") for name in cut(data) if name in built]


def plugins(data: dict, registry: dict) -> list[tuple[str, str]]:
    """The first-party plugins this version tags first, as (repo, id)."""
    published = plugin_repos(registry)
    return [(name, published[name]) for name in cut(data) if name in published]


def first(data: dict, registry: dict) -> list[str]:
    """Every stream this version tags before the core."""
    return [*(name for name, _, _ in images(data, registry)), *(name for name, _ in plugins(data, registry))]


def others(data: dict, registry: dict) -> list[str]:
    """The streams this version tags once the core embeds what the first step published."""
    early = set(first(data, registry))
    return [name for name in cut(data) if name not in early]


def unlisted_plugins(data: dict, registry: dict) -> list[str]:
    """The first-party plugins a manifest not yet released cuts the core without (OPS-R86)."""
    named = cut(data)
    if data.get("status") in SETTLED or CORE not in named:
        return []
    return [name for name in plugin_repos(registry) if name not in named]


def unlisted(missing: list[str]) -> str:
    """What is wrong with a manifest that cuts the core without `missing`."""
    return (f"cuts {CORE} and not {', '.join(missing)}; every version that cuts the core "
            "cuts each first-party plugin (OPS-R86)")


def manifest_for(version: str) -> pathlib.Path:
    """The manifest path for a validated version, built from a constant base."""
    if not VERSION_RE.match(version):
        sys.exit(f"::error::version must be X.Y.Z, got {version!r}")
    path = (VERSIONS_DIR / f"{version}.toml").resolve()
    if not path.is_relative_to(VERSIONS_DIR.resolve()):
        sys.exit(f"::error::path escapes {VERSIONS_DIR}")  # pragma: no cover
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--for", dest="asked", required=True,
                    choices=("cut", "searched", "images", "plugins", "others"))
    a = ap.parse_args()

    path = manifest_for(a.version)
    if not path.is_file():
        print(f"::error::no manifest at {path}", file=sys.stderr)
        return 1
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if a.asked in ("images", "plugins", "others"):
        registry = tomllib.loads(REGISTRY.read_text(encoding="utf-8"))
        missing = unlisted_plugins(data, registry)
        if missing:
            print(f"::error::{path.name} {unlisted(missing)}", file=sys.stderr)
            return 1
        listed = {"images": images, "plugins": plugins}
        rows = (["\t".join(row) for row in listed[a.asked](data, registry)] if a.asked in listed
                else others(data, registry))
        if rows:
            print("\n".join(rows))
        return 0
    names = cut(data) if a.asked == "cut" else searched(data)
    # A version that cuts nothing is a manifest somebody has not finished. Said
    # here rather than left for whichever `while read` loop iterates over an
    # empty file and reports success for having done nothing.
    if not names:
        print(f"::error::{path.name} names no repositories to {a.asked}", file=sys.stderr)
        return 1
    print("\n".join(names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
