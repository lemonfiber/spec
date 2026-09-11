---
id: F8
title: Recipes and named adapters
kind: feature
area: F
audience: operator
status: draft
maturity: planned
priority: P1
labels: [extensibility, verification, security]
requires: [F3, F4]
relates: [F5, F6, F7, G8, C1]
---

# F8 — Recipes and named adapters

**Status:** Draft · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Let a plugin configure the thing it installed, and the services around it, without
letting it become a way to move an operator's secrets somewhere they did not agree to.

[F3](f3-stack-manifests.md) says what a plugin is: data describing a service. That is
enough to *add* a service and not enough to *substitute* one. The case the whole design
exists for — run Plex instead of Jellyfin — needs an account created, a server claimed and
a token read back, because the media server is what the request service signs in through.
Those are first-run flows, and a manifest that could not express them would describe a
container nobody had configured.

So a plugin carries **recipes**: ordered calls that capture values, feed them into later
calls, branch on what came back, and wait when something is not ready yet. Where even that
cannot reach, it **names** an adapter lemonfiber implements, and never supplies one.

This is separated from F3 because it is the part with the risk in it. F3's manifest
describes a container whose reach is fixed by lemonfiber
([ADR-0021](../../../00-overview/decisions/0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md)).
A recipe is different in kind: it runs with lemonfiber's own authority — the credential
store, every service in the stack on its loopback port, and the open internet — and it
does so on behalf of a manifest a stranger wrote. Shipping it in the same version as the
first plugin anything would mean the riskiest mechanism arriving before anybody has
operated the simplest one.

## Behaviour

### A recipe is a sequence, not a program

A recipe is an ordered list of calls. Each may **capture** values out of a response and
name them, **substitute** values captured earlier into a later call, **branch** on a
status code or a captured value, and **wait and retry** a bounded number of times when a
service is not ready.

There is no arbitrary computation, no loop that does not terminate, no destination worked
out while running, and no call assembled out of something that came back. A recipe is
powerful enough to create an account, claim a server and read back a token — which is what
a first-run flow is — and no more powerful than that.

That bound is not tidiness. It is what makes the next section possible: a sequence this
shape has a **finite, computable set of things it could do**, so the question *what would
this plugin send, and where* can be answered by reading the manifest rather than by
running it and watching. Relaxing the bound later would not cost elegance; it would cost
the only mechanism that makes recipes safe to offer.

### What a recipe may carry is declared as pairs

Declaring the secrets a plugin holds and the hosts it reaches, as two separate lists,
describes both halves of a problem and refuses neither. A manifest saying *"I capture the
media server's API key"* and *"I reach `plex.tv`"* has declared everything and still
described sending the first to the second.

So the manifest declares **pairs**: this captured value, to that destination. Every value
carries where it came from — a service in this stack, the credential store, the operator,
or an external response — and every destination is either a service in this stack or an
external host. A flow with no pair behind it is a validation failure, found before
anything runs ([ADR-0022](../../../00-overview/decisions/0022-a-recipe-declares-pairs-not-lists.md)).

The verbosity is the point. A plugin capturing three values and reaching two hosts has six
possible pairs and will want very few of them, and the ones it does not declare are the
ones nobody has to wonder about afterwards.

### Anything leaving the machine is agreed to, specifically

A pair that carries a value to an external host is stated at the rehearsal in the terms an
operator can judge — *this plugin will send your media server's API key to `plex.tv`* —
and is approved as itself. Not as a consequence of approving the install: a single yes to
an installation is consent to the installation, and the pairs are the one part of a
manifest an operator can meaningfully weigh.

Everything else a rehearsal says is about a change to their own machine. This is the only
part about something leaving it.

### A recipe names, and never addresses

An in-stack destination is named by its service id, and lemonfiber resolves it to the
address it already knows. An external destination is named by a DNS name. A manifest
carrying an IP literal, a network range or a bare host port is refused.

Without that rule a declared host is a declared host wherever it points, and the machine
this runs on sits beside a router's administration page, a NAS and whatever else the
household owns — none of it reachable from outside, all of it reachable from here. Names
close the manifest; they do not close DNS, so an external name that answers with a
loopback, private or link-local address is refused at the call. The manifest said this
destination was outside; an answer from inside contradicts it, and the contradiction is
the refusal rather than a thing to be reconciled.

### Where data will not reach, a plugin names an adapter

Some flows cannot be honestly expressed as calls and captures. For those a plugin names
one of a fixed set of **adapters** lemonfiber implements and ships — the Servarr-shaped
registration flow, and others as they earn their place. The plugin supplies the
parameters; lemonfiber supplies the behaviour.

This keeps the awkward cases in code that is reviewed, tested and covered like the rest of
the product, while still letting a plugin reach them. The set is published rather than
discovered, and naming one that does not exist is a validation failure listing what is
available.

## States

| State | Meaning |
|-------|---------|
| `flows-declared` | Every flow the recipe could produce has a declared pair behind it |
| `undeclared-flow` | A value could reach a destination no pair permits; refused at validation |
| `awaiting-approval` | A pair carrying a value out of the machine has been stated and not yet agreed to |
| `approved` | The operator agreed to each outward pair, named |
| `address-literal` | The manifest names an address rather than a name; refused |
| `resolved-inward` | A destination declared external answered with a private, loopback or link-local address; refused at the call |
| `adapter-unknown` | The manifest names an adapter this lemonfiber does not implement |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| A recipe could send a captured secret somewhere no pair allows | Refuse at validation. The flow is computable from the manifest, so this is found before a call is made rather than after two have landed. |
| A pair is declared and the operator declines it | The install does not proceed. A declined disclosure is not something to route around by installing anyway and failing later. |
| A manifest declares a pair it never uses | Allowed. Declaring more than is used is conservative, and the account says what was declared. |
| A manifest names `192.168.1.1` | Refuse. A recipe names services and hosts; it does not address machines. |
| An external name resolves into the home network | Refuse at the call, naming the name and what it answered. Checked per call, because the answer can change between them. |
| A recipe branches on a value that was never captured | Refuse at validation; the reference is checkable without running anything. |
| A recipe's call never succeeds | Bound the retries, then fail naming the call and what it last answered. |
| The manifest names an adapter that does not exist | Refuse, naming the adapter and listing what is available. |
| A plugin needs a destination it cannot know until it runs | Not expressible, and not worked around. The honest answer is a declaration form that is still statically bounded, decided once for everybody. |
| An operator has switched off a plugin's reach | Its recipes report that nothing was asked, rather than failing as though the destination were down (`G8-R16`). |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F8-R1** | A recipe MUST be an ordered sequence of calls supporting capture, substitution of earlier captures, branching on status or captured value, and bounded wait-and-retry. |
| **F8-R2** | A recipe MUST NOT support unbounded computation, a destination computed while running, or a call assembled out of a response. |
| **F8-R3** | Every value a recipe captures MUST carry its origin — a service in this stack, the credential store, the operator, or the response of an external host. |
| **F8-R4** | Every destination MUST be classified as a service in this stack or as an external host, and there MUST be no third classification. |
| **F8-R5** | A manifest MUST declare each permitted flow as a pair naming a captured value and a destination, and a flow with no declared pair MUST fail validation. |
| **F8-R6** | The flow check MUST be performed statically, before any of the recipe's calls is made. |
| **F8-R7** | A pair carrying a value to an external host MUST be approved by the operator at rehearsal, named as that value and that destination, and MUST NOT be approved implicitly by approving the installation. |
| **F8-R8** | A recipe MUST name an in-stack destination by its service id and an external destination by a DNS name, and a manifest containing an address literal, a network range or a bare host port MUST be refused. |
| **F8-R9** | A destination declared external that resolves to a loopback, private or link-local address MUST be refused at the call, and the resolution MUST be checked on each call rather than once. |
| **F8-R10** | A recipe MUST NOT reach any host, service or value the manifest has not declared. |
| **F8-R11** | A plugin MAY name one of a published, fixed set of lemonfiber-implemented adapters for flows recipes cannot express, and MUST NOT supply an adapter of its own. |
| **F8-R12** | Naming an adapter this lemonfiber does not implement MUST be refused, naming the adapter and the set that is available. |
| **F8-R13** | The set of adapters MUST be published rather than discovered. |

## Related

- [ADR-0022](../../../00-overview/decisions/0022-a-recipe-declares-pairs-not-lists.md) — why pairs rather than lists, and why the check is static
- [F3](f3-stack-manifests.md) — what a plugin is, and the manifest these extend
- [F4](f4-capabilities.md) — the capability a substitution fills once a recipe has configured it
- [F6](f6-plugin-lifecycle.md) — the rehearsal the approval happens in
- [G8](../g-ux/g8-privacy.md) — the account of what leaves this machine, and the switch a declared reach gets
- [plugin-manifest contract](../../../20-architecture/contracts/plugin-manifest.md) — where the blocks these add are declared
