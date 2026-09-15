#!/usr/bin/env python3
"""Compute a version manifest's transition — OPS-R32, OPS-R35, OPS-R57.

Reads the manifest for a version, rewrites its `status` line, and at release
stamps `released_on` and appends the embedded `[pins]`, then writes the result to
**stdout** — the caller redirects it back to the file. Emitting rather than
writing in place keeps the edit a line rewrite (comments and layout survive) and
keeps any filesystem write out of this script. The manifest path is built from a
validated version and a constant directory, so no free-form input is
dereferenced.

A version's goals do not always ship under that version's own tag. A minor whose
release run fails part-way is finished by a patch, and the patch is the artefact
people actually get — so `--released-as` records which tag carried the goals this
manifest locked. There is no manifest per patch: a patch delivers no goals of its
own, and one would be a version the train has to walk past.

A withdrawal is the one transition that destroys information if it is recorded
bare. A release is yanked because something was wrong with it, and the manifest
is where anyone later asks what — so `--withdrawn-because` is required to reach
`yanked` and refused everywhere else. The release itself is never removed from
the record; only marked.

A pre-release is the one thing recorded here that is not a transition. `OPS-R60`
says a pre-release does not move the version's status, so `--prerelease` writes a
`[[prerelease]]` table and leaves everything else where it was — including the
status, which is passed as whatever the manifest already holds. What the record
keeps is what nothing can answer afterwards: the goals the gate called unmet at
that moment. The verdict moves as work lands, and which goals a particular
artefact went out without is a fact about that artefact rather than about now.

Usage:
  set_status.py --version X.Y.Z --status <state> [--released-on YYYY-MM-DD]
                [--released-as X.Y.Z] [--withdrawn-because WHY]
                [--prerelease TAG --prerelease-on YYYY-MM-DD [--unmet ID ...]]
                [--pin name=sha ...] > <manifest>
Exit 0 = emitted, 1 = the manifest is missing or misshapen, 2 = usage.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

from patterns import PRERELEASE_ID, STATES
from patterns import VERSION as VERSION_RE

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PRERELEASE_TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)-(.+)$")
IN_FLIGHT_FOR_PRERELEASE = ("staged", "in_progress", "releasable")
VERSIONS_DIR = pathlib.Path("70-operations/versions")


def manifest_for(version: str) -> pathlib.Path:
    """The manifest path for a validated version, built from a constant base."""
    if not VERSION_RE.match(version):
        sys.exit(f"::error::version must be X.Y.Z, got {version!r}")
    path = (VERSIONS_DIR / f"{version}.toml").resolve()
    if not path.is_relative_to(VERSIONS_DIR.resolve()):
        sys.exit(f"::error::path escapes {VERSIONS_DIR}")  # pragma: no cover
    return path


def parse_pins(specs: list[str]) -> list[str]:
    pairs: list[str] = []
    for spec in specs:
        if "=" not in spec:
            sys.exit(f"::error::--pin wants name=sha, got {spec!r}")
        name, _, sha = spec.partition("=")
        pairs.append(f'{name} = "{sha}"')
    return pairs


def stamped(text: str, key: str, value: str, beneath: str) -> str:
    """Write `key = "value"` under an existing line, replacing one already there.

    Placed beneath a named line rather than appended, so it stays above the
    `[pins]` table a release also writes — a scalar under a table header belongs
    to the table, and readers that parse by line would file it as a pin.

    One function for both scalars a release stamps, because the placement rule is
    the thing that is easy to get wrong and there is no reason for two copies of
    it to be able to disagree.
    """
    line = f'{key} = "{value}"'
    text, n = re.subn(rf"(?m)^{key}\s*=.*$", line, text)
    if n:
        return text
    return re.sub(rf"(?m)^({beneath}\s*=.*)$", lambda m: f"{m.group(1)}\n{line}",
                  text, count=1)


def with_released_on(text: str, date: str) -> str:
    """Stamp the release date under `status`, replacing one already there."""
    if not DATE_RE.match(date):
        sys.exit(f"::error::--released-on wants YYYY-MM-DD, got {date!r}")
    return stamped(text, "released_on", date, "status")


def with_released_as(text: str, tag: str) -> str:
    """Stamp the tag the goals actually went out under, beneath the date.

    Beneath the date where there is one, so the three lines read in the order the
    events happened: what state this is in, when it went out, and what it went out
    as. A manifest carrying no date is one being corrected by hand, and the tag
    still belongs under `status` rather than at the end of the goals.
    """
    if not VERSION_RE.match(tag):
        sys.exit(f"::error::--released-as wants X.Y.Z, got {tag!r}")
    dated = re.search(r"(?m)^released_on\s*=", text)
    return stamped(text, "released_as", tag, "released_on" if dated else "status")


def with_withdrawn_because(text: str, why: str) -> str:
    """Stamp why a release was withdrawn, beneath whatever records that it went out.

    Under `released_as` where there is one, otherwise the date, otherwise the
    status — the same descending order the other stamps use, so the lines read in
    the order the events happened and a withdrawal is last because it is.
    """
    if not why.strip():
        sys.exit("::error::--withdrawn-because wants a reason")
    if '"' in why:
        sys.exit("::error::--withdrawn-because cannot contain a quote")
    for anchor in ("released_as", "released_on"):
        if re.search(rf"(?m)^{anchor}\s*=", text):
            return stamped(text, "withdrawn_because", why, anchor)
    return stamped(text, "withdrawn_because", why, "status")


def prerelease_tag(tag: str, version: str) -> str:
    """Refuse a tag that is not this version carrying a pre-release identifier.

    Three faults look alike from a workflow and are different to a reader, so each
    is named: a tag for another version, the version's own release tag, and an
    identifier ARCH-R43 has already given a meaning to.
    """
    found = PRERELEASE_TAG_RE.match(tag)
    if not found:
        sys.exit(f"::error::--prerelease wants vX.Y.Z-<id>, got {tag!r}")
    named, identifier = found.groups()
    if named != version:
        sys.exit(f"::error::--prerelease {tag} names {named}, not {version}")
    if not PRERELEASE_ID.match(identifier):
        sys.exit(
            f"::error::{identifier!r} is not a usable pre-release identifier; "
            "`rc` is reserved by ARCH-R43 for the point schema_version starts binding"
        )
    return tag


def with_prerelease(text: str, tag: str, when: str, unmet: list[str], pairs: list[str]) -> str:
    """Append one `[[prerelease]]` table to the end of the manifest.

    Appended rather than placed, and it stays above `[pins]` without being put
    there: a pre-release belongs to a version in flight and `[pins]` is written at
    release, so a manifest carrying one cannot yet carry the other. That ordering
    is what keeps the record: `with_pins` rewrites everything from `[pins]` to the
    end of the file, so a record below it would be swallowed by the release — and
    the answer to what went out *before* a version would disappear at exactly the
    moment somebody asks.
    """
    if not DATE_RE.match(when):
        sys.exit(f"::error::--prerelease-on wants YYYY-MM-DD, got {when!r}")
    goals = ", ".join(f'"{goal}"' for goal in unmet)
    inline = ", ".join(pairs)
    block = [
        "[[prerelease]]",
        f'tag = "{tag}"',
        f'cut_on = "{when}"',
        f"unmet = [{goals}]",
        f"pins = {{ {inline} }}" if inline else "pins = {}",
    ]
    return text.rstrip() + "\n\n" + "\n".join(block) + "\n"


def with_pins(text: str, pairs: list[str]) -> str:
    """Replace the trailing [pins] table (or append one)."""
    kept: list[str] = []
    for line in text.splitlines():
        if line.strip() == "[pins]":
            break
        kept.append(line)
    block = "[pins]\n" + "\n".join(pairs) + "\n"
    return "\n".join(kept).rstrip() + "\n\n" + block


def refuse_inconsistent(a: argparse.Namespace) -> None:
    """Reject a combination of flags that cannot describe one transition.

    Apart from `main` because each of these is a sentence about which status a
    stamp belongs to, and reading five of them in a row is the whole of the rule —
    interleaved with the rewriting they were a list nobody finished reading.
    """
    # A yank with no reason is the record losing the only thing anyone will come
    # back to it for, and a reason on anything else is a withdrawal nobody made.
    if a.status == "yanked" and not a.withdrawn_because:
        sys.exit("::error::--withdrawn-because is required to withdraw a release")
    if a.withdrawn_because and a.status != "yanked":
        sys.exit(
            f"::error::--withdrawn-because belongs to a withdrawn manifest, not {a.status!r}"
        )
    if a.released_on and a.status != "released":
        sys.exit(f"::error::--released-on belongs to a released manifest, not {a.status!r}")
    if a.released_as and a.status != "released":
        sys.exit(f"::error::--released-as belongs to a released manifest, not {a.status!r}")
    # A manifest whose goals went out under its own tag says so by being that
    # version. Stamping the name twice would read as though something had been
    # decided, and the caller that passed it computed the wrong tag.
    if a.released_as == a.version:
        sys.exit(f"::error::--released-as {a.version} is this manifest's own version")
    refuse_half_a_prerelease(a)


def refuse_half_a_prerelease(a: argparse.Namespace) -> None:
    """Reject a pre-release record that is not one, kept apart from the stamps above.

    Its own function because it asks a different question. The stamps are about which
    status a mark belongs to; this is about a record that is written in three parts
    and means nothing with any of them missing.
    """
    # A pre-release is not a transition, so the only statuses it can be recorded
    # against are the ones a version is in while it is still being worked on. A
    # record on a released manifest would be a pre-release of something already out;
    # on a planned one, of a version nobody has committed to yet.
    if a.prerelease and a.status not in IN_FLIGHT_FOR_PRERELEASE:
        sys.exit(
            f"::error::a pre-release belongs to a version in flight, not {a.status!r} "
            f"({'/'.join(IN_FLIGHT_FOR_PRERELEASE)})"
        )
    if a.prerelease and not a.prerelease_on:
        sys.exit("::error::--prerelease-on is required to record a pre-release")
    if a.prerelease_on and not a.prerelease:
        sys.exit("::error::--prerelease-on belongs to a pre-release record")
    if a.unmet and not a.prerelease:
        sys.exit("::error::--unmet belongs to a pre-release record")


def stamps(text: str, a: argparse.Namespace) -> str:
    """Apply every stamp the transition asked for, in the order they are written."""
    if a.released_on:
        text = with_released_on(text, a.released_on)
    if a.released_as:
        text = with_released_as(text, a.released_as)
    if a.withdrawn_because:
        text = with_withdrawn_because(text, a.withdrawn_because)
    # Before `with_pins`, which rewrites everything from `[pins]` to the end: a
    # record written after it would be inside the table it appends.
    if a.prerelease:
        text = with_prerelease(
            text,
            prerelease_tag(a.prerelease, a.version),
            a.prerelease_on,
            a.unmet,
            parse_pins(a.pin),
        )
    elif a.pin:
        text = with_pins(text, parse_pins(a.pin))
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--status", required=True, choices=sorted(STATES))
    ap.add_argument("--released-on", metavar="YYYY-MM-DD")
    ap.add_argument("--released-as", metavar="X.Y.Z")
    ap.add_argument("--withdrawn-because", metavar="WHY")
    ap.add_argument("--prerelease", metavar="vX.Y.Z-ID")
    ap.add_argument("--prerelease-on", metavar="YYYY-MM-DD")
    ap.add_argument("--unmet", action="append", default=[], metavar="ID")
    ap.add_argument("--pin", action="append", default=[], metavar="name=sha")
    a = ap.parse_args()

    refuse_inconsistent(a)

    path = manifest_for(a.version)
    if not path.is_file():
        print(f"::error::no manifest at {path}", file=sys.stderr)
        return 1
    text, n = re.subn(r"(?m)^status\s*=.*$", f'status  = "{a.status}"',
                      path.read_text(encoding="utf-8"))
    if n != 1:
        print(f"::error::expected exactly one status line in {path}, found {n}", file=sys.stderr)
        return 1
    text = stamps(text, a)

    sys.stdout.write(text)
    print(f"{path.name}: status={a.status}"
          + (f", released_on={a.released_on}" if a.released_on else "")
          + (f", released_as={a.released_as}" if a.released_as else "")
          + (", withdrawn" if a.withdrawn_because else "")
          + (f", prerelease={a.prerelease} unmet={len(a.unmet)}" if a.prerelease else "")
          + (f", pins={len(a.pin)}" if a.pin else ""),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
