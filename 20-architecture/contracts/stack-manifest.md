# Contract: `stack.toml`

**Status:** Accepted

The interface between `lemonfiber` and `media-stack`. Everything lemonfiber knows about
the stack comes from this file; it knows nothing about Sonarr that isn't declared
here.

**Satisfies:** [B1-R2](../../10-functional/features/b-running/b1-forms.md),
[B1-R3](../../10-functional/features/b-running/b1-forms.md),
[F1-R5](../../10-functional/features/f-extensibility/f1-customisation.md),
[F1-R9](../../10-functional/features/f-extensibility/f1-customisation.md),
[F2-R1](../../10-functional/features/f-extensibility/f2-service-catalogue.md)–[F2-R4](../../10-functional/features/f-extensibility/f2-service-catalogue.md)

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
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | Unique. Must match a Compose profile name exactly. |
| `name` | string | ✔ | Human-facing |
| `description` | string | ✔ | Shown in form previews |

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
describes   = "Watches for new episodes and fetches them"
without_it  = "Find and download episodes yourself"
media_types = ["tv"]
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | Unique. MUST match the Compose service name. |
| `name` | string | ✔ | Human-facing |
| `profile` | string | ✔ | **Exactly one** (`B1-R1`). MUST reference a declared profile. |
| `image` | string | ✔ | Without tag |
| `tag` | string | ✔ | Explicit version. A floating tag fails validation (`E1-R1`). |
| `port` | integer | | Primary UI/API port. Omitted for services with no listener. |
| `bind` | enum | ✔ if `port` | `loopback` \| `lan`. Enforces [C6](../../10-functional/features/c-trust/c6-web-security.md)'s two-tier policy. |
| `health` | table | | See below. Absent means lifecycle waits on container state only. |
| `api` | table | | How lemonfiber talks to it for [seeding](../../10-functional/features/d-content/d1-seed.md). Absent means no API integration. |
| `criticality` | enum | ✔ | `critical` \| `core` \| `important` \| `enhancing` \| `optional` (`F2-R3`) |
| `license` | string | ✔ | SPDX identifier. A non-OSI value fails validation (`F2-R5`, `F2-R12`). |
| `upstream` | string | ✔ | Project URL, for maintenance review (`F2-R14`) |
| `describes` | string | ✔ | What it does *for the operator* (`F2-R1`) |
| `without_it` | string | ✔ | Consequence of its absence (`F2-R2`) |
| `media_types` | array | | Which media types it handles; drives root-folder seeding |
| `depends_on` | array | | **Same profile only.** Cross-profile entries fail validation (`B1-R14`). |
| `capabilities` | array | | e.g. `["NET_ADMIN"]`. Any entry beyond an allow-list fails validation. |
| `host_managed` | bool | | `true` for native-mode Jellyfin — lifecycle is the OS's (`B2-R15`) |

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
api = { kind = "servarr",  key_source = "config-xml", path = "/config/config.xml" }
api = { kind = "sabnzbd",  key_source = "config-ini", path = "/config/sabnzbd.ini" }
api = { kind = "qbittorrent", key_source = "generated" }
api = { kind = "seerr",    key_source = "api-settings" }
api = { kind = "bindery",  key_source = "config-json", path = "/config/config.json" }
```

`kind` selects the client implementation. `servarr` covers Sonarr, Radarr, Lidarr
and Prowlarr, since they share an API shape — which is what makes one client
sufficient for four services.

`key_source` says where the credential comes from:

| Value | Meaning |
|-------|---------|
| `config-xml`, `config-ini`, `config-json` | The service mints it and writes it to `path`; lemonfiber reads it |
| `api-settings` | Retrieved over the service's own API once authenticated |
| `generated` | The service offers nothing durable to read, so lemonfiber generates the credential, sets it, and records it for its consumers (`A7-R14`) |
| `none` | The API needs no credential at all |

`generated` exists because qBittorrent mints only a *temporary* WebUI password
and asks for it to be replaced. It also has a consumer that is not a service —
the VPN's forwarded-port push authenticates against the same WebUI API, so the
recorded value has to reach the stack's environment and not only lemonfiber's own
store.

**Bindery is deliberately its own kind.** It is not a Servarr application, and
Prowlarr's app sync does not cover it (`D1-R15`).

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
| `tag` is not `latest` or otherwise floating | Service named (`E1-R1`) |
| `bind` present when `port` is | Service named |
| `license` is a recognised OSI identifier | Service and licence named (`F2-R5`) |
| `capabilities` within the allow-list | Service and capability named |
| Manifest services match `compose.yml` services exactly | Divergence listed both ways |

That last rule matters more than it looks: a manifest describing a service that
isn't in the compose file — or vice versa — is the most likely error when adding
one, and it fails in confusing ways at runtime.

## Worked example

The real stack, abridged to one service per profile. The full file lives in
`media-stack`.

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

[[profile]]
id = "torrent"
name = "Torrents"
description = "Torrent downloading, VPN-isolated"

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
capabilities = ["NET_ADMIN"]

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
```

Note `qbittorrent.depends_on = ["gluetun"]` — legal because both are in
`torrent`, and the single permitted cross-service dependency in the stack
(`B1-R14`).

Note `seerr.bind = "lan"` against everything else's `loopback` — the two-tier
policy expressed as data rather than as a rule someone has to remember.

## Compatibility

See [versioning](versioning.md).

## Related

- [ADR-0002 Profiles and forms](../../00-overview/decisions/0002-profiles-and-forms.md)
- [ADR-0005 Embedded stack assets](../../00-overview/decisions/0005-embedded-stack-assets.md)
- [B1 Forms](../../10-functional/features/b-running/b1-forms.md) · [F2 Service catalogue](../../10-functional/features/f-extensibility/f2-service-catalogue.md)
- [component-model.md](../component-model.md) — where the manifest is parsed
