---
id: C2
title: VPN verification
kind: feature
area: C
audience: operator
status: accepted
tracks: v1
milestone: M3
labels: [vpn, network, verification]
depends: [A3, B5, B8, C1]
---

# C2 — VPN verification

**Status:** Accepted · **Audience:** Operator · **Area:** C — Trust & correctness

---

## Purpose

Prove that torrent traffic is actually leaving through the tunnel.

This is the only feature in the catalogue whose failure has consequences outside
the machine. Every other silent failure costs disk, time, or patience. This one
exposes the operator's home IP address to every peer in a swarm.

And it is genuinely hard to verify by hand. A running Gluetun container proves
nothing about qBittorrent's traffic. Checking your IP in a browser tells you about
the *browser*. The operator has no practical way to confirm the thing that
matters, so they assume — and assumption is exactly what
[P3](../../../00-overview/vision.md#p3--the-tool-proves-things-rather-than-assuming-them)
forbids.

## Behaviour

### The core check: compare egress from inside both containers

Ask **Gluetun** what its public IP is. Ask **qBittorrent**, from inside its own
network namespace, the same question. Compare.

| Observation | Meaning |
|-------------|---------|
| Both report the same non-home IP | Traffic is genuinely traversing the tunnel |
| qBittorrent reports the host's real IP | **Leaking.** Critical failure. |
| qBittorrent has no connectivity | Killswitch is holding — tunnel down but not leaking |
| The two differ, both non-home | Misconfiguration; traffic is taking an unexpected path |

This works because qBittorrent shares Gluetun's network namespace. If that
sharing is intact, the answers must match; if it isn't, the difference is
immediately visible.

### Providers are described by capability, not by name

lemonfiber supports every VPN provider the tunnel container supports — around
two dozen. They are **not** equivalent, and the differences are not cosmetic:

| Capability | Providers |
|------------|-----------|
| Tunnel, killswitch, egress verification | **All** |
| **Server-side port forwarding** | ProtonVPN, Private Internet Access, PrivateVPN, Perfect Privacy |

Everything else — NordVPN, Mullvad, Surfshark, AirVPN, Windscribe and the rest —
has **no port forwarding at all**. NordVPN discontinued it; Mullvad withdrew it
in 2023.

This is why capability, not provider name, is the unit. A spec written around one
provider would either exclude most users or report a permanent false failure for
them.

### Where port forwarding is unavailable, checks are *not applicable* — never failed

On a provider without port forwarding, the port checks do not run and report
`not-applicable`. Reporting them as failures would be wrong: nothing is broken,
and an operator cannot fix a capability their provider does not offer.

What lemonfiber does instead is state the consequence **once, at setup**: without
a forwarded port, peers cannot initiate connections, so torrent throughput and
seeding are both reduced. That is a real trade-off the operator should make
knowingly — and it is a reason to choose one provider over another, which is
useful precisely when they are choosing.

### The forwarded-port lifecycle, where the provider supports it

Four things must hold, each checked separately because each fails differently:

1. A port was granted at all.
2. The download client is configured to listen on **that** port.
3. The port is actually reachable.
4. It still matches after any reconnect.

Point 4 is the one that bites. **The forwarded port does not survive a
reconnect**, and a reboot is a reconnect. Without this check the stack comes back
looking perfectly healthy while the client listens on a port the VPN no longer
forwards — everything green, incoming connections silently gone.

There is a second, subtler trap: the download client must also be *reset* when
the tunnel drops, or it will not re-acquire correctly on reconnect. Both the
acquire and the release path must be wired, not just the acquire.

### Provider-specific traps are named, because they are not guessable

Each provider has one failure that looks like a broken installation and is
actually a credential problem — and no provider explains it at the point of
failure:

| Provider | The trap |
|----------|----------|
| **ProtonVPN** | Port forwarding must be enabled **when the WireGuard configuration is generated**, and the server must support P2P. Not fixable at runtime — it requires generating new credentials. |
| **NordVPN** | Credentials are **service credentials** from the account dashboard, *not* the account email and password. The obvious values are rejected with no explanation. |

Where the tunnel is up but no port was granted on a port-forwarding provider,
that provider's trap is named as the first candidate cause.

### Killswitch verification is opt-in and honestly reported

The only way to prove a killswitch works is to break the tunnel and confirm
traffic stops. That interrupts active transfers, so it is never part of a default
run.

Until it has been run, the killswitch reports **`unverified`** — not `pass`.
Claiming an untested fail-closed guarantee would be precisely the kind of
comfortable falsehood this feature exists to eliminate.

### Continuous, not just on demand

Egress matching is re-checked periodically while torrents are active. A leak that
begins after startup is still a leak, and the operator is notified immediately
([B5](../b-running/b5-notifications.md), critical severity).

### Exit location is reported

Not a pass/fail, but frequently not what the operator intended — and it affects
speed and, for some, legality.

## States

| State | Meaning |
|-------|---------|
| `verified` | Tunnel up, egress matches, and — where supported — port granted and matching |
| `verified-no-pf` | Tunnel up and egress matches; provider offers no port forwarding. **Not degraded.** |
| `degraded` | Provider supports port forwarding, but none granted or the port mismatches |
| `killswitch-holding` | Tunnel down; download client has no connectivity. Safe. |
| `leaking` | Download client's egress does not match the tunnel. **Critical.** |
| `unverified` | Could not be checked |
| `not-configured` | No VPN configured; torrents disabled or accepted without one |

`verified-no-pf` exists so a NordVPN or Mullvad operator sees a green state
rather than a permanent amber one. Their tunnel is working correctly; they simply
bought a product without that feature.

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| IP-echo service unreachable from both containers | `unverified`, not `pass`. Loss of the oracle is not evidence of safety. |
| IP-echo reachable from one container only | Strong signal. Report as a probable leak or probable killswitch depending on which. |
| Tunnel up, no forwarded port, **provider supports it** | `degraded`, naming that provider's trap as the first candidate cause. |
| Tunnel up, no forwarded port, **provider does not support it** | `verified-no-pf`. Port checks report `not-applicable`. Never a failure. |
| Provider capability unknown to lemonfiber | Attempt port acquisition once; on failure report `unverified` for port checks rather than assuming either way. |
| Operator changes provider to one without port forwarding | Detect the capability change and state that seeding performance will drop, rather than silently reporting `not-applicable`. |
| Tunnel drops without the client being reset | The client will not re-acquire correctly on reconnect. Both release and acquire paths MUST be wired. |
| Port granted but client not updated | `degraded` — re-push the port and report that it had drifted. |
| Port changed after reconnect | Detect, re-push, and record. Do not wait for the operator. |
| VPN configured but torrents not in the active form | `skipped`, not a failure. |
| Operator declined a VPN | `not-configured`. Report their acknowledged exposure without repeating the warning every run. |
| Exit country differs from the configured preference | Report; not a failure. |
| Killswitch test requested with active transfers | Warn, state the duration, require confirmation. |
| Killswitch test leaves the tunnel down | Restore the previous state and verify restoration before reporting. |
| Multiple IP-echo sources disagree | Prefer agreement of two; report inconsistency rather than picking one. |
| Gluetun healthy but qBittorrent not sharing its namespace | This is the misconfiguration the check exists to catch. Report as `leaking` with the network mode named. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **C2-R1** | Verification MUST compare public IP observed from inside the download client's namespace against the VPN container's. |
| **C2-R2** | A mismatch between the download client's egress and the tunnel MUST be reported as `leaking` at critical severity. |
| **C2-R3** | Inability to reach an IP-echo source MUST report `unverified`, never `pass`. |
| **C2-R4** | Forwarded-port assignment, client configuration, reachability and post-reconnect match MUST each be checked separately. |
| **C2-R5** | A forwarded port that changed MUST be re-pushed to the download client automatically and the change recorded. |
| **C2-R6** | When the tunnel is up but no port was granted on a port-forwarding-capable provider, that provider's known trap MUST be named as the first candidate cause. |
| **C2-R15** | Providers MUST be modelled by capability, not by name; support MUST NOT be limited to an enumerated provider list. |
| **C2-R16** | Where the provider does not support port forwarding, port checks MUST report `not-applicable` and MUST NOT report as failed or degraded. |
| **C2-R17** | The consequence of running without a forwarded port — reduced peer connectivity and seeding — MUST be stated once at setup, and MUST NOT be repeated as a recurring warning. |
| **C2-R18** | Where a provider's capability is unknown, port checks MUST report `unverified` rather than assuming presence or absence. |
| **C2-R19** | Both the port-acquire and port-release paths MUST be wired, so the client re-acquires correctly after a tunnel drop. |
| **C2-R20** | Changing to a provider without port forwarding MUST state the resulting loss of seeding performance. |
| **C2-R7** | Killswitch verification MUST be opt-in and MUST report `unverified` until it has been run. |
| **C2-R8** | Killswitch verification MUST restore the prior state and MUST verify restoration before reporting. |
| **C2-R9** | Egress matching MUST be re-checked periodically while torrent transfers are active. |
| **C2-R10** | A leak detected after startup MUST notify immediately at critical severity. |
| **C2-R11** | The VPN exit country MUST be reported. |
| **C2-R12** | A download client not sharing the VPN's network namespace MUST be reported as `leaking`, naming the network mode. |
| **C2-R13** | Where the VPN is unconfigured by acknowledged choice, lemonfiber MUST NOT repeat the warning on every run. |
| **C2-R14** | Disagreement between IP-echo sources MUST be reported rather than resolved arbitrarily. |

## Related

- [C1 Diagnostics](c1-diagnostics.md) — the framework this runs within
- [A3 Credential validation](../a-getting-started/a3-credential-validation.md) — initial VPN validation
- [B8 Autostart](../b-running/b8-autostart.md) — post-reboot port re-acquisition
- [B5 Notifications](../b-running/b5-notifications.md)
- [J5 VPN verification](../../journeys/j5-vpn-verification.md)
