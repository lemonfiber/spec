#!/usr/bin/env python3
"""Files every repo carries a copy of are checked against their one home.

Two lint configs and a handful of brand assets exist in more than one repository
because the tools and GitHub both read them from the tree they are given. This
checks each copy against the canonical one in ``shared/`` (GOV-R12, Q-R56).

Usage, from the root of the repository being checked::

    check_shared_files.py --canonical <path to a spec checkout> --repo owner/name

Exit 0 = every copy agrees with its home, 1 = at least one does not.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import tomllib

# The members of `shared/` this file names. Named here rather than at each use so
# the accounting below and the checks above cannot come to mean different files.
MARKDOWNLINT = "markdownlint.jsonc"
TYPOS = "typos.toml"
HOOKS = "hooks"


def markdownlint(repo: pathlib.Path, canonical: pathlib.Path) -> list[str]:
    """The markdownlint config is copied verbatim, key order included."""
    want = canonical / "shared" / MARKDOWNLINT
    got = repo / ".markdownlint.jsonc"
    if not got.is_file():
        return [f"{got.name} is missing; copy {want} to the repo root"]
    if got.read_bytes() != want.read_bytes():
        return [f"{got.name} differs from the canonical copy; replace it with {want}"]
    return []


def typos(repo: pathlib.Path, canonical: pathlib.Path) -> list[str]:
    """The typos config is a floor: a repo may add entries, never contradict one."""
    want_path = canonical / "shared" / TYPOS
    got_path = repo / TYPOS
    if not got_path.is_file():
        return [f"typos.toml is missing; copy {want_path} to the repo root"]
    want = tomllib.loads(want_path.read_text(encoding="utf-8"))
    got = tomllib.loads(got_path.read_text(encoding="utf-8"))
    problems = []

    want_words = want.get("default", {}).get("extend-words", {})
    got_words = got.get("default", {}).get("extend-words", {})
    for word, value in want_words.items():
        if word not in got_words:
            problems.append(f"typos.toml is missing the shared word {word!r}")
        elif got_words[word] != value:
            problems.append(
                f"typos.toml maps {word!r} to {got_words[word]!r}, shared is {value!r}"
            )

    want_res = want.get("default", {}).get("extend-ignore-re", [])
    got_res = got.get("default", {}).get("extend-ignore-re", [])
    for pattern in want_res:
        if pattern not in got_res:
            problems.append(f"typos.toml is missing the shared pattern {pattern!r}")
    return problems


def asset_rows(canonical: pathlib.Path):
    """Yield (digest, path, home_repo, home_path) for each row of the manifest."""
    manifest = canonical / "shared" / "assets.sha256"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, path, home = line.split()
        home_repo, home_path = home.split(":", 1)
        yield digest, path, home_repo, home_path


def assets(repo: pathlib.Path, canonical: pathlib.Path, name: str) -> list[str]:
    """Every copy present in this repo matches the file it was taken from."""
    problems = []
    for digest, path, home_repo, home_path in asset_rows(canonical):
        if home_repo == name:
            continue
        target = repo / path
        if not target.is_file():
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != digest:
            problems.append(
                f"{path} differs from {home_repo}/{home_path}; "
                f"copy it again rather than editing it here"
            )
    return problems


def hooks(repo: pathlib.Path, canonical: pathlib.Path) -> list[str]:
    """The pre-push hook, where a repo has adopted it.

    Conditional rather than required: a repo that has not enabled hooks yet is
    not failed for it, but one carrying a copy must carry the current one — a
    guard that has quietly drifted is worse than none, because it is trusted.

    Compared byte for byte, as the other copies here are. Reading both as text
    folds CRLF endings to LF, so a hook rewritten with CRLF reads as identical
    to the canonical one — and that hook is one the kernel will not run, because
    the interpreter its first line names has a carriage return on the end.
    """
    complaints = []
    # Read from the canonical directory rather than named here. This listed two
    # hooks, which is what `shared/hooks/` held when it was written; a third
    # would have been copied into every repository and compared in none, and the
    # run would have said the copies match.
    for name in sorted(
        one.name
        for one in (canonical / "shared" / HOOKS).iterdir()
        if one.is_file()
    ):
        got = repo / ".githooks" / name
        if not got.is_file():
            continue
        want = canonical / "shared" / HOOKS / name
        if got.read_bytes() != want.read_bytes():
            complaints.append(f".githooks/{name} differs from the canonical copy; replace it with {want}")
    return complaints


# Every member of `shared/` that a check above compares, and the ones nothing
# compares because they are not copies. `README.md` documents the directory and
# `assets.sha256` is the manifest `assets()` reads rather than a file any repo
# carries.
COMPARED = {MARKDOWNLINT, TYPOS, HOOKS}
NOT_A_COPY = {"README.md", "assets.sha256"}


def unaccounted(canonical: pathlib.Path) -> list[str]:
    """What sits in `shared/` that no check here looks at.

    The checks are named one by one below, which is what this directory held when
    they were written. A file added since is copied into every repository by
    whoever adds it and compared in none — and the run still says the copies
    match, which is true of the ones it looked at and reads as an account of all
    of them.
    """
    held = {one.name for one in (canonical / "shared").iterdir()}
    missed = sorted(held - COMPARED - NOT_A_COPY)
    if not missed:
        return []
    return [
        f"shared/{name} is compared by nothing here, so a repository's copy of it "
        f"may differ and this check will still pass"
        for name in missed
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical", default=".", help="path to a lemonfiber/spec checkout")
    ap.add_argument("--repo", default="", help="owner/name of the repo being checked")
    ap.add_argument("--root", default=".", help="root of the repo being checked")
    args = ap.parse_args()

    repo = pathlib.Path(args.root).resolve()
    canonical = pathlib.Path(args.canonical).resolve()
    name = args.repo.split("/")[-1]

    if not (canonical / "shared").is_dir():
        print(f"::error::no shared/ directory under {canonical}")
        return 1

    problems = unaccounted(canonical) + (
        markdownlint(repo, canonical)
        + typos(repo, canonical)
        + assets(repo, canonical, name)
        + hooks(repo, canonical)
    )
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        print(f"\n{len(problems)} shared file(s) out of step with {canonical / 'shared'}.")
        return 1
    print("shared files: lint configs and brand assets match their canonical copies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
