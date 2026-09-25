# Contract: `stack.toml`

**Status:** Accepted

The interface between `lemonfiber` and `lemonfiber-media-stack`. Everything
lemonfiber knows about
the stack comes from this file; it knows nothing about Sonarr that isn't declared
here.

**Satisfies:** [B1-R2](../../10-functional/features/b-running/b1-forms.md),
[B1-R3](../../10-functional/features/b-running/b1-forms.md),
[F1-R5](../../10-functional/features/f-extensibility/f1-customisation.md),
[F1-R9](../../10-functional/features/f-extensibility/f1-customisation.md),
[F2-R1](../../10-functional/features/f-extensibility/f2-service-catalogue.md)–[F2-R4](../../10-functional/features/f-extensibility/f2-service-catalogue.md),
[F2-R10](../../10-functional/features/f-extensibility/f2-service-catalogue.md),
[F4-R1](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R9](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R12](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F9-R4](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md)

---

## Why this file exists

Adding a service must not require a Rust change (`F1-R5`), and forms must be
data rather than code (`B1-R2`). Both demand that per-service knowledge live
somewhere lemonfiber reads rather than somewhere it compiles.

The alternative — a `match` over service names in Rust — means every stack change
is a release, third-party stacks are impossible, and the "it's just Compose"
guarantee quietly stops being true.

## File location

`stack.toml`, at the root of a stack directory, beside `compose.yml`.

## Top-level structure

```toml
schema_version = 1
stack_version  = "1.0.0"
min_cli_version = "0.4.0"

[[profile]]  # 12 of these
[[form]]     # 11 of these
[[service]]  # 19 of these
[[wiring]]   # one per link between two of them
```

## `schema_version`

An integer naming the manifest **format** generation. Incremented only on a
breaking structural change.

lemonfiber refuses a manifest whose `schema_version` it does not implement, with
both versions named (`F1-R9`). This turns version skew into a clear error rather
than an obscure Compose failure — and because the stack is embedded at build time
([ADR-0005](../../00-overview/decisions/0005-embedded-stack-assets.md)), it is
usually caught at **compile time** rather than reaching a user at all.

`stack_version` is the *content* version and is semver; it moves when services or
forms change. `min_cli_version` lets a stack refuse an older binary.

## `[[profile]]`

```toml
[[profile]]
id          = "tv"
name        = "Television"
description = "Automated television acquisition"

[[profile]]
id          = "torrent"
name        = "Torrents"
description = "Torrent downloading, VPN-isolated"
protocol    = "torrent"
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | Unique. Must match a Compose profile name exactly. |
| `name` | string | ✔ | Human-facing |
| `description` | string | ✔ | Shown in form previews |
| `protocol` | enum | | `usenet` \| `torrent`. Present only on a profile that cannot run without a configured provider. |

### `protocol` — what makes the intersection possible

[B1-R4](../../10-functional/features/b-running/b1-forms.md) requires a closure to
be intersected with the operator's configured protocols before anything starts.
Nothing in this contract said *which* profiles that applies to, so the only way
to satisfy it was for lemonfiber to know the strings `usenet` and `torrent` —
per-service knowledge in code, which is the one thing this file exists to
prevent.

`protocol` supplies it as data. A profile that declares one cannot run unless the
operator has configured that provider; a profile that declares none is never
narrowed away.

The consequence of getting this wrong is not cosmetic. A torrent profile started
without a configured VPN brings up the tunnel container with no credentials, and
the failure mode of a VPN that is not actually protecting anything is the one
failure in this product with consequences outside the machine.

A fork that renames its profiles keeps working, which was the point.

## `[[form]]`

```toml
[[form]]
id          = "tv"
name        = "TV"
description = "Search, download and automate television"
profiles    = ["search", "usenet", "torrent", "tv", "subs"]
composable  = true
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | Unique |
| `name` | string | ✔ | Human-facing |
| `description` | string | ✔ | One line, plain language |
| `profiles` | array | ✔ | The closure. Every entry MUST reference a declared profile. |
| `composable` | bool | | Default `true`. May be combined with other forms (`B1-R5`). |

A form's `profiles` list is the **complete** closure, written out. Dependencies
are not inferred — `tv` names `search` explicitly rather than lemonfiber deducing
that Sonarr needs indexers.

That verbosity is deliberate: inference would require lemonfiber to understand
each service's semantics, which is exactly the coupling this contract exists to
avoid.

## `[[service]]`

```toml
[[service]]
id          = "sonarr"
name        = "Sonarr"
profile     = "tv"
image       = "lscr.io/linuxserver/sonarr"
tag         = "4.0.15"
port        = 8989
bind        = "loopback"
health      = { kind = "http", path = "/ping", timeout_s = 60 }
api         = { kind = "servarr", key_source = "config-xml", path = "/config/config.xml" }
criticality = "core"
license     = "GPL-3.0-only"
upstream    = "https://github.com/Sonarr/Sonarr"
last_release = "2026-06-26"
describes   = "Watches for new episodes and fetches them"
without_it  = "Find and download episodes yourself"
reaches     = "television metadata providers"
asks_for    = "Reads series, season and episode information, artwork and air dates for what is in your library and what you add to it."
media_types = ["tv"]
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | Unique. MUST match the Compose service name. |
| `name` | string | ✔ | Human-facing |
| `profile` | string | ✔ | **Exactly one** (`B1-R1`). MUST reference a declared profile. |
| `image` | string | ✔ | Without tag or digest |
| `digest` | string | ✔ | `sha256:…` of the multi-architecture index. What actually runs (`E1-R1`). |
| `tag` | string | ✔ | The human-readable version the digest corresponds to. Recorded and shown; never resolved at run time. |
| `port` | integer | | Primary UI/API port. Omitted for services with no listener. |
| `bind` | enum | ✔ if `port` | `loopback` \| `lan`. Enforces [C6](../../10-functional/features/c-trust/c6-web-security.md)'s two-tier policy. |
| `health` | table | | See below. Absent means lifecycle waits on container state only. |
| `api` | table | | How lemonfiber talks to it for [seeding](../../10-functional/features/d-content/d1-seed.md). Absent means no API integration. |
| `criticality` | enum | ✔ | `critical` \| `core` \| `important` \| `enhancing` \| `optional` (`F2-R3`) |
| `license` | string | ✔ | SPDX identifier. A non-OSI value fails validation (`F2-R5`, `F2-R12`). |
| `upstream` | string | ✔ | Project URL, for maintenance review (`F2-R14`) |
| `last_release` | string | ✔ | `YYYY-MM-DD`. The **latest upstream release**, not the pinned one — an abandonment signal, refreshed when the pin is reviewed (`F2-R14`) |
| `describes` | string | ✔ | What it does *for the operator* (`F2-R1`) |
| `without_it` | string | ✔ | Consequence of its absence (`F2-R2`) |
| `reaches` | string | | Where this service's own requests go, in terms an operator would recognise. `""` means it reaches nothing — an answer, not an omission. Both this and `asks_for` or neither (`F2-R10`). |
| `asks_for` | string | | What it asks for there. Never blank, including for a service that reaches nothing (`F2-R10`). |
| `media_types` | array | | Which media types it handles; drives root-folder seeding. One or more of `tv`, `movies`, `music`, `books`, `comics`. |
| `provides` | array | | The capabilities this service provides, in the published [capability vocabulary](capability-vocabulary.md). A name the vocabulary does not carry fails validation, named (`ARCH-R110`). |
| `depends_on` | array | | **Same profile only.** Cross-profile entries fail validation (`B1-R14`). |
| `grants` | array | | Extra kernel capabilities granted to the container, e.g. `["NET_ADMIN"]`. Any entry beyond an allow-list fails validation. Spelled `capabilities` until `0.16.0`; that spelling is still accepted and always will be, because a rename is not a reason to refuse to read somebody's own stack description. |
| `host_managed` | bool | | `true` for native-mode Jellyfin — lifecycle is the OS's (`B2-R15`) |
| `memory_mib` | integer | | The memory it expects to need, in MiB. An estimate the stack declares, summed into a form's footprint and never shown as a measurement (`B1-R18`). |

### The media types, and why the set is written down here

`media_types` is what points a service at the part of the library it works on —
it drives root-folder seeding, so a service declaring `tv` is one lemonfiber can
seed with `/data/media/tv` without being told again.

The set is `tv`, `movies`, `music`, `books` and `comics`. It was, until now,
written down in exactly one place: the validator's own source. That is the shape
`F4-R14` objects to for declarations generally — a closed enumeration in
first-party code that something outside has to match without being able to read
it — and it had a concrete cost. A plugin serving comics had no term for what it
serves, so the one field that would have pointed it at `/data/media/comics` could
not be used, and the plugin was left to be aimed by hand on first run.

`comics` is therefore in the set although no bundled service declares it. A
vocabulary that only admits what is already bundled is one a plugin cannot
extend the library with, which is the opposite of what
[F3](../../10-functional/features/f-extensibility/f3-stack-manifests.md) is for.

### `provides` — what it can do, so wiring can ask rather than name

[`F9-R1`](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md)
puts a bundled service's capabilities in this manifest rather than in
lemonfiber's source, for `F1-R5`'s reason: a fork adding a service declares what
it can do the same way, with no code change. A plugin declares the same facts in
the same vocabulary, in `provides` on its own service — which is what makes
substitution a change of which service fills a capability rather than a rewrite
of everything that named one.

The names come from [`capability-vocabulary.json`](capability-vocabulary.md), and
that file is generated from **this field**: a capability no service here declares
fails the generation, which is how `F9-R3` — *a capability nothing implements
MUST NOT be published* — is enforced by the artefact refusing to be built.

Four bundled services declare nothing, and that is the answer rather than an
omission. Recyclarr writes quality profiles into other services' configuration
and Unpackerr watches the filesystem; Homepage and Caddy are configured by
lemonfiber writing a file rather than by anything asking them a question. A
capability is something one service asks another for while both are running, and
nothing asks these four — so there is nothing to stand in for.

### `reaches` and `asks_for` — the errand, where the errand is decided

The privacy inventory lists what leaves the machine, and most of what leaves it is
not lemonfiber's. An indexer query is Prowlarr asking an indexer; a poster is
Radarr asking a metadata provider. Those are the stack's errands, and the stack is
what knows them.

This pair used to be a table compiled into lemonfiber, keyed by service id. That
made the catalogue's prose version with the binary rather than with the stack that
carries it, which `F2-R10` forbids, and it meant a service added to a Compose
project could not be described until a lemonfiber release shipped — the one cost
`F1-R5` exists to refuse. Declaring it here is what makes both true at once.

Three consequences worth stating, because each is a case somebody will meet:

- **A service that declares neither is reported as one lemonfiber has no record
  of**, and listed rather than dropped. There is no compiled table left to answer
  for it. Saying nothing is honest; guessing, or leaving it out of an inventory
  that reads as complete, is not.
- **An empty `reaches` is the strongest claim here**, not a missing value. It says
  no request leaves the machine, which is why `asks_for` may not be blank beside
  it: a service that goes nowhere still says what it does instead.
- **Half the pair is none of it.** A destination with no purpose attached describes
  where without why, and "it talks to a metadata provider" and "it sends your
  library to a metadata provider" are the same destination and different decisions.

The pair is optional in the *format*, so an operator's own stack directory
(`F1-R3`) stays readable without it. It is not optional of a bundled service: the
stack this project ships declares it for every service, its own validation refuses
one that does not, and the lemonfiber build refuses a stack that leaves any service
silent. An inventory of what leaves a machine is only honest if a service cannot
arrive in it unlisted.

### `health`

```toml
health = { kind = "http", path = "/ping", timeout_s = 60 }
health = { kind = "tcp", timeout_s = 30 }
health = { kind = "container" }
```

`kind = "http"` is checked against `port` + `path`. Startup is health-gated, not
process-gated (`B2-R1`), so this is what "started" actually means.

### `api`

```toml
api = { kind = "servarr",  key_source = "config-xml", path = "/config/config.xml", version = 3 }
api = { kind = "sabnzbd",  key_source = "config-ini", path = "/config/sabnzbd.ini" }
api = { kind = "qbittorrent", key_source = "generated" }
api = { kind = "seerr",    key_source = "api-settings" }
api = { kind = "bindery",  key_source = "api-settings" }
api = { kind = "jellyfin", key_source = "generated" }
api = { kind = "bazarr",   key_source = "config-yaml", path = "/config/config/config.yaml" }
```

`kind` selects the client implementation. `servarr` covers Sonarr, Radarr, Lidarr
and Prowlarr, since they share an API shape — which is what makes one client
sufficient for four services. `bazarr` is its own, because it is told about the
\*arrs rather than being one of them, and it is told in a form body whose field
names are its configuration file's own paths flattened. `jellyfin` is the one media server lemonfiber sets
an account on rather than reading a key from, so its `key_source` is `generated`
like qBittorrent's — it mints the administrator password by driving Jellyfin's
own first-run setup.

`version` is the major version of the service's HTTP API, the `/api/vN` path
segment. It is **required for `servarr`** and read there, because that one shape
spans two versions — Sonarr and Radarr answer at `/api/v3`, Lidarr and Prowlarr
at `/api/v1` — so it is data the manifest carries rather than a guess the client
makes from a service's name. It is absent for the other kinds, whose one fixed
version their client already knows.

`key_source` says where the credential comes from:

| Value | Meaning |
|-------|---------|
| `config-xml`, `config-ini`, `config-json`, `config-yaml` | The service mints it and writes it to `path`; lemonfiber reads it |
| `api-settings` | Retrieved over the service's own API once authenticated |
| `generated` | The service offers nothing durable to read, so lemonfiber generates the credential, sets it, and records it for its consumers (`A7-R14`) |
| `none` | The API needs no credential at all |

The four file shapes are four shapes, not one with a guess: a reader that sniffed
the format would be right until a service changed it, and wrong silently. Which
file a service writes is a fact about that service, so the manifest says it.

`generated` exists because qBittorrent mints only a *temporary* WebUI password
and asks for it to be replaced. It also has a consumer that is not a service —
the VPN's forwarded-port push authenticates against the same WebUI API, so the
recorded value has to reach the stack's environment and not only lemonfiber's own
store.

**Bindery is deliberately its own kind.** It is not a Servarr application, and
Prowlarr's app sync does not cover it (`D1-R15`).

It also has no configuration file to read. Bindery keeps everything in SQLite and
issues a **per-account** API key, which exists only once first-run setup has
created an account — so the key is retrieved over its own API after
authenticating, and `path` does not apply.

## `[[wiring]]` — the link between two services, and which of them it names

```toml
[[wiring]]
by   = "seerr"
asks = "identity.source"

[[wiring]]
by   = "bazarr"
asks = "library.curate"
each = true

[[wiring]]
by        = "bindery"
asks      = "indexer.search"
filled_by = "prowlarr"
why       = "Two services here answer as an indexer and one of them has to be the one this asks."

[[wiring]]
by  = "qbittorrent"
to  = "gluetun"
why = "It has no network namespace of its own."
```

`provides` says what a service can do.
[`F4-R1`](../../10-functional/features/f-extensibility/f4-capabilities.md)'s
second clause is the other half, and it is this: **the wiring asks for a
capability rather than naming a service**.
[`F9-R4`](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md)
is that clause applied to the stack this project ships.

A wiring lived nowhere before this. It was a `depends_on` in this file, a URL in
a Compose fragment, and a service id in lemonfiber's own source — three places,
none of which said *what the link is for*, and all of which name a service. So a
reader asking "what reaches Jellyfin, and would anything else do?" had to read
the code, and the answer was always "Jellyfin, because it says Jellyfin".

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `by` | string | ✔ | The service whose wiring this is — what asked. A declared service. This is the name a capability nothing fills is reported against (`F4-R9`). |
| `asks` | string | | The capability asked for, in the published [vocabulary](capability-vocabulary.md). Exactly one of this and `to`. |
| `each` | bool | | `true` where the wiring reaches **every** service that fills the capability rather than the one that does. Only with `asks`. Default `false`. |
| `filled_by` | string | | Which claimant fills it, where the stack's own services contest it. Only with `asks`, never with `each`, and the named service must declare the capability. Requires `why`. |
| `to` | string | | The service named. The by-name exception (`F4-R12`). Exactly one of this and `asks`. Requires `why`. |
| `why` | string | | Why this is by name, or why this claimant was chosen. Never blank where it is required. |

### `each` — one filler, or all of them

Some asks are for the one service that does a thing and some are for all of
them. The subtitle finder watches *every* service that curates a library; the
request service signs in against *the* identity source. Both are honest asks and
they resolve differently, so the wiring says which it is rather than leaving a
reader to infer it from how many claimants happen to exist today.

Without it the difference would be invisible until it bit: four services declare
`library.curate`, so an ask that meant "the one" would be reported as contested
and refused (`F4-R8`), and an ask that meant "all of them" would be reported the
same way — one of those two is a wiring that works.

### `filled_by` — a choice, recorded, rather than a rule

Where two of the stack's own services claim one capability and a wiring asks for
one of them, somebody has to choose. `F4-R8` says who: not install order, not
precedence, not recency — an operator, and their choice is recorded.

`filled_by` is the stack making that choice for the stack it ships, in the file
the operator can read and with the reason beside it. It is a default, not a
rule: the operator substitutes by choosing another claimant, that change is
journalled like any other
([`F4-R10`](../../10-functional/features/f-extensibility/f4-capabilities.md)),
and it can be put back. A fork shipping different services makes its own choice
the same way.

It is `why`-bearing for the same reason `to` is. A choice with no reason beside
it is indistinguishable from a rule somebody encoded, which is the thing `F4-R8`
refuses.

### `to` — by name, and shown as by name

`F4-R12` keeps by-name wiring available and makes it visible as the exception it
is. `to` is that spelling: it names a service, it carries the reason, and
anything that lists the stack's wiring shows it as by-name rather than as an ask
that happened to resolve to one candidate.

**The stack has exactly one.** qBittorrent is inside Gluetun's network
namespace, and it is worth writing down why that is genuinely about one service
rather than an ask for `network.egress-guard` resolved late:

- What is shared is a **container's namespace**, not an errand. `network_mode:
  service:gluetun` makes two containers one network entity. There is no
  indirection for the sharing to pass through, and nothing to substitute *at*.
- The property this buys is that qBittorrent has **no network of its own**, so
  when the tunnel drops it loses connectivity rather than falling back to the
  home IP (`C2-R12`). That is a statement about those two containers, and an ask
  that resolved to a name at render time would state it no better while hiding
  the one relationship in this stack a reader most needs spelled out.
- It is not one link but four that have to agree: the shared namespace, the
  health-gated start order, the profile they share (`B1-R14`), and the port
  Gluetun publishes *on qBittorrent's behalf*. A capability is something one
  service asks another for while both are running; this is two containers being
  co-scheduled as one.

So it stays by name, it says why, and the exception is legible. Everything else
in the stack asks.

### What this does not cover

A wiring here is a link between two services in *this* stack. lemonfiber writes
the proxy and dashboard entries for a service from its tier and its description,
which is generation rather than wiring, and a plugin's service is wired on the
same terms ([`ARCH-R103`](plugin-manifest.md)). A plugin has no field by which it
could add a `[[wiring]]` of its own, and in particular none by which it could add
a by-name one — that is `F4-R12`'s third clause, and the plugin manifest's
[absent fields](plugin-manifest.md#the-fields-that-are-absent-and-why) are where
it is held.

## Validation

Validation reports **every** violation in one pass, each naming its location
(`F1-R9`). Reporting one error per run turns fixing a fork into a guessing game.

| Rule | Failure |
|------|---------|
| `schema_version` supported | Both versions named |
| Every `id` unique within its kind | Duplicate named |
| Every `service.profile` references a declared profile | Both named |
| Every `form.profiles` entry references a declared profile | Both named |
| Exactly one profile per service | Service named |
| No `depends_on` crossing a profile boundary | Service and target named (`B1-R14`) |
| `digest` present and well-formed | Service named (`E1-R1`) |
| `tag` is not `latest` or otherwise floating | Service named (`E1-R1`) |
| `bind` present when `port` is | Service named |
| `license` is a recognised OSI identifier | Service and licence named (`F2-R5`) |
| `last_release` is `YYYY-MM-DD` and not in the future | Service and value named (`F2-R14`) |
| `reaches` and `asks_for` declared together or not at all | Service and the declared half named (`F2-R10`) |
| `asks_for` is not blank where it is declared | Service named (`F2-R10`) |
| No service is silent about its errand in a manifest where another declares one | Every silent service named (`F2-R10`) |
| `memory_mib` above zero where it is declared | Service named (`B1-R18`) |
| `grants` within the allow-list | Service and kernel capability named |
| `protocol` is a permitted value | Profile and value named |
| At most one profile per `protocol` | Both profiles named |
| Every `wiring.by`, `wiring.to` and `wiring.filled_by` references a declared service | Wiring and the unknown id named (`F4-R1`) |
| Exactly one of `asks` and `to` on a wiring | Wiring named, and which of the two it has |
| `why` present and not blank where `to` or `filled_by` is | Wiring named (`F4-R12`) |
| `each` and `filled_by` only where `asks` is, and never together | Wiring and the field named |
| `filled_by` declares the capability it is chosen for | Wiring, service and capability named (`F4-R8`) |
| `wiring.asks` is a core capability name in shape | Wiring and the name named |
| No wiring names its own `by` as `to` or `filled_by` | Wiring named |
| No two wirings carry the same `by` and `asks`, or the same `by` and `to` | Both wirings named |
| Every `depends_on` edge is also declared as a by-name `[[wiring]]` | Service and target named (`F4-R12`, `F9-R4`) |
| Manifest services match `compose.yml` services exactly | Divergence listed both ways |

That last rule matters more than it looks: a manifest describing a service that
isn't in the compose file — or vice versa — is the most likely error when adding
one, and it fails in confusing ways at runtime.

## Worked example

The real stack, abridged to one service per profile. The full file lives in
`lemonfiber-media-stack`.

```toml
schema_version  = 1
stack_version   = "1.0.0"
min_cli_version = "0.4.0"

# ── Profiles ────────────────────────────────────────────────
[[profile]]
id = "search"
name = "Indexers"
description = "Finding things"

[[profile]]
id = "usenet"
name = "Usenet"
description = "Usenet downloading"
protocol = "usenet"

[[profile]]
id = "torrent"
name = "Torrents"
description = "Torrent downloading, VPN-isolated"
protocol = "torrent"

[[profile]]
id = "tv"
name = "Television"
description = "TV automation"

[[profile]]
id = "media"
name = "Library"
description = "Serving what you have"

# … movies, music, books, subs, tuning, dash, proxy

# ── Forms ───────────────────────────────────────────────────
[[form]]
id = "search"
name = "Search"
description = "Find things. Nothing else runs."
profiles = ["search"]

[[form]]
id = "dl"
name = "Download"
description = "You have a link — fetch it."
profiles = ["usenet", "torrent"]

[[form]]
id = "hunt"
name = "Hunt"
description = "Search and grab, manually."
profiles = ["search", "usenet", "torrent"]

[[form]]
id = "tv"
name = "TV"
description = "Search, download and automate television"
profiles = ["search", "usenet", "torrent", "tv", "subs"]

[[form]]
id = "library"
name = "Library"
description = "Serve what exists. Requires no third-party accounts."
profiles = ["media"]

[[form]]
id = "proxy"
name = "Proxy"
description = "Friendly hostnames. Layers onto any other form."
profiles = ["proxy"]

# … movies, music, books, auto, full

# ── Services ────────────────────────────────────────────────
[[service]]
id = "prowlarr"
name = "Prowlarr"
profile = "search"
image = "lscr.io/linuxserver/prowlarr"
tag = "2.5.2"
port = 9696
bind = "loopback"
health = { kind = "http", path = "/ping", timeout_s = 60 }
api = { kind = "servarr", key_source = "config-xml", path = "/config/config.xml" }
criticality = "core"
license = "GPL-3.0-only"
upstream = "https://github.com/Prowlarr/Prowlarr"
describes = "Holds your indexer accounts in one place and shares them with everything else"
without_it = "Every app needs indexers configured separately"

[[service]]
id = "gluetun"
name = "Gluetun"
profile = "torrent"
image = "qmcgaw/gluetun"
tag = "v3.40.0"
health = { kind = "container" }
criticality = "critical"
license = "MIT"
upstream = "https://github.com/qdm12/gluetun"
describes = "Routes torrent traffic through your VPN and blocks it if the VPN drops"
without_it = "Your home IP is visible to every peer"
grants = ["NET_ADMIN"]

[[service]]
id = "qbittorrent"
name = "qBittorrent"
profile = "torrent"
image = "lscr.io/linuxserver/qbittorrent"
tag = "5.0.3"
port = 8081
bind = "loopback"
health = { kind = "http", path = "/api/v2/app/version", timeout_s = 60 }
api = { kind = "qbittorrent", key_source = "generated" }
criticality = "core"
license = "GPL-2.0-only"
upstream = "https://github.com/qbittorrent/qBittorrent"
describes = "Downloads torrents"
without_it = "No torrent downloads"
depends_on = ["gluetun"]

[[service]]
id = "sonarr"
name = "Sonarr"
profile = "tv"
image = "lscr.io/linuxserver/sonarr"
tag = "4.0.15"
port = 8989
bind = "loopback"
health = { kind = "http", path = "/ping", timeout_s = 90 }
api = { kind = "servarr", key_source = "config-xml", path = "/config/config.xml" }
criticality = "core"
license = "GPL-3.0-only"
upstream = "https://github.com/Sonarr/Sonarr"
describes = "Watches for new episodes and fetches them"
without_it = "Find and download episodes yourself"
media_types = ["tv"]

[[service]]
id = "seerr"
name = "Seerr"
profile = "media"
image = "ghcr.io/seerr-team/seerr"
tag = "3.3.0"
port = 5055
bind = "lan"
health = { kind = "http", path = "/api/v1/status", timeout_s = 90 }
api = { kind = "seerr", key_source = "api-settings" }
criticality = "important"
license = "MIT"
upstream = "https://github.com/seerr-team/seerr"
describes = "Where the household asks for things"
without_it = "Requests come to you in person"

# ── Wiring ──────────────────────────────────────────────────
[[wiring]]
by   = "seerr"
asks = "identity.source"

[[wiring]]
by  = "qbittorrent"
to  = "gluetun"
why = "It has no network namespace of its own — it is inside this one container's."
```

Note `qbittorrent.depends_on = ["gluetun"]` — legal because both are in
`torrent`, and the single permitted cross-service dependency in the stack
(`B1-R14`). It is also the stack's only by-name wiring, and the `[[wiring]]`
entry above is where it says so.

Note `seerr.bind = "lan"` against everything else's `loopback` — the two-tier
policy expressed as data rather than as a rule someone has to remember.

## Compatibility

See [versioning](versioning.md).

## Related

- [ADR-0002 Profiles and forms](../../00-overview/decisions/0002-profiles-and-forms.md)
- [ADR-0005 Embedded stack assets](../../00-overview/decisions/0005-embedded-stack-assets.md)
- [B1 Forms](../../10-functional/features/b-running/b1-forms.md) · [F2 Service catalogue](../../10-functional/features/f-extensibility/f2-service-catalogue.md)
- [F4 The capability vocabulary](../../10-functional/features/f-extensibility/f4-capabilities.md) · [F9 Capabilities of the bundled services](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md) — what `provides` and `[[wiring]]` are for
- [capability-vocabulary.md](capability-vocabulary.md) — the names a wiring may ask for
- [component-model.md](../component-model.md) — where the manifest is parsed
