---
id: N23
title: What keeps going, and what stopped moving
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P2
labels: [mobile, queue, ux]
requires: [N1, B10, C7]
relates: [N2, N8, N10, N16]
---

# N23 — What keeps going, and what stopped moving

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Two things a stack does while nobody is looking, and both fail by going quiet.

[B10](../b-running/b10-hosting.md) hands a long-running command — the guard on
the data location, the clock that closes requests nobody ruled on — to the
machine's own service manager, so it outlives the terminal that started it.
[N10](n10-nobody-watching.md) already shows what each one guarantees and whether
it is running (`N10-R10`). What it does not do is let the operator hand one over,
or take one back, from here.

[C7](../c-trust/c7-queue-health.md) reads the whole queue at once and says what
has stopped and why. [N2](n2-operator-companion.md) makes stuck downloads
reachable (`N2-R9`) and [N16](n16-nobody-was-looking.md) shows what self-healing
did about them. What neither says is how a stopped queue reads on a small screen
without losing the one distinction that makes it worth reading: *which kind* of
stopped, and whether the cause is one thing or twenty.

## Behaviour

### Hosting a command is offered here, as an act of its own

The operator names a command and asks for it to be kept running. That is the
whole request, and it is never arrived at as a side effect of anything else
(`B10-R6`). Taking one back is offered the same way.

What installing does to the machine is said with it: whether the command was
started, where its words are now written, and every file it wrote. Removing says
every file it took back. A hosted command with nowhere visible to speak is one
the operator cannot tell from a failure.

### A platform nothing can be configured on says so, and says what to do

Where the machine has no service manager lemonfiber configures, the stack says so
and gives an instruction. The app shows both and offers no install — offering one
would be offering an act the stack has already said it cannot perform here.

### Standing is six things, and *installed* is not one of them

Hosted, installed but unverified, stopped, orphaned, not hosted, unsupported.
The app shows which, as `N10-R10` already requires of what is not running. The
case this page adds is right after an install: what comes back says whether the
manager is running the command now, and the app reports that rather than the
install having succeeded.

### A stopped queue says which kind of stopped

Stalled, slow, completed but never imported, failing to import again and again,
fetched over and over, orphaned on disk, and waiting on something that never
matches. Each is a different thing to do, and the stack orders them worst first.
The app keeps the categories and the order. *Slow* is the one most worth keeping
apart: it needs patience, not a fix, and shown as stuck it teaches an operator to
ignore the list.

### One cause is one row

Twenty downloads stopped by a full disk are one thing to fix. The stack says so —
one row naming the cause, with how many items it stands for — and the app shows
that row rather than twenty ([G4](../g-ux/g4-error-model.md) `G4-R3`).

### The service's own words about what is blocking it

Where a service said what was in its way, those words are carried. A permission
denial from an import log is the thing the operator can act on, and the app shows
it as it was said.

### How long, not only whether

Each row carries how long it has been that way. That is what makes *stuck* a
sentence an operator can weigh, and it is shown with the row.

### A queue that could not be read is not an empty queue

Where one service's queue would not answer, or is one lemonfiber cannot read at
all, the list may be short. The app says so, naming each service and its reason
where the stack names them, and never renders a short list as a clear one
(`C7-R11`, `C7-R15`).

### A stuck item leads to where it got to

Each stuck item is named so its trace can be asked for, and the app takes the
operator there ([N8](n8-what-comes-in.md)) rather than to a count.

## States

| State | Meaning |
|-------|---------|
| Hosted | Installed, and the manager confirms it is running. |
| Unverified | Installed, and the manager would not say. Never shown as running. |
| Not hosted | Runs only while a terminal holds it. |
| Unsupported | No service manager lemonfiber configures; an instruction is shown instead. |
| Stopped | Items in the queue have stopped, by category, worst first. |
| Partly read | Some queues could not be read, named. Never shown as clear. |
| Clear | Every queue was read, and nothing has stopped. |

## Edge cases

- **Installing a command already hosted.** What is there is replaced, the
  answer names every file it touched, and there are never two.
- **Removing a command that was never hosted.** Said, and not shown as a failure.
- **A hosted command whose program moved after an update.** *Orphaned*, with the
  program it names, and never shown as hosting anything.
- **A full disk stopping every download at once.** One row, the disk, with a
  count — not a screen of downloads.
- **Something seeding at a hundred percent.** Not stuck, and not on this list.

## Requirements

| ID | Requirement |
|----|-------------|
| **N23-R1** | The app MUST offer hosting a named long-running command and removing one, each as an act of its own, and MUST NOT host a command as a side effect of any other act (`B10-R6`). |
| **N23-R2** | After an install, the app MUST say whether the command was started and where its words are written, and MUST report the standing the stack returned rather than the install having succeeded (`B10-R7`, `B10-R13`). |
| **N23-R3** | Every file an install or a removal wrote or took back MUST be shown with its result (`B10-R10`). |
| **N23-R4** | Where the platform has no service manager lemonfiber configures, the app MUST show the stack's instruction and MUST NOT offer an install (`B10-R4`). |
| **N23-R5** | A rehearsed install or removal MUST be labelled as a rehearsal (`N6-R1`). |
| **N23-R6** | A stopped item MUST be shown in the category the stack gave it, in the stack's order, and *slow* MUST NOT be rendered as stuck (`C7-R3`, `C7-R6`). |
| **N23-R7** | Where the stack reports one cause standing for several items, the app MUST show it once with the count, and MUST NOT expand it into a row per item (`C7-R10`, `C7-R13`). |
| **N23-R8** | What a service said was blocking an item MUST be shown in its own words, and how long the item has been that way MUST be shown with it (`C7-R9`). |
| **N23-R9** | Where a queue could not be read, or a service's queue is one lemonfiber cannot read, the app MUST say so, naming each service and its reason where the stack names them, and MUST NOT present the list as complete (`C7-R11`, `C7-R15`). |
| **N23-R10** | A stuck item MUST lead to its trace (`N8-R4`), and MUST NOT lead only to a count. |

## Notes

**What the contract carries.**

| Row | Carried | Not carried |
|---|---|---|
| `N23-R1` | `hosting-install` and `hosting-remove`, each naming the command | — |
| `N23-R2` | `hosting.changed`: `installed`, `started`, `name`; per command `output` and `standing` | — |
| `N23-R3` | `changed.touched` | — |
| `N23-R4` | `manager: unsupported` and `instruction` | — |
| `N23-R5` | `changed.rehearsed` | — |
| `N23-R6` | `dashboard.stuck[].stall`, worst first: `redownload-loop`, `repeated-import-failure`, `completed-not-imported`, `orphaned`, `stalled-download`, `waiting-indefinitely`, `slow` | A remedy per category (`C7-R3`). `stuck` carries what is wrong and what blocked it, not what to do |
| `N23-R7` | `stuck[].items` and `stuck[].name`, which names the cause where several share one | — |
| `N23-R8` | `stuck[].blocking`, `stuck[].held_for` | — |
| `N23-R9` | `stuck` (the `/api/stuck` read): `incomplete`, and `unsupported` naming each service with why | Which service's queue would not answer: `incomplete` is a flag. The dashboard's per-category list carries neither |
| `N23-R10` | `stuck` names each item's `service`, `stage` and `title`, the term a `trace` searches by | — |

The per-category list is on `dashboard`, which the stack publishes on its event
stream; a screen holding that stream reads it on `N1-R67`'s terms.

**Two acts `C7` names are not offered here, because nothing serves them.**
Marking an item as intentionally unmanaged (`C7-R12`) and adjusting the
thresholds (`C7-R5`) have no action on the route the app reaches. `N1-R17`
applies: the app does not approximate either.

## Related

- [N1](n1-companion-app.md) — parity, and what the app may claim
- [N2](n2-operator-companion.md) — stuck downloads, reachable
- [N8](n8-what-comes-in.md) — where one item got to
- [N10](n10-nobody-watching.md) — what a long-running command guarantees
- [N16](n16-nobody-was-looking.md) — what self-healing did about the queue
- [B10](../b-running/b10-hosting.md) — hosting long-running commands
- [C7](../c-trust/c7-queue-health.md) — queue health and stuck items
