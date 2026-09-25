---
id: N12
title: Running out of room
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P3
labels: [mobile, storage, queue, ux]
requires: [N1, D5]
relates: [C5, H1, H6, N2, N6]
---

# N12 — Running out of room

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

A disk filling up is the most ordinary way a media stack stops working, and the
warning arrives on a phone.

What an operator wants at that moment is not a bar chart. It is *what can I
delete, and what does deleting it cost me* — and the stack already knows, per
candidate, in more detail than most people would guess. None of it is reachable
from anywhere but the machine.

Deleting things is also the one place on this surface where a wrong tap is
expensive and irreversible, so the requirements below are mostly about making
the cost legible before the tap rather than afterwards.

## Behaviour

### A candidate's standing is what decides whether deleting it is safe

The contract says of each thing it could remove whether it was **never
imported**, is **still seeding** — with the ratio it has reached — or has been
**left alone**. These are not degrees of the same thing.

Something never imported is a download that never became part of the library and
is usually free to go. Something left alone is finished with. **Something still
seeding is being shared, and removing it stops that** — which on a private
tracker is not a tidy-up, it is a ratio the operator cannot get back and may be
held to.

The app shows which, always, and shows the ratio where there is one.

### The cost of removing something is shown before it is removed

Each candidate carries what removing it would mean. That is stated with the
candidate, not behind a confirmation — a confirmation that appears after the
decision has been made in the operator's head is a speed bump rather than
information.

### Removing is agreed to, not defaulted

The contract carries an agreement for these operations. Nothing here is a
one-tap action, nothing is pre-selected, and the app never proposes a set to
remove — proposing is deciding, and this is the operator's decision.

### What is taking room is answered by category, not by file

Where the space has gone is a question about kinds of thing, and the contract
answers it that way. An operator does not want a directory listing; they want to
know whether it is the library, the landing area, or something they had
forgotten about.

### Stopping seeding is its own act, with its own cost

Stopping sharing something is not the same as deleting it, and the contract
keeps them apart. The app does too, and says what stopping costs — because the
reason to stop is usually space and the cost is usually a ratio, and an operator
trading one for the other should see both numbers.

### A rehearsed removal removed nothing

Removal can be rehearsed, and a rehearsal is labelled as one (`N6-R1`). This is
the surface where believing a rehearsal was real is most expensive: an operator
who thinks they freed forty gigabytes and did not will find out when the disk
fills again.

### Nothing here deletes the operator's media on its own initiative

The app removes what an operator chose, and nothing else. It does not tidy, it
does not suggest, and it does not act on a threshold.

## States

| State | Meaning |
|-------|---------|
| Comfortable | There is room. Candidates are still listed, because the question gets asked before it is urgent. |
| Tight | Space is low, with what is taking it and what could go. |
| Full | Out of room, with what the stack has stopped doing about it. |
| Rehearsed | A removal that removed nothing, labelled as such. |
| Unknown | Space or candidates could not be read. Never rendered as comfortable. |

## Edge cases

- **A candidate that is both never imported and still seeding.** The standing the
  contract gives is what is shown; the app does not reconcile the two itself.
- **A ratio of zero on something recently grabbed.** Shown as it is. A recently
  grabbed thing has not had time to share, and hiding the zero would make the
  safest-looking candidate the most costly.
- **Space freed by something other than the operator.** Reported as a change, not
  as the result of their action.
- **A disk that filled while the app was closed.** The state is shown as current,
  not as new since last time.

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N12-R1** | Every candidate for removal MUST be shown with its standing, and *never imported*, *seeding* and *left alone* MUST NOT be flattened into one another. |
| **N12-R2** | Where a candidate is seeding, its ratio MUST be shown. |
| **N12-R3** | What removing a candidate would cost MUST be shown with the candidate, and MUST NOT appear only in a confirmation. |
| **N12-R4** | The app MUST NOT pre-select candidates for removal or propose a set to remove. |
| **N12-R5** | Removal MUST be agreed to explicitly, and MUST NOT be reachable as a single undifferentiated action. |
| **N12-R6** | What is consuming space MUST be shown by the categories the contract gives, and MUST NOT be rendered as a file listing. |
| **N12-R7** | Stopping seeding MUST be shown as distinct from removing, with what stopping costs. |
| **N12-R8** | A rehearsed removal MUST be labelled as a rehearsal (`N6-R1`) and MUST NOT be reported as space freed. |
| **N12-R9** | The app MUST NOT remove anything on its own initiative, including on a threshold. |
| **N12-R10** | Space that could not be read MUST be told apart from space that is comfortable. |

## Related

- [N1](n1-companion-app.md) — connecting, parity, and what the app may claim
- [N2](n2-operator-companion.md) — a disruptive action states what it disturbs
- [N6](n6-taking-a-copy.md) — what a rehearsal may not look like
- [D5](../d-content/d5-disk-space.md) — what is taking room and what could go
- [C5](../c-trust/c5-storage.md) — the data location, and losing it
- [H1](../h-glue/h1-cross-seed.md) — why something is still seeding
- [H6](../h-glue/h6-library-cleanup.md) — tidying the library
