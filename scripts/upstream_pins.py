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
    upstream_pins.py stage    --manifest plugin.toml --main <main's plugin.toml> --move <move.json> --out <dir>
    upstream_pins.py admit    --manifest plugin.toml --image <i> --bump <dir> --move-out <move.json>
    upstream_pins.py message  --move move.json --log <url> [--root .]
    upstream_pins.py reader   --workflow first-party-plugin.yml      the reader's repository and revision

`stage` runs where the image ran and lemonfiber was built, and holds no secret: it copies
the manifest, `proofs.json` and every recording of the new pin into a directory that
travels to the next job as an artifact. `admit` runs in the job that holds the App's
token and trusts none of it. It works the move out again from main's manifest and the
registry, then refuses the bump unless every entry is a plain file, the manifest is
main's with exactly that move, and every other file is `proofs.json` or a recording the
manifest names taken from exactly that pin. Only then is any of it written into the
checkout, and each path written is printed.

`message` writes the commit message to standard output and the pull request's title,
body and whether it may merge to `$GITHUB_OUTPUT`, from the move `admit` worked out and
the recordings in the checkout alone. `reader` prints `repository=` and `revision=`
lines for `$GITHUB_OUTPUT`, read from the workflow that runs the reader everywhere else,
so the revision is written once.

Every path named on the command line must lie inside the working directory, and no file
is read or written through a link (`paths.plain_read`, `paths.plain_write`).

Exit 0 = done, 1 = an image could not be read or moved (named on standard error), 2 = usage.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import secrets
import sys
import tomllib

import paths
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
#: How many recordings left naming the old image a pull request lists by name.
STALE_LISTED = 20
#: What a staged bump holds, the name it travels under, and the most of each file read.
MANIFEST_FILE, PROOFS_FILE, ARTIFACT = "plugin.toml", "proofs.json", "upstream-pin-"
MOVE_LIMIT, RECORDING_LIMIT = 64 * 1024, 1024 * 1024
MANIFEST_LIMIT = plugin_pin.MANIFEST_LIMIT
#: A contract as `speaks` names one, and a conformance case's file.
CONTRACT = re.compile(r"\A[a-z0-9][a-z0-9.-]*@\d+\Z")
CASE = re.compile(r"\A[a-z0-9][a-z0-9_-]*\.json\Z")
#: What a bump that cannot be committed as it stands raises.
Refused = plugin_pin.Refused
#: What the commit and the pull request cite, and who signs the commit off.
CITED = "Spec: REPO-R98, E1-R1, E1-R10, ARCH-R121"
SIGNED = "Signed-off-by: lemonfiber release <info@nightworks.io>"
#: How the reader's repository and revision are written in the workflow that runs it.
READER = re.compile(r"(?m)^\s+READER_(REPOSITORY|REVISION):\s*(\S+)\s*$")
READER_REVISION = re.compile(r"\A[0-9a-f]{40}\Z")
READER_REPOSITORY = re.compile(r"\A[A-Za-z0-9-]+/[A-Za-z0-9._-]+\Z")


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


def recording_of(body: bytes) -> str:
    """What a recording says it was taken from, or nothing where it is not one."""
    try:
        read = json.loads(body)
    except ValueError:
        return ""
    return str(read.get("recorded_from", "")) if isinstance(read, dict) else ""


def stale(root: pathlib.Path, image: str, digest: str) -> list[str]:
    """Every plain recording under `root` taken from `image` at a digest other than `digest`.

    Read from the files rather than from what recorded them, so a recorder that left a
    recording behind, whatever it said of itself, cannot let a bump call itself clean.
    A directory whose name begins with a dot is the harness's, not the plugin's, and a
    link is never followed.
    """
    found = []
    for relative in paths.plain_files(root)[0]:
        if not relative.endswith(".json") or any(part.startswith(".") for part in relative.split("/")[:-1]):
            continue
        taken, _, at = recording_of(paths.plain_read(root, relative, RECORDING_LIMIT)).partition("@")
        if taken == image and at != digest:
            found.append(relative)
    return found


def fixtures(value: object) -> set[str]:
    """Every `fixture` a parsed manifest names, wherever it names one."""
    if isinstance(value, dict):
        named = {value["fixture"]} if isinstance(value.get("fixture"), str) else set()
        return named.union(*(fixtures(one) for one in value.values()))
    if isinstance(value, list):
        return set().union(*(fixtures(one) for one in value))
    return set()


def conformance_of(manifest: dict, image: str) -> set[str]:
    """The conformance directories of every contract an adapter fronting a service that
    runs `image` speaks, as `conformance/<capability>@<major>`."""
    services = manifest.get("service", [])
    running = {one.get("id") for one in services if one.get("image") == image}
    spoken = {str(contract) for one in services if one.get("fronts") in running for contract in one.get("speaks", [])}
    return {f"conformance/{contract}" for contract in spoken if CONTRACT.match(contract)}


def recordings_named(manifest: dict, image: str, relative: str) -> bool:
    """Whether `relative` is a recording a bump of `image` may write: a `.json` file
    outside every dot-directory, which the manifest names or a conformance case is."""
    folder, _, name = relative.rpartition("/")
    if not name.endswith(".json") or any(part.startswith(".") for part in relative.split("/")):
        return False
    return relative in fixtures(manifest) or (folder in conformance_of(manifest, image) and CASE.match(name) is not None)


def stage(root: pathlib.Path, main_text: str, move: dict, out: pathlib.Path) -> list[str]:
    """Copy what a bump changed into `out` for the job that commits it, and name each file.

    That is the manifest, `proofs.json`, and every recording the manifest names that now
    names the new pin. A recording the run wrote of anything else stays behind.
    """
    manifest = tomllib.loads(main_text)
    pinned = f"{move['image']}@{move['to']['digest']}"
    out.mkdir(exist_ok=True)
    staged = [MANIFEST_FILE]
    paths.plain_write(out, MANIFEST_FILE, paths.plain_read(root, MANIFEST_FILE, MANIFEST_LIMIT))
    for relative in paths.plain_files(root)[0]:
        if relative == PROOFS_FILE or (recordings_named(manifest, move["image"], relative)
                                       and recording_of(paths.plain_read(root, relative, RECORDING_LIMIT)) == pinned):
            paths.plain_write(out, relative, paths.plain_read(root, relative, RECORDING_LIMIT))
            staged.append(relative)
    return staged


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
    manifest and the registry alone, by the rules the plan used; then every entry must
    be a plain file, the manifest must be main's with exactly that move and nothing
    else, and every other file must be `proofs.json` or a recording the manifest names,
    taken from exactly that pin.
    """
    files, other = paths.plain_files(bump)
    if other:
        raise Refused(f"the bump holds what is not a plain file: {', '.join(other)}")
    if MANIFEST_FILE not in files:
        raise Refused(f"the bump holds no {MANIFEST_FILE}")
    manifest = tomllib.loads(main_text)
    moves, problems = plan(manifest, image)
    if not moves:
        raise Refused(f"the registry moves {image} nowhere now: {'; '.join(problems) or 'its pin is the newest'}")
    move = moves[0]
    written, _ = plugin_pin.pinned(main_text, image, move["to"]["tag"], move["to"]["digest"])
    files_out = {MANIFEST_FILE: paths.plain_read(bump, MANIFEST_FILE, MANIFEST_LIMIT)}
    if files_out[MANIFEST_FILE] != written.encode():
        raise Refused(f"{MANIFEST_FILE} is not main's with {image} moved to {move['to']['tag']} at "
                      f"{move['to']['digest']} and nothing else")
    pinned = f"{image}@{move['to']['digest']}"
    for relative in files:
        if relative == MANIFEST_FILE:
            continue
        body = paths.plain_read(bump, relative, RECORDING_LIMIT)
        if relative == PROOFS_FILE:
            if not isinstance(json.loads(body), dict):
                raise Refused(f"{PROOFS_FILE} is not a report")
        elif not recordings_named(manifest, image, relative):
            raise Refused(f"{relative} is not a recording the manifest names")
        elif recording_of(body) != pinned:
            raise Refused(f"{relative} is not a recording taken from {pinned}")
        files_out[relative] = body
    return move, files_out


def described(move: dict, left: list[str], log: str) -> tuple[str, str, bool]:
    """The pull request's title and body for a move, and whether it may merge itself.

    Decided only from what the committing job read itself: it may where no recording
    still names the image this replaces, and the required checks then judge the rest.
    One that left a recording behind did not come out clean, and stays open, disarmed,
    naming each (`OPS-R87`).
    """
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
    lines = [said, ""]
    if not left:
        lines.append("Every recording of it the manifest names is recorded again from it by `lemonfiber plugin "
                     "record`, at the lemonfiber `targets.toml` names; the plugin check judges every claim, proof "
                     "and check against them.")
    else:
        lines.append("Not every recording was taken again from it, so these still name the image this replaces "
                     f"and are refused (ARCH-R121); the record job's log says why: {log}")
        lines += [f"- `{path}`" for path in left[:STALE_LISTED]]
        if len(left) > STALE_LISTED:
            lines.append(f"- and {len(left) - STALE_LISTED} more")
        lines += ["", "It stays open and is not armed to merge until that is put right on this branch."]
    lines += ["", CITED, SIGNED]
    return title, "\n".join(lines), not left


def reader_of(workflow: str) -> dict[str, str]:
    """The reader's repository and revision, as the workflow that runs it pins them."""
    found = {key.lower(): value for key, value in READER.findall(workflow)}
    if not READER_REPOSITORY.match(found.get("repository", "")) or not READER_REVISION.match(found.get("revision", "")):
        raise ValueError("the workflow pins no reader repository and full revision")
    return found


def output(lines: dict[str, str]) -> None:
    """Values for the step's outputs, each multi-line one behind a delimiter no line holds."""
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
        for key, value in lines.items():
            delimiter = f"value_{secrets.token_hex(16)}"
            handle.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def read(raw: str, limit: int) -> bytes:
    """A file named on the command line, read as a plain file under the working directory."""
    return paths.plain_read(pathlib.Path.cwd().resolve(), paths.plain_relative(raw), limit)


def write(raw: str, body: bytes) -> None:
    """A file named on the command line, written as a plain file under the working directory."""
    paths.plain_write(pathlib.Path.cwd().resolve(), paths.plain_relative(raw), body)


def plugin_root(raw: str) -> pathlib.Path:
    """The directory a manifest named on the command line sits in, every step of it a
    real directory under the working directory."""
    folder, _, name = paths.plain_relative(raw).rpartition("/")
    if name != MANIFEST_FILE:
        raise Refused(f"{raw} is not a {MANIFEST_FILE}")
    return paths.plain_directory(folder or ".")


def asked_reader(args: argparse.Namespace) -> int:
    for key, value in reader_of(read(args.workflow, MANIFEST_LIMIT).decode("utf-8")).items():
        print(f"{key}={value}")
    return 0


def asked_message(args: argparse.Namespace) -> int:
    move = json.loads(read(args.move, MOVE_LIMIT))
    left = stale(paths.plain_directory(args.root), move["image"], move["to"]["digest"])
    title, body, clean = described(move, left, registry.printable(args.log))
    print(f"{title}\n\n{body}")
    output({"title": title, "body": body, "clean": "yes" if clean else "no"})
    return 0


def asked_stage(args: argparse.Namespace) -> int:
    move = json.loads(read(args.move, MOVE_LIMIT))
    main_text = read(args.main, MANIFEST_LIMIT).decode("utf-8")
    out = paths.plain_directory(args.out, make=True)
    print("\n".join(stage(plugin_root(args.manifest), main_text, move, out)))
    return 0


def manifest_text(args: argparse.Namespace) -> tuple[pathlib.Path, str]:
    root = plugin_root(args.manifest)
    return root, paths.plain_read(root, MANIFEST_FILE, MANIFEST_LIMIT).decode("utf-8")


def asked_artifact(args: argparse.Namespace) -> int:
    print(f"name={artifact_of(manifest_text(args)[1], args.image)}")
    return 0


def asked_admit(args: argparse.Namespace) -> int:
    root, text = manifest_text(args)
    move, files = admitted(text, args.image, paths.plain_directory(args.bump))
    for relative, body in files.items():
        paths.plain_write(root, relative, body)
        print(relative)
    write(args.move_out, json.dumps(move, indent=2).encode())
    return 0


def asked_plan(args: argparse.Namespace) -> int:
    root, text = manifest_text(args)
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
    paths.plain_write(root, MANIFEST_FILE, written.encode())
    print(json.dumps(move, indent=2))
    return 0


ASKED = {"reader": asked_reader, "message": asked_message, "stage": asked_stage, "artifact": asked_artifact,
         "admit": asked_admit, "plan": asked_plan, "apply": asked_plan}
#: Each subcommand's options beyond `--manifest`, which the five that read a manifest take.
OPTIONS = {
    "plan": (), "apply": ("--image",), "artifact": ("--image",), "admit": ("--image", "--bump", "--move-out"),
    "stage": ("--main", "--move", "--out"),
}


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
    asked.add_parser("reader").add_argument("--workflow", required=True)
    args = parser.parse_args(argv)
    try:
        return ASKED[args.asked](args)
    except (OSError, ValueError) as why:
        print(f"::error::{why}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
