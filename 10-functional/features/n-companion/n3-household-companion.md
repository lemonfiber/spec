---
id: N3
title: The household's companion
kind: feature
area: N
audience: household
status: draft
maturity: planned
priority: P2
labels: [mobile, household, ux]
requires: [N1, D4, D6]
relates: [D7, D8, G5, G6, G9]
---

# N3 — The household's companion

**Status:** Draft · **Audience:** Household · **Area:** N — Companion

---

## Purpose

The other half of the same application, for the people who did not build the
stack and should never have to think about it.

A household member wants three things: to ask for something, to know whether it
is coming, and to find it when it arrives. They do not want a dashboard, and they
must never be shown a control that would let them stop the stack.

This exists in one app with [N2](n2-operator-companion.md) rather than as a
second product because a household is not two populations — the operator is
usually also a member, and asking somebody to install two apps to watch a film
and to fix the machine that serves it is a worse answer than asking who is
signing in.

## Behaviour

### The credential decides the application

A household identity ([D6](../d-content/d6-household-identity.md)) signs in and
gets this. An operator signs in and gets [N2](n2-operator-companion.md) as well.
There is no setting that switches between them, and no build that contains only
one.

### Entitlement is the core's answer, never a hidden button

What a member may do is decided by the core and rendered here. The app does not
implement a permission model of its own, and a control absent from this
application is absent because the core said so.

That distinction matters the day it is wrong: a bug that shows a control must
still be refused by the core, and never merely by the app having drawn it.

### Asking for something

A member searches, finds a title, and asks for it ([D4](../d-content/d4-request-flow.md)).
What happens next is stated honestly at the point of asking: whether it needs
approval, and whether they have allowance left
([D7](../d-content/d7-approval-quotas.md)).

Somebody who has run out is told so before they ask, not after.

### Knowing whether it is coming

A request they made carries its state in their terms — waiting on somebody,
approved and being fetched, here, or refused with the reason that was given. Not
a pipeline stage, and not a percentage that means nothing to them.

### Finding it when it arrives

The app does not play media. It hands off to whichever client the household uses
([G6](../g-ux/g6-client-apps.md)), which is a link and a hand-off rather than a
second player nobody asked for.

### What a member is never shown

No lifecycle controls, no logs, no credentials, no other member's requests, no
diagnostics. Where a member's own request failed for a reason that is really a
stack fault, they are told it did not work and that the operator has been told —
never given the operator's error.

### Parental controls are honoured, not re-implemented

What a member may watch or ask for is already decided
([D8](../d-content/d8-parental-controls.md)). The app renders those limits and
does not hold a second copy of them.

## States

| State | Meaning |
|-------|---------|
| Signed in as a member | The household application. |
| Signed in as the operator | Both applications, with the operator's surface reachable. |
| No allowance left | Asking is declined with when it resets, before a search happens rather than after. |
| Request waiting | Somebody has to approve it, and the app says so. |
| Request refused | Refused, carrying the reason that was given. |
| Request fulfilled | Here, with a hand-off to a client that plays it. |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| The stack is unreachable | Their own requests are shown from the last read, marked with when. Asking for something new is declined rather than queued, because a queued request is a promise the app cannot keep. |
| A member's request failed because the stack is broken | They are told it did not work and that the operator has been told. They are not shown the fault. |
| A member is also the operator | One sign-in, both applications. They are not asked to choose a mode. |
| A title is already held | Said so before they ask for it again. |
| A member is removed from the household while signed in | The next call is refused by the core, and the app returns to signed-out rather than continuing to render what it had. |
| Parental limits hide a title | It is not shown. The app does not display a title it then refuses to request. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N3-R1** | The application a person is given MUST be decided by the identity that signed in, and MUST NOT be a setting or a separate build. |
| **N3-R2** | The app MUST NOT implement its own permission model; what a member may do MUST be the core's answer. |
| **N3-R3** | A control a member is not entitled to MUST be refused by the core if it is ever reached, and MUST NOT rely on the app having omitted it. |
| **N3-R4** | Before a member asks for something, the app MUST state whether it needs approval and whether they have allowance left. |
| **N3-R5** | A member whose allowance is spent MUST be told before asking, with when it resets. |
| **N3-R6** | A member's own requests MUST carry their state in household terms, and MUST NOT expose pipeline internals. |
| **N3-R7** | A refused request MUST carry the reason that was given. |
| **N3-R8** | The app MUST NOT play media; it MUST hand off to a household client. |
| **N3-R9** | A member MUST NOT be shown lifecycle controls, logs, credentials, diagnostics, or another member's requests. |
| **N3-R10** | Where a member's request failed because of a stack fault, the app MUST tell them it did not work and that the operator has been told, and MUST NOT show them the fault. |
| **N3-R11** | Parental limits MUST be rendered from the core's answer, and the app MUST NOT hold a second copy of them. |
| **N3-R12** | While the stack is unreachable, asking for something new MUST be declined rather than queued. |
| **N3-R13** | An identity removed from the household MUST result in a signed-out app at the next refused call, and MUST NOT continue to render what was already loaded. |

## Related

- [N1](n1-companion-app.md) — connecting, and what the app may claim
- [D4](../d-content/d4-request-flow.md) — the request flow rendered here
- [D6](../d-content/d6-household-identity.md) — who is signing in
- [D7](../d-content/d7-approval-quotas.md), [D8](../d-content/d8-parental-controls.md) — allowance and limits
- [G6](../g-ux/g6-client-apps.md), [G9](../g-ux/g9-mobile-handoff.md) — the clients this hands off to
