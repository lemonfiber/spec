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

### The forwarded-port lifecycle is verified, not assumed

ProtonVPN assigns a forwarded port dynamically via NAT-PMP. Four things must all
hold, and each is checked separately because each fails differently:

1. A port was granted at all.
2. The download client is configured to listen on **that** port.
3. The port is actually reachable.
4. It still matches after any reconnect.

Point 4 is the one that bites. **The forwarded port does not survive a
reconnect**, and a reboot is a reconnect. Without this check the stack comes back
looking perfectly healthy while the client listens on a port the VPN no longer
forwards — everything green, incoming connections silently gone.

### The commonest failure is named first

If the tunnel is up but no port was granted, the overwhelmingly likely cause is
that **port forwarding was not enabled when the WireGuard configuration was
generated**, or the server doesn't support P2P. Neither is fixable at runtime;
both require going back to the provider's dashboard and generating new
credentials.

An operator will not guess this. It is stated as the first candidate cause.

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
| `verified` | Tunnel up, egress matches, port granted and matching |
| `degraded` | Tunnel up, but no forwarded port or a port mismatch |
| `killswitch-holding` | Tunnel down; download client has no connectivity. Safe. |
| `leaking` | Download client's egress does not match the tunnel. **Critical.** |
| `unverified` | Could not be checked |
| `not-configured` | No VPN configured; torrents disabled or accepted without one |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| IP-echo service unreachable from both containers | `unverified`, not `pass`. Loss of the oracle is not evidence of safety. |
| IP-echo reachable from one container only | Strong signal. Report as a probable leak or probable killswitch depending on which. |
| Tunnel up, no forwarded port | `degraded`, naming the NAT-PMP-at-generation cause first. |
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
| **C2-R6** | When the tunnel is up but no port was granted, the configuration-generation cause MUST be named first. |
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
