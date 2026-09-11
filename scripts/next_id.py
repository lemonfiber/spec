#!/usr/bin/env python3
"""The next free requirement identifier for a prefix, and where its family lives.

Allocating one by grepping a file for its highest number is not merely tedious,
it is wrong. A prefix is not confined to a file: `DES` is defined across four,
with `accessibility.md` holding R15–R20 while `brand-rules.md` runs to R21, and
`Q-R65` is defined in `90-appendix/faq.md` rather than beside the rest of `Q`.
A grep of the file you happen to be editing returns a number somebody else has
already used, which is how `DES-R15`..`R18` came to be allocated twice.

It is also max+1 and never count+1. Identifiers are permanent (`GOV-R8`), so a
withdrawn requirement leaves a hole: `GOV` has a permanent gap at R36–R39, and
counting would hand back an identifier that once meant something else.

It reads the branches too, not only the working tree. An identifier allocated
on a pull request that has not merged is taken, and a tree that cannot see it
hands it out again — which is the same double allocation one level up, and it
nearly happened: `F9` was allocated on an unmerged branch while this script,
reading `main`, still reported the ceiling as `F8`.

    python3 scripts/next_id.py DES          # the next one
    python3 scripts/next_id.py DES -n 4     # the next four
    python3 scripts/next_id.py --prefixes   # every prefix in use, and its ceiling
    python3 scripts/next_id.py DES --here   # this tree only, and say so

Exit 0 with the identifiers on stdout, 2 if the prefix is unknown.
"""

from __future__ import annotations

import argparse
import collections
import pathlib
import subprocess
import sys

from patterns import REQ_DEF

ROOT = pathlib.Path(__file__).resolve().parent.parent


def branches() -> list[str]:
    """Every ref that might hold an identifier this tree does not.

    Remote branches rather than local ones: a pull request's work is on the
    remote whether or not this clone has a local branch for it.
    """
    done = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/remotes"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    if done.returncode != 0:
        return []
    return [
        ref for ref in done.stdout.split()
        # `refs/remotes/origin/HEAD` is a symbolic ref to another entry in this
        # same list, so reading it would be reading one branch twice.
        if not ref.endswith("/HEAD")
    ]


def defined_on(ref: str) -> set[str]:
    """The identifiers a ref defines, asked of git rather than of the disk."""
    done = subprocess.run(
        # POSIX ERE, which is what git grep speaks: no `\s`. The rows are then
        # matched again with REQ_DEF below, so this only has to be no narrower
        # than that pattern.
        ["git", "grep", "-h", "-E",
         r"^\|[[:space:]]*\*\*[A-Z]+[0-9]*-R[0-9]+\*\*[[:space:]]*\|",
         ref, "--", "*.md"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    # Exit 1 is "no match", which is an answer. Anything else is a ref this
    # clone cannot read, and guessing about it would defeat the point.
    if done.returncode not in (0, 1):
        return set()
    return set(REQ_DEF.findall(done.stdout))


def defined(here: bool = False) -> dict[str, dict[int, pathlib.Path]]:
    """Every requirement this repository defines, by prefix and number.

    Read from definitions rather than citations. A citation of an identifier that
    was never defined is a fault the integrity check reports; treating one as
    occupying a number would let a typo reserve it forever.
    """
    found: dict[str, dict[int, pathlib.Path]] = collections.defaultdict(dict)
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts or "vendor" in path.parts:
            continue
        for identifier in REQ_DEF.findall(path.read_text(encoding="utf-8")):
            prefix, number = identifier.rsplit("-R", 1)
            found[prefix][int(number)] = path.relative_to(ROOT)

    if not here:
        for ref in branches():
            short = ref.removeprefix("refs/remotes/")
            for identifier in defined_on(ref):
                prefix, number = identifier.rsplit("-R", 1)
                # A number this tree already has keeps the path it has here; the
                # branch is only ever news about one the tree does not know.
                found[prefix].setdefault(int(number), pathlib.Path(f"({short})"))
    return found


def report_prefixes(families: dict[str, dict[int, pathlib.Path]]) -> int:
    for prefix in sorted(families, key=lambda p: (len(p), p)):
        numbers = families[prefix]
        files = sorted({str(path) for path in numbers.values()})
        gaps = sorted(set(range(1, max(numbers) + 1)) - set(numbers))
        print(
            f"{prefix:<8} highest R{max(numbers):<5} "
            f"{len(numbers):>4} defined  "
            f"{len(files)} file(s)"
            + (f"  gaps: {', '.join(f'R{g}' for g in gaps)}" if gaps else "")
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prefix", nargs="?", help="the family, e.g. DES or N1")
    parser.add_argument("-n", "--count", type=int, default=1)
    parser.add_argument("--prefixes", action="store_true", help="list every prefix in use")
    parser.add_argument(
        "--here", action="store_true",
        help="read this tree only, ignoring what other branches have taken",
    )
    args = parser.parse_args()

    families = defined(here=args.here)
    seen = 0 if args.here else len(branches())
    if args.here:
        print(
            "# reading this tree only: an identifier taken on an unmerged "
            "branch will be handed out again.", file=sys.stderr,
        )
    elif not seen:
        print(
            "# no branches could be read, so only this tree was searched. An "
            "identifier taken on an unmerged branch will be handed out again.",
            file=sys.stderr,
        )
    else:
        print(f"# {seen} branch(es) read as well as this tree.", file=sys.stderr)

    if args.prefixes:
        return report_prefixes(families)

    if not args.prefix:
        parser.error("name a prefix, or pass --prefixes")

    prefix = args.prefix.upper().removesuffix("-R")
    if prefix not in families:
        near = sorted(p for p in families if p.startswith(prefix[:1]))
        print(f"::error::no requirement is defined under {prefix}.", file=sys.stderr)
        if near:
            print(f"Prefixes starting {prefix[:1]}: {', '.join(near)}", file=sys.stderr)
        return 2

    numbers = families[prefix]
    ceiling = max(numbers)

    # Where the family already lives, so a new one is added beside its relatives
    # rather than wherever the author happened to be.
    where = collections.Counter(str(path) for path in numbers.values())
    print(f"# {prefix} is defined in:", file=sys.stderr)
    for path, count in where.most_common():
        span = sorted(n for n, p in numbers.items() if str(p) == path)
        print(f"#   {path}  ({count}: R{span[0]}..R{span[-1]})", file=sys.stderr)
    print(f"# highest is R{ceiling}", file=sys.stderr)

    for offset in range(args.count):
        print(f"{prefix}-R{ceiling + 1 + offset}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
