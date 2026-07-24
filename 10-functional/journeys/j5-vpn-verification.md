# J5 — Verifying the VPN isn't leaking

**Status:** Accepted · **Audience:** Operator

**Exercises:** [C1](../features/c-trust/c1-diagnostics.md) ·
[C2](../features/c-trust/c2-vpn-verification.md)

---

## The journey

```
$ lemonfiber doctor --only vpn

  ✓ gluetun tunnel up            185.65.x.x  (NL, ProtonVPN)
  ✓ qbittorrent egress matches   185.65.x.x  ← proves isolation
  ✓ forwarded port assigned      51413
  ✓ qbittorrent listen_port      51413  (matches)
  ✗ killswitch                   UNVERIFIED

    The killswitch has not been tested. Proving it works requires
    dropping the tunnel and confirming traffic stops.

    → lemonfiber doctor --only vpn --disruptive
      Takes about 10 seconds and will interrupt active torrents.
```

## Why this is the journey that matters most

It's the only one whose failure has consequences **outside the machine**. Every
other silent failure in this product costs disk, time or patience. This one
exposes the operator's home IP to every peer in a swarm.

It's also genuinely hard to verify by hand. A running Gluetun container proves
nothing about qBittorrent's traffic. Checking your IP in a browser tells you about
the browser. The operator has no practical way to confirm the thing that matters —
so they assume, which is exactly what
[P3](../../00-overview/vision.md#p3--the-tool-proves-things-rather-than-assuming-them)
forbids.

## How the core check works

Ask **Gluetun** its public IP. Ask **qBittorrent**, from inside its own network
namespace, the same question. Compare.

| Result | Meaning |
|--------|---------|
| Same non-home IP | Traffic genuinely traverses the tunnel |
| qBittorrent reports the home IP | **Leaking.** Critical. |
| qBittorrent has no connectivity | Killswitch holding — tunnel down, not leaking |
| Two different non-home IPs | Misconfiguration; traffic taking an unexpected path |

This works because qBittorrent shares Gluetun's network namespace. If the sharing
is intact the answers *must* match; if it broke, the difference is immediately
visible (`C2-R1`).

## Why `UNVERIFIED` is not a failure — and not a pass

The killswitch line reports `UNVERIFIED`, not green. It hasn't been tested,
because testing it means deliberately breaking the tunnel and interrupting
transfers.

**Reporting it as passing would be exactly the comfortable falsehood this product
exists to eliminate** (`C2-R7`). An untested fail-closed guarantee is not a
guarantee — it's an assumption wearing a tick mark.

## Not every provider can do this

The port checks above only apply where the provider offers port forwarding —
ProtonVPN, PIA, PrivateVPN and Perfect Privacy. On NordVPN, Mullvad, Surfshark
and most others, there is no forwarded port to check.

On those, the port lines report **`not-applicable`**, and the overall state is
`verified-no-pf` — green, not amber (`C2-R16`). Nothing is broken; the operator
bought a product without that feature, and the consequence was stated once when
they chose it (`A1-R12`).

## The port lifecycle, where it applies

Four things must hold, checked separately because each fails differently (`C2-R4`):

1. A port was granted at all.
2. qBittorrent is listening on **that** port.
3. It's actually reachable.
4. It still matches **after a reconnect**.

Point 4 is the one that bites. The ProtonVPN forwarded port **does not survive a
reconnect**, and a reboot is a reconnect. Without this check the stack comes back
looking perfectly healthy while listening on a port the VPN no longer forwards —
everything green, incoming connections silently gone.

## Continuous, not just on demand

Egress matching is re-checked while torrents are active. A leak beginning after
startup is still a leak, and notifies immediately at critical severity
(`C2-R10`).

## Related

- [J3 Download only](j3-download-only.md) — where the VPN first appears
- [C2 VPN verification](../features/c-trust/c2-vpn-verification.md)
- [B8 Autostart](../features/b-running/b8-autostart.md) — post-reboot re-acquisition
