---
id: N16
title: What happened while nobody was looking
kind: feature
area: N
audience: operator
status: draft
maturity: planned
priority: P2
labels: [mobile, observability, queue, ux]
requires: [N1, K2]
relates: [B8, H5, G7, N2, N10]
---

# N16 — What happened while nobody was looking

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Three things in this product happen when the operator is not at the machine: an
outside watcher notices the stack has stopped, the machine restarts and the
stack does or does not come back, and the download queue unwedges itself. All
three are read afterwards, and the companion is where afterwards happens.

They belong on one page because they share a failure. Each of them can go wrong
*quietly* — a monitor that stopped reporting, a boot that brought back four
services of five, a self-heal that could not reach the client it manages — and
each of those silences looks exactly like good news. A surface that cannot tell
*nothing is wrong* from *nothing was measured* turns all three into a stack the
operator believes is fine.

[K2](../k-observability/k2-uptime.md) exists because when the stack's own
reporting is the thing that failed, an outside watcher is the only observer that
can still tell the truth. That argument survives the trip to a phone, and it is
the argument for this page.

## Behaviour

### A second opinion is shown as a second opinion

The outside watcher and the stack's own health view are two observers, and where
they disagree the disagreement is the information. An app that reconciled them
into one verdict would discard exactly the signal the watcher exists to provide,
and would do it silently, because a single verdict looks authoritative.

So both are shown, with which said which.

### A monitor that is not reporting is not a service that is down

These arrive as the same absence and mean opposite things: one is the stack
having stopped, the other is the watcher having stopped. Told apart, the second
is a thing to go and fix; flattened into the first, it is a stack the operator
believes is broken — or, the other way round, a watcher whose silence reads as
all clear.

A heartbeat that has not arrived says how long it has been missing and what it
was covering, because *late* and *never* are different.

### What the watcher could not be set up to check is part of its answer

The stack is honest about how a monitor can be configured, and where a check
could not be made to look at what it should, that is shown instead of its
result. A green tick from a monitor watching the wrong thing is worse than no
monitor, and the operator cannot see which it is.

### Coming back after a restart is stated, including where it cannot be promised

Whether the stack comes back on its own is a fact about this machine and this
platform, not about the product, and where the platform cannot be made to do it
the app says so rather than showing the setting as off. *Off* invites switching
it on; *not available here* invites reading why.

A boot that did not bring everything back names what did not come back. That is
the failure this whole area exists for: nothing errored, nothing was logged
anywhere the operator would look, and it simply stopped working.

### A verification that has not run is not a verification that passed

Post-boot verification is shown with when it last ran. One that has not run
since the last restart is the case the operator most needs to see, and it is
also the one that looks most like success.

### The queue's own repairs are shown before and after, and as what they were

An item about to be acted on carries why it was classified as wedged and how
many strikes it has. Afterwards, removing, blocklisting and re-searching are
three acts rather than one: a blocklist outlives the item, and an operator
reading *cleared* has not been told that something will now never be tried
again.

Where self-healing could not reach what it manages, that is its own answer.
Rendered as nothing needing attention, it is a queue filling up behind a
component that stopped working.

### The app watches; it does not act

Nothing here is the app's decision. It does not clear an item, does not change a
strike count or a grace window, and does not turn autostart on or off on the
operator's behalf. What is configured is the core's, which is the line
[N2](n2-operator-companion.md) already draws.

### None of this is first-run setup

`N1-R4` declines first-run setup with its reason, and reading what setup settled
is not offering it — the distinction `N15` makes.

## Requirements

| ID | Requirement |
|----|-------------|
| **N16-R1** | Where the outside watcher and the stack's own health view disagree, both MUST be shown with which said which, and they MUST NOT be reconciled into a single verdict. |
| **N16-R2** | A monitor that is not reporting MUST be told apart from a service that is down. |
| **N16-R3** | A heartbeat that has not arrived MUST state how long it has been missing and what it was covering. |
| **N16-R4** | Where the contract says a check could not be configured to observe what it should, the app MUST show that rather than the check's result. |
| **N16-R5** | Whether the stack returns after a restart MUST be shown, and where the platform cannot provide it the app MUST say so rather than rendering it as off. |
| **N16-R6** | A restart that did not bring everything back MUST name what did not come back, and MUST NOT be reported as a completed start. |
| **N16-R7** | Post-boot verification MUST be shown with when it last ran, and one that has not run since the last restart MUST NOT be shown as passing. |
| **N16-R8** | An item the queue would act on MUST be shown with why it was classified as wedged and how many strikes it holds, before the action. |
| **N16-R9** | Removing, blocklisting and re-searching MUST be shown as the three acts they are, and MUST NOT be flattened into one. |
| **N16-R10** | Where self-healing could not reach what it manages, that MUST be shown as its own answer and MUST NOT be rendered as nothing needing attention. |
| **N16-R11** | A rehearsed self-heal MUST be labelled as a rehearsal (`N6-R1`) and MUST NOT be reported as items cleared. |
| **N16-R12** | The app MUST NOT act on a wedged item, change a strike count or a grace window, or turn returning-after-restart on or off (`N2`). |
| **N16-R13** | Uptime, restart or queue state that could not be read MUST be told apart from there being nothing wrong. |
| **N16-R14** | Nothing on this surface MUST offer first-run setup (`N1-R4`). |

## Notes

Nothing here asks the core for a capability it does not have. Where a field this
page needs turns out not to be carried, the work stops and the gap is raised
against the contract rather than approximated from a neighbouring value — which
is `N1-R17`, and is the rule that keeps this surface honest about what it
actually knows.
