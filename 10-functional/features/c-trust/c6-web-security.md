# C6 — Web UI security & binding policy

**Status:** Accepted · **Audience:** Operator · **Area:** C — Trust & correctness

---

## Purpose

Serving a web UI turns lemonfiber into a network service. That web UI can start,
stop and reconfigure the entire stack, read logs, and reach every credential the
system holds. It is the most privileged surface in the product.

Meanwhile the household needs Jellyfin and Jellyseerr reachable from the TV and
their phones. So "bind everything to loopback" is not achievable, and "bind
everything to the network" is not acceptable.

This feature defines which surfaces are exposed, to whom, and what must be true
before exposure is permitted.

## Behaviour

### The binding policy is two-tier

| Tier | Services | Default binding | Rationale |
|------|----------|-----------------|-----------|
| **Admin** | The \*arrs, SABnzbd, qBittorrent, Bindery, Prowlarr, NZBHydra2, lemonfiber's own UI | `127.0.0.1` | Full control over the system. Only the operator needs them. |
| **Household** | Jellyfin, Jellyseerr, Calibre-Web-Automated, Audiobookshelf, Homepage | LAN | Useless if unreachable from a TV or phone. |

This is stronger than the common practice of binding everything to `0.0.0.0`,
which exposes every admin service — most with weak or disabled default
authentication — to every device on the network, including ones the operator
doesn't administer.

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
| Household service needs to be reachable but the network is untrusted | Explain the trade-off; do not silently expose. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **C6-R1** | Admin services MUST bind to loopback by default. |
| **C6-R2** | Household-facing services MUST bind to the LAN by default. |
| **C6-R3** | No service MAY bind to all interfaces by default. |
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

## Related

- [B6 Remote stack control](../b-running/b6-remote-stack.md) — the reason LAN binding exists
- [A7 Credential management](../a-getting-started/a7-credential-management.md)
- [D6 Household identity](../d-content/d6-household-identity.md) — who reaches household surfaces
- [C1 Diagnostics](c1-diagnostics.md) — binding verification
