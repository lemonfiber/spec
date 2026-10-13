# Contract: `bundle.toml`

**Status:** Accepted

The interface between `lemonfiber` and the default bundle `lemonfiber-plugins` keeps.
Everything lemonfiber knows about the stack it ships comes from this file and the plugin
trees it pins: which profiles and forms there are, which first-party plugin fills each
capability by default, where each part sits, and the choices the stack makes on its
own behalf.

**Satisfies:** [B1-R1](../../10-functional/features/b-running/b1-forms.md),
[B1-R2](../../10-functional/features/b-running/b1-forms.md),
[B1-R3](../../10-functional/features/b-running/b1-forms.md),
[B1-R12](../../10-functional/features/b-running/b1-forms.md),
[B1-R15](../../10-functional/features/b-running/b1-forms.md),
[F2-R13](../../10-functional/features/f-extensibility/f2-service-catalogue.md),
[F2-R14](../../10-functional/features/f-extensibility/f2-service-catalogue.md),
[F9-R4](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md),
[F14-R7](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md),
[F14-R19](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md)

---

## Why this file exists

Every bundled part is a first-party plugin in a repository of its own
([ADR-0041](../../00-overview/decisions/0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md)),
and the bundle is what pins them and what the binary embeds
([ADR-0042](../../00-overview/decisions/0042-the-bundle-is-first-party-plugins-pinned-and-embedded.md)).
A plugin manifest describes one part, in the vocabulary every author shares
([ADR-0043](../../00-overview/decisions/0043-the-core-writes-every-compose-entry-from-one-typed-service-model.md)
§2). What is about the whole stack has no place in any one part: the profiles, the
forms, the services the catalogue no longer carries, which of two claimants the stack
chooses, and the links that are genuinely about one service. The bundle declares those,
and pins each part by the tree it was reviewed at
([ADR-0045](../../00-overview/decisions/0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md)).

A part enters the bundle before its adapter exists. Such a part is **assembled**:
lemonfiber builds the stack it ships from the bundle and the parts' copies, and an
assembled part's one service is a stack service in every respect, its in-process
adapter included. A part whose adapter has shipped is **installed** through the plugin
path, moving in place of the stack service it replaces (ADR-0042 §4). The bundle says
which, per part.

## File location

`bundle/bundle.toml` in `lemonfiber-plugins`, which the core pins as a submodule and
compiles in. Beside it, `bundle/plugins/<id>/` holds each pinned plugin's tree, copied
byte for byte from its origin at the pinned revision.

The stack lemonfiber ships is assembled from these and from nothing else
(`ARCH-R263`). It carries no `stack.toml`, no `include` list and no `services/` file, and
lemonfiber materialises none for it. The [stack manifest](stack-manifest.md) is the form
the assembly produces inside lemonfiber, and the format of a stack directory an operator
names with `--stack-dir` (`F1-R3`).

## Top-level structure

```toml
schema = 2

[[profile]]  # one per profile
[[form]]     # one per form
[[wiring]]   # a choice of filler, or a link by name
[[removed]]  # one per service the catalogue no longer carries
[[plugin]]   # one per first-party plugin, ordered by id
```

`schema` names the format generation. `schema = 1` is the bundle of plugins alone,
each copy one manifest at `bundle/plugins/<id>.toml` and each pin naming a release.
lemonfiber reads `1` and `2`, and refuses any other, naming both (`ARCH-R265`).

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
| `id` | string | ✔ | Unique. The Compose profile lemonfiber writes its services into. |
| `name` | string | ✔ | Human-facing |
| `description` | string | ✔ | Shown in form previews |
| `protocol` | enum | | `usenet` \| `torrent`. Present only on a profile that cannot run without a configured provider. |

### `protocol` — what makes the intersection possible

[B1-R4](../../10-functional/features/b-running/b1-forms.md) requires a closure to be
intersected with the operator's configured protocols before anything starts, and
[B1-R15](../../10-functional/features/b-running/b1-forms.md) requires the profiles it
applies to to be declared rather than recognised by name. `protocol` is that
declaration. A profile that declares one cannot run unless the operator has configured
that provider; a profile that declares none is never narrowed away.

The consequence of getting this wrong is not cosmetic. A torrent profile started
without a configured VPN brings up the tunnel container with no credentials, and the
failure mode of a VPN that is not protecting anything is the one failure in this
product with consequences outside the machine.

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

A form's `profiles` list is the **complete** closure, written out. Dependencies are not
inferred: `tv` names `search` explicitly rather than lemonfiber deducing that Sonarr
needs indexers, because inference would require lemonfiber to understand each
service's semantics
([ADR-0002](../../00-overview/decisions/0002-profiles-and-forms.md)).

## `[[removed]]`

```toml
[[removed]]
id          = "readarr"
removed_in  = "0.1.0"
reason      = "Discontinued upstream in 2025. Its repository is archived, so the pin could only ever age."
replaced_by = "bindery"
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | The service the catalogue carried. No pinned plugin's id. |
| `removed_in` | string | ✔ | The version it went in |
| `reason` | string | ✔ | Why it went (`F2-R13`) |
| `replaced_by` | string | | The pinned plugin that took the job over, where one did |

## `[[wiring]]` — a choice of filler, or a link by name

```toml
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

An ask is the asker's: a part asks for a capability in its own manifest's
[`[[ask]]`](plugin-manifest.md#ask--what-a-plugins-service-asks-for), with `each` where
it reaches every filler, as any plugin does. A bundle wiring is one of the two things no
manifest may say (`F14-R9`, `F14-R22`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `by` | string | ✔ | The service whose wiring this is. A service of a pinned plugin. |
| `asks` | string | | The capability whose filler the stack chooses. Exactly one of this and `to`. The `[[ask]]` of `by`'s plugin MUST ask it, not `each`. |
| `filled_by` | string | ✔ with `asks` | The claimant the stack chooses. A service of a pinned plugin that provides the capability. |
| `to` | string | | The service named. The by-name exception (`F4-R12`). Exactly one of this and `asks`. |
| `why` | string | ✔ | Why this claimant was chosen, or why this is by name. Never blank. |

`provides` says what a service can do, and an ask says what a service needs.
[`F4-R1`](../../10-functional/features/f-extensibility/f4-capabilities.md)'s second
clause is that **the wiring asks for a capability rather than naming a service**, and
[`F9-R4`](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md) is
that clause applied to the stack this project ships.

### `filled_by` — a choice, recorded, rather than a rule

Where two parts claim one capability and a part asks for one of them, somebody has to
choose. `F4-R8` says who: not install order, not precedence, not recency, but an
operator, and their choice is recorded.

`filled_by` is the stack making that choice for the stack it ships, in a file the
operator can read and with the reason beside it. It is a default, not a rule: the
operator substitutes by choosing another claimant, that change is journalled like any
other ([`F4-R10`](../../10-functional/features/f-extensibility/f4-capabilities.md)), and
it can be put back. A plugin's ask of the same capability is settled by the same choice
where the operator made none (`F14-R23`).

It is `why`-bearing for the same reason `to` is. A choice with no reason beside it is
indistinguishable from a rule somebody encoded, which is the thing `F4-R8` refuses.

### `to` — by name, and shown as by name

`F4-R12` keeps by-name wiring available and makes it visible as the exception it is.
`to` names a service, carries the reason, and anything that lists the stack's wiring
shows it as by-name rather than as an ask that happened to resolve to one candidate. A
link by name joins the service it names and never a service standing in for it
(`ARCH-R242`).

Each by-name link says why: it is a service configured in another's own terms, or
making another's own calls, so it is about that service. Everything else asks.

The torrent client's link to the tunnel is not here. It is
[`network.via`](plugin-manifest-service.md#inside-another-services-network--networkvia)
on the client's own service, an ask of `network.egress-guard`, so a substitute egress
guard takes the client inside its own network.

## `[[plugin]]` — each part, pinned

```toml
[[plugin]]
id           = "sabnzbd"
origin       = "https://github.com/lemonfiber/plugin-sabnzbd"
revision     = "4c1d0a7e9b2f3c5d6e8f0a1b2c3d4e5f6a7b8c9d"
manifest     = "sha256:2b9e…"
tree         = "sha256:7f04…"
fills        = ["download.usenet"]
stage        = "assembled"
profile      = "usenet"
last_release = "2026-09-30"

[[plugin]]
id           = "jellyfin"
origin       = "https://github.com/lemonfiber/plugin-jellyfin"
release      = "0.18.0"
revision     = "9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b"
manifest     = "sha256:c310…"
tree         = "sha256:5ad2…"
fills        = ["media.serve", "identity.source"]
stage        = "installed"
profile      = "media"
last_release = "2026-10-02"
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | The plugin's `[plugin].id`, and the id of the service that takes the part's place: its one service where `assembled`, the service declaring `replaces` where `installed`. |
| `origin` | string | ✔ | The plugin's repository, as an `https` URL |
| `release` | string | | The tag the release train cut there, without the `v`. Absent where the revision was not tagged: a plugin that builds no image is never tagged, and a pre-release may pin one that does at a commit (`OPS-R86`). |
| `revision` | string | ✔ | The full commit whose tree is pinned, on the origin's default branch |
| `manifest` | string | ✔ | `sha256:<64 hex>` of `plugin.toml` at the revision |
| `tree` | string | ✔ | `sha256:<64 hex>` of the plugin's tree at the revision — see [the tree](#the-tree--what-a-pin-covers) |
| `fills` | array | ✔ | The capabilities it fills by default. Each one a service of the plugin provides or speaks. |
| `stage` | enum | ✔ | `assembled` \| `installed` — see below |
| `profile` | string | ✔ | The declared profile every service of the plugin sits in (`B1-R1`) |
| `last_release` | string | ✔ | `YYYY-MM-DD`. The **latest upstream release**, not the pinned one: an abandonment signal, kept by the reviewers who move the pin and refreshed when they do (`F2-R14`) |

A plugin **builds an image** where one of its services runs an image under
`ghcr.io/lemonfiber/`, where lemonfiber publishes the images it builds and nothing
else ([ADR-0033](../../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md)).
Only such a plugin is tagged by the train, and where `release` is named every image it
builds is tagged at that release (`REPO-R92`).

The id is the service's because every name the stack already gives a part follows from
it: the container, the configuration directory `./config/<id>`, the settings and secret
namespaces, the materialised files and the journal's history. A part becoming a plugin
renames none of them.

### `stage` — assembled, or installed

| Stage | What lemonfiber does with it |
|-------|-------------------------------|
| `assembled` | Writes its one service into the stack it ships, as a stack service: the stack's origin, its setting and credential names, every `[[secret]]` its plugin declares, held in the service id's namespace (`ARCH-R275`), its claims judged as a bundled service's (`F9-R2`), and its `api` honoured (`ARCH-R272`). The plugin declares exactly one service, which speaks no contract, and every fixture its claims name lies under `recordings/<id>/`. |
| `installed` | Installs it through the plugin path offline from the embedded tree and settles it as its capabilities' default filler (ADR-0042 §3), offered by the `up` of a form that holds its profile (`ARCH-R298`); a stack running the part as its own service is offered the move in place by `lemonfiber update` (§4, `ARCH-R299`). The service whose id is the plugin's declares `replaces` naming it, and keeps the stack's setting, secret and credential names for it (`ARCH-R273`), and every link by name and choice of filler naming that id reaches it (`ARCH-R301`). |

The release whose bundle moves a part from `assembled` to `installed` is the release that
deletes its in-process adapter from the core. A stack whose operator has not taken the
move keeps running the part's own service, assembled from the pin's copy, and what the
deleted adapter filled stands unfilled until the move is taken.

The media server is pinned `installed` before its move can be made: the move takes the
stack's own service out of the Compose project, which only the generated project can,
and the stack runs from the generated project only from the compose cutover. Until the
release that moves it, the stack keeps the media server's service, claims and
recordings as the media stack held them at the source switch, the one part not read
from the bundle (`ARCH-R263`), with its in-process adapter.

### Profiles and forms for a part

Every service of a pinned plugin sits in the profile its `[[plugin]]` names, whatever
the stage (`ARCH-R96`). A plugin manifest has no profile field, so a substitute and the
part it stands in for are declared in the same vocabulary, and the bundle is the one
place a profile is assigned. The plugin's `[plugin].forms` names exactly the forms whose
closure holds that profile, so what the manifest says it joins and what the bundle
starts agree.

## The tree — what a pin covers

A plugin's tree is every file the binary carries from it, at the paths its repository
holds them:

- `plugin.toml`;
- each service's starting files, under `config/<service id>/`
  ([starting files](plugin-manifest-service.md#starting-files--what-it-starts-with));
- every recording the manifest names, a claim's, a proof's or a contributed check's;
- `conformance/`, where the plugin speaks a contract.

`tree` is the SHA-256 of a listing of those files, one line per file, sorted by path
bytewise: the file's SHA-256 in lowercase hex, two spaces, its path relative to the
repository root with `/` between segments, and a line feed. The listing is what
`sha256sum` prints for the same files in that order, so any reader reproduces the
digest with standard tools (`ARCH-R267`).

`manifest` is the digest of `plugin.toml` alone. Both are pinned: `manifest` is what the
catalogue's signed index already names, and `tree` is what the binary carries.

The copy at `bundle/plugins/<id>/` is that tree, each file at its path in the plugin's
repository. A first-party plugin keeps its starting files at `config/<id>/` and its
recordings at `recordings/<id>/`, the paths the media stack held them at, so every
materialised file and every fixture keeps its path when a part's source moves.

## The reserved register

The ids, the published ports and the proxy hostnames of every service a pinned plugin
declares, of either stage, are reserved, and so is every hostname the proxy's
configuration in its copy answers on (`ARCH-R269`). A service of any other plugin taking
one is refused, naming it and the part that holds it, except the first-party service
whose `replaces` names that id
([`replaces`](plugin-manifest-service.md#service--what-runs), `ARCH-R222`). Reading both
stages is what keeps a part's port reserved through its move: an installed part is still
the bundle's.

## Validation

Validation reports **every** violation in one pass, each naming its location (`F1-R9`).

| Rule | Failure |
|------|---------|
| `schema` is `1` or `2` | Both values named |
| Every `id` unique within its table | Duplicate named |
| Every `form.profiles` entry references a declared profile | Form and profile named (`B1-R12`) |
| `protocol` is a permitted value, on at most one profile per value | Profile and value named |
| Every `[[removed]]` carries `id`, `removed_in` and `reason`, and names no pinned plugin | Entry named (`F2-R13`) |
| A `replaced_by` names a pinned plugin | Entry and id named |
| Exactly one of `asks` and `to` on a wiring, with `why` not blank | Wiring named, with what it has (`ARCH-R268`) |
| `filled_by` with `asks` and nowhere else; no wiring carrying `asks` without it | Wiring named: an ask belongs in the asker's `[[ask]]` (`ARCH-R268`) |
| Every `by`, `to` and `filled_by` names a service of a pinned plugin, and none names its own `by` | Wiring and id named |
| `by`'s plugin asks `asks` in its `[[ask]]`, not `each` | Wiring, service and capability named |
| `filled_by` provides or speaks the capability it is chosen for | Wiring, service and capability named (`F4-R8`) |
| No two wirings carry the same `by` and `asks`, or the same `by` and `to` | Both wirings named |
| Every `[[plugin]]` carries every required field, and `stage` is `assembled` or `installed` | Plugin and field named (`ARCH-R266`) |
| `revision` is 40 hex on the origin's default branch; `manifest` and `tree` are `sha256:<64 hex>` | Plugin and field named |
| `id` is the plugin's `[plugin].id` and the id of the service that takes the part's place | Plugin and both ids named (`ARCH-R266`) |
| An `assembled` plugin declares one service, speaking no contract, with every claim fixture under `recordings/<id>/` | Plugin named, with what it declares |
| An `installed` plugin's service whose id is the plugin's declares `replaces` naming it | Plugin named |
| `profile` is a declared profile, and `[plugin].forms` names exactly the forms whose closure holds it | Plugin, profile and forms named |
| Every `fills` entry is provided or spoken by a service of the plugin | Plugin and capability named |
| `last_release` is `YYYY-MM-DD` and not in the future | Plugin and value named (`F2-R14`) |
| Every pinned plugin's `license` is an OSI licence, except where its `upstream` is under `https://github.com/lemonfiber/` and a service's image is under `ghcr.io/lemonfiber/`, where it is `Hippocratic-3.0` and nothing else | Plugin and licence named (`F2-R5`) |
| Every service of a pinned plugin declares `reaches` and `asks_for` | Plugin and service named (`F2-R10`, `ARCH-R270`) |
| No reserved id, port or hostname is taken twice across the pinned plugins | Each one and both plugins named (`ARCH-R269`) |
| A copy is the tree at the pinned revision, and its digests are the pin's | Plugin and the differing path named (`ARCH-R267`, `REPO-R92`) |

## Published schema

Each release of lemonfiber carries a JSON schema of `bundle.toml`,
`contract/bundle.schema.json`, generated from the types lemonfiber reads it into
(`ARCH-R172`).

## Requirements

| ID | Requirement |
|----|-------------|
| **ARCH-R263** | lemonfiber MUST assemble the stack it ships from the bundle it embeds and the plugin trees it pins, and from nothing else, but the media server's service, its claims and their recordings, which it MUST read from the media stack as frozen at the source switch until the release that moves the media server in place (`ARCH-R299`); and it MUST NOT carry or materialise a `stack.toml`, an `include` list or a `services/` file for it. |
| **ARCH-R265** | The default bundle MUST declare, in `bundle/bundle.toml` at `schema = 2`, every profile, form and removed service of the stack it ships, as `[[profile]]`, `[[form]]` and `[[removed]]` with the fields this contract states, and one `[[plugin]]` per first-party plugin; no plugin manifest MAY declare a profile, a form or a removed service; and lemonfiber MUST read `schema` 1 and 2 and MUST refuse any other, naming both. |
| **ARCH-R266** | Each `[[plugin]]` MUST name `id`, `origin`, `revision`, `manifest`, `tree`, `fills`, `stage`, `profile` and `last_release`, and MAY name `release`; `id` MUST be the plugin's own and the id of the service that takes the part's place; an `assembled` plugin MUST declare exactly one service, speaking no contract, whose claims' fixtures lie under `recordings/<id>/`; an `installed` plugin's service of that id MUST declare `replaces` naming it; every service of the plugin MUST sit in the declared profile `profile` names, and `[plugin].forms` MUST name exactly the forms whose closure holds it; and each violation MUST be refused naming the plugin and the field. |
| **ARCH-R267** | `tree` MUST be the SHA-256 of a listing, sorted by path bytewise, of one line per file of the plugin's tree (`plugin.toml`, `config/<service id>/` for every service, every recording the manifest names, and `conformance/`), each line the file's SHA-256 in lowercase hex, two spaces, its path relative to the repository root and a line feed; and the catalogue's copy at `bundle/plugins/<id>/` MUST be that tree, each file at its path in the plugin's repository. |
| **ARCH-R268** | A bundle `[[wiring]]` MUST be either a choice of filler, naming `by`, `asks`, `filled_by` and `why`, where `by`'s plugin asks that capability in its `[[ask]]` and not `each` and `filled_by` provides or speaks it, or a link by name, naming `by`, `to` and `why`; every service it names MUST be a pinned plugin's; and a wiring of any other shape, an ask without `filled_by` among them, MUST be refused naming the wiring. |
| **ARCH-R269** | The ids, published ports and proxy hostnames of every service a pinned plugin declares, `assembled` and `installed` alike, and every hostname the proxy's configuration in its copy answers on, MUST be reserved; a service of any other plugin taking one MUST be refused naming it and the plugin holding it, except a first-party service whose `replaces` names that id. |
| **ARCH-R275** | An `assembled` plugin's service MUST keep every `[[secret]]` its plugin declares, each held in the secret store in the service id's namespace as `<service id>:<secret id>` and written to that service's own secrets file as a plugin's is (`ARCH-R247`). |
| **ARCH-R298** | The `up` of a form whose closure holds the profile of an `installed` pin, where neither that plugin nor a stack service of its id is present, MUST offer installing the plugin from its embedded tree, offline, through the plugin path as any install is (`F6-R1`); the offer MUST be rehearsable, and without the operator's yes nothing of the form MUST be written or started. |
| **ARCH-R299** | Where the stack runs a part as its own service and the bundle pins that part `installed`, `lemonfiber update` MUST offer moving it in place: the plugin's service takes the same container name, configuration directory, data and setting, secret and credential names (`ARCH-R273`), and the stack's own service is stopped and left out of the stack; the move MUST be rehearsed and shown before anything changes, journalled as one operation and undone as one unit (`F6-R9`); without the yes the stack's own service MUST keep running, assembled from the pin's copy, what its deleted in-process adapter filled MUST be reported unfilled, and `up` and the doctor MUST name the move as offered. |
| **ARCH-R300** | lemonfiber MUST trust a plugin as first-party only at the id, the manifest digest and the tree digest its pin names. |
| **ARCH-R301** | A link by name or a choice of filler naming a reserved id MUST reach the first-party service whose `replaces` names it, and the checks that refuse a plugin service an id, port or hostname the running stack holds MUST pass over that service. |

## Related

- [ADR-0045](../../00-overview/decisions/0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md) — the decision this contract implements
- [ADR-0046](../../00-overview/decisions/0046-the-stores-are-filled-once-at-the-cutover-and-a-secret-never-enters-the-journal.md) — an assembled part's secrets, and when the environment file is filed
- [ADR-0042](../../00-overview/decisions/0042-the-bundle-is-first-party-plugins-pinned-and-embedded.md) — the bundle, pinned and embedded
- [ADR-0002 Profiles and forms](../../00-overview/decisions/0002-profiles-and-forms.md)
- [plugin-manifest](plugin-manifest.md) — what each pinned plugin declares
- [stack-manifest](stack-manifest.md) — the form the bundle is assembled into, and a `--stack-dir` stack's format
- [lemonfiber-plugins](../../30-repos/lemonfiber-plugins.md) — where the bundle lives, and the CI that holds each copy to its origin
- [releasing](../../70-operations/releasing.md) — `OPS-R86`, which plugins the train tags and which it pins by revision alone
- [B1 Forms](../../10-functional/features/b-running/b1-forms.md) · [F9 Capabilities of the bundled services](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md)
