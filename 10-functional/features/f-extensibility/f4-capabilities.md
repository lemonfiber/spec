---
id: F4
title: The capability vocabulary
kind: feature
area: F
audience: operator
status: accepted
maturity: planned
priority: P1
labels: [extensibility, wiring, verification]
requires: [F2, F3]
relates: [F1, F5, F6, F7, F9, B1, C1, D1]
---

# F4 — The capability vocabulary

**Status:** Accepted · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Make it possible for one service to stand in for another, by describing services in terms
of **what they can do** rather than **what they are called**.

Everything in the bundled stack is currently wired by name. The request service signs in
through Jellyfin because it was told "Jellyfin"; the media-filing services register a
download client because they were told "qBittorrent". Wiring by name is why substituting
Plex for Jellyfin is not a configuration change but a rewrite: every consumer that named
Jellyfin has to be found and changed, and a plugin that did that would be reaching into
services it has no business reaching into.

A capability is a named, contracted thing a service can do — *serves media*, *accepts a
webhook*, *answers as an indexer*. A service **claims** capabilities; wiring **asks** for
them. Plex claiming *serves media* and *is an identity source* is then a candidate for
anything that asked for those, and nothing that consumes them needs to know a plugin
exists.

The vocabulary is only worth anything if a claim can be wrong and be caught. So a
capability is not a label: it carries a contract, and probes that demonstrate the contract
holds. Claiming a capability you do not satisfy fails verification, which is what makes
substitution safe to offer at all.

**This feature is the model and its rules.** Having the nineteen bundled services declare
their capabilities, pass the probes, and converting the stack's wiring to ask rather than
to name, is [F9](f9-bundled-capabilities.md) — the larger half of the work and the smaller
half of the thinking, which is why the two are separable.

## Behaviour

### lemonfiber owns the core vocabulary; plugins may add namespaced ones

The capabilities the bundled stack needs are published, versioned and owned by lemonfiber.
A plugin claims from that set — it does not invent alternatives to it, because two names
for the same thing means neither wires.

A plugin may declare a **namespaced** capability of its own — `plex:direct-play` — for
something nothing bundled consumes. A namespaced capability is inert until something asks
for it, which is exactly the right amount of power: it lets an ecosystem grow a vocabulary
without letting one plugin fragment the shared one.

### Something has to speak it

A vocabulary nothing speaks is not a vocabulary, and a capability nothing implements is
one nobody has tested. So the bundled stack becomes the reference implementation of every
core capability, and the wiring that currently names services is converted to ask in it —
which is what makes a stack with Plex in place of Jellyfin wire identically.

That work is [F9](f9-bundled-capabilities.md). What belongs here is the rule it applies:
**wiring asks for a capability rather than naming a service.** By-name wiring remains
possible where it is genuinely about one service — but it is the exception, it is visible
as such, and a plugin cannot introduce one.

### Substitution is a plugin filling a capability something else was filling

Substituting is not a special operation. A plugin claims a capability, the operator
chooses it as the filler, and everything that asked for that capability now reaches the
new service. What changes is a setting, and it is journalled like any other change, so it
appears in the history and can be put back.

### Two claimants is a refusal, not a race

Where two plugins claim the same capability, or two would override the same thing,
lemonfiber **refuses** — naming both claimants and exactly what they collide on. It does
not pick by install order, by precedence, or by recency. An operator resolves it by
choosing, and their choice is recorded.

This is the same posture the product takes everywhere else it meets ambiguity: say what
was found and let the person decide, rather than guess and be right most of the time.

### Where a plugin may extend lemonfiber is a vocabulary too

A capability is a named thing a service can do, published and owned here so that two names
for one thing cannot exist. The points at which a plugin may extend **lemonfiber itself**
— the register of checks it runs, the remedies they carry — are the same kind of thing and
get the same treatment. The set of extension points is published, versioned and owned by
lemonfiber, and a manifest declaring at a point this lemonfiber does not publish is
refused by name, told what it named and what exists, rather than failing to parse.

That is `F4-R14`'s rule pointed at a second surface, and it matters for the same reason: a
declaration that is skipped because nothing recognised it leaves a plugin whose stated
behaviour is narrower than its actual one, which is undetected reach rather than a missing
feature.

The namespacing rule is `F4-R4`'s, likewise. A contribution is declared into the plugin's
own namespace, so two plugins cannot collide and neither can reach the bundled set — which
is why nothing here has to be resolved by install order, and why the refusal `F4-R8`
specifies never arises for contributions. A namespaced capability is inert until something
asks for it; a namespaced contribution is attributed to its plugin wherever it appears.
Neither can be mistaken for lemonfiber's own.

Adding is not overriding, and the difference is the point. Filling a capability something
else was filling is a substitution the operator chose and the journal records
([F9](f9-bundled-capabilities.md)). Taking the identity of a bundled check is a plugin
changing what lemonfiber says about itself, which no operator asked for and no journal
would show as a choice.

### A claim is demonstrated, not asserted

A capability carries probes. Claiming it and failing its probes is a verification failure,
and a plugin that fails verification is not installed. A capability whose probes cannot be
run is reported as unproven — never as satisfied.

## States

| State | Meaning |
|-------|---------|
| `claimed` | A service declares the capability |
| `demonstrated` | The capability's probes ran against the service and passed |
| `unproven` | The probes could not be run; the claim stands unverified and is not treated as met |
| `refuted` | The probes ran and failed; the claim is false and the plugin is not installed |
| `contested` | More than one installed candidate claims the capability; refused pending the operator's choice |
| `unfilled` | Something asks for the capability and nothing installed claims it |
| `point-unknown` | A manifest declares at an extension point this lemonfiber does not publish; refused by name |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Two plugins claim the same capability | Refuse, naming both and what they collide on. Never resolve by order or recency. |
| A plugin claims a capability it does not satisfy | Its probes fail; the plugin is not installed. |
| A capability's probes cannot be run | Report unproven. An unrunnable proof is not a satisfied one. |
| Something asks for a capability nothing fills | Report it as unfilled, naming what asked, rather than failing obscurely at the point of use. |
| A plugin invents a core-looking capability name | Refuse. Only namespaced capabilities may be plugin-declared. |
| A plugin declares a namespaced capability nothing consumes | Accept it and treat it as inert. It becomes meaningful when something asks for it. |
| A substitution would leave a capability unfilled | Say so before installing rather than after — the rehearsal names what would stop being available. |
| The operator wires to a service by name deliberately | Allow it, and show it as a by-name wiring so it is visible as the exception it is. |
| A plugin declares at an extension point this lemonfiber does not publish | Refuse, naming the point and listing the ones that exist. Not a parse failure — the distinction `F4-R14` draws, applied to contributions. |
| A contribution would take the identity of a bundled check or remedy | Refuse, naming both. Adding is not overriding; standing in for something bundled is F9's subject. |
| The word `capabilities` is already taken | The stack manifest's `Service.capabilities` already means *kernel* capabilities granted to a container. These are a different thing entirely, and one of the two MUST be renamed rather than overloaded — a field whose meaning depends on where you are reading it is how a security-relevant setting gets misread. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F4-R1** | Services MUST declare what they can do as named capabilities, and stack wiring MUST ask for capabilities rather than naming services. |
| **F4-R2** | The core capability vocabulary MUST be published, versioned and owned by lemonfiber. |
| **F4-R3** | Every core capability MUST carry a stated contract and probes that demonstrate it. |
| **F4-R4** | A plugin MUST NOT declare a capability in the core vocabulary's namespace, and MUST be able to declare namespaced capabilities of its own. |
| **F4-R5** | *Withdrawn — carried to [F9-R1](f9-bundled-capabilities.md) and [F9-R2](f9-bundled-capabilities.md) when the bundled declarations became their own feature. The number is not reused.* |
| **F4-R6** | A service claiming a capability whose probes fail MUST NOT be installed or wired to. |
| **F4-R7** | A capability whose probes cannot be run MUST be reported as unproven and MUST NOT be treated as satisfied. |
| **F4-R8** | Where more than one installed candidate claims the same capability, lemonfiber MUST refuse and name every claimant and the collision, and MUST NOT resolve it by install order, precedence or recency. |
| **F4-R9** | A capability that something asks for and nothing fills MUST be reported explicitly, naming what asked for it. |
| **F4-R10** | Substituting one service for another MUST be expressible as a change of which service fills a capability, and MUST be journalled as a change. |
| **F4-R11** | A substitution that would leave a capability unfilled MUST state so before it is applied. |
| **F4-R12** | Wiring to a specific service by name MUST remain possible for the operator, MUST be shown as a by-name wiring, and MUST NOT be introducible by a plugin. |
| **F4-R13** | What a service can do MUST NOT share a name with the kernel capabilities a container is granted; the two MUST be distinguishable without knowing which document is being read. |
| **F4-R14** | Extending the set of things a service may declare MUST NOT require a closed enumeration in first-party source to be edited, and an unrecognised declaration MUST be refused by name rather than by parse failure. |
| **F4-R15** | The points at which a plugin may extend lemonfiber itself MUST be published, versioned and owned by lemonfiber, and a manifest declaring at a point this lemonfiber does not publish MUST be refused by naming that point and the ones that exist, rather than by parse failure. |
| **F4-R16** | A contribution MUST be declared in the declaring plugin's own namespace, MUST NOT be declarable in the namespace of anything bundled, and MUST be attributed to that plugin wherever it appears. |
| **F4-R17** | A plugin MUST NOT replace, re-order or suppress a bundled check or the remedy it carries, and a contribution that would MUST be refused naming what it collided with. Standing in for something bundled MUST remain an operator's recorded choice rather than a manifest's assertion. |

## Related

- [F9 Capabilities of the bundled services](f9-bundled-capabilities.md) — the nineteen that implement this vocabulary, and the wiring converted to ask in it
- [F3 Plugin manifests](f3-stack-manifests.md) — where a capability is claimed and asked for
- [F2 Service catalogue](f2-service-catalogue.md) — what each bundled service is, which capabilities describe in machine terms
- [F6 Plugin lifecycle](f6-plugin-lifecycle.md) — when the probes run and what a failure costs
- [F7 Plugin provenance](f7-plugin-provenance.md) — how a substitution stays visible afterwards
- [D1 Auto-wiring & seeding](../d-content/d1-seed.md) — the wiring this generalises
- [C1 Diagnostics](../c-trust/c1-diagnostics.md) — the register a contributed check joins, in the vocabulary this publishes
