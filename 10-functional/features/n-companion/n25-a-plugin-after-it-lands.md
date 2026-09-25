---
id: N25
title: A plugin after it lands
kind: feature
area: N
audience: operator
status: draft
maturity: planned
priority: P3
labels: [mobile, extensibility, ux]
requires: [N1, N5, F5, F6]
relates: [N6, N11, N20]
---

# N25 — A plugin after it lands

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

[N5](n5-connecting-the-stack.md) makes installing a plugin a companion act: the
catalogue, what vouches for a plugin, an install in progress, a refused one.
[N20](n20-what-a-plugin-may-send.md) keeps what a plugin would send off the
machine apart from the install that wants it. Neither says what happens next.

[F6](../f-extensibility/f6-plugin-lifecycle.md) does: an install is rehearsed
before it is written, verified after, and reversed if either fails; an update is
one account and one reversal; a removal is a rollback with a name on it.
[F5](../f-extensibility/f5-plugin-catalogue.md) adds that where a plugin came
from, and whether anybody read it, stays with it for as long as it is installed.
This page is those acts, and that record, from here.

## Behaviour

### A rehearsal says everything the install would do, and asks nothing

Before anything is written, the stack says every change the install makes, in
order and in full paths; every proof it would ask; every bundled setting it
declares it will change; and every capability it would leave contested. The app
shows all four. A rehearsal that showed less than the real run would be a preview
of a different install.

A rehearsal asked no proof, and a proof nobody asked is not a proof that passed.
The app never shows the first as the second.

### Installed means proven and verified, and a failure says what went back

An install is finished when its proofs held and the stack's own checks found
nothing it made worse. Where either failed, the stack puts it back and says what
went back and what did not, with the reason each is still standing. The app
shows that account as it came. *Could not tell* is not *broke*, and a check the
stack could conclude nothing about is shown as that rather than as a failure.

### An update is one thing, with one answer

Moving a plugin from one version to another is rehearsed as one account and put
back as one unit. The app shows both versions, every service that stops for it —
named before any of them does — and, where the new version did not hold, what
putting the old one back came to. The stack is never shown between the two.

### A removal says what it stops and what it leaves unfilled, before it happens

Taking a plugin out stops its services and can leave something asking for a
capability nothing then fills. Both are said before the removal is agreed to.
Afterwards, what was put back and what was not are shown, because a removal that
got as far as the files and no further is a different machine from one that
finished.

### Where it came from, and whether anybody read it, stays on it

Every installed plugin carries the source the operator named, its version, and
whether anybody reviewed it. *Unreviewed* is not a banner at install time; it is
part of the plugin for as long as the plugin is here, and the app shows it on
every appearance.

## States

| State | Meaning |
|-------|---------|
| Rehearsed | What an install, update or removal would do. Nothing written, no proof asked. |
| Installed | Proofs held and the stack's checks found nothing made worse. |
| Put back | Something failed; what went back and what did not are shown. |
| Updating | Between asking and the answer. Never shown as either version. |
| Removed | The record no longer holds it, and its changes went back. |
| Partly removed | Files put back and the record not written. |
| Unknown | The plugin record could not be read. Never shown as none installed. |

## Edge cases

- **A plugin installed from a source that has since gone.** It keeps working
  (`F5-R11`), and is shown with the source it was installed from.
- **An install that would contest a capability the bundled stack fills.** The
  contest is shown in the rehearsal, and answering it is `N5`'s.
- **A reversal that could not finish.** What is still standing is named with its
  reason; the install is not shown as undone.
- **A plugin whose configuration directory still holds what its service wrote
  after an update went back.** Named as still standing.

## Requirements

| ID | Requirement |
|----|-------------|
| **N25-R1** | The app MUST offer rehearsing a plugin install, and the rehearsal MUST show every change in order with its full path, every proof, every bundled setting the plugin declares it will change, and every capability it would leave contested (`F6-R1`). |
| **N25-R2** | A proof that was not asked MUST NOT be shown as passed, and a check the stack could conclude nothing about MUST NOT be shown as failed. |
| **N25-R3** | An install MUST NOT be shown as installed until its proofs held and the stack's own checks found nothing it made worse (`F6-R3`, `F6-R4`, `N5-R11`). |
| **N25-R4** | Where an install was put back, the app MUST show what went back and what did not, with the reason each is still standing, and MUST NOT present a partial reversal as complete (`F6-R5`, `F6-R6`, `N6-R6`). |
| **N25-R5** | The app MUST offer updating a plugin, and MUST show the version it moves from and to and every service that stops for it before it is agreed to; where the update did not hold, it MUST show what putting the previous version back came to (`F6-R8`, `F6-R9`). |
| **N25-R6** | The app MUST offer removing a plugin, and MUST show every service it stops and every capability it would leave unfilled before the removal is agreed to (`F6-R8`, `F6-R11`). |
| **N25-R7** | A removal that put the files back without writing the record MUST be shown as partial, and MUST NOT be shown as removed (`F6-R7`). |
| **N25-R8** | Every installed plugin MUST be shown with the source it was installed from, its version and whether it was reviewed, and an unreviewed plugin MUST be shown as unreviewed wherever it appears (`F5-R5`, `F5-R7`). |
| **N25-R9** | A rehearsed install, update or removal MUST be labelled as a rehearsal (`N6-R1`). |
| **N25-R10** | A plugin record that could not be read MUST be told apart from there being no plugins installed. |

## Notes

**None of this can be answered while nothing serves it.** The `plugins`
envelope is published and generated into the SDK, and no HTTP route produces it:
the action route accepts no plugin verb, and the read table serves no plugin read
([the register](../../../90-appendix/what-the-companion-does-not-read.md) records
this). `N5-R10` and `N5-R11` wait on the same read. The rows stand as written,
because the envelope already describes what they need.

| Row | What `plugins` carries | Not carried |
|---|---|---|
| `N25-R1` | `install.changes` (`path`, `puts`), `install.proofs`, `install.overrides`, `install.contests` | — |
| `N25-R2` | `proofs[].came_to`, absent where nothing was asked; `verified.broke` and `verified.unsettled` apart | — |
| `N25-R3` | `install.recorded`, `install.proofs[].came_to`, `install.verified` | — |
| `N25-R4` | `install.reversed`: `reversed`, `left` with `because`, `noted` | — |
| `N25-R5` | `update`: `from`, `to`, `interrupts`, `install`, `stopped`, `restored`, `went_back` | — |
| `N25-R6` | `removal`: `interrupts`, `leaves` | — |
| `N25-R7` | `removal.removed` and `removal.went_back`, apart | — |
| `N25-R8` | `installed[]`: `from`, `version`, `declared.reviewed`, `declared.upstream` | The revision the source was at and what signed it (`F5-R7`). Whether an origin can still be fetched (`F5-R11`) |
| `N25-R9` | `install.recorded`, `removal.removed`, and `proofs[].came_to` absent on a rehearsal | A single flag saying a run was a rehearsal |
| `N25-R10` | — | Whether the record was read: `installed` is a list, and an empty one is the only answer the envelope gives |

## Related

- [N1](n1-companion-app.md) — parity, and what the app may claim
- [N5](n5-connecting-the-stack.md) — the catalogue, and installing
- [N20](n20-what-a-plugin-may-send.md) — what a plugin may send, and may never run
- [N6](n6-taking-a-copy.md) — what a reversal owes, and a rehearsal's label
- [N11](n11-the-record.md) — the record every change is journalled in
- [F5](../f-extensibility/f5-plugin-catalogue.md) — the catalogue and what vouches for a plugin
- [F6](../f-extensibility/f6-plugin-lifecycle.md) — the plugin lifecycle
