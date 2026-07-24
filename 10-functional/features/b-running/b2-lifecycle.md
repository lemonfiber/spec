# B2 — Lifecycle control

**Status:** Accepted · **Audience:** Operator · **Area:** B — Running it

---

## Purpose

Start, stop, restart and inspect the stack — whole forms or individual services —
without the operator needing to know Docker.

This is the most-used feature in the product. It must be fast, predictable, and
honest about what actually happened. "Started" must mean the thing is *usable*,
not merely that a container process exists.

## Behaviour

### Starting is health-gated, not process-gated

A container reaching "running" says nothing about whether the application inside
it has finished initialising. The \*arrs take several seconds to open their
databases and bind their ports; Jellyfin takes longer on first run.

Starting therefore waits for each service to report **healthy**, and reports
progress per service. An operator told "started" who then gets connection refused
has been lied to.

### Every operation states what it will affect before doing it

Stopping `hunt` while `tv` is also running stops six services, four of which
`tv` still needs. The operator sees the affected list first.

### Individual services are addressable

Restarting one wedged service must not require restarting the form. Operations
apply to a form, a list of services, or everything.

### Operations are idempotent

Starting an already-running form is a no-op that reports as such, not an error
and not a restart. Stopping something already stopped likewise.

### Order is derived, not configured

Because [no `depends_on` crosses a profile boundary](../../../00-overview/decisions/0002-profiles-and-forms.md),
services can start in any order. Where genuine ordering exists — qBittorrent
requiring Gluetun's network namespace — it lives within a single profile and is
handled by Compose.

The corollary matters for stopping: the VPN must be stopped **last**, since
tearing down Gluetun first would drop qBittorrent's networking out from under it.

### The underlying command is always inspectable

`--dry-run` prints the exact `docker compose` invocation without executing it.
This serves debugging, learning, and the operator who wants to run it themselves
([ADR-0001](../../../00-overview/decisions/0001-docker-compose-as-engine.md)).

### Status answers "is it working", not "is it running"

Per-service status distinguishes: not created, created but stopped, starting,
healthy, unhealthy, restart-looping, and stopped-with-error. "Up" is not a
status — it's an ambiguity. See [G7](../g-ux/g7-health-summary.md) for the
one-line rollup.

## States

Per service:

| State | Meaning |
|-------|---------|
| `absent` | No container exists |
| `stopped` | Exists, not running |
| `starting` | Running, health check not yet passing |
| `healthy` | Running and passing health checks |
| `unhealthy` | Running but failing health checks |
| `crash-looping` | Repeatedly exiting and restarting |
| `failed` | Exited non-zero and not restarting |

Per form: `inactive`, `partial` (some services healthy), `active` (all healthy),
`degraded` (running with at least one failure).

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Docker daemon unreachable | Detect before attempting anything; distinguish from "container failed to start". |
| Service never becomes healthy | Bounded wait, then report the timeout with that service's last log lines inline. Don't hang forever, don't silently give up. |
| Service crash-loops | Detect the loop rather than reporting "starting" indefinitely. Show the exit code and recent logs. |
| Stopping while downloads are active | Report what's in flight and offer to wait. SABnzbd and qBittorrent both resume, but the operator should choose knowingly. |
| Port conflict on start | Name the port, the service, and the conflicting process where the OS allows. |
| Image missing locally | Pull it, with progress. Don't fail with "no such image". |
| Image pull fails | Report which image and why; leave already-started services running. |
| Stopping a shared service | Refuse if another active form requires it; name that form. |
| Gluetun stopped while qBittorrent runs | Stop qBittorrent first. Ordering within the `torrent` profile is enforced. |
| Restart requested for a native-mode Jellyfin | Report that it's host-managed and print the platform-specific command; do not attempt to control the OS service manager. |
| Operation issued while another is in progress | Serialise. Report that an operation is running rather than racing. |
| Disk full at start | Detect and report as a disk problem, not a container failure — the remedies are entirely different. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **B2-R1** | Starting MUST wait for health, not merely for the container to run, before reporting success. |
| **B2-R2** | Per-service progress MUST be shown during start. |
| **B2-R3** | Every operation MUST list the services it will affect before acting. |
| **B2-R4** | Operations MUST be addressable to a form, a service list, or everything. |
| **B2-R5** | Operations MUST be idempotent, and a no-op MUST report as such rather than erroring. |
| **B2-R6** | Stopping MUST stop the VPN last where a download client depends on its network namespace. |
| **B2-R7** | Stopping a service still required by another active form MUST be refused, naming that form. |
| **B2-R8** | A service that fails to become healthy MUST time out within a bounded period and MUST surface its recent logs. |
| **B2-R9** | Crash-looping MUST be reported distinctly from `starting`. |
| **B2-R10** | Status MUST distinguish at minimum: absent, stopped, starting, healthy, unhealthy, crash-looping, failed. |
| **B2-R11** | `--dry-run` MUST print the exact underlying command without executing it. |
| **B2-R12** | Missing images MUST be pulled with visible progress rather than producing an error. |
| **B2-R13** | Stopping with active downloads MUST report them and offer to wait. |
| **B2-R14** | Concurrent lifecycle operations MUST be serialised, not raced. |
| **B2-R15** | Native-mode Jellyfin MUST report as host-managed and MUST NOT be started or stopped by lemonfiber. |

## Related

- [B1 Forms](b1-forms.md) — what a lifecycle operation applies to
- [B3 Dashboard](b3-dashboard.md) — where state is observed
- [B8 Autostart](b8-autostart.md) — lifecycle across reboots
- [G7 Health summary](../g-ux/g7-health-summary.md) — the one-line rollup
