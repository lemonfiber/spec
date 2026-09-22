---
id: N6
title: Taking a copy, and putting it back
kind: feature
area: N
audience: operator
status: draft
maturity: planned
priority: P2
labels: [mobile, storage, updates, ux]
requires: [N1, E3]
relates: [A4, A6, A7, E4, N2]
---

# N6 — Taking a copy, and putting it back

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Backups are the thing an operator thinks about at the worst possible moment, and
the companion is where they are when that moment arrives.

[N2](n2-operator-companion.md) already covers undoing *an update* — a rollback
puts the previous version back, a restore puts back what was there, and
flattening the two into *undo* would promise something the app cannot tell it
has. This is the rest of it: taking a copy when nothing is wrong, putting one
back when something is, reversing an action that was not an update, and seeing
what the stack is holding on the operator's behalf.

It is also the requirement the companion's own `backups` module has been waiting
for. That module is deliberately empty, and says so: nothing in `N1`–`N4` asked
this app to do anything with a snapshot, so it is a held name rather than
abandoned work. `N1-R17` is why it stayed empty — a field wants a requirement
before it wants a surface — and this is that requirement.

## Behaviour

### A rehearsal is not the thing, and never looks like it

Taking a copy, reversing an action and wiring a service can all be *rehearsed* —
run to find out what would happen, changing nothing. The contract carries that as
a flag on the answer, and an app that dropped it would show an operator the
report of a backup that does not exist.

So a rehearsal is labelled as one wherever its result is shown, and nothing about
it is phrased in the past tense.

### The scope is stated before it happens, not after

A copy is of the whole stack, of one service, or of an existing project on the
machine. These are different undertakings and the operator agrees to one of them,
so the scope is named before the work starts and again on the result.

### What a copy removed is part of what it did

Taking a new copy can prune old ones. That is housekeeping the operator did not
ask for individually and would not otherwise see, and it is reported with the
copy rather than discovered later by an archive being missing.

### A copy that is running is not a copy that is stuck

The contract says how a copy is progressing and whether it is being paced
deliberately. An operator watching a long copy on a phone needs those apart: one
is working, the other is not, and the difference is the whole reason to look.

### A restore says where it put things

Putting a copy back can land data somewhere other than where it came from. Where
the contract says so, the app says so — a restore that silently relocated a
library is a restore the operator will believe failed.

### An undo says what it could not reverse

Reversing an action is not all-or-nothing. The contract carries what was
reversed and what was `left`, with the reason for each. **The part that was left
is the part worth reading**, and the app leads with it: an operator who believes
a thing was undone and finds half of it still there has been told something
false.

### What the stack is holding is shown, and secrets are named without being shown

The stack keeps things on the operator's behalf, each with where it is and why.
Some of them are secret. The app says one exists and what it is for, and does not
render its value — which is the same line `N2` already draws, where nothing edits
a credential's value over a LAN.

### Resetting configuration is a diff, not a promise

Putting settings back is described by what changed and what connections went with
it. The app shows that rather than a reassurance, because *reset* means very
different amounts depending on what had been set.

### None of this is first-run setup

`N1-R4` declines first-run setup with its reason, and nothing here crosses that
line: a stack must exist and be paired before any of this is reachable.

## States

| State | Meaning |
|-------|---------|
| Idle | No copy or restore is running. What exists is listed. |
| Rehearsing | A run is in progress that will change nothing, and is labelled so throughout. |
| Working | A copy or restore is running, with how far it has got. |
| Paced | Running, deliberately slowed. Distinguished from stalled. |
| Partial | An undo or restore finished with things it could not do, each named with why. |
| Unknown | The archives or the stored list could not be read. Never shown as empty. |

## Edge cases

- **A restore offered where the stack named neither rollback nor restore.** Nothing
  is offered, for the reason `N2` already gives: an undo that is not there is
  worse than none, because it is what somebody agreed on the strength of.
- **An archive list that is empty and an archive list that could not be read.**
  These are different answers and the app never renders the second as the first.
- **A copy pruned the only other copy.** Reported as part of what the copy did,
  because an operator holding one copy and believing they hold two is the state
  this surface exists to prevent.
- **A secret whose value the stack would return.** The app does not render it
  even where the contract carries it.

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N6-R1** | A rehearsed run MUST be labelled as a rehearsal wherever its result is shown, and MUST NOT be described in the past tense as though it had happened. |
| **N6-R2** | The scope of a copy or a restore MUST be stated before it starts and again on its result, naming whether it is the whole stack, one service, or an existing project. |
| **N6-R3** | Copies removed by taking a new one MUST be reported with that copy, and MUST NOT be left to be discovered by an archive being absent. |
| **N6-R4** | A running copy MUST show how far it has got, and a deliberately paced one MUST be distinguishable from a stalled one. |
| **N6-R5** | Where a restore put data somewhere other than where it came from, the app MUST say so. |
| **N6-R6** | An undo MUST name what it could not reverse and why, and MUST NOT present a partial reversal as a complete one. |
| **N6-R7** | The app MUST show what the stack is holding and why, and MUST NOT render the value of anything the contract marks secret. |
| **N6-R8** | Resetting configuration MUST be described by what changed and which connections went with it, rather than by a reassurance. |
| **N6-R9** | An empty list of archives MUST be told apart from a list that could not be read. |
| **N6-R10** | Where the stack offers neither a rollback nor a restore, the app MUST offer neither, and MUST NOT present one as the other (`N2`). |
| **N6-R11** | Nothing on this surface MUST offer first-run setup (`N1-R4`). |

## Related

- [N1](n1-companion-app.md) — connecting, parity, and what the app may claim
- [N2](n2-operator-companion.md) — undoing an update, and why the two ways differ
- [E3](../e-maintenance/e3-backup-restore.md) — what a copy is and what it covers
- [E4](../e-maintenance/e4-rollback.md) — putting a version back
- [A4](../a-getting-started/a4-reconfiguration.md) — changing settings, and reverting them
- [A6](../a-getting-started/a6-uninstall.md) — what is left behind when the stack goes
- [A7](../a-getting-started/a7-credential-management.md) — what is held, and where
