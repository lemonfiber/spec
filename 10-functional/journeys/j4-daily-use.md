# J4 — Daily use

**Status:** Accepted · **Audience:** Operator

**Exercises:** [B3](../features/b-running/b3-dashboard.md) ·
[B4](../features/b-running/b4-logs.md) ·
[G7](../features/g-ux/g7-health-summary.md)

---

## The journey

```
$ lemonfiber
```

Bare invocation with configuration present opens the dashboard (`B3-R1`). No
subcommand to remember, because this is what the operator does most.

```
  ✓ Everything's fine · 12 services · 3 downloading · 480 GB free

  VPN        185.65.x.x (NL) · port 51413 · egress matches ✓
  Transfers  The Expanse S04E03   ▓▓▓▓▓▓▓░░░  71%   14 MB/s   2m
             Dune Part Two        ▓▓░░░░░░░░  18%    8 MB/s  21m
  Queue      sonarr 4 · radarr 1 · lidarr 0
  Storage    480 GB free · hardlinks ✓ · ~26 days at current rate
  Services   12 healthy
```

## What the top line is doing

`Everything's fine` is not a count of running containers. It's computed from the
findings that actually affect the operator — VPN state, queue health, provider
capacity, disk, hardlink status (`G7-R2`).

**A stack with all twelve containers up and a leaking VPN does not say
"everything's fine"** (`G7-R4`). That distinction is the entire reason the
summary exists rather than a service count.

The healthy case matters as much as the unhealthy one. An operator who can glance
and be reassured stops checking obsessively — which is what makes a self-hosted
system tolerable to live with long-term.

## Why the VPN row sits second

Above transfers, deliberately: it's the only item on screen with consequences
outside the machine.

## The figures no single service knows

Three lines above are things no component can report on its own, and they're the
dashboard's real justification:

| Figure | Why it needs a cross-service view |
|--------|-----------------------------------|
| `egress matches ✓` | Compares public IP observed inside qBittorrent against Gluetun's |
| `hardlinks ✓` | Whether imports are linking or copying — otherwise invisible |
| `~26 days at current rate` | Free space projected against queued content |

## Going deeper

| Want | Action |
|------|--------|
| Why is something slow? | Logs, filtered — multiple services interleaved (`B4-R1`) |
| Why did an import fail? | Sonarr's and SABnzbd's lines side by side, which is the only way it's explicable |
| What's wrong? | The summary expands to affected items and their remedies (`G7-R7`) |

## Degrading honestly

If the telemetry channel drops but control still works, the dashboard says so and
stays open (`B3-R7`). Affected panels are marked; the rest stay live.

**Stale, unknown and zero are rendered differently** (`B3-R5`). `0 B/s` and
`unknown` mean opposite things to someone deciding whether a download is stuck.

## Related

- [J5 VPN verification](j5-vpn-verification.md) — when the VPN row looks wrong
- [J7 Upgrading](j7-upgrading.md) — when an update is available
- [G7 Health summary](../features/g-ux/g7-health-summary.md)
