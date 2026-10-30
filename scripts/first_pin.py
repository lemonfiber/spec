#!/usr/bin/env python3
"""What a first-party plugin's Dockerfile stands in for, and whether a built part's
revision may ship: only once its own image is pinned — ARCH-R285.

    first_pin.py ships --owner <organisation> [--directory .]
    first_pin.py stands-in --owner <organisation> [--directory .]

`stands-in` prints what the image the `Dockerfile` builds stands in for when the live
pass records: `adapter` where a service fronts one; `built` where no service speaks a
contract and the service whose id is the plugin's runs `ghcr.io/<owner>/<plugin id>`;
`built unpinned` where no service speaks a contract and that service runs exactly the
image and digest the `Dockerfile`'s last `FROM` names, a tag between them aside; and
nothing otherwise, or where there is no `Dockerfile`.

A part whose tree holds a `Dockerfile` builds the image its service whose id is the
plugin's runs. Until the first pin of that image merges, its manifest names the
upstream image the `Dockerfile` builds on, which lacks what the `Dockerfile` adds for the
posture lemonfiber runs it under. Such a revision is recorded from the image it builds,
and ships nothing: it is refused here wherever that service runs the image the
`Dockerfile`'s last `FROM` names, at any digest, and not `ghcr.io/<owner>/<plugin id>`.

A tree with no `Dockerfile`, or whose service of the plugin's id runs any other image,
is not refused: an adapter's `Dockerfile` builds on a base its upstream does not run.

`ships` prints nothing where the revision may ship. Exit 0 = it may, or `stands-in`
answered, 1 = it may not (named on standard error), 2 = usage or a manifest that cannot
be read.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import tomllib

REFERENCE = re.compile(r"((?:[^@/:]+(?::[0-9]+)?/)?[^@:]+)(?::[^@/]+)?(?:@(sha256:[0-9a-f]{64}))?")


def built_on(dockerfile: str) -> tuple[str, str | None] | None:
    """The image and digest the last `FROM` of `dockerfile` names, or none where it names
    no image reference, flags and a stage name aside."""
    stages = [
        line.split()[1:]
        for line in dockerfile.splitlines()
        if line.split()[:1] and line.split()[0].upper() == "FROM"
    ]
    words = [word for word in (stages[-1] if stages else []) if not word.startswith("--")]
    found = REFERENCE.fullmatch(words[0]) if words else None
    return (found.group(1), found.group(2)) if found else None


def unshipped(manifest: dict, dockerfile: str | None, owner: str) -> str | None:
    """Why a revision whose manifest is `manifest` and whose `Dockerfile` is `dockerfile`
    may not ship, or none where it may."""
    if dockerfile is None:
        return None
    plugin = manifest.get("plugin", {}).get("id", "")
    own = f"ghcr.io/{owner.lower()}/{plugin}"
    base = built_on(dockerfile)
    for service in manifest.get("service", []):
        image = service.get("image", "")
        if service.get("id") != plugin or image == own or base is None or image != base[0]:
            continue
        return (
            f"service {plugin} runs {image}, the image its Dockerfile builds on, not {own}, "
            "the image it builds: this revision ships nothing until the first pin of that "
            "image merges"
        )
    return None


def stands_in(manifest: dict, dockerfile: str | None, owner: str) -> str:
    """What the image `dockerfile` builds stands in for in a manifest `manifest`."""
    if dockerfile is None:
        return ""
    services = manifest.get("service", [])
    plugin = manifest.get("plugin", {}).get("id", "")
    own = f"ghcr.io/{owner.lower()}/{plugin}"
    ours = [one for one in services if one.get("id") == plugin]
    base = built_on(dockerfile)
    if any("fronts" in one for one in services):
        return "adapter"
    if any(one.get("speaks") for one in services):
        return ""
    if any(one.get("image") == own for one in ours):
        return "built"
    if (
        base is not None
        and base[1] is not None
        and any((one.get("image"), one.get("digest")) == base for one in ours)
    ):
        return "built unpinned"
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("asked", choices=("ships", "stands-in"))
    parser.add_argument("--owner", required=True)
    parser.add_argument("--directory", default=".")
    asked = parser.parse_args(argv)
    root = pathlib.Path(asked.directory)
    try:
        manifest = tomllib.loads((root / "plugin.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as unread:
        print(f"plugin.toml could not be read: {unread}", file=sys.stderr)
        return 2
    dockerfile = root / "Dockerfile"
    text = dockerfile.read_text(encoding="utf-8") if dockerfile.is_file() else None
    if asked.asked == "stands-in":
        print(stands_in(manifest, text, asked.owner))
        return 0
    why = unshipped(manifest, text, asked.owner)
    if why is not None:
        print(why, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
