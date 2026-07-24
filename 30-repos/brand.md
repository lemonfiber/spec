# Repo: `brand`

**Status:** Accepted

The design system — logo assets, colour/type/space tokens, and usage docs.
Published as `@lemonfiber/brand`.

**Implements:** [60-brand](../60-brand/), the
[design-token contract](../20-architecture/contracts/design-tokens.md).

---

## What this repo is

The single source of the brand: SVG marks, tokens as CSS + JSON, and the detailed
usage docs. Pull assets from here rather than re-drawing or re-exporting — that is
the repo's whole purpose, and the reason it's a repo rather than a folder in `cli`.

`cli`'s web UI consumes it as a pinned npm dependency
([contract](../20-architecture/contracts/design-tokens.md)); the marks are also
referenced where the web UI shows a logo.

## Layout

```
brand/
├── assets/logo/        SVG marks — proprietary (see licence)
├── tokens/
│   ├── tokens.css      CSS custom properties
│   └── tokens.json     the same values as data
├── docs/
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
| `assets/logo/*` | **Proprietary**, all rights reserved | Trademark protection — anyone could otherwise ship a fork under the exact name and mark |
| `tokens/*` | Open (same as tokens are meant to be embedded) | The web UI embeds them; they must be freely usable |
| `docs/*` | CC BY-SA 4.0 | Documentation, like the spec |

This is the standard pattern — Rust, Mozilla and Python all protect marks inside
open projects. The `LICENSE` file governs the marks; `LICENSE-tokens` governs the
rest, and the README states the split at the top so no one mistakes the marks for
freely reusable.

## What the spec owns vs. this repo

| Spec (`60-brand/`, contracts) | This repo (`docs/`) |
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
| Token parity | `tokens.css` and `tokens.json` hold identical values (`ARCH-R38`) |
| **Contrast check** | Every body-text pairing meets WCAG AA (`ARCH-R40`, [baseline](../60-brand/accessibility.md)) |
| SVG hygiene | Marks are valid, optimised, and outlined where specified |
| `npm publish` dry-run | The package builds and exports resolve |

The contrast check is the notable one: it computes the ratios in
[accessibility](../60-brand/accessibility.md) and fails on a body pairing below
AA. A recolour that looks fine and fails a meter is caught here, not in the web UI.

## Publishing

A tagged release publishes `@lemonfiber/brand` to the registry. `cli` bumps its
pinned dependency deliberately (cite `GOV-R12`) to pick up a brand change — the
[token contract](../20-architecture/contracts/design-tokens.md#versioning) keeps
brand and binary decoupled, so a recolour never surprises a shipped `cli`.

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
| **REPO-R32** | A release MUST publish `@lemonfiber/brand`, and `cli` MUST consume a pinned version. |
| **REPO-R33** | Aesthetic changes within the rules MAY cite `GOV-R12`; changes to the rules MUST be `DES-R` changes. |

## Related

- [60-brand/](../60-brand/) — the brand section
- [design-tokens contract](../20-architecture/contracts/design-tokens.md)
- [licence rationale](../90-appendix/license-rationale.md)
- [ADR-0004 Four-repo split](../00-overview/decisions/0004-four-repo-split.md) — why brand is its own repo
