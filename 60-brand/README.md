# Brand & design system

**Status:** Accepted

The visual language: logo, colour, type, and the tokens that carry them into the
product. This section owns the **requirements and cross-repo integration**; the
[`brand` repo](../30-repos/brand.md) owns the detailed usage docs and the assets
themselves.

---

## The split of responsibility

Per the [three-layer model](../40-quality/code-comments.md#the-three-documentation-layers),
brand documentation lives in two places and does not duplicate:

| Here (spec `60-brand/`) | `brand` repo `docs/` |
|-------------------------|----------------------|
| Binding rules as requirements (`DES-R`) | Full logo usage, clear-space maths, colour pairings |
| How brand reaches the three surfaces | The contact sheet, asset index |
| The accessibility contract | — |
| The [token contract](../20-architecture/contracts/design-tokens.md) (in architecture) | The token files themselves |

If you're applying the brand, read the `brand` repo's docs. If you're building a
consumer of it — the web UI, the TUI — read here.

## Why brand is in the spec at all

Two reasons it isn't just "a logo folder":

1. **It's a build-time contract.** The web UI consumes `@lemonfiber/brand` tokens
   at build time, structurally identical to the CLI consuming the stack manifest.
   A contract between two repos belongs in the canonical spec.
2. **It intersects accessibility.** [G3](../10-functional/features/g-ux/g3-accessibility.md)
   requires WCAG AA; whether the palette *meets* AA is a checkable property of the
   tokens, not a matter of taste — so it's specified, and tested.

## Contents

| Doc | Covers |
|-----|--------|
| [brand-rules.md](brand-rules.md) | The binding constraints — closed palette, amber-as-signal, mark integrity |
| [surface-mapping.md](surface-mapping.md) | How the brand reaches web, TUI and CLI — and what doesn't apply where |
| [accessibility.md](accessibility.md) | The contrast contract, with computed per-pairing verdicts |

The [token schema](../20-architecture/contracts/design-tokens.md) lives in
`20-architecture/contracts/` with the other build-time contracts.

## The `DES-R` namespace

Brand requirements use `DES-R##` — the sixth namespace, alongside feature
(`A2-R4`), governance (`GOV-R`), architecture (`ARCH-R`), per-repo (`REPO-R`) and
quality (`Q-R`).

Brand is the most judgment-heavy area in the project — "is the lemon saturated
enough?" has no requirement. So `DES-R` covers only the **checkable** constraints:
palette closure, contrast, mark integrity, token guarantees. Aesthetic judgment
stays judgment, and the [governance note](brand-rules.md#governing-a-visual-repo)
addresses how a visual repo cites the spec at all.

## The one thing to remember

**The palette is closed and the brand reaches only one surface fully.** The web
UI wears the full brand; the TUI gets a mapped-down subset; the CLI is nearly
brand-free. Designing as if all three can carry the logo and the amber is the
mistake this section exists to prevent — see [surface-mapping](surface-mapping.md).

## Related

- [30-repos/brand.md](../30-repos/brand.md) — the repo
- [design-tokens contract](../20-architecture/contracts/design-tokens.md)
- [G3 Accessibility](../10-functional/features/g-ux/g3-accessibility.md)
- [licence rationale](../90-appendix/license-rationale.md) — marks proprietary, tokens open
