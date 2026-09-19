---
id: G10
title: The household's web surface
kind: feature
area: G
audience: household
status: draft
maturity: planned
priority: P2
labels: [web, household, ux]
requires: [D4, D6, G1]
relates: [D7, D8, G5, G6, N3]
---

# G10 — The household's web surface

**Status:** Draft · **Audience:** Household · **Area:** G — Cross-cutting UX

---

## Purpose

The same household surface as the companion, in a browser, for the people who
will not install an app.

[N3](../n-companion/n3-household-companion.md) describes what a household member
needs: to ask for something, to know whether it is coming, and to watch it when
it arrives. Nothing about those three is particular to a phone. A member at a
laptop, on a television's browser, or on a borrowed device has the same three
needs and no way to meet them, because the web surface today is the operator's
console and stops there.

[G1](g1-interface-tiers.md) already says every action is available from every
surface and that no surface implements behaviour of its own. This says what that
means for the person who is not the operator: the browser is not a lesser
household surface, and a member who opens it is not asked to install something
before they can be helped.

## Behaviour

### Signing in decides what is shown

One form. A household identity signs in through the same door as the operator
([D6](../d-content/d6-household-identity.md)), and what is drawn afterwards is
decided by who signed in rather than by an address, a mode or a build.

An operator who is also a member sees both and moves between them. This is the
same sentence [N3](../n-companion/n3-household-companion.md) makes about the
companion, and for the same reason: a household is not two populations.

### Entitlement is the core's answer

What a member may do is read from what the core sent. The browser holds no
permission model, computes no role, and hides nothing on its own authority — a
control it may not use is one the core has said so about, and a control it never
received is one the core narrowed away before answering.

### What a member reaches

Their own requests, in household words. What they may ask for, with approval and
allowance stated before they ask. What the household holds. And playing it.

### Playing it

The stream comes from the media server over the local network. Away from that
network it is declined, saying so, rather than buffering against something it
cannot reach.

**A member is handed the service that faces them, not the one that happens to be
the door.** A household reaches two: somewhere to ask for things, and somewhere
to watch them. Which of those is the *front* door is an arrangement the operator
made, and a member with a question about watching does not care. So both are
offered, each with its own address and its own standing — and where one cannot
be reached from where they are, that is said rather than an address handed over
that will not answer.

**What the player may not do is the whole of what it must get right.** It renders
what the core says a member may watch and holds no second copy of it, so an age
limit is never enforced twice and never disagrees with itself. It implements no
part of asking, approving or allowance. A client the household already uses stays
a first-class way to watch ([G6](g6-client-apps.md)); this is a second way, not a
replacement for one.

### What a member is never shown

No lifecycle controls, no logs, no credentials, no diagnostics, no other member's
requests. Where a member's own request failed for a reason that is really a stack
fault, they are told it did not work and that the operator has been told — never
given the operator's error.

## States

| State | What is shown |
|-------|---------------|
| Signed out | The one form, and nothing about the stack. |
| Signed in as a member | Their requests, what they may ask for, what is held, and what plays. |
| Signed in as an operator who is also a member | Both, and a way between them. |
| Nothing has been asked for yet | What to do first, not an empty table. |
| Refused a control | Said, not omitted. A screen that omits is a screen that reads as broken. |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| The stack is unreachable | Their own requests are shown from the last read, marked with when. Asking for something new is declined rather than queued. |
| The media server cannot be reached from this network | Playback is declined, saying the stack cannot be reached from here. Nothing buffers and nothing is queued. |
| A member is removed from the household while signed in | The next call is refused by the core, and the surface returns to signed-out rather than continuing to render what it had. |
| A member opens an address that is not theirs | Refused in the core's words, rather than answered with an empty page. |
| Parental limits hide a title | It is not shown. The surface does not display a title it then refuses to request. |
| The browser is on a phone | The same surface, sized for it. Not a second design and not a prompt to install something. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **G10-R1** | What the web surface shows MUST be decided by the identity that signed in, and MUST NOT be a setting, an address or a separate build. |
| **G10-R2** | The web surface MUST NOT implement its own permission model; what a member may do MUST be the core's answer. |
| **G10-R3** | A control a member is not entitled to MUST be refused by the core if it is ever reached, and MUST NOT rely on the surface having omitted it. |
| **G10-R4** | A member MUST be able to see their own requests, ask for something, see what the household holds, and play it. |
| **G10-R12** | Where the household reaches a service that faces them, the surface MUST be able to hand them its address, whether or not that service is the front door. |
| **G10-R13** | Where a service a member is handed to cannot be reached from where they are, the surface MUST say so, and MUST NOT present an address it knows will not answer. |
| **G10-R5** | Before a member asks for something, the surface MUST state whether it needs approval and whether they have allowance left. |
| **G10-R6** | What a member may watch MUST be the core's answer. The surface MAY render it, and MUST NOT compute, cache or enforce a second copy of it. |
| **G10-R7** | Where the media server cannot be reached, playback MUST be declined with the reason, and MUST NOT be queued or shown as buffering. |
| **G10-R8** | The player MUST NOT implement request, approval or allowance logic of its own. |
| **G10-R9** | A member MUST NOT be shown lifecycle controls, logs, credentials, diagnostics, or another member's requests. |
| **G10-R10** | A refusal MUST be shown as a refusal, and MUST NOT be rendered as an empty result. |
| **G10-R11** | An identity removed from the household MUST result in a signed-out surface at the next refused call, and MUST NOT continue to render what was already loaded. |

## Related

- [N3](../n-companion/n3-household-companion.md) — the same surface, as an app
- [D4](../d-content/d4-request-flow.md) — the request flow rendered here
- [D6](../d-content/d6-household-identity.md) — who is signing in
- [G1](g1-interface-tiers.md) — every action from every surface
- [G6](g6-client-apps.md) — the clients a household already watches on
