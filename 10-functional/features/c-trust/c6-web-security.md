---
id: C6
title: Web UI security & binding policy
kind: feature
area: C
audience: operator
status: accepted
maturity: shipped
shipped: 0.10.0
labels: [security, web]
relates: [A7, B6, C1, D6]
---

# C6 — Web UI security & binding policy

**Status:** Accepted · **Audience:** Operator · **Area:** C — Trust & correctness

---

## Purpose

Serving a web UI turns lemonfiber into a network service. That web UI can start,
stop and reconfigure the entire stack, read logs, and reach every credential the
system holds. It is the most privileged surface in the product.

Meanwhile the household needs Jellyfin and Seerr reachable from the TV and
their phones. So "bind everything to loopback" is not achievable, and "bind
everything to the network" is not acceptable.

This feature defines which surfaces are exposed, to whom, and what must be true
before exposure is permitted.

## Behaviour

### The binding policy is two-tier

| Tier | Services | Default binding | Rationale |
|------|----------|-----------------|-----------|
| **Admin** | The \*arrs, SABnzbd, qBittorrent, Bindery, Prowlarr, NZBHydra2, lemonfiber's own UI | `127.0.0.1` | Full control over the system. Only the operator needs them. |
| **Household** | Jellyfin, Seerr, Calibre-Web-Automated, Audiobookshelf, Homepage | LAN | Useless if unreachable from a TV or phone. |

This is stronger than the common practice of binding everything to `0.0.0.0`,
which exposes every admin service — most with weak or disabled default
authentication — to every device on the network, including ones the operator
doesn't administer.

### What "LAN" means to a container, stated honestly

The admin tier is exact: `127.0.0.1`, and nothing else resolves to it.

The household tier cannot be, and pretending otherwise would be the dishonesty
this feature exists to avoid. A published container port takes a host address,
and the stack has no way to learn which of the host's addresses is the LAN one —
that varies by machine, changes with DHCP, and is different again on a laptop
that moves. So the household tier's default is every interface, and the operator
is told so plainly rather than being sold a precision that isn't there.

What the stack owes in exchange is a single, documented knob that narrows it — a
publish address the operator can pin to one interface — and a diagnostic that
reports what is *actually* listening rather than what was intended (`C6-R17`,
`C6-R13`). "Bound to the LAN" is the intent; "published on every interface unless
you say otherwise" is the fact, and the fact is what gets written down.

### Admin exposure requires authentication, enforced by refusal

Binding lemonfiber's own UI beyond loopback is opt-in, and is **refused** unless
authentication is configured. Not warned about — refused. A warning that can be
clicked past is how unauthenticated control surfaces end up on networks.

If authentication is later removed while LAN-bound, the binding reverts to
loopback immediately.

### Honest about transport

On a LAN, lemonfiber serves plain HTTP unless the operator has arranged
otherwise. It says so, rather than implying protection it doesn't provide.

Self-signed TLS is available but **not enabled by default**: it trains operators
to click through certificate warnings, which is a worse security outcome than
honest HTTP on a trusted local network. The [Caddy overlay](../b-running/b1-forms.md)
provides real certificates for operators who want them.

### A certificate the companion pinned does not change quietly

A phone paired to this stack holds the fingerprint of the certificate it was
introduced to ([ADR-0018](../../../00-overview/decisions/0018-trusting-a-stack-over-the-local-network.md)),
and refuses a connection presenting a different one. That refusal is the point,
and it is indistinguishable — to the operator, at the moment it happens — from
an impostor on the network.

So replacing the certificate is an act the stack announces before it performs,
naming re-pairing as the consequence. The alternative is an alarm that fires for
routine maintenance, which is an alarm people learn to click through, and a
security control nobody reads is not one.

Where the stack is not the thing renewing — the [Caddy overlay](../b-running/b1-forms.md)
obtaining real certificates, which rotates on its own schedule — it cannot make
that promise, and says so when the pairing material is produced rather than
letting every paired device find out at the next renewal.

### Session handling is conservative

Sessions expire. Credentials are stored hashed with a modern password-hashing
function, never reversibly. Failed attempts are rate-limited. State-changing
requests are protected against cross-site request forgery.

None of this is novel; it's the standard set, and the specification records it so
that omission is a defect rather than an oversight.

### The web UI is not a proxy for admin services

lemonfiber's UI does not tunnel to Sonarr's web interface. Doing so would
effectively expose every admin service through one authenticated hole, and one
authentication bug would expose all of them.

### The policy is checked, not just configured

A [diagnostic check](c1-diagnostics.md) verifies actual bindings against the
policy. Configuration drift, a manual compose edit, or a service defaulting
differently after an upgrade must be detected — the check asks what is actually
listening, not what was intended.

## States

| State | Meaning |
|-------|---------|
| `loopback` | Admin surfaces on `127.0.0.1`; household surfaces on the LAN. Default. |
| `lan-admin` | lemonfiber's UI is LAN-bound with authentication configured |
| `refused` | LAN binding requested without authentication |
| `policy-violation` | An admin service found bound beyond loopback |
| `proxied` | Caddy overlay active; real certificates in use |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| LAN binding requested without auth | Refuse. Explain how to configure authentication. |
| Auth removed while LAN-bound | Revert to loopback immediately and state why. |
| An admin service found on `0.0.0.0` | Report as `policy-violation` with the service named and a remedy. |
| Operator deliberately exposes an admin service | Permitted with explicit acknowledgement; recorded so diagnostics stop reporting it as unintentional. |
| Weak password set | Enforce a minimum; state the reasoning without lecturing. |
| Repeated failed logins | Rate-limit and record. Report as a condition if sustained. |
| Docker publishes a port bypassing the host firewall | Warn — Docker's port publishing bypasses some host firewalls, which surprises operators who believe they're protected. |
| IPv6 present | Apply the same policy to IPv6 bindings. A loopback-only policy that leaves `::` open is not loopback-only. |
| Operator on an untrusted network (café, shared flat) | The LAN tier assumes a trusted network. State that assumption plainly. |
| Reverse proxy terminates TLS upstream | Detect and don't duplicate; trust forwarded headers only from configured sources. |
| Session active during a credential change | Invalidate existing sessions. |
| The certificate a companion pinned is about to be replaced | Announce it before replacing it, naming re-pairing as the consequence. A pinned device refuses afterwards, and a refusal nobody was warned about is read as a fault. |
| Renewal is performed by something the stack does not control | Say so at pairing. The stack cannot promise a warning it will not receive, and an unkeepable promise is worse than the absence of one. |
| Household service needs to be reachable but the network is untrusted | Explain the trade-off; do not silently expose. |
| A plugin adds a service that will listen | It declares which tier it belongs in, and lemonfiber assigns the address. A plugin that could write its own address could put an admin surface on the LAN without touching anything this feature inspects. |
| A plugin's service is bound to the wrong tier | Caught the way every other wrong binding is caught: by checking what is actually listening against the policy (`C6-R13`), not by trusting what was declared. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **C6-R1** | Admin services MUST bind to loopback by default. |
| **C6-R2** | Household-facing services MUST bind to the LAN by default. |
| **C6-R3** | No **admin** service MAY bind to all interfaces by default. |
| **C6-R4** | LAN binding of lemonfiber's UI MUST be refused unless authentication is configured. |
| **C6-R5** | Removing authentication while LAN-bound MUST immediately revert to loopback. |
| **C6-R6** | lemonfiber MUST state plainly when it is serving unencrypted HTTP. |
| **C6-R7** | Self-signed TLS MUST NOT be enabled by default. |
| **C6-R8** | Stored authentication credentials MUST use a modern password-hashing function and MUST NOT be recoverable. |
| **C6-R9** | Sessions MUST expire, and MUST be invalidated on credential change. |
| **C6-R10** | State-changing requests MUST be protected against cross-site request forgery. |
| **C6-R11** | Failed authentication attempts MUST be rate-limited. |
| **C6-R12** | lemonfiber's UI MUST NOT proxy or tunnel to admin service interfaces. |
| **C6-R13** | Actual listening bindings MUST be verified against policy by a diagnostic check. |
| **C6-R14** | Binding policy MUST apply equally to IPv4 and IPv6. |
| **C6-R15** | Deliberate exposure of an admin service MUST require explicit acknowledgement and MUST be recorded. |
| **C6-R16** | Where Docker port publishing bypasses the host firewall, lemonfiber MUST warn. |
| **C6-R17** | The interface household services publish on MUST be operator-configurable through a single documented setting, and where it defaults to all interfaces that MUST be stated plainly alongside its consequences. |
| **C6-R18** | A service an installed plugin adds MUST be bound by the tier lemonfiber assigns from the classification the plugin declared, and a plugin MUST NOT be able to declare an address, an interface or a published port mapping. |
| **C6-R19** | Replacing a certificate a companion may have pinned MUST be announced before it is replaced, naming re-pairing as the consequence; where renewal is performed by something lemonfiber does not control, that MUST be stated when the pairing material is produced rather than discovered at the next renewal ([ADR-0025](../../../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md)). |

**Affected repos** (`GOV-R7`): `lemonfiber-media-stack` publishes the household
tier on a configurable address; `lemonfiber` reports the observed binding under
`C6-R13`, and announces a certificate replacement under `C6-R19` since it is the
side that produces pairing material.

## Related

- [B6 Remote stack control](../b-running/b6-remote-stack.md) — the reason LAN binding exists
- [A7 Credential management](../a-getting-started/a7-credential-management.md)
- [D6 Household identity](../d-content/d6-household-identity.md) — who reaches household surfaces
- [C1 Diagnostics](c1-diagnostics.md) — binding verification
- [ADR-0025](../../../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md) — why `C6-R19` exists, and what a pin permits
