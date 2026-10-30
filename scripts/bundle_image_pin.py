#!/usr/bin/env python3
"""Move an image the bundle pins apart from its parts — ARCH-R363.

The fence is no part: no plugin declares it, and lemonfiber writes one beside each
fenced service. So its image is pinned in a table of the bundle's own, `[<service>]`,
rather than in a plugin's manifest, and the train tag that published an image moves
that table to it. This rewrites the table's `image`, `tag` and `digest` in place,
leaving every comment and every other line as it is, and writes the commit message
the rolling pull request takes.

    bundle_image_pin.py apply --bundle <bundle.toml> --service <id> \\
        --repository <owner/name> --image <registry path> --tag <vX.Y.Z> \\
        --digest <sha256:…> --message <file>

Prints `moved=yes` or `moved=no`. Refuses, naming what:

- a repository other than `lemonfiber/lemonfiber-<service>`, the one ADR-0033 builds the
  image in, so no other repository moves its pin;
- an image other than `ghcr.io/lemonfiber/<service>`, a tag the train does not cut, or a
  digest that is not one;
- a digest other than the one the registry answers for the image at that tag, read with
  `docker buildx imagetools inspect` before anything is written;
- a bundle with no `[<service>]` table to move.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

#: Where lemonfiber publishes the images it builds, and nothing else (ADR-0033).
REGISTRY = "ghcr.io/lemonfiber"

SERVICE = re.compile(r"\A[a-z0-9]+(-[a-z0-9]+)*\Z")
TAG = re.compile(r"\Av(\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?)\Z")
DIGEST = re.compile(r"\Asha256:[0-9a-f]{64}\Z")
#: A key of the table, with the quoted value it holds and anything after it on the line.
FIELD = re.compile(r'\A(?P<key>image|tag|digest)(?P<gap>\s*=\s*)"[^"]*"(?P<rest>.*)\Z')


class Refused(Exception):
    """What was asked cannot be pinned, and why."""


def checked(service: str, repository: str, image: str, tag: str, digest: str) -> str:
    """The version `tag` names, once every argument is what the train hands over."""
    if not SERVICE.match(service):
        raise Refused(f"{service!r} is not a service id")
    if repository != f"lemonfiber/lemonfiber-{service}":
        raise Refused(
            f"{repository!r} is not lemonfiber/lemonfiber-{service}, the repository {service} is built in"
        )
    if image != f"{REGISTRY}/{service}":
        raise Refused(f"{image!r} is not {REGISTRY}/{service}, the image {service} is published as")
    version = TAG.match(tag)
    if not version or re.search(r"-rc\d*(\.|\Z)", tag):
        raise Refused(f"{tag!r} is not a tag the train cuts")
    if not DIGEST.match(digest):
        raise Refused(f"{digest!r} is not a sha256 digest")
    return version.group(1)


def published(image: str, tag: str) -> str:
    """The digest the registry answers for `image` at `tag`."""
    asked = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", f"{image}:{tag}", "--format", "{{json .Manifest}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if asked.returncode != 0:
        raise Refused(f"the registry does not answer for {image}:{tag}: {asked.stderr.strip()}")
    try:
        digest = json.loads(asked.stdout)["digest"]
    except (ValueError, KeyError, TypeError) as why:
        raise Refused(f"the registry's answer for {image}:{tag} names no digest") from why
    return str(digest)


def moved(text: str, service: str, image: str, version: str, digest: str) -> str:
    """`text` with the `[<service>]` table naming `image` at `version` and `digest`."""
    wanted = {"image": image, "tag": version, "digest": digest}
    lines = text.split("\n")
    header = f"[{service}]"
    starts = [index for index, line in enumerate(lines) if line.strip() == header]
    if len(starts) != 1:
        raise Refused(f"the bundle holds {len(starts)} {header} tables, and one is moved")
    seen = set()
    for index in range(starts[0] + 1, len(lines)):
        line = lines[index]
        if line.lstrip().startswith("["):
            break
        field = FIELD.match(line)
        if field:
            key = field.group("key")
            seen.add(key)
            lines[index] = f'{key}{field.group("gap")}"{wanted[key]}"{field.group("rest")}'
    missing = sorted(set(wanted) - seen)
    if missing:
        raise Refused(f"{header} names no {', '.join(missing)}")
    return "\n".join(lines)


def message(service: str, image: str, tag: str, digest: str) -> str:
    """The commit message, and so the pull request's title and body."""
    return (
        f"chore(bundle): the {service} image at {tag}\n\n"
        f"The release train tagged {tag} in lemonfiber-{service}, which published\n"
        f"{image}@{digest}. The bundle's [{service}] table now pins it.\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["apply"])
    for name in ("bundle", "service", "repository", "image", "tag", "digest", "message"):
        parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args(argv)
    bundle = pathlib.Path(args.bundle)
    try:
        version = checked(args.service, args.repository, args.image, args.tag, args.digest)
        answered = published(args.image, args.tag)
        if answered != args.digest:
            raise Refused(
                f"{args.image}:{args.tag} is {answered} at the registry, not {args.digest}"
            )
        before = bundle.read_text(encoding="utf-8")
        after = moved(before, args.service, args.image, version, args.digest)
    except (Refused, OSError) as why:
        print(f"::error::{why}", file=sys.stderr)
        return 1
    if after == before:
        print("moved=no")
        return 0
    bundle.write_text(after, encoding="utf-8")
    pathlib.Path(args.message).write_text(
        message(args.service, args.image, args.tag, args.digest), encoding="utf-8"
    )
    print("moved=yes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
