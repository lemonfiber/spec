# Repo: `brand`

**Status:** Accepted

The design system — logo assets, colour/type/space tokens, and usage docs,
packaged as `@lemonfiber/brand`. Consumers take it as a commit-pinned git
dependency; nothing is published to a registry yet.

**Implements:** [60-brand](../60-brand/), the
[design-token contract](../20-architecture/contracts/design-tokens.md).

---

## What this repo is

The single source of the brand: SVG marks, tokens as CSS + JSON, and the detailed
usage docs. Pull assets from here rather than re-drawing or re-exporting — that is
the repo's whole purpose, and the reason it's a repo rather than a folder in `lemonfiber`.

`lemonfiber`'s web UI consumes it as a dependency pinned to a commit
([contract](../20-architecture/contracts/design-tokens.md)); the marks are also
referenced where the web UI shows a logo.

## Layout

```
brand/
├── assets/logo/        SVG marks and their PNG exports — proprietary (see licence)
├── scripts/
│   ├── logo.py         draws every file in assets/logo/ — proprietary
│   └── check_tokens.py the token gate
├── tokens/
│   ├── tokens.css      CSS custom properties
│   └── tokens.json     the same values as data
├── .docs/
│   ├── colour.md       full palette + rules
│   ├── typography.md
│   ├── logo-usage.md   clear space, minimums, pairings
│   └── asset-sheet.html  contact sheet
├── package.json        @lemonfiber/brand
├── CHANGELOG.md
├── LICENSE             marks — proprietary
├── LICENSE-tokens      tokens + docs — open
└── README.md
```

## The split licence

This repo is where the project's "open source, protected brand" position becomes
concrete ([licence rationale](../90-appendix/license-rationale.md)):

| Path | Licence | Why |
|------|---------|-----|
| `assets/logo/*`, `scripts/logo.py` | **Proprietary**, all rights reserved | Trademark protection — anyone could otherwise ship a fork under the exact name and mark |
| `tokens/*` | Open (same as tokens are meant to be embedded) | The web UI embeds them; they must be freely usable |
| `.docs/*` | CC BY-SA 4.0 | Documentation, like the spec |

This is the standard pattern — Rust, Mozilla and Python all protect marks inside
open projects. The `LICENSE` file governs the marks; `LICENSE-tokens` governs the
rest, and the README states the split at the top so no one mistakes the marks for
freely reusable.

## What the spec owns vs. this repo

| Spec (`60-brand/`, contracts) | This repo (`.docs/`) |
|-------------------------------|---------------------|
| The token schema and versioning | The token files |
| The accessibility contract + CI check | — |
| Surface mapping (web/TUI/CLI) | — |
| Binding rules as `DES-R` | Full usage guidance, clear-space maths, the contact sheet |

The rule of thumb matches every other repo: **what and why, and cross-repo
contracts, are the spec's; the detailed how is the repo's.**

## CI

| Check | Enforces |
|-------|----------|
| `spec-check` | Governance — every change cites a spec identifier ([GOV](../50-governance/cross-repo-ci.md)) |
| `just logo-check` (`scripts/logo.py --check`), in `just ci` only | Every file under `assets/logo/` is what the generator's grids draw, and nothing else is there |
| `tokens` (`scripts/check_tokens.py`) | Every token in `tokens.json` appears in `tokens.css` and every `--lf-` property in `tokens.css` appears in `tokens.json`, with identical values, the ink theme's included; `ink`, `ink-soft`, `text-muted`, `leaf` and `fiber-deep` each meet WCAG AA on `paper`, and the ink theme's `text`, `text-muted`, `text-faint` and `fiber-deep` on its own `paper`; `--self-test` first holds the arithmetic to ratios WCAG states and the parity check to each way the two files can drift apart |

A JSON key names its CSS property: `color.ink` is `--lf-color-ink`, `size.displayXl`
is `--lf-size-display-xl`, and `font.weightBody` and `font.trackingDisplay` are
`--lf-weight-body` and `--lf-tracking-display`. A number under `space` or `radius`
is that many px, and a CSS font stack is its `font` family followed by its
`fallback` list, so `font` stays the bare family names its readers take. The
contrast half measures the pairings above and no others, so it covers part of what
`ARCH-R40` asks. A recolour that looks fine and fails that meter is caught
here, not in the web UI.

## Publishing

`@lemonfiber/brand` is not published to a registry and has no tags, so consumers
pin a commit. A consumer moves the pin
deliberately (cite `GOV-R12`) to pick up a brand change — the
[token contract](../20-architecture/contracts/design-tokens.md#versioning) keeps
brand and binary decoupled, so a recolour never surprises a shipped `lemonfiber`.

## Governing aesthetic change

Brand is judgment-heavy. The [governance resolution](../60-brand/brand-rules.md#governing-a-visual-repo):
changes within the rules (a new export, a recolour inside the palette) cite
`GOV-R12`; changes to what the rules *permit* are `DES-R` changes following the
normal lifecycle. This keeps the repo under governance without pretending
aesthetics are requirements.

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R29** | The marks MUST be licensed proprietary; tokens and docs MUST be openly licensed, with the split stated in the README. |
| **REPO-R30** | CI MUST verify `tokens.css` and `tokens.json` hold identical values. |
| **REPO-R31** | CI MUST run the contrast check and fail on a body pairing below WCAG AA. |
| **REPO-R32** | A release MUST publish `@lemonfiber/brand`, and `lemonfiber` MUST consume a pinned version. |
| **REPO-R33** | Aesthetic changes within the rules MAY cite `GOV-R12`; changes to the rules MUST be `DES-R` changes. |

## Related

- [60-brand/](../60-brand/) — the brand section
- [design-tokens contract](../20-architecture/contracts/design-tokens.md)
- [licence rationale](../90-appendix/license-rationale.md)
- [ADR-0004 Four-repo split](../00-overview/decisions/0004-four-repo-split.md) — why brand is its own repo
