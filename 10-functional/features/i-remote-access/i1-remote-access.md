---
id: I1
title: Remote access for the household
kind: feature
area: I
audience: both
status: accepted
tracks: v2
priority: P1
labels: [remote-access, network, verification, security]
relates: [C2, C6, G8, I2]
---

# I1 — Remote access for the household

**Status:** Accepted · **Audience:** Both · **Area:** I — Remote access & identity

---

## Purpose

Let a household member watch from outside the home — on cellular, at a friend's
house — without the operator opening a port they don't understand or handing
their stack to a proprietary control plane.

This was a deliberate 1.0 non-goal ([roadmap post-1.0](../../../00-overview/roadmap.md#post-10-candidates),
the reserved **B7**): every easy option in 2024 either ran through a proprietary
coordinator or was substantially harder to stand up. It returns in v2 because the
constraint that blocked it — "easy *and* open-source *and* verifiable" — is now
satisfiable with a self-hosted overlay control plane, and because reaching the
stack from outside is the single most-requested capability a running stack still
lacks.

The value lemonfiber adds over a copied WireGuard config is the same as
everywhere else: it **proves the path works from the outside**, not just that a
daemon started.

## Behaviour

### It refuses a proprietary control plane

Remote access MUST NOT depend on a service whose coordination plane is closed or
whose terms forbid the traffic. Cloudflare Tunnel is refused as a built-in path
for both reasons — the tunnel is coordinated by Cloudflare and its terms restrict
video streaming, which is the use case. The tool may name it in documentation as
an option the operator can wire by hand, but never configures it as a default.

### It picks the archetype from the network, not a guess

lemonfiber first establishes what the network *is*, because it decides which
options can work at all:

- **Public reachable address** — a forwardable IPv4 or working IPv6. Both an
  overlay and a public-ingress path are possible.
- **CGNAT / no reachable address** — the carrier owns the public edge; no inbound
  port can ever arrive. Only an outbound-tunnel overlay works.

It detects the condition by comparing the router's WAN address against a
STUN-observed public address; a mismatch means CGNAT. The operator is told which
condition was found and why it narrows the choice, rather than being offered a
path that cannot work on their line.

### Two archetypes, one of them the default

| Archetype | What it is | When |
|-----------|-----------|------|
| **Overlay network** *(default)* | A self-hosted control plane (Headscale) with unmodified clients and a **self-hosted relay** (DERP), so no third party ever coordinates or carries traffic. Works behind CGNAT via hole-punching with a relay fallback. | Any line, especially CGNAT |
| **Public ingress** | The bundled reverse proxy (Caddy) terminates real public TLS via ACME, with a dynamic-DNS updater keeping the record pointed at the home address. | Only with a public IP or IPv6 |

The overlay is the default because it is the only one that works on every line and
never exposes a service to the open internet. The ingress path is offered when a
public address exists and the operator wants native per-service URLs — and it is
refused unless authentication is in place ([I2](i2-identity.md), [C6](../c-trust/c6-web-security.md)),
never merely warned about.

### It cannot automate the router, and says so

No universal API forwards a router port, and enabling UPnP to do it is a security
regression the tool won't make. Where a path needs an inbound port (public
ingress on a public line), lemonfiber generates the exact rule to add and then
**verifies from outside** whether it took — it does not pretend to have done the
step it cannot do.

### It proves reachability from the outside

A tunnel that shows "connected" locally proves nothing about whether the
household can actually reach Jellyfin. The check that matters runs from an
**off-network vantage** (a lightweight external prober, or a guided check from a
phone on cellular):

- **End-to-end reach** — fetch a known Jellyfin endpoint over the path and assert
  a success response and the expected server identity.
- **TLS validity** (ingress path) — the leaf certificate chains to a public root,
  matches the hostname, and is not near expiry.
- **Handshake liveness** (overlay/WireGuard paths) — a recent handshake and
  advancing byte counters.
- **Path honesty** — for the overlay, whether the connection is **direct or
  relayed**, reported as such, because a relayed path can be dramatically slower
  and the household deserves the truth rather than a green light.
- **DNS correctness** — the hostname resolves to the current address (catches a
  stale dynamic-DNS record).
- **No accidental exposure** — a service meant to be tunnel-only is not also
  answering directly on the WAN.

### Every step has a non-interactive equivalent

Provisioning a device, issuing an overlay pre-auth key, rotating it, and running
the reachability proof are all reachable as plain subcommands, so the wizard
never costs the scripter ([vision](../../../00-overview/vision.md#who-its-for)).

## States

| State | Meaning |
|-------|---------|
| `unconfigured` | No remote access set up; offers to configure the archetype the line supports |
| `overlay-direct` | Overlay active, peer reachable on a direct path |
| `overlay-relayed` | Overlay active but traffic is relayed; stated plainly, with the bandwidth caveat |
| `ingress-live` | Public ingress active, TLS valid, externally reachable |
| `degraded` | Configured but the last external proof failed; names which check failed |
| `unreachable` | No path currently reaches the stack from outside |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| CGNAT line | Steer to the overlay; never offer public ingress that cannot receive a packet. |
| Symmetric NAT defeats hole-punching | Fall back to the self-hosted relay; report the path as relayed, not direct. |
| Dynamic-DNS record stale | The DNS-correctness proof fails loudly with the observed vs expected address, and the remedy names the record to update. |
| Certificate near expiry | Surface it before it lapses; ACME renewal is expected but its success is proven, not assumed. |
| Router port-forward not applied | The external reach proof fails; the remedy is the exact rule, since the tool cannot add it. |
| IPv6-only household | Prefer an AAAA-based ingress or the overlay; do not assert an IPv4 path that doesn't exist. |
| Relay bandwidth collapse | Report relayed state and measured throughput honestly; do not present a slow relayed path as healthy. |
| Overlay control plane down | Existing peer sessions may persist; new joins fail — say which, and that the control plane, not the tunnel, is the fault. |
| Operator enables ingress without auth | Refuse to expose the control surface until authentication is configured ([C6](../c-trust/c6-web-security.md)). |
| Household device offline during a proof | The proof is inconclusive, not failed; distinguish "could not test" from "tested and unreachable". |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **I1-R1** | Remote access MUST NOT depend on a proprietary or closed coordination plane, and MUST NOT configure a path whose terms of service forbid media streaming. |
| **I1-R2** | The tool MUST detect whether the line has a publicly reachable address or is behind CGNAT, and MUST NOT offer a path that cannot work on the detected condition. |
| **I1-R3** | A self-hosted overlay network MUST be the default archetype, using a self-hosted control plane and a self-hostable relay so no third party coordinates or carries traffic. |
| **I1-R4** | The public-ingress archetype MUST be offered only when a publicly reachable address exists, and MUST be refused unless authentication is configured. |
| **I1-R5** | The tool MUST NOT enable UPnP or otherwise weaken the router to obtain an inbound port; where a port is required it MUST emit the exact rule and verify externally whether it took. |
| **I1-R6** | Reachability MUST be proven from an off-network vantage by fetching a known service endpoint and asserting success and expected identity — a local "connected" state MUST NOT be reported as reachable. |
| **I1-R7** | On a TLS ingress path, the tool MUST verify the certificate chains to a public root, matches the hostname, and is not near expiry. |
| **I1-R8** | On a tunnel path, the tool MUST verify a recent handshake and advancing traffic counters. |
| **I1-R9** | The tool MUST report whether an overlay connection is direct or relayed, and MUST NOT present a relayed path as equivalent to a direct one. |
| **I1-R10** | The tool MUST verify that the access hostname resolves to the current address and MUST report a stale dynamic-DNS record with the observed and expected values. |
| **I1-R11** | The tool MUST verify that a service intended to be tunnel-only is not also directly reachable on the WAN. |
| **I1-R12** | A failed or inconclusive external proof MUST be distinguished from each other and from success, and each failure MUST carry a remedy ([G4](../g-ux/g4-error-model.md)). |
| **I1-R13** | Device enrolment, key issue, key rotation, and the reachability proof MUST each be reachable non-interactively. |
| **I1-R14** | Configuring remote access MUST NOT expose any administrative surface beyond its existing binding policy ([C6](../c-trust/c6-web-security.md)). |
| **I1-R15** | Credentials and keys created for remote access MUST be managed and rotatable through the same path as other secrets ([A7](../a-getting-started/a7-credential-management.md)). |

## Related

- [I2 Household identity & SSO](i2-identity.md) — the authentication remote access requires
- [C2 VPN verification](../c-trust/c2-vpn-verification.md) — the egress-proof machinery this reuses from the outside
- [C6 Web UI security & binding policy](../c-trust/c6-web-security.md) — what may and may not be exposed
- [G8 Privacy stance](../g-ux/g8-privacy.md) — the data-egress posture remote access must honour
- [B6 Controlling a stack on another machine](../b-running/b6-remote-stack.md) — operator remote control, distinct from household viewing
