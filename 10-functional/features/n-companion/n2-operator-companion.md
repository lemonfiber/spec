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
relates: [B2, B4, B5, C2, C7, C8, D5, E1]
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
first, and says what it disturbs and for how long.

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
| **N2-R8** | A disruptive action MUST state what it disturbs and for how long before it is confirmed. |
| **N2-R9** | Stuck downloads, provider health, disk pressure and VPN verification MUST each be reachable. |
| **N2-R10** | Logs MUST be offered as a bounded, searchable read, MUST name the service, and MUST state that the view is a window rather than the whole. |
| **N2-R11** | Requests awaiting a decision MUST be surfaced with enough to decide on, and MUST be approvable and refusable from the app. |
| **N2-R12** | The app MUST NOT offer to set or change a credential's value. |
| **N2-R13** | A reading older than the current session MUST carry its age wherever it is shown, including on the opening verdict. |

## Related

- [N1](n1-companion-app.md) — connecting, and what the app may claim
- [C1](../c-trust/c1-diagnostics.md), [C3](../c-trust/c3-auto-remediation.md) — the findings and repairs rendered here
- [G7](../g-ux/g7-health-summary.md) — the verdict this opens on
- [G4](../g-ux/g4-error-model.md) — the words a problem is given
- [D7](../d-content/d7-approval-quotas.md) — the requests waiting
