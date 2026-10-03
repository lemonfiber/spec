#!/usr/bin/env python3
"""Which of the train's two steps a run is on, and what it tags — ADR-0033 §4.

A version that cuts a repository building one of the stack's own images is cut in
two runs of the same lane. The first tags those repositories and stops; the
second, once the embedded stack pins what they published, tags everything else.
The lane does not take the step as an input. It reads it from the repositories:

- a listed image repository that does not carry the tag makes this the first
  step, and the run tags each one that lacks it;
- when every one carries it, or the version cuts none, this is the second step,
  and the run tags the other streams.

So a first step that stopped part-way is finished by running it again, and a
second step can never be reached while an image is untagged.

Two lists are written. `tagging.txt` is what the run tags. `declaring.txt` is
what has to declare the version before it does: in the first step that is every
stream still to be tagged, the other streams included, because an image tag
publishes and is never moved, and a core that cannot be tagged afterwards is
better found before it.

Usage:
  train_step.py --version X.Y.Z --tag <tag>

Run from the spec checkout, with each stream cloned under `checkouts/<repo>`.
Writes `step=images|streams` to `$GITHUB_OUTPUT` where the runner names one, and
prints it either way. Exit 0 = settled, 1 = no manifest or a tag lookup that
failed, 2 = usage.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
import tomllib

import manifest_repos
from check_image_pins import cut_by_train

CHECKOUTS = pathlib.Path("checkouts")
TAGGING = pathlib.Path("tagging.txt")
DECLARING = pathlib.Path("declaring.txt")

#: The first step: the image repositories are tagged, and nothing else.
IMAGES = "images"
#: The second step, and the only one for a version that cuts no image.
STREAMS = "streams"

#: What `git ls-remote --exit-code` answers when the remote holds no such ref.
NO_SUCH_REF = 2

#: A repository name and a tag, as they may reach the git command line: letters
#: or digits first, so neither can arrive as a flag or climb out of `checkouts/`.
#: Kept beside the call they guard, where an analysis of that call can see them.
_REPO = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,99}\Z")
_TAG = re.compile(r"\Av[A-Za-z0-9][A-Za-z0-9.-]{0,99}\Z")


def carries(repo: str, tag: str) -> bool:
    """Whether the repository's remote holds the tag. A lookup that fails refuses."""
    if not (_REPO.match(repo) and _TAG.match(tag)):
        sys.exit(f"::error::{repo!r} at {tag!r} is not a lookup this hands to git")
    result = subprocess.run(
        ["git", "-C", str(CHECKOUTS / repo), "ls-remote", "--exit-code", "--tags",
         "origin", f"refs/tags/{tag}"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == NO_SUCH_REF:
        return False
    sys.exit(f"::error::could not ask {repo} whether it carries {tag}: {result.stderr.strip()}")


def settle(images: list[str], others: list[str], tag: str) -> tuple[str, list[str], list[str]]:
    """The step, what it tags, and what has to declare the version first."""
    untagged = [repo for repo in images if not carries(repo, tag)]
    if untagged:
        return IMAGES, untagged, untagged + others
    return STREAMS, others, others


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()

    if not cut_by_train(a.tag, a.version):
        sys.exit(f"::error::{a.tag!r} is not a tag the train cuts for {a.version!r}")
    path = manifest_repos.manifest_for(a.version)
    if not path.is_file():
        print(f"::error::no manifest at {path}", file=sys.stderr)
        return 1
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    registry = tomllib.loads(manifest_repos.REGISTRY.read_text(encoding="utf-8"))
    images = [repo for repo, _, _ in manifest_repos.images(data, registry)]
    step, tagging, declaring = settle(images, manifest_repos.others(data, registry), a.tag)

    TAGGING.write_text("".join(f"{repo}\n" for repo in tagging), encoding="utf-8")
    DECLARING.write_text("".join(f"{repo}\n" for repo in declaring), encoding="utf-8")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as out:
            out.write(f"step={step}\n")
    print(f"step={step}: tags {', '.join(tagging) or 'nothing'} at {a.tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
