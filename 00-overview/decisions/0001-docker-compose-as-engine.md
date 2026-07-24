# ADR-0001: Docker Compose as the execution engine

**Status:** Accepted
**Date:** 2026-07-24

## Context

lemonfiber needs to start, stop, and inspect ~19 containers with varying subsets
active depending on the selected form. Three broad approaches exist: drive the
Docker Engine API directly, generate and invoke Compose, or target a heavier
orchestrator.

The complicating factor is **profiles**. The partial-stack requirement
([P2](../vision.md#p2--partial-stacks-are-first-class-not-degraded)) is
expressed naturally by Compose profiles, which are a *Compose CLI* concept — the
Docker Engine API has no notion of them. Reimplementing profile semantics
(including which services activate, dependency ordering, and network/volume
lifecycle) against the raw Engine API means reimplementing a meaningful chunk of
Compose itself.

## Decision

**Docker Compose v2 is the execution engine.** lemonfiber generates the correct
`docker compose` invocation (file list, profile flags, env) and shells out to it.

`compose.yml` is a real, human-readable file in `media-stack` that users can
read, fork, and run **without lemonfiber at all**.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Docker Engine API directly** (via bollard) | Would require reimplementing profiles, dependency ordering, and network lifecycle. Also loses the "run it without lemonfiber" escape hatch — the stack would only be operable through our binary, which is a lock-in we don't want. |
| **`compose-go` library, embedded** | Go-only, so unusable from Rust. Even in Go it's an internal-ish API with weak stability guarantees. |
| **Kubernetes / k3s** | Wildly disproportionate for a single-host desktop app. Would also make the Windows story far worse. |
| **Podman / Quadlet** | Interesting rootless story, but Docker Desktop is what the target audience already has on macOS and Windows. Supporting both multiplies the platform matrix without user benefit. |
| **Hand-rolled `docker run` orchestration** | Loses networks, dependency ordering, and declarative config. This is what Compose is *for*. |

## Consequences

### Positive
- Profiles come free, and they're exactly the primitive [P2](../vision.md#p2--partial-stacks-are-first-class-not-degraded) needs.
- `media-stack` is independently useful. Someone can clone it and run
  `docker compose --profile tv up` with no Rust toolchain involved. This is a
  real hedge against lemonfiber being abandoned.
- The compose file is reviewable by anyone who knows Compose — a far larger
  group than those who'd read our Rust.
- Debugging is tractable: lemonfiber logs the exact command it ran, and the user can
  paste it into a shell.

### Negative
- Requires the Compose v2 CLI plugin present on the host. Bundled with Docker
  Desktop, but a separate install on some Linux distros — so a preflight check
  is mandatory (`FR-011`).
- Subprocess invocation means parsing CLI output for errors, which is less
  structured than an API. Mitigated by `--format json` where available, and by
  ADR-0008's split (reads go through the API).
- Compose CLI behaviour can shift between versions. Mitigated by asserting a
  minimum version at startup.

### Neutral
- lemonfiber becomes, in part, a command builder. That logic is pure and highly
  testable — see the golden-file tests in
  [testing strategy](../../40-quality/testing-strategy.md).

## Revisit if

- Compose v2 is deprecated in favour of a stable, profile-aware API.
- Profile semantics prove insufficient for a required form.
- Rootless/daemonless operation becomes a hard requirement.
