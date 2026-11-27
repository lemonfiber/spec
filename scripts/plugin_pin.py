#!/usr/bin/env python3
"""Set the pin of every service in a `plugin.toml` that runs one image — OPS-R85.

Every bump that moves an image pin in a plugin's manifest writes it here:
`manifest_pin.py` moving lemonfiber's own image to what its repository published
(`OPS-R90`, `OPS-R91`), and `upstream_pins.py` moving an upstream's image to the newest
release of its major (`REPO-R98`).

The manifest is edited as text rather than re-serialised, so every comment and every
other line stays byte for byte what it was. In each `[[service]]` block that runs the
image, its one `digest` line and its one `tag` line take the new values, aligned as they
were. The result is read back and refused unless it is the manifest it was with exactly
those services moved, and nothing else.

A release the image runs can move with its pin (`REPO-R98`, `OPS-R91`). `release_targets`
names each expectation of a proof asking a service that runs it which names the old
release written whole: its `stdout_starts_with`, its `body_starts_with` and each string
value of its `json`, each to read with every such naming replaced. `moved_text` writes
them: each place the old release is written whole is tried on its own, and belongs to
the one value its replacement changes with nothing else of the manifest changing. A
value is moved only where its places together make it read exactly as asked; one
reached only through an escape, or whose places change it otherwise, is left as written
and named, and the pull request is not armed to merge.
"""

from __future__ import annotations

import copy
import re
import tomllib

from patterns import DIGEST, IMAGE_TAG

#: The two fields a pin is, in the order they are written.
FIELDS = ("digest", "tag")
#: The most of a manifest that is read.
MANIFEST_LIMIT = 256 * 1024
#: Where a proof's expectation writes what the program or service it asks says first,
#: and where it holds the JSON members the answer must carry.
RELEASE_TEXT, RELEASE_JSON = ("stdout_starts_with", "body_starts_with"), "json"
#: A place in a parsed manifest: the keys and list indices that reach a value.
Path = tuple[str | int, ...]


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
        at
        for at, block in enumerate(blocks)
        if block.startswith("[[service]]") and re.search(rf'(?m)^image\s*=\s*"{re.escape(image)}"\s*$', block)
    ]
    if len(written_so) != len(declared):
        raise Refused(
            f"{len(declared)} services run {image} and {len(written_so)} are written so this can move them"
        )
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


def written_as_release(release: str) -> re.Pattern[str]:
    """Where `release` is written whole: neither a digit nor a digit and a dot before it,
    nor a digit or a dot and a digit after it, so `1.2` is not read inside `11.2.0`."""
    return re.compile(rf"(?<!\d)(?<!\d\.){re.escape(release)}(?!\.?\d)")


def expectation_texts(proof: dict) -> list[tuple[Path, str]]:
    """Each string a proof's expectation may name a release in, by its place in the
    proof: `RELEASE_TEXT`'s keys and each string value of its `json`."""
    expect = proof.get("expect")
    if not isinstance(expect, dict):
        return []
    found: list[tuple[Path, str]] = [
        (("expect", key), expect[key]) for key in RELEASE_TEXT if isinstance(expect.get(key), str)
    ]
    members = expect.get(RELEASE_JSON)
    if isinstance(members, dict):
        found += [
            (("expect", RELEASE_JSON, member), value)
            for member, value in members.items()
            if isinstance(value, str)
        ]
    return found


def release_targets(manifest: dict, services: list[str], was: str, now: str) -> dict[Path, str]:
    """Each expectation of a proof asking one of `services` that names the release `was`
    written whole, by its place, with what it reads with every such naming `now`."""
    if not was or not now or was == now:
        return {}
    declared = manifest.get("service", [])
    only = declared[0].get("id") if len(declared) == 1 else None
    release = written_as_release(was)
    return {
        ("proof", at, *place): release.sub(lambda _: now, value)
        for at, proof in enumerate(manifest.get("proof", []))
        if proof.get("service", only) in services
        for place, value in expectation_texts(proof)
        if release.search(value)
    }


def value_at(manifest: object, path: Path) -> object:
    """What `path` reaches in a parsed manifest, or None where it reaches nothing."""
    for step in path:
        try:
            manifest = manifest[step]
        except (KeyError, IndexError, TypeError):
            return None
    return manifest


def with_values(manifest: dict, values: dict[Path, str]) -> dict:
    """A parsed manifest with each place in `values` holding what it says."""
    moved = copy.deepcopy(manifest)
    for path, value in values.items():
        holder = value_at(moved, path[:-1])
        holder[path[-1]] = value
    return moved


def spliced(text: str, places: list[re.Match[str]], now: str) -> str:
    """`text` with `now` written at each of `places`."""
    for place in sorted(places, key=lambda one: one.start(), reverse=True):
        text = f"{text[: place.start()]}{now}{text[place.end() :]}"
    return text


def moved_text(text: str, targets: dict[Path, str], was: str, now: str) -> tuple[str, list[Path], list[Path]]:
    """`text` with `was` replaced by `now` where it is written whole inside a value
    `targets` names, each value then reading as `targets` says and no other byte changed;
    and the places moved and those left as written."""
    before = tomllib.loads(text)
    places: dict[Path, list[re.Match[str]]] = {path: [] for path in targets}
    for place in written_as_release(was).finditer(text):
        try:
            read = tomllib.loads(spliced(text, [place], now))
        except tomllib.TOMLDecodeError:
            continue
        for path in targets:
            value = value_at(read, path)
            if value != value_at(before, path) and read == with_values(before, {path: value}):
                places[path].append(place)
                break
    taken = [
        path
        for path, found in places.items()
        if found and tomllib.loads(spliced(text, found, now)) == with_values(before, {path: targets[path]})
    ]
    written = spliced(text, [place for path in taken for place in places[path]], now)
    return written, taken, [path for path in targets if path not in taken]


def named(text: str, places: list[Path]) -> list[str]:
    """What each of `places` lies in, each once, services before proofs and each in the
    manifest's order: a proof by its id, a service's `built_on` as `<service id>.built_on`."""
    manifest = tomllib.loads(text)
    found = []
    for path in sorted(places, key=lambda one: (one[0] != "service", one[1])):
        held = manifest[path[0]][path[1]]
        found.append(str(held.get("id")) if path[0] == "proof" else f"{held.get('id')}.built_on")
    return list(dict.fromkeys(found))
