# ADR-0003: Rust + Ratatui for the CLI/TUI

**Status:** Accepted
**Date:** 2026-07-24

## Context

lemonfiber must run on macOS, Linux, and Windows, and must be trivially installable by
someone who is not a developer ("everyone can use it with ease"). That makes
**distribution the dominant constraint**, ahead of language preference.

A tempting argument for Go is that Docker is written in Go, so its SDK is
first-party. On inspection this mostly evaporates: per [ADR-0001](0001-docker-compose-as-engine.md)
we drive Compose via its CLI, and per [ADR-0008](0008-hybrid-docker-access.md)
the read path needs only container state and log streams — both of which have
solid clients in every candidate language. Go's home-field advantage doesn't
apply to the work we're actually doing.

## Decision

**Rust**, with:

| Concern | Crate |
|---------|-------|
| TUI | `ratatui` |
| Terminal backend | `crossterm` (strong Windows support, incl. legacy conhost) |
| CLI parsing | `clap` (derive) |
| Docker API (reads) | `bollard` |
| Async runtime | `tokio` |
| HTTP (Servarr APIs) | `reqwest` |
| Cross-platform paths | `directories` |
| Errors | `thiserror` (library) + `color-eyre` (binary) |
| Embedded assets | `include_dir` |
| Release engineering | `cargo-dist` |

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Go + Bubble Tea** | Genuinely close. Faster to a working TUI, simpler concurrency, `goreleaser` matches `cargo-dist`. Lost on: Ratatui's immediate-mode model fits a telemetry dashboard more directly than Elm's message plumbing, and Rust's type system gives stronger guarantees on the state machines (wizard steps, check results) that make up much of this program. A defensible coin-flip, decided by preference. |
| **Python + Textual** | Fastest to iterate and excellent for dashboards. Lost decisively on distribution: every end user needs Python or `uv` installed first, which directly contradicts the core goal. |
| **Node + Ink** | `npx` needs no install *if Node is present* — true for developers, false for the broader audience. Weakest of the three for dense terminal dashboards. |
| **Shell + `gum`** | Very low complexity, but cannot deliver a live dashboard, and Windows support is poor. |
| **Tauri / Electron GUI** | A GUI is a legitimate future direction, but a terminal-first tool suits the audience (people already in a shell running Docker) and is dramatically cheaper to ship on three platforms. |

## Consequences

### Positive
- Single static binary per platform; end users install nothing else.
  `cargo-dist` generates macOS (arm64 + x86_64), Linux (gnu + musl), and Windows
  artifacts, plus shell and PowerShell installers and the Homebrew tap.
- `crossterm` gives real Windows terminal support rather than a POSIX
  approximation.
- Exhaustive `match` over enums makes the wizard state machine and check results
  hard to get subtly wrong — a meaningful correctness win for
  [P3](../vision.md#p3--the-tool-proves-things-rather-than-assuming-them).
- No GC pauses in the render loop.

### Negative
- Slower compile times than Go; CI matrix builds are the long pole.
- `tokio` plus borrow-checker friction is real, particularly around sharing
  state between the render loop and background pollers. Mitigated by the
  message-passing architecture in [lemonfiber spec](../../30-repos/lemonfiber.md) — background
  tasks own their data and send snapshots, rather than sharing mutable state.
- `bollard` is a third-party client, not vendor-maintained. Acceptable: it's
  mature, and our usage is narrow (list, inspect, stats, logs, exec).

### Neutral
- Requires `rustup` for contributors. Standard for the ecosystem, and irrelevant
  to end users.

## Revisit if

- Compile times or the CI matrix become a genuine bottleneck.
- A GUI becomes the primary interface, at which point the calculus changes.
