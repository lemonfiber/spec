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
  answer, and what each one asks.
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
- **Who it runs as.** lemonfiber writes every service that speaks a contract to run as
  the operator's uid and gid, and writes `lemonfiber.key` readable by that uid alone, so
  an adapter reads its key and nothing else on the machine can (`F14-R27`).
- **The upstream's credential.** Where the upstream needs a credential lemonfiber keeps,
  lemonfiber writes it beside the key as `upstream.json`, a JSON object of named strings,
  each time it creates, rotates or moves that credential. The adapter's `upstream` names
  those fields and the secret each holds, which is one lemonfiber mints and seeds into
  the upstream before its first start (`ARCH-R315`, `ARCH-R317`). The adapter reads it on each
  use and never writes it (`F14-R28`).
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
| `identity.source` | First-run state; create the administrator; the household's accounts; one account by name; an account's standing and limits; invite; take an invitation back; withdraw; when an invitation was sent; libraries; ratings; the country its ratings are named for; replace the administrator's password; allow; claimable; suspend; sessions for an account; whether devices sign in by code |
| `media.serve` | The guard and the locations (below); holdings for an account; what is playing; a title; a title's poster or backdrop for an account; part-way; record progress; open a device's session for an account; sign a device out; has an item; rescan; how many seasons and episodes each series holds; refresh one item; trust a proxy; allow origins; mint, list, date and revoke a key for an app |
| `library.curate` | Identity; download clients (register, update, set a field, test, list); root folders (register, list); quality profiles; run a command; hardlinks (read, set); records and carry; catalogue lookup, plan, add and indexer count; releases for a quality; apply a music format; queue; pipeline (library, find, history, queue, parts, stuck) |
| `download.usenet`, `download.torrent` | Transfers; pulling, stop, resume; throttled, restrain, moving; moved; `file_under`: each category and its completed folder; `filed`: every category and the completed folder it holds for it (below); seeding and letting a completed download go, and the port it takes peers on (read, set) (`download.torrent`); usenet accounts (`download.usenet`) |
| `indexer.search` | Register, list, test and re-key an application; indexers; aggregators (list, add) |
| `indexer.proxy` | Solve a challenge; whether it answers |
| `request.intake` | Establish an owner; initialised; configure identity; answers; search a page of titles a member may ask for; what one title is, its certification in a country and where its poster is published; ask on a member's behalf; requests, each with the id its title is found by; link members; member for an account; requesting; approval first; remove a member; telling and tell; fulfilment targets (list, add, move, test); the media server link (read, set); asking (read, set); left; quota; approves own; decide; hold and release requests; reachable; notices |
| `subtitles.fetch` | Watching; watch |
| `network.egress-guard` | Whether the tunnel is up; the forwarded port |
| `proxy.front` | Apply a routing table (household names, upstreams, TLS mode and certificate files); the table it serves; reload |
| `dashboard.show` | Apply a panel list (groups of entries and the page's widgets, below); the list it shows |
| `quality.sync` | Apply profiles to a curator; what it last applied |
| `archive.extract` | `watch`: every curator at once, each named by the media type it files, with its address, its key and its download folder, which is whom a finished extraction is handed back to, in place of those it watches; `working`: what it is extracting now |
| `stream.guard` | Apply a guard: the media server filler's declaration verbatim, where the upstream and the adapter are, the one proxy address the guard trusts and the pass service's address, where it asks about a live-stream pass (below); the guard it enforces, all of it read back; the certificate it presents |
| `invite.decline` | `hold`: the media server key it switches an invitation off with; `held`: that key's SHA-256; `apply the invitations it may decline`: how the media server tells a claimed account, and each invitation's token hash, its account, the name the account was made under, when it was issued and when it lapses |
| `request.gate` | Apply the routes it admits, for each curator and media server, each with the path segment it answers under and the upstream's supported majors; the routes it admits, each credential by its SHA-256 |

The capability types are neutral: none names a product. A curator is referred to by the
media type it files, never by its id.

## The guard and the locations

A filler of `media.serve` answers `GET /lemonfiber/media.serve/v1/declared` with:

- **The byte paths.** Path patterns under which the upstream serves bytes for an item,
  each with where the item's id sits, the shape an id has apart from the pattern, and
  the paths the pattern covers that name no item. A request whose item has another
  shape is answered `403`, and one on an exempt path is passed as any other path is, as
  Jellyfin's `/Videos/ActiveEncodings` and `/Videos/MergeVersions` are.
- **The question.** The request the guard makes to decide a byte request: a method and a
  path template with `{item}`, sent to the upstream or to the adapter, and the statuses
  that mean "may", "may not", "no session" and "not from there".
- **The refused paths.** Path patterns the guard answers `403` to without asking
  anything, because no question about an item covers them: a picture the upstream finds
  by a name rather than an id, such as an artist's, a genre's, a music genre's, a
  person's or a studio's, and a splash screen composed from every library.
- **The parameters that name another item.** For each byte path, the query parameters
  under which the upstream serves an item other than the one in the path, each marked
  refused or asked. A request carrying a refused one is answered `403`, as Jellyfin's
  `itemId` and `LiveStreamId` are. An asked one carries the shape the item it names
  has; the guard asks the question about that item as well as the item in the path, as
  for a trickplay playlist's `MediaSourceId`, and refuses it given twice, under another
  spelling or in another shape (`ARCH-R304`).
- **The token.** How a member's `Authorization: Bearer <token>` is presented to the
  upstream: as is, rewritten to a header template, or moved to a query parameter. The
  shape a token must have is a pattern, and a token that does not match is left as it
  came. The query parameters the upstream also reads a token from are named, as
  Jellyfin's `ApiKey` and `api_key` are; the guard carries one into the question as it
  came, and refuses more than one, another spelling or another shape.
- **The live-stream paths.** Path patterns under which the upstream serves a live
  stream's bytes, its playlists and segments included, each with where the live stream's
  id sits and the shape that id has. They are what a pass is asked about: the core hands
  them to the pass service, and the live stream a request names is the one a live-stream
  path places in its path.
- **The locations.** Templates for an item's stream, poster and backdrop, with
  `{base}` and `{item}`, built by the core against the household address and the guard's
  TLS port.
- **The ports.** The port the upstream listens on, and the upstream's own encrypted
  port where a household client expects it.

The core builds every location a member is given from the templates (`F14-R10`). A
declaration that admits a byte path without a question, or a template whose host is not
`{base}`, is refused at install.

## What the guard is applied

The core gives the filler of `stream.guard` one envelope (`apply a guard`), holding four
things and nothing else:

- **The declaration**, verbatim, as the media server's filler answered `declared`.
- **Where the upstream and the adapter are.** The address at which the guard reaches the
  media server, and the media server filler's adapter where it speaks the contract, each
  on the network the core's topology fixes for its ask of `media.serve` (`ARCH-R244`).
  The question goes to the one the declaration names, at that address.
- **The proxy it trusts.** The one address the guard believes when a request says which
  client it came from: the `proxy.front` filler's fixed address (`ARCH-R244`).
- **Where it asks about a pass.** The address of the core's pass service, at which it
  asks about a live-stream pass (below, `ARCH-R291`).

The guard enforces exactly what the envelope holds: the declaration unaltered and nothing
added to it. `the guard it enforces` answers the whole envelope back as the guard holds
it ([ADR-0050](../../00-overview/decisions/0050-a-contract-hands-its-filler-all-it-enforces-and-reads-back-no-secret.md), `ARCH-R207`, `ARCH-R303`).

## The live-stream pass

A live stream is not an item: the media server serves the bytes of whichever live stream
a request names, so the guard cannot ask the media server about one (`D11-R13`). Its
bytes are served on a pass the core issues instead.

- **The key.** The core generates the key it makes passes with, and the key never
  leaves lemonfiber's own processes. The guard never holds it, so the guard stays the
  stock filler of `stream.guard`.
- **The pass service.** The core confirms a pass through a service of its own: the
  lemonfiber binary of the running release, run as a service of the project with
  `lemonfiber pass`, holding the key read-only. It is on one network, which it shares with
  the `stream.guard` filler and nothing else (`ARCH-R312`), and `apply a guard` hands the
  guard its address. The core runs on the host and joins no network of the project, so no
  address on the guard's networks is the core's own.
- **The question.** For every request for a live stream's bytes, its playlists and
  segments included, the guard asks the pass service whether the pass the request carries
  is good for exactly the live stream the request names. Anything but a yes, and no
  answer, is a refusal.
- **The one place.** A pass travels in one fixed place, in one spelling, held to an exact
  shape. A request carrying it anywhere else, under another spelling or in another shape,
  is refused, so the guard and the core never read two different passes from one request.
- **The normal form.** Before it asks, the guard holds the request to the normal form it
  holds an item's byte route to: one canonical path, no byte the forward would re-escape,
  and one spelling of each parameter it reads. It asks about exactly the bytes it forwards.
- **The pass.** A pass names the member it was issued to and the moment it lapses, and
  carries an HMAC-SHA256 under the core's key over the live stream it is for, that member
  and that moment, written in base64url without padding. It lapses five minutes after it
  is issued, and the client asks for another before then. It travels in the `lfpass` query
  parameter, the one place a player fetching a playlist's segments carries it unaltered.
- **The answer.** The pass service answers `GET /pass`, asked with the request the guard
  forwards named in `X-Forwarded-Uri`: `204` where the pass in that request's `lfpass` is
  good for the live stream its path names and has not lapsed, and `403` for anything else.
  The live stream a path names is the one a live-stream path of the declaration places in
  it; a path no live-stream path covers names none, and is answered `403`.
- **The image.** The pass service runs `ghcr.io/lemonfiber/lemonfiber` at the running
  release, pinned by the digest resolved when the project is written, as every other image
  of the project is pinned. A build no image was published for writes the project without
  the pass service and says so.

## The completed folders

Both download clients file a completed download under one folder per category,
`/data/downloads/complete/<category>`, so a curator's downloads land in one folder
whichever client fetched them
([ADR-0052](../../00-overview/decisions/0052-a-curators-downloads-complete-into-one-folder-and-the-core-tells-each-part-what-it-holds.md)).
`file_under` hands the filler of `download.usenet` or `download.torrent` each category and
its completed folder, and `filed` answers every category the client holds and the
completed folder it files that category under.

The seed tells every download client its completed folders this way: an assembled client
through its in-process adapter, and a plugin's over its contract. It reads each back with
`filed`. A client holding a folder for a category other than the one lemonfiber last filed
there holds the operator's choice, and the seed keeps it and reports it drifted, as it does
every seeded value (`D1-R3`). The extractor is handed the folder `filed` reads back, not
the one lemonfiber wrote (`ARCH-R306`, `ARCH-R311`).

## The forwarded port

Where the egress guard's provider forwards a port, a torrent client inside the guard has
to take peers on it, and the port changes whenever the tunnel reconnects. The guard's
filler answers it as an operation of `network.egress-guard`: the port forwarded now, or
none. The core asks for it every minute while the stack runs, when the stack starts, and
after a reconnect the doctor observes, and acts when the answer differs from the last: it
sets the port, over `download.torrent`, on every filler of that capability running inside
the guard (`network.via`), and sets it back to none when forwarding ends, so a client
re-acquires a port correctly after a reconnect. Where it could not set the port, it says
the port was not passed rather than failing silently (`ARCH-R251`).

One pass does all of it, at one interval, and two processes run it each minute: the
hosted `watch` loop, for as long as the stack runs, and the dashboard's gather, while a
surface is open. A stack with neither has its port checked at the next thing that runs.
When the stack starts, and after every diagnosis whose VPN check ran against a running
stack, the pass compares the guard's port with each client's peer port and sets it where
they differ, whatever the last answer was. That is the reconnect the doctor observes: the
diagnosis fixes a client off the forwarded port itself, journals it and says so, and
offers no separate repair for it.

Nothing is mounted into the guard for this, no endpoint is opened for it to call, and the
guard holds no credential of the client's: the port crosses through the core, contract to
contract, so a substitute guard or a substitute client takes part on the same terms.

## A request service's owner

A request service may answer its own key only once it holds an owner, and the owner is
made by the first sign-in through the identity source, which nothing holding only the
key can do. `establish` is that step: it carries the identity source `configure
identity` carries, and the adapter makes its upstream hold an owner through it, so the
upstream answers the key the core minted for it. An upstream that already holds one, or
that answers its key from its first start, is answered `204` and left as it was. The
core asks it each time it sets up the request service's identity, before anything else
it asks the request service, and
`lemonfiber plugin record` asks it as the contract's first case. `configure identity`
still finishes the setting up (`ARCH-R319`).

The conformance cases name the member they link, find and ask for by 32 lowercase
hexadecimal digits, the shape a media server's account id takes, so an upstream that
holds members only by that id is asked about one it can hold.

## The request gate's routes

`apply the routes it admits` gives the filler of `request.gate` every route at once, one
for each curator, named by the media type it files, and one for the media server. A route
holds the path segment it answers under, its upstream's address, the upstream's majors the
stack supports (the gate forwards to no other, and a curator's route names none where the
gate knows its one supported API itself), the credential the gate presents to that
upstream, and the SHA-256 hash of each token the gate admits on it. Applying the routes applies the tokens:
a token whose hash no applied route holds is refused, and a rotation applies the new hash
beside the old until the new token is proved
([ADR-0032](../../00-overview/decisions/0032-the-request-service-reaches-the-arrs-through-a-gate.md) §2).

`the routes it admits` answers each route as the gate holds it, with each credential's
SHA-256, in lower-case hexadecimal, in place of its value. The core tells by it which of
the media server keys filed under the gate's name the gate holds, keeps that one and
revokes the rest, so the answer is exact rather than the short fingerprint the journal
shows. No answer of the gate's holds a credential's value (`ARCH-R305`).

## Decline, extraction and the dashboard

- **Decline.** `hold` gives the filler of `invite.decline` the one media server key it
  switches an invitation off with, and `held` answers that key's SHA-256, never its
  value. `apply the invitations it may decline` gives it every invitation it may act on,
  each as its token's hash, its account, the name the account was made under (which the
  page names), when it was issued and when it lapses, with how the running media server
  tells a claimed account from an unclaimed one: by the password it reports, by a
  password change after the issue time alone, or not known, under which nothing is
  removed. It acts on no other. The
  decline address an invitation carries is the filler's own page (`D6-R15`, `ARCH-R307`).
- **Extraction.** `watch` gives the filler of `archive.extract` every curator at once, in
  place of those it watches, each named by the media type it files, with the curator's
  address, its key and its download folder: the completed folder the download clients hold
  for the curator's category, as `filed` reads it back. The
  filler extracts what lands there and hands each finished extraction back to that curator
  itself, so the core makes no call for it. `working` answers what it is extracting now
  (`ARCH-R306`).
- **The dashboard.** The core applies the panel list to the filler of `dashboard.show`:
  over the contract where the filler speaks it, and where the filler is the assembled
  Homepage, which speaks none, through an in-process adapter that writes the files
  Homepage reads and reads them back, as a request gate speaking no contract is told
  through the files it reads. `apply a panel list` gives the filler groups of
  entries, each entry a name, an icon, a link and a description, with an optional
  reachability check and an optional widget, and the widgets along the page. Every widget
  is one the core names: a page widget, the machine's resources or a web search box, or a
  per-entry widget. The search box sends a search to the address the core setting
  `LEMONFIBER_DASHBOARD_SEARCH` holds, the terms appended to it, and to DuckDuckGo where
  none is recorded ([settings](web-api.md#settings)). None reads a credential, so the
  dashboard holds none (`C6-R20`). `the list it shows` answers the list applied
  (`ARCH-R308`).

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

- `lemonfiber plugin record` takes them, asking the adapter at its pin in front of a fresh
  container of the upstream at its pin ([ARCH-R296](plugin-manifest.md)). A pull request
  asks the adapter it built instead, and holds the recordings to what that adapter
  answers without writing them ([ARCH-R285](plugin-manifest.md)).
- `lemonfiber plugin conform` judges the recordings without running anything.
- Install repeats a live pass of the cases marked `live` against the running adapter.

### What a case asks

Each case in `conformance.json` carries `asked`: the body it posts, a value of its
operation's request type that the core declares beside the operation, so every adapter
speaking the contract is recorded answering the same questions. A case asked without
the key posts `{}`. `lemonfiber plugin record` asks the cases after the first run, each
contract's cases in the order its `conformance.json` lists them and the contracts in the
order the adapter's `speaks` lists them, except that a contract is asked after every
contract whose answers its cases' placeholders read. The upstream's first run happens
once, so a case asked under the key that the first run already asked is not asked again:
its recording is the first run's last answer to it.

A string in `asked` that is exactly one of these placeholders is filled before the case
is posted; any other string is posted as written.

| Placeholder | Filled with |
|---|---|
| `{minted}` | A credential minted for this case alone from the core's random source |
| `{upstream:<field>}` | `<field>` of the `upstream.json` the adapter holds, as the first run wrote it |
| `{minted:upstream:<field>}` | A credential minted for this case, written to `upstream.json` as `<field>` once the adapter answers the case with a success, as the core writes a credential the adapter replaced |
| `{<capability>@<major>/<case>#<pointer>}` | The string at the JSON pointer `<pointer>` in the answer to that case, asked earlier in the same run |

**A case bound to a kind of media is asked once for each kind.** An operation of
`library.curate` that takes a kind of media — a `Kind`, a `Record` or a root folder's media
type — publishes one case per kind it takes, named `<operation>-answers-<media type>`, each
asking what that kind's case asks. An adapter is asked, and judged on, the cases of the
media types the upstream it fronts files (`media_types`), so a curator of films records
what it does with films rather than refusing television (`ARCH-R320`).

**The download client the cases register is a real one.** `register_download_client`'s
case names the client in the native API of the download filler the bundle ships,
`sabnzbd`, as the core names the clients it registers. A curator tests a client before it
saves one and refuses one that does not answer, so while it records a curator
`lemonfiber plugin record` answers at the host the case names itself: reached from the
upstream's container alone, it answers the queries a curator tests a SABnzbd client
with, and nothing more. So the cases after it find a client the curator holds
(`ARCH-R321`).

**So is every other party the cases point the upstream at.** A case that hands the
upstream an identity source names its protocol as `jellyfin`, the native API of the media
server the bundle ships, and one that hands it a curator names the curator of series.
While it records, `lemonfiber plugin record` answers each party at the host and port the
cases name, reached from the upstream's container alone, in that party's native API, as
it answers what the upstream asks of it and nothing more, each on a port of its own. The
identity source signs in the owner the case names, whatever password the case minted for
it, makes and lists a key under the name it was asked to make one for, says which server
it is, and lists two accounts, the owner and the member the cases link. The curator
answers in the native API of the curator of series the queries an upstream tests a
curator with before it saves one, its release in every answer. So the state a later case
reads is the state install makes, from the cases alone, and no plugin seeds an upstream
for its recordings (`ARCH-R326`).

Every value a placeholder fills is a credential or an identifier the run made, so it is
scrubbed from every recording and from everything the run prints as `ARCH-R297` scrubs
the credentials a run makes. A placeholder naming a case not yet asked, a pointer the
answer does not hold, a value there that is not a string or a field `upstream.json` does
not hold fails the service at that case, naming the case and the placeholder
([ARCH-R296](plugin-manifest.md)).

**An answer holding a credential says where.** An operation whose answer holds a
credential the upstream issues, such as a session's token or a key it mints, names each
place in its answer that holds one as a JSON pointer, `""` where the whole answer is one,
and its contract document publishes them as `x-lemonfiber-secret`. `lemonfiber plugin
record` scrubs the value at each as it scrubs a credential its run read, so a token no
later case reads is redacted all the same (`ARCH-R327`).

A plugin whose recordings or live pass fail a case does not fill the capability, and
the refusal names the case. The first-party adapters are judged by the same runner
against the same cases. The stream guard's recorded byte cases are `stream.guard`'s
conformance suite.

## Facets the core asks of every provider

Two contracts say something about a part beside the capability it fills, and the core
asks each of every service that speaks it, never choosing among fillers ([ADR-0053](../../00-overview/decisions/0053-a-part-claimed-first-is-claimed-over-a-contract-and-an-indexer-source-is-pulled-over-its-own.md)).

**A part that belongs to whoever claims it first is claimed over `owner.claim@1`.**
`owner()` answers `Open`, `Settling`, `Ours` or `Theirs`, and `claim()` claims an `Open`
part with the credential in the adapter's `upstream.json`, answering what it then is. It
changes nothing that is `Ours` or `Theirs`, and the credential, the plugin's minted
secret, never crosses a call (`ARCH-R328`). The core asks `claim` at install's first run
and on every seed, waiting out `Settling` within its patience; a part `Open` after a claim
it recorded is drift, and a part `Theirs` is refused naming the plugin's secret. One
doctor check asks `owner()` of every speaker, and reset puts a claim back (`ARCH-R329`).
`lemonfiber plugin record` asks `claim` before any other case (`ARCH-R330`).

**A curator that reads its indexers from an aggregator is told it over `indexer.pull@1`.**
`aggregators()` lists the aggregators it reads from, and `add_aggregator` adds one by
name, address, protocol and key, the protocol being the aggregator's native API
(`ARCH-R332`). Where the indexer's app sync serves a curator's media, the indexer is told
about the curator; otherwise a curator speaking `indexer.pull@1` is told about the
indexer whose native API matches, and an `unsupported` answer leaves the two unpaired.
While it records, `lemonfiber plugin record` answers the aggregator at the host the case
names in its native API (`ARCH-R333`).

Each speaker's conformance proves its facet, so neither has a substitute (`ARCH-R331`).

## What a speaker cannot do

An operation the upstream an adapter fronts cannot perform answers `unsupported`.
Conformance passes it, and the core treats the operation as not offered for that filler,
by the answer's type alone (`ARCH-R334`).

## Versioning

A contract's major changes only when an operation is removed or its meaning changes.
Adding an optional field or an operation is a minor change the core speaks without a new
major. An added operation holds every speaker to record again, since a recording no case
answers and a case no recording answers both fail its conformance (`ARCH-R334`). The core speaks every major listed in `index.json`. When a second major arrives,
the first stays spoken until it is deprecated by announcement and then removed, as [versioning.md](versioning.md) holds for a plugin manifest.

## Requirements

| ID | Requirement |
|----|-------------|
| **ARCH-R199** | The core MUST generate an OpenAPI document and a conformance list per capability and major from the port types it calls, the list naming for each case the `asked` it posts, and a difference between the types and the published documents MUST fail the build. |
| **ARCH-R200** | A manifest's `speaks` MUST name only capabilities and majors listed in `contract/capabilities/index.json`, and an unlisted one MUST be refused by name. |
| **ARCH-R201** | Every operation MUST be at `/lemonfiber/<capability>/v<major>/<operation>` on the adapter's `listens` port, and every request MUST carry the plugin's key as a bearer token. |
| **ARCH-R202** | The core MUST mint each plugin's key from its own random source, write it to the adapter's configuration directory before the adapter starts, and use it for no other plugin. |
| **ARCH-R203** | An answer outside its operation's schema, status set, size bound or time bound MUST be refused, MUST NOT be read, and MUST be recorded against the plugin's conformance standing. |
| **ARCH-R204** | A refusal MUST be a problem document whose `type` the contract declares, and the core MUST map it to a code without reading its prose. |
| **ARCH-R205** | Every adapter MUST answer `about` and `ready`, and `about` MUST list the upstream releases it supports, each with the digest its recordings were taken from. |
| **ARCH-R206** | A filler of `media.serve` MUST answer `declared` with its byte paths, each with where the item's id sits, the shape an id has and the paths under it that name no item, its question, its token presentation with the query parameters the upstream also reads a token from, its refused paths, the query parameters on each byte path that name another item, each marked refused or asked with the shape of the item an asked one names, its location templates and its ports, and a declaration that admits a byte path without a question, or whose template host is not `{base}`, MUST be refused at install. |
| **ARCH-R207** | The core MUST give the filler of `stream.guard`, inside the envelope `apply a guard` carries (`ARCH-R303`), the media server filler's declaration unaltered and nothing added to it, and MUST build every location a member is given from the declared templates. |
| **ARCH-R208** | A plugin MUST hold a recording for every case its capabilities' conformance lists, taken at the digest its adapter declares, and `lemonfiber plugin conform` MUST judge them without running anything. |
| **ARCH-R209** | Install MUST run the live conformance cases against the running adapter, and a failed case MUST keep the plugin from filling the capability and MUST be named. |
| **ARCH-R210** | No capability type MUST name a product, and a curator MUST be referred to by the media type it files. |
| **ARCH-R211** | A contract's major MUST change only when an operation is removed or its meaning changes, and the core MUST speak every major its index lists. |
| **ARCH-R212** | An adapter's `listens` port MUST be published on `127.0.0.1` alone with no host port named, and the core MUST read the host port the engine gave it from the engine and MUST NOT reach an adapter at any other address. |
| **ARCH-R213** | A service that speaks a capability's contract MUST also provide that capability, and a manifest where one does not MUST be refused by name; that capability MUST be demonstrated by its contract and MUST NOT require a `[[claim]]`. |
| **ARCH-R214** | Where the service filling a capability speaks that capability's contract, the core MUST ask it over the contract alone and MUST NOT reach it through an adapter of its own. |
| **ARCH-R217** | A plugin's conformance recordings MUST sit at `conformance/<capability>@<major>/<case>.json` beside its manifest, one per case of each contract it speaks, each in the recording format of `ARCH-R120` and naming the digest the manifest pins for the service its adapter `fronts`, and `lemonfiber plugin conform` MUST judge each recorded answer as the core reads a live one and MUST name each case whose recording is absent, unreadable, of another request or of another digest. |
| **ARCH-R251** | The core MUST ask the filler of `network.egress-guard` for the forwarded port every minute while the stack runs, when the stack starts and after a reconnect the doctor observes; where the answer differs from the last, it MUST set it over `download.torrent` on every filler of that capability that takes `network.via` that guard, and MUST set it back to none when forwarding ends; where it could not set it, it MUST say the port was not passed rather than fail silently, and nothing MUST be mounted into the guard and no endpoint opened for it. The hosted `watch` loop MUST run that pass every minute for as long as the stack runs and the dashboard's gather MUST run the same pass at the same interval while a surface is open; after every diagnosis whose VPN check ran against a running stack the core MUST run one pass that sets the port on each client whose peer port differs from the guard's, journalled and said, and the doctor MUST NOT offer a separate repair for it. |
| **ARCH-R291** | The core MUST generate the key it issues live-stream passes with, and MUST confirm a pass only through its pass service: the lemonfiber binary of the running release, run as a service of the project with `lemonfiber pass`, holding the key read-only and answering only on the network it shares with the `stream.guard` filler (`ARCH-R312`); the key MUST NOT leave lemonfiber's own processes and the guard MUST NOT hold it, and the guard MUST ask the pass service about a pass on every request for a live stream's bytes (`D11-R13`). |
| **ARCH-R292** | A live-stream pass MUST travel in one fixed place in one spelling, held to an exact shape, and the guard MUST refuse a request carrying it anywhere else, under another spelling or in another shape. Before it asks the core, the guard MUST hold the request to the normal form it holds an item's byte route to (one canonical path, no byte the forward would re-escape, one spelling of each parameter it reads), and MUST ask about exactly the bytes it forwards. |
| **ARCH-R303** | `apply a guard` MUST carry the media server filler's declaration verbatim, where the guard reaches the media server and, where it speaks the contract, its filler's adapter, on the network the core's topology fixes (`ARCH-R244`), the one proxy address the guard trusts (`ARCH-R244`) and the pass service's address, at which it asks about a live-stream pass (`ARCH-R291`), and nothing else, and `the guard it enforces` MUST answer all four back as the guard holds them. |
| **ARCH-R304** | The filler of `stream.guard` MUST answer `403` to a request on a declared refused path without asking anything, and to a request on a byte path carrying a query parameter that path's declaration marks refused; for one carrying a parameter marked asked, it MUST ask the declared question about the item that parameter names as well as the item in the path and forward only where both answers are "may", and MUST refuse that parameter given more than once or in a shape the question cannot take. |
| **ARCH-R305** | Each route `apply the routes it admits` gives the filler of `request.gate` MUST hold the path segment it answers under, its upstream's address, the upstream's majors the stack supports, the credential the gate presents to that upstream and the SHA-256 hash of each token the gate admits on it, and the gate MUST refuse a token whose hash no applied route holds, and every call but its health with `403` while no route is applied; `the routes it admits` MUST answer each credential's SHA-256, in lower-case hexadecimal, and MUST NOT answer its value. |
| **ARCH-R306** | `watch` MUST give the filler of `archive.extract` every curator at once, in place of those it watches, and, for each curator named by the media type it files, that curator's address, its key and its download folder, the completed folder the download clients hold for the curator's category as `filed` reads it back (`ARCH-R311`), and the filler MUST hand each finished extraction back to that curator itself; `working` MUST answer what it is extracting now, and the contract MUST have no operation by which the core hands an extraction back. |
| **ARCH-R307** | `hold` MUST give the filler of `invite.decline` the media server key it switches an invitation off with, and `held` MUST answer that key's SHA-256, in lower-case hexadecimal, and MUST NOT answer its value; `apply the invitations it may decline` MUST give it how the media server tells a claimed account, and each invitation as its token's hash, its account, the name the account was made under, when it was issued and when it lapses, and it MUST act on no invitation the core did not apply. The decline address an invitation carries MUST be the filler's own page (`D6-R15`). |
| **ARCH-R308** | The core MUST apply the panel list to the filler of `dashboard.show`, over the contract where the filler speaks it, and where the filler is the assembled Homepage, which speaks none, through an in-process adapter that writes the files Homepage reads and reads them back; `apply a panel list` MUST give the filler groups of entries, each a name, an icon, a link and a description with an optional reachability check and an optional widget, and the page's widgets; every widget, on the page or on an entry, MUST be one the core names, the page's being the machine's resources and a web search box, and none MUST read a credential (`C6-R20`); the search box MUST send a search to the address the core setting `LEMONFIBER_DASHBOARD_SEARCH` holds, or to `https://duckduckgo.com/?q=` where none is recorded, and a value of that setting that is not an absolute `https` or `http` address MUST be refused naming the setting; `the list it shows` MUST answer the list applied. |
| **ARCH-R311** | `file_under` MUST hand the filler of `download.usenet` and of `download.torrent` each category and its completed folder, `/data/downloads/complete/<category>` for both, and `filed` MUST answer every category the client holds and the completed folder it files that category under; the seed MUST tell every download client its completed folders this way, through its in-process adapter where the client is an assembled part and over its contract where a plugin fills the capability, MUST read each back with `filed`, and where a client holds a folder for a category other than the one lemonfiber last filed there MUST keep it and report it drifted (`D1-R3`). |
| **ARCH-R319** | `request.intake@1` MUST declare `establish`, taking the identity source `configure_identity` takes and answering `204` once the upstream holds an owner and answers the adapter's upstream credential, `204` where it already did, and a refusal as `configure_identity` is refused otherwise; the core MUST ask it each time it sets up the request service's identity, before any other operation of the contract, and `lemonfiber plugin record` MUST ask it as the contract's first case. |
| **ARCH-R320** | An operation of `library.curate@1` that takes a kind of media MUST publish one conformance case per media type it takes, named `<operation>-answers-<media type>`, and an adapter MUST be asked and judged on exactly the cases of the media types its upstream's `media_types` names. |
| **ARCH-R321** | `register_download_client` MUST save the client it is handed, and its conformance case MUST name the client's protocol as the native API of the download filler the bundle ships, `sabnzbd`; while it records a curator, `lemonfiber plugin record` MUST answer at the host the case names, reachable from the upstream's container alone, the queries a curator tests a SABnzbd client with, and nothing more. |
| **ARCH-R326** | A conformance case that hands the upstream an identity source MUST name its protocol as `jellyfin`, and one that hands it a curator MUST name the curator of series; while it records, `lemonfiber plugin record` MUST answer at each host and port the cases name, each party on a port of its own, reachable from the upstream's container alone, in that party's native API: for the identity source, the sign-in of the owner the case names, a key made and listed under the name it was asked to make one for, what server it is, and a list of accounts holding that owner and the member the cases link; for the curator, the queries an upstream tests a curator with before it saves one, its release in every answer; and nothing more. |
| **ARCH-R327** | Each operation whose answer holds a credential the upstream issues MUST name every place its answer holds one as a JSON pointer, `""` where the whole answer is one, its contract document MUST publish them as `x-lemonfiber-secret`, and `lemonfiber plugin record` MUST scrub the value at each as a credential its run read (`ARCH-R297`). |
| **ARCH-R328** | `owner.claim@1` MUST declare `owner`, answering `Open`, `Settling`, `Ours` or `Theirs`, and `claim`, which claims an `Open` part with the credential in the adapter's `upstream.json` and answers what the part then is, and MUST NOT change a part that is `Ours` or `Theirs`; the credential MUST be the plugin's minted secret and MUST NOT cross a call. |
| **ARCH-R329** | The core MUST ask `claim` of every service speaking `owner.claim@1` at install's first run and on every seed, waiting out `Settling` within its patience, MUST report a part `Open` after a claim it recorded as drift and a part `Theirs` as refused naming the plugin's secret, MUST ask `owner` of every speaker in one doctor check, and reset MUST put a claim back. |
| **ARCH-R330** | `lemonfiber plugin record` MUST ask `claim` of a service whose adapter speaks `owner.claim@1` before any other case. |
| **ARCH-R331** | `owner.claim` and `indexer.pull` MUST be asked by the core of every service that speaks them and MUST NOT be chosen among fillers; each MUST be proved by its speakers' conformance, and neither has a substitute. |
| **ARCH-R332** | `indexer.pull@1` MUST declare `aggregators`, listing the aggregators a curator reads its indexers from, and `add_aggregator`, adding one by name, address, protocol and key, the protocol being the aggregator's native API. |
| **ARCH-R333** | Where an indexer's app sync serves a curator's media, the core MUST tell the indexer about the curator; otherwise it MUST tell a curator speaking `indexer.pull@1` about the indexer whose native API matches, and MUST leave the two unpaired where either answers `unsupported`; while it records, `lemonfiber plugin record` MUST answer the aggregator at the host the case names in its native API. |
| **ARCH-R334** | An operation the upstream an adapter fronts cannot perform MUST be answered `unsupported`; conformance MUST pass it, and the core MUST treat the operation as not offered for that filler, by the answer's type alone. |
| **ARCH-R314** | A live-stream pass MUST name the member it was issued to and the moment it lapses and MUST carry an HMAC-SHA256 under the core's pass key over the live stream it is for, that member and that moment, written in base64url without padding, and MUST lapse five minutes after it is issued; it MUST travel in the `lfpass` query parameter; the media server filler's declaration MUST carry the live-stream paths, each a path pattern with where the live stream's id sits and the shape that id has, and the core MUST hand them to the pass service; the pass service MUST answer `GET /pass`, asked with the forwarded request named in `X-Forwarded-Uri`, with `204` where the pass in that request's `lfpass` is good for the live stream a live-stream path places in that request's path and has not lapsed, and with `403` otherwise, a path no live-stream path covers included; it MUST run `ghcr.io/lemonfiber/lemonfiber` at the running release pinned by the digest resolved when the project is written, and a build no image was published for MUST write the project without it and say so. |

## Related

- [ADR-0041](../../00-overview/decisions/0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md)
- [ADR-0050](../../00-overview/decisions/0050-a-contract-hands-its-filler-all-it-enforces-and-reads-back-no-secret.md): what the guard, the gate, decline, extraction and the dashboard are applied
- [ADR-0052](../../00-overview/decisions/0052-a-curators-downloads-complete-into-one-folder-and-the-core-tells-each-part-what-it-holds.md): the completed folders, the dashboard's asker and the pass service
- [F14](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md)
- [capability-vocabulary.md](capability-vocabulary.md): what each capability is, and its probes
- [plugin-manifest.md](plugin-manifest.md): where `speaks` is declared
- [web-api.md](web-api.md): the generation this mirrors
