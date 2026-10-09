# Contract: capability contracts

**Status:** Accepted

What the core asks of whatever fills a capability, and how an adapter answers.

**Satisfies:** [F14-R1](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md),
[F14-R3](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md),
[F14-R4](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md),
[F14-R5](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md),
[F14-R6](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md),
[F14-R8](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md),
[F14-R10](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md),
[F14-R13](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md)

---

## Why this file exists

[ADR-0041](../../00-overview/decisions/0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md)
moves every service's behaviour out of lemonfiber's process. What the core used to call
in-process, on a port with one implementation, it now asks over HTTP of an adapter
container a plugin ships. The capability vocabulary
([capability-vocabulary.md](capability-vocabulary.md)) says what a service can do. This
says how it is asked to do it, so one adapter can stand in for another without the core
knowing either.

## The artefacts

The core generates one OpenAPI document per capability and major from the port types it
calls, the way it generates the web API's:

```text
contract/capabilities/<capability>/v<major>/openapi.json
contract/capabilities/<capability>/v<major>/conformance.json
contract/capabilities/index.json
```

- The OpenAPI document is normative for every path, request and answer.
- `conformance.json` lists the cases an adapter's recordings and its live pass must
  answer.
- `index.json` lists every capability, the majors the core speaks, and each document's
  digest.

Nothing here is written by hand. A difference between the types and the published
documents fails the build, as for the web API.

## Speaking a contract

A service says what it speaks, in its manifest:

```toml
[[service]]
id     = "plex-adapter"
speaks = ["media.serve@1", "identity.source@1"]
listens = 8080
```

`speaks` names a capability and a major the core speaks. A service that speaks a
contract also `provides` that capability, so it can be chosen to fill it as any other
service is. Its contract is what demonstrates it: the live pass at install and the
conformance suite's recordings stand where a `[[claim]]`'s probes stand for a service
that speaks none, and it binds no probes for that capability. Whichever
service settles as the filler, the core asks it over the contract it speaks and over
nothing else. A service that speaks none is run and watched, and nothing asks it
anything.

## Paths, keys and answers

- **Paths.** Every operation is at
  `/lemonfiber/<capability>/v<major>/<operation>`, on the port the adapter `listens`
  on.
- **Where.** The core runs on the host, so it reaches an adapter on the host's loopback
  interface. lemonfiber publishes the adapter's `listens` port on `127.0.0.1` alone and
  names no host port, so the engine gives it a free one. The core asks the engine which
  port that is before it asks the adapter anything, and reaches the adapter nowhere else.
  Nothing off the machine can reach it, and the plugin's key guards it from everything
  on the machine.
- **Key.** Every request carries `Authorization: Bearer <key>`. The key is minted by the
  core for that plugin alone and written to the adapter's configuration directory as
  `lemonfiber.key` before it starts. An adapter refuses any request without it
  (`401`).
- **Answers.** A success answers `200` with the operation's JSON body, or `204` where
  it has none. A refusal answers a problem document
  (`application/problem+json`) whose `type` is one of the contract's declared
  refusals, so the core maps it to its own code without reading prose.
- **Bounds.** An answer is at most 1 MiB unless the operation declares a larger bound,
  and must arrive within 15 seconds unless the operation declares a longer one. Outside
  either, the call fails closed.
- **Untrusted.** Every answer is decoded against the operation's schema. An unknown
  field, a wrong type, a missing required field or an undeclared status is a
  nonconforming answer. It is refused, it is not read, and the plugin's conformance
  standing records it.

## What every adapter answers

| Operation | What it is for |
|---|---|
| `GET /lemonfiber/adapter/v1/about` | Which contracts and majors it speaks, the upstream it fronts, and the upstream releases it supports, each with the digest its recordings were taken from (`F14-R13`) |
| `GET /lemonfiber/adapter/v1/ready` | Whether its upstream answers, for health |

## The capabilities

The operations below are the ports the core calls today, grouped by the capability that
asks for them. Their shapes are the generated documents' alone.

| Capability | Operations |
|---|---|
| `identity.source` | First-run state; create the administrator; the household's accounts; one account by name; an account's standing and limits; invite; take an invitation back; withdraw; when an invitation was sent; libraries; ratings; allow; claimable; suspend; sessions for an account; whether devices sign in by code |
| `media.serve` | The guard and the locations (below); holdings for an account; what is playing; a title; a title's poster or backdrop for an account; part-way; record progress; open a device's session for an account; sign a device out; has an item; rescan; trust a proxy; allow origins; mint, list, date and revoke a key for an app |
| `library.curate` | Identity; download clients (register, update, set a field, test, list); root folders (register, list); quality profiles; run a command; hardlinks (read, set); records and carry; catalogue lookup, plan, add and indexer count; releases for a quality; apply a music format; queue; pipeline (library, find, history, queue, parts, stuck) |
| `download.usenet`, `download.torrent` | Transfers; pulling, stop, resume; throttled, restrain, moving; moved; seeding (`download.torrent`); usenet accounts (`download.usenet`) |
| `indexer.search` | Register, list, test and re-key an application; indexers; aggregators (list, add) |
| `indexer.proxy` | Solve a challenge; whether it answers |
| `request.intake` | Initialised; configure identity; answers; requests; link members; member for an account; requesting; approval first; remove a member; telling and tell; fulfilment targets (list, add, move, test); the media server link (read, set); asking (read, set); left; quota; approves own; decide; hold and release requests; reachable; notices |
| `subtitles.fetch` | Watching; watch |
| `network.egress-guard` | Whether the tunnel is up; the forwarded port |
| `proxy.front` | Apply a routing table (household names, upstreams, TLS mode and certificate files); the table it serves; reload |
| `dashboard.show` | Apply a panel list (groups, entries, links, widgets the core names); the list it shows |
| `quality.sync` | Apply profiles to a curator; what it last applied |
| `archive.extract` | The folders it watches for each curator; hand a finished extraction back; what it is working on |
| `stream.guard` | Apply a guard (below); the guard it enforces; the certificate it presents |
| `invite.decline` | Hold a key for the request service; the key it holds; decline an invitation |
| `request.gate` | Apply the routes it admits, for each curator and media server; the routes it admits |

The capability types are neutral: none names a product. A curator is referred to by the
media type it files, never by its id.

## The guard and the locations

A filler of `media.serve` answers `GET /lemonfiber/media.serve/v1/declared` with:

- **The byte paths.** Path patterns under which the upstream serves bytes for an item,
  each with where the item's id sits.
- **The question.** The request the guard makes to decide a byte request: a method and a
  path template with `{item}`, sent to the upstream or to the adapter, and the statuses
  that mean "may", "may not", "no session" and "not from there".
- **The token.** How a member's `Authorization: Bearer <token>` is presented to the
  upstream: as is, rewritten to a header template, or moved to a query parameter. The
  shape a token must have is a pattern, and a token that does not match is left as it
  came.
- **The locations.** Templates for an item's stream, poster and backdrop, with
  `{base}` and `{item}`, built by the core against the household address and the guard's
  TLS port.
- **The ports.** The port the upstream listens on, and the upstream's own encrypted
  port where a household client expects it.

The core hands the declaration to the filler of `stream.guard` (`apply a guard`), which
enforces exactly it. The core builds every location a member is given from the
templates (`F14-R10`). A declaration that admits a byte path without a question, or a
template whose host is not `{base}`, is refused at install.

## Conformance

A plugin's repository holds a recording for every case in the capability's
`conformance.json`. Each recording is the request the case makes and the adapter's answer,
taken against the upstream at the digest the adapter declares, as a claim's recordings
are ([ARCH-R120](plugin-manifest.md) onward).

- **Where.** By convention, beside the manifest: `conformance/<capability>@<major>/<case>.json`,
  one file per case. The manifest lists none of them; the cases come from the published
  `conformance.json`, so a missing recording is named by its case.
- **Against what.** The upstream is the service the adapter names in `fronts`. Every
  recording names the digest the manifest pins for that service, and one naming another
  is refused rather than judged.
- **Judged as the core reads.** A recorded answer is held to its operation exactly as a
  live one is: the same schema, status set and size bound.

- `lemonfiber plugin conform` judges the recordings without running anything.
- Install repeats a live pass of the cases marked `live` against the running adapter.

A plugin whose recordings or live pass fail a case does not fill the capability, and
the refusal names the case. The first-party adapters are judged by the same runner
against the same cases. The stream guard's recorded byte cases are `stream.guard`'s
conformance suite.

## Versioning

A contract's major changes only when an operation is removed or its meaning changes.
Adding an optional field or an operation is a minor change the core speaks without a new
major. The core speaks every major listed in `index.json`. When a second major arrives,
the first stays spoken until it is deprecated by announcement and then removed, as [versioning.md](versioning.md) holds for a plugin manifest.

## Requirements

| ID | Requirement |
|----|-------------|
| **ARCH-R199** | The core MUST generate an OpenAPI document and a conformance list per capability and major from the port types it calls, and a difference between the types and the published documents MUST fail the build. |
| **ARCH-R200** | A manifest's `speaks` MUST name only capabilities and majors listed in `contract/capabilities/index.json`, and an unlisted one MUST be refused by name. |
| **ARCH-R201** | Every operation MUST be at `/lemonfiber/<capability>/v<major>/<operation>` on the adapter's `listens` port, and every request MUST carry the plugin's key as a bearer token. |
| **ARCH-R202** | The core MUST mint each plugin's key from its own random source, write it to the adapter's configuration directory before the adapter starts, and use it for no other plugin. |
| **ARCH-R203** | An answer outside its operation's schema, status set, size bound or time bound MUST be refused, MUST NOT be read, and MUST be recorded against the plugin's conformance standing. |
| **ARCH-R204** | A refusal MUST be a problem document whose `type` the contract declares, and the core MUST map it to a code without reading its prose. |
| **ARCH-R205** | Every adapter MUST answer `about` and `ready`, and `about` MUST list the upstream releases it supports, each with the digest its recordings were taken from. |
| **ARCH-R206** | A filler of `media.serve` MUST answer `declared` with its byte paths, its question, its token presentation, its location templates and its ports, and a declaration that admits a byte path without a question, or whose template host is not `{base}`, MUST be refused at install. |
| **ARCH-R207** | The core MUST give the filler of `stream.guard` the media server filler's declaration and nothing it was not declared, and MUST build every location a member is given from the declared templates. |
| **ARCH-R208** | A plugin MUST hold a recording for every case its capabilities' conformance lists, taken at the digest its adapter declares, and `lemonfiber plugin conform` MUST judge them without running anything. |
| **ARCH-R209** | Install MUST run the live conformance cases against the running adapter, and a failed case MUST keep the plugin from filling the capability and MUST be named. |
| **ARCH-R210** | No capability type MUST name a product, and a curator MUST be referred to by the media type it files. |
| **ARCH-R211** | A contract's major MUST change only when an operation is removed or its meaning changes, and the core MUST speak every major its index lists. |
| **ARCH-R212** | An adapter's `listens` port MUST be published on `127.0.0.1` alone with no host port named, and the core MUST read the host port the engine gave it from the engine and MUST NOT reach an adapter at any other address. |
| **ARCH-R213** | A service that speaks a capability's contract MUST also provide that capability, and a manifest where one does not MUST be refused by name; that capability MUST be demonstrated by its contract and MUST NOT require a `[[claim]]`. |
| **ARCH-R214** | Where the service filling a capability speaks that capability's contract, the core MUST ask it over the contract alone and MUST NOT reach it through an adapter of its own. |
| **ARCH-R217** | A plugin's conformance recordings MUST sit at `conformance/<capability>@<major>/<case>.json` beside its manifest, one per case of each contract it speaks, each in the recording format of `ARCH-R120` and naming the digest the manifest pins for the service its adapter `fronts`, and `lemonfiber plugin conform` MUST judge each recorded answer as the core reads a live one and MUST name each case whose recording is absent, unreadable, of another request or of another digest. |

## Related

- [ADR-0041](../../00-overview/decisions/0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md)
- [F14](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md)
- [capability-vocabulary.md](capability-vocabulary.md): what each capability is, and its probes
- [plugin-manifest.md](plugin-manifest.md): where `speaks` is declared
- [web-api.md](web-api.md): the generation this mirrors
