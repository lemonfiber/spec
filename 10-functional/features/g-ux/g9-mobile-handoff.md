---
id: G9
title: Mobile client handoff
kind: feature
area: G
audience: both
status: accepted
tracks: v2
milestone: M8
priority: P2
labels: [household, ux, verification]
relates: [G6, D6, I1]
---

# G9 — Mobile client handoff

**Status:** Accepted · **Audience:** Both · **Area:** G — Cross-cutting UX

---

## Purpose

[G6](g6-client-apps.md) tells a household member *which* app to install. This
feature gets them *from an install to a working, signed-in app* with the least
possible typing — a scanned code instead of a hand-entered server address — and
then **proves the device actually connected**, so "they're set up" is a fact the
operator can see rather than a hopeful assumption. It is the last hop of the
[remote-access](../i-remote-access/i1-remote-access.md) story: once the stack is
reachable, a person still has to get their phone onto it.

## Behaviour

### It provisions the household member first

A person's account is created against the media server through its own interface
([D6](../d-content/d6-household-identity.md)) — one household identity, not a new
silo — before any device is handed over, so the code they scan leads to an account
that already exists.

### It hands over a scannable code, not an address to type

Instead of dictating a server URL, lemonfiber generates a per-person code (a QR)
encoding the server address, and where a client supports it a deep link that opens
the app straight to that server. Typing a hostname on a TV remote is exactly the
friction this removes.

### It guides the code-based sign-in, it does not fake it

Where the media server offers a code-authorisation flow (a short code the person
approves from an already-signed-in session), lemonfiber initiates and guides it —
but it MUST NOT auto-approve on the person's behalf, because that human step is
the flow's anti-abuse purpose. The tool's job is to make the step obvious and to
confirm its result, not to bypass it.

### It recommends open clients

The clients it points a person to MUST be open-source and self-hostable-stack
compatible; a proprietary or paid client MAY be mentioned but MUST be flagged as
such, never offered as the default.

### It proves the device connected

After the hand-off, lemonfiber queries the media server for the new device or
session and asserts it registered — turning "the phone connected" into an observed
fact. Because completing the sign-in needs the person to act on their device, this
proof is **semi-interactive**: until the person finishes, the result is *pending*,
distinct from *failed*.

## States

| State | Meaning |
|-------|---------|
| `unprovisioned` | No household account exists for this person yet |
| `ready` | Account created; a scannable code has been issued |
| `pending` | The person has the code but has not completed sign-in on their device |
| `connected` | The media server confirms the device registered a session |
| `failed` | The hand-off did not complete and the reason is known |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Person has not finished the on-device step | Report `pending`, not `failed`; the proof is inconclusive until they act. |
| Client does not support deep links | Fall back to a code encoding just the server address; typing is reduced, not eliminated. |
| Person picks a proprietary client | Allow it but flag it as not open-source; never present it as the recommended path. |
| Code-authorisation flow requires human approval | Guide it and wait; never auto-approve, since that defeats its purpose. |
| Media server unreachable from the device | Surface it as a reachability problem ([I1](../i-remote-access/i1-remote-access.md)), not a client fault. |
| Account already exists for the person | Reuse it; do not create a second identity for the same household member. |
| The QR is intercepted/shared | It leads only to the server address and an account that still requires the person's own sign-in; it is not a bearer credential. |
| Device registers then the person signs out | Reflect the current session state honestly rather than a stale `connected`. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **G9-R1** | A household member's account MUST be provisioned through the media server as one household identity ([D6](../d-content/d6-household-identity.md)) before a device is handed over. |
| **G9-R2** | The tool MUST issue a per-person scannable code encoding the server address, and a deep link where the client supports one. |
| **G9-R3** | Where the media server offers a code-authorisation sign-in, the tool MUST guide it and MUST NOT auto-approve on the person's behalf. |
| **G9-R4** | Recommended clients MUST be open-source; a proprietary client MAY be named but MUST be flagged as not open-source and MUST NOT be the default. |
| **G9-R5** | After hand-off the tool MUST query the media server and assert the new device or session registered, rather than assuming it. |
| **G9-R6** | An incomplete on-device step MUST be reported as `pending`, distinct from `failed`. |
| **G9-R7** | A client without deep-link support MUST fall back to a code encoding the server address. |
| **G9-R8** | An existing account for the person MUST be reused; the tool MUST NOT create a duplicate household identity. |
| **G9-R9** | The scannable code MUST NOT be a bearer credential; it MUST still require the person's own sign-in. |
| **G9-R10** | A device unreachable from its network MUST be reported as a reachability problem, not a client fault. |
| **G9-R11** | Session state MUST be reflected honestly; a signed-out device MUST NOT continue to read as connected. |
| **G9-R12** | Provisioning, code issue, and the connection proof MUST each be reachable non-interactively. |

## Related

- [G6 Client app guidance](g6-client-apps.md) — which apps to use
- [D6 Household identity & invitations](../d-content/d6-household-identity.md) — the one account this signs into
- [I1 Remote access for the household](../i-remote-access/i1-remote-access.md) — the reachability this rides on
- [D4 Household request flow](../d-content/d4-request-flow.md) — what the person does once connected
