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

    python3 scripts/next_id.py DES          # the next one
    python3 scripts/next_id.py DES -n 4     # the next four
    python3 scripts/next_id.py --prefixes   # every prefix in use, and its ceiling

Exit 0 with the identifiers on stdout, 2 if the prefix is unknown.
"""

from __future__ import annotations

import argparse
import collections
import pathlib
import sys

from patterns import REQ_DEF

ROOT = pathlib.Path(__file__).resolve().parent.parent


def defined() -> dict[str, dict[int, pathlib.Path]]:
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
    args = parser.parse_args()

    families = defined()

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
