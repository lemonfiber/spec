# Per-repo specifications

**Status:** Accepted

Where [20-architecture](../20-architecture/) describes the system, this section
describes each repository — its structure, its rules, and what is specific to
working inside it.

---

## The repos

```mermaid
flowchart TD
    spec[spec<br/>canonical]

    subgraph impl[Implementation]
        lemonfiber[lemonfiber<br/>Rust binary]
        stack[media-stack<br/>Compose + manifest]
        web[lemonfiber-web<br/>the web surface]
        sdk[sdk-ts<br/>the TypeScript client]
        sdkphp[sdk-php<br/>the PHP client]
        tap[homebrew-tap<br/>generated formula]
        brand[brand<br/>design tokens]
        site[website<br/>the public frontpage]
        docs[website-docs<br/>the documentation site]
    end

    stack -->|submodule, pinned| lemonfiber
    web -->|submodule, pinned| lemonfiber
    sdk -->|npm, pinned| web
    lemonfiber -->|contract artefact| sdk
    lemonfiber -->|contract artefact| sdkphp
    lemonfiber -->|release CI generates| tap
    brand -->|npm, pinned| site
    lemonfiber -->|docs submodule, pinned| docs
    brand -->|docs submodule, pinned| docs
    spec -.->|governs all| impl
```

| Repo | Spec | Language | What's specific about it |
|------|------|----------|--------------------------|
| `lemonfiber` | [lemonfiber.md](lemonfiber.md) · [lemonfiber-tui.md](lemonfiber-tui.md) · [lemonfiber-reference.md](lemonfiber-reference.md) | Rust | Three surfaces, one core; the submodule; the build |
| `lemonfiber-web` | [lemonfiber-web.md](lemonfiber-web.md) | TypeScript | Two surfaces, one component library; draws the API, implements nothing |
| `sdk-ts` | [sdk-ts.md](sdk-ts.md) | TypeScript | Published; owns the stream's hard parts so no consumer reimplements them |
| `sdk-php` | [sdk-php.md](sdk-php.md) | PHP | The same contract, implemented as a peer rather than translated |
| `media-stack` | [media-stack.md](media-stack.md) | YAML/TOML | Runs standalone; the compose rules CI enforces |
| `homebrew-tap` | [homebrew-tap.md](homebrew-tap.md) | Ruby | Generated; exists so `brew` works |
| `website` | [website.md](website.md) | Astro | The org is the motor; roadmap read, not written |
| `website-docs` | [website-docs.md](website-docs.md) | Astro | It renders; it does not own — every page pinned to the repo that wrote it |
| `brand` | [brand.md](brand.md) | CSS/SVG | Tokens are generated; the marks are not open |

## The `REPO-R` namespace

Per-repo requirements use `REPO-R##` — obligations specific to one repository's
structure or tooling, distinct from behaviour (`A2-R4`), architecture (`ARCH-R1`),
governance (`GOV-R2`) and quality (`Q-R1`).

## The relationships that matter

**`media-stack` → `lemonfiber` (submodule).** `lemonfiber` embeds a pinned tag of `media-stack`
and validates its `schema_version` at build time (`ARCH-R6`). They version
independently; the pin says exactly which stack a given binary ships
([versioning](../20-architecture/contracts/versioning.md)).

**`lemonfiber` → `homebrew-tap` (generation).** `lemonfiber`'s release CI regenerates the
formula. The tap is downstream of every `lemonfiber` release and is otherwise inert.

**Every repo → `website-docs` (submodules).** The documentation site shows each repo's
own `.docs/`, README and policy files, pinned to an exact revision and rendered rather
than copied ([ADR-0015](../00-overview/decisions/0015-docs-site-renders-what-it-does-not-own.md)).
The specification is the exception: it is linked to its mdBook, not mirrored.

**Everything ← `spec` (governance).** No change to any of them lands without
citing this repository ([50-governance](../50-governance/)).

**`lemonfiber` → the SDKs (generation).** `lemonfiber` emits one contract artefact
from its own `serde` types; `sdk-ts` and `sdk-php` generate their types from it
and hand-write only behaviour ([ADR-0014](../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md)).

## The one property to remember per repo

- **`lemonfiber`** — logic cannot render. The core crate has no UI dependency, so a
  surface can never grow behaviour of its own.
- **`media-stack`** — it runs without lemonfiber. Plain `docker compose` works,
  which is what makes adopting the tool reversible.
- **`homebrew-tap`** — nobody writes it. It's generated, and exists only because
  Homebrew requires a repo of that name.
- **`website`** — the org is the motor. Roadmap and status are read from the org
  at build time, never hand-authored, so the page cannot drift from reality.
- **`website-docs`** — it renders; it does not own. Every page is another repo's
  file at a revision the site names, so a wrong sentence is fixed where it was written.

## Related

- [20-architecture](../20-architecture/) — the system across repos
- [40-quality](../40-quality/) — the standards all code is held to
- [50-governance](../50-governance/) — how change enters each repo
