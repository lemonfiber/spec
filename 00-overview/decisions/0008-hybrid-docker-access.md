# ADR-0008: Compose CLI for writes, Docker API for reads

**Status:** Accepted
**Date:** 2026-07-24

## Context

[ADR-0001](0001-docker-compose-as-engine.md) settled that Compose is the
execution engine. That answers *how containers start*, but not *how the live
dashboard gets its data*.

The dashboard refreshes ~every second and needs container state, CPU/memory,
network throughput, and streaming logs. Two options:

**Shell out for everything.** Every refresh spawns `docker compose ps --format
json`, plus `docker stats --no-stream`, plus a `docker logs -f` per service.
Process spawn on Windows costs tens of milliseconds; at 1 Hz across 16 services
this is both wasteful and jittery. Streaming logs through subprocess pipes means
managing child lifetimes, and stats via CLI is a poll rather than a stream.

**Use the Docker API for everything.** Structured, streaming, cheap — but the
API has no concept of Compose profiles, so the write path would mean
reimplementing Compose (rejected in ADR-0001).

The two paths have genuinely different requirements, and there's no reason they
must use the same mechanism.

## Decision

**Split by direction.**

| Direction | Mechanism | Operations |
|-----------|-----------|------------|
| **Writes** (state changes) | `docker compose` subprocess | `up`, `down`, `restart`, `pull`, `stop`, `config` |
| **Reads** (observation) | Docker Engine API via `bollard` | container list/inspect, stats stream, log stream, `exec` |

The seam is enforced by module boundaries: `stack::compose` may spawn processes
but never touches bollard; `docker::*` uses bollard but never spawns.

Correlation between the two uses Compose's standard labels, which the Engine API
exposes on every container:

- `com.docker.compose.project`
- `com.docker.compose.service`

So lemonfiber lists containers by project label and maps them back to manifest
services without shelling out.

The `exec` path matters specifically for the VPN leak test — running
`wget -qO- https://ifconfig.me` inside both `gluetun` and `qbittorrent` and
comparing results. Via bollard this is a clean streamed API call.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Subprocess for everything** | Process spawn per refresh is slow (notably on Windows), stats becomes polling rather than streaming, and log tailing requires child-process babysitting. |
| **Docker API for everything** | Requires reimplementing profile semantics — explicitly rejected in ADR-0001. |
| **`docker compose watch` / events** | Useful as a change signal, but doesn't provide stats or logs. May be added later as an optimisation to reduce poll frequency. |

## Consequences

### Positive
- Dashboard refreshes are cheap: one API connection, streamed, no process churn.
- Logs and stats arrive as async streams that map naturally onto tokio tasks
  feeding the render loop.
- Write path stays debuggable — lemonfiber logs the literal `docker compose` command,
  and the user can run it themselves.
- Clean testing seam: reads and writes are separately mockable, so most of lemonfiber
  is testable without a Docker daemon.

### Negative
- Two Docker access mechanisms to understand and keep working. Real complexity;
  justified by the performance difference on the hot path.
- `bollard` must negotiate an API version compatible with the user's daemon.
  Handled by version negotiation at startup, with a clear error on mismatch.
- On Windows, the API is reached over a named pipe rather than a Unix socket —
  `bollard` handles this, but it's an extra platform-specific path to test.

### Neutral
- If `bollard` cannot connect but the CLI works, lemonfiber degrades to a
  reduced-functionality mode: control still works, live telemetry is disabled
  with an explanatory banner rather than a crash.

## Revisit if

- `bollard` proves unreliable across daemon versions.
- Compose exposes a stable structured status/stream API, collapsing the split.
