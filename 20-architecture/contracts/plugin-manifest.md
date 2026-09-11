# Contract: `plugin.toml`

**Status:** Draft

The interface between `lemonfiber` and a plugin. Everything lemonfiber will do
on a plugin's behalf comes from this file; it knows nothing about a plugin that
is not declared here.

**Satisfies:** [F3-R1](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R2](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R8](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R10](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R14](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R23](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R24](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R21](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R22](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F4-R14](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F1-R9](../../10-functional/features/f-extensibility/f1-customisation.md)

---

## Why this file exists

[ADR-0021](../../00-overview/decisions/0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md)
decided that a plugin is declarative data and that lemonfiber writes its Compose
entry rather than accepting one. This says what that data is.

It is a second manifest rather than a use of the first because the two describe
different things. [`stack.toml`](stack-manifest.md) describes **a whole stack** —
its profiles, its forms, and the complete set of services that constitute it. A
plugin describes **one addition to a stack that already exists**, and the
difference is not cosmetic: a fork replaces the stack and is the operator's own
work, unattributed and unjournalled ([F1-R3](../../10-functional/features/f-extensibility/f1-customisation.md));
a plugin is a stranger's work added to a running system, and every one of its
changes has to be attributable and reversible
([F7-R1](../../10-functional/features/f-extensibility/f7-plugin-provenance.md)).
Overloading one file with both verbs would mean a document whose meaning depends
on how it arrived.

## What this version covers

This describes the **additive** plugin: one that adds a service to a stack. That
is the whole of what a plugin is in the version that introduces the format, and
it is deliberately the smallest thing that is genuinely useful — a service that
runs, is health-gated, appears in status, is journalled and can be removed.

Recipes, the hosts they reach, the values they capture and the bundled settings
they override each add a block to this file in the version that introduces them.
Every one of those additions is **additive**: a manifest written against this
version stays valid, which is the property that lets the format get real use
before `1.0.0` freezes it.

## File location

`plugin.toml`, at the root of a plugin's source — a git repository or a
directory. One plugin per source; a source declaring two is refused rather than
resolved, because "which one did I install" has no good answer.

## Top-level structure

```toml
schema_version = 1

[plugin]     # identity and provenance
[[service]]  # exactly one, in this version
[requires]   # what the plugin needs of lemonfiber
```

## `[plugin]` — identity and provenance

```toml
[plugin]
id          = "plex"
name        = "Plex Media Server"
version     = "1.2.0"
description = "Plays your library on TVs, phones and browsers"
without_it  = "Files on disk, no way to watch them"
upstream    = "https://github.com/plexinc/pms-docker"
license     = "Plex-EULA"
forms       = ["library", "full"]
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | Unique, lowercase. The name it is installed and journalled under. |
| `name` | string | ✔ | Human-facing |
| `version` | string | ✔ | Semver. The plugin's own content version, moved by its author. |
| `description` | string | ✔ | What it does *for the operator*, in the terms [F2-R1](../../10-functional/features/f-extensibility/f2-service-catalogue.md) asks of a bundled service |
| `without_it` | string | ✔ | The consequence of its absence (`F2-R2`) |
| `upstream` | string | ✔ | Project URL, so the operator can judge the thing rather than the wrapper |
| `license` | string | ✔ | SPDX identifier. **Not** required to be OSI-approved — see below. |
| `forms` | array | ✔ | Which forms the service joins. Every entry MUST name a form the stack declares. |

`description` and `without_it` are required of a plugin for the same reason they
are required of a bundled service: the catalogue exists to convert an inventory
into a judgement about severity, and a plugin that appears in `lemonfiber ps`
without them puts a name in front of an operator and nothing else.

**The licence is declared but not constrained.** Every bundled service is
OSI-licensed and `F2-R5` fails validation on anything else, because the bundled
set is a curated list this project stands behind. A plugin is not: the operator
chose it. Refusing to install proprietary software on somebody's own machine
would be `F1`'s objection exactly — the tool standing between an operator and
their stack. So the licence is **recorded and shown**, including on the
`lemonfiber plugins` read (`F7-R5`), and the operator decides. A plugin whose
licence is absent is refused; one whose licence is merely not open is installed
and said so.

**There is deliberately no `min_lemonfiber_version`.** `stack.toml` has one, and
a plugin has none on purpose: `F3-R21` requires an unmet requirement to be
refused by naming the capability rather than a version. See
[`[requires]`](#requires--what-the-plugin-needs-of-lemonfiber).

## `[[service]]` — what runs

Declared in [`stack.toml`](stack-manifest.md#service)'s vocabulary, restricted to
the fields below. The restriction is the substance of ADR-0021: the set of
fields *is* the set of things a plugin may ask for.

```toml
[[service]]
id     = "plex"
name   = "Plex"
image  = "docker.io/plexinc/pms-docker"
digest = "sha256:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
tag    = "1.41.3.9314"
port   = 32400
bind   = "lan"
health = { kind = "http", path = "/identity", timeout_s = 90 }
criticality = "important"
media_types = ["movie", "tv"]
takes_data  = true
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | Unique across the stack **and** every installed plugin. A collision is refused, naming both. |
| `name` | string | ✔ | Human-facing |
| `image` | string | ✔ | Registry path, without tag or digest |
| `digest` | string | ✔ | `sha256:…`. What actually runs. |
| `tag` | string | ✔ | The human-readable version the digest corresponds to. Recorded and shown; never resolved. |
| `port` | integer | | Primary UI/API port. Omitted for a service with no listener. |
| `bind` | enum | ✔ if `port` | `loopback` \| `lan`. A **tier**, not an address — see below. |
| `health` | table | | As `stack.toml`. Absent means lifecycle waits on container state only. |
| `criticality` | enum | ✔ | As `stack.toml`. A plugin MUST NOT declare `critical` — see below. |
| `media_types` | array | | Which media types it handles |
| `takes_data` | bool | | `true` if it needs the data root mounted. Default `false`. |

### The image is named by digest

`F3-R8` requires a referenced image to be pinned. A tag is not a pin: it is a
name the publisher can repoint, so the image reviewed and the image run can
differ with nothing in the manifest changing. That is the same reasoning
[ADR-0009](../../00-overview/decisions/0009-action-pinning.md) applied to
workflow actions — *whoever can move the ref changes what every consumer runs,
unreviewed at the consumer* — and it applies with more force here, because the
consumer is an operator's home machine rather than a CI runner.

So `digest` is what lemonfiber writes into the generated entry, and `tag` is
carried beside it as the readable name. A manifest with a tag and no digest is
refused. Declaring a digest that does not correspond to the tag is not
detectable without reaching the registry and is not treated as though it were:
the digest is what runs, and the tag is a label on it.

### `bind` is a tier, and lemonfiber assigns the address

A plugin declares `loopback` or `lan`. It cannot declare an address, a
host-facing interface, or a published port mapping, because a plugin that could
write its own address could place an admin surface on the LAN without touching
anything [C6](../../10-functional/features/c-trust/c6-web-security.md) inspects.
lemonfiber renders the tier to an address exactly as it does for a bundled
service, and the two-tier policy stays a property of the system rather than a
request the plugin makes.

### A plugin may not declare itself `critical`

`critical` means *its failure has consequences outside the machine*, and in the
bundled stack exactly one service holds it. It is not a severity a contributor
assigns to their own work: the classification drives how failures are reported
and how hard lemonfiber tries to stop the operator proceeding. A plugin
declaring it is refused, naming the value and the four that are available.

### The fields that are absent, and why

These exist in `stack.toml` and are **not** part of a plugin's vocabulary. A
manifest carrying one is refused by name (`ARCH-R84`), rather than having it
ignored:

| Field | Why a plugin may not declare it |
|-------|--------------------------------|
| `grants` | Kernel capabilities. The allow-list is one entry long and exists so the VPN tunnel can hold `NET_ADMIN`; extending it on the strength of an untrusted manifest is a deny-list wearing a hat. |
| `depends_on` | The bundled stack contains exactly one cross-service dependency (`B1-R14`), and it is the one that keeps torrent traffic inside the tunnel. A plugin introducing an ordering edge between services it does not own is a source of failures nobody can attribute. |
| `host_managed` | Native-mode lifecycle is the operating system's (`B2-R15`). A plugin cannot install a system service. |
| `profile` | Assigned, not declared — see below. |
| `api` | How lemonfiber talks to a service for seeding. A plugin naming an adapter is the subject of the version that introduces recipes; until then a plugin's service is operated generically, as `F1-R10` and `F1-R11` already promise for a service lemonfiber does not know. |
| `last_release` | An abandonment signal maintained by the people reviewing the bundled pins (`F2-R14`). Self-reported by a plugin it would signal nothing. |

## What lemonfiber writes

A plugin's service gets **its own profile**, named for the plugin, which is
added to the closure of each form the plugin declared. Its own profile rather
than an existing one, because a profile is the unit that starts and stops
together, and a stranger's service joining `tv` would mean `lemonfiber up tv`
could no longer be described without naming what is installed.

From the declaration above, lemonfiber generates:

```yaml
plex:
  extends:
    file: compose/_common.yml
    service: defaults
  image: docker.io/plexinc/pms-docker@sha256:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
  profiles: [plugin-plex]
  ports: ["${LAN_BIND}:32400:32400"]
  volumes:
    - ${DATA_ROOT:-./data}:/data
    - ./config/plex:/config
```

That is the whole of it, and the whole of what it can ever be. There is no field
in `plugin.toml` that adds a line to this, which is what makes "what can this
plugin reach" answerable from the format rather than from the instance.

`defaults` rather than `rootless`: the `PUID`/`PGID` pair is a LinuxServer.io
convention, and setting it on an image that ignores it is a silent no-op that
reads like a security control. Which template a plugin's service extends follows
from whether it declares it honours the pair, the same question the bundled
stack answers per service.

The `${DATA_ROOT}:/data` mount appears only where `takes_data` is `true`, and
when it appears it is the **single** data mount — [ADR-0006](../../00-overview/decisions/0006-single-data-mount.md)'s
rule holds for a plugin by construction rather than by review, because there is
no second mount to declare.

## `[requires]` — what the plugin needs of lemonfiber

```toml
[requires]
capabilities = ["service.add", "service.health.http"]
```

A plugin names what it needs. lemonfiber answers from the same set
`GET /api/capabilities` serves (`ARCH-R78`), and an unmet requirement is refused
by naming the capability, never by naming a version (`F3-R21`, `F6-R10`).

This is the companion's problem in a different costume, and it gets the same
answer for the same reason: a plugin written a year ago against a stack it has
never met keeps working for exactly as long as the things it actually uses still
exist, and when it stops working the message says which thing went. A version
number cannot say that, because it conflates "older" with "missing something you
needed".

## Reading a declaration lemonfiber does not recognise

**Unknown names are tolerated when reading an answer and refused when reading an
instruction.** The two rules point in opposite directions, deliberately, and
conflating them opens a hole:

| Reading | Rule | Why |
|---------|------|-----|
| A client reading the capability set a stack **offers** | `ARCH-R81` — MUST treat an unrecognised name as one it does not understand, and MUST NOT refuse the payload for containing it | The stack is describing itself. A newer stack knowing more words is normal, and refusing the whole answer over one of them turns every upgrade into an outage. |
| lemonfiber reading what a plugin **asks for** | `ARCH-R91` — MUST refuse, naming what was not recognised | The plugin is issuing instructions. Ignoring one you do not understand means a plugin's declaration is silently narrower than its behaviour — and since the declaration is the entire basis for saying what a plugin may do, a tolerated unknown is undetected reach. |

`ARCH-R81` reads as a general forward-compatibility principle, and it is one —
for answers. Applied to manifests it would mean a plugin could carry a field
this lemonfiber does not implement, have it skipped, and be installed on the
strength of a declaration that did not describe it.

Refusal is not the same as a parse failure, which is the distinction `F4-R14`
draws. An unrecognised field or value is named, alongside what was available,
and it is reported with every other violation in the same pass — not raised as
the first error a deserialiser happened to reach.

## The published schema

The schema is **generated from the types lemonfiber deserialises**, published
with every release, and never hand-written. This is
[ADR-0014](../../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md)'s
principle applied a second time, and for its stated reason: *a schema that is
written is a claim about the server; a schema that is generated is a description
of it.*

A hand-written plugin schema would be a second description of this contract that
can disagree with the parser, and the disagreement would surface as a plugin
that validates in an author's editor and is refused on an operator's machine.

Publication is what makes authoring ordinary. A JSON Schema published at a
stable location gives completion, inline validation and hover documentation in
any editor that speaks it, in any language, with nothing to install and nothing
to keep in step. It is a better instrument than a library for the same job, and
there is only one of it.

## Validation

Every violation is reported in one pass, each naming its location (`F3-R22`,
`F1-R9`). This includes the faults a strict deserialiser would otherwise raise
one at a time — an unknown field, an unknown enum value, a wrong type — because
a third-party manifest is far likelier to carry several of them than a
first-party one, and fixing a manifest one error per run is a guessing game.

| Rule | Failure |
|------|---------|
| `schema_version` supported | Both versions named |
| Every required field present | Field and its table named |
| No field outside the permitted set | Field named, with the permitted set |
| No unrecognised enum value | Value named, with the values available |
| `plugin.id` not already installed | Both origins named (`F5-R12`) |
| `service.id` collides with no stack or installed-plugin service | Both named |
| `digest` present and well-formed | Service named |
| `bind` present when `port` is | Service named |
| `criticality` is not `critical` | Value named, with the four available |
| `license` present | Plugin named |
| Every `forms` entry names a declared form | Both named |
| Every entry in `requires.capabilities` is offered | Capability named, never a version |

A manifest that fails any of these is refused outright — never partly applied,
never applied on the strength of the parts that did parse (`F3-R2`).

## Compatibility

`schema_version` is a monotonic integer naming the format generation, as it is
for [`stack.toml`](versioning.md). The **supported window is not the same**, and
the difference is the point.

`stack.toml`'s window is the current generation and one predecessor, which buys
a fork's maintainer one release cycle of overlap. That is the right trade for a
fork: one person, actively tracking, who will bump. It is the wrong trade for a
plugin ecosystem, where most authors are not watching and a plugin that was
finished is not abandoned. A two-generation window would quietly delete the long
tail of the catalogue at every second schema bump, and the operator's experience
of that is not "this plugin is old" but "my media server stopped".

So a plugin manifest generation is supported until it is **deprecated by
announcement and then removed**, never merely by being overtaken. In practice
the format is expected to stop moving well before the pressure arrives:
`schema_version` changes in place until the first release candidate
([versioning](versioning.md#before-the-first-release-candidate)), and everything
this version leaves for later is additive by design.

Capability negotiation carries what the window does not. A manifest that still
parses but asks for something that has gone is refused by naming the thing
(`ARCH-R90`) — which is the honest failure, and a different failure from being
unreadable.

## Requirements

| ID | Requirement |
|----|-------------|
| **ARCH-R83** | A plugin MUST be described by a single `plugin.toml` at the root of its source, and lemonfiber MUST act on nothing about a plugin that is not declared there. |
| **ARCH-R84** | A plugin's service MUST be declared in the stack manifest's service vocabulary restricted to the fields this contract permits, and a field outside that set MUST be refused by name rather than ignored. |
| **ARCH-R85** | lemonfiber MUST generate the Compose entry for a plugin's service, and MUST NOT accept a Compose fragment, overlay, patch or merge key from a plugin. |
| **ARCH-R86** | The generated entry MUST extend the same shared template the bundled services extend, and MUST carry no mount other than the single data mount and the service's own configuration directory. |
| **ARCH-R87** | The manifest MUST have no field by which a plugin could express a kernel capability, a device, a network mode, a privileged container, a user override, or an entrypoint or command. |
| **ARCH-R88** | The published address of a plugin's service MUST be assigned by lemonfiber from the declared binding tier, and a plugin MUST NOT be able to declare an address, an interface or a port mapping. |
| **ARCH-R89** | A plugin MUST declare the capabilities it requires of lemonfiber by name, and the manifest MUST NOT carry a minimum lemonfiber version. |
| **ARCH-R90** | An unmet requirement MUST be refused by naming the capability, and MUST NOT be refused by naming a version. |
| **ARCH-R91** | A declaration naming something this lemonfiber does not recognise MUST be refused, naming what was not recognised and what is available, and MUST NOT be ignored, skipped or tolerated. |
| **ARCH-R92** | The plugin manifest schema MUST be generated from the types lemonfiber deserialises, MUST be published with every release, and MUST NOT be hand-written. |
| **ARCH-R93** | Regenerating the published schema MUST produce no diff, and CI MUST fail if it does. |
| **ARCH-R94** | Manifest validation MUST report every violation in one pass, including unrecognised fields, unrecognised values and type faults, each named with its location. |
| **ARCH-R95** | A plugin's image MUST be named by digest, and a manifest naming an image by tag alone MUST be refused. |
| **ARCH-R96** | A plugin's service MUST be placed in a profile of its own, added to the closure of each form the manifest declares, and naming a form the stack does not declare MUST be refused by name. |
| **ARCH-R97** | A plugin MUST NOT declare a criticality of `critical`, and one that does MUST be refused naming the value and those available. |

## Related

- [ADR-0021](../../00-overview/decisions/0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md) — the decision this contract implements
- [stack-manifest](stack-manifest.md) — the vocabulary a plugin's service is declared in, and the whole-stack manifest this is not
- [versioning](versioning.md) — the three version identifiers, and the window this one does not share
- [web-api](web-api.md) — `ARCH-R78`–`ARCH-R82`, the capability negotiation this reuses and the tolerance rule it inverts
- [F3](../../10-functional/features/f-extensibility/f3-stack-manifests.md) — what a plugin is
- [F7](../../10-functional/features/f-extensibility/f7-plugin-provenance.md) — what stays readable once one is installed
