---
id: F14
title: Every part is a plugin
kind: feature
area: F
audience: operator
status: accepted
maturity: planned
priority: P1
labels: [extensibility, wiring, verification, security]
requires: [F3, F4, F8, F9]
relates: [F2, F5, F6, F7, D11, D6, B1, G5]
---

# F14 — Every part is a plugin

**Status:** Accepted · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Let a household run what it chooses, in every part of its stack, and have what it chose
work as fully as the part it replaced. Plex instead of Jellyfin means members still sign
in through the request service, still see their own shelves under their own limits, still
play through the guarded door on their phones, and still pick up where they left off.
Traefik instead of Caddy means every household name still answers. A guard of the
operator's choosing means the same cases are still refused.

The model since [F3](f3-stack-manifests.md) and [F4](f4-capabilities.md) can settle a
plugin as the filler of a capability, but it cannot make the plugin work. Behaviour lives
in adapters compiled into the core, and the core names the parts it ships. This feature
moves every part's behaviour behind a published contract, so the core holds no code for
any service, and every part, first-party or not, is a plugin
([ADR-0041](../../../00-overview/decisions/0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md)).

## Behaviour

### A capability is a contract

Each capability the vocabulary names has a published, versioned contract: HTTP and JSON,
generated from the core's port types the way the web API's documents are. The contract
is what the core asks of whatever fills the capability. For the media server, that is
the household's accounts and limits, setup, titles and seasons, what a member was
part-way through, the grant, progress, the byte guard and the locations a member is
given. A service says which contracts it speaks, and the core holds one client per
contract and nothing about any product.

### A part is its upstream and its adapter

A plugin that fills a capability brings two containers. One runs the upstream, such as
Plex's server. The other is the plugin's adapter, which speaks the contract and
translates to the upstream. The adapter's code runs in its own container, never in
lemonfiber's process ([F3-R6](f3-stack-manifests.md)). The core reaches it with a key
minted for that plugin alone, on a network shared only by the core, the adapter and its
upstream. Every answer is held to the contract's schema and bounded in size and time, and
anything else is refused.

### The bundled parts are plugins too

Jellyfin, the curators, the download clients, the indexers, the request service, the
subtitle fetcher, the proxy, the dashboard, the egress guard, the helpers and
lemonfiber's own guards are each a first-party plugin in a repository of their own. They
are installed, updated, removed and validated the way any other plugin is. The bundle
says which first-party plugin fills each capability until the operator chooses otherwise,
and it travels inside the binary, so a first install needs no network.

### Every part has a capability, and something asks for it

The proxy, the dashboard, quality sync, archive extraction, the stream guard, decline and
the request gate join the vocabulary. Every capability is asked by something in the
bundle, so every part has a slot a substitute can fill. A plugin may ask for capabilities
too, which lets a substitute stand in for a part that itself asks. No plugin links to
another by name.

### The guard follows the media server

The media server's filler declares how its bytes are guarded: which paths carry them,
what question decides whether a session may have them, and in what form a member's token
is presented. The stream guard's filler enforces exactly that. Every location a member is
given, the stream and the pictures alike, is built from templates the filler declares, so
a member's app works the same against any media server.

### A substitution replaces

Choosing a filler stops the part it replaces and takes it out of its form. Its data stays
where it was, so undoing the choice brings it back as it was. The rehearsal says what
does not carry over: accounts the old media server held are not accounts on the new one,
and progress stays where it was recorded. Asking the household's members back is offered
as part of the change.

### One privileged shape

The egress guard needs to manage the network and open a tunnel, which no other plugin may
do. A filler of the egress guard capability may take one shape the core writes, with
network administration and the tunnel device and nothing else, once the operator has
approved it at install.

### Each slot is proved by a substitute

Every capability has a substitute beside its first-party filler, built to the same
contract and run end to end against its pinned upstream: installed, its first-run flow
run, held to the conformance suite, substituted, the features its capability serves
exercised, and undone.

## States

| State | Meaning |
|---|---|
| `conforming` | The adapter answers every operation of the contracts it speaks as the suite requires |
| `nonconforming` | An operation answered outside the contract; the plugin does not fill that capability until a live proof it passes clears the record |
| `substituted` | The operator's chosen filler serves the capability; the part it replaced is stopped, its data kept |
| `restored` | A substitution was undone; the part it replaced runs again with its data |

## Edge cases

| Situation | Behaviour |
|---|---|
| An adapter answers with a field the contract does not have, or a body larger than the bound | Refused as nonconforming for that call; the call fails closed and nothing reads the answer |
| The stream guard's question goes unanswered | The byte request is refused, as it is for the first-party guard |
| A substitute's adapter speaks an older major of a contract the core no longer speaks | Refused at install, naming the contract and the majors the core speaks |
| The operator undoes a substitution after members used the substitute | The part that was replaced comes back with its data; what members did on the substitute stays on the substitute |
| A plugin that is not the egress guard's filler asks for the privileged shape | Refused at validation, naming the field |
| An adapter claims an upstream release it has no recordings for | Refused at install, naming the release |
| A plugin recorded nonconforming is proved again and fails | The record stays, and the proof names each case that failed |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F14-R1** | Every capability in the vocabulary MUST have a published, versioned contract generated from the core's port types, and the core MUST reach every service only through a contract it speaks. |
| **F14-R2** | The core MUST hold no code specific to any service, and an architecture check MUST refuse a bundled service's name in core code outside the bundle. |
| **F14-R3** | A service MUST declare the contracts it speaks, and a manifest MUST NOT name an in-process adapter. |
| **F14-R4** | Every answer from an adapter MUST be held to its contract's schema and bounded in size and time, and an answer outside them MUST be refused and MUST NOT be read. |
| **F14-R5** | The core MUST reach an adapter only with a key minted for that plugin alone, on a network shared only by the core, the adapter and its upstream, and an adapter MUST NOT be given a credential lemonfiber holds for anything else. |
| **F14-R6** | A plugin MUST NOT fill a capability unless its adapter conforms to that capability's contract, proved by recordings against its pinned upstream and by a live conformance pass at install, and first-party adapters MUST be held to the same suite. |
| **F14-R7** | Every part of the bundle MUST be a first-party plugin, installed, updated, removed and validated by the path any plugin takes, and the bundle and its first-party manifests MUST be embedded in the binary. |
| **F14-R8** | The vocabulary MUST name `proxy.front`, `dashboard.show`, `quality.sync`, `archive.extract`, `stream.guard`, `invite.decline` and `request.gate`, each with a contract, and every capability in the vocabulary MUST be asked by something in the bundle. |
| **F14-R9** | A plugin MAY ask for capabilities and MUST NOT link to a service by name. |
| **F14-R10** | The stream guard's filler MUST enforce the guard the media server's filler declares, and every location the core gives a member MUST be built from templates the media server's filler declares. |
| **F14-R11** | Substituting a filler MUST stop the part it replaces and take it out of its form while keeping its data, undoing it MUST bring that part back with its data, and the rehearsal MUST say what does not carry over. |
| **F14-R12** | A filler of `network.egress-guard` MAY take the one privileged shape the core writes, which MUST grant network administration and the tunnel device and nothing else, only after the operator approves it at install, and a manifest asking for it for any other capability MUST be refused by name. |
| **F14-R13** | An adapter MUST declare the upstream releases it supports, each proved by its own recordings, and the core MUST NOT compare versions. |
| **F14-R14** | Every capability MUST be proved by a substitute other than its first-party filler, run end to end against its pinned upstream through install, its first-run flow, conformance, substitution, the features the capability serves, and undo. |
| **F14-R15** | Every first-party adapter MUST be built on the adapter kit, from a repository of its own, into an image the release train publishes. |
| **F14-R16** | An answer outside a contract MUST be recorded against the plugin with the capability, the operation, why and when, and a plugin recorded nonconforming for a capability MUST NOT fill it until it passes a live proof run after the record; updating it, installing it again and proving it again MUST each run that proof, and a passing proof MUST clear its records. |
| **F14-R17** | The installed plugins as `lemonfiber plugin installed` and `GET /api/plugins` answer them MUST name, for each plugin, every capability it is recorded nonconforming for, with the operation, why and when, and nothing a member is shown MUST name it. |

## Related

- [ADR-0041](../../../00-overview/decisions/0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md): the decision this feature carries out
- [F3](f3-stack-manifests.md): plugin manifests, and code that never runs in lemonfiber's process
- [F4](f4-capabilities.md): the capability vocabulary, fillers and substitution
- [F8](f8-recipes.md): first-run flows, which capture what an adapter is given
- [F9](f9-bundled-capabilities.md): the bundled parts' capabilities, which become first-party plugins
- [D11](../d-content/d11-watching-what-the-house-holds.md): the guard and the locations a member is given
