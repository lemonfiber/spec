---
id: N7
title: Moving in beside what is already there
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P3
labels: [mobile, storage, wiring, ux]
requires: [N1, A5]
relates: [D1, A6, E3, N2]
---

# N7 — Moving in beside what is already there

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Most people who install lemonfiber already have something running. Taking that
over is the most consequential thing the product does to a machine it did not
set up, and it is a long operation an operator will not sit and watch.

So it is exactly the thing they will pick a phone up to check on — *did it take
my Sonarr settings, is it safe to turn the old one off, what did it decide it
could not bring across*. The stack already answers all three. Nothing renders
them away from the machine.

[A5](../a-getting-started/a5-migration.md) owns what moving in is and what it
covers. This owns what it looks like from somewhere else while it happens, and
afterwards.

## Behaviour

### What did not come across is the part worth reading

An import carries some things and not others, and the contract names each thing
it could not carry and why. **That list is the finding**, not a footnote to a
success message: an operator who believes their quality profiles came over, and
discovers in three weeks that they did not, was told something true and useless.

The app leads with what was left behind.

### A stance is four things, and only one of them is done

Moving in is *unchanged*, *pending*, *blocked* or *applied*. The app renders
which, and never renders the first three as the last. A blocked move carries its
refusal, and the refusal is shown rather than a generic failure.

### A refusal is an answer

Where the stack refuses to take something over — because it would overwrite, or
because it cannot read it — that refusal is what the operator needs and is shown
with its reason. It is not an error state and not a retry prompt.

### What wants a copy first says so before it is agreed to

Some things the stack takes over are taken over destructively, and it says which
of those it would want a backup of first. That is stated with the decision rather
than after it, and it is the same discipline `N6` applies to a copy's scope.

### A conflict names what already holds the thing

Running beside an existing setup means ports that are taken. The contract carries
what is conflicting and what holds it, and the app names the holder — *something
else is on 8989* is not actionable, and *your existing Sonarr is on 8989* is.

### A port that moved is remembered, not just reported

Where the stack put a service on a different port to avoid a collision, that is
not a transient detail of the install. It is how the operator will reach the
thing for as long as it runs, and the app keeps it available rather than showing
it once.

### Unassessable is not the same as fine

When the stack wires services together it may be unable to assess whether a
connection is sound. That is a third answer beside *sound* and *broken*, and it
stays a third answer here: an app that rendered it as fine would be inventing
confidence the core declined to express (`N2-R14`).

### A wiring that would break something says what and how to mend it

Where a connection carries a severity, it carries what would break and what would
put it right. Both are shown; a severity alone is a colour, not information.

### The survey is offered here, and comes before any mode

Moving in starts with a look that changes nothing
([A5](../a-getting-started/a5-migration.md) `A5-R1`), and the app offers that
look. What it found — each existing project, each of its services, whether each
is running and whether lemonfiber could take it over — is shown before any mode
is, because a mode chosen before the survey is read is a mode chosen blind.

A survey that could not look is not a survey that found nothing. The contract
says which, and an empty machine and an unread one are never the same screen.

### A mode is offered as the stack offers it, and replacement is never the default

The stack gives the modes least destructive first, says what each would come to
and whether it disturbs what is already running, and marks the one it offers
already chosen. The app keeps all three: the order, the disturbance and the
preselection. It preselects nothing the stack did not, so replacement — the one
that stops somebody's working stack — is never a tap away by default.

### A layout that cannot hardlink is a cost, with a remedy that stays an offer

Where the existing layout cannot hold a hardlink, the survey says why, what it
costs in room, and what would fix it. The fix is the operator's to take: it is
their library on their disks, and the stack does not force it. The app shows the
cost and offers the remedy as its own act, never as a step folded into a move.

### What cannot be taken over is named

A service the stack found and cannot adopt is named as unsupported, with the
reason. Left off the list, it reads as something the move will look after.

### A wiring run is offered here, and each connection says how it ended

Wiring the services together ([D1](../d-content/d1-seed.md)) is safe to run
again and changes nothing that is already right, and the app offers it. What
comes back is a state per connection, and those states are the report: *skipped*
is a prerequisite that was not there and will be finished by a later run,
*failed* is a service that refused, and a value the operator changed is kept
rather than put back. A run that turned all of them into one tick has thrown away
the only thing an operator can act on.

### The operator's own value is kept, and never offered for overwriting

Where a connection holds a value the operator set, the stack keeps it and says
so, and where both the operator and lemonfiber moved away from the baseline it
shows the two side by side and resolves neither. The app does the same. It does
not offer to put lemonfiber's value back (`N19-R4`).

### A service's refusal is in the service's words

Where a service rejected a write, its own words are carried. The app shows them
as they came rather than a sentence of its own, because the words are what the
operator will search for.

## States

| State | Meaning |
|-------|---------|
| Unchanged | Nothing has been taken over. What would be is shown. |
| Pending | A move is agreed and not finished. Never rendered as done. |
| Blocked | The stack refused, and the refusal is shown with its reason. |
| Applied | It finished. What was not carried is shown alongside what was. |
| Unassessable | A wiring could not be judged. Shown as its own answer, not as sound. |
| Unknown | The move could not be read. Never rendered as unchanged. |

## Edge cases

- **An import that carried nothing.** Distinguished from an import that has not
  run. Both are quiet screens and they mean opposite things.
- **A conflict on a port the operator cannot change.** The holder is named, and
  what the stack did instead is shown, rather than the move simply failing.
- **A move applied while the app was closed.** The app renders the finished state
  and what was not carried, rather than treating it as new.
- **A refusal the operator can do nothing about.** Still shown. An operator who
  cannot see why a thing did not happen will try it again.

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N7-R1** | What an import could not carry MUST be shown with the reason for each, and MUST NOT be subordinated to a success message. |
| **N7-R2** | The stance of a move MUST be rendered as given, and *unchanged*, *pending* or *blocked* MUST NOT be presented as *applied*. |
| **N7-R3** | A refusal MUST be shown with the reason the stack gave, and MUST NOT be rendered as a generic failure or a retry prompt. |
| **N7-R4** | Where the stack would take something over destructively and wants a copy first, the app MUST say so before the decision is agreed to. |
| **N7-R5** | A conflict MUST name what already holds the thing it conflicts over. |
| **N7-R6** | Where a service was placed on a different port to avoid a conflict, the app MUST keep that reachable afterwards and MUST NOT show it only at the moment it happened. |
| **N7-R7** | A wiring the stack could not assess MUST be shown as its own answer, and MUST NOT be rendered as sound. |
| **N7-R8** | Where a wiring carries a severity, what would break and what would put it right MUST both be shown. |
| **N7-R9** | An import that carried nothing MUST be told apart from an import that has not run. |
| **N7-R10** | A rehearsed wiring run MUST be labelled as a rehearsal, on the same terms as `N6-R1`. |
| **N7-R11** | The app MUST offer the survey of what is already on the machine, and MUST show every project and service it found, with whether each is running and whether it could be taken over, before any mode is offered (`A5-R1`, `A5-R2`). A survey that could not look MUST be told apart from one that found nothing. |
| **N7-R12** | The app MUST offer the modes the stack gives, in the stack's order, each with what it would come to and whether it disturbs what is running. It MUST NOT preselect a mode the stack did not preselect, and MUST NOT preselect replacement (`A5-R3`). |
| **N7-R13** | Where the survey reports a layout that cannot hardlink, the app MUST show why, what it costs and the remedy, and MUST offer the remedy only as an act of its own, never as part of a move (`A5-R10`). |
| **N7-R14** | A service the survey found and cannot take over MUST be named as unsupported with the reason, and MUST NOT be omitted (`A5-R12`). |
| **N7-R15** | The app MUST offer a wiring run, and MUST show each connection with the state the stack gave it. *Skipped* MUST NOT be rendered as failed, and a connection kept because the operator changed it MUST NOT be rendered as wired or as drift to repair (`D1-R3`, `D1-R5`, `D1-R6`). |
| **N7-R16** | Where a connection is kept because the operator changed it, the app MUST say it is kept; where the operator's value and lemonfiber's both moved, the app MUST show what the service holds beside what lemonfiber would write. The app MUST NOT offer to overwrite the operator's value (`N19-R4`). |
| **N7-R17** | A write a service rejected MUST be shown with the service's own words, and MUST NOT be paraphrased (`D1-R11`). |

## Notes

**What the contract carries for the rows above.** Checked against the core's
`contract/web-api.contract.json` and the actions its HTTP route accepts.

| Row | Carried | Not carried |
|---|---|---|
| `N7-R11` | `migration`, served at `/api/migration`: `standing` (each project, its services, `running`, `adoptable`) and `read`, which is false where the engine could not look | The configuration source and the library location of each service `A5-R2` names. The survey carries projects, services and ports; the library appears only as the filesystems in `linking` |
| `N7-R12` | `modes`: `mode`, `what`, `disturbs`, `preselected`, least destructive first. The action route accepts `migrate-adopt`, `migrate-import`, `migrate-beside` and `migrate-replace`, and each answers unconfirmed with what it would come to | — |
| `N7-R13` | `linking`: `because`, `cost`, `remedy`, `filesystems`, and `forced`, which is always false | No action carries the remedy out. It is offered as words, and there is no act for the app to offer beside them |
| `N7-R14` | `unsupported`, each with `what` and `because`; `not_carried` for what no mode carries | — |
| `N7-R15` | `seed`, from the `seed` action: each wiring's `state` — wired, already-wired, drifted, stale, conflicted, adopted, unmanaged, observed, would-wire, would-adopt, skipped, failed, refused — with the `reason` or `detail` each carries; `assessment`, `unsupported` and `rehearsed` | Whether a run was interrupted (`D1-R13`). A pass reports what it attempted, not what it did not reach |
| `N7-R16` | `drifted` says an operator-changed value was kept; `conflicted` carries `ours` and `yours` side by side | The value itself on `drifted`, which carries none. `unmanaged` withholds the value by design, so a secret among what the stack takes on is never shown |
| `N7-R17` | `failed` carries the service's own words in `detail` | — |

`N7-R13` is written as an offer that stands on its own for a reason the contract
makes plain: `forced` is always false. Folding the remedy into a move would be
the app forcing what the stack declines to.

## Related

- [N1](n1-companion-app.md) — connecting, parity, and what the app may claim
- [N2](n2-operator-companion.md) — the verdict, and why a value is never substituted
- [N6](n6-taking-a-copy.md) — copies, and what a rehearsal may not look like
- [A5](../a-getting-started/a5-migration.md) — what moving in is and what it covers
- [D1](../d-content/d1-seed.md) — wiring the services to each other
- [A6](../a-getting-started/a6-uninstall.md) — leaving, and what is left behind
