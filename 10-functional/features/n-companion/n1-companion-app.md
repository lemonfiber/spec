---
id: N1
title: The companion app
kind: feature
area: N
audience: both
status: draft
maturity: planned
priority: P1
labels: [mobile, security, ux]
requires: [C6, D6, G1, G4]
relates: [A4, B2, C1, G3, I1]
---

# N1 — The companion app

**Status:** Draft · **Audience:** Both · **Area:** N — Companion

---

## Purpose

A fourth surface, on the device the operator actually has on them.

The CLI, TUI and web UI all run on the machine the stack runs on. That is the
right place to set a stack up and the wrong place to be when the downloads stop
at eleven at night. The question this feature answers is not "can we have an
app" but **what a surface is allowed to be once it is no longer on the host** —
what it may assume, what it must prove, and what it must say when it cannot
reach anything.

It is one application serving two people. Which one it is for is decided by the
credential that signs in, never by which build was installed
([D6](../d-content/d6-household-identity.md)).

This feature owns **getting connected and staying honest about it**. What the
app then shows is [N2](n2-operator-companion.md) and
[N3](n3-household-companion.md); what it uses of the device is
[N4](n4-native-integration.md).

## Behaviour

### It is a surface, and parity binds it

The app renders the core's answers and decides nothing the core does not already
decide ([ADR-0017](../../../00-overview/decisions/0017-the-companion-app-as-a-fourth-surface.md)).
Every action reachable from a terminal is reachable here, with one stated
exception below.

### Reaching a stack is the operator's choice, not the app's

lemonfiber's admin surface binds to loopback and refuses to widen without
authentication ([C6](../c-trust/c6-web-security.md)). A phone therefore cannot
reach a stack until the operator has chosen to let it, and the app must not
present that choice as something it can make on their behalf.

What it does instead is explain the choice in the operator's terms, and name
what has to be true: a bound address, authentication configured, both devices on
the same network.

### Pairing carries an address and a credential, once

A person types as little as possible. The app is pointed at a stack by scanning
a code the operator's own surfaces can display, and falls back to typed entry
where a camera is unavailable or declined.

Whatever the route, the app exchanges the credential **once** at `/api/session`
for a session, and carries that session in `X-Lemonfiber-Token` afterwards. The
credential is not kept to be re-sent: a secret held for one exchange is a smaller
secret than one held for every request.

### The SDK is the only way out, and a gap in it is a question rather than a workaround

Every call to the stack goes through [`sdk-php`](../../../30-repos/sdk-php.md).
The app issues no HTTP request of its own, builds no URL, and parses no envelope
the SDK did not hand it.

**Where the SDK does not yet expose something the app needs, that is where the
work stops.** The gap is raised against the SDK and the contract, and the app
waits. It does not reach past the SDK to the endpoint, re-implement the call
beside it, or approximate the answer from something adjacent.

This is the rule that keeps a fourth client from quietly becoming a third source
of truth. The failure it prevents is the ordinary one: a screen needs a field
nobody generated yet, somebody fetches it directly "just this once", and the
contract now has a consumer it does not know about. A missing capability is
information — it says the contract or the SDK is behind — and information is
worth more than the screen it was blocking.

### An unreachable stack is a state, not a missing feature

The app never hides an action because it cannot currently reach the stack. It
offers the action and reports, in the words of [G4](../g-ux/g4-error-model.md),
that the stack could not be reached and what to check.

This is the honest form of parity across a device boundary: the surface offers
everything, and reachability is a condition it reports rather than a capability
it lacks.

### Nothing is presented as current that is not

A value read four hours ago, shown without saying so, is the failure this
product's own dashboard rules exist to prevent. Anything the app shows from a
previous connection is marked with when it was read, and is never mixed
indistinguishably with a live reading.

### First-run setup does not cross the boundary

`G1-R14` asks that setup be completable from every surface. It cannot be
completed from a phone, and the reason is structural rather than a shortfall of
effort: the thing that lets a phone reach the machine — a bound, authenticated
admin surface — is created *during* setup. A phone cannot perform the act that
makes a phone able to perform acts.

Reconfiguration ([A4](../a-getting-started/a4-reconfiguration.md)) is offered in
full. First-run setup is declined with that reason stated, rather than absent.

### More than one stack

An operator may run more than one. The app holds several, each with its own
address and session, and never lets a reading from one appear under another.
Switching is explicit.

### Honest about the transport it got

On a LAN the connection is plain HTTP unless the operator has arranged
otherwise, which is C6's deliberate position. The app says which it got rather
than implying a protection it does not have.

When remote access ([I1](../i-remote-access/i1-remote-access.md)) lands, the same
session travels the overlay instead. The app's conversation does not change.

## States

| State | Meaning |
|-------|---------|
| Unpaired | No stack is configured. The app explains what has to be true and how to make it so. |
| Paired, unreachable | A stack is configured and cannot be reached now. Last-read values are shown, marked as such. |
| Paired, reachable | A live session. Everything is current. |
| Session expired | The stack is reachable and the session is no longer valid. Re-authentication is offered without re-pairing. |
| Refused | The stack answered and declined the credential. Distinct from unreachable, because the remedy is different. |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| The operator scans a code for a stack the phone cannot route to | Paired, then immediately unreachable, with the address named — a wrong network is the common cause and is worth naming. |
| The stack's address changes with DHCP | Reported as unreachable at the address held. Re-pairing is offered; the app does not scan the network for a replacement. |
| Two stacks on one phone answer at the same address | Each is held separately by what it calls itself, and a reading is never attributed to the wrong one. |
| The credential is correct and the surface is loopback-bound | The stack is unreachable rather than refusing, and the app names the binding as the likely cause. |
| The device is offline entirely | Unreachable, distinguished from a stack that is down, because the person can tell the difference and the remedy differs. |
| The API answers a wire version the app does not know | Refused loudly, naming both versions. An app that guessed at a newer envelope would render a stale shape as current. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N1-R1** | The app MUST speak the published web API contract and MUST NOT implement a second API client of its own ([ADR-0013](../../../00-overview/decisions/0013-an-sdk-owns-the-api-client.md)). |
| **N1-R2** | Every action available from another surface MUST be offered by the app, except where a requirement here states otherwise and why. |
| **N1-R3** | The app MUST NOT hide or remove an action because the stack is currently unreachable; it MUST offer the action and report the reachability failure. |
| **N1-R4** | The app MUST NOT offer first-run setup, and MUST state that setup is performed at the machine and why, rather than omitting it silently. |
| **N1-R5** | The app MUST offer reconfiguration in full once connected. |
| **N1-R6** | Pairing MUST be possible by scanning a code, and MUST remain possible by typed entry where no camera is available or permission is declined. |
| **N1-R7** | The credential MUST be exchanged for a session once, and MUST NOT be retained for re-sending on subsequent requests. |
| **N1-R8** | The session MUST be carried in the credential header the API defines, and MUST NOT be placed in a URL or a query parameter. |
| **N1-R9** | Any value shown that was not read in the current session MUST be marked with when it was read, and MUST NOT be presented indistinguishably from a live reading. |
| **N1-R10** | A stack that cannot be reached, one that refuses the credential, and a device with no network MUST be reported as three different things, each with its own remedy. |
| **N1-R11** | The app MUST support more than one configured stack, MUST keep each one's session separate, and MUST NOT attribute a reading from one stack to another. |
| **N1-R12** | The app MUST state whether the connection it has is encrypted, and MUST NOT imply protection it does not have. |
| **N1-R13** | The app MUST refuse an envelope whose wire version it does not support, naming the version it received and the versions it reads. |
| **N1-R14** | A change of transport — LAN today, an overlay under [I1](../i-remote-access/i1-remote-access.md) later — MUST NOT require a change to how the app authenticates or to the contract it speaks. |
| **N1-R15** | The app MUST NOT log, transmit or include in a diagnostic report any credential, session token, or stack address. |
| **N1-R16** | Every call to the API MUST be made through the SDK. The app MUST NOT issue an HTTP request of its own, construct an API URL, or parse an envelope the SDK did not produce. |
| **N1-R17** | Where the SDK does not expose a capability the app requires, the app MUST NOT reach past it, re-implement the call, or approximate the answer from another endpoint. The gap MUST be raised against the SDK and the contract, and the dependent work MUST stop until it is closed. |
| **N1-R18** | The pairing material MUST carry the fingerprint of the certificate the stack will present, and the app MUST take it from that material rather than from the network ([ADR-0018](../../../00-overview/decisions/0018-trusting-a-stack-over-the-local-network.md)). |
| **N1-R19** | The app MUST pin the paired fingerprint against that stack and MUST validate every subsequent connection against it, whether or not the platform trust store would accept the certificate. |
| **N1-R20** | A connection presenting a different certificate MUST be refused rather than warned about, MUST be reported as this machine not being the one the app was introduced to, and MUST offer re-pairing as the remedy. |
| **N1-R21** | Certificate verification MUST NOT be disabled in any build, under any flag or configuration value. |
| **N1-R22** | Pinning MUST be to the stack rather than to an address, so that reaching the same stack by another route does not re-open the question of its identity. |
| **N1-R23** | A credential, a session token and pairing material MUST NOT be written to any cache, and MUST NOT survive beyond the storage [N4](n4-native-integration.md) defines for them. |
| **N1-R24** | A reading the app retained from an earlier session MAY be shown on opening, and MUST carry when it was read as `N1-R9` requires; the confirmation of an action just performed MUST NOT be served from a retained value. |

## Related

- [G1](../g-ux/g1-interface-tiers.md) — the surfaces this joins, and the parity rule it inherits
- [C6](../c-trust/c6-web-security.md) — the binding policy that decides whether a phone can reach anything
- [D6](../d-content/d6-household-identity.md) — who is signing in
- [G4](../g-ux/g4-error-model.md) — how a refusal is worded
- [I1](../i-remote-access/i1-remote-access.md) — the transport this is built to move onto
- [N2](n2-operator-companion.md), [N3](n3-household-companion.md), [N4](n4-native-integration.md)
