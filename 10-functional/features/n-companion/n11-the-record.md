---
id: N11
title: What was done, and where it came from
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P3
labels: [mobile, observability, ux]
requires: [N1, E4]
relates: [F7, G8, H8, N2, N6]
---

# N11 — What was done, and where it came from

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Two records the stack keeps, both answering questions that arrive at bad moments
and neither reachable from a phone.

*What happened to this thing* is asked when something worked yesterday and does
not today. The stack keeps every change with what it did, to what, why, and how
to reverse it — which is a better record than most software keeps of itself, and
it is invisible away from the machine.

*Where did this service come from* is asked when somebody wants to know what
they are actually running: which image, pinned to what, under whose licence.

Neither is a log. `N2` already owns logs, and is right that they are read rather
than tailed. These are decisions and origins, which are a different kind of
thing and want a different screen.

## Behaviour

### The record is bounded, and the boundary is stated

History goes back a certain distance and no further. An operator scrolling to
the end and finding nothing must be told they reached the edge of what is kept,
because *nothing before this* and *nothing happened before this* are opposite
claims and the screen must not let one be read as the other.

### A change carries how to reverse it

Every change says what would undo it. That is the record's most useful field and
the link to [N6](n6-taking-a-copy.md): looking up what went wrong and being able
to act on it from the same place is the difference between a record and a museum.

Where a change cannot be reversed, that is said rather than the field being
quietly absent.

### A change that happened with others is not a change that happened alone

The contract says how many changes accompanied each one. Eleven things changing
at once is an event; one thing changing is a decision, and an operator looking
for what broke their stack needs to know which they are reading.

### Why it happened, where the stack knows

A change can carry the reason it was made, and where it does the reason is shown.
It is the difference between *the quality profile changed* and *the quality
profile changed because the update you agreed to at nine o'clock replaced it*.

### What is running is named by what it actually is

A service is an image, pinned to a digest, from an upstream, under a licence.
All four are what an operator is entitled to know about software running on
their own machine, and the pin is the one that says whether *the latest version*
means anything.

### A licence is shown because it is sometimes the answer

Most are open and unremarkable. Some are not, and an operator running something
proprietary should not have to find that out from somewhere else — it is carried
on the wire and it is shown.

### Neither of these is a log

Logs are `N2`'s, and are read rather than tailed. A change record is a list of
decisions and a provenance list is a list of origins; rendering either as a
stream of lines would make both unusable for the question they answer.

## States

| State | Meaning |
|-------|---------|
| Recorded | Changes exist within the horizon, newest first. |
| At the horizon | The end of what is kept, said plainly. |
| Empty | Nothing has been done within the horizon. Distinct from unreadable. |
| Unknown | The record or the provenance could not be read. Never rendered as empty. |

## Edge cases

- **A change with no reversal.** Said to have none, rather than the row simply
  lacking a control.
- **A record whose horizon is shorter than the thing being investigated.** The
  app says the change may have happened and fallen off, rather than implying it
  did not happen.
- **A service whose upstream is unreachable.** The pin and the licence are still
  facts and are still shown.
- **Two changes at the same instant.** Ordered deterministically and shown as
  concurrent rather than as one preceding the other.

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N11-R1** | The history's horizon MUST be stated, and the end of what is kept MUST NOT be presentable as nothing having happened. |
| **N11-R2** | A change MUST carry how it would be reversed, and one that cannot be reversed MUST say so rather than omitting the field. |
| **N11-R3** | A change MUST show how many changes accompanied it. |
| **N11-R4** | Where a change carries the reason it was made, that reason MUST be shown. |
| **N11-R5** | A change record MUST NOT be rendered as a log (`N2`). |
| **N11-R6** | A service's provenance MUST show its image, the digest it is pinned to, its upstream and its licence. |
| **N11-R7** | A licence MUST be shown for every service, not only where it is unusual. |
| **N11-R8** | Where an upstream cannot be reached, the pin and the licence MUST still be shown. |
| **N11-R9** | An empty record MUST be told apart from a record that could not be read. |
| **N11-R10** | Changes at the same instant MUST be ordered deterministically and MUST NOT be presented as one preceding the other. |

## Related

- [N1](n1-companion-app.md) — connecting, parity, and what the app may claim
- [N2](n2-operator-companion.md) — logs, which these are not
- [N6](n6-taking-a-copy.md) — reversing what the record names
- [E4](../e-maintenance/e4-rollback.md) — putting a version back
- [F7](../f-extensibility/f7-plugin-provenance.md) — what an install carries with it
- [H8](../h-glue/h8-stats.md) — the other thing the stack remembers
