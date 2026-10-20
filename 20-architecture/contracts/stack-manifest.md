# Contract: `stack.toml`

**Status:** Accepted

The format of a whole stack: the form lemonfiber assembles the
[bundle](bundle.md) into, and the format of a stack directory an operator names with
`--stack-dir` in its place (`F1-R3`). lemonfiber knows nothing about Sonarr that isn't
declared in it.

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

## Its place beside the bundle

The stack lemonfiber ships is assembled from the bundle
([ADR-0045](../../00-overview/decisions/0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md)):
the profiles, forms, wiring and removed services are the bundle's, and each service is
the one service of a first-party plugin the bundle pins as `assembled`, declared in that
plugin's own manifest. lemonfiber assembles them into this format and materialises none
of it (`ARCH-R263`). A `--stack-dir` stack is written in this format by hand.

Either way a service is declared in the plugin manifest's service model
([ADR-0043](../../00-overview/decisions/0043-the-core-writes-every-compose-entry-from-one-typed-service-model.md)):
every field that describes a container is the plugin manifest's, with the same types and
the same validation, and lemonfiber generates each service's Compose entry from it, as it
does a plugin's. The stack carries no Compose file lemonfiber reads (`ARCH-R246`), so a
part moving from `assembled` to `installed` moves from one declaration in the model to
another.

Assembled, a service takes its `profile` and `last_release` from its `[[plugin]]` in the
bundle; `describes`, `without_it`, `license` and `upstream` from its plugin's
`description`, `without_it`, `license` and `upstream`; and every other field from its
plugin's one service. `host_managed` is this format's alone.

Assembled, a service also keeps every
[`[[secret]]`](plugin-manifest.md#secret-and-override--declared-before-they-are-held) its
plugin declares, held in the secret store under its own id (`gluetun:wireguard-key`), so
its `env` names its secrets as a plugin's does (`ARCH-R275`). A `--stack-dir` service
declares none: its file holds one `[[service]]` and nothing else (`ARCH-R264`), so an
`env` value there naming a secret is refused, naming the variable (`ARCH-R247`).

## File location

`stack.toml`, at the root of a stack directory an operator names with `--stack-dir`.
Each service is declared in a file of its own, `services/<id>.toml`, and `stack.toml`
names every one of those files in its `include` list (`ARCH-R264`). The stack lemonfiber
ships has no such directory: it is assembled from the bundle (`ARCH-R263`).

## Top-level structure

```toml
schema_version = 1
stack_version  = "1.0.0"
min_cli_version = "0.4.0"
include = ["services/sonarr.toml", "services/radarr.toml"]  # one per service

[[profile]]  # 12 of these
[[form]]     # 11 of these
[[wiring]]   # one per link between two services
[[removed]]  # one per service the catalogue no longer carries
```

Each file `include` names holds one `[[service]]`, with its `[[service.claim]]`
tables, and nothing else:

```toml
# services/sonarr.toml
[[service]]
id = "sonarr"
# …
```

## `include` — where each service is

The manifest is a root and a file per service, so that no file grows with the stack
and a service's whole description is read in one place. The root keeps what is about
more than one service — the profiles, the forms, the wiring between services and the
services the catalogue no longer carries — and `include` names each service's file,
in the order the manifest lists the services.

Membership is the list, never the directory. A file is part of the stack because
`include` names it, so a file left in `services/` that nothing names is refused rather
than read: a directory listing that decided membership would make a stray or a
half-deleted file a service.

The rules, each refused by name, every violation in one pass (`F1-R9`, `ARCH-R264`):

- An entry is a path relative to the stack root, of the form `services/<id>.toml`.
  Anything else — another directory, another extension, a `..` — names the entry.
- An entry names a file that exists. A missing one names the entry.
- No entry appears twice.
- Every `.toml` file in `services/` is named by an entry. One that is not names the
  file.
- A service file holds exactly one `[[service]]`, whose `id` is the `<id>` its file is
  named for, and no other top-level key. A file holding none, two, a mismatched `id`
  or a `[[profile]]` names the file and what it holds.
- `stack.toml` itself holds no `[[service]]`.

The format changes in place at `schema_version = 1`, because no release candidate has
shipped ([versioning](versioning.md#before-the-first-release-candidate)): the stack is
embedded, and the build refuses a stack its parser cannot read.

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

## `[[profile]]`, `[[form]]` and `[[removed]]`

A stack declares its profiles, its forms and the services its catalogue no longer
carries in the tables the [bundle](bundle.md) declares them in, with the same fields and
the same rules: [`[[profile]]`](bundle.md#profile), with `protocol` on a profile that
cannot run without a configured provider; [`[[form]]`](bundle.md#form), whose
`profiles` is the complete closure; and [`[[removed]]`](bundle.md#removed).

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
| `id` | string | ✔ | Unique. The name lemonfiber gives its Compose service. |
| `name` | string | ✔ | Human-facing |
| `profile` | string | ✔ | **Exactly one** (`B1-R1`). MUST reference a declared profile. Assembled, the one its `[[plugin]]` names. |
| `image` | string | ✔ | Without tag or digest |
| `digest` | string | ✔ | `sha256:…` of the multi-architecture index. What actually runs (`E1-R1`). |
| `tag` | string | ✔ | The human-readable version the digest corresponds to. Recorded and shown; never resolved at run time. |
| `port` | integer | | The port it is published at on the host: its primary UI/API port. Omitted for a service with no listener, and for one whose only listener is reached across internal networks and published nowhere, as the request gate's is ([ADR-0032](../../00-overview/decisions/0032-the-request-service-reaches-the-arrs-through-a-gate.md)). |
| `bind` | enum | ✔ if `port` | `loopback` \| `lan`. Enforces [C6](../../10-functional/features/c-trust/c6-web-security.md)'s two-tier policy. |
| `health` | table | | See below. Absent means lifecycle waits on container state only. |
| `api` | table | | How lemonfiber talks to it for [seeding](../../10-functional/features/d-content/d1-seed.md). Absent means no API integration. |
| `listens` | integer | ✔ if `api`, or where it answers on a port other than `port` | The port it answers on inside the container, where `port` is published to. Default `port`. See [`api`](#api). |
| `criticality` | enum | ✔ | `critical` \| `core` \| `important` \| `enhancing` \| `optional` (`F2-R3`) |
| `license` | string | ✔ | SPDX identifier. A non-OSI value fails validation (`F2-R5`, `F2-R12`), except on a service whose image lemonfiber builds from its own code, which carries `Hippocratic-3.0` and nothing else. Such a service is told by its `image`, under `ghcr.io/lemonfiber/`, where lemonfiber publishes the images it builds and nothing else ([ADR-0033](../../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md)), together with its `upstream`, under `https://github.com/lemonfiber/`. An upstream's image lemonfiber rebuilds is under `ghcr.io/lemonfiber/` too, and keeps its upstream's licence. |
| `upstream` | string | ✔ | Project URL, for maintenance review (`F2-R14`) |
| `last_release` | string | ✔ | `YYYY-MM-DD`. The **latest upstream release**, not the pinned one — an abandonment signal, refreshed when the pin is reviewed (`F2-R14`). Assembled, the one its `[[plugin]]` names. |
| `describes` | string | ✔ | What it does *for the operator* (`F2-R1`) |
| `without_it` | string | ✔ | Consequence of its absence (`F2-R2`) |
| `reaches` | string | | Where this service's own requests go, in terms an operator would recognise. `""` means it reaches nothing — an answer, not an omission. Both this and `asks_for` or neither (`F2-R10`). |
| `asks_for` | string | | What it asks for there. Never blank, including for a service that reaches nothing (`F2-R10`). |
| `media_types` | array | | Which media types it handles; drives root-folder seeding. One or more of `tv`, `movies`, `music`, `books`, `comics`. |
| `provides` | array | | The capabilities this service provides, in the published [capability vocabulary](capability-vocabulary.md). A name the vocabulary does not carry fails validation, named (`ARCH-R110`). |
| `claim` | array of tables | ✔ if `provides` | One per capability in `provides`: the probes that demonstrate it, each bound to a request on this service and a recorded response. See [`[[service.claim]]`](#serviceclaim--the-evidence-for-what-it-provides) (`ARCH-R136`). |
| `host_managed` | bool | | `true` for native-mode Jellyfin — lifecycle is the OS's (`B2-R15`), and lemonfiber writes it no Compose entry |
| `memory_mib` | integer | | The memory it expects to need, in MiB. An estimate the stack declares, summed into a form's footprint and never shown as a measurement (`B1-R18`). |
| `publish`, `takes_data`, `config_path`, `config_ro`, `mount`, `tmpfs`, `env`, `user_mode`, `posture`, `mem_limit_mib`, `network`, `shape` | | | The rest of its container, each as the [plugin manifest](plugin-manifest.md#service--what-runs) declares it (`ARCH-R225`). |

`grants` and `depends_on` are not fields. A service needing a kernel capability or a
device takes a [shape](plugin-manifest-service.md#shapes--the-only-route-to-a-device-or-a-privilege),
and the one start-order edge the format writes is
[`network.via`](plugin-manifest-service.md#inside-another-services-network--networkvia)'s.

Both spellings of the old field, `grants` and the `capabilities` it was called until
`0.16.0`, are still read, and then refused, naming for each grant the shape that replaces
it (`NET_ADMIN` is `egress-guard`'s). This contract once said the `capabilities` spelling
was accepted and always would be, because a rename was no reason to refuse somebody's
own stack description. [ADR-0043](../../00-overview/decisions/0043-the-core-writes-every-compose-entry-from-one-typed-service-model.md)
supersedes that sentence: a kernel capability named in a manifest is now reach the model
refuses, not a spelling, and reading the field is what lets the refusal say what to write
instead. `depends_on` is read and refused the same way, naming `network.via`
(`ARCH-R246`).

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

Every bundled part provides a capability, so every part has a slot a substitute can
fill (`F14-R8`). The parts lemonfiber configures rather than another service queries
provide one too: Recyclarr `quality.sync`, Unpackerr `archive.extract`, Homepage
`dashboard.show` and Caddy `proxy.front`, with the stream guard, the decline service
and the request gate providing `stream.guard`, `invite.decline` and `request.gate`
([ADR-0041](../../00-overview/decisions/0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md)
§6).

### `[[service.claim]]` — the evidence for what it provides

`provides` is a declaration. A claim is the evidence for it, in exactly the shape a
plugin's [`[[claim]]`](plugin-manifest.md#claim--the-probes-a-core-name-is-demonstrated-by)
takes, so a bundled service and a plugin standing in for it are held to one contract
by one reader:

```toml
[[service]]
id       = "jellyfin"
provides = ["media.serve", "identity.source"]

[[service.claim]]
capability = "media.serve"

[[service.claim.probe]]
id      = "guarded"
request = { method = "GET", path = "/Items" }
expect  = { status = 401 }
fixture = "recordings/jellyfin/media-serve-guarded.json"

[[service.claim.probe]]
id      = "catalogue"
request = { method = "GET", path = "/Items" }
expect  = { status = 200, json_has_keys = ["Items", "TotalRecordCount"] }
fixture = "recordings/jellyfin/media-serve-catalogue.json"
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `capability` | string | ✔ | A capability in this service's `provides` |
| `probe[].id` | string | ✔ | Names a probe the capability declares. Every one of them, exactly once. |
| `probe[].request` | table | ✔ unless `run` | `method`, `path`, and optionally `accept`, on this service. As a plugin's [request](plugin-manifest.md#what-a-request-may-ask-for). |
| `probe[].run` | table | ✔ for a run probe | As a plugin's [`probe[].run`](plugin-manifest.md#claim--the-probes-a-core-name-is-demonstrated-by), where the vocabulary declares the probe a run. |
| `probe[].expect` | table | ✔ | What the answer must be, within what the probe permits. |
| `probe[].fixture` | string | ✔ | The recorded response, under `recordings/<service id>/` in the stack directory. |

**The binding rules are the plugin's, unchanged** (`ARCH-R109`): every probe the
capability declares is bound, no binding names a probe it does not declare, every
expectation is one the probe permits, and each is refused by naming the probe. A
recording is the file a plugin's is, [one response recorded from the pinned
image](plugin-manifest-proof.md#what-a-recording-is) (`ARCH-R120`), and its
`recorded_from` MUST name this service's own `image@digest`. Moving a pin therefore
means re-recording in the same change: a recording naming another digest is refused
rather than trusted.

**Every bundled claim is judged against its recordings before a release is tagged**
(`ARCH-R137`), in the stack repository's CI on every change and in lemonfiber's
release gate against the stack it embeds. A probe the recording refutes refuses the
change and the tag, naming the service, the capability and the probe; that is
`F9-R5`'s *no gentler treatment for being bundled*, because a plugin's claim failing
the same probe is refused the same way. A probe that cannot be judged — its
recording absent, unreadable, or of another request — is reported unproven, naming
the recording, and is never counted as demonstrated (`ARCH-R122`).

A claim with no capability in `provides` to answer is refused. A claim of
`quality.sync` binds its probe with `run`, the one capability whose probe is a run
([capability vocabulary](capability-vocabulary.md#a-probe-is-a-request-unless-the-capabilitys-fillers-listen-on-nothing)).

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
(`F1-R3`) stays readable without it. It is not optional of a bundled service: every
first-party plugin declares it on every service (`ARCH-R270`), the bundle's validation
refuses a pinned plugin that does not, and the lemonfiber build refuses a stack that
leaves any service silent. An inventory of what leaves a machine is only honest if a
service cannot arrive in it unlisted.

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

`listens` is where lemonfiber and the services that ask reach it: the port the
service answers on inside the stack's network, which is not always the one it
publishes. SABnzbd publishes 8085 and answers on 8080. Without it the inside
port is a constant in lemonfiber's source, and a service standing in for one that
listens elsewhere would be registered at a port it does not answer on
(`ARCH-R144`).

**Bindery is deliberately its own kind.** It is not a Servarr application, and
Prowlarr's app sync does not cover it (`D1-R15`).

It also has no configuration file to read. Bindery keeps everything in SQLite and
issues a **per-account** API key, which exists only once first-run setup has
created an account — so the key is retrieved over its own API after
authenticating, and `path` does not apply.

## `[[wiring]]` — the link between two services, and which of them it names

A stack's `[[wiring]]` takes the two shapes the bundle's
[`[[wiring]]`](bundle.md#wiring--a-choice-of-filler-or-a-link-by-name) takes, a choice
of filler and a link by name, and in this format a third: the ask, `by` and `asks`
with `each` where it reaches every filler, which in the bundle is the asking plugin's
own [`[[ask]]`](plugin-manifest.md#ask--what-a-plugins-service-asks-for). Assembled, every
`[[ask]]` of an `assembled` part is a wiring of that shape here.

```toml
[[wiring]]
by   = "seerr"
asks = "identity.source"

[[wiring]]
by   = "bazarr"
asks = "library.curate"
each = true

[[wiring]]
by   = "prowlarr"
asks = "indexer.proxy"

[[wiring]]
by   = "bindery"
asks = "download.usenet"

[[wiring]]
by   = "bindery"
asks = "download.torrent"

[[wiring]]
by        = "bindery"
asks      = "indexer.search"
filled_by = "prowlarr"
why       = "Two services here answer as an indexer and one of them has to be the one this asks."

[[wiring]]
by  = "decline"
to  = "jellyfin"
why = "It makes three of Jellyfin's own calls, with a key lemonfiber minted for it alone."
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

### `filled_by` and `to`

A choice of filler and a link by name mean here what they mean in the bundle:
[`filled_by`](bundle.md#filled_by--a-choice-recorded-rather-than-a-rule) is the stack's
default for a contested ask, which the operator's choice overrides and which carries
its reason, and [`to`](bundle.md#to--by-name-and-shown-as-by-name) is the by-name
exception, shown as one. A fork shipping different services makes its own choices the
same way.

### What this does not cover

A wiring here is a link between two services in *this* stack. lemonfiber writes
the proxy and dashboard entries for a service from its tier and its description,
which is generation rather than wiring, and a plugin's service is wired on the
same terms ([`ARCH-R103`](plugin-manifest.md)). A plugin has no field by which it
could add a `[[wiring]]` of its own, and in particular none by which it could add
a by-name one — that is `F4-R12`'s third clause, and the plugin manifest's
[absent fields](plugin-manifest-service.md#the-fields-that-are-absent-and-why) are where
it is held.

## Validation

Validation reports **every** violation in one pass, each naming its location
(`F1-R9`). Reporting one error per run turns fixing a fork into a guessing game.

| Rule | Failure |
|------|---------|
| `schema_version` supported | Both versions named |
| Every `include` entry is `services/<id>.toml`, names a file that exists, and appears once | Entry named (`ARCH-R264`) |
| Every `.toml` file in `services/` is named by `include` | File named (`ARCH-R264`) |
| A service file holds one `[[service]]` whose `id` matches its file name, and nothing else | File and what it holds named (`ARCH-R264`) |
| `stack.toml` holds no `[[service]]` | Each one named (`ARCH-R264`) |
| Every `id` unique within its kind | Duplicate named |
| Every `service.profile` references a declared profile | Both named |
| Every `form.profiles` entry references a declared profile | Both named |
| Exactly one profile per service | Service named |
| No `grants`, `capabilities` or `depends_on` | Service and field named, with the shape or field that replaces it (`ARCH-R246`) |
| Every container field is held to the plugin manifest's [validation](plugin-manifest.md#validation) | As that table names (`ARCH-R225`) |
| `digest` present and well-formed | Service named (`E1-R1`) |
| `tag` is not `latest` or otherwise floating | Service named (`E1-R1`) |
| `bind` present when `port` is | Service named |
| `license` is a recognised OSI identifier, or `Hippocratic-3.0` where `image` is under `ghcr.io/lemonfiber/` and `upstream` under `https://github.com/lemonfiber/` — and only `Hippocratic-3.0` there | Service and licence named (`F2-R5`) |
| `last_release` is `YYYY-MM-DD` and not in the future | Service and value named (`F2-R14`) |
| `reaches` and `asks_for` declared together or not at all | Service and the declared half named (`F2-R10`) |
| `asks_for` is not blank where it is declared | Service named (`F2-R10`) |
| No service is silent about its errand in a manifest where another declares one | Every silent service named (`F2-R10`) |
| `memory_mib` above zero where it is declared | Service named (`B1-R18`) |
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
| Every service with an `api` declares `listens` | Service named (`ARCH-R144`) |
| Every capability in `provides` has exactly one `[[service.claim]]` | Service and capability named (`ARCH-R136`) |
| Every `[[service.claim]]` names a capability in the service's `provides` | Service and capability named (`ARCH-R136`) |
| Every probe a claimed capability declares is bound, and no binding names one it does not declare | Service, capability and probe named (`ARCH-R109`) |
| A binding's expectation is one the probe permits | Service, probe and constraint named (`ARCH-R109`) |
| Every `fixture` is under `recordings/<service id>/` and names a recording that exists | Service and path named (`ARCH-R136`) |
| Every recording's `recorded_from` is the service's own `image@digest` | Service, recording and both images named (`ARCH-R136`) |

## Published schemas

Each release of lemonfiber carries a JSON schema of the bundle,
`contract/bundle.schema.json`, and, for as long as it reads a `--stack-dir` stack, one
of the root manifest, `contract/stack-manifest.schema.json`, and one of a service's
file, `contract/stack-service.schema.json`, each generated from the types lemonfiber
reads them into, so an editor or a fork's CI can check a manifest without the binary.
A `[[service.claim]]` is the plugin manifest's `[[claim]]`, so the service schema takes
its definition from the plugin manifest's rather than restating it (`ARCH-R172`).

## Worked example

The real stack, abridged to one service per profile. The root comes first and each
service file follows it, headed by its path. The full stack lives in
`lemonfiber-media-stack`.

```toml
schema_version  = 1
stack_version   = "1.0.0"
min_cli_version = "0.4.0"
include = [
  "services/prowlarr.toml",
  "services/gluetun.toml",
  "services/qbittorrent.toml",
  "services/sonarr.toml",
  "services/seerr.toml",
]

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

# ── Wiring ──────────────────────────────────────────────────
[[wiring]]
by   = "seerr"
asks = "identity.source"

[[wiring]]
by  = "decline"
to  = "jellyfin"
why = "It makes three of Jellyfin's own calls, with a key lemonfiber minted for it alone."
```

```toml
# services/prowlarr.toml
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
```

```toml
# services/gluetun.toml
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
provides = ["network.egress-guard"]
shape = "egress-guard"
```

```toml
# services/qbittorrent.toml
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
takes_data = true
user_mode = "puid-env"
network = { via = "network.egress-guard" }
```

```toml
# services/sonarr.toml
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
```

```toml
# services/seerr.toml
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
```

Note `qbittorrent.network`: it asks for whatever fills `network.egress-guard` and
runs inside it, and lemonfiber writes that as the shared namespace, the start that
waits for the guard to be healthy, and the guard publishing 8081 on qBittorrent's
behalf. Both are in `torrent`, so the start-order edge stays inside one profile
(`B1-R14`).

Note `seerr.bind = "lan"` against everything else's `loopback` — the two-tier
policy expressed as data rather than as a rule someone has to remember.

## Compatibility

See [versioning](versioning.md).

## Requirements

| ID | Requirement |
|----|-------------|
| **ARCH-R171** | *Superseded by [ARCH-R263](bundle.md) and [ARCH-R264](stack-manifest.md): the stack lemonfiber ships is assembled from the bundle and carries no `include` list or service file, and the `include` layout is a `--stack-dir` stack's. The number is not reused.* |
| **ARCH-R172** | lemonfiber MUST publish, with each release, a JSON schema of the bundle (`contract/bundle.schema.json`) and, for as long as it reads a `--stack-dir` stack, JSON schemas of the root manifest (`contract/stack-manifest.schema.json`) and of a service's file (`contract/stack-service.schema.json`), each generated from the types it reads them into; the service schema's definition of a claim MUST be the plugin manifest's own. |
| **ARCH-R246** | A stack service MUST be declared in the plugin manifest's service model, a bundled part's in the manifest of the first-party plugin the bundle pins and a `--stack-dir` stack's in its service file, with the fields only a stack carries beside it, and a stack MUST carry no Compose file lemonfiber reads; lemonfiber MUST still read `grants`, `capabilities` and `depends_on` and MUST refuse each, naming for every grant the shape that replaces it and for `depends_on` `network.via`. |
| **ARCH-R264** | A stack manifest read from a directory named with `--stack-dir` MUST declare each service in a file of its own, `services/<id>.toml`, named by the root manifest's `include` list, which alone decides membership. lemonfiber MUST refuse, naming it, an entry that is not of that form, names no file, or appears twice; a file in `services/` no entry names; a service file holding anything but one `[[service]]` whose `id` matches its name; and a `[[service]]` in the root manifest. |

## Related

- [bundle](bundle.md) — what the stack lemonfiber ships is assembled from: the profiles, forms, wiring and each part, pinned
- [ADR-0002 Profiles and forms](../../00-overview/decisions/0002-profiles-and-forms.md)
- [ADR-0005 Embedded stack assets](../../00-overview/decisions/0005-embedded-stack-assets.md)
- [B1 Forms](../../10-functional/features/b-running/b1-forms.md) · [F2 Service catalogue](../../10-functional/features/f-extensibility/f2-service-catalogue.md)
- [F4 The capability vocabulary](../../10-functional/features/f-extensibility/f4-capabilities.md) · [F9 Capabilities of the bundled services](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md) — what `provides` and `[[wiring]]` are for
- [capability-vocabulary.md](capability-vocabulary.md) — the names a wiring may ask for
- [component-model.md](../component-model.md) — where the manifest is parsed
