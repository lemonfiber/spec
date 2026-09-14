---
id: N2
title: The operator's companion
kind: feature
area: N
audience: operator
status: draft
maturity: planned
priority: P1
labels: [mobile, ux, verification]
requires: [N1, C1, C3, G7]
relates: [B2, B4, B5, C2, C7, C8, D5, E1, E4]
---

# N2 — The operator's companion

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

What the operator opens the app to find out, and what they can do about it
without going to the machine.

The ordering is deliberate and is the whole design: **is anything wrong**, then
**what**, then **may I fix it from here**. A dashboard that leads with statistics
answers a question nobody opened the app to ask.

This is the surface where lemonfiber's own difference shows most: the product
already knows what is wrong in plain language, already knows what would put it
right, already asks before changing anything, and already records what it did so
it can be undone ([C1](../c-trust/c1-diagnostics.md),
[C3](../c-trust/c3-auto-remediation.md)). None of that is invented here. This
feature renders it on a phone.

## Behaviour

### It opens on the answer, not on the data

The first screen is the overall verdict ([G7](../g-ux/g7-health-summary.md)) —
healthy, degraded, broken, or unknown — and unknown is a first-class answer
rather than a blank. Beneath it is what is wrong, worst first.

### A finding carries its remedy, and the remedy is offered

Every problem lemonfiber raises carries a code, what it means in plain language,
and what to do ([G4](../g-ux/g4-error-model.md)). Where the product can put it
right itself, the repair is offered here on the same terms it is offered
anywhere: what it would do, what else changes, whether it can be undone, and a
confirmation before it happens.

A repair is never carried out because the operator tapped the finding.

### The stack's life is controllable

Starting, stopping and restarting, by form or by service
([B2](../b-running/b2-lifecycle.md)). A destructive or disruptive action asks
first, and says what it disturbs and how long for — as the stack reported it. The
stack answers that with a bound where it has one and with *open-ended* where it
does not (`B2-R16`), and the app states whichever it was given. It does not
estimate: a duration worked out in the app would be a guess at something the stack
knows and the app does not, wrong in exactly the cases an operator most needs it,
and wrong silently, because nothing on either side would ever compare it to what
happened.

### An update is a decision, not a number

Whether the stack is current is an answer, and the app opens on it the way it
opens on everything else here ([E1](../e-maintenance/e1-stack-updates.md)). An
operator holding a phone is not comparing version strings; they are deciding
whether tonight is the night.

So what is offered is what the decision needs. That a release is user-facing is
the distinction that matters on this surface — a change somebody in the house
will notice is a different decision from a patch nobody will — and a release
that has been withdrawn is not an update at all. Applying one asks first, and
says which services it would change, because an update of eight services and an
update of one are different evenings.

**Undoing is part of the offer, and the two ways of undoing are not
interchangeable.** A rollback puts the previous version back; a restore puts
back what was there ([E4](../e-maintenance/e4-rollback.md)). Which one is
available is the stack's answer per service, and an app that flattened them into
*undo* would be promising a thing it cannot tell it has. Where the stack named
neither, nothing is offered — an undo that is not there is worse than none,
because it is what somebody agreed to the update on the strength of.

Afterwards, each service says how it ended, and *not fetched*, *not started* and
*not reached* are three different evenings too: one is a network, one is the
service, one is the machine. A single *failed* would send an operator looking in
the wrong place.

### The things that go wrong while nobody is watching

Downloads that are stuck ([C7](../c-trust/c7-queue-health.md)), a provider out of
allowance or refusing a login ([C8](../c-trust/c8-provider-health.md)), a disk
filling ([D5](../d-content/d5-disk-space.md)), a tunnel that is up with no
forwarded port ([C2](../c-trust/c2-vpn-verification.md)). These are the ones
worth carrying in a pocket, because each is invisible until something the
household wanted does not arrive.

### Logs are readable, not tailed

A phone is a bad terminal. Logs are offered as a bounded, searchable read for a
named service ([B4](../b-running/b4-logs.md)) rather than as an endless stream,
and the app says it is showing a window rather than everything.

### Requests waiting on the operator

A household member's request that needs a decision is surfaced here, with enough
to decide on ([D7](../d-content/d7-approval-quotas.md)). Approving from a phone
is the case this whole surface justifies itself with.

### What it does not do

Nothing here edits a credential's value. The app can report that a credential is
refused and offer the reconciliation lemonfiber already has; it is not a place to
type a provider password into over a LAN.

## States

| State | Meaning |
|-------|---------|
| Healthy | Nothing is wrong. The app says so plainly rather than showing an empty list. |
| Degraded | Something is wrong and the stack is serving. Findings are listed worst first. |
| Broken | Something is wrong and the stack is not serving. |
| Unknown | Checks could not be run or could not answer. Never reported as healthy. |
| Repairing | A confirmed repair is running. Progress is shown; the screen does not claim completion until the core reports it. |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| A repair is offered and the stack becomes unreachable before it is confirmed | The confirmation is refused rather than queued. A repair the operator agreed to against one reading must not run against a different one. |
| A finding's repair needs a service the app cannot reach | Reported as the core reports it, rather than offered and failed. |
| Two repairs are offered for one finding | Both are shown with what each does. The app does not choose. |
| A disruptive check is available | It is offered only with what it disturbs and for how long stated first. |
| The verdict is unknown because the engine is down | Reported as the engine being down, which is a different remedy from a check that failed. |
| A log window is requested for a service that is not running | The absence is stated; an empty window is not shown as though the service were quiet. |
| Something is running on the machine that the stack does not declare | Named and shown apart from the stack's own services, with no verb offered against it. The app did not start it and cannot say what it is for. |
| An update would make a change that cannot be undone | Said in the confirmation, against the service it is true of, before the operator agrees. Undoing the update afterwards will not put this back. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N2-R1** | The app MUST open on the overall verdict, and MUST render `unknown` as its own answer rather than as healthy or as an absence. |
| **N2-R2** | Findings MUST be ordered by severity, worst first. |
| **N2-R3** | Every finding shown MUST carry its code, its plain-language meaning, and its remedy, in the words the core produced. |
| **N2-R4** | Where the core offers a repair, the app MUST offer it, and MUST state what it does, what else it affects, and whether it can be undone, before asking for confirmation. |
| **N2-R5** | A repair MUST NOT be carried out without an explicit confirmation distinct from the act of viewing the finding. |
| **N2-R6** | A repair confirmed against one reading MUST NOT be carried out if the reading has changed; the app MUST refuse and re-offer. |
| **N2-R7** | The app MUST offer start, stop and restart by form and by service. |
| **N2-R8** | A disruptive action MUST state what it disturbs, and MUST state the bound on the disturbance the stack reported or that the stack reported none (`B2-R16`), before it is confirmed. The app MUST NOT estimate a duration of its own. |
| **N2-R9** | Stuck downloads, provider health, disk pressure and VPN verification MUST each be reachable. |
| **N2-R10** | Logs MUST be offered as a bounded, searchable read, MUST name the service, and MUST state that the view is a window rather than the whole. |
| **N2-R11** | Requests awaiting a decision MUST be surfaced with enough to decide on, and MUST be approvable and refusable from the app. |
| **N2-R12** | The app MUST NOT offer to set or change a credential's value. |
| **N2-R13** | A reading older than the current session MUST carry its age wherever it is shown, including on the opening verdict. |
| **N2-R14** | Where the contract does not carry something a requirement here asks the app to state, the app MUST NOT substitute a value of its own; the gap MUST be raised against the contract (`N1-R17`) and the requirement MUST be answered there. |
| **N2-R15** | The app MUST report whether the stack is current, has an update pending, or is stale, as the stack reported it, and MUST NOT derive that answer by comparing version strings of its own. |
| **N2-R16** | Where an update is pending, the app MUST distinguish a release the household will notice from one it will not, and MUST NOT present a withdrawn release as an update. |
| **N2-R17** | Applying an update MUST be confirmed before it runs, and the confirmation MUST name the services it would change. |
| **N2-R18** | The app MUST report how an applied update ended for each service, and MUST distinguish *updated*, *not fetched*, *not started* and *not reached* from one another rather than reporting a single failure. |
| **N2-R19** | Where an update can be undone, the app MUST say which way it can be undone — a rollback and a restore are not one offer — and MUST NOT offer undoing where the stack named neither. |
| **N2-R20** | The app MUST NOT apply an update the stack did not report as pending, and MUST NOT offer to apply one where the stack reported the version in use is current. |
| **N2-R21** | Where the stack reports containers running on the machine that its own configuration does not declare, the app MUST make them reachable, MUST name each and state what it is running, and MUST NOT present one as part of the stack or offer a verb against it. |
| **N2-R22** | Where the stack reports that a change an update would make cannot be undone, the confirmation MUST say so before it is agreed to, and MUST name the services it is true of. |

## Related

- [N1](n1-companion-app.md) — connecting, and what the app may claim
- [C1](../c-trust/c1-diagnostics.md), [C3](../c-trust/c3-auto-remediation.md) — the findings and repairs rendered here
- [G7](../g-ux/g7-health-summary.md) — the verdict this opens on
- [G4](../g-ux/g4-error-model.md) — the words a problem is given
- [D7](../d-content/d7-approval-quotas.md) — the requests waiting
