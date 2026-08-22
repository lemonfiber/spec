# Repo: `lemonfiber-web`

**Status:** Accepted

The web surface: a static single-page application drawn from the JSON API the
`lemonfiber` binary serves. TypeScript, Hippocratic 3.0.

**Implements:** the web side of
[G1](../10-functional/features/g-ux/g1-interface-tiers.md),
[G3](../10-functional/features/g-ux/g3-accessibility.md), and the
[web API contract](../20-architecture/contracts/web-api.md).

---

## What this repo is

A **static application with no server of its own**. It is built to a directory of
files, tagged, and embedded into the binary as a pinned submodule
([ADR-0012](../00-overview/decisions/0012-web-assets-embedded-at-build-time.md)).
At run time it talks to `lemonfiber` over the
[web API](../20-architecture/contracts/web-api.md) and to nothing else.

That constraint is the point, not a limitation. `G1-R2` says no surface may
implement behaviour independently; an application whose only capability is to ask
the core and draw the answer **cannot** violate it.

## Why a separate repo

[ADR-0011](../00-overview/decisions/0011-web-surface-as-a-fifth-repo.md) records the
argument. In short: a Node toolchain inside a Rust workspace whose gates, lints and
coverage rules all assume Rust is a poor fit, and component review wants a cadence of
its own. The contract being avoided is one already published and versioned for scripts.

## What it consumes

| From | What | How |
|---|---|---|
| `lemonfiber` | State and actions | The [web API](../20-architecture/contracts/web-api.md), at run time |
| `brand` | Colour, type, spacing, radii, the logo | [`@lemonfiber/brand`](../20-architecture/contracts/design-tokens.md), at build time |

It hardcodes no colour, size or spacing — those are the brand's to own, and this
application consumes them as data.

## The two surfaces

The application serves two audiences, and the spec marks every feature for one or
both. They are **not** the same interface with things hidden:

- **The console** — an operator's view. Everything: state, checks, logs, services,
  setup, household administration.
- **The household view** — what everyone else gets. Asking for something, seeing
  whether it is ready, and nothing else. No logs, no services, no settings.

Both are built from one component library and one set of tokens, so they cannot drift
apart visually; what differs is which of them a given person is served.

## Quality bar

The Rust workspace's standards apply from the first commit, in their web equivalents:

| The workspace requires | Here |
|---|---|
| 100% line coverage | Vitest thresholds at 100 for lines, statements, branches and functions |
| `unwrap`/`panic` denied | `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`; `any` and non-null assertions banned |
| `pedantic`, `-D warnings` | `typescript-eslint` `strictTypeChecked`, zero warnings tolerated |
| architecture tests | `dependency-cruiser` layering rules and a file-size guard, in CI |
| `cargo fmt --check` | Prettier `--check` as its own gate |

Beyond them, because this surface has requirements the CLI does not:
accessibility assertions in component and end-to-end tests
([G3](../10-functional/features/g-ux/g3-accessibility.md) is a goal, not a courtesy),
a bundle-size budget, and a content-security policy that permits no external origin.

## What it must not do

- **Reach anything but `lemonfiber`.** No CDN, no font host, no analytics, no
  telemetry. Typefaces and assets are embedded at build time, which is also what makes
  the interface identical on Linux, Windows and macOS.
- **Implement behaviour.** If the answer is not in an envelope, the surface does not
  know it.
- **Invent an action.** Everything it can do, the CLI can do
  ([`ARCH-R48`](../20-architecture/contracts/web-api.md)).

## Related

- [ADR-0011](../00-overview/decisions/0011-web-surface-as-a-fifth-repo.md) — why it is its own repo
- [ADR-0012](../00-overview/decisions/0012-web-assets-embedded-at-build-time.md) — how it ships
- [web-api.md](../20-architecture/contracts/web-api.md) · [design-tokens.md](../20-architecture/contracts/design-tokens.md)
- [lemonfiber.md](lemonfiber.md) — the binary that serves it
