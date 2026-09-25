---
id: N8
title: What comes in, and where it got to
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P3
labels: [mobile, quality, queue, ux]
requires: [N1, D2]
relates: [D9, H6, N2, N3]
---

# N8 — What comes in, and where it got to

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Two questions an operator asks about content, and neither has a surface here.

The first is *what am I asking for* — how good a copy, how big that makes
things, and whether this machine can actually serve it. The second is *where did
the thing I asked for get to*, which is the question
[D9](../d-content/d9-pipeline-trace.md) exists to answer and which arrives most
often when somebody is not at the machine.

[N3](n3-household-companion.md) answers the second question for a **member**, in
household terms and without pipeline internals (`N3-R6`). This is the operator's
version, where the internals are the answer rather than something to be spared.

## Behaviour

### A quality choice is stated in what it costs, not in what it is called

A preset has a resolution and a name, and neither tells an operator what
choosing it does. What does is how much space an hour of it takes, and whether
this machine has to transcode to serve it.

Both are on the wire. The app leads with them, because *1080p* and *this will
use roughly this much and your machine will have to work to play it* are
different sentences and only one is a decision.

### Whether this machine must transcode is a fact about this machine

The contract says whether a choice needs transcoding *here*. That is not a
property of the preset and cannot be worked out from its name, and it is the
difference between a library that plays and one that stutters on the television
it was bought for.

### A disposition is six things, and the app renders which

A choice can be shown, recorded, rehearsed, held, reapplied or about to be
reapplied. These are not degrees of the same thing: *rehearsed* changed nothing,
*held* is waiting, *recorded* is a decision the stack has taken. Flattening them
into saved and unsaved would tell an operator that a rehearsal had taken effect.

### A trace says how sure it is

Where a thing got to is answered with a confidence, and *uncertain* is an answer
rather than a hedge to be dropped. An app that rendered an uncertain trace as a
certain one would be inventing the one thing the operator opened it to find out.

### Outstanding is per episode, and that is the point

A season is not a single state. The contract carries what is had and what is
outstanding episode by episode, each at its own stage — not monitored,
monitored, searching, found, grabbed, downloading — and an operator asking about
a show is asking about the gaps rather than about a percentage.

### A folder that stopped being watched says why

Watching a folder can stop, and the reason it stopped is carried. A watch that
is simply absent from a screen is a watch an operator believes is running.

### Nothing here is the household's answer

What a member sees about their own request is `N3`'s, in household terms and
without the pipeline. This surface is the operator's and shows the pipeline,
and the two are not the same screen with a different filter.

## States

| State | Meaning |
|-------|---------|
| Shown | A choice is being looked at and nothing has been decided. |
| Recorded | The stack has taken the decision. |
| Rehearsed | A run that changed nothing, labelled as such (`N6-R1`). |
| Held | Waiting on something, with what. |
| Certain | The trace is answered with confidence. |
| Uncertain | The trace is answered without it, and says so. |
| Unknown | The trace or the choices could not be read. Never rendered as empty. |

## Edge cases

- **A preset that needs transcoding on this machine and not on another.** The
  answer is about this machine, and the app does not generalise it.
- **A trace for something the stack is not monitoring.** *Not monitored* is a
  stage and is shown as one, rather than as nothing found.
- **A season complete but for one episode.** The gap is what is shown; a
  completion figure would bury it.
- **A watch stopped by the operator and a watch stopped by a fault.** Different
  reasons, shown differently.

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N8-R1** | A quality choice MUST be shown with what an hour of it costs in space, and MUST NOT be presented by name and resolution alone. |
| **N8-R2** | Where the contract says a choice needs transcoding on this machine, the app MUST show that, and MUST NOT present it as a property of the preset. |
| **N8-R3** | A disposition MUST be rendered as the value given, and *rehearsed*, *held* and *recorded* MUST NOT be flattened into one another. |
| **N8-R4** | A trace MUST carry its confidence, and an uncertain trace MUST NOT be rendered as certain. |
| **N8-R5** | Where the contract carries what is outstanding episode by episode, the app MUST show the gaps rather than a completion figure alone. |
| **N8-R6** | A stage the contract names MUST be rendered as that stage, and *not monitored* MUST NOT be rendered as nothing found. |
| **N8-R7** | A watch that has stopped MUST be shown with the reason it stopped, and MUST NOT be omitted from the surface. |
| **N8-R8** | The operator's trace MUST NOT be reused as a member's view of their own request, which is `N3-R6`'s and carries no pipeline internals. |
| **N8-R9** | Choices or a trace that could not be read MUST be told apart from there being none. |

## Related

- [N1](n1-companion-app.md) — connecting, parity, and what the app may claim
- [N2](n2-operator-companion.md) — the verdict, and why a value is never substituted
- [N3](n3-household-companion.md) — the member's version of *where did it get to*
- [D2](../d-content/d2-quality-presets.md) — the presets and what they mean
- [D9](../d-content/d9-pipeline-trace.md) — where a thing got to
- [H6](../h-glue/h6-library-cleanup.md) — watching a folder
