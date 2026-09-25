---
id: N18
title: Running part of it on purpose
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P2
labels: [mobile, ux, observability]
requires: [N1, B1]
relates: [B2, B3, N2, N16]
---

# N18 — Running part of it on purpose

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

[B1](../b-running/b1-forms.md) gives the operator a vocabulary for *"I only need
part of this"*. A **form** is the noun they use — `library` serves what exists,
`hunt` searches and grabs, `full` is the lot — and the services that start are
whatever those forms expand to, intersected with what the operator actually
configured.

This page is what that looks like on a screen small enough to show a count and
not much else.

**The failure to avoid is a number.** Six services of eighteen is not a stack
that is four-fifths broken; it is a stack doing exactly what somebody asked for.
A surface that renders a partial stack as degraded — an amber badge, a
completion figure, twelve things listed as absent — is wrong about the product
in the way that is hardest to argue with, because it looks like diligence.

## Behaviour

### A partial stack is an intent, not a shortfall

What is running is shown as the forms that were asked for and the services those
expand to. Both layers are needed: services alone lose why any of them is there,
and forms alone lose what is actually up.

Nothing missing from an active form's expansion is reported as missing. A
service nobody asked for is not absent — it was never wanted.

### A service that was filtered out says so, and says why

A form's profile set is intersected with what the operator configured, so
`lemonfiber up dl` on a Usenet-only machine starts SABnzbd and does not attempt
Gluetun with credentials that do not exist.

On a phone, *did not start* and *was filtered out because you have no torrent
credentials* arrive as the same silence and mean entirely different things. One
is a fault to chase; the other is the feature working. The reason travels, or
the operator goes looking for a problem that is not there.

### What a form would do is shown before it does it

A form is introspectable: the profiles it expands to, the services that would
start, which would be filtered and why, and roughly what it would cost to run.
That is a rehearsal, and it is labelled as one — never phrased as though those
services had started.

The footprint is an estimate the stack declares, not a measurement of what is
running. Shown as the second, it is a number the operator will believe and act
on.

### Forms compose, and the same service is not counted twice

Several active forms can include one service, and it starts once. The app shows
it once, and names every form that asked for it — because *why is this running*
has as many answers as there are forms claiming it, and removing one of them
does not necessarily stop it.

### The vocabulary is the stack's, not the app's

Forms are data in the stack's manifest rather than code, so they can be added or
changed without a release of anything. An app holding its own list would be a
second copy that goes out of date silently — and the first thing the operator
would notice is a form of their own that the app does not believe exists.

### The app shows what is running; it does not decide it

Starting and stopping is the operator's, through [N2](n2-operator-companion.md),
and nothing here starts a form because a screen was opened or a threshold was
crossed.

## Requirements

| ID | Requirement |
|----|-------------|
| **N18-R1** | What is running MUST be shown as both the forms asked for and the services they expand to, and a service MUST NOT be shown without what brought it. |
| **N18-R2** | A stack running part of itself MUST NOT be presented as degraded, incomplete, or as a proportion of a whole; a partial stack is the operator's intent. |
| **N18-R3** | A service filtered out of a form MUST be shown as filtered with the reason, and MUST NOT be omitted or rendered as failed. |
| **N18-R4** | Before a form is started, what it would start and what it would filter out MUST be shown with the reason for each, labelled as a rehearsal (`N6-R1`) and never phrased as having happened. |
| **N18-R5** | A footprint MUST be shown as the estimate the stack declares, and MUST NOT be presented as a measurement of what is running (`N10-R4`). |
| **N18-R6** | Where several active forms include one service, the app MUST show it once and MUST name every form that asked for it. |
| **N18-R7** | The app MUST hold no copy of the form or profile vocabulary; the names, their members and their intent MUST be the stack's answer. |
| **N18-R8** | The app MUST NOT start or stop a form on its own initiative, including on a schedule or a threshold (`N2`). |
| **N18-R9** | Forms or profiles that could not be read MUST be told apart from none being active. |

## Notes

`N18-R2` is the row the rest of the page is arranged around, and it is a
prohibition rather than a feature because the failure it names is one a
well-meaning surface arrives at on its own. Every instinct a dashboard has —
show progress, show completeness, flag what is absent — produces it.
