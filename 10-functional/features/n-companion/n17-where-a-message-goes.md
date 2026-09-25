---
id: N17
title: Where a message goes
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P2
labels: [mobile, notifications, network, ux]
requires: [N1, B9]
relates: [B5, N4, N10, N16]
---

# N17 — Where a message goes

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

[B5](../b-running/b5-notifications.md) decides what is worth telling somebody
and when. [B9](../b-running/b9-notification-backends.md) decides how the message
actually gets there, and makes one argument this page exists to carry: **an
alert that silently fails to send is worse than no alert**, because it teaches
the operator the stack is quiet when it is actually on fire.

A phone is where that failure lands. It is the device an alert is expected to
arrive on, and the one place where *no notification* and *a notification that
never sent* are indistinguishable from the inside.

### What this app is not

It is not a notification service, and it does not become one.

`B9` refuses a hosted notification plane as a built-in back-end and makes a
self-hostable service the default. The companion holds to that literally: it
ships no push identity, operates no relay, and requires no coordination service
of lemonfiber's between a household's stack and their phones. What delivers a
message is the back-end the operator already configured, and the app subscribes
to it the way any other client would.

That has an honest cost, and stating it is part of the design rather than a
caveat on it. A self-hosted service reaching a sleeping phone is that service's
problem and that service's app, not this one's. So the companion says what its
subscription can and cannot do rather than implying it will always reach
somebody — an app that quietly promises delivery it cannot provide reproduces
exactly the failure `B9` is about, one layer up.

## Behaviour

### Delivery is confirmed or it is not claimed

The stack confirms a message was delivered rather than firing it into the dark,
and that confirmation travels. *Sent* and *confirmed delivered* are different
facts, and the app shows which it has. A message the back-end never acknowledged
is shown as unconfirmed, not as sent.

A back-end configured and never used is a third state again. It looks identical
to a working one right up until the moment it matters.

### Each back-end says what it is and who chose it

The household chooses the channel and the operator owns the policy, so a
back-end carries both: what it is, where it delivers, and whose choice it was.
The distinction matters for the same reason it does anywhere else in this
product — a setting somebody made and a setting nobody made are different
things to act on.

### A hosted back-end says what leaves the device

Where an operator has enabled a hosted service themselves, which `B9` permits as
a manual option and never as a default, the app says what goes out to use it.
That is the same line [N10](n10-nobody-watching.md) draws about every other
outbound connection: what the product does and what somebody's chosen service
does are two lists, and merging them makes the privacy claim untestable.

### The app carries messages; it does not write them

Nothing here originates in the app. It raises no notification of its own, and
what a notification may contain is already settled — no credential, no household
member's name, no requested title.

### A failure carries the back-end's own reason

A delivery that failed says why, in the words the back-end gave. Rendered as a
generic failure with a retry, it becomes an invitation to send the same message
into the same dark.

## Requirements

| ID | Requirement |
|----|-------------|
| **N17-R1** | The app MUST NOT operate, require or ship a notification service, relay or push identity of its own; what delivers a message MUST be the back-end the operator configured. |
| **N17-R2** | Where the app subscribes to a back-end, it MUST state what that subscription can and cannot deliver while the app is not running, and MUST NOT imply delivery it cannot provide. |
| **N17-R3** | A message MUST be shown as delivered only where the contract carries a confirmation, and an unconfirmed message MUST NOT be rendered as sent. |
| **N17-R4** | A back-end that is configured and has never delivered MUST be told apart from one that is delivering. |
| **N17-R5** | Each back-end MUST be shown with what it is, where it delivers, and whether the operator or the household chose it. |
| **N17-R6** | The app MUST NOT set or change a back-end's credential (`N2-R12`), and MUST NOT render its value. |
| **N17-R7** | Where a back-end is a hosted service, the app MUST state what leaves the device to use it, and MUST NOT list it among the connections lemonfiber itself makes (`N10-R1`). |
| **N17-R8** | A notification the app displays MUST carry no credential, no household member's name and no requested title (`N4-R10`). |
| **N17-R9** | The app MUST NOT raise a notification of its own; every one MUST originate in the core's decisions (`N4-R11`). |
| **N17-R10** | A delivery that failed MUST carry the reason the back-end gave, and MUST NOT be rendered as a generic failure to retry. |
| **N17-R11** | Back-ends or delivery records that could not be read MUST be told apart from there being none. |

## Notes

`N17-R1` is the row that decides the shape of everything else here, and it was a
decision rather than a reading: a companion that shipped its own push identity
would be a hosted notification plane in all but name, arriving through the one
surface `B9` did not have in view when it refused one.

**Five of these eleven are waiting on the contract.** `AlertsEnvelope` carries
the preset, what it means and the exceptions an operator has made — which is
what `N10-R8` reads — and nothing about back-ends or delivery, checked against
all sixty-two published envelopes. So `N17-R3`, `N17-R4`, `N17-R5`, `N17-R7` and
`N17-R10` cannot be answered until the contract carries where a message went and
whether it arrived.

That is `B9`'s own subject rather than an extra this page invented, which is why
the requirements stand as written: *an alert that silently fails to send is
worse than no alert*, and a surface cannot say so about a delivery it is never
told the fate of.
