---
id: F9
title: Capabilities of the bundled services
kind: feature
area: F
audience: operator
status: accepted
maturity: planned
priority: P1
labels: [extensibility, wiring, verification]
requires: [F4]
relates: [F2, F5, F6, F8, D1]
---

# F9 — Capabilities of the bundled services

**Status:** Accepted · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Make the capability vocabulary real by having something implement it, and convert the
bundled stack's wiring to ask in it.

[F4](f4-capabilities.md) defines what a capability is: a named, contracted thing a
service can do, carrying probes that demonstrate the contract holds. On its own that is a
document. A vocabulary nothing speaks is not a vocabulary, and a capability nothing
implements is one nobody has tested — so it would be published, versioned, and wrong in
ways no one would discover until a plugin author trusted it.

This is where the nineteen bundled services declare what they can do, pass the probes
that prove it, and the wiring that currently names them is changed to ask instead. It is
the larger half of the work by a wide margin and the smaller half of the thinking, which
is why it is separable: F4 is a model and a set of rules, and this is nineteen services'
worth of applying them.

The payoff is the one the whole extensibility area exists for. Once the request service
asks for *an identity source* rather than for Jellyfin, a plugin claiming that capability
can stand in — and nothing that consumes it has to know a plugin exists.

## Behaviour

### Every bundled service declares what it can do

All nineteen are given capabilities and the probes that demonstrate them. This is not
bookkeeping. The bundled stack becomes the **reference implementation** of every core
capability, so a plugin author has something concrete to satisfy rather than a paragraph
to interpret.

The declarations live in the stack manifest, not in lemonfiber's source. A fork that adds
a service declares its capabilities the same way, and adding one still requires no code
change ([F1-R5](f1-customisation.md)).

### No capability is published that nothing demonstrates

Every capability in the core vocabulary is declared by at least one bundled service. A
capability with no implementation is a contract nobody has had to satisfy, and it will be
subtly wrong in exactly the way that costs a plugin author a day.

That constraint runs the other way too: it stops the vocabulary growing speculatively.
A capability earns its place by something needing it, not by seeming likely to be useful.

### The wiring asks, rather than naming

Where the stack currently names a service, it asks for a capability. The request service
asks for an identity source; the media-filing services ask for a download client.

Wiring by name stays possible where it is genuinely about one service — but it becomes
the exception, and it is shown as one, so the reason it is by name is visible to whoever
reads it next.

### A capability lost at a pin bump is a failure, not a surprise

A bundled service that stops satisfying a capability it declares — because an upstream
release moved something — fails exactly as a plugin failing a claim does. The probes are
the source of truth for both, and there is no separate, gentler treatment for the
services this project happens to ship. A version does not go out with a bundled claim
its own probes refuse.

### Substitution stops being a rewrite

The test of whether this landed is not that the declarations exist. It is that replacing
a bundled service with a plugin claiming the same capability requires **no change to
anything that consumes it**. If a consumer still has to be found and edited, the wiring
was not really converted.

## States

| State | Meaning |
|-------|---------|
| `declared` | A bundled service declares the capability in the manifest |
| `demonstrated` | The capability's probes ran against the bundled service and passed |
| `unproven` | The probes could not be run; the claim is not treated as met |
| `refuted` | The probes ran and failed; the version does not ship |
| `unimplemented` | A capability the vocabulary publishes that no bundled service declares |
| `by-name` | A wiring deliberately kept to a named service, shown as the exception |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| A bundled service loses a capability at a pin bump | The same failure as a plugin failing a claim. The probes are the source of truth for both, and the version does not ship. |
| A capability is published that nothing bundled declares | Refuse it into the vocabulary. An untested contract is worse than an absent one, because a plugin author will trust it. |
| Two bundled services genuinely do the same thing | Both declare it. That is what a vocabulary is for, and the operator chooses which fills it ([F4-R8](f4-capabilities.md)). |
| A wiring cannot honestly be expressed as a capability | Keep it by name, and show it as by-name so the exception is visible rather than assumed to be an oversight. |
| A fork adds a service | It declares capabilities in its own manifest, with no lemonfiber change, like every other thing a manifest carries. |
| A probe needs a service that is not running | Report unproven rather than failed. Nothing was demonstrated, and nothing was refuted. |
| Converting a wiring changes behaviour subtly | It is a change like any other: journalled, and reversible through the same machinery. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F9-R1** | Every bundled service MUST declare the capabilities it provides, and the declaration MUST live in the stack manifest rather than in lemonfiber's source. |
| **F9-R2** | Every capability a bundled service declares MUST pass that capability's probes, and a version MUST NOT ship while a bundled claim's probes refuse it. |
| **F9-R3** | Every capability in the core vocabulary MUST be declared by at least one bundled service, and a capability nothing implements MUST NOT be published. |
| **F9-R4** | The bundled stack's wiring MUST be converted to ask for capabilities rather than to name services, except where a wiring is genuinely about one service, which MUST be shown as a by-name wiring. |
| **F9-R5** | A bundled service that stops satisfying a declared capability MUST fail in the same way a plugin failing a claim does, with no gentler treatment for being bundled. |
| **F9-R6** | Replacing a bundled service with a plugin that claims the same capability MUST require no change to anything that consumes that capability. |

## Related

- [F4 The capability vocabulary](f4-capabilities.md) — the model, the rules and the probes this implements
- [F2 Service catalogue](f2-service-catalogue.md) — the nineteen services these describe in machine terms
- [F5 The plugin catalogue](f5-plugin-catalogue.md) — where a plugin claiming one of these comes from
- [D1 Service auto-wiring](../d-content/d1-seed.md) — the wiring this converts
- [stack-manifest contract](../../../20-architecture/contracts/stack-manifest.md) — where a bundled service's capabilities are declared
