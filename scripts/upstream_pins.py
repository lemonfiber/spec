#!/usr/bin/env python3
"""Move each upstream image a `plugin.toml` pins to the newest release of its major — REPO-R98.

An upstream image is one not under `ghcr.io/lemonfiber/`: lemonfiber's own images move
when their repository publishes one (`OPS-R90`, `OPS-R91`). For each upstream image this
finds the newest tag its registry publishes that

  - is spelled the way the pinned tag is spelled: the same prefix, the same number of
    dotted numbers and the same suffix, so `v3.41.3` follows `v3.40.0` and `4.5.5`
    follows `4.5.1`, while `12.0-rc7`, `4.0.16-develop` and `4.5.5.1234-ls200` are
    other spellings and are never taken. A fixed build tag, one ending in `-ls` and its
    build's number, follows only another: the numbers in its suffix and its build
    number count after its version, so `4.0.20.3014-ls327` follows `4.0.20.3014-ls326`
    and `5.2.5_v2.0.15-ls480` follows `5.2.4_v2.0.15-ls479`;
  - has the same first number as the pinned tag, which is its major. A major carries
    breaking changes and is the operator's decision (`E1-R10`), so a pin never crosses
    one here;

and resolves it to the digest of its multi-architecture index, which must publish both
`linux/amd64` and `linux/arm64` (`E1-R1`, `F2-R6`). A tag that stays where it is can
still move: publishers rebuild a release on a patched base under the same tag, and the
digest follows that rebuild too.

    upstream_pins.py plan     --manifest plugin.toml                JSON: each pin that would move, each problem
    upstream_pins.py apply    --manifest plugin.toml --image <i>    move it; JSON: the move, or null
    upstream_pins.py artifact --manifest plugin.toml --image <i>    `name=` the bump travels under
    upstream_pins.py admit    --manifest plugin.toml --image <i> --bump <dir> --move-out <move.json>
    upstream_pins.py message  --move move.json --log <url> [--root .]

The recordings are taken again and staged by `pin_bump.py`, in the job holding no
secret. `admit` runs in the job that holds the App's token and trusts none of what that
job wrote. It works the move out again from main's manifest and the registry, and
admits the bump only as `pin_bump.admitted_files` does. Only then is any of it written
into the checkout, and each path written is printed.

`message` writes the commit message to standard output and the pull request's title,
body and whether it may merge to `$GITHUB_OUTPUT`, from the move `admit` worked out and
the recordings in the checkout alone.

Every path named on the command line must lie inside the working directory, and no file
is read or written through a link (`paths.plain_read`, `paths.plain_write`).

Exit 0 = done, 1 = an image could not be read or moved (named on standard error), 2 = usage.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tomllib

import paths
import pin_bump
import plugin_pin
import registry
from manifest_repos import IMAGE_HOME

#: lemonfiber's own images, whose pins move when their repository publishes one.
OWN_IMAGES = f"{IMAGE_HOME}/"
#: The platforms an index must publish to be taken.
REQUIRED = {("linux", "amd64"), ("linux", "arm64")}
#: A fixed build's suffix, as LinuxServer.io writes one.
BUILD = re.compile(r"-ls\d+\Z")
#: The rolling branch each image's pin moves on, after the first service running it.
BRANCH = "upstream-pin/"
SERVICE_ID = re.compile(r"\A[a-z0-9][a-z0-9-]{0,62}\Z")
#: The name a bump travels between the two jobs under, before its first service's id.
ARTIFACT = "upstream-pin-"
#: What a bump that cannot be committed as it stands raises.
Refused = plugin_pin.Refused
#: What the commit and the pull request cite.
CITED = "Spec: REPO-R98, E1-R1, E1-R10, ARCH-R121"


def upstream(image: str) -> bool:
    """Whether an image is an upstream's rather than one lemonfiber builds."""
    return not image.startswith(OWN_IMAGES)


def version_of(tag: str) -> tuple[str, tuple[int, ...], str] | None:
    """A tag's prefix, numbers and suffix, or None for a tag with no number in it.

    The prefix is everything before the first digit; the numbers are the run of digits
    and single dots after it; the suffix is whatever follows the last number. Read by
    hand rather than by a pattern, so a long tag costs one pass.
    """
    start = next((at for at, char in enumerate(tag) if char.isdigit()), None)
    if start is None:
        return None
    numbers, current, at = [], "", start
    while at < len(tag):
        char = tag[at]
        if char.isdigit():
            current += char
        elif char == "." and current and at + 1 < len(tag) and tag[at + 1].isdigit():
            numbers.append(int(current))
            current = ""
        else:
            break
        at += 1
    numbers.append(int(current))
    return tag[:start], tuple(numbers), tag[at:]


def ordered(tag: str) -> tuple[str, int, str, tuple[int, ...]] | None:
    """How a tag is spelled and where it sorts: its prefix, how many numbers its version
    has, its suffix with every number in it written 0, and the numbers it sorts by.

    A fixed build tag's suffix is read for its numbers too, its build's last, because
    each build has a suffix of its own; any other tag's suffix is part of its spelling.
    """
    read = version_of(tag)
    if read is None:
        return None
    prefix, numbers, suffix = read
    if not BUILD.search(suffix):
        return prefix, len(numbers), suffix, numbers
    counted = tuple(int(number) for number in re.findall(r"\d+", suffix))
    return prefix, len(numbers), re.sub(r"\d+", "0", suffix), numbers + counted


def newest_in_major(current: str, tags: list[str]) -> str:
    """The newest tag spelled like `current` and in its major; `current` if none is newer."""
    mine = ordered(current)
    if mine is None:
        return current
    spelling, best, best_key = mine[:3], current, mine[3]
    for tag in tags:
        theirs = ordered(tag)
        if theirs is None or theirs[:3] != spelling or theirs[3][0] != best_key[0]:
            continue
        if theirs[3] > best_key:
            best, best_key = tag, theirs[3]
    return best


def pins(manifest: dict) -> tuple[dict[str, dict], list[str]]:
    """Each upstream image the manifest runs, with its pin and its services, and each
    image whose services disagree on its pin, which this does not move."""
    found: dict[str, dict] = {}
    apart: list[str] = []
    for service in manifest.get("service", []):
        image = service.get("image", "")
        if not upstream(image):
            continue
        held = found.setdefault(image, {"tag": service.get("tag", ""), "digest": service.get("digest", ""),
                                        "services": []})
        held["services"].append(str(service.get("id", "")))
        if (held["tag"], held["digest"]) != (service.get("tag", ""), service.get("digest", "")) and image not in apart:
            apart.append(image)
    for image in apart:
        del found[image]
    return found, apart


def move_of(image: str, held: dict) -> tuple[dict | None, str]:
    """Where an image's pin would move, None where it stays, or why it cannot be read."""
    first = held["services"][0]
    if not SERVICE_ID.match(first):
        return None, f"{image}: {first!r} is not a service id to name a branch after"
    published, problem = registry.tags(image)
    if problem:
        return None, f"{image}: its tags could not be listed: {problem}"
    tag = newest_in_major(held["tag"], published)
    digest, platforms, problem = registry.resolve(image, tag)
    if problem:
        return None, f"{image}: {tag} could not be resolved: {problem}"
    if missing := REQUIRED - platforms:
        listed = ", ".join(f"{os_}/{arch}" for os_, arch in sorted(missing))
        return None, f"{image}: {tag} does not publish {listed}, so it is not taken (F2-R6)"
    if (tag, digest) == (held["tag"], held["digest"]):
        return None, ""
    return {
        "image": image,
        "services": held["services"],
        "branch": f"{BRANCH}{first}",
        "from": {"tag": held["tag"], "digest": held["digest"]},
        "to": {"tag": tag, "digest": digest},
    }, ""


def plan(manifest: dict, only: str = "") -> tuple[list[dict], list[str]]:
    """Every upstream pin that would move, and every image that could not be read."""
    found, apart = pins(manifest)
    problems = [f"{image}: its services are pinned apart, so it is moved by hand"
                for image in apart if not only or image == only]
    moves = []
    for image, held in found.items():
        if only and image != only:
            continue
        move, problem = move_of(image, held)
        if problem:
            problems.append(problem)
        if move:
            moves.append(move)
    return moves, problems


def artifact_of(main_text: str, image: str) -> str:
    """The name the bump of `image` travels between the two jobs under, from main's manifest."""
    found, _ = pins(tomllib.loads(main_text))
    if image not in found or not SERVICE_ID.match(found[image]["services"][0]):
        raise Refused(f"main's manifest runs {image} at no one pin under a service id")
    return f"{ARTIFACT}{found[image]['services'][0]}"


def admitted(main_text: str, image: str, bump: pathlib.Path) -> tuple[dict, dict[str, bytes]]:
    """The move and the files a staged bump may commit, or `Refused` naming why.

    Nothing in `bump` is trusted: it was written by a job that ran the plugin's image and
    built lemonfiber. So the move is not read from it. It is worked out here, from main's
    manifest and the registry alone, by the rules the plan used, and the files are then
    held to it by `pin_bump.admitted_files`.
    """
    moves, problems = plan(tomllib.loads(main_text), image)
    if not moves:
        raise Refused(f"the registry moves {image} nowhere now: {'; '.join(problems) or 'its pin is the newest'}")
    return moves[0], pin_bump.admitted_files(main_text, moves[0], bump)


def described(move: dict, left: list[str], log: str) -> tuple[str, str, bool]:
    """The pull request's title and body for a move, and whether it may merge itself."""
    names = ", ".join(move["services"])
    was, now = move["from"], move["to"]
    if was["tag"] == now["tag"]:
        title = f"chore(pins): {names} {now['tag']} rebuilt"
        said = (f"{move['image']}:{now['tag']} was published again, and its index is now {now['digest']}. "
                "The release is the same; the build is newer.")
    else:
        title = f"chore(pins): {names} {was['tag']} -> {now['tag']}"
        said = (f"{move['image']}:{now['tag']} is the newest release in the major {was['tag']} belongs to, "
                f"and its index is {now['digest']}.")
    body, clean = pin_bump.body_of(said, left, log, CITED)
    return title, body, clean


def asked_message(args: argparse.Namespace) -> int:
    return pin_bump.message(args, described)


def asked_artifact(args: argparse.Namespace) -> int:
    print(f"name={artifact_of(pin_bump.manifest_text(args.manifest)[1], args.image)}")
    return 0


def asked_admit(args: argparse.Namespace) -> int:
    root, text = pin_bump.manifest_text(args.manifest)
    move, files = admitted(text, args.image, paths.plain_directory(args.bump))
    pin_bump.admit_into(root, files, move, args.move_out)
    return 0


def asked_plan(args: argparse.Namespace) -> int:
    root, text = pin_bump.manifest_text(args.manifest)
    moves, problems = plan(tomllib.loads(text), getattr(args, "image", ""))
    for problem in problems:
        print(f"::warning::{problem}", file=sys.stderr)
    if args.asked == "plan":
        print(json.dumps({"moves": moves, "problems": problems}, indent=2))
        return 0
    if not moves:
        print("null")
        return 1 if problems else 0
    move = moves[0]
    written, _ = plugin_pin.pinned(text, move["image"], move["to"]["tag"], move["to"]["digest"])
    paths.plain_write(root, pin_bump.MANIFEST_FILE, written.encode())
    print(json.dumps(move, indent=2))
    return 0


ASKED = {"message": asked_message, "artifact": asked_artifact, "admit": asked_admit, "plan": asked_plan,
         "apply": asked_plan}
#: Each subcommand's options beyond `--manifest`, which the four that read a manifest take.
OPTIONS = {"plan": (), "apply": ("--image",), "artifact": ("--image",), "admit": ("--image", "--bump", "--move-out")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    asked = parser.add_subparsers(dest="asked", required=True)
    for name, options in OPTIONS.items():
        one = asked.add_parser(name)
        for option in ("--manifest", *options):
            one.add_argument(option, required=True)
    message = asked.add_parser("message")
    message.add_argument("--move", required=True)
    message.add_argument("--log", required=True)
    message.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    try:
        return ASKED[args.asked](args)
    except (OSError, ValueError) as why:
        print(f"::error::{why}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
