# ADR-0005: lemonfiber embeds the stack at build time

**Status:** Accepted
**Date:** 2026-07-24

## Context

Given [ADR-0004](0004-four-repo-split.md), lemonfiber and media-stack are separate
repos — so lemonfiber needs the stack's files (`compose.yml`, `stack.toml`, service
configs, overlays) at runtime. How it obtains them determines the first-run
experience and the failure modes.

The first-run experience is the whole product thesis. Any step that can fail
before the user has anything working is disproportionately expensive.

## Decision

**The stack is a git submodule, embedded into the binary at compile time** via
`include_dir!`, and materialised to disk on first run.

```
lemonfiber/
├── assets/media-stack/     # git submodule, pinned to a tag
├── build.rs                # validates schema_version at COMPILE TIME
└── src/stack/embedded.rs   # include_dir!("assets/media-stack")
```

On `lemonfiber init`, files are written to the platform config directory
(`~/.config/lemonfiber/stack` on Linux, `~/Library/Application Support/…` on
macOS, `%APPDATA%\…` on Windows). A `--stack-dir <path>` flag overrides this
entirely, pointing at a local checkout for development or customisation.

`build.rs` parses the submodule's `stack.toml` and **fails the build** if its
`schema_version` isn't one this lemonfiber supports.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Fetch a release tarball on `init`** | Requires network at the worst possible moment — first run, before the user has any success. Adds TLS/proxy/rate-limit failure modes, and makes version skew a runtime error. |
| **`git clone` on `init`** | All of the above, plus requires git installed. Many Windows users don't have it. |
| **Ship stack files alongside the binary** (tarball/installer) | Breaks the single-file distribution promise, and `brew`/`scoop`/`curl \| sh` all become more complex. |
| **Read from a user-specified path only** | Zero-config first run becomes impossible; the user must obtain the stack themselves first. |

## Consequences

### Positive

- **First run needs no network and no git.** Download one binary, run it, get a
  working stack. This is the single biggest contributor to the setup-time goal.
- **Version skew becomes a compile error.** `build.rs` validates the contract at
  build time, so an incompatible pairing can never reach a user. This is the
  strongest available mitigation for ADR-0004's main downside.
- Reproducible: a given lemonfiber version always materialises byte-identical stack
  files, making bug reports meaningful.
- `--stack-dir` preserves full hackability — a power user can fork media-stack,
  point lemonfiber at it, and never rebuild.

### Negative

- **A stack fix requires a lemonfiber release.** The main cost. Accepted because stack
  changes are infrequent (a pinned image bump, a new service) and `--stack-dir`
  lets urgent cases be worked around immediately.
- Binary grows by the size of the stack files — a few hundred KB of text.
  Negligible.
- Contributors must remember `git submodule update --init`. Mitigated by a
  `build.rs` check that emits a clear error if `assets/media-stack` is empty,
  rather than a confusing `include_dir!` failure.

### Neutral

- Materialised files are user-editable. lemonfiber detects local modifications (by
  hash) and will not silently overwrite them on upgrade — it warns and offers a
  diff (`FR-032`).

## Revisit if

- Stack changes become frequent enough that release coupling is painful.
- Third-party stacks become a real use case, favouring a fetch-based plugin model.
