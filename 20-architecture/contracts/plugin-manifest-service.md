# Contract: `plugin.toml` — `[[service]]`

**Status:** Accepted

Part of the [`plugin.toml` contract](plugin-manifest.md): each service a plugin runs,
declared field by field. The requirements this page describes are listed with the rest
of the contract's, under [Requirements](plugin-manifest.md#requirements).

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
| `criticality` | enum | ✔ | As `stack.toml`. `critical` only with `shape = "egress-guard"` — see below. |
| `reaches` | string | | Where this service's own requests go, as `stack.toml` declares it. Both this and `asks_for` or neither; a first-party plugin's service declares both (`F2-R10`, `ARCH-R270`). |
| `asks_for` | string | | What it asks for there, as `stack.toml` declares it. Never blank (`ARCH-R270`). |
| `media_types` | array | | Which media types it handles, in `stack.toml`'s vocabulary. Drives root-folder seeding, which is how a plugin's service is pointed at the library the stack already fills. |
| `takes_data` | bool | | `true` if it needs the data root mounted at `/data`, from the operator's [storage setting](plugin-manifest.md#the-data-root--one-setting-every-data-mount). Default `false`. |
| `provides` | array | | The capabilities this service claims (`F4-R1`). Core names from the published vocabulary; a plugin's own MUST be namespaced (`F4-R4`). At most one service of a plugin may declare a given core name — see below. |
| `config_path` | string | | Where inside the container its configuration directory is mounted. Default `/config`. |
| `config_ro` | bool | | `true` to mount the configuration directory read-only. Default `false`. |
| `shares_config` | string | | Only where it `fronts`: an absolute path inside this adapter where the whole configuration directory of the service it fronts is mounted, so it writes that service's own files — see [`shares_config`](#shares_config--an-adapter-writing-its-upstreams-files) (`ARCH-R339`). |
| `rebuilt` | array | | Relative paths beneath its configuration directory it rebuilds when missing, a cache or a log, which every backup leaves out — see [`rebuilt`](#rebuilt--what-a-backup-leaves-out) (`ARCH-R338`). |
| `mount` | array of tables | | Each further path mounted from its own mount tree, `./mounts/<id>`, which lies apart from its configuration directory: `from` (✔), `to` (✔) and `ro` (default `false`) — see [mounts](#mounts--from-its-own-tree-and-nowhere-else). |
| `tmpfs` | array | | Absolute paths given scratch space in memory, empty whenever the container starts. |
| `env` | table | | Its environment: a variable's name to one of four typed kinds of value — see [environment](#environment--four-kinds-of-value). |
| `user_mode` | enum | | `image` \| `puid-env` \| `uid`. Who the container runs as. Default `image`, and `uid` where the service speaks a contract or is `confined` — see [who it runs as](#who-it-runs-as-and-how-tightly-it-is-held). |
| `posture` | enum | | `standard` \| `confined`. How tightly the container is held, as declared. Default `standard`. `confined` only where the plugin's own CI runs the image under it. |
| `memory_mib` | integer | | The memory it expects to need, in MiB. An estimate, summed into a form's footprint (`B1-R18`) and never written as a limit. |
| `mem_limit_mib` | integer | | The most memory the container may hold, in MiB, written as its limit. |
| `network` | table | | `{ via = "<capability>" }`: it runs inside the network of the service that fills that capability, and has none of its own — see [`network.via`](#inside-another-services-network--networkvia). |
| `listens` | integer | ✔ if `speaks`, or where it answers on a port other than `port` | The port it answers on inside the container: where `port` is published to, and where lemonfiber, the services that ask and the proxy reach it. Default `port`. |
| `speaks` | array | | Each capability contract the service answers as an adapter, written `capability@major` from `contract/capabilities/index.json` (`ARCH-R200`). A service that speaks a contract is asked over it, and no other way. See [capability-contracts.md](capability-contracts.md). |
| `upstream` | table | | Only where it `speaks`: each field of the `upstream.json` lemonfiber writes for this adapter, to `{ secret = "<id>" }` naming a secret the plugin holds, usually one it [mints](plugin-manifest-secret.md#secret-and-override--declared-before-they-are-held) (`ARCH-R317`). |
| `fronts` | string | ✔ if `speaks` | The plugin's own service this adapter stands in front of: the upstream it answers its contracts for. It names another service of the same plugin, one that speaks no contract, and its conformance recordings are taken against the digest that service is pinned by. |
| `native` | string | | The API this service answers the stack's other services in, by the name those services know it by (`jellyfin`, `plex`, `emby`). Declared on the upstream an adapter `fronts`, where other services reach that upstream directly rather than through the adapter: a request service is set up against a media server in the media server's native API (`F14-R26`, `ARCH-R221`). |
| `replaces` | string | | An id the [bundle reserves](bundle.md#the-reserved-register), of the service this service moves in place of: the same container name, configuration directory and data, so an install moves the bundled service rather than running beside it ([ADR-0042](../../00-overview/decisions/0042-the-bundle-is-first-party-plugins-pinned-and-embedded.md) §4). It names the service's own id, and only that service may take the reserved id, port and hostname (`ARCH-R222`). Only a first-party plugin's install honours it (`F14-R29`), and the service keeps the stack's setting, secret and credential names for that id, so the move migrates none (`ARCH-R273`). |
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

What a service reaches of the host is fixed: the single data mount, the service's own
configuration directory, and its own mount tree (`ARCH-R227`). That is what makes
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

### `shares_config` — an adapter writing its upstream's files

Some upstreams are configured only through files they read, with no API to set what the
core applies: a dashboard's layout, a request service's settings. The adapter in front
of one answers its contract by writing those files, so it needs the upstream's
configuration directory, and only that:

```toml
[[service]]
id            = "homepage-adapter"
fronts        = "homepage"
speaks        = ["dashboard.show@1"]
shares_config = "/upstream"
```

- **The whole directory, never a part of it.** lemonfiber mounts the configuration
  directory of the service `fronts` names, which lemonfiber made and no container can
  replace. A path inside it would be a source the upstream could swap for a link, which
  the engine follows each time it mounts, at boot with nothing of lemonfiber's running.
- **Its own upstream alone.** Only a service that `fronts` may declare it, and it shares
  the directory of that service, which is the same plugin's. Any other service declaring
  it is refused naming the field.
- **Held to what is declared.** The path is absolute, not `/`, not within `/data`, and no
  other mount's target. lemonfiber writes that one mount and no other into the
  upstream's directory, and the reading of an install or update says the adapter writes
  its upstream's files.

The adapter runs as the operator's uid (`F14-R27`), which is who owns the directory, so
nothing beyond the mount is granted for it.

### `rebuilt` — what a backup leaves out

A cache, a scratch area and a log are no part of what breaks, and they are the bulk of a
configuration directory: a media server's cache alone grows to tens of gigabytes. A
service names the paths it rebuilds when they are missing, each relative to its
configuration directory, and every backup leaves them out:

```toml
[[service]]
id      = "jellyfin"
rebuilt = ["cache", "log"]
```

Each is a relative path with no `..` and no interpolation, refused naming the path
otherwise. A path the service does not hold is skipped, and nothing beneath the
configuration directory is left out unless a manifest names it.

### Mounts — from its own tree, and nowhere else

A second path beside the first — Jellyfin's `/cache`, Audiobookshelf's `/metadata` —
is a mount whose source lies in the service's own mount tree, a directory lemonfiber
keeps beside its configuration directory rather than inside it:

```toml
[[service.mount]]
from = "cache"
to   = "/cache"

[[service.mount]]
from = "Caddyfile"
to   = "/etc/caddy/Caddyfile"
ro   = true
```

`from` is a relative path inside the service's own mount tree, a file or a directory,
and lemonfiber writes it as `./mounts/<id>/<from>`. An absolute path, a `..` or an
interpolation is refused, naming the mount, and so is a source lying inside another of
the service's sources. `to` is an absolute path and not `/`; on a service that takes data
it lies outside `/data`; and no two of the service's mounts share a target. So a further
mount widens nothing a reader has to judge: it is a place lemonfiber gave the service,
landing where the image reads it.

The tree is apart from the configuration directory because a container writes its
configuration directory. A source inside it would be a path the container could replace
with a link, and the engine follows a link whenever it mounts, including when it
restarts the container itself after the machine boots, when nothing of lemonfiber's runs
first. A source in a tree no container sees, except through that one mount, is a path no
container can change; and because no source lies inside another, what a container
writes through one mount never reaches the path of the next.

`tmpfs` reaches nothing of the host at all, and its targets are held to the same rules.
It is scratch space in memory, empty whenever the container starts and writable by
whoever the container runs as. The door keeps its working files there, so nothing it
writes outlives it.

**A service's state lives under its own two directories and nowhere else** (`ARCH-R228`).
There is no volume the engine keeps on a service's behalf: state somewhere the operator
cannot see is state a backup, a move and the question "what can this reach" all miss.
The proxy keeps its certificates and its own state in two such volumes today
(`caddy_data`, `caddy_config`), so the in-place move copies each into the proxy's
mount tree once, mounts them from there, and leaves the volumes as they were, so that
undoing the move finds them.

There is no field by which a mount reaches any other path on the host, but the one by
which an adapter shares its upstream's directory ([`shares_config`](#shares_config--an-adapter-writing-its-upstreams-files)). In particular
there is none for the engine's socket, which is root on the host, for a first-party
service as for anybody else's (`ARCH-R239`).

### Starting files — what it starts with

An image often needs a file before its first start that it would not write for itself: a
download client's settings with its folders already set, a quality sync's guides, a
dashboard's layout, the proxy's routes. A plugin ships such files in its own source,
under `config/<service id>/`, and lemonfiber writes each into that service's
configuration directory at the same relative path (`ARCH-R271`):

```
plugin-sabnzbd/
├── plugin.toml
└── config/
    └── sabnzbd/
        └── sabnzbd.ini      written to ./config/sabnzbd/sabnzbd.ini
```

- **Materialised, as every file lemonfiber writes for a stack is.** Each is recorded by
  content, and one the operator has changed is never overwritten without a diff and
  confirmation (`F1-R4`).
- **Bounded.** At most 64 files and 1 MiB in all per service. A starting file is
  configuration a reviewer reads, not a payload.
- **No symbolic link,** anywhere in the tree, and no path outside `config/<id>/` of a
  service the plugin declares. A link would be a write to wherever it points, decided by
  the plugin and followed on the operator's machine.

Any plugin may ship them, first-party or not: a substitute that needs a starting file
stands in for a part that has one on the same terms.

#### A secret in a starting file

An upstream that reads its key from its own settings file is given it there. A starting
file names a secret the plugin holds as `{{secret:<id>}}`, and lemonfiber writes the
value in its place; `{{secret:<id>|pbkdf2}}` writes the salted PBKDF2-HMAC-SHA512 form a
service that keeps only a hash of its password reads, as `@ByteArray(<salt>:<hash>)`
(`ARCH-R316`):

```ini
# config/sabnzbd/sabnzbd.ini
api_key = {{secret:upstream-key}}
```

- **Only the plugin's own.** A placeholder names a `[[secret]]` whose `of` is one of the
  plugin's own services. A credential that crosses is another service's and stays out
  of this plugin's files.
- **Held as a secret is.** A file holding one is readable by the service's owner alone,
  and it is recorded, diffed and shown with the placeholder where the value is.
- **Text, and one syntax.** A file with a placeholder is UTF-8, and any other form, or a
  secret the manifest does not declare, is refused naming the file and the placeholder.
- **A few, and only through no link.** A service's files hold at most 16 placeholders in
  all: each is written at install and again whenever its secret is replaced, and the
  hashed form is a hundred thousand rounds. A file holding one is written only where no
  link stands on the way to it, since the directory is one the container writes.
- **Replaced where it stands.** The service rewrites its own settings once it runs, so a
  replaced secret is not written from the template again. lemonfiber keeps the files as
  shipped, finds the line a placeholder is on by the text around it, and replaces the
  value there alone, keeping everything the service wrote; a file where that line is gone
  is refused by name, and the old value stays in force (`ARCH-R318`).

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
| `{ setting = "<name>", default = <constant> }`, with `recorded_with` where only the operator holds it and `was` where an earlier release kept it in the stack's environment file | The operator's value for that setting, or the default where none is recorded |
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

**A value only the operator holds is stood in for when recorded.** A setting or secret a
service needs to start or pass its health check, which lemonfiber cannot mint and only
the operator can supply, declares `recorded_with`: the stand-in `lemonfiber plugin
record` gives it in the operator's place. It is a constant that reaches no third party,
such as an address from a documentation range or the provider a service names `custom`,
or `minted`, 32 random bytes made for that run alone and written in base64. The recorder
runs the service with those stand-ins and never with an operator's value, and grants it
what its `shape` grants as lemonfiber runs it, so CI holds it to starting under its
posture, passing its health check and answering its probes, and skips nothing
(`REPO-R93`). Every recording taken that way says so in its note (`ARCH-R336`). The egress
guard dials a tunnel at a documentation address with keys made for the run; the tunnel
never comes up, and the guard still starts and answers what it is asked:

```toml
[service.env]
VPN_SERVICE_PROVIDER    = { setting = "gluetun:provider", default = "", recorded_with = "custom" }
WIREGUARD_ENDPOINT_IP   = { setting = "gluetun:endpoint-ip", default = "", recorded_with = "192.0.2.1" }
WIREGUARD_ENDPOINT_PORT = { setting = "gluetun:endpoint-port", default = "", recorded_with = "51820" }
WIREGUARD_PUBLIC_KEY    = { setting = "gluetun:endpoint-key", default = "", recorded_with = "minted" }
WIREGUARD_ADDRESSES     = { setting = "gluetun:addresses", default = "", recorded_with = "10.64.0.2/32" }
WIREGUARD_PRIVATE_KEY   = { secret = "wireguard-key" }

[[secret]]
id            = "wireguard-key"
of            = "gluetun"
why           = "Dial the tunnel to your VPN provider, which knows this machine by the key"
recorded_with = "minted"
```

Settings live in the core's settings store, and the operator reads and changes them from
the command line, the web surface and the companion's operator screens alike, through
`lemonfiber settings` and [`GET /api/settings`](web-api.md#settings). Each change
is journalled and regenerates the entries that read it. A secret lives in the secret
store, never in the settings store (`ARCH-R248`). Neither is the stack's environment
file: the first run of the release that stops reading the stack's static Compose files
reads that file once, files every value the assembled parts and the published settings
read from it under their setting or secret, journals each, and lemonfiber does not read
the file for them again. A part's later move in place keeps those names (`ARCH-R273`),
so it migrates nothing. The file stays the one `lemonfiber config` reads and writes, for
lemonfiber's own keys such as `DATA_ROOT` and `PUID` (`ARCH-R249`).

**A setting names the key it was.** That filing reads each value from the key the
manifest names in its `was`, never from a list the core keeps: `{ setting =
"gluetun:countries", default = "Netherlands", was = "VPN_COUNTRIES" }` is filed from
`VPN_COUNTRIES`, and a [`[[secret]]`](plugin-manifest-secret.md#secret-and-override--declared-before-they-are-held)
declares its `was` the same way. `was` is a variable's name, held to the rules a
variable's name is, and two settings or secrets naming one key, across the stack and
every installed plugin, are refused naming both (`ARCH-R337`).

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
[`[[secret]]`](plugin-manifest-secret.md#secret-and-override--declared-before-they-are-held) the manifest
declares: a value lemonfiber mints, one the operator enters, one its recipe captures,
or a credential `F14-R18` or `F14-R20` lets cross to it. lemonfiber writes it to an environment file of
the service's own, readable by the owner alone (`0600`), names that file in the entry,
and never writes the value into the project. Every rehearsal, reading and diagnostic
shows the variable and the secret's name, never its value (`ARCH-R247`). A crossing
credential is read from where it is held whenever the entry is written, never copied
(`ARCH-R277`), and the journal keeps a secret's fingerprint, never its value
(`ARCH-R276`).

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
made. A bundled part's images are run so by its own repository's CI wherever a change
moves an image, its digest, its posture, its environment or its user (`REPO-R93`).
lemonfiber writes the posture declared and refuses nothing at run
time on account of it (`ARCH-R250`).

**`standard` binds no port below 1024.** None of its six capabilities is
`NET_BIND_SERVICE`, so a service that answers on a low port listens above 1024 and
publishes the low port to it. The proxy listens on 8080 and 8443 and publishes 80 and
443 to them, and its Caddyfile names both (`http_port`, `https_port`). An image whose
binary carries a file capability `standard` does not hold cannot start under it at any
port, and Caddy's image carries `NET_BIND_SERVICE` on its binary, so the guarded door
and the proxy run an image their own repositories rebuild from Caddy's with that
capability removed ([ADR-0045](../../00-overview/decisions/0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md)).

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

The client never learns the forwarded port from the guard itself: the core asks the
guard's filler for it over `network.egress-guard` every minute while the stack runs (from
the hosted `watch` loop, and from the dashboard's gather while a surface is open), when the
stack starts and after every diagnosis whose VPN check ran, and sets it on the client over
`download.torrent` when it changes ([capability-contracts](capability-contracts.md#the-forwarded-port),
`ARCH-R251`). No script is mounted into the guard, and no endpoint is opened for it.

### Shapes — the only route to a device or a privilege

| Shape | Written as | Who may declare it |
|-------|------------|--------------------|
| `egress-guard` | `NET_ADMIN` added, and the `/dev/net/tun` device | The upstream an adapter of the same plugin fronts, where that adapter speaks `network.egress-guard`; a plugin's one service where it provides `network.egress-guard` itself, honoured only where the bundle assembles the plugin (`F14-R12`); in the stack, the service that provides `network.egress-guard` |
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
document. A core name here with no [`[[claim]]`](plugin-manifest.md#claim--the-probes-a-core-name-is-demonstrated-by)
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

### No `api`

A service names no in-process adapter. lemonfiber asks a plugin's service over the
contract it speaks (`F14-R3`), and a manifest whose service names `api` is refused as
naming a field the format does not have, naming `service <id>.api` (`ARCH-R272`). The
API an upstream answers the stack's other services in is its `native`.

A service speaking no contract is operated generically, as `F1-R10` and `F1-R11`
promise for a service lemonfiber does not know: whatever asks for a capability it
fills is told that nothing here can register it there, rather than being left
unwired without a word.

### `critical` comes with the egress guard's shape

`critical` means *its failure has consequences outside the machine*, and in the
bundled stack exactly one service holds it: the egress guard, whose failure exposes
the home address. It is not a severity a contributor assigns to their own work: the
classification drives how failures are reported and how hard lemonfiber tries to stop
the operator proceeding. So it is allowed with `shape = "egress-guard"` and nowhere
else, whoever wrote the plugin, and a substitute egress guard is as critical as the
guard it replaces. A service declaring it without that shape is refused, naming the
value, the shape it needs and the four available without it (`ARCH-R97`).

### The fields that are absent, and why

Some of these are fields `stack.toml` carries for the stack alone, and the rest are what
a Compose entry could say and the model does not. A manifest carrying one is refused by
name (`ARCH-R84`), rather than having it ignored:

| Field | Why a plugin may not declare it |
|-------|--------------------------------|
| `grants` | Kernel capabilities, by name. No manifest, the stack's included, names a capability, a device or a group: a service that needs one declares a [shape](#shapes--the-only-route-to-a-device-or-a-privilege), which lemonfiber writes, so nothing a manifest writes can widen what it is given. |
| `depends_on` | An ordering edge, by name. The one edge the format writes is [`network.via`](#inside-another-services-network--networkvia)'s, to whatever fills the capability it names, because a container inside another's network cannot start before that network exists; it is the edge that keeps torrent traffic inside the tunnel (`B1-R14`). Any other edge between services is a source of failures nobody can attribute, and one naming a service is a link by name. |
| `[[wiring]]` | The bundle's [choices of filler and links by name](bundle.md#wiring--a-choice-of-filler-or-a-link-by-name) — `by`, `asks`, `filled_by`, `to`: who is chosen for whom, and who names whom. **Not the [`[[wiring]]`](plugin-manifest.md#wiring--how-the-stacks-own-services-reach-one-service) below**, which is spelled the same and says something else: `hostname`, `dashboard_group` and `service`, naming where lemonfiber puts *this* plugin's service on the proxy and the dashboard. One is a link between two services; the other is one service's own address. Since `ARCH-R127` made the plugin's a list too, the spelling no longer tells them apart and the file it is written in is what does. A plugin declares what it can do in `provides`, is asked for by whatever already asks, and asks in [`[[ask]]`](plugin-manifest.md#ask--what-a-plugins-service-asks-for), by capability only. In particular it cannot introduce a **by-name** link, which is `F4-R12`'s third clause: a by-name wiring is the operator's exception to make and a plugin naming another service is reaching into wiring it does not own. |
| `host_managed` | Native-mode lifecycle is the operating system's (`B2-R15`). A plugin cannot install a system service. |
| `profile` | Assigned, not declared: by the [bundle](bundle.md#profiles-and-forms-for-a-part) for a first-party plugin, and `plugin-<id>` for any other ([what lemonfiber writes](plugin-manifest.md#what-lemonfiber-writes)). |
| `environment` | Free-form variables. A free-form pair is how a manifest would configure its way past what the format says it does, and a value carrying `${…}` would read the stack's environment file, credentials included. A service's environment is [`env`](#environment--four-kinds-of-value) instead, where every value is one of four typed kinds and nothing is interpolated. |
| `ports`, `volumes`, `networks`, `network_mode`, `devices`, `cap_add`, `user`, `privileged`, `entrypoint`, `command` | Compose's own keys. Each is what lemonfiber writes from the typed fields above or never writes at all, and a manifest naming one is naming the output rather than declaring the service. |
| `last_release` | An abandonment signal maintained by the people reviewing the bundled pins, in the bundle beside each pin (`F2-R14`). Self-reported by a plugin it would signal nothing. |

## Related

- [plugin-manifest](plugin-manifest.md) — the rest of the contract, what lemonfiber writes from it, its validation and its requirements
- [stack-manifest](stack-manifest.md) — the vocabulary a plugin's service is declared in
- [bundle](bundle.md) — the ids a first-party `replaces` may name, and the profile its services sit in
- [ADR-0043](../../00-overview/decisions/0043-the-core-writes-every-compose-entry-from-one-typed-service-model.md) — the one service model every Compose entry is written from
