---
id: N20
title: What a plugin may send, and what it may never run
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P2
labels: [mobile, security, ux]
requires: [N1, F8]
relates: [F3, F11, N5, N10, N2]
---

# N20 — What a plugin may send, and what it may never run

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

[F8](../f-extensibility/f8-recipes.md) lets a plugin configure the thing it
installed without becoming a way to move an operator's secrets somewhere they
did not agree to. It draws that line in one sentence this page exists to keep on
a small screen:

> A single yes to an installation is consent to the installation.

A pair that carries a value to an external host — *this plugin will send your
media server's API key to `plex.tv`* — is stated at the rehearsal and approved as
itself. Everything else a rehearsal says is about a change to the operator's own
machine. **This is the only part about something leaving it.**

A phone is where that distinction is most expensive to lose, because a phone is
where one large button covering everything is the natural design. The surface
that most wants a single *Install* is the surface that must not have one.

[F11](../f-extensibility/f11-executing-contributed-code.md) is the other half,
and it is shorter: contributed code is not executed, and no opt-in, sandbox or
capability grant makes it executable. The companion's only job there is not to
become the route by which that stops being true.

## Behaviour

### What leaves the machine is agreed to on its own

A value going to an external host is named — which value, to which host — in
terms the operator can weigh, and is agreed to separately from the installation
that wants it. Two agreements, because they are two decisions: one is about
changing this machine, and the other is about somebody else's.

A surface offering one button for both has not obtained consent for the second.
It has obtained consent for the first and taken the second along with it.

### A destination is a name, and is shown as one

A manifest names an in-stack destination by service id and an external one by a
DNS name; an IP literal, a network range or a bare host port is refused outright.
The app shows the name the manifest gave. A resolved address shown in its place
would be the app answering a question the operator did not ask, and hiding the
one they did — *where is this going* is a name, not a number.

Names close the manifest; they do not close DNS. Where an external name answered
with a loopback, private or link-local address, the call is refused — the
manifest said the destination was outside and the answer came from inside, and
that contradiction is the refusal rather than something to reconcile. Shown as a
network error with a retry, it becomes a button that keeps trying to reach a
household's router.

### A recipe is a sequence, and is shown as one

A rehearsal lists every step in the order the recipe gives, labelled as a
rehearsal. An app that summarised it — *configures Plex* — would have removed the
only thing an operator can actually judge.

Where a plugin names an adapter for a flow that cannot be honestly expressed as
calls and captures, the app says which adapter, and that it is one lemonfiber
implements and ships rather than anything the plugin supplied.

### Nothing a plugin wrote runs here

The app does not execute code a plugin supplied, does not offer to, and offers
no setting, opt-in or grant that would. A plugin declaring native or executable
content is shown as refused, with the reason, rather than offered.

This is not a policy the app enforces on the core's behalf — the core already
refuses it. It is a promise that the app does not grow a second door.

## Requirements

| ID | Requirement |
|----|-------------|
| **N20-R1** | A value a plugin would send to an external host MUST be stated as what it is and where it would go, in terms the operator can judge. |
| **N20-R2** | Such a value MUST be agreed to as itself, and MUST NOT be agreed to as a consequence of agreeing to an installation; one agreement MUST NOT cover both. |
| **N20-R3** | A destination MUST be shown as the name the manifest gave, and MUST NOT be shown as a resolved address. |
| **N20-R4** | Where a call was refused because an external name answered from inside the network, the app MUST show that refusal and its reason, and MUST NOT render it as a network error to retry. |
| **N20-R5** | A rehearsed recipe MUST show every step in the order the recipe gives, labelled as a rehearsal (`N6-R1`), and MUST NOT be summarised into an outcome. |
| **N20-R6** | Where a plugin names an adapter, the app MUST show which one, and that it is lemonfiber's rather than the plugin's. |
| **N20-R7** | The app MUST NOT execute content a plugin supplied, MUST NOT offer to, and MUST NOT present any opt-in, sandbox or capability grant that would (`F3-R6`). |
| **N20-R8** | A plugin declaring native or executable content MUST be shown as refused with the reason, and MUST NOT be offered for installation (`F3-R7`). |
| **N20-R9** | A refusal the core gave about a plugin MUST carry the core's own reason (`N5-R10`). |
| **N20-R10** | Recipes, pairs, destinations or adapters that could not be read MUST be told apart from there being none. |

## Notes

`N20-R2` is the row this page is for. It is written as a prohibition on
*combining* two agreements rather than as a requirement to ask twice, because
the failure is not a missing prompt — it is a present one that covers more than
the operator read it as covering.
