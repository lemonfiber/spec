---
id: A3
title: Credential validation
kind: feature
area: A
audience: operator
status: accepted
tracks: v1
milestone: M3
labels: [security, verification]
requires: [G4]
relates: [A1, A7, C2, C8]
---

# A3 — Credential validation

**Status:** Accepted · **Audience:** Operator · **Area:** A — Getting started

---

## Purpose

A wrong credential must fail **where it was entered**, not three screens later as
an empty search result.

This is the most common silent failure in self-hosted media stacks. An operator
pastes a Usenet API key with a trailing space, or a WireGuard key generated
without port forwarding enabled, and everything reports healthy. Weeks later they
conclude "the stack doesn't work" and abandon it. The credential was wrong for
the entire time and nothing said so.

Validation is the practical expression of
[P3](../../../00-overview/vision.md#p3--the-tool-proves-things-rather-than-assuming-them):
where a claim is checkable, check it.

## Behaviour

### Every credential is tested against the live service before it is stored

Not format-checked — **tested**. A syntactically perfect API key that the
indexer rejects is worthless, and format validation gives false confidence.

| Credential | How it's proven |
|------------|-----------------|
| Usenet provider | Connect to the host/port, authenticate, confirm the connection limit |
| Usenet indexer | Issue a real (trivial) search query and confirm a well-formed response |
| Torrent indexer | Same — a real query against the Torznab endpoint |
| VPN (WireGuard) | Bring the tunnel up, confirm the public IP changed, confirm port forwarding was granted |
| Existing service | Reach its API with the supplied key and read back its identity |

### Validation is a distinct, visible step

The operator sees it happen and sees the result. A spinner that resolves to a
green check with the *observed* fact — "connected, 30 connections available" —
tells them more than "OK".

Confirming the observation matters: it lets the operator notice that they bought
a 10-connection plan but the provider reports 8, or that the tunnel came up in
the wrong country.

### Failure distinguishes cause

Three genuinely different failures, three different remedies:

| Cause | Message shape | Remedy |
|-------|---------------|--------|
| **Rejected** | The service answered and said no | Check the key; check the username; check the account is active |
| **Unreachable** | No answer at all | Check the hostname/port; check your own connectivity; the service may be down |
| **Reachable but unusable** | Authenticated, but the account can't do the job | Account exhausted, plan expired, no P2P on this server |

Collapsing these into "validation failed" sends the operator hunting the wrong
problem, which is worse than no message.

### VPN validation is special-cased, per provider

Each provider has a characteristic failure that looks like a broken installation
and is actually a credential problem. None of them explain it at the point of
failure, and no operator will guess it:

| Provider | Trap | Why it's invisible |
|----------|------|--------------------|
| **ProtonVPN** | Port forwarding must be enabled **when the WireGuard config is generated**, and the server must support P2P | The tunnel connects perfectly; only the port is missing. Unrecoverable at runtime — requires new credentials. |
| **NordVPN** | Credentials are **service credentials** from the dashboard, not the account email and password | The obvious values are rejected with no explanation, so it reads as "my password is wrong" |

Where a provider has a known trap, validation names it as the first candidate
cause on failure. Where lemonfiber has no specific knowledge of a provider, it
reports the generic failure without speculating.

Port-forwarding validation only applies where the provider supports it at all —
see [C2](../c-trust/c2-vpn-verification.md#providers-are-described-by-capability-not-by-name).

### Re-validation is available on demand

Credentials rot. Accounts lapse, keys get rotated, plans change. Validation is
re-runnable at any time, and is also a [diagnostic check](../c-trust/c1-diagnostics.md)
so it participates in ongoing health rather than being a one-off gate.

### Secrets are never echoed

Not to the screen, not to logs, not to the support bundle. Validation reports
*outcomes*, never inputs.

## States

Per credential:

| State | Meaning |
|-------|---------|
| `empty` | Nothing supplied |
| `validating` | Test in flight |
| `valid` | Proven working, with observed capabilities recorded |
| `rejected` | Service answered and refused |
| `unreachable` | No usable response |
| `degraded` | Authenticated but cannot perform its function |
| `stale` | Previously valid, not re-checked within the freshness window |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Trailing whitespace or newline in a pasted key | Trim it silently. This is the single most common paste error and punishing it serves nobody. |
| Operator pastes an entire config file | Extract the needed field where the format is unambiguous; otherwise say precisely what was expected. |
| Service is rate-limiting | Distinguish from rejection. Report it as transient and offer retry with backoff. |
| Validation times out | Bounded wait, then report `unreachable` with the elapsed time. Never hang indefinitely. |
| VPN tunnel comes up but no forwarded port | Report `degraded`, and name the NAT-PMP-at-generation cause first. |
| Tunnel connects to an unexpected country | Report it. Not an error, but it's frequently not what the operator intended. |
| Usenet account valid but has zero remaining data | `degraded` — hand off to [C8](../c-trust/c8-provider-health.md). |
| Operator wants to proceed with an unvalidated credential | Permitted with explicit confirmation. It's their machine. Record that it was unvalidated so later diagnostics can point at it. |
| Network unavailable entirely | Detect once and say so, rather than reporting every credential as individually unreachable. |
| Self-signed certificate on a private indexer | Report the specific TLS failure and require an explicit opt-in to proceed. Never silently skip verification. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **A3-R1** | No credential MAY be persisted before a validation attempt has completed. |
| **A3-R2** | Validation MUST test against the live service, not merely check format. |
| **A3-R3** | Validation results MUST report an observed capability, not only pass/fail. |
| **A3-R4** | `rejected`, `unreachable`, and `degraded` MUST be distinguished, each with its own remedy. |
| **A3-R5** | Leading and trailing whitespace MUST be trimmed from pasted credentials without error. |
| **A3-R6** | Credentials MUST NOT appear in any log, error message, screen output, or support bundle. |
| **A3-R7** | Validation MUST time out within a bounded period and report the elapsed time. |
| **A3-R8** | Where the provider supports port forwarding, VPN validation MUST verify a port was granted, and on failure MUST name that provider's known trap first. |
| **A3-R14** | Port-forwarding validation MUST be skipped for providers that do not support it, and its absence MUST NOT be reported as a validation failure. |
| **A3-R15** | Where lemonfiber has no provider-specific knowledge, validation MUST report the generic failure and MUST NOT speculate about the cause. |
| **A3-R9** | VPN validation MUST report the observed exit country. |
| **A3-R10** | Validation MUST be re-runnable on demand and MUST participate in [C1 diagnostics](../c-trust/c1-diagnostics.md). |
| **A3-R11** | Total loss of network connectivity MUST be reported once, not once per credential. |
| **A3-R12** | TLS verification MUST NOT be skipped without explicit per-host opt-in. |
| **A3-R13** | Proceeding with an unvalidated credential MUST be possible, MUST require confirmation, and MUST be recorded. |

## Related

- [A1 Prerequisites](a1-prerequisites.md) — what needs validating
- [A7 Credential management](a7-credential-management.md) — storage and rotation
- [C2 VPN verification](../c-trust/c2-vpn-verification.md) — ongoing, deeper VPN checks
- [C8 Provider health](../c-trust/c8-provider-health.md) — quota and capacity over time
- [G4 Error model](../g-ux/g4-error-model.md)
