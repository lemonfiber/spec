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
[F4-R1](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R4](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R14](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F3-R17](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R18](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R31](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R33](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R34](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R35](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
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

[plugin]          # identity and provenance
[[service]]       # what runs — one or more
[[claim]]         # a core capability, and the probes that demonstrate it
[[wiring]]        # how the stack's own proxy and dashboard reach one service
[[proof]]         # what must hold before it is installed
[[contribution]]  # a row at a published extension point
[[recipe]]        # the ordered calls that configure what it installed (F8)
[[secret]]        # every value it will hold (F3-R17)
[[override]]      # every bundled thing it will change (F3-R18)
[requires]        # what the plugin needs of lemonfiber
```

`[[secret]]` and `[[override]]` are declared here and, in this version, are
always empty in practice: capturing a value is a recipe, and recipes arrive with
[F8](../../10-functional/features/f-extensibility/f8-recipes.md). They are part
of the format now because `F3-R17` and `F3-R18` fail validation on an
*undeclared* secret or override, and a format with no place to declare one
cannot enforce that.

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

**One or more, and the reason for more is not generality.** A plugin is one
thing an operator installs and one thing they remove, and that thing is often
two containers: a media server and the reader of its watch history, a service
and the sidecar that indexes it. The two differ in exactly the way the format
exists to record — one faces the household on `lan`, the other is an operator
surface with no business being reachable from the sofa; one is `important`,
the other `enhancing` — so a format permitting one forces the author to put both
halves on the wider tier, or to publish two plugins an operator then keeps in
step by hand. Neither is a thing to ask of somebody, and the second is how a
household ends up with an admin page on its network.

What more than one costs is three questions a single service never raised, and
each is answered rather than deferred:

- **Which service a hostname is about.** `[[wiring]]` names it, and is an array
  rather than a table for that reason alone.
- **Which service a proof or a contributed check asks.** Each names it, and must
  where the plugin declares more than one.
- **Which service answers for a capability.** Exactly one may declare a given
  core name — see below.

Service ids are unique within the manifest as well as across the stack, which
was not a rule anything could break while there was one of them. Two services
sharing an id is not a collision with anything installed; it is one name for two
containers, and every rule that reaches for a service *by* that name would reach
one of the two and say nothing about the other.

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
media_types = ["movies", "tv"]
takes_data  = true
provides    = ["media.serve", "plex:direct-play"]
config_path = "/config"
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | Unique within this manifest, across the stack **and** across every installed plugin. A collision is refused, naming both. |
| `name` | string | ✔ | Human-facing |
| `image` | string | ✔ | Registry path, without tag or digest |
| `digest` | string | ✔ | `sha256:…`. What actually runs. |
| `tag` | string | ✔ | The human-readable version the digest corresponds to. Recorded and shown; never resolved. |
| `port` | integer | | Primary UI/API port. Omitted for a service with no listener. |
| `bind` | enum | ✔ if `port` | `loopback` \| `lan`. A **tier**, not an address — see below. |
| `health` | table | | As `stack.toml`. Absent means lifecycle waits on container state only. |
| `criticality` | enum | ✔ | As `stack.toml`. A plugin MUST NOT declare `critical` — see below. |
| `media_types` | array | | Which media types it handles, in `stack.toml`'s vocabulary. Drives root-folder seeding, which is how a plugin's service is pointed at the library the stack already fills. |
| `takes_data` | bool | | `true` if it needs the data root mounted. Default `false`. |
| `provides` | array | | The capabilities this service claims (`F4-R1`). Core names from the published vocabulary; a plugin's own MUST be namespaced (`F4-R4`). At most one service of a plugin may declare a given core name — see below. |
| `config_path` | string | | Where inside the container the one configuration directory is mounted. Default `/config`. |

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

### `config_path` — where its own directory lands, not how many there are

`ARCH-R86` fixes the **mount set**: the single data mount, and the service's own
configuration directory. That is what makes "what can this plugin reach"
answerable from the format. It does not follow that the configuration directory
must land at `/config`, and assuming it did made a whole class of image
uninstallable.

`/config` is a LinuxServer.io convention, not a standard. Of the twenty bundled
services, five keep their configuration somewhere else, and `compose/` says so
for each: Homepage and Seerr at `/app/config`, Caddy at a file under
`/etc/caddy`, Jellyfin and Audiobookshelf needing a second path beside the first.
A plugin whose image is any of those shapes would previously be generated a
container mounting a directory the application never reads — installing
successfully, passing its health probe, and losing everything it had written the
moment the container was replaced.

So the target is data. The source is still lemonfiber's, there is still exactly
one of it, and the number of mounts is unchanged. What is permitted is narrow:

- a single absolute path, and not `/`;
- not `/data` and nothing beneath it, which would be a second mount over the
  library wearing a different name;
- no `..`, and no interpolation.

A second path beside the first — Jellyfin's `/cache`, Audiobookshelf's
`/metadata` — is deliberately **not** offered. One directory is what `ARCH-R86`
permits, and a plugin needing two is one the format should refuse rather than
quietly satisfy.

### `provides` — what it can do, in the vocabulary

`F4-R1` has services declare what they can do as named capabilities so that
wiring can ask for a capability rather than name a service. A plugin's service
declares them here, exactly as a bundled service declares them in `stack.toml`.

A core name comes from the published vocabulary (`F4-R2`) and means the
contracted thing that vocabulary defines; claiming one and failing its probes is
a verification failure and the plugin is not installed (`F4-R6`). A plugin's own
capability MUST be namespaced with the plugin's id — `komga:opds` — and is inert
until something asks for it (`F4-R4`).

The vocabulary is published as
[`capability-vocabulary.json`](capability-vocabulary.md) and is answerable from
the binary, so an author asking what they may claim asks the tool rather than a
document. A core name here with no [`[[claim]]`](#claim--the-probes-a-core-name-is-demonstrated-by)
block binding its probes is refused: `F4`'s whole posture is that *a claim is
demonstrated, not asserted*, and a name in a list asserts.

### One service answers for a core capability, and a plugin's own may be shared

Something asks for a core capability by name and exactly one service answers.
Two services of one plugin declaring `media.serve` is not a choice an operator
could make — they installed one plugin — so there is nothing for them to resolve
and nothing for `F4-R8` to put in front of them. It is two answers to one
question, and it is refused when the manifest is read, naming the capability and
both services.

A plugin's own namespaced capability is not held to this. It is inert: nothing
asks for it and no published contract defines it, so two services both declaring
`plex:direct-play` is two true statements rather than a contest. Refusing it
would be refusing something with no consequence, which is the defect a stand-in
gate is warned against in the other direction.

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
| `[[wiring]]` | The stack manifest's array of [links between its own services](stack-manifest.md#wiring--the-link-between-two-services-and-which-of-them-it-names) — `by`, `asks`, `filled_by`, `to`: who asks whom for what. **Not the [`[[wiring]]`](#wiring--how-the-stacks-own-services-reach-one-service) below**, which is spelled the same and says something else: `hostname`, `dashboard_group` and `service`, naming where lemonfiber puts *this* plugin's service on the proxy and the dashboard. One is a link between two services; the other is one service's own address. Since `ARCH-R127` made the plugin's a list too, the spelling no longer tells them apart and the file it is written in is what does. A plugin declares what it can do in `provides` and is asked for by whatever already asks; it does not get to say what reaches what. In particular it cannot introduce a **by-name** link, which is `F4-R12`'s third clause: a by-name wiring is the operator's exception to make and a plugin naming another service is reaching into wiring it does not own. |
| `host_managed` | Native-mode lifecycle is the operating system's (`B2-R15`). A plugin cannot install a system service. |
| `profile` | Assigned, not declared — see below. |
| `environment` | Arbitrary variables into a container lemonfiber generates. The two things an image is usually told this way are where its data lives and where its library is, and both are declarations here — `config_path` and `media_types` — checked and bounded. A free-form pair is neither, and is how a plugin would configure its way past what the format says it does. |
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

`./config/plex:/config` is the default target. A manifest declaring
`config_path = "/app/data"` gets `./config/plex:/app/data` — the same one
directory, the same source lemonfiber chose, mounted where the image actually
reads it.

That is the whole of it, and the whole of what it can ever be. There is no field
in `plugin.toml` that adds a line to this, which is what makes "what can this
plugin reach" answerable from the format rather than from the instance.

lemonfiber also writes the stack's own wiring for it, from the same declaration
and by the same argument — a plugin that supplies no Compose entry supplies no
proxy stanza and no dashboard entry either, and gets both written for it. For a
`lan` service:

```caddyfile
comics.{$DOMAIN} {
    reverse_proxy plex:32400
}
```

```yaml
- Library:
    - Plex:
        href: http://{{HOMEPAGE_VAR_LAN_HOST}}:32400
        description: Plays your library on TVs, phones and browsers
```

A `loopback` service gets no proxy stanza — that is the bundled policy holding
rather than a limitation of the format. **It still gets a dashboard entry**, with
its `href` rendered from the tier rather than from the LAN host: the bundled
stack puts nine of them on Homepage today, Prowlarr and NZBHydra2 among them, and
a plugin's service is on the same terms as a bundled one in the same tier.

The tier decides the route and nothing else. Refusing the whole wiring for a
loopback service would refuse something lemonfiber accepts, which is why
`a_loopback_service_may_be_given_a_dashboard_group` passes and why the refusal
that does exist is narrower than this paragraph once said: a `loopback` service
given a `wiring.hostname` is refused, naming the service and the tier.

`defaults` rather than `rootless`: the `PUID`/`PGID` pair is a LinuxServer.io
convention, and setting it on an image that ignores it is a silent no-op that
reads like a security control. Which template a plugin's service extends follows
from whether it declares it honours the pair, the same question the bundled
stack answers per service.

The `${DATA_ROOT}:/data` mount appears only where `takes_data` is `true`, and
when it appears it is the **single** data mount — [ADR-0006](../../00-overview/decisions/0006-single-data-mount.md)'s
rule holds for a plugin by construction rather than by review, because there is
no second mount to declare.

## `[[claim]]` — the probes a core name is demonstrated by

```toml
[[claim]]
capability = "media.serve"

[[claim.probe]]
id      = "guarded"
request = { method = "GET", path = "/api/v1/series" }
expect  = { status = 401 }
fixture = "fixtures/media-serve-guarded.json"

[[claim.probe]]
id      = "catalogue"
request = { method = "GET", path = "/api/v1/series" }
expect  = { status = 200, json_has_keys = ["content", "totalElements"] }
fixture = "fixtures/media-serve-catalogue.json"
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `capability` | string | ✔ | A core name, which MUST also appear in the service's `provides` |
| `probe[].id` | string | ✔ | Names a probe the capability declares. Every one of them, exactly once. |
| `probe[].request` | table | ✔ | `method`, `path`, and optionally `accept` — on this plugin's own service. See [what a request may ask for](#what-a-request-may-ask-for). |
| `probe[].expect` | table | ✔ | What the answer must be. Within what the probe permits — see below. |
| `probe[].fixture` | string | ✔ | The recorded response. Required here where it is optional on a proof: a claim nobody can demonstrate without owning the service is a claim the catalogue's CI cannot check (`F5-R2`). |

**The vocabulary owns what must be shown; this owns where to ask.** A capability
is one contract with many claimants, each answering at a path of its own, so the
published probe declares the question, the statuses that answer it, and whether a
credential is needed — and the binding declares the method, the path and the
recorded response. A binding that leaves a probe unbound, names one the
capability does not declare, or carries an expectation weaker than the probe
requires is refused naming the probe (`ARCH-R109`).

`provides` and this are a declaration and its evidence rather than two lists. A
core name in `provides` with no claim is refused; a claim whose capability is not
in `provides` is refused; both name the other half.

A namespaced capability gets no claim block and cannot have one. There is no
published contract for it to satisfy — that is what *inert* means — and the
plugin's own `[[proof]]` entries are where it says what it can nevertheless
demonstrate.

## `[[wiring]]` — how the stack's own services reach one service

```toml
[[wiring]]
hostname = "comics"
dashboard_group = "Library"
```

Three fields, and none of them names a service outside this plugin. The stack
manifest's
[`[[wiring]]`](stack-manifest.md#wiring--the-link-between-two-services-and-which-of-them-it-names)
is the other kind and is an array of links between the stack's own services;
this one is a plugin saying where its *own* entry goes, and lemonfiber writes
both the route and the panel from it.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `service` | string | ✔ where the plugin declares more than one service | Which of this plugin's services this is about. Default: the only one. |
| `hostname` | string | | The label in front of the operator's domain. A single DNS label — not a name, an address or a port. Default: the service's `id`. |
| `dashboard_group` | string | | Which group on the bundled dashboard it appears under. Default: the group the stack uses for its tier. |

**An array, and one entry per service at most.** A hostname is a fact about one
container rather than about a plugin, which only became visible once a plugin
could declare two: a default taken from the plugin's own id would have given two
services one address. A second wiring for the same service is refused naming the
service — it has one address and one panel.

A plugin that is installed and then has to be wired by hand is one the operator
has to do the work lemonfiber exists to do. The bundled stack puts a household
service behind Caddy and on Homepage; a plugin's service gets the same, written
by lemonfiber from what the manifest already declares — the id and port to reach
it on, the tier that decides whether it is reachable at all, and the description
that goes beside it.

**The tier governs, not the plugin.** Only `lan` services are proxied, because
the bundled policy is that an admin surface does not get a hostname — every
admin stanza in the shipped `Caddyfile` is commented out with what you would be
accepting written next to it. A `loopback` service gets no route, and there is
no field by which it can ask for one: a wiring giving one a `hostname` is
refused, naming the service and the tier that decides it. That is the same reasoning as `ARCH-R88`: a
plugin that could publish its own address could put an admin surface on the
household network without touching anything `C6` inspects.

**A link, not a widget.** The dashboard entry is an icon, a link and the
description the manifest already carries. A widget reads a service's API with a
credential, which means an adapter and a captured value — a recipe, arriving
with `F8`. A plugin gets the panel that needs nothing and waits for the one that
needs something.

### What a request may ask for

A request is `method`, `path`, and — where the service needs asking — `accept`.

```toml
request = { method = "GET", path = "/identity", accept = "application/json" }
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `method` | string | ✔ | |
| `path` | string | ✔ | On the service being asked. |
| `accept` | string | | One media type, sent as the request's `Accept` header. |

**Why there is a field at all.** A service that answers XML unless a caller asks
for JSON cannot satisfy a capability whose probe requires a JSON assertion, and
before this there was nowhere to ask. Measured against
`plexinc/pms-docker@sha256:e0ab2739…`, the same path in the same second:

```
GET /identity                          GET /identity  (Accept: application/json)
Content-Type: text/xml;charset=utf-8   Content-Type: application/json
<MediaContainer size="0" …/>           {"MediaContainer":{"size":0, …}}
```

**Why it is one field and not a header map, which is the part worth reading
twice.** A probe declares who it is asked as, and `credential = "none"` on every
`guarded` probe has meant what it says partly because a manifest could present
nothing. A map of headers would turn that into a convention somebody has to
enforce, and it could not be enforced: a service may name its credential header
whatever it likes — `X-Plex-Token`, `X-Api-Key`, something nobody has seen — so
no list of refused names is ever closed. One named field keeps it a property of
the format instead. **A probe still cannot present a credential, because there
is nowhere to write one.**

A recipe's `[[recipe.step]].call` does carry a `headers` table, and the
asymmetry is deliberate rather than an oversight. A recipe runs with lemonfiber's
own authority, exists in order to carry a captured value to a destination, and
every flow it could produce is declared as a `[[recipe.pair]]` and checked before
a call is made. A probe has no such analysis and gates an install.

`accept` is **one** media type: `type/subtype`, optionally followed by
`; name=value` parameters. A list is refused — which representation came back
would then be the service's choice, and a recording is of one answer. A wildcard
is refused — it asks for nothing in particular, which is what a request with no
`accept` already says and says more plainly. What a media type may carry is
letters, digits and ``!#$%&'+-.^_`|~``; anything that would have to be quoted on
the wire is refused, because a value needing quoting is one a reviewer cannot
read as what arrives.

## `[[proof]]` — what must hold before it is installed

```toml
[[proof]]
id      = "plex.serves"
title   = "Plex answers on its declared health path"
request = { method = "GET", path = "/identity" }
expect  = { status = 200, json_has_keys = ["MediaContainer"] }
fixture = "fixtures/identity.json"
why     = "The path the health probe asks for is one this image serves."
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | Unique within the plugin. What a verdict is reported against. |
| `title` | string | ✔ | What it establishes, in one line |
| `request` | table | ✔ | `method` and `path`. The same shape a `health` probe takes. |
| `expect` | table | ✔ | What the answer must be. A status alone is not sufficient — see below. |
| `fixture` | string | | A recorded response to run against where no instance exists (`F10-R4`) |
| `service` | string | ✔ where the plugin declares more than one service | Which of this plugin's services is asked. Default: the only one. |
| `why` | string | ✔ | Why this is worth asserting. A proof nobody can justify is one nobody will maintain. |

`F3-R1` has named a plugin's proofs among what its manifest declares since the
feature was written, and `F3-R3` runs them in the existing verification engine.
There was no block to declare them in, which left an author two bad options:
carry them in a second file the installer never reads, or leave `F3-R4` — *a
plugin whose proofs do not pass is not installed* — with nothing to evaluate.

**`expect` must constrain the body.** A status is a claim about the network
path, not about the service: Docker publishes a port by putting a proxy in front
of it, and that proxy accepts a connection before knowing whether anything
inside is listening. A manifest whose every proof asserts only a status is
refused, naming the proofs, because it has declared nothing a replaced container
would fail.

### What an expectation may say

One vocabulary, read in three places — a `[[proof]]`, a `[[claim.probe]]` and a
contributed check — because all three ask a service a question and judge the
answer, and three vocabularies for one job would be three things to keep in step.

| Key | Type | What it asserts |
|-----|------|-----------------|
| `status` | integer | The response status. Not sufficient alone, except for a refusal — see above. |
| `json` | table | Places the body must carry, each with the exact value it must hold. A value is a boolean, a whole number or a string; nothing nested, because a shape deeper than that is asking about a document rather than about a claim — and where the thing worth asserting is deeper *in* the answer, the key reaches it rather than the value growing to match. |
| `json_has_keys` | array | Places the body must carry, whatever they hold |
| `json_types` | table | Places the body must carry, each with the kind of value it must be: `bool`, `int`, `str`, `list` or `dict` |
| `json_at_least` | table | Places the body must carry, each with a number it must not be below. *At least one series*, rather than *a catalogue exists*. |
| `json_array_min` | integer | The body read as a JSON **array**, with at least this many entries. A catalogue is very often a list rather than an object, and none of the key-wise constraints can say anything about one. |
| `json_is_absent` | boolean | **The body did not parse as JSON at all.** How a proof says *this answered with an application shell, not an object* — which is what a client-routed service answers for every path it does not implement, and the reason a status proves nothing against one. |
| `content_type` | string | A substring of the content type the answer was served as |
| `body_starts_with` | string | What the body must begin with, where it is not JSON |

The set is closed. A key outside it is refused by name rather than ignored, for
`ARCH-R91`'s reason pointed at an expectation: an assertion nothing evaluates is
a proof that silently checks less than it says, which is worse than one that
fails.

`json_is_absent` is the one worth reading twice, because its name invites the
other reading — *these keys are absent* — and the two are not close. It says
nothing about keys. It says the answer was not JSON.

#### Where an expectation looks

The four key-wise constraints above take a **place** rather than a name. The
other five are about the answer as a whole and take none.

A key that does not begin with `/` is the name of a top-level member, which is
what every key written before this generation is and is why none of them changed
meaning. A key that does begin with `/` is a
[JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901), with one extension this
contract defines.

| Key | Reaches |
|-----|---------|
| `content` | the top-level member `content` |
| `/MediaContainer/machineIdentifier` | `machineIdentifier` inside `MediaContainer` |
| `/MediaContainer/Setting/[id=PublishServerOnPlexOnlineKey]/value` | the entry of the `Setting` list whose `id` holds that word, then its `value` |
| `/MediaContainer/Directory/[type=movie]/Location/[path=~1data~1media~1movies]/path` | the film library's location under the stack's data root |
| `/a~1b` | the top-level member literally called `a/b` (RFC 6901's escapes: `~1` is `/`, `~0` is `~`) |

**Standard, and ours.** Everything but the third row is RFC 6901 unchanged. The
third is the extension, and it is one step and one comparison: a reference token
written `[field=value]` means *the entry of this list whose `field` holds
`value`*, exactly one entry must, and there are no operators, no wildcards, no
nesting and no indices.

An index would be the trap the selector exists to avoid. Plex answers a hundred
and fifty-one settings at `/:/prefs` and the order of them is not a promise
anybody made, so *the ninety-first* is the wrong answer one release later, in a
way that keeps passing.

**A selector's value is escaped like any other reference token**, which the fourth
row is there to show and which the common case needs: a filesystem path is full
of slashes, and a slash in a token is written `~1`. Unescaped,
`[path=/data/media/movies]` is four steps rather than one, and is refused by
name rather than resolved somewhere nobody meant.

Its cost is stated rather than hidden. `[` and `]` belong to the selector, so a
reference token carrying either is refused rather than read as a member name — a
member actually called `[a=b]` is unreachable through a pointer. That is the
price of the extension; it also closes the mistake anybody would actually make,
which is writing `…/Setting[id=X]/value` and being told nothing while it looks
for a member with brackets in its name.

**Why a name was not enough.** A flat name says everything there is to say about
a flat answer, and the two plugins published before this one both have flat
answers. A service that nests its payload — Plex puts every response one level
down under `MediaContainer` — could only be asserted about at the envelope, so
`json_has_keys = ["MediaContainer"]` was the strongest claim available and it
says that the service replied. A probe that passes by observing that something
replied is worse than one that fails, because a port proxy replies.

A key naming no place is **refused when the manifest is read**, naming the key
and what is wrong with it. It is not evaluated as a missing member: an assertion
nothing can evaluate is one that silently checks less than it says, which is
`ARCH-R91` pointed at an expectation.

`[[recipe.step]].capture.from` is a different dialect — `json.token`, a dotted
path — and is deliberately left alone here. Nothing resolves it yet, because
nothing runs a recipe; it is aligned with this by
[F8](../../10-functional/features/f-extensibility/f8-recipes.md), in the change
that makes it run.

Three verdicts, never two (`F3-R5`, `F4-R7`): passed, failed, and could not be
run. The third is reported as unproven and is never counted as the first.

### What a recording is

A `fixture` names a file beside the manifest holding **one response somebody
recorded from the image this manifest pins**. It is what lets a claim be shown
where no instance exists — an author's laptop, the catalogue's CI, a reviewer's
checkout — and it is ordinary reviewable data rather than a cassette a tool
wrote and only that tool reads (`F10-R4`, `F10-R5`).

```json
{
  "recorded_from": "ghcr.io/example/thing@sha256:6c2a967…",
  "note": "An unauthenticated read of the catalogue. A refusal is the pass: a library server on the household network that answered this would be publishing somebody's collection to every device on it.",
  "request":  { "method": "GET", "path": "/api/v1/series" },
  "response": {
    "status": 401,
    "headers": { "content-type": "application/json" },
    "json": { "status": 401, "error": "Unauthorized" }
  }
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `recorded_from` | string | ✔ | The image this answer came out of, as `image@sha256:…` |
| `note` | string | ✔ | Why this is the answer worth recording — the half a diff cannot show |
| `request.method` | string | ✔ | What was asked |
| `request.path` | string | ✔ | Where it was asked |
| `request.accept` | string | | What representation it asked for, where it asked for one |
| `response.status` | integer | ✔ | |
| `response.headers` | table | | The headers an expectation may constrain; `content-type` is the one in use |
| `response.json` | any | | The body as it parsed, or `null` where it did not parse as JSON |
| `response.body_starts_with` | string | | The beginning of a body that is not JSON |

**It names the image by digest, and that digest is the manifest's own pin.** A
recording taken from some other build is a claim about software nobody is
installing, and the drift is silent: it passes, and the service it describes is
not the service that will run. Moving the pin means re-recording in the same
change, and a recording naming a different image is refused rather than trusted.

**What was asked for is part of which call a recording is of.** A service that
negotiates answers two different things at one path, so a recording that did not
say which it asked for would be evidence for whichever question somebody later
pointed at it. A recording taken plainly is not evidence for a request that
names an `accept`, and one that named an `accept` is not evidence for a request
that does not.

**A recording that is absent, unreadable, or records a request the assertion
does not ask is unproven** — never a pass and never a failure. Nothing about the
service has been established either way, and reporting it as a failure would say
the service is broken when the recording is. It is the third verdict's plainest
case, and the one an author meets most often.

## `[[contribution]]` — a row in a register lemonfiber already runs

```toml
[[contribution]]
at        = "doctor.check"
id        = "komga:claimed"
title     = "Komga has an administrator, so nobody else can become one"
category  = "services"
request   = { method = "GET", path = "/api/v1/claim" }
expect    = { status = 200, json = { isClaimed = true } }
fixture   = "fixtures/api-v1-claim-claimed.json"
timeout_s = 10
why       = "An unclaimed Komga hands administrator to whoever asks first."

[[contribution]]
at     = "doctor.remedy"
id     = "komga:claim-it"
for    = "komga:claimed"
action = "Open Komga and create the administrator account"
why    = "Until somebody does, the first caller on the household network becomes it."
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `at` | string | ✔ | A point [`extension-points.json`](extension-points.md) publishes. One this build does not is refused by name, with the ones that exist. |
| `id` | string | ✔ | `<plugin-id>:<name>`. Namespaced, always (`F4-R16`). |
| … | | | Everything else is the row that point declares, and nothing else |

The fields are not enumerated here, and deliberately: the row belongs to the
point and the point is published, so restating it would be a second description
of a format that already has one — `F10-R2`'s objection, one level down. What is
fixed here is that a contribution is declared **in this block and nowhere else**,
and that it carries exactly the row its point declares.

What that buys is the property `F3-R26` is written for: nothing new evaluates a
contribution. The doctor already runs checks independently, bounds each one,
keeps `unverified` distinct from `pass`, and carries a remedy on anything that
does not pass. A contributed check is another row in that register, run on
exactly those terms and attributed to its plugin wherever it appears.

Every check carries at least one remedy (`F3-R34`). A check that can say
something is wrong and nothing about what to do has moved the work to the
operator rather than done it, and `C1-R2` has no exemption for a contributed
finding.

The row's `service` field is what a check names where the plugin declares more
than one, and it is required there: *the plugin's own service* is the default
and has no referent once there are two. A remedy asks nothing and names nothing.

**Contributing is a capability a manifest asks for by name.** Each published
point names the one a contribution there requires
([extension-points](extension-points.md#a-point-names-the-capability-it-is-taken-at)),
and a manifest carrying a contribution without asking for it is refused by naming
that capability — the same rule `recipe.run` gets below, and for the same reason:
a build that read a row it could not run and dropped it would install a plugin
whose declared behaviour is wider than its actual one.

## `[[recipe]]` — declarable before it is runnable

```toml
[[recipe]]
id    = "adopt-existing-library"
title = "Point it at the comics the stack already files"
why   = "…"

[[recipe.step]]
id      = "sign-in"
call    = { method = "POST", to = "komga", path = "/api/v1/login" }
expect  = { status = 200 }
capture = [{ name = "token", from = "json.token", origin = "stack-service" }]

[[recipe.step]]
id      = "create"
call    = { method  = "POST", to = "komga", path = "/api/v1/libraries",
            headers = { Authorization = "Bearer {{token}}" } }
expect  = { status = 200 }

[[recipe.pair]]
value = "token"
to    = "komga"
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `step[].call.method` | string | ✔ | |
| `step[].call.to` | string | ✔ | A service id in this stack, or a DNS name outside it. Never an address, a range or a bare host port (`F8-R8`). |
| `step[].call.path` | string | ✔ | |
| `step[].call.headers` | table | | Headers the call carries. A value may substitute an earlier capture. |
| `step[].call.body` | string | | The body the call carries. A value may substitute an earlier capture. |

**A call needs somewhere to put what an earlier step captured**, and `headers`
and `body` are it. Without them a recipe can name a destination and capture a
value and has no way to carry one to the other — which is every first-run flow
this feature exists for, since creating an account and reading back a token is
worth nothing if the token cannot then be presented.

They are also what makes the pair check bite. Every `{{capture}}` in a call is a
flow from that value to that call's destination, so the set of flows a recipe
could produce is computable by reading it — and a flow with no
`[[recipe.pair]]` behind it fails validation before a call is made
([ADR-0022](../../00-overview/decisions/0022-a-recipe-declares-pairs-not-lists.md)).
A `call` with nowhere to substitute into would make that analysis a check over an
empty set.

[F8](../../10-functional/features/f-extensibility/f8-recipes.md) governs what the
calls may do; this says where they are written. A step names a method, an
in-stack service or an external DNS name, and a path; it may capture values out
of a response, substitute earlier captures into a later call, branch on a status
or a captured value, and wait a bounded number of times. Every value it could
carry to every destination it could reach is declared as a `[[recipe.pair]]`, and
a flow with no pair behind it fails validation before a call is made.

**Nothing runs one yet, and the manifest says so rather than implying it.**
Running a recipe is a capability a manifest asks for by name:

```toml
[requires]
capabilities = ["service.add", "service.health.http", "recipe.run"]
```

A lemonfiber that does not offer `recipe.run` refuses such a manifest **by naming
that capability** (`F3-R21`, `ARCH-R90`), which is the honest failure. The
alternative — parsing the block and skipping it — would install a plugin whose
declared behaviour is wider than its actual one, and that is the tolerated
unknown `ARCH-R91` exists to refuse.

The block is in the format before its engine is for the same reason `[[secret]]`
and `[[override]]` are: a rule that cannot be stated for want of a field is not
being enforced, and adding the field later would make every manifest written
against this version wrong.

## `[[secret]]` and `[[override]]` — declared before they are held

```toml
[[secret]]
id   = "api-key"
of   = "komga"
why  = "Read the library counts the dashboard panel shows"

[[override]]
id   = "homepage.services"
why  = "Add its own entry to the bundled dashboard"
```

`F3-R17` fails validation on a secret captured but not declared, and `F3-R18` on
a bundled thing changed but not declared. Both need somewhere to declare one.

**What counts as capturing, and what counts as changing.** A recipe is
declarable before it is runnable and its block is where both verbs are written,
so both rules are decided by reading the manifest rather than by watching one
run:

| Declared | Held to |
|----------|---------|
| `[[secret]]` | every `[[recipe.step]].capture` |
| `[[override]]` | every `[[recipe.step]].call` whose method is not one that only asks and whose `to` is a service the stack ships |

A secret is matched on the captured value's **name** and nothing else. `of` and
a capture's `origin` both answer *whose*, and they answer it in different
vocabularies — one names a service, the other a kind of source — so holding them
to each other would be inventing a correspondence this contract does not state,
and refusing manifests for not keeping it. What both do name is the value. A
capture whose name no `[[secret]]` carries is refused, naming the value and its
origin.

Every captured value, rather than the ones that look like credentials. There is
no field saying which is which and there should not be: a library id read back
from a first-run flow is a value the plugin now holds and can carry somewhere,
and a format in which the author decides what is worth declaring is one where
the interesting cases are the ones nobody declared.

An override names an owner and what of theirs, and the **owner** is the half a
call can be held to by reading, because a path is a route on a service rather
than the name of a setting. Three destinations, and only one of them is this: a
call to one of the plugin's own services changes what the plugin installed and
is what a recipe is for; a call to a DNS name outside the stack leaves the
machine and is declared as a host rather than as an override; a call to a
service the stack ships is refused, naming the call and the service, unless an
`[[override]]` names that owner. The verbs that change are written as the
complement of the ones that only ask, so a verb added to what a call may use is
a change its author has to declare rather than one nobody is told about.

So both blocks are absent from a manifest declaring no recipe, and are filled in
one that declares a recipe which captures or changes anything. An earlier
reading of this section — that both are in practice always absent until `F8`
arrives in `0.18.0` — held only while a recipe could not be written down at all.
They are in the format for the reason they always were: a rule that cannot be
stated for want of a field is not being enforced, and adding the field later
would make every manifest written against this version wrong.

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
| `service.id` collides with no other service in this manifest, the stack, or an installed plugin | Both named |
| `service.port` is not a port the stack already publishes | Port and both services named |
| `wiring.hostname` is not a name the stack's own proxy is written to answer on | Name given |
| At most one service declares a given core capability | Capability and both services named |
| `digest` present and well-formed | Service named |
| `bind` present when `port` is | Service named |
| `criticality` is not `critical` | Value named, with the four available |
| `license` present | Plugin named |
| Every `forms` entry names a declared form | Both named |
| Every entry in `requires.capabilities` is offered | Capability named, never a version |
| `config_path` is one absolute path, not `/`, and outside the data root | Path named, with what is permitted |
| Every `provides` entry is a published core name or namespaced with the plugin's id | Capability named, with the namespace required |
| Every `[[proof]]` carries `id`, `title`, `request`, `expect` and `why` | Proof and field named |
| At least one `[[proof]]` constrains the body rather than only the status | Every status-only proof named |
| `wiring.hostname` is a single DNS label | Value named |
| A `loopback` service declares no `wiring.hostname` | Service named, and the tier that governs |
| Every `[[wiring]]`, `[[proof]]` and contributed check names a declared service, and names one where the plugin declares more than one | Name given, with the services declared |
| No service is wired twice | Service named |
| `request.accept` is one media type, not a list and not a wildcard | Value named, with what is permitted |
| Every expectation key names a place an answer could hold | Key named, with what is wrong with it |
| Every secret captured is one `[[secret]]` declared (`F3-R17`) | Value and its origin named |
| Every bundled thing changed is one `[[override]]` declared (`F3-R18`) | Setting and its owner named |
| Every core name in `provides` has a `[[claim]]`, and every `[[claim]]` a name in `provides` | Both halves named |
| Every probe a claimed capability declares is bound, and no other | Probe named, with the ones it declares |
| Every binding's status and body constraint are within what its probe permits | Probe named, with what it requires |
| Every `[[contribution]].at` names a published extension point | Point named, with those that exist |
| Every contributed identity is namespaced, and none is one the point records as bundled | Both named |
| Every `doctor.check` carries a `doctor.remedy` naming it | Check named |
| A `[[recipe]]` is declared and `requires.capabilities` does not name `recipe.run` | Capability named, never a version |

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
| **ARCH-R100** | A plugin's service MUST be able to name the path inside its container at which its one configuration directory is mounted; that path MUST be validated as a single absolute path that is neither the root nor within the data root, and naming it MUST NOT change the number of mounts the generated entry carries. |
| **ARCH-R101** | The manifest MUST have no field by which a plugin could set an environment variable on the container lemonfiber generates for it. |
| **ARCH-R102** | A plugin's service MUST declare the capabilities it claims in the manifest, a claim outside the published core vocabulary MUST be namespaced with the plugin's id, and a claim naming neither MUST be refused by name. |
| **ARCH-R103** | lemonfiber MUST generate the stack's own proxy and dashboard wiring for a plugin's service from what the manifest declares, on the same terms as a bundled service in the same binding tier, and MUST NOT accept a proxy stanza, dashboard entry or any other wiring fragment from a plugin. |
| **ARCH-R104** | A plugin MUST NOT be able to obtain a proxy hostname for a service bound to loopback, and the binding tier alone MUST decide whether a service is reachable by name. |
| **ARCH-R105** | A plugin's proofs MUST be declarable in the manifest, each naming what it asks and what the answer must be, and a manifest whose every proof constrains only a response status MUST be refused naming those proofs. |
| **ARCH-R116** | A core capability MUST be claimed by a `[[claim]]` block binding every probe the published vocabulary declares for it, the claimed name MUST also appear in the service's `provides`, and either half without the other MUST be refused naming both. |
| **ARCH-R117** | A recipe MUST be declarable in the manifest, and a manifest declaring one MUST name the capability that runs it in `[requires]`; a build not offering that capability MUST refuse the manifest by naming it rather than by parsing the block and skipping it. |
| **ARCH-R120** | A recorded response MUST be one file of readable data carrying the request it recorded and the answer to it, and a field outside the published set MUST be refused by name rather than ignored. |
| **ARCH-R121** | A recording MUST name the image it was taken from by digest, that digest MUST be the one the manifest pins for the service being asked, and a recording naming another image MUST be refused rather than run against. |
| **ARCH-R122** | An assertion whose recording is absent, unreadable, or records a request the assertion does not ask MUST be reported unproven, naming the recording, and MUST NOT be reported as passed or as failed. |
| **ARCH-R123** | A request in a manifest MUST be able to name the one representation it asks for, that field MUST hold a single media type and MUST be refused by name where it holds a list, a wildcard or anything else, and the manifest MUST have no field by which a request outside a recipe could carry a credential or any other header. |
| **ARCH-R124** | A recording MUST record the representation its request asked for, and the representation asked for MUST be part of whether a recording is of the request an assertion asks. |
| **ARCH-R125** | An expectation's key-wise constraint MUST take a place in the answer rather than a top-level name, written as a JSON Pointer (RFC 6901) extended with a single-entry list selector this contract defines, a key that does not begin with `/` MUST keep meaning the top-level member of that name, and a key naming no place MUST be refused by name rather than evaluated as a member that is absent. |
| **ARCH-R126** | A plugin MAY declare more than one service; every service id MUST be unique within the manifest, and at most one of a plugin's services MUST declare a given core capability, refused naming the capability and both services. |
| **ARCH-R127** | Wiring MUST be declared per service, a manifest declaring more than one service MUST name the service each wiring is about, and a service MUST NOT carry two. |
| **ARCH-R128** | A proof and a contributed check MUST name which of the plugin's services they ask where the plugin declares more than one, and one that does not MUST be refused by name rather than resolved to whichever service is read first. |

## Related

- [ADR-0021](../../00-overview/decisions/0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md) — the decision this contract implements
- [stack-manifest](stack-manifest.md) — the vocabulary a plugin's service is declared in, and the whole-stack manifest this is not
- [capability-vocabulary](capability-vocabulary.md) — the names `provides` may carry and the probes a `[[claim]]` binds
- [extension-points](extension-points.md) — the points a `[[contribution]]` is made at and the row each one takes
- [versioning](versioning.md) — the three version identifiers, and the window this one does not share
- [web-api](web-api.md) — `ARCH-R78`–`ARCH-R82`, the capability negotiation this reuses and the tolerance rule it inverts
- [F3](../../10-functional/features/f-extensibility/f3-stack-manifests.md) — what a plugin is
- [F7](../../10-functional/features/f-extensibility/f7-plugin-provenance.md) — what stays readable once one is installed
