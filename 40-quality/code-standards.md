# Code standards

**Status:** Accepted

How Rust is written in `cli`. Every rule here is mechanically enforced or
explicitly marked judgment — a standard that is neither is decoration.

**Satisfies:** the correctness posture of
[P3](../00-overview/vision.md#p3--the-tool-proves-things-rather-than-assuming-them),
[G4](../10-functional/features/g-ux/g4-error-model.md).

---

## MSRV

The minimum supported Rust version is **pinned and tested**, not merely declared.
CI builds against it; a feature requiring a newer compiler is a deliberate MSRV
bump, not an accident discovered downstream.

## Lint policy — strict, zero-suppression

```rust
#![forbid(unsafe_code)]
#![deny(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::todo,
    clippy::unimplemented,
    clippy::indexing_slicing,
)]
#![warn(clippy::pedantic, clippy::nursery)]
#![deny(missing_docs)]
```

| Rule | Rationale |
|------|-----------|
| `forbid(unsafe_code)` | Nothing in this domain needs it. `forbid`, not `deny` — it cannot be re-permitted locally. |
| No `unwrap`/`expect`/`panic` in library code | A panic is an unhandled error with no remedy — the exact opposite of [G4](../10-functional/features/g-ux/g4-error-model.md). Every error path must be a typed value. |
| No `indexing_slicing` | `arr[i]` panics; `arr.get(i)` is a value. |
| No `todo`/`unimplemented` | Shipped code is finished (`Q-R` philosophy, [comment policy](code-comments.md)). |
| `pedantic` + `nursery` | On as warnings; each finding is fixed, not silenced. |
| `missing_docs` | Public API is documented ([M7](code-comments.md#mechanical-rules)). |

### Zero suppression

There are exactly two legal responses to a lint finding: **change the code**, or
**change the rule** (with a documented reason, at the crate root, reviewed).

`#[allow(...)]` in `src/` is **not** a third option, and an architecture test
fails the build on its presence. A suppression does not answer a finding — it
hides one, in the place least likely to be looked at again.

Test code is exempt: `#[cfg(test)]` and `tests/` may `unwrap`, `expect`, and
`allow` freely. A test that panics on a broken assumption is working correctly.

## Error handling

Typed in the core, rich at the binary — and the type carries the remedy so it
cannot be forgotten.

### In `lemonfiber-core` — `thiserror`, matchable

```rust
#[derive(Debug, thiserror::Error)]
pub enum StorageError {
    #[error("data root spans more than one filesystem")]
    SplitMount { path: PathBuf, remedy: Remedy },

    #[error("data root is on an exFAT volume, which cannot hardlink")]
    NoHardlinks { path: PathBuf, remedy: Remedy },
}
```

Every variant carries a `Remedy` (`G4-R1`). This is the mechanism that makes
"every error names its fix" structural rather than a thing reviewers must police:
a variant without a remedy does not compile.

Callers **match** on these — the [doctor](../10-functional/features/c-trust/c1-diagnostics.md)
and [remediation](../10-functional/features/c-trust/c3-auto-remediation.md)
subsystems map error kinds to findings and fixes, which `anyhow`-style opaque
errors could not support.

### In the `lemonfiber` binary — `color-eyre`

The binary renders errors in G4's four-part shape: what happened, what it means,
what to do, where to look. `color-eyre` provides the report; the `Remedy` supplies
the "what to do".

### The `Remedy` type

```rust
pub struct Remedy {
    pub summary: String,       // one line: what to do
    pub steps: Vec<String>,    // concrete actions
    pub doc: Option<DocLink>,  // deeper reference in .docs/
}
```

Remedies are data, so they can be rendered identically across CLI, TUI and web
(`G1`), and tested.

## Module boundaries

Enforced by the crate graph, not by convention
([component-model](../20-architecture/component-model.md)):

- `lemonfiber-core` depends on no UI crate (`ARCH-R11`).
- `stack::compose` and `docker::*` do not depend on each other (`ARCH-R14`).
- An architecture test asserts these edges, so a violating `use` fails CI.

## Naming & idiom

Judgment rules — bind everyone, enforced by review:

- **J** Match the surrounding code. New code should be indistinguishable from
  what's there.
- **J** Names carry the *why* so comments don't have to
  ([J1](code-comments.md#judgment-rules)).
- **J** Prefer `Result` and the type system over runtime checks. An invariant
  encoded in a type cannot be violated; one checked at runtime can.
- **J** No premature abstraction. A trait with one implementation is usually a
  function.

## Formatting

`rustfmt` with the repo's `rustfmt.toml`, enforced in CI. Not negotiable and not
discussed — formatting arguments are wasted minutes, and a formatter ends them.

## Async discipline

`tokio`, shallow ([component-model](../20-architecture/component-model.md#async-model)).
Judgment rules:

- **J** Async only where there is real concurrency. Pure computation stays sync.
- **J** The render loop never `.await`s I/O or holds a lock across a frame
  (`ARCH-R15`) — this one is also checked by a lint on the render module.
- **J** Background tasks own their data and send snapshots (`ARCH-R16`).

## Requirements

| ID | Requirement |
|----|-------------|
| **Q-R11** | `unsafe` MUST be forbidden crate-wide. |
| **Q-R12** | `unwrap`, `expect`, `panic`, `todo`, `unimplemented` and slice indexing MUST be denied in non-test code. |
| **Q-R13** | Lint suppressions MUST NOT appear in `src/`; an architecture test MUST fail on their presence. |
| **Q-R14** | Rule changes MUST be at the crate root with a documented reason, never inline. |
| **Q-R15** | Library errors MUST be typed and matchable; every user-facing variant MUST carry a remedy. |
| **Q-R16** | A user-facing error variant without a remedy MUST NOT compile. |
| **Q-R17** | The MSRV MUST be pinned and built in CI. |
| **Q-R18** | Module boundary rules MUST be asserted by an architecture test. |
| **Q-R19** | `rustfmt` and the full lint set MUST pass in CI. |
| **Q-R20** | Public items MUST be documented (`missing_docs` denied). |

## Related

- [code-comments.md](code-comments.md) — the comment half of the same posture
- [testing-strategy.md](testing-strategy.md) · [ci-cd.md](ci-cd.md)
- [component-model](../20-architecture/component-model.md) — the boundaries enforced here
- [G4 Error model](../10-functional/features/g-ux/g4-error-model.md)
