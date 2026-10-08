---
id: N23
title: What keeps going, and what stopped moving
kind: feature
area: N
audience: operator
status: accepted
maturity: built
priority: P2
labels: [mobile, queue, ux]
requires: [N1, B10, C7]
relates: [C5, N2, N8, N10, N16]
---

# N23 — What keeps going, and what stopped moving

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Two things a stack does while nobody is looking, and both fail by going quiet.

[B10](../b-running/b10-hosting.md) hands a long-running command — the guard on
the data location, the clock that closes requests nobody ruled on — to the
machine's own service manager, so it outlives the terminal that started it.
[N10](n10-nobody-watching.md) already shows what each one guarantees and whether
it is running (`N10-R10`). What it does not do is let the operator hand one over,
or take one back, from here.

The guard can also be started from here without handing it to anything. Asked
for over the web API, it is a job the stack keeps only while somebody keeps asking
about it, and the app asks while its screen is open. That guard lives as long as
the screen does, and it is a different thing from a hosted one.

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

### A guard can be started here, and lives while the screen asks

The data-root guard ([C5](../c-trust/c5-storage.md)) looks at the data location
every few seconds and, the moment it is gone or has become a different volume,
stops the forms it was started for, so the services do not write a phantom
library onto whatever is left. It never starts them again (`C5-R8`, `C5-R9`).

The app offers starting one for the forms the operator names. Before it starts,
the app says what it would guard and what it would do: the data location, how
often it looks, and the command it would run when that location goes.

Started over the web API, the guard is a job with no ending of its own, and the
stack keeps such a job only while somebody asks about it. The app asks while its
screen is open, on the cadence it declares (`N1-R27`), and releases the guard when
the screen is left. So the guard lives only while this screen keeps asking, and
the app says so plainly — before it starts and for as long as it runs. A guard
that is meant to outlive the screen is a hosted one, offered above as an act of
its own, and the app never presents a screen-held guard as hosted.

### A guard that ended says how

A guard ends in one of four ways, and each is a different afternoon. It saw the
data location go, and says which forms it stopped, whether stopping them worked,
and why it ended. It was ended without seeing anything: released when the screen
was left, or let go because nothing asked about it. It never started, because
there was no data location to guard or it was already gone, and the stack says
which. Or the stack no longer knows it, because the stack itself restarted and
nothing it was running survived that.

*Stopped* is the field worth reading twice. A guard that saw the drive go and
could not stop the services has not protected anything, and the app never shows
it as though it had.

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
| Guarding | A guard this screen started is running, and lives while the screen asks. |
| Guard ended | The guard saw the data location go, with which forms it stopped, whether that worked, and why. |
| Guard let go | The guard ended without seeing anything: released, or not asked about. Never shown as a loss. |
| Guard unknown | The stack no longer knows the guard, because the stack restarted. Never shown as guarding. |
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
- **The phone locks while a guard's screen is open.** Nothing asks while it is
  locked, and the stack lets the guard go once it has gone unasked for long
  enough. Coming back, the app shows the guard as let go, not as still guarding.
- **A guard that saw the data location go and could not stop the services.**
  Shown as that, and never as a guard that protected the library.

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
| **N23-R11** | The app MUST offer starting the data-root guard for forms the operator names, as an act of its own, and before it starts MUST say what it would guard and what it would do: the data location, how often it looks, and the command it would run when that location is lost (`C5-R7`, `C5-R8`). A refusal to start MUST be shown with the stack's reason. |
| **N23-R12** | The app MUST say plainly, before the guard starts and for as long as it runs, that it lives only while this screen keeps asking about it and stops when the screen is left. While the screen is open the app MUST ask about it on the cadence it declares (`N1-R27`), and when the screen is left it MUST release it. A guard started this way MUST NOT be presented as hosted (`N23-R1`). |
| **N23-R13** | A guard that saw the data location go MUST be shown with the forms it stopped, whether stopping them succeeded, and why it ended (`N8-R7`); one that did not succeed MUST NOT be shown as having stopped them. A guard ended without an outcome — released, or let go because nothing asked — and a guard the stack no longer knows MUST each be told apart from one that saw the data location go, and from one still guarding. |

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
| `N23-R11` | The `watch` action, which takes `forms` and answers with a job; `watch.would` — `root`, `every`, `command` — on a run that only says what a guard would do. A refusal to start is the error envelope: no data location configured, or one already gone | **What a guard would do, before it starts.** `would` is answered only by a rehearsal, and no action argument on the HTTP route asks for one, so the app cannot read the data location, the interval or the command from the stack before the guard runs |
| `N23-R12` | The job: `GET /api/jobs/{job}` answers `job` at `202` while the guard runs, and asking is what renews its lease; `DELETE /api/jobs/{job}` releases it. The stack lets a guard go once it has gone unasked for between thirty minutes and an hour | — |
| `N23-R13` | `watch.forms`, `watch.stopped`, `watch.reason` on a guard that saw the data location go; `job` at `200` for one ended without an outcome; `404` for a name the stack's current run never handed out | **Released or let go.** Both answer `job` at `200`, so the app can say it released a guard itself and cannot tell a guard another client released from one nobody asked about |

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
