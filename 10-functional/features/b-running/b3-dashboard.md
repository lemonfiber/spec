---
id: B3
title: Live dashboard
kind: feature
area: B
audience: operator
status: accepted
tracks: v1
labels: [tui, verification]
requires: [G7]
relates: [B2, B4, C2, G1]
---

# B3 — Live dashboard

**Status:** Accepted · **Audience:** Operator · **Area:** B — Running it

---

## Purpose

One screen that answers "what is my stack doing right now?"

Without it, the answer requires opening six web UIs: SABnzbd for Usenet
progress, qBittorrent for torrents, Sonarr for the queue, Gluetun's logs for VPN
state, and a terminal for disk usage. Each holds one fragment; nobody holds the
whole picture.

The dashboard's value is precisely the fragments **no single service can
provide** — that qBittorrent's traffic is genuinely leaving via the tunnel, that
imports are hardlinking rather than copying, that the disk will fill before the
queue drains.

## Behaviour

### It opens by default

Running `lemonfiber` with configuration present and no subcommand opens the
dashboard. It is the product's front door for the operator.

### Content, in priority order

Ordered by what the operator needs to see first, not by what's easiest to render:

| Section | Shows |
|---------|-------|
| **Health summary** | One line: everything fine, or *n* things need attention ([G7](../g-ux/g7-health-summary.md)) |
| **VPN** | Tunnel state, exit IP and country, forwarded port, and whether the download client's egress matches |
| **Transfers** | Active downloads with name, protocol, progress, speed, ETA |
| **Queue** | Per-\*arr queue depth, plus anything stuck ([C7](../c-trust/c7-queue-health.md)) |
| **Storage** | Free space, projected exhaustion, hardlink status |
| **Services** | Per-service state, grouped by profile |

The VPN row is placed second, above transfers, deliberately: it is the only item
on the screen with consequences outside the machine.

### It refreshes without blocking

The view updates about once a second. Input remains responsive during image
pulls, log streaming and slow API calls. A dashboard that freezes while polling
is worse than a static status command.

### It degrades honestly

If live telemetry is unavailable — the Docker API unreachable while the CLI still
works, or an \*arr not responding — the affected panel says so explicitly rather
than showing stale data as current or blank data as zero.

**Stale, unknown, and zero are three different things** and must never be
rendered identically. "0 B/s" and "unknown" mean opposite things to someone
deciding whether their download is stuck.

### It shows figures no service knows

- **Egress comparison** — the download client's public IP against the VPN's
- **Hardlink status** — whether imports are linking or copying
- **Projected disk exhaustion** — free space against queued content size
- **Cross-service stalls** — downloaded but never imported

### Panels are addressable

The operator can view any panel alone, for a narrow terminal or a focused
question.

## States

| State | Meaning |
|-------|---------|
| `live` | Telemetry current, refreshing normally |
| `degraded` | Some sources unavailable; affected panels marked |
| `disconnected` | Docker API unreachable; control may still work via the CLI path |
| `no-stack` | Configured but nothing running; offers to start a form |
| `unconfigured` | No configuration; offers [setup](../a-getting-started/a2-setup-wizard.md) |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Docker API unavailable, CLI path working | Enter `disconnected`, state that telemetry is off but control still works. Don't exit. |
| A service's API unreachable | Mark that panel unavailable; leave the rest live. One failure must not blank the screen. |
| Terminal too narrow | Degrade gracefully: drop columns by priority, never truncate mid-value or corrupt the layout. |
| Terminal resized | Reflow without restarting or losing scroll position. |
| No downloads active | Say "no active transfers", not an empty box. Absence of data is information. |
| Very large queue | Show the top *n* by relevance with a total count. Never attempt to render thousands of rows. |
| VPN not configured | Omit the VPN panel entirely rather than showing a permanently red one. |
| Native-mode Jellyfin | Show it, marked host-managed, with health if reachable. |
| Data unchanged between refreshes | Don't redraw unnecessarily; avoid flicker. |
| Very long service or release names | Truncate with an unambiguous marker; full value available on focus. |
| Running over SSH on a slow link | Reduce refresh rate rather than saturating the connection. |
| Clock skew between host and containers | Compute durations from a single clock source; never render a negative ETA. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **B3-R1** | Invoking lemonfiber with configuration present and no subcommand MUST open the dashboard. |
| **B3-R2** | The dashboard MUST show health summary, VPN state, transfers, queue depth, storage and service states. |
| **B3-R3** | VPN state MUST include exit IP, country, forwarded port, and egress-match confirmation. |
| **B3-R4** | Refresh MUST NOT block user input. |
| **B3-R5** | Stale, unknown and zero values MUST be visually distinct. |
| **B3-R6** | An unavailable data source MUST mark only its own panel, leaving others live. |
| **B3-R7** | Loss of the telemetry channel MUST NOT terminate the dashboard, and MUST be stated. |
| **B3-R8** | The dashboard MUST show hardlink status and projected disk exhaustion. |
| **B3-R9** | Narrow terminals MUST degrade by dropping lower-priority columns, never by corrupting layout. |
| **B3-R10** | Resizing MUST reflow without restart or loss of scroll position. |
| **B3-R11** | Absent data MUST be stated explicitly rather than rendered as an empty region. |
| **B3-R12** | Large collections MUST be truncated with a total count shown. |
| **B3-R13** | Any panel MUST be viewable in isolation. |
| **B3-R14** | Idle refresh MUST sustain 1 Hz below 2% CPU, and lemonfiber's resident memory SHOULD stay under 50 MB. |
| **B3-R15** | Durations and ETAs MUST derive from one clock source and MUST never render negative. |

## Related

- [B2 Lifecycle](b2-lifecycle.md) — the state being displayed
- [B4 Log viewing](b4-logs.md) — drilling into a specific service
- [C2 VPN verification](../c-trust/c2-vpn-verification.md) — the egress comparison
- [G1 Interface tiers](../g-ux/g1-interface-tiers.md) — TUI and web rendering
- [G7 Health summary](../g-ux/g7-health-summary.md)
