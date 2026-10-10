---
id: F14
title: Every part is a plugin
kind: feature
area: F
audience: operator
status: accepted
maturity: building
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

A plugin's service asks in the manifest's `[[ask]]`, naming a core capability and, where it
wants every service that fills it rather than one, `each`. Nothing in an ask can name the
service that answers it. A plugin's ask is settled as the stack's own asks of that capability
are: against everything installed that claims it, by the operator's choice, and otherwise by the
stack's own choice. A credential reaches the asker only through the gate in
[Credentials between plugins](#credentials-between-plugins). The wiring lists a plugin's asks
after the stack's, each naming the plugin. An install or update states what each of its asks
would reach before it acts.

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
do. The upstream an egress guard adapter fronts may declare `shape = "egress-guard"`, and
the core writes its entry as every plugin's entry with network administration and the
tunnel device added and nothing else. The adapter stays unprivileged. The reading names
each service taking the shape, and the operator approves each one apart from the offer,
on every install and update that takes it.

### Each slot is proved by a substitute

Every capability has a substitute beside its first-party filler, built to the same
contract and run end to end against its pinned upstream: installed, its first-run flow
run, held to the conformance suite, substituted, the features its capability serves
exercised, and undone.

### Credentials between plugins

Wiring hands credentials from one part to another: a curator's key to the subtitle
finder, the media server's to the request service. A credential lemonfiber holds
reaches a plugin's service only where it is that plugin's own, or where the plugin is
first-party and the credential is the stack's or another first-party plugin's.

A plugin is first-party only where this build embeds it in its first-party set: its id
and the digest of its manifest, as the signed default bundle names them at the release
the build pins. Anything else is third-party however it was installed, a reviewed
catalogue entry included. Until the bundle is embedded, the set is empty and nothing is
first-party.

A third-party substitute may be granted one named credential for a capability it fills.
The grant is part of the install or update offer and needs the operator's approval; it
is journalled, can be revoked, and is shown on the credentials surface. Without a grant,
nothing crosses to it.

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
| A service that is not the upstream of an egress guard adapter declares the privileged shape | Refused at validation, naming `service <id>.shape` |
| An adapter claims an upstream release it has no recordings for | Refused at install, naming the release |
| A plugin recorded nonconforming is proved again and fails | The record stays, and the proof names each case that failed |
| A plugin's ask names a namespaced capability, its own or another plugin's | Refused at validation naming `ask <service>.capability`: a namespaced capability carries the id of the plugin it belongs to, so asking for one names a plugin |
| A plugin's ask names a service the plugin does not declare | Refused at validation naming the service and the services declared |
| A plugin asks for a capability nothing installed claims | Listed as unfilled, naming the plugin's service as what asked (F4-R9) |
| A plugin asks for one filler of a capability several claim and the operator chose none | Settled by the stack's own choice for that capability, as the stack's ask is; contested only where the stack has none (F4-R8) |
| A plugin's service asks for a capability it provides | Refused at validation naming the service and the capability: nothing asks itself |

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
| **F14-R12** | A plugin's service MAY declare `shape = "egress-guard"` only where it is the upstream an adapter of the same plugin fronts and that adapter speaks `network.egress-guard`, any other service declaring it MUST be refused at validation naming `service <id>.shape`, and lemonfiber MUST write that service's entry as every plugin's entry plus exactly the `NET_ADMIN` capability and the `/dev/net/tun` device, and MUST write neither for any other service. |
| **F14-R13** | An adapter MUST declare the upstream releases it supports, each proved by its own recordings, and the core MUST NOT compare versions. |
| **F14-R14** | Every capability MUST be proved by a substitute other than its first-party filler, run end to end against its pinned upstream through install, its first-run flow, conformance, substitution, the features the capability serves, and undo. |
| **F14-R15** | Every first-party adapter MUST be built on the adapter kit, from a repository of its own, into an image the release train publishes. |
| **F14-R16** | An answer outside a contract MUST be recorded against the plugin with the capability, the operation, why and when, and a plugin recorded nonconforming for a capability MUST NOT fill it until it passes a live proof run after the record; updating it, installing it again and proving it again MUST each run that proof, and a passing proof MUST clear its records. |
| **F14-R17** | The installed plugins as `lemonfiber plugin installed` and `GET /api/plugins` answer them MUST name, for each plugin, every capability it is recorded nonconforming for, with the operation, why and when, and nothing a member is shown MUST name it. |
| **F14-R18** | A credential lemonfiber holds MUST reach a plugin's service only where it is that plugin's own, where the plugin is first-party and the credential is the stack's, or where both the plugin and the credential's owner are first-party. |
| **F14-R19** | A plugin MUST be first-party only where the build embeds its id and the digest of its manifest in its first-party set, as the signed default bundle names them at the release the build pins; any other plugin MUST be third-party however it was installed. |
| **F14-R20** | A third-party plugin MAY be granted one named credential for a capability it fills; the grant MUST be part of the install or update offer and approved by the operator, MUST be journalled and revocable, and MUST be shown on the credentials surface, and without a grant no credential MUST cross to it. |
| **F14-R21** | An install or update whose plugin takes the egress guard's shape MUST state in its reading each service taking it with the capability and the device it is given, MUST NOT act unless the operator approved that shape for that service apart from the offer, written `egress-guard@<service>`, and MUST refuse an approval naming a service that does not take it. |
| **F14-R22** | A plugin's service MAY ask for a core capability in the manifest's `[[ask]]`, naming the capability and optionally `each`; the manifest MUST have no field by which an ask names the service that fills it, and an ask naming a capability outside the published core vocabulary, a namespaced one included, naming a service the plugin does not declare, or naming a capability its own service provides MUST be refused at validation, naming the ask and what it named. |
| **F14-R23** | A plugin's ask MUST be settled as the stack's own asks of that capability are: against every installed claimant, by the operator's choice where one is recorded, otherwise by the stack's own choice for that capability, and otherwise contested or unfilled; every connection made for it MUST hand a credential only where F14-R18 or F14-R20 lets it cross, and its asker MUST join no network beyond the default. |
| **F14-R24** | The wiring, as `lemonfiber wiring` and `GET /api/wiring` answer it, MUST carry every installed plugin's asks after the stack's, each with the origin of the service that asks, and a plugin's asks MUST be counted wherever the stack's are: in what nothing fills, in what a substitution changes, and in what an install would leave contested. |
| **F14-R25** | An install or update reading MUST state every ask the plugin's services would make, each with what it would reach and how that would be settled; its offer MUST be named over those asks as a part of its own, and an answer to a reading whose asks have since moved MUST be refused naming that part. |
| **F14-R26** | Where the media server is a plugin's service that speaks `identity.source`, its first-run setup MUST go over that contract with an administrator's password lemonfiber mints and keeps under that server's own setting, and the request service's identity setup MUST be given that password with the stack-network address and the `native` API of the service the adapter `fronts`; where that service declares no `native` API, the setup MUST NOT be attempted and the run MUST say so, naming the plugin. |
| **F14-R27** | lemonfiber MUST write the entry of every plugin service that speaks a contract to run as the operator's uid and gid, as the stack's own images run, and MUST write the key it asks that service with readable by that uid alone; a service that speaks none MUST be written without a user. |
| **F14-R28** | Where an adapter's upstream needs a credential lemonfiber keeps, lemonfiber MUST be the only writer of it: it MUST write it into the adapter's configuration directory as `upstream.json`, a JSON object of named strings readable by the operator's uid alone, whenever it creates, rotates or moves that credential, and the adapter MUST read it there and MUST NOT write it. |
| **F14-R29** | An install or update MUST honour a service's `replaces` only where the plugin is first-party, moving the bundled service it names in place under the same container name, configuration directory and data; a third-party plugin declaring `replaces` MUST be refused at install and update, naming the service. |

## Related

- [ADR-0041](../../../00-overview/decisions/0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md): the decision this feature carries out
- [F3](f3-stack-manifests.md): plugin manifests, and code that never runs in lemonfiber's process
- [F4](f4-capabilities.md): the capability vocabulary, fillers and substitution
- [F8](f8-recipes.md): first-run flows, which capture what an adapter is given
- [F9](f9-bundled-capabilities.md): the bundled parts' capabilities, which become first-party plugins
- [D11](../d-content/d11-watching-what-the-house-holds.md): the guard and the locations a member is given
