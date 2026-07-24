# Code comments

**Status:** Accepted

Code should be readable on its own. Architecture belongs in `lemonfiber/.docs/`.
Comments are the exception, not the norm — reserved for the few places where
genuinely non-obvious code needs a *why* the code itself cannot carry.

This is the Rust counterpart of a convention proven in PHP and TypeScript. The
mechanical rules port directly; **M4 does not**, and the reasoning is recorded
below rather than silently dropped.

---

## Philosophy

1. **Readable code first.** If a comment could be deleted by renaming a binding,
   extracting a function, or introducing a named constant — do that instead.
2. **Architecture lives in `.docs/`.** System shape, data flow, cross-module
   contracts and "how the pieces fit" are documented in Markdown and linked from
   the code, never re-explained inline.
3. **Comments explain *why*, never *what*.** A comment restating what the next
   line does is noise. A comment capturing a non-obvious reason, constraint or
   trap earns its place — and if it does, it is never a throwaway one-liner.
4. **Production-ready always.** Shipped code is finished. No deferral notes, no
   tickets, no "come back to this." If work remains, the work is not done.

## The three documentation layers

```
lemonfiber/spec/          canonical · cross-repo · WHAT and WHY
  47 features, 645 requirements, ADRs
        ▲ cited by
lemonfiber/.docs/                repo-local · Rust-specific HOW
  architecture/ adr/ conventions/ runbooks/
        ▲ linked from
src/**/*.rs               why only · 2–4 line blocks · no IDs
```

Each layer points **one step outward**. Nothing is duplicated, and each has a
different rate of change: the spec changes on decisions, `.docs/` on
implementation approach, comments on the code beside them.

`media-stack` and `homebrew-tap` have **no `.docs/` tree** — they are YAML and
Ruby, their decisions are product decisions, and those belong in the canonical
spec.

`brand` **does** carry a `.docs/` tree, but of a different kind: it holds the
brand *usage* documentation (colour, typography, logo usage) — the repo's own
domain docs, not Rust implementation notes. The convention is the same (repo-local
docs, dotted, not shipped in the npm package); the content is design rather than
code. So: `lemonfiber` and `brand` have `.docs/`; `media-stack` and `homebrew-tap`
don't.

## Scope

Applies to **Rust production source**: `crates/**/src/**/*.rs`.

Explicitly **excluded**:

- `**/tests/**` and `#[cfg(test)]` modules — tests may carry explanatory
  rationale freely; a test that needs a paragraph to explain what it proves is
  usually a good test.
- `build.rs` — build scripts are scaffolding.
- Generated code.
- `*.rs.fixture` — the policy's own violation fixtures (see [Enforcement](#enforcement)).

## The two layers

Enforced at two levels. Keeping them distinct is what stops the test being either
toothless or tyrannical.

- **Mechanical (`M*`)** — comment *shape*. Deterministic, enforced by a test.
- **Judgment (`J*`)** — comment *worth*. Whether the code deserves a comment at
  all. Only a human reviewer or an AI assistant can judge these; the test cannot.
  They bind every contributor regardless.

## Mechanical rules

| # | Rule |
|---|------|
| **M1** | No lone single-line `//` comment. An informative `//` must be part of a contiguous block of **2–4 lines**. A one-line note means the code should say it instead — delete it, or if the *why* is real, expand it into a proper block. |
| **M2** | A contiguous `//` block is **2 lines minimum, 4 lines maximum**. Anything needing more than 4 lines of prose belongs in `.docs/`, linked. |
| **M3** | No informative `/* … */` block comments. |
| **M5** | No deferral or provenance tokens anywhere in a comment: `TODO`, `FIXME`, `HACK`, `XXX`, `SAFETY:`-adjacent placeholders, ticket keys, **requirement IDs**, ADR numbers, phase numbers. |
| **M6** | Every Markdown link in a doc comment pointing at a `.md` file MUST resolve to a real file under `.docs/`. Broken doc links fail the build. |
| **M7** | Every public item MUST carry a doc comment (`missing_docs` denied at crate level). |

### Why M1 is the load-bearing rule

M1 is the mechanism that kills the specific failure this policy exists to
prevent: comments explaining obvious behaviour.

`// Increment the counter` cannot be expanded into two lines of genuine *why*,
because there isn't any. A real reason — an invariant, an ordering constraint, a
defended-against edge case — naturally occupies two to four lines. **The length
floor is a relevance filter.**

It is also the rule that resists AI-generated narration most effectively, since
that style is characteristically one line per statement.

### M4 is deliberately absent

The PHP and TypeScript versions of this convention include **M4: docblocks are
`@`-tag only, no descriptive prose** — a symbol's purpose is its name plus a link.

**M4 does not port to Rust**, and forcing it would be actively harmful:

- `///` doc comments *are* prose by design; rustdoc renders them as the public
  API surface consumers read.
- `#![deny(missing_docs)]` exists specifically to require them, and cannot be
  meaningfully satisfied by a bare link.
- A tag-only convention would produce `cargo doc` output that is useless to
  anyone outside this project.

The intent M4 protects — no walls of prose in code, architecture in `.docs/` —
is carried instead by **J3** and **J4**, plus M7 requiring the doc comment to
exist at all. What Rust loses is the mechanical guarantee; what it keeps is the
ecosystem's own documentation conventions, which matter more.

### M5, stated without euphemism

M5's pattern matches ticket keys, **requirement IDs**, ADR numbers and phase
numbers. That is not collateral damage — it is the rule.

**A requirement ID may never appear in a Rust comment.** Not as provenance, not
as a breadcrumb, not "just this once."

Provenance is not documentation. A comment naming *which* planning artefact
caused a line to exist is worthless to the next reader and rots the moment that
artefact is superseded. The reason a line exists belongs in `.docs/`, where it
can be revised, reached from the code by a link. Everything an ID would have
gestured at, the linked page states outright.

This is [GOV-R6](../50-governance/canonical-spec.md#the-gov-r-namespace), and it
binds authors and AI agents alike: **a plan may never instruct anyone to write a
requirement ID into a code comment, and no such instruction may be obeyed.**
Citations go in commit trailers and PR bodies, which is where provenance belongs.

### The directive allow-list

A small set of comments are not informative comments — they are machine
directives. Only these are exempt from M1–M3:

- `// SAFETY: …` preceding an `unsafe` block, where the crate permits `unsafe` at
  all. lemonfiber denies `unsafe_code` crate-wide, so in practice this is
  unreachable and remains listed only so its absence is deliberate.
- `#[allow(…)]` and `#[expect(…)]` are attributes, not comments, and fall outside
  this policy — they are governed by the lint policy in
  [code-standards](code-standards.md).

That is the entire list. **Suppression comments are not on it, and the omission
is deliberate** — an exemption in the comment policy would hide a lint finding in
the one place the comment gate has been told not to look.

## Judgment rules

| # | Rule |
|---|------|
| **J1** | Prefer self-documenting code. Exhaust rename / extract / named-constant before writing any comment. |
| **J2** | Write an inline `//` block only when the code is genuinely complex or the *why* is non-obvious — a constraint, an ordering trap, a defended-against edge case. Never to narrate *what* the code does. |
| **J3** | Architecture, data flow and cross-module contracts go in `.docs/`, never inline. |
| **J4** | Doc comments are a **one-line summary plus a link** where a documented home exists. Multi-paragraph rustdoc essays are a J4 violation even though M4 does not mechanically forbid them. |
| **J5** | Nothing is deferred in a comment. If it isn't done, it isn't production-ready — finish it or cut it. |

## Worked examples

```rust
// ✗ M1 — lone one-liner, and narrates WHAT
// Increment the retry counter
retries += 1;

// ✗ M1/J2 — AI narration; one line per statement
// First check if the port is available, then bind to it
if port_available(p) { bind(p)?; }

// ✗ M5 — requirement ID as provenance
// Required by C2-R5: re-push the port after reconnect
push_port(port).await?;

// ✓ M1, M2, J2 — two lines, explains WHY, no ID
// The forwarded port is reassigned on every reconnect and the
// client silently keeps the stale one, so re-read rather than cache.
let port = tunnel.forwarded_port().await?;
```

```rust
// ✓ M7, J4 — one-line summary plus a link out
/// Re-reads the tunnel's currently forwarded port.
///
/// See [port lifecycle](../.docs/architecture/vpn-port-forwarding.md).
pub async fn forwarded_port(&self) -> Result<Option<u16>> {
```

```rust
// ✗ J4 — rustdoc essay; belongs in .docs/
/// Re-reads the forwarded port.
///
/// The VPN provider assigns a port dynamically via NAT-PMP. This port
/// does not survive a reconnect, which means that after any tunnel
/// drop the download client will be listening on a port that is no
/// longer forwarded. Historically this was handled by a sidecar
/// container, but that approach had the drawback of …
```

## Enforcement

### Why a lexer, not a regex

A regex scanning for `//` is wrong in Rust, and wrong in ways that produce both
false positives and false negatives:

```rust
let s = "// not a comment";
let r = r#"also // not a comment"#;
let c = '/';
/* nested /* block */ comments are legal */
```

Enforcement therefore uses a **real Rust lexer** (`rustc_lexer`), which
classifies tokens natively:

| Token | Rule applied |
|-------|--------------|
| `LineComment` with `///` or `//!` | Doc comment → M5, M6, M7 |
| `LineComment` otherwise | Inline → M1, M2, M5, unless allow-listed |
| `BlockComment` with `/**` or `/*!` | Doc comment → M5, M6 |
| `BlockComment` otherwise | **M3 violation** |
| String, raw string, char literals | Skipped — the reason a lexer is required |

### Proving the gate fires

A comment policy walks production source looking for offenders. A young
repository has almost no production source, and what it has is comment-free — so
every rule passes, **and passes for the wrong reason**.

A green comment gate over an empty tree proves nothing whatsoever, and goes on
proving nothing right up until the first narratively-commented file merges, at
which point it is too late to discover the rule was mistuned.

The gate therefore runs **twice**:

1. Over the production tree, where it must find nothing.
2. Over a tree of deliberate violations, where **each rule must find its own
   violation and no other**.

Fixtures live at `crates/*/tests/fixtures/comment_policy/`, one per rule plus a
compliant control every rule must pass.

They are named `*.rs.fixture`, not `*.rs`. **The extension is load-bearing**: the
fixtures contain policy violations on purpose, and the extension keeps them out
of the formatter's, clippy's, the compiler's and the coverage tool's field of
view. Any gate grepping tracked source for banned tokens must scope itself to
`*.rs`, or it will indict the fixtures that prove it works.

## Requirements

| ID | Requirement |
|----|-------------|
| **Q-R1** | An informative `//` comment MUST be part of a contiguous 2–4 line block. |
| **Q-R2** | Informative `/* … */` block comments MUST NOT be used. |
| **Q-R3** | Comments MUST NOT contain deferral tokens, ticket keys, requirement IDs, ADR numbers or phase numbers. |
| **Q-R4** | Every public item MUST carry a doc comment; `missing_docs` MUST be denied at crate level. |
| **Q-R5** | Every Markdown `.md` link in a doc comment MUST resolve to a real file under `.docs/`. |
| **Q-R6** | Comment-policy enforcement MUST use a Rust lexer, never a regex over raw source. |
| **Q-R7** | The enforcement gate MUST run against a fixture tree of deliberate violations, and each rule MUST detect its own fixture and no other. |
| **Q-R8** | Violation fixtures MUST use an extension excluding them from compilation, formatting, linting and coverage. |
| **Q-R9** | The directive allow-list MUST NOT include any lint- or coverage-suppression form. |
| **Q-R10** | Architecture and cross-module contracts MUST live in `lemonfiber/.docs/`, not in comments. |

## Portability

To adopt this convention elsewhere:

1. Copy this file into the target project's conventions tree.
2. Copy the enforcement test **and its fixture tree**; adjust scope roots only. A
   test shipped without its fixtures is a test that cannot tell you it has
   stopped working.
3. Reconsider M4 per language: mandatory where the doc format is tag-based
   (PHPDoc, TSDoc), omitted where it is prose-based (rustdoc).

## Related

- [code-standards.md](code-standards.md) — lint policy, MSRV, error handling
- [GOV-R6](../50-governance/canonical-spec.md#the-gov-r-namespace) — why IDs are banned in comments
- [50-governance/README](../50-governance/README.md#the-two-reference-paths) — the two reference paths
