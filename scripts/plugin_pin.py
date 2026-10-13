#!/usr/bin/env python3
"""Set the pin of every service in a `plugin.toml` that runs one image — OPS-R85.

Every bump that moves an image pin in a plugin's manifest writes it here: the release
lanes moving lemonfiber's own image to what they published (`OPS-R90`, `OPS-R91`), and
`upstream-pins` moving an upstream's image to the newest release of its major
(`REPO-R98`).

The manifest is edited as text rather than re-serialised, so every comment and every
other line stays byte for byte what it was. In each `[[service]]` block that runs the
image, its one `digest` line and its one `tag` line take the new values, aligned as they
were. The result is read back and refused unless it is the manifest it was with exactly
those services moved, and nothing else.

    plugin_pin.py --manifest plugin.toml --image <image> --tag <tag> --digest <digest>

Prints the id of each service moved, one a line, and nothing where no service runs the
image. Exit 0 = written or nothing to write, 1 = refused, naming why.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import tomllib

import paths
from patterns import DIGEST, IMAGE_TAG

#: The two fields a pin is, in the order they are written.
FIELDS = ("digest", "tag")
#: The most of a manifest that is read.
MANIFEST_LIMIT = 256 * 1024


class Refused(ValueError):
    """The manifest cannot be moved as asked; the message says why."""


def running(manifest: dict, image: str) -> list[dict]:
    """The services of a parsed manifest that run `image`."""
    return [one for one in manifest.get("service", []) if one.get("image") == image]


def pinned(text: str, image: str, tag: str, digest: str) -> tuple[str, list[str]]:
    """`text` with every service running `image` at `tag` and `digest`, and their ids."""
    if not DIGEST.match(digest):
        raise Refused(f"{digest!r} is not a sha256 digest")
    if not IMAGE_TAG.match(tag):
        raise Refused(f"{tag!r} is not a tag")
    before = tomllib.loads(text)
    declared = running(before, image)
    blocks = re.split(r"(?m)^(?=\[)", text)
    written_so = [
        at for at, block in enumerate(blocks)
        if block.startswith("[[service]]")
        and re.search(rf'(?m)^image\s*=\s*"{re.escape(image)}"\s*$', block)
    ]
    if len(written_so) != len(declared):
        raise Refused(f"{len(declared)} services run {image} and {len(written_so)} are written so this can move them")
    for at in written_so:
        block = blocks[at]
        for field, value in zip(FIELDS, (digest, tag), strict=True):
            block, changed = re.subn(rf'(?m)^{field}(\s*)=\s*"[^"]*"', rf'{field}\g<1>= "{value}"', block)
            if changed != 1:
                raise Refused(f"a service running {image} does not declare `{field}` once")
        blocks[at] = block
    written = "".join(blocks)
    for one in declared:
        one.update(digest=digest, tag=tag)
    if tomllib.loads(written) != before:
        raise Refused(f"the manifest as written is not the one it was with {image} at {tag} and {digest}")
    return written, [str(one.get("id")) for one in declared]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--digest", required=True)
    args = parser.parse_args(argv)
    cwd = pathlib.Path.cwd().resolve()
    try:
        relative = paths.plain_relative(args.manifest)
        text = paths.plain_read(cwd, relative, MANIFEST_LIMIT).decode("utf-8")
        written, moved = pinned(text, args.image, args.tag, args.digest)
        if moved:
            paths.plain_write(cwd, relative, written.encode("utf-8"))
    except (OSError, ValueError) as why:
        print(f"::error::{why}", file=sys.stderr)
        return 1
    for sid in moved:
        print(sid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
