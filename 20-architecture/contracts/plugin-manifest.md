# Contract: `plugin.toml`

**Status:** Accepted

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
[F1-R9](../../10-functional/features/f-extensibility/f1-customisation.md),
[F10-R12](../../10-functional/features/f-extensibility/f10-authoring.md)

---

## Why this file exists

[ADR-0021](../../00-overview/decisions/0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md)
decided that a plugin is declarative data and that lemonfiber writes its Compose
entry rather than accepting one. This says what that data is.
[ADR-0043](../../00-overview/decisions/0043-the-core-writes-every-compose-entry-from-one-typed-service-model.md)
made that data the one model every Compose entry is written from, the stack's own
services included.

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
[[ask]]           # a core capability one of its services asks for
[[wiring]]        # how the stack's own proxy and dashboard reach one service
[[proof]]         # what must hold before it is installed
[[contribution]]  # a row at a published extension point
[[recipe]]        # the ordered calls that configure what it installed (F8)
[[secret]]        # every value it will hold (F3-R17)
[[override]]      # every bundled thing it will change (F3-R18)
[requires]        # what the plugin needs of lemonfiber
```

`[[secret]]` and `[[override]]` are filled in by a manifest whose recipes capture
or change anything ([F8](../../10-functional/features/f-extensibility/f8-recipes.md)),
and are absent otherwise. `F3-R17` and `F3-R18` fail validation on an
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
| `forms` | array | ✔ | Which forms the service joins. Every entry MUST name a form the stack declares (`ARCH-R96`). The core refuses an empty list and compares no entry with the stack's forms. |

`description` and `without_it` are required of a plugin for the same reason they
are required of a bundled service: the catalogue exists to convert an inventory
into a judgement about severity, and a plugin that appears in `lemonfiber ps`
without them puts a name in front of an operator and nothing else.

**The licence is declared but not constrained.** Every bundled service is
OSI-licensed, bar the images lemonfiber builds from its own code, which carry
lemonfiber's own licence, and `F2-R5` fails validation on anything else, because
the bundled set is a curated list this project stands behind. A plugin is not:
the operator chose it. Refusing to install proprietary software on somebody's
own machine would be `F1`'s objection exactly — the tool standing between an operator and
their stack. So the licence is **recorded and shown**, including on the
`lemonfiber plugins` read (`F7-R5`), and the operator decides. A plugin whose
licence is absent is refused; one whose licence is merely not open is installed
and said so.

**There is deliberately no `min_lemonfiber_version`.** `stack.toml` has one, and
a plugin has none on purpose: `F3-R21` requires an unmet requirement to be
refused by naming the capability rather than a version. See
[`[requires]`](#requires--what-the-plugin-needs-of-lemonfiber).

## `[[service]]` — what runs

Declared in the one service model every Compose entry is written from
([ADR-0043](../../00-overview/decisions/0043-the-core-writes-every-compose-entry-from-one-typed-service-model.md)).
A first-party plugin, a third-party plugin and [`stack.toml`](stack-manifest.md#service)
declare a service in the same fields, with the same types and the same validation, and
whether a plugin is first-party decides whether it may be installed and which
credentials reach it, never what it may say (`ARCH-R225`). The set of fields *is* the
set of things a service may ask for of the machine, which is the substance of ADR-0021:
it is wider than one shape, and still closed and typed.

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
shape       = "render"
memory_mib  = 600

[[service.mount]]
from = "transcode"
to   = "/transcode"

[service.env]
PLEX_CLAIM = { setting = "plex:claim-token", default = "" }
```

A service that has no network of its own, with a memory ceiling:

```toml
[[service]]
id            = "transmission"
name          = "Transmission"
image         = "lscr.io/linuxserver/transmission"
digest        = "sha256:0d2a7c9be1a3f4e6c8b5d7f9e1a3c5b7d9f1e3a5c7b9d1f3e5a7c9b1d3f5e7a9"
tag           = "4.0.6"
port          = 9091
bind          = "loopback"
criticality   = "core"
takes_data    = true
user_mode     = "puid-env"
mem_limit_mib = 512
network       = { via = "network.egress-guard" }

[service.env]
TRANSMISSION_WEB_HOME = "/usr/share/transmission/public_html"
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | Unique within this manifest, across the stack **and** across every installed plugin. A collision is refused, naming both. |
| `name` | string | ✔ | Human-facing |
| `image` | string | ✔ | Registry path, without tag or digest |
| `digest` | string | ✔ | `sha256:…`. What actually runs. |
| `tag` | string | ✔ | The human-readable version the digest corresponds to. Recorded and shown; never resolved. |
| `port` | integer | | The port it is published at on the host: its primary UI/API port. Omitted for a service that publishes nothing. |
| `bind` | enum | ✔ if `port` | `loopback` \| `lan`. A **tier**, not an address, and every port the service publishes is published on it — see [ports](#ports--the-tier-is-lemonfibers-the-numbers-are-the-manifests). |
| `publish` | array of tables | | Each further port it publishes on its tier: `port`, on the host (✔), and `listens`, inside the container (default `port`). Only where `port` is declared. |
| `health` | table | | As `stack.toml`. Absent means lifecycle waits on container state only. |
| `criticality` | enum | ✔ | As `stack.toml`. A plugin MUST NOT declare `critical` — see below. |
| `media_types` | array | | Which media types it handles, in `stack.toml`'s vocabulary. Drives root-folder seeding, which is how a plugin's service is pointed at the library the stack already fills. |
| `takes_data` | bool | | `true` if it needs the data root mounted at `/data`, from the operator's [storage setting](#the-data-root--one-setting-every-data-mount). Default `false`. |
| `provides` | array | | The capabilities this service claims (`F4-R1`). Core names from the published vocabulary; a plugin's own MUST be namespaced (`F4-R4`). At most one service of a plugin may declare a given core name — see below. |
| `config_path` | string | | Where inside the container its configuration directory is mounted. Default `/config`. |
| `config_ro` | bool | | `true` to mount the configuration directory read-only. Default `false`. |
| `mount` | array of tables | | Each further path mounted from inside its own configuration directory: `from` (✔), `to` (✔) and `ro` (default `false`) — see [mounts](#mounts--inside-its-own-directory-and-nowhere-else). |
| `tmpfs` | array | | Absolute paths given scratch space in memory, empty whenever the container starts. |
| `env` | table | | Its environment: a variable's name to one of four typed kinds of value — see [environment](#environment--four-kinds-of-value). |
| `user_mode` | enum | | `image` \| `puid-env` \| `uid`. Who the container runs as. Default `image`, and `uid` where the service speaks a contract or is `confined` — see [who it runs as](#who-it-runs-as-and-how-tightly-it-is-held). |
| `posture` | enum | | `standard` \| `confined`. How tightly the container is held, as declared. Default `standard`. `confined` only where the plugin's own CI runs the image under it. |
| `memory_mib` | integer | | The memory it expects to need, in MiB. An estimate, summed into a form's footprint (`B1-R18`) and never written as a limit. |
| `mem_limit_mib` | integer | | The most memory the container may hold, in MiB, written as its limit. |
| `network` | table | | `{ via = "<capability>" }`: it runs inside the network of the service that fills that capability, and has none of its own — see [`network.via`](#inside-another-services-network--networkvia). |
| `api` | table | | The adapter lemonfiber reaches it through, in `stack.toml`'s shape. `kind` and `key_source` from the published set — see below. |
| `listens` | integer | ✔ if `api` or `speaks`, or where it answers on a port other than `port` | The port it answers on inside the container: where `port` is published to, and where lemonfiber, the services that ask and the proxy reach it. Default `port`. |
| `speaks` | array | | Each capability contract the service answers as an adapter, written `capability@major` from `contract/capabilities/index.json` (`ARCH-R200`). A service that speaks a contract names no `api`: it is asked one way. See [capability-contracts.md](capability-contracts.md). |
| `fronts` | string | ✔ if `speaks` | The plugin's own service this adapter stands in front of: the upstream it answers its contracts for. It names another service of the same plugin, one that speaks no contract, and its conformance recordings are taken against the digest that service is pinned by. |
| `native` | string | | The API this service answers the stack's other services in, by the name those services know it by (`jellyfin`, `plex`, `emby`). Declared on the upstream an adapter `fronts`, where other services reach that upstream directly rather than through the adapter: a request service is set up against a media server in the media server's native API (`F14-R26`, `ARCH-R221`). |
| `replaces` | string | | The id of the stack's own service this service moves in place of: the same container name, configuration directory and data, so an install moves the bundled service rather than running beside it ([ADR-0042](../../00-overview/decisions/0042-the-bundle-is-first-party-plugins-pinned-and-embedded.md) §4). It names the service's own id, and only that service may take the stack service's id, port and hostname (`ARCH-R222`). Only a first-party plugin's install honours it (`F14-R29`). |
| `shape` | enum | | `egress-guard` \| `render`. The one privileged shape lemonfiber writes for this service, from a closed set; each names who may declare it, and the operator approves it apart from the offer — see [shapes](#shapes--the-only-route-to-a-device-or-a-privilege) (`F14-R12`, `F14-R21`, `ARCH-R237`, `ARCH-R238`). |

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

### Ports — the tier is lemonfiber's, the numbers are the manifest's

A service declares `loopback` or `lan`. It cannot declare an address or a
host-facing interface, because a service that could write its own address could
place an admin surface on the LAN without touching anything
[C6](../../10-functional/features/c-trust/c6-web-security.md) inspects. lemonfiber
renders the tier to an interface for every service alike, and the two-tier policy
stays a property of the system rather than a request a manifest makes.

The numbers are the manifest's. `port` is where the service is published on the host
and `listens` where it answers inside its container, so an image answering on 8080 is
published at 8085 by declaring both, and one answering where it is published declares
`port` alone. A service publishing more than one port declares each further one in
`[[service.publish]]`, on the same tier: a door serving plain HTTP and TLS, a proxy
answering on 80 and 443.

```toml
port    = 8096
bind    = "lan"

[[service.publish]]
port = 8920
```

A port another service already publishes is refused, naming the port and both services
(`ARCH-R226`). A service that speaks a contract is also published at its `listens` port
on the loopback interface, at a port the engine chooses, which is where lemonfiber
reaches it.

### `config_path` — where its own directory lands

What a service reaches of the host is fixed: the single data mount, and the service's
own configuration directory with what lies inside it (`ARCH-R227`). That is what makes
"what can this plugin reach" answerable from the format. It does not follow that the
configuration directory must land at `/config`, and assuming it did made a whole class
of image uninstallable.

`/config` is a LinuxServer.io convention, not a standard. Of the twenty bundled
services, five keep their configuration somewhere else: Homepage and Seerr at
`/app/config`, Caddy at a file under `/etc/caddy`, Jellyfin and Audiobookshelf
needing a second path beside the first.
A plugin whose image is any of those shapes would be generated a container mounting
a directory the application never reads — installing successfully, passing its health
probe, and losing everything it had written the moment the container was replaced.

So the target is data. The source is still lemonfiber's, and there is still exactly
one of it. What is permitted is narrow:

- a single absolute path, and not `/`;
- not `/data` and nothing beneath it, which would be a second mount over the
  library wearing a different name;
- no `..`, and no interpolation.

`config_ro = true` mounts it read-only, for an image that reads its configuration and
has no business changing it: the guarded door reads its routes there and writes
nothing.

### Mounts — inside its own directory, and nowhere else

A second path beside the first — Jellyfin's `/cache`, Audiobookshelf's `/metadata` —
is a mount whose source lies inside the service's own configuration directory:

```toml
[[service.mount]]
from = "cache"
to   = "/cache"

[[service.mount]]
from = "Caddyfile"
to   = "/etc/caddy/Caddyfile"
ro   = true
```

`from` is a relative path inside the service's own configuration directory, a file or
a directory, and lemonfiber writes it as `./config/<id>/<from>`. An absolute path, a
`..` or an interpolation is refused, naming the mount. `to` is an absolute path and not
`/`; on a service that takes data it lies outside `/data`; and no two of the service's
mounts share a target. So a further mount widens nothing a reader has to judge: it is
the directory lemonfiber already gave the service, landing in a second place.

`tmpfs` reaches nothing of the host at all, and its targets are held to the same rules.
It is scratch space in memory, empty whenever the container starts and writable by
whoever the container runs as. The door keeps its working files there, so nothing it
writes outlives it.

**A service's state lives under its own directory and nowhere else** (`ARCH-R228`).
There is no volume the engine keeps on a service's behalf: state somewhere the operator
cannot see is state a backup, a move and the question "what can this reach" all miss.
The proxy keeps its certificates and its own state in two such volumes today
(`caddy_data`, `caddy_config`), so the in-place move copies each into the proxy's
directory once, mounts them from there, and leaves the volumes as they were, so that
undoing the move finds them.

There is no field by which a mount reaches any other path on the host. In particular
there is none for the engine's socket, which is root on the host, for a first-party
service as for anybody else's (`ARCH-R239`).

### Environment — four kinds of value

```toml
[service.env]
VPN_TYPE              = "wireguard"
SERVER_COUNTRIES      = { setting = "gluetun:countries", default = "Netherlands" }
DOMAIN                = { setting = "domain", default = "home.local" }
INDEXER_URL           = { url_of = "indexer.search" }
UN_SONARR_0_URL       = { url_of = "library.curate", files = "tv", native = "servarr" }
WIREGUARD_PRIVATE_KEY = { secret = "wireguard-key" }
```

| Value | Written as |
|-------|------------|
| A string, an integer or a boolean | A constant: the value exactly as declared |
| `{ setting = "<name>", default = <constant> }` | The operator's value for that setting, or the default where none is recorded |
| `{ url_of = "<capability>" }`, with `files` and `native` where needed | `http://<service>:<port>`: the service the ask reaches, at the port it `listens` on |
| `{ secret = "<name>" }` | The value of the `[[secret]]` the manifest declares by that name, in a file of the service's own and never in the project |

A variable's name is upper-case letters, digits and `_`, and does not start with a
digit. `TZ`, `PUID` and `PGID` are lemonfiber's: it writes the operator's time zone into
every entry and the pair where `user_mode` asks for it, and a manifest naming one is
refused (`ARCH-R229`).

**Nothing a manifest writes is interpolated.** Compose substitutes `${…}` from the
stack's environment file in any value, quoted or not. Every constant, every setting's
value and every secret is written with `$` doubled, so it reaches the container as exactly
itself, and no
value a manifest declares is written as a reference to that file (`ARCH-R230`). A value
that could name a variable there would be a field for reading whatever the file holds.

**A setting is the plugin's own, or one the core publishes.** A plugin's own is
namespaced with its id, as its own capabilities are (`gluetun:countries`), and a stack
service's with the service's id. The core publishes two, the same for every service:
`domain`, the operator's domain, and `lan-host`, the address the household reaches the
machine at. A setting in any other namespace is refused, naming it (`ARCH-R231`).

Settings live in the core's settings store, and the operator reads and changes them from
the command line, the web surface and the companion's operator screens alike, through
`lemonfiber settings` and [`GET /api/settings`](web-api.md#settings). Each change
is journalled and regenerates the entries that read it. A secret lives in the secret
store, never in the settings store (`ARCH-R248`). Neither is the stack's environment
file: the in-place move that brings a part's first-party plugin reads that file once,
files each value the part read from it under the plugin's own setting or secret,
journals each, and lemonfiber does not read the file for it again (`ARCH-R249`).

**A URL is an ask.** `url_of` names a core capability, as an `[[ask]]` does, and is
settled, shown and counted as one (`F14-R22` to `F14-R25`): the reading says what it
would reach, and a substitution rewrites it. It asks for one filler and never for
`each`, because a variable holds one address, so a variable naming a capability its
service asks `each` of is refused. `files` narrows the ask to the filler that files that
medium, which is how a service told about each curator in its own variable names each
one: one `url_of` for each, by the medium it files, never by its id. Two variables naming
one capability and medium, or a variable and an `[[ask]]` naming them, are one ask. While
nothing fills it, the variable is left out and the ask is reported unfilled (`F4-R9`). It
never names a service: that would be a link by name, which a plugin may not introduce
(`F4-R12`, `ARCH-R232`).

**An ask reaches the adapter, unless it says otherwise.** The core speaks contracts, so
what fills a capability is, by default, the service that speaks its contract. A service
that talks to the upstream in the upstream's own API says so with `native`, naming the API
the upstream declares (`native = "servarr"`), and its ask then reaches the service the
adapter `fronts`; a filler whose upstream declares no such API leaves the ask unfilled,
naming the API. Where the filler speaks no contract, as the stack's own services do, the
ask reaches the filler itself (`ARCH-R253`).

**A secret is declared, held, and written apart.** `{ secret = "<name>" }` names a
[`[[secret]]`](#secret-and-override--declared-before-they-are-held) the manifest
declares: a value the operator enters, one its recipe captures, or a credential
`F14-R18` or `F14-R20` lets cross to it. lemonfiber writes it to an environment file of
the service's own, readable by the owner alone (`0600`), names that file in the entry,
and never writes the value into the project. Every rehearsal, reading and diagnostic
shows the variable and the secret's name, never its value (`ARCH-R247`).

### Who it runs as, and how tightly it is held

| `user_mode` | Written as |
|-------------|------------|
| `image` | No user: the image decides |
| `puid-env` | `PUID` and `PGID` set to the operator's uid and gid, for an image that drops to them itself |
| `uid` | The operator's uid and gid as the container's user |

The `PUID`/`PGID` pair is a LinuxServer.io convention, and setting it on an image that
ignores it is a silent no-op that reads like a security control. So the manifest says
which kind of image it is, rather than lemonfiber asserting something about an image
nobody checked. A service that speaks a contract is built for lemonfiber's, reads a key
written readable by the operator's uid alone, and is `uid` (`F14-R27`, `ARCH-R233`).

| `posture` | Written as |
|-----------|------------|
| `standard` | No privilege gained after start; every kernel capability dropped but `CHOWN`, `DAC_OVERRIDE`, `FOWNER`, `SETGID`, `SETUID` and `KILL`, the six an image needs to start as root, give its files to the operator and drop to them, and what its shape adds; at most 1024 processes |
| `confined` | All of `standard`, with a read-only root, no kernel capability at all, `user_mode = "uid"` and no shape. Its own network translates no address off the host (`ARCH-R243`). |

`standard` is every service's, the stack's own and every plugin's, first-party and
third-party alike, and it is what lemonfiber already writes for a plugin's service
(`ARCH-R234`). `confined` is for an image that holds a credential administering another
service, as lemonfiber's own do.

**Posture is declared, and proved where the plugin is built.** A plugin's CI runs each
of its images under the posture its manifest declares, `standard` included, and a
manifest declares `confined` only where that run passes under it. So whether an image
survives six capabilities, or a read-only root and none, is answered where the image is
made. The stack's own images are run under `standard` by the media stack's CI, the CI
that already runs them to record their claims, before the version that writes them
ships (`REPO-R93`). lemonfiber writes the posture declared and refuses nothing at run
time on account of it (`ARCH-R250`).

`mem_limit_mib` is a ceiling and `memory_mib` an estimate, and they are two fields
because they answer two questions (`ARCH-R235`). The estimate is summed into what a form
would need and is never enforced: a figure that fits a media server idling would kill
it transcoding. The ceiling is written as the container's limit, for a service whose
upper bound is part of what makes it safe, such as one that answers a household page
and must not be able to exhaust the machine.

### Inside another service's network — `network.via`

```toml
network = { via = "network.egress-guard" }
```

Some services must have no network of their own. A torrent client inside the egress
guard's network namespace loses connectivity when the tunnel drops, rather than falling
back to the home address (`C2-R12`). `network.via` asks for that, by capability
(`ARCH-R236`):

- the service is written into the network namespace of the service that holds the
  tunnel: the filler, or where an adapter fills the capability, the upstream that adapter
  fronts, which takes the `egress-guard` shape. It has no network of its own;
- it starts only once that service reports healthy, which is the one start-order edge
  the format writes;
- the ports it declares are published on that service's entry, on its own tier, since a
  container with no network of its own publishes nothing;
- it is an ask of the capability, settled, shown and counted as every ask is, so choosing
  another egress guard moves the service inside the one chosen.

The capabilities a service may take `via` are a closed set, and it holds
`network.egress-guard` alone. A service may not take `via` a capability it provides.
Starting the service starts the capability's filler first and waits until it is healthy,
whatever profile the filler sits in. That is the one start-order edge allowed to cross a
profile (`B1-R14`), because the client and the guard are two plugins and so two profiles.

The client never learns the forwarded port from the guard itself: the guard's filler
reports it over `network.egress-guard`, and the core sets it on the client over
`download.torrent` ([capability-contracts](capability-contracts.md#the-forwarded-port),
`ARCH-R251`). No script is mounted into the guard.

### Shapes — the only route to a device or a privilege

| Shape | Written as | Who may declare it |
|-------|------------|--------------------|
| `egress-guard` | `NET_ADMIN` added, and the `/dev/net/tun` device | The upstream an adapter of the same plugin fronts, where that adapter speaks `network.egress-guard` (`F14-R12`); in the stack, the service that provides `network.egress-guard` |
| `render` | The host's `/dev/dri` device, and the group that owns it on the host added to the container's groups | A service that provides `media.serve`, or the upstream an adapter of the same plugin fronts, where that adapter speaks it |

A shape is a name, never a list: no manifest names a kernel capability, a device or a
group (`ARCH-R237`). The render group is read from the host's device rather than
declared, because its id differs from machine to machine and a manifest naming one
would be naming a number it cannot know. Where the host has no `/dev/dri`, as under
Docker Desktop or on a machine without a GPU, `render` is written as nothing and the
reading says the service runs without hardware transcoding.

The reading names every service taking a shape and what the shape gives it, and the
operator approves each apart from the offer, written `<shape>@<service>` (`F14-R21`,
`ARCH-R238`).

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
demonstrated, not asserted*, and a name in a list asserts. A capability the same service
[`speaks`](capability-contracts.md#speaking-a-contract) is demonstrated by its contract
instead: the live pass at install and its recordings are the evidence, and it carries no
`[[claim]]`.

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

### `api` names an adapter lemonfiber already has

A plugin's service may declare `api` in the stack manifest's own shape
([`api`](stack-manifest.md#api)): `kind` names one of the adapters lemonfiber
implements and `key_source` where the service's credential is read. Naming one is
how a plugin's service is reached by whatever asks for a capability it claims:
lemonfiber registers it with the services that ask, through that adapter, as it
registers a bundled service declaring the same, and nothing that asks changes
(`F9-R6`).

The set is fixed and published as `contract/adapters.json`, generated from the
kinds and key sources lemonfiber implements (`F8-R13`, `ARCH-R143`). A plugin
cannot add to it: no field lets a manifest supply an adapter (`F8-R11`), and a
`kind` or `key_source` outside the set is refused, naming it and the set
(`F8-R12`). A service declaring `api` declares `listens` too, as the stack's own
services do (`ARCH-R144`).

A service declaring no `api` is operated generically, as `F1-R10` and `F1-R11`
promise for a service lemonfiber does not know: whatever asks for a capability it
fills is told that nothing here can register it there, rather than being left
unwired without a word.

### A plugin may not declare itself `critical`

`critical` means *its failure has consequences outside the machine*, and in the
bundled stack exactly one service holds it. It is not a severity a contributor
assigns to their own work: the classification drives how failures are reported
and how hard lemonfiber tries to stop the operator proceeding. A plugin
declaring it is refused, naming the value and the four that are available.

### The fields that are absent, and why

Some of these are fields `stack.toml` carries for the stack alone, and the rest are what
a Compose entry could say and the model does not. A manifest carrying one is refused by
name (`ARCH-R84`), rather than having it ignored:

| Field | Why a plugin may not declare it |
|-------|--------------------------------|
| `grants` | Kernel capabilities, by name. No manifest, the stack's included, names a capability, a device or a group: a service that needs one declares a [shape](#shapes--the-only-route-to-a-device-or-a-privilege), which lemonfiber writes, so nothing a manifest writes can widen what it is given. |
| `depends_on` | An ordering edge, by name. The one edge the format writes is [`network.via`](#inside-another-services-network--networkvia)'s, to whatever fills the capability it names, because a container inside another's network cannot start before that network exists; it is the edge that keeps torrent traffic inside the tunnel (`B1-R14`). Any other edge between services is a source of failures nobody can attribute, and one naming a service is a link by name. |
| `[[wiring]]` | The stack manifest's array of [links between its own services](stack-manifest.md#wiring--the-link-between-two-services-and-which-of-them-it-names) — `by`, `asks`, `filled_by`, `to`: who asks whom for what. **Not the [`[[wiring]]`](#wiring--how-the-stacks-own-services-reach-one-service) below**, which is spelled the same and says something else: `hostname`, `dashboard_group` and `service`, naming where lemonfiber puts *this* plugin's service on the proxy and the dashboard. One is a link between two services; the other is one service's own address. Since `ARCH-R127` made the plugin's a list too, the spelling no longer tells them apart and the file it is written in is what does. A plugin declares what it can do in `provides`, is asked for by whatever already asks, and asks in [`[[ask]]`](#ask--what-a-plugins-service-asks-for), by capability only. In particular it cannot introduce a **by-name** link, which is `F4-R12`'s third clause: a by-name wiring is the operator's exception to make and a plugin naming another service is reaching into wiring it does not own. |
| `host_managed` | Native-mode lifecycle is the operating system's (`B2-R15`). A plugin cannot install a system service. |
| `profile` | Assigned, not declared — see below. |
| `environment` | Free-form variables. A free-form pair is how a manifest would configure its way past what the format says it does, and a value carrying `${…}` would read the stack's environment file, credentials included. A service's environment is [`env`](#environment--four-kinds-of-value) instead, where every value is one of four typed kinds and nothing is interpolated. |
| `ports`, `volumes`, `networks`, `network_mode`, `devices`, `cap_add`, `user`, `privileged`, `entrypoint`, `command` | Compose's own keys. Each is what lemonfiber writes from the typed fields above or never writes at all, and a manifest naming one is naming the output rather than declaring the service. |
| `last_release` | An abandonment signal maintained by the people reviewing the bundled pins (`F2-R14`). Self-reported by a plugin it would signal nothing. |

## What lemonfiber writes

A plugin's service gets **its own profile**, named for the plugin, which is
added to the closure of each form the plugin declared (`ARCH-R96`). Its own
profile rather than an existing one, because a profile is the unit that starts
and stops together, and a stranger's service joining `tv` would mean
`lemonfiber up tv` could no longer be described without naming what is installed.

The core writes that profile as `plugin-<id>` and adds it to no form's closure: an
install starts it alone, a removal takes it down alone, and `lemonfiber up <form>`
names only the profiles the stack's own forms declare. `0.18.0` locks `ARCH-R96`.

From the declarations of every service, the stack's and every plugin's, lemonfiber
generates one Compose project (`ARCH-R224`). Nothing in it is read from a file somebody
wrote: there is no fragment, no shared template and no overlay. For the Plex
declaration above, the entry is:

```yaml
plex:
  image: docker.io/plexinc/pms-docker@sha256:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
  profiles: [plugin-plex]
  restart: unless-stopped
  environment:
    TZ: ${TZ}
    PLEX_CLAIM: ""
  ports: ["${LAN_BIND}:32400:32400"]
  volumes:
    - ${DATA_ROOT}:/data
    - ./config/plex:/config
    - ./config/plex/transcode:/transcode
  security_opt: ["no-new-privileges:true"]
  cap_drop: [ALL]
  cap_add: [CHOWN, DAC_OVERRIDE, FOWNER, SETGID, SETUID, KILL]
  devices: ["/dev/dri:/dev/dri"]
  group_add: ["${RENDER_GID}"]
  pids_limit: 1024
```

Every line comes from one place:

| Line | From |
|------|------|
| `image` | `image` joined to `digest`; the tag is never written |
| `profiles` | `plugin-<id>`, or a stack service's own `profile` |
| `restart`, `TZ` | Every entry alike |
| `PUID`, `PGID`, `user` | [`user_mode`](#who-it-runs-as-and-how-tightly-it-is-held) |
| The rest of `environment` | [`env`](#environment--four-kinds-of-value), every value literal |
| `env_file` | The service's own secrets file, where `env` names a `secret` |
| `ports` | `port`, `listens` and `publish`, on the interface the tier renders; for a service taking `via`, on its filler's entry |
| `volumes` | The data mount where `takes_data`, from the [storage setting](#the-data-root--one-setting-every-data-mount); the configuration directory at `config_path`; each `mount` |
| `tmpfs` | `tmpfs` |
| `security_opt`, `cap_drop`, `cap_add`, `pids_limit`, `read_only` | `posture`, with what the shape adds |
| `mem_limit` | `mem_limit_mib` |
| `devices`, `group_add` | `shape` |
| `network_mode`, `depends_on` | [`network.via`](#inside-another-services-network--networkvia) |
| `networks` | [Derived](#the-networks), never declared |

The only substitutions an entry carries are the variables lemonfiber writes itself: the
interface a tier renders, the data root, the operator's uid and gid, the time zone and
the render group. Everything a manifest supplied is written as a literal.

That is the whole of it. There is no field in `plugin.toml` that adds a line outside
that table, which is what makes "what can this service reach" answerable from the
format rather than from the instance; only the operator's own overlay changes it, and
it is shown as unvetted wherever it does. A service that is native-mode on the host
(`host_managed`) gets no entry.

The project is lemonfiber's output, not a file to edit: a service changes by changing
its manifest. An edit made to the generated project is a locally modified materialised
file, detected by content and never overwritten without a diff and confirmation
(`F1-R4`).

### The operator's overlay

An operator whose service needs something the model cannot say writes it in an overlay
of their own: one Compose file on their own machine, in lemonfiber's configuration
directory, which lemonfiber merges last, over the project it generated (`ARCH-R252`).
This is the escape hatch ADR-0021 §6 described, kept on the same terms: it is the
operator taking responsibility for their own machine with their eyes open, and never a
route a manifest can take on anybody's behalf.

- **It is never a plugin's.** No manifest, catalogue entry or bundle supplies one, and
  nothing lemonfiber installs writes to it (`ARCH-R85`).
- **It is unvetted, and said so.** The doctor and every rehearsal name the overlay and
  each service it changes as unvetted, because nothing in it was held to the model.
- **It is journalled.** A change to it is recorded by content when lemonfiber next writes
  or starts the project, so what the machine ran is answerable afterwards.

lemonfiber also writes the stack's own wiring for a plugin's service, from the same
declaration and by the same argument — a plugin that supplies no Compose entry supplies
no proxy stanza and no dashboard entry either, and gets both written for it. The proxy
reaches a service at its `listens` port. For a `lan` service:

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

### The data root — one setting, every data mount

The data mount is written from one operator setting, the same for every service that
takes data (`ARCH-R240`):

| Setting | The data mount |
|---------|----------------|
| `bind`, with a host path | That path, bound at `/data` |
| `nfs`, with `server` and `export` | One NFS volume the project shares, mounted at `/data`, with mount options lemonfiber fixes |

[ADR-0006](../../00-overview/decisions/0006-single-data-mount.md)'s rule holds by
construction: each service has one data mount and no second to declare, and the
setting decides where it comes from, never how many there are. The setting is a
location, not a storage mode: what that location can do is still found by making a
hardlink there (`C5-R2`).

The server is a host name or an address and the export an absolute path. Either is
refused, naming it, where it holds a comma, whitespace or anything else that would
change the mount options written. There is no overlay: a service added later takes the
same mount, which a hand-kept list of the services that take data did not guarantee.

### The networks

Every network in the project, and every service's place on it, is derived by
lemonfiber from the settled asks between capabilities and the stack's links by name
(`ARCH-R241`). There is no shared default network: two services share a network only
where one of the rules below joins them, so every link is one the wiring states. No
manifest, first-party or third-party, names a network, a subnet or an address, and none
has a field in which to.

- **An ask is a network.** Each settled ask is a network of its own, joining the asking
  service and the service the ask reaches — the adapter, or the upstream where the ask is
  `native` — with no route off the host. A link by name joins the service it names, and
  never a service standing in for it (`ARCH-R242`).
- **A hostname and a panel are asks.** A service the proxy routes a hostname to asks
  `proxy.front`, and one whose dashboard panel reads it asks `dashboard.show`, so the
  proxy and the dashboard reach exactly the services they front or show.
- **An adapter and its upstream are a private network.** Every adapter and the service
  it `fronts` share a network nothing else joins, with no route off the host. The core
  reaches the adapter at its contract port, published on the loopback interface, which
  is the third member `F14-R5` names (`ARCH-R243`).
- **A service's own network.** A service that publishes a port, or that is not confined,
  is on one network of its own carrying its ports and its route off the host. Where it is
  confined, that network translates no address off the host, so its port answers and it
  cannot reach out, and a confined service publishing nothing has none.
- **A service taking `via`** has no network: it is inside its filler's, and an ask it
  fills joins the service it is inside.

So a link the stack relies on is one its wiring states. Two the shipped stack made over
its shared network and never wrote down are asks: Prowlarr asks `indexer.proxy` of the
service that gets past an indexer's bot protection, and Bindery asks `download.usenet`
and `download.torrent` of the download clients, as the other curators do.

**Two addresses are fixed, because two trust decisions rest on them.** The media server
believes which client a request came from only where the guarded door says so, and the
door believes it only where the proxy says so. So lemonfiber fixes the address of the
`stream.guard` filler on the network of its ask of `media.serve`, and the addresses of it
and of the `proxy.front` filler on the network of its ask of `proxy.front`, each from a
subnet lemonfiber holds in which the engine assigns no other address. It tells the media
server the guard's address as the one proxy it trusts, and the guard the proxy's
(`ARCH-R244`).

A plugin's service is placed by the same rules: a filler of an ask is on the network
that ask derives, whatever installed it, so a stand-in is reached over exactly the
networks the part it replaced was reached over and gains a route to nothing else
(`F9-R6`). Choosing which service fills an ask moves what that ask's network joins, so
the choice regenerates the project in the same journalled change as the setting, and a
choice and the reach it grants move together (`ARCH-R245`).

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
| `probe[].fixture` | string | ✔ | The recorded response. Required here where it is optional on a proof: a claim nobody can demonstrate without owning the service is a claim the catalogue's CI cannot check (`F5-R13`). |

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

## `[[ask]]` — what a plugin's service asks for

```toml
[[ask]]
service    = "subfinder"        # optional where the plugin declares one service
capability = "library.curate"
each       = true               # every service that fills it, not one
```

| Field | Type | Req | Meaning |
|---|---|---|---|
| `service` | string | | The plugin's own service that asks. Required where the plugin declares more than one service |
| `capability` | string | ✔ | A core name the published vocabulary carries |
| `each` | bool | | `true` to reach every service that fills it. Default `false`: one filler, settled by the operator's choice or the stack's own (`F14-R23`) |
| `native` | string | | The upstream's own API the service talks in, as the upstream declares it in its `native`. The ask then reaches the upstream the filler's adapter `fronts` rather than the adapter (`ARCH-R253`) |

The stack's `[[wiring]]` has `filled_by`, `to` and `why`; an ask has none of them. A link by
name is the operator's exception (`F4-R12`), and a manifest has nowhere to write one
(`F14-R22`).

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

A plugin declares the checks that must hold before it is installed: each a request, what
the answer is expected to be, and the recording it is proved against. The whole of
`[[proof]]` is on [its own page](plugin-manifest-proof.md).

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

## `[[recipe]]` — ordered calls, bounded by reading

A plugin may declare ordered calls that configure what it installed, each bounded by
what it reads, and run only when asked for by name. The whole of `[[recipe]]` is on [its
own page](plugin-manifest-recipe.md).

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

A secret a service's [`env`](#environment--four-kinds-of-value) names is declared here
too. Its value is one a recipe captures, a credential `F14-R18` or `F14-R20` lets cross
to the plugin, or, where neither supplies it, one the operator enters at install without
it being shown. It is held in the secret store and reaches the container only through the
service's own secrets file (`ARCH-R247`).

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
| No port the service publishes (`port`, each `publish.port`, and a `via` service's on its filler) is one another service publishes | Port and both services named |
| `publish` only where `port` is | Service named |
| `wiring.hostname` is not a name the stack's own proxy is written to answer on | Name given |
| At most one service declares a given core capability | Capability and both services named |
| `digest` present and well-formed | Service named |
| `bind` present when `port` is | Service named |
| `criticality` is not `critical` | Value named, with the four available |
| `license` present | Plugin named |
| Every `forms` entry names a declared form | Both named |
| Every entry in `requires.capabilities` is offered | Capability named, never a version |
| `config_path` is one absolute path, not `/`, and outside the data root | Path named, with what is permitted |
| Every `mount.from` is a relative path inside the service's own configuration directory, with no `..` and no interpolation | Mount named, with what is permitted |
| Every `mount.to` and `tmpfs` entry is an absolute path, not `/`, outside `/data` where the service takes data, and no other mount's target | Mount named, with what is permitted |
| Every `env` name is a variable's name and none of `TZ`, `PUID` and `PGID` | Variable named |
| Every `env` value is a constant, `{ setting, default }`, `{ url_of }` (with `files` and `native` only) or `{ secret }`, and nothing else | Variable named, with the four kinds |
| Every `{ secret }` names a `[[secret]]` the manifest declares | Variable and secret named |
| Every `files` names a medium in `stack.toml`'s vocabulary, and only on `url_of` | Variable named, with the media |
| Every `setting` is one the core publishes or in the plugin's own namespace | Setting named, with the namespace required |
| Every `url_of` names a core capability its service does not ask `each` of, and is held to every rule an `[[ask]]` is | Variable and capability named |
| `user_mode` is `uid` where the service speaks a contract or is `confined` | Service named |
| A `confined` service declares no `shape` | Service named |
| `memory_mib` and `mem_limit_mib` above zero where declared | Service named |
| `network.via` names a capability in its closed set, one the service does not provide | Service and capability named, with the set |
| `shape` is declared only where that shape permits | `service <id>.shape` named |
| Every `provides` entry is a published core name or namespaced with the plugin's id | Capability named, with the namespace required |
| Every `[[proof]]` carries `id`, `title`, `request`, `expect` and `why` | Proof and field named |
| At least one `[[proof]]` constrains the body rather than only the status | Every status-only proof named |
| Every `expected` entry carries `fixture`, `verdict`, `constraint` and `reason`, its `verdict` is `fails`, and its `fixture` names a recording that exists | Assertion, entry and field named |
| Every `expected` entry names a constraint its assertion's `expect` makes, with a `place` exactly where that constraint is key-wise | Assertion, entry and constraint named, with the constraints the assertion makes |
| No two `expected` entries of one assertion name the same recording | Assertion and recording named |
| `wiring.hostname` is a single DNS label | Value named |
| A `loopback` service declares no `wiring.hostname` | Service named, and the tier that governs |
| Every `[[wiring]]`, `[[proof]]` and contributed check names a declared service, and names one where the plugin declares more than one | Name given, with the services declared |
| No service is wired twice | Service named |
| Every `[[ask]]` names a declared service, and names one where the plugin declares more than one | Name given, with the services declared |
| Every `ask.capability` is a core name the published vocabulary carries | Capability named: a namespaced one as naming a plugin, a removed one with its generation, an unknown one with the names carried |
| No service asks for the same capability twice | Service and capability named |
| No service asks for a capability it provides | Service and capability named; nothing asks itself |
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
| Every `{{name}}` in a call is an earlier capture or an input, and a pair carries it to that call's `to` (`F8-R5`) | Value and destination named |
| No `{{name}}` in a call's `to`, or in its `path` but for a query value (`F8-R2`) | Step and field named |
| No `{{name}}` in a header's name (`F8-R2`) | Step and header named, as `PLUGIN-33` |
| Every call's `path` is a plain absolute path (`F8-R2`) | Step named, with what is wrong with it, as `PLUGIN-37` |
| Every `origin` is one of the four, and agrees with where the value comes from (`F8-R3`) | Value named, with both origins |
| A credential-store value, and every capture from a call that carried or read one, is carried, by a pair or a `{{name}}`, or read by a guard, only to the service it belongs to, and any other capture from a service in this stack only to that service or by a pair releasing it (`F8-R16`) | Value, the service it is held to and the destination named |
| A pair's `release` is on a capture from a service in this stack, by a call that carried and read no credential-store value, carried to another destination, and nowhere else (`F8-R16`) | Pair named |
| Every credential-store input's `of` is a service of the stack's whose credential lemonfiber holds, never one of this plugin's own (`F8-R3`) | Input and service named |
| `input[].secret` is a boolean, and only on an `operator` input | Input named |
| Every `to` is a service in this stack with a published port, or a DNS name of two labels or more (`F8-R4`, `F8-R8`) | Destination named |
| Every `when` names an earlier step or an earlier value | Guard and name given |
| Every `retry` is within the published bounds | Bound named |
| Every `capture.from` is an expectation key or `header.<name>` | Key named, with what is wrong with it |

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
| **ARCH-R86** | *Superseded by [ARCH-R224](plugin-manifest.md) and [ARCH-R227](plugin-manifest.md): every entry is written from the one model and extends no template, and a service mounts its own directory and what lies inside it besides the data mount. The number is not reused.* |
| **ARCH-R87** | *Superseded by [ARCH-R239](plugin-manifest.md): no field reaches the engine's socket, a privileged container, a host namespace, an entrypoint or a command, and a capability, a device or a group comes only from a shape, while `user_mode` and `network.via` are typed fields of the model. The number is not reused.* |
| **ARCH-R88** | *Superseded by [ARCH-R226](plugin-manifest.md): the interface is lemonfiber's from the tier, and the host and container ports are the manifest's. The number is not reused.* |
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
| **ARCH-R101** | *Superseded by [ARCH-R229](plugin-manifest.md): a service's environment is typed, four kinds of value and nothing else. The number is not reused.* |
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
| **ARCH-R130** | A `[[proof]]` and a `doctor.check` row MUST be able to carry `expected`, a list of entries each naming a recording, the verdict `fails`, the constraint of its `expect` that fails there (with its place where the constraint is key-wise), and a reason. An entry missing any of them, naming a verdict other than `fails` or a recording that does not exist, naming a constraint or place its assertion's `expect` does not make, or naming a recording another entry of the same assertion names MUST be refused by name, and a `[[claim.probe]]` MUST have no such field. |
| **ARCH-R143** | The set of adapters a plugin's service may name MUST be published as `contract/adapters.json`, generated from the adapter kinds and key sources lemonfiber implements, and regenerating it MUST produce no diff. |
| **ARCH-R144** | A service declaring `api`, bundled or a plugin's, MUST declare `listens`, the port it answers on inside the stack's network, and lemonfiber MUST reach it at that port rather than at its published port or at a port named in lemonfiber's source. |
| **ARCH-R154** | *Superseded by [ARCH-R241](plugin-manifest.md)–[ARCH-R243](plugin-manifest.md): the networks are derived from the settled asks, and no compose file is read for them. The number is not reused.* |
| **ARCH-R155** | *Superseded by [ARCH-R245](plugin-manifest.md): a choice of filler regenerates the one project rather than each plugin's document. The number is not reused.* |
| **ARCH-R216** | A service that speaks a contract MUST name in `fronts` one other service of the same plugin that speaks none, and a manifest where it names none, itself, a service the plugin does not declare or one that speaks a contract MUST be refused by name. |
| **ARCH-R221** | `native` MUST be one lowercase word and MUST be declared only on a service another service of the same plugin `fronts`, and a manifest declaring it anywhere else MUST be refused, naming the service. |
| **ARCH-R222** | `replaces` MUST name a service the shipped stack declares and MUST equal the id of the service declaring it; that service MAY take the named service's id, port and hostname, every other service MUST still be refused any of the three, and a manifest declaring `replaces` anywhere else MUST be refused, naming `service <id>.replaces`. |
| **ARCH-R224** | lemonfiber MUST write the Compose entry of every service it runs, the stack's own and every plugin's, from the one typed service model, as one generated project, and MUST NOT read a Compose file, fragment, template or overlay from the stack or from a plugin. |
| **ARCH-R225** | A first-party plugin's service, a third-party plugin's service and a stack service MUST be declared in the same closed set of container fields, with the same types and the same validation, and whether a plugin is first-party MUST NOT change which of those fields it may declare or how its entry is written. |
| **ARCH-R226** | A service MUST be published at `port` to its `listens` port, or to `port` itself where it declares none, and at each `[[service.publish]]` entry alike, every one on the interface its `bind` tier renders; a port another service publishes MUST be refused, naming the port and both services; and the manifest MUST have no field naming an address or an interface. |
| **ARCH-R227** | A service MAY mount its configuration directory read-only, MAY declare further mounts whose source is a relative path inside that directory, read-only where it says so, and MAY declare `tmpfs` paths; a source that is absolute, holds `..` or interpolates, and a target that is not absolute, is `/`, lies within `/data` on a service that takes data or is another of its mounts' targets, MUST be refused naming the mount, and the manifest MUST have no field by which a mount reaches any other path on the host. |
| **ARCH-R228** | A service's state MUST live under its own configuration directory, and lemonfiber MUST NOT write a volume the engine keeps for a service; the in-place move of a part whose entry kept state in such a volume MUST copy it into the service's directory once, mount it from there, and leave the volume as it was. |
| **ARCH-R229** | A service's environment MUST be declared in `[service.env]`, every value a constant, an operator setting with a default, the URL of a capability's filler, or a declared secret, and nothing else; a value of any other kind, and a manifest naming `TZ`, `PUID` or `PGID` there, MUST be refused naming the variable. |
| **ARCH-R230** | lemonfiber MUST write every constant, every setting's value and every secret so that Compose substitutes nothing in it, and MUST NOT write any value a manifest declares as a reference to the stack's environment file. |
| **ARCH-R231** | A setting MUST be one the core publishes or one in the declaring plugin's own namespace, a stack service's own id for a stack service, and any other MUST be refused naming it; lemonfiber MUST write the operator's value where one is recorded and the declared default otherwise. |
| **ARCH-R232** | `{ url_of = "<capability>" }` MUST name a core capability and MUST be an ask of one filler, narrowed by `files` to the filler that files that medium where it is given, one ask with every other variable or `[[ask]]` of the same service naming that capability and medium, held to every rule an `[[ask]]` is held to and settled, shown and counted as one, and a variable naming a capability its service asks `each` of MUST be refused; lemonfiber MUST write it as the URL of the service the ask reaches at the port that service listens on, and MUST leave the variable out, reporting the ask unfilled, while nothing fills it. |
| **ARCH-R233** | `user_mode` MUST be `image`, `puid-env` or `uid`, written respectively as no user, as `PUID` and `PGID` set to the operator's uid and gid, and as the operator's uid and gid for the container's user; a service that speaks a contract or whose posture is `confined` MUST be `uid`, and one that is not MUST be refused naming the service. |
| **ARCH-R234** | Every service's entry, the stack's own and every plugin's, MUST be written with `posture = "standard"` unless it declares `confined`: gaining no privilege after it starts, holding no kernel capability but `CHOWN`, `DAC_OVERRIDE`, `FOWNER`, `SETGID`, `SETUID`, `KILL` and those its shape adds, and holding at most 1024 processes; a service whose `posture` is `confined` MUST in addition be written with a read-only root, no kernel capability at all and the `uid` user, and a confined service declaring a shape MUST be refused naming the service. |
| **ARCH-R235** | `mem_limit_mib` MUST be written as the container's memory limit, and `memory_mib` MUST be an estimate that is never written as a limit. |
| **ARCH-R236** | `network = { via = "<capability>" }` MUST name a capability from a closed set holding `network.egress-guard` alone and not one the service provides; lemonfiber MUST write the service into the network namespace of the service that fills it, or of the upstream that filler's adapter fronts where an adapter fills it, MUST start that filler first and start the service only once the filler reports healthy, whatever profile the filler sits in, MUST publish the service's ports on the filler's entry on the service's own tier, MUST give the service no network of its own, and MUST settle, show and count it as an ask of that capability. |
| **ARCH-R237** | A device, a group or an added kernel capability MUST come only from a named shape in a closed set holding `egress-guard` and `render`; `render` MUST be declared only by a service that provides `media.serve` or by the upstream an adapter of the same plugin fronts where that adapter speaks it, refused naming `service <id>.shape` elsewhere, and MUST be written as the host's `/dev/dri` device with the group that owns it on the host added, or as nothing where the host has no `/dev/dri`, which the reading MUST say. |
| **ARCH-R238** | An install or update whose plugin takes any shape MUST state in its reading each service taking it with what the shape gives, and MUST NOT act unless the operator approved that shape for that service apart from the offer, written `<shape>@<service>`, as `F14-R21` holds for the egress guard's. |
| **ARCH-R239** | The manifest MUST have no field by which a service could mount the engine's socket, run privileged, join the host's network, PID or IPC namespace, name an entrypoint or a command, or obtain a kernel capability, a device or a group other than through a shape. |
| **ARCH-R240** | The data root MUST be one operator setting, `bind` with a host path or `nfs` with a server and an export, and lemonfiber MUST write the single data mount of every service that takes data from it and from nothing else; a server that is not a host name or an address, and an export that is not an absolute path or holds a character that would change the mount options written, MUST be refused naming it. |
| **ARCH-R241** | lemonfiber MUST derive every network of the project and every service's place on it from the settled asks between capabilities and the stack's links by name, MUST write no network shared by services that no rule of the derivation joins, and the manifest MUST have no field naming a network, a subnet or an address. |
| **ARCH-R242** | Each settled ask MUST be a network of its own joining the asking service and the service the ask reaches, with no route off the host; a service given a proxy hostname MUST ask `proxy.front` and one whose dashboard panel reads it `dashboard.show`; an ask filled by a service taking `via` MUST join the service it is inside; and a link by name MUST join the service it names and never a service standing in for it. |
| **ARCH-R243** | Every adapter and the service it fronts MUST share a network no other service joins, with no route off the host, and the core MUST reach the adapter at its contract port published on the loopback interface; a service that publishes a port or is not confined MUST be on a network of its own carrying its ports and its route off the host, translating no address off the host where it is confined. |
| **ARCH-R244** | lemonfiber MUST fix the address of the `stream.guard` filler on the network of its ask of `media.serve`, and the addresses of it and of the `proxy.front` filler on the network of its ask of `proxy.front`, each from a subnet lemonfiber holds in which the engine assigns no other address, and MUST tell the media server's filler the guard's address as the one proxy it trusts and the guard the proxy's. |
| **ARCH-R245** | Choosing which service fills an ask MUST regenerate the project in the same journalled change as the setting. |
| **ARCH-R247** | `{ secret = "<name>" }` MUST name a `[[secret]]` the manifest declares, refused naming the variable otherwise; lemonfiber MUST write its value only to an environment file of the service's own readable by its owner alone (`0600`), named by the entry, MUST NOT write it into the project, and MUST show the variable and the secret's name, never its value, in every rehearsal, reading and diagnostic. |
| **ARCH-R248** | A setting MUST live in the core's settings store and a secret in the secret store; the operator MUST be able to read and change a setting from the command line, the web API and the companion's operator screens alike, and each change MUST be journalled and MUST regenerate every entry that reads it. |
| **ARCH-R249** | The in-place move that brings a part's first-party plugin MUST read the stack's environment file once, file each value the part read from it under the plugin's own setting or secret, journal each, and lemonfiber MUST NOT read the environment file for that part again. |
| **ARCH-R250** | A plugin's CI MUST run each of its images under the posture its manifest declares, `standard` included, and a manifest MAY declare `posture = "confined"` only where that run passes under it; lemonfiber MUST write the posture a manifest declares and MUST NOT refuse to install, update or start a service on account of its posture. |
| **ARCH-R252** | lemonfiber MUST merge one operator-written overlay from its own configuration directory last, over the project it generates; MUST NOT accept or write an overlay from a plugin, a catalogue or the bundle; MUST name the overlay and every service it changes as unvetted in the doctor and in every rehearsal; and MUST journal each change to it, by content, when it next writes or starts the project. |
| **ARCH-R253** | An ask and a `url_of` MUST reach the service that speaks the capability's contract, the filler itself where the filler speaks none, and the upstream that filler's adapter fronts only where the asker names that upstream's declared API in `native`; an ask naming an API the filler's upstream does not declare MUST be reported unfilled, naming the API. |

## Related

- [ADR-0021](../../00-overview/decisions/0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md) — the decision this contract implements
- [stack-manifest](stack-manifest.md) — the vocabulary a plugin's service is declared in, and the whole-stack manifest this is not
- [capability-vocabulary](capability-vocabulary.md) — the names `provides` may carry and the probes a `[[claim]]` binds
- [extension-points](extension-points.md) — the points a `[[contribution]]` is made at and the row each one takes
- [versioning](versioning.md) — the three version identifiers, and the window this one does not share
- [web-api](web-api.md) — `ARCH-R78`–`ARCH-R82`, the capability negotiation this reuses and the tolerance rule it inverts
- [F3](../../10-functional/features/f-extensibility/f3-stack-manifests.md) — what a plugin is
- [F7](../../10-functional/features/f-extensibility/f7-plugin-provenance.md) — what stays readable once one is installed
