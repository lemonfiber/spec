#!/usr/bin/env python3
"""Move a `plugin.toml`'s pin to the image its repository published — OPS-R90, OPS-R91.

`manifest-pin` runs this after `first-party-image` or `rust-service-release` published
lemonfiber's own image: every service of the manifest running it moves to the digest
published and to its tag, a train tag's without its `v`, and every recording the
manifest names is taken again from it through `pin_bump.py` (`ARCH-R285`). A train
tag's move goes on `release/image-pin` and a commit's on `release/image-commit-pin`, so
the two never move each other's pull request.

    manifest_pin.py apply   --manifest plugin.toml --image <i> --tag <t> --digest <d> --ref-type <branch|tag>
    manifest_pin.py admit   --manifest plugin.toml --image <i> --tag <t> --digest <d> --ref-type <branch|tag> \\
                            --bump <dir> --move-out <move.json>
    manifest_pin.py message --move move.json --log <url> [--root .]

`apply` moves the pin in the job holding no secret and prints the move as JSON, or
`null` where no service runs the image. `admit` runs in the job holding the App's token
and trusts none of what the other job wrote: it works the move out again from main's
manifest and the image, tag and digest the publishing workflow handed on, then admits
the bump only as `pin_bump.admitted_files` does, writes it into the checkout and prints
each path written. `message` writes the commit message to standard output and the pull
request's title, body and whether it came out clean to `$GITHUB_OUTPUT`, from that move
and the recordings in the checkout alone.

Exit 0 = done, 1 = refused or unreadable (named on standard error), 2 = usage.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import paths
import pin_bump
import plugin_pin
from manifest_repos import IMAGE_HOME

#: The rolling branch each kind of publish moves the pin on.
BRANCHES = {"tag": "release/image-pin", "branch": "release/image-commit-pin"}
#: What the commit and the pull request cite.
CITED = "Spec: OPS-R90, OPS-R91, ARCH-R121, ARCH-R285"
Refused = plugin_pin.Refused


def moved(main_text: str, image: str, tag: str, digest: str, ref_type: str) -> tuple[str, dict | None]:
    """The manifest with every service running `image` at what was published, and the
    move, or the manifest as it was and None where no service runs it."""
    if not image.startswith(f"{IMAGE_HOME}/"):
        raise Refused(f"{image} is not an image lemonfiber publishes")
    if ref_type not in BRANCHES:
        raise Refused(f"a {ref_type!r} publishes no pin")
    pinned = tag.removeprefix("v") if ref_type == "tag" else tag
    written, services = plugin_pin.pinned(main_text, image, pinned, digest)
    if not services:
        return main_text, None
    return written, {
        "image": image,
        "services": services,
        "branch": BRANCHES[ref_type],
        "published": tag,
        "to": {"tag": pinned, "digest": digest},
    }


def admitted(main_text: str, args: argparse.Namespace, bump: pathlib.Path) -> tuple[dict, dict[str, bytes]]:
    """The move and the files a staged bump may commit, or `Refused` naming why."""
    _, move = moved(main_text, args.image, args.tag, args.digest, args.ref_type)
    if move is None:
        raise Refused(f"main's manifest runs no service of {args.image}")
    return move, pin_bump.admitted_files(main_text, move, bump)


def described(move: dict, left: list[str], log: str) -> tuple[str, str, bool]:
    """The pull request's title and body for a move, and whether it came out clean."""
    said = (
        f"Every service of plugin.toml running {move['image']} runs the image {move['published']} published, "
        f"at {move['to']['digest']}."
    )
    body, clean = pin_bump.body_of(said, left, log, CITED)
    return f"chore(manifest): the image at {move['published']}", body, clean


def asked_apply(args: argparse.Namespace) -> int:
    root, text = pin_bump.manifest_text(args.manifest)
    written, move = moved(text, args.image, args.tag, args.digest, args.ref_type)
    if move is not None:
        paths.plain_write(root, pin_bump.MANIFEST_FILE, written.encode())
    print(json.dumps(move, indent=2))
    return 0


def asked_admit(args: argparse.Namespace) -> int:
    root, text = pin_bump.manifest_text(args.manifest)
    move, files = admitted(text, args, paths.plain_directory(args.bump))
    pin_bump.admit_into(root, files, move, args.move_out)
    return 0


def asked_message(args: argparse.Namespace) -> int:
    return pin_bump.message(args, described)


ASKED = {"apply": asked_apply, "admit": asked_admit, "message": asked_message}
#: What publishing named, which `apply` and `admit` both take.
PUBLISHED = ("--manifest", "--image", "--tag", "--digest", "--ref-type")
OPTIONS = {"apply": PUBLISHED, "admit": (*PUBLISHED, "--bump", "--move-out"), "message": ("--move", "--log")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    asked = parser.add_subparsers(dest="asked", required=True)
    for name, options in OPTIONS.items():
        one = asked.add_parser(name)
        for option in options:
            one.add_argument(option, required=True)
    asked.choices["message"].add_argument("--root", default=".")
    args = parser.parse_args(argv)
    try:
        return ASKED[args.asked](args)
    except (OSError, ValueError) as why:
        print(f"::error::{why}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
