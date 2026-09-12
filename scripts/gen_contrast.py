#!/usr/bin/env python3
"""The measured contrast table in 60-brand/accessibility.md, from the tokens.

The page opens by saying that whether the palette meets WCAG AA is a computed
property of the tokens rather than an opinion, and then stated fifteen numbers
that nothing computed. Three of them had gone wrong: `fiber-deep` was darkened
from `#A85A12` to `#9C5411`, `text-muted` from `#6E6A57` to `#565344` and
`text-faint` from `#8B8770` to `#6A6756`, and the page went on quoting the old
hexes and the ratios that went with them. Two requirements rested on figures
that had stopped being true — one of them on a failure that had become a pass.

So the table is written here instead. What stays hand-written is the prose
around it, which is where a judgement about *use* belongs; what a pair measures
is arithmetic and is not anybody's to type.

The formula is WCAG 2.1's, and `brand:scripts/check_tokens.py` implements it
too. That is a published constant rather than a fact about this project: two
copies of it cannot drift apart meaningfully, because if they ever disagreed
one of them would simply be wrong about the standard.

Reads `60-brand/tokens.json`, which is a byte-identical copy of
`brand:tokens/tokens.json` held there by `shared/assets.sha256`.

Run:  python3 scripts/gen_contrast.py
"""

from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKENS = ROOT / "60-brand" / "tokens.json"
PAGE = ROOT / "60-brand" / "accessibility.md"

# Matched by its header row, the way the other generators here find their
# tables. A marker comment would be a second thing to keep in step, and the
# header is already unique on the page.
TABLE = re.compile(r"^\| Token \| Hex \|.*(?:\n\|.*)*", re.MULTILINE)

# The three grounds anything is ever set on. `pith` is a shade of paper and
# `line` is a rule rather than a surface, so neither is one.
SURFACES = ("paper", "canvas", "ink")

# WCAG 2.1: 7 for AAA body, 4.5 for AA body, 3 for AA at large sizes.
AAA = 7.0
AA = 4.5
AA_LARGE = 3.0


def channel(value: int) -> float:
    """One sRGB channel, linearised."""
    part = value / 255
    return part / 12.92 if part <= 0.03928 else ((part + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    bare = hex_colour.lstrip("#")
    red, green, blue = (int(bare[at:at + 2], 16) for at in (0, 2, 4))
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


def ratio(one: str, other: str) -> float:
    first, second = luminance(one), luminance(other)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def verdict(measured: float) -> str:
    """What a ratio clears, in the words WCAG uses for it."""
    if measured >= AAA:
        return "AAA"
    if measured >= AA:
        return "AA"
    if measured >= AA_LARGE:
        return "AA large"
    return "fails"


def colours() -> dict[str, str]:
    """Every brand colour, by token name."""
    held = json.loads(TOKENS.read_text(encoding="utf-8")).get("color", {})
    if not held:
        raise SystemExit(f"::error::{TOKENS} carries no colours")
    missing = [one for one in SURFACES if one not in held]
    if missing:
        raise SystemExit(
            f"::error::{TOKENS} has no {', '.join(missing)}, and the table is "
            f"measured against those surfaces"
        )
    return held


def cell(token: str, surface: str, held: dict[str, str]) -> str:
    """One measurement, or a dash where a token is the surface itself."""
    if token == surface:
        return "—"
    measured = ratio(held[token], held[surface])
    return f"{measured:.2f} · {verdict(measured)}"


def table() -> list[str]:
    held = colours()
    rows = [
        "| Token | Hex | " + " | ".join(f"On `{one}`" for one in SURFACES) + " |",
        "|-------|-----|" + "|".join("---" for _ in SURFACES) + "|",
    ]
    for token, value in held.items():
        measured = " | ".join(cell(token, one, held) for one in SURFACES)
        rows.append(f"| `{token}` | {value} | {measured} |")
    return rows


def main() -> None:
    text = PAGE.read_text(encoding="utf-8")
    if not TABLE.search(text):
        raise SystemExit(f"::error::no measured table found in {PAGE}")
    PAGE.write_text(TABLE.sub("\n".join(table()), text, count=1), encoding="utf-8")
    print(f"60-brand: contrast measured for {len(colours())} tokens against "
          f"{len(SURFACES)} surfaces")


if __name__ == "__main__":
    main()
