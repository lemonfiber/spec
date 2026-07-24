# ADR-0004: Four repos rather than a monorepo

**Status:** Accepted
**Date:** 2026-07-24

## Context

The project produces four artifacts: a specification, a Rust binary, a set of
Compose/config files, and Homebrew formulae. These could live in one repo with
directories, or in separate repos under the `lemonfiber` org.

Two facts constrain the choice:

1. **Homebrew formulae must live in their own repo.** A tap *is* a repo named
   `homebrew-<name>`. This isn't a preference; it's how `brew tap` works. So the
   floor is two repos regardless.
2. **The artifacts have genuinely different change rates and review styles.**
   The spec changes on decisions. The stack changes when a service is added or a
   pinned image bumps — reviewed by reading YAML. lemonfiber changes constantly during
   development — reviewed by reading Rust, with tests and a CI matrix.

## Decision

Four repos:

| Repo | Contents | Changes when | Reviewed by |
|------|----------|--------------|-------------|
| `spec` | This specification | A decision is made | Reading prose |
| `cli` | Rust CLI/TUI (the `lemonfiber` binary) | Feature work | Reading Rust + CI |
| `media-stack` | `compose.yml`, `stack.toml`, service configs, overlays | A service changes | Reading YAML |
| `homebrew-tap` | Formulae (generated) | Every release | Nothing — it's generated |

`media-stack` enters `cli` as a **git submodule**, embedded at build time —
see [ADR-0005](0005-embedded-stack-assets.md).

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Monorepo + separate tap** | The most defensible alternative, and normally I'd favour it. Lost on a specific product goal: `media-stack` must be independently forkable and usable *without lemonfiber* (see ADR-0001). A directory inside a Rust repo signals "implementation detail"; a repo signals "artifact you can use." |
| **Two repos** (`lemonfiber` incl. stack, + tap) | Loses the independent-fork property entirely. |
| **Five+** (splitting docs from spec, etc.) | No benefit; more coordination overhead. |

## Consequences

### Positive
- `media-stack` can be cloned and run with plain `docker compose` by someone who
  has never heard of lemonfiber. This is a real hedge: if lemonfiber stagnates, the stack
  still works.
- Each repo gets CI proportionate to its risk. `media-stack` needs
  `docker compose config` validation and a lint; `lemonfiber` needs a three-platform
  build matrix. Merged, everything pays the expensive cost.
- Issues land in the right place without triage.
- The spec is citable and versioned independently of any implementation.

### Negative
- **Version skew is now possible** — the central risk this split introduces. A
  change spanning lemonfiber and media-stack requires two PRs, and a user could pair
  incompatible versions. Mitigated by the `schema_version` contract in
  `stack.toml` ([versioning](../../20-architecture/contracts/versioning.md)) and,
  because the stack is embedded at build time, largely converted into a
  *compile-time* error rather than a runtime one.
- Cross-repo changes need coordination. Real cost, accepted.
- Four sets of CI config, licence files, and issue templates to keep aligned.

### Neutral
- The submodule pin makes "which stack version does lemonfiber v0.4 ship?" precisely
  answerable — arguably better than a monorepo, where the answer is implicit.

## Revisit if

- Cross-repo coordination overhead visibly slows development.
- The independent-usability property of `media-stack` turns out not to matter to
  anyone in practice.
