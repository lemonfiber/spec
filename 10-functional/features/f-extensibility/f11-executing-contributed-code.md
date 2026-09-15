---
id: F11
title: Executing contributed code
kind: feature
area: F
audience: operator
status: draft
maturity: planned
priority: P3
labels: [extensibility, security, verification]
requires: [F3]
relates: [F4, F5, F6, F8, F10, C1, G8]
---

# F11 — Executing contributed code

**Status:** Draft · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Hold open, as its own question, whether code a stranger wrote may ever execute inside
lemonfiber's process — and record what an answer would have to survive.

It is not a gap in [F3](f3-stack-manifests.md). F3 answered this, deliberately and in the
strongest available terms, and the answer is `F3-R6`: **contributed code MUST NOT be
executed, and no opt-in, sandbox or capability grant may make it executable.** `F3-R7` adds
that native plugins are not a supported mechanism and never become one. An earlier draft of
F3 reserved a sandboxed escape hatch; it was removed on purpose, because reserving a code
path for the rare case is how the rare case becomes the common one.

So this feature exists to be the place that question is asked in, rather than to be the
place it is quietly answered. Whoever opens it is **crossing a line somebody drew**, and
the first thing they owe is an argument that the reasons for drawing it no longer hold.

## The tension this has to resolve

| What stands | What this feature would need |
|-------------|------------------------------|
| `F3-R6` forbids executing contributed code, **including** by opt-in, sandbox or capability grant. The sandbox is named in the prohibition, so "but it is sandboxed" is not a reply to it — it is the thing being refused. | A superseding decision that says what changed, not an edit that makes the old rule read differently. |
| `F3-R7` rules out native plugins as a supported mechanism. | An account of why this is not that, in terms an operator can check. |
| `F3-R10` asks that a plugin review as a readable diff with nothing opaque needed to understand it. A compiled module is the opposite of a readable diff. | Either an artefact that reviews, or an honest statement that this class of plugin is not reviewable and what stands in for review. |
| [ADR-0021](../../../00-overview/decisions/0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md) records why the two obvious answers lost. A WASM module is a good sandbox **for computation**, and nothing a plugin needs is computation — it runs a service and calls an API, both of which are I/O the host must grant anyway, so the sandbox constrains the part nobody feared. A supervised subprocess holds lemonfiber's own authority on that machine, so isolating faults buys nothing against misbehaviour. | An answer to both objections, rather than a stronger sandbox. The question is not *how well is it confined* but *what does it still reach*. |
| The declarative surface buys a property: what runs and what it may reach is stated in advance and checkable without running it. | A way to keep that property, or an explicit account of what is traded for what. |
| [F8](f8-recipes.md)'s recipes and named adapters were built to replace the escape hatch. | Cases recipes genuinely cannot express, named — not hypothesised. |

The original question is recorded as [RFC #66](https://github.com/lemonfiber/spec/issues/66),
which asked whether the plugin surface should commit to a sandboxed WASM escape hatch or
ship data-only first. It was answered data-first, and this is where the other half was
parked rather than closed.

## Why it is not folded into F3

Retiring `F3-R6` is a **security line, not a gap**. Two things follow.

It must be decided on its own evidence, by somebody looking at it, rather than arriving as
a clause inside a change about something else — which is how a prohibition becomes a
default nobody voted for.

And it must not gate anything. What a plugin may add to lemonfiber *declaratively*
([`F3-R26`](f3-stack-manifests.md)–`F3-R30`) is settled and shipping; none of it waits on
this, and none of it becomes easier if this is answered yes. A feature that holds a
question open is only useful while it holds nothing else hostage.

## What an answer must not cost

Whatever shape this takes, the things below are not available to trade, because each is a
promise made elsewhere and relied on.

- **The container contract.** `F3-R24` fixes what a plugin's service may reach of the
  machine — no mount beyond the data root and its own configuration directory, no device,
  no kernel capability, no network mode, no privileged container, no user override. Nothing
  here widens it.
- **The account of what leaves this machine.** `F5` makes that account complete by naming
  every destination and who added it. Code that could open a socket without declaring it
  ends that.
- **The unrun/passed distinction.** `F3-R5` and `F3-R28` both say an extension that cannot
  be run is reported as unrun and never as passed. Code that fails to load is no different.
- **Adding is not overriding.** `F4-R17` keeps a plugin from changing what lemonfiber says
  about itself. Code able to register itself over a bundled check would be that, with an
  extra step.

## Acceptance criteria

These are conditions on *deciding*, not a design. A draft feature is not binding and
implementation MUST NOT cite it; these say what a proposal has to carry before it stops
being a draft.

| ID | Requirement |
|----|-------------|
| **F11-R1** | This feature MUST NOT be implemented while `F3-R6` stands, and retiring `F3-R6` MUST be a superseding decision record that states what changed, never an edit to the requirement in place. |
| **F11-R2** | A proposal MUST answer both objections already recorded — that a sandbox confines computation while the risk is I/O, and that an opaque artefact forecloses the readable review `F3-R10` asks for — rather than asserting that the sandbox is strong. |
| **F11-R3** | A proposal MUST name the cases recipes and named adapters genuinely cannot express, with an example of each, and MUST NOT rest on the possibility that such cases exist. |
| **F11-R4** | Contributed code, if it is ever executed, MUST NOT hold lemonfiber's own authority on the machine: the credential store, the container runtime's socket and the data root MUST be unreachable from it by construction rather than by policy. |
| **F11-R5** | What contributed code may reach MUST be stated in advance and checkable without running it, and a reach beyond what was stated MUST be refused rather than logged. |
| **F11-R6** | An operator MUST be able to tell from an installed plugin whether any part of it executes in lemonfiber's process, without reading its source. |
| **F11-R7** | Where the confinement a proposal depends on cannot be enforced on a supported platform, the code MUST be refused there and reported as refused — never run unconfined, and never reported as run. |
| **F11-R8** | Contributed code that cannot be loaded or run MUST be reported as unrun and MUST NOT be reported as passed, satisfied, or by being omitted. |
| **F11-R9** | Nothing this feature introduces may widen what a plugin's container may reach (`F3-R24`), and a proposal MUST say so explicitly rather than leaving it inferred. |
| **F11-R10** | Contributed code MUST NOT be able to register itself over a bundled check, remedy or command; `F4-R17` holds whatever the mechanism. |

## Related

- [F3 Plugin manifests](f3-stack-manifests.md) — `F3-R6` and `F3-R7`, the prohibition this would have to cross
- [ADR-0021](../../../00-overview/decisions/0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md) — why a plugin is data, and the two alternatives that lost
- [F8 Recipes and named adapters](f8-recipes.md) — what was built instead of the escape hatch
- [F10 Writing a plugin](f10-authoring.md) — the authoring experience a change here would alter
- [F4 The capability vocabulary](f4-capabilities.md) — the namespacing and no-overriding rules that hold whatever the mechanism
- [G8 Privacy stance](../g-ux/g8-privacy.md) — the account of what leaves this machine
