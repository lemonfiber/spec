# Contract: design tokens

**Status:** Accepted

The interface between `brand` and `lemonfiber`'s web UI. The web UI's visual language
comes entirely from these tokens; it hardcodes no colour, size, or spacing.

**Satisfies:** [G1-R2](../../10-functional/features/g-ux/g1-interface-tiers.md),
[G3-R3](../../10-functional/features/g-ux/g3-accessibility.md),
[DES-R1](../../60-brand/README.md)

---

## Why this is a contract

The web UI ([component-model](../component-model.md#web-ui)) is built at release
time and embedded in the binary. If it hardcodes `#F0C419`, a brand change means
editing Rust-adjacent frontend source in a different repo — the same coupling the
[stack manifest](stack-manifest.md) exists to avoid, in a different guise.

Tokens make the brand **data the web UI consumes**, exactly as the manifest makes
the stack data the CLI consumes. `brand` owns the values; `lemonfiber` consumes them at
build time.

## Consumption: npm, build-time

`brand` publishes `@lemonfiber/brand`. `lemonfiber`'s `web-ui` takes it as a build
dependency and compiles the tokens into the embedded assets:

```jsonc
// lemonfiber/crates/lemonfiber/web-ui/package.json
"dependencies": { "@lemonfiber/brand": "0.2.0" }
```

```css
@import "@lemonfiber/brand/tokens.css";
.header { background: var(--lf-color-paper); color: var(--lf-color-ink); }
```

The version is pinned. A brand release is a deliberate `lemonfiber` dependency bump
(cite `GOV-R12`), never a floating pull — the same discipline as pinned image
tags (`E1-R1`), for the same reason.

The `web-ui` build already runs at release time and is the only non-Rust
toolchain (`ARCH-R19`); consuming an npm package fits that step and reaches the
end user embedded, never as a runtime dependency.

## The token surface

Published as **both** `tokens.css` (CSS custom properties) and `tokens.json`
(raw values). CSS for the web UI; JSON for anything that needs the values as data
— notably the TUI's [colour mapping](../../60-brand/surface-mapping.md).

### Namespacing

Every token is prefixed `--lf-` (CSS) or lives under a typed key (JSON). The
prefix is part of the contract: it guarantees no collision with a token the web
UI defines itself, and makes brand tokens greppable.

### Categories

| Category | Prefix | Example |
|----------|--------|---------|
| Colour — core | `--lf-color-{ink,lemon,fiber,leaf,…}` | `--lf-color-lemon: #F0C419` |
| Colour — surfaces | `--lf-color-{paper,pith,canvas,line,…}` | `--lf-color-paper: #FBF7EA` |
| Type | `--lf-font-*`, `--lf-size-*`, `--lf-weight-*`, `--lf-tracking-*` | `--lf-size-body: 15px` |
| Space | `--lf-space-{1..8}` | `--lf-space-4: 16px` (4px base) |
| Radius | `--lf-radius-{sm,md,icon,pill}` | `--lf-radius-md: 4px` |
| Elevation | `--lf-shadow-*` | `--lf-shadow-lift` |

### Theme

A single attribute switches the ink (dark) theme:

```css
[data-lf-theme="ink"] { --lf-color-paper: #17160F; … }
```

Surface tokens are redefined under the attribute; core tokens like `--lf-color-ink`
are not. The web UI's theme toggle
([G3](../../10-functional/features/g-ux/g3-accessibility.md)) stamps this attribute
— tokens are what make theme-awareness a data change rather than a code branch.

## What the tokens MUST guarantee

These are contract obligations, not brand preferences — the web UI relies on them:

| Rule | Why |
|------|-----|
| Every token exists in both `tokens.css` and `tokens.json` | The TUI reads JSON; drift between the two breaks colour mapping |
| Token names are stable within a major version | Renaming a token is a breaking change to every consumer |
| Removing or renaming a token bumps the major version | `lemonfiber` pins a version; a silent removal breaks its build |
| Every text/surface colour pair used for body copy meets **WCAG AA** | [G3-R3](../../10-functional/features/g-ux/g3-accessibility.md) requires it; see [accessibility](../../60-brand/accessibility.md) |
| The ink theme redefines every surface token the paper theme defines | A half-themed token renders an unreadable pairing in dark mode |

The contrast obligation is the one with teeth: a token pairing that fails AA is a
**contract violation**, caught by the [token contrast check](../../60-brand/accessibility.md),
not a matter of taste.

## Versioning

Tokens follow semver, independent of `lemonfiber`, `stack_version`, and `schema_version`
([versioning](versioning.md)):

| Change | Version |
|--------|---------|
| Add a token | Minor |
| Change a token's value (recolour, resize) | Minor — consumers pick it up on bump |
| **Rename or remove a token** | **Major** — breaks consumers |
| Change what a token *means* | **Major** |

`lemonfiber` pinning an exact version means a brand recolour reaches users only when
`lemonfiber` deliberately bumps and rebuilds — brand and binary stay decoupled, and a
brand change can never surprise a shipped binary.

## What is NOT in this contract

The **logo assets** (`assets/logo/*.svg`) are not tokens and not part of this
build-time interface in the same way. They are proprietary marks
([licence](../../90-appendix/license-rationale.md)), referenced where the web UI
needs a logo, and governed by [brand rules](../../60-brand/brand-rules.md) rather
than by a token schema.

## Requirements

| ID | Requirement |
|----|-------------|
| **ARCH-R36** | The web UI MUST derive all colour, type, spacing and radius from `@lemonfiber/brand` tokens, hardcoding none. |
| **ARCH-R37** | `lemonfiber` MUST depend on an exact, pinned `@lemonfiber/brand` version, never a range. |
| **ARCH-R38** | Tokens MUST be published as both `tokens.css` and `tokens.json`, with identical values. |
| **ARCH-R39** | Removing or renaming a token MUST be a major version bump. |
| **ARCH-R40** | Every body-text colour pairing MUST meet WCAG AA, verified by the token contrast check. |
| **ARCH-R41** | The ink theme MUST redefine every surface token the default theme defines. |

## Related

- [60-brand/](../../60-brand/) — the brand section: rules, surfaces, accessibility
- [30-repos/brand.md](../../30-repos/brand.md) — the repo
- [stack-manifest.md](stack-manifest.md) — the parallel build-time contract
- [component-model](../component-model.md#web-ui) — the consumer
