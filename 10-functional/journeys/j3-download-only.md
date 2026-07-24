# J3 — "I have a link — just fetch it"

**Status:** Accepted · **Audience:** Operator

**Exercises:** [B1](../features/b-running/b1-forms.md) ·
[B2](../features/b-running/b2-lifecycle.md) ·
[C2](../features/c-trust/c2-vpn-verification.md)

---

## The journey

```
$ lemonfiber up dl

  ✓ sabnzbd       healthy    http://localhost:8085
  ✓ gluetun       healthy    VPN: 185.65.x.x (NL) · port 51413
  ✓ qbittorrent   healthy    http://localhost:8081

  3 services · 2 profiles
```

Downloaders only. No indexers, no automation, no library.

## Why the VPN line is on screen

A torrent client without a forwarded port works — badly. Peers can't initiate
connections, so throughput and seeding both suffer, and nothing anywhere reports
a problem.

Showing the exit IP and forwarded port by default means the degraded case is
visible immediately rather than after weeks of wondering why torrents are slow
(`C2-R4`).

## Protocol filtering

`dl` expands to `usenet` + `torrent`, but the closure is **intersected with what
the operator configured** (`B1-R4`).

| Configured | `lemonfiber up dl` starts |
|------------|---------------------------|
| Usenet only | SABnzbd |
| Torrents only | Gluetun + qBittorrent |
| Both | All three |

Without this, every torrent-bearing form would fail for Usenet-only operators —
a large fraction of them — by trying to start Gluetun with credentials that don't
exist.

## Where it goes wrong

| Situation | Behaviour |
|-----------|-----------|
| VPN configured but tunnel won't come up | qBittorrent has no network — the killswitch holding, correctly. Reported as `killswitch-holding`, not as a leak (`C2-R7`). |
| Tunnel up, no forwarded port | `degraded`. Names the NAT-PMP-at-config-generation cause first. |
| qBittorrent's egress differs from Gluetun's | **`leaking`, critical.** Usually means the network namespace sharing broke (`C2-R12`). |
| Torrents chosen without a VPN | Permitted — it's their machine — but only after explicit acknowledgement at setup (`A1-R9`). |
| Stopping the form | qBittorrent stops **before** Gluetun; tearing down the tunnel first would drop networking from under it (`B2-R6`). |

## What this journey is for

Two real cases:

1. **A link from elsewhere** — someone sent an NZB or a magnet, and the full
   automation stack is irrelevant to fetching it.
2. **Isolating a problem.** When downloads misbehave, running only the
   downloaders removes every other variable. That diagnostic use is a direct
   consequence of forms being first-class.

## Related

- [J2 Search only](j2-search-only.md) — the complementary slice
- [J5 VPN verification](j5-vpn-verification.md) — proving the tunnel properly
- [C2 VPN verification](../features/c-trust/c2-vpn-verification.md)
