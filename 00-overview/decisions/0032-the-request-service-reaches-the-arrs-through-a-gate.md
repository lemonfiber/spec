# ADR-0032: The request service reaches the \*arrs and the media server through a gate, holding only the gate's tokens

**Status:** Accepted
**Date:** 2026-09-28
**Decided:** 2026-09-28, by the maintainer, Wessel Verheij: accepted with Seerr's removals of a title with its files forwarded through the gate rather than refused, and locked in 0.17.0.

## Context

[C6](../../10-functional/features/c-trust/c6-web-security.md)'s `C6-R20` lets a household-tier service hold a credential that is administrative on
another service only for one operation that must answer at any hour, held alone,
through a fixed set of calls, and confined. It then says: *no other household-tier
service may hold such a credential.* Seerr is a household-tier service
(`bind = "lan"`, published on `${LAN_BIND}:5055`), and it holds four.

**What Seerr holds, as the core seeds it on `lemonfiber` main:**

| Credential | How it gets there | Where Seerr keeps it |
|------------|-------------------|----------------------|
| Sonarr's API key | The core reads it from Sonarr's `config.xml` (`D1-R1`) and registers Sonarr with `POST /api/v1/settings/sonarr`, whose `apiKey` field Seerr requires | `settings.json` in `./config/seerr`, sent as `?apikey=` on every call |
| Radarr's API key | The same, through `POST /api/v1/settings/radarr` | The same |
| A Jellyfin API key named `Seerr` | On the sign-in that initialises it, Seerr mints one with the administrator's session (`POST /Auth/Keys?App=Seerr`) | `settings.json`, as `jellyfin.apiKey` |
| The Jellyfin administrator's access token | The same sign-in returns it | Its database, as its owner's `jellyfinAuthToken`, on device `BOT_seerr` |

It also receives the Jellyfin administrator's password in transit. The core signs in
to Seerr through Jellyfin as `admin`, with the password it minted
(`JELLYFIN_ADMIN_PASSWORD`), whenever it reads or writes Seerr: on every seed, every
household read, every invitation and every removal. Seerr forwards that password to
Jellyfin's `POST /Users/AuthenticateByName`.

Seerr sits on the stack's single, default network, with every other service. It can
reach Sonarr, Radarr, Jellyfin, the download clients and the indexers directly. The
stack declares no network of its own.

**What the keys yield.** Sonarr and Radarr each hold one API key, in `config.xml`, and
it authorises the whole of their v3 API. With it a caller can delete a series or a
film together with its files, add or change a download client or an indexer, and
change root folders. Both mount the data root read-write. A Jellyfin API key or an
administrator's session is full Jellyfin administration: create an administrator,
reopen CORS, install a plugin that runs inside the Jellyfin container, which also
mounts the data root read-write
([ADR-0029](0029-a-household-service-declines-an-invitation-with-one-key.md) §6). A
compromise of Seerr reaches the library three ways.

**No narrower credential exists.** Neither \*arr has a second key, a scope or a role.
Jellyfin's keys have no scope on any supported line (ADR-0029). The \*arrs offer no
operation on their key except replacing it (`ResetApiKey`).

**What Seerr calls.** Read from the pinned image's source (`seerr-team/seerr`
`v3.5.0`: `server/api/servarr/`, `server/api/jellyfin.ts`, `server/routes/auth.ts`,
`server/routes/avatarproxy.ts`):

- Fulfilment is a small set of \*arr calls: look a title up, add it at a quality
  profile and root folder, monitor what the member asked for, start its search, and read the
  library, the queue and the profiles back.
- Member sign-in needs no key at all. `AuthenticateByName` and Quick Connect answer to
  the member's own credential.
- The Jellyfin key serves library reads, the user list for importing members, and
  ending a member's Seerr session on sign-out.
- Two calls Seerr makes are removals rather than fulfilment: `DELETE /movie/{id}` and
  `DELETE /series/{id}` with `deleteFiles=true`, behind its *remove from Radarr* and
  *remove from Sonarr* actions.
- Seerr runs its own schedule: download tracking every minute, a Jellyfin
  recently-added scan every five minutes, full scans nightly.

**The requirements that meet here:**

- **[D1](../../10-functional/features/d-content/d1-seed.md)'s `D1-R17`** obliges each fulfilling \*arr to be registered with the request service,
  and in Seerr's API a registration is a key.
- **`D1-R7`** obliges Seerr to authenticate against Jellyfin. Seerr initialises only
  from a sign-in whose account is a Jellyfin administrator, and answers any other with
  `403` (`NOT_ADMIN`).
- **[G1](../../10-functional/features/g-ux/g1-interface-tiers.md)'s `G1-R5`** keeps lemonfiber's web surface from running persistently by default.
  Seerr sends a request the moment it is approved, including by policy (`D7`) at
  3 a.m., and polls the \*arrs every minute, so what answers it runs whenever the
  stack does.
- **`C6-R12`** forbids lemonfiber's UI proxying or tunnelling to admin service
  interfaces. A proxy in front of several administrative interfaces is one
  authentication bug away from exposing all of them.

The calls Seerr needs and the calls that do damage share paths. `PUT /series` carries
the series' path and root folder. `POST /command` carries any command name. A rule
that looks only at method and path cannot tell them apart.

## Decision

**A lemonfiber-built request gate sits between Seerr and Sonarr, Radarr and
Jellyfin. It holds their credentials; Seerr holds only tokens lemonfiber mints for the
gate. The gate publishes no port, is reachable only from Seerr, answers a fixed list
of calls, checks every write's body against what the upstream holds, and refuses
everything else without forwarding it. Seerr leaves the stack's default network, so
the gate is its only path to those three services.**

### 1. The service

- **Its image.** A lemonfiber-built image, built and published the way the decline
  service's is (ADR-0029 §1), pinned by digest (`E1-R1`). It is a bundled service, not
  part of the core: the core's surface does not run persistently by default (`G1-R5`),
  and Seerr calls whenever the stack runs.
- **Where it runs.** Service id `request-gate`, in the `media` profile beside Seerr,
  restarted by the stack's policy, with Seerr's criticality, `important`.
- **Its binding tier.** None: it publishes no port. Its manifest entry carries no
  `port` and no `bind`, as Gluetun's carries none, and its health is
  `kind = "container"`, answered by the image's own health check. `C6-R13`'s check,
  which asks what is actually listening, finds nothing of it on the host.
- **Its routes.** One listener, one route per upstream, each under the upstream's
  service id: `/sonarr`, `/radarr`, `/jellyfin`. Seerr is told each as a host, a port
  and a base path, which is how it takes every address.

### 2. What Seerr holds instead

**A token per route**: 256 random bits, minted by the core, one for each \*arr route
and one for the Jellyfin route.

| Question | Answer |
|----------|--------|
| **Where Seerr keeps it** | Where it keeps the key today: `apiKey` of each `radarr` and `sonarr` entry, and `jellyfin.apiKey`, in `./config/seerr/settings.json`. Seerr sends a \*arr token as `?apikey=` and the Jellyfin token in `Authorization: MediaBrowser … Token="…"`, both its own fixed behaviour. |
| **Where the gate keeps it** | Only as a SHA-256 hash, per route, in a read-only file the core writes. A copy of the gate's files yields no token. |
| **Where the core keeps it** | Nowhere. The core checks what Seerr holds by hashing the value Seerr's settings return and comparing it with the gate's file. |
| **What it can do** | The calls in §3 on its own route, through the gate. |
| **What it cannot do** | Anything on another route. Anything off the list. Anything at the \*arr or at Jellyfin directly, which does not know it. Anything from a host other than Seerr, because nothing else reaches the gate. |
| **Rotation** (`A7-R4`–`A7-R6`) | Mint a new token and add its hash beside the old one, so both are accepted. Write the new token to Seerr with `PUT /api/v1/settings/{radarr,sonarr}/{id}` or `POST /api/v1/settings/jellyfin`. Prove it with Seerr's own test route (`POST /api/v1/settings/{radarr,sonarr}/test`), which makes Seerr call the gate with it. For Jellyfin, `POST /api/v1/settings/jellyfin` itself makes Seerr call `GET /System/Info` with the new token before it saves. Only then remove the old hash. If the proof fails, the old token stays. |
| **Revocation** | Remove the hash. The gate answers `401` on that route from its next read of the file. Removing Seerr from the stack revokes all three. |

The core registers the tokens in the credential inventory of
[A7](../../10-functional/features/a-getting-started/a7-credential-management.md) (`A7-R1`): *request gate
tokens — used by Seerr — generated by lemonfiber*.

### 3. The calls the gate answers

The gate never forwards a request as it came. For each call on the list, it builds
the upstream request itself:

- the method and path;
- the query parameters named below;
- a body built from the fields named below;
- its own credential for that upstream.

Seerr's token, headers and any other parameter are dropped, `X-Forwarded-For` with
them, so Jellyfin logs the gate's address for every sign-in. The one exception is the
device a Jellyfin sign-in comes from (below). Paths match case-insensitively, as the
upstreams match them. **Every call not listed is refused with `403`, is not forwarded,
and is recorded.** So is a listed call whose parameters or body fail the checks below.
The list is read before the token: a call off the list is refused and recorded whatever
token it carries, and a call on the list without its route's token is answered `401`,
is not forwarded, and is not recorded.

**Sonarr and Radarr**, under `/{id}/api/v3`. Rows naming `/movie` answer on a Radarr
route only; rows naming `/series`, `/episode` or `/languageprofile` answer on a Sonarr
route only:

| Method | Path | Seerr's use | What the gate checks |
|--------|------|-------------|----------------------|
| GET | `/system/status` | Settings test, version | — |
| GET | `/qualityProfile` | Settings test, request options | — |
| GET | `/rootfolder` | The same | — |
| GET | `/tag` | The same | — |
| GET | `/queue` | Download tracking | `includeEpisode` only |
| GET | `/languageprofile` | Settings test, on Sonarr 3 only | — |
| GET | `/movie`, `/movie/{id}` | Radarr scan, availability sync | `tmdbId` only |
| GET | `/movie/lookup` | Before adding a film | `term` of the form `tmdb:{digits}` |
| POST | `/movie` | A film request | Body built from `title`, `tmdbId`, `year`, `titleSlug`, `qualityProfileId`, `profileId`, `minimumAvailability`, `rootFolderPath`, `monitored`, `tags`, `addOptions.searchForMovie`. The profile, the root folder and every tag must be ones Radarr holds, and the film must not be in Radarr already. |
| PUT | `/movie` | A request for a film Radarr holds, unmonitored and without a file | The gate reads the film itself and requires both conditions. It changes only `monitored`, `qualityProfileId`, `minimumAvailability` and `addOptions`, and adds tags. It keeps `path` and `rootFolderPath` as Radarr holds them, and sends no query string, so no `moveFiles`. |
| GET | `/series`, `/series/{id}` | Sonarr scan, availability sync | `tvdbId` only |
| GET | `/series/lookup` | Before adding a series, and a title lookup | `term` only |
| GET | `/episode` | Re-monitoring requested seasons | `seriesId` only |
| POST | `/series` | A series request | Body built from `tvdbId`, `title`, `qualityProfileId`, `languageProfileId`, `seasons[].seasonNumber`, `seasons[].monitored`, `tags`, `seasonFolder`, `monitored`, `monitorNewItems`, `rootFolderPath`, `seriesType`, `addOptions.ignoreEpisodesWithFiles`, `addOptions.searchForMissingEpisodes`. The same profile, root folder, tag and not-yet-held checks apply. |
| PUT | `/series` | More seasons of a series Sonarr holds | The gate reads the series itself. It changes only the series' `monitored` and each requested season's `monitored`, and each only from false to true, and adds tags. Everything else goes back as Sonarr holds it. |
| PUT | `/episode/monitor` | Re-monitoring requested episodes | `episodeIds`, and `monitored` must be `true` |
| POST | `/command` | Starting a search, refreshing download tracking | `name` is `MoviesSearch` with `movieIds` (Radarr), `MissingEpisodeSearch` with `seriesId` (Sonarr), or `RefreshMonitoredDownloads` (both), and nothing else |
| DELETE | `/movie/{id}` | *Remove from Radarr* | The id alone from the path, read as an integer, and the query parameters `deleteFiles` and `addImportExclusion`, each a boolean, and nothing else. No body. Recorded (§4). |
| DELETE | `/series/{id}` | *Remove from Sonarr* | The same |

**Jellyfin**, under `/jellyfin`. These calls carry no token, because they answer to
the member's own credential or to nobody's:

| Method | Path | Seerr's use | What the gate sends |
|--------|------|-------------|---------------------|
| GET | `/System/Info/Public` | The server's name | No credential |
| POST | `/Users/AuthenticateByName` | Sign-in, owner and member | Body built from `Username` and `Pw`, on Seerr's device |
| POST | `/QuickConnect/Initiate` | Quick Connect sign-in | No body, on Seerr's device |
| GET | `/QuickConnect/Connect` | The same | `secret` only, on Seerr's device |
| POST | `/Users/AuthenticateWithQuickConnect` | The same | Body built from `Secret`, on Seerr's device |
| GET, HEAD | `/UserImage` | A member's avatar | `UserId` only, no credential |

**Seerr's device.** Jellyfin opens a sign-in's session on the device the call names,
and Seerr ends it at sign-out by that device's id (`DELETE /Devices`, below). Each
sign-in therefore goes upstream as `Client="Seerr"`, `Device="Seerr"`, the gate's own
`Version`, and the `DeviceId` Seerr sent, where that id meets the `DELETE /Devices` rule.
A sign-in from any other device, or from none, is refused. Calls under the gate's own
key go upstream as `lemonfiber-request-gate`, so Jellyfin's device list names the
sessions Seerr opens as Seerr's and the gate's key as the gate's.

**No administrator session passes through.** Where a sign-in's answer is an
administrator's, the gate ends that session (`POST /Sessions/Logout`, presenting its
token). It hands Seerr the answer with `AccessToken` replaced by a random value that
opens nothing. `User.Policy.IsAdministrator` goes through unchanged, which is what
lets Seerr initialise. A member's answer goes through as it came: its token is the
member's own, under the member's policy. An answer the gate cannot read as either, and
an administrator's answer whose session it cannot end, go back to nobody: the gate
answers `502`.

These calls require the Jellyfin token, and go upstream under the gate's own key:

| Method | Path | Seerr's use | Query parameters |
|--------|------|-------------|------------------|
| GET | `/System/Info` | Settings test | — |
| GET | `/Users` | Importing members (`D6-R1`) | — |
| GET | `/Users/{id}`, `/Users/{id}/Views` | Library discovery | — |
| GET | `/Library/MediaFolders` | The same | — |
| GET | `/Items` | Library scans and item lookups | `SortBy`, `SortOrder`, `IncludeItemTypes`, `Recursive`, `StartIndex`, `ParentId`, `collapseBoxSetItems`, `ids`, `fields` |
| GET | `/Items/Latest` | The recently-added scan | `Limit`, `ParentId`, `userId` |
| GET | `/Shows/{id}/Seasons` | Library scans | — |
| GET | `/Shows/{id}/Episodes` | The same | `seasonId`, `fields` |
| DELETE | `/Devices` | Ending a Seerr-opened session at sign-out | `Id`, which must be one Seerr assigns: `BOT_seerr`, or a base64 value that decodes to `BOT_seerr` or to `BOT_seerr_` and a name |

An `{id}` in a path is letters, digits and hyphens only.

The gate answers two calls itself, and forwards neither:

| Method | Path | Answer |
|--------|------|--------|
| POST | `/Auth/Keys?App=Seerr` | `204`. No key is created. |
| GET | `/Auth/Keys` | One entry, `AppName` `Seerr`, whose `AccessToken` is a placeholder the gate accepts for nothing |

Seerr's initialising sign-in mints its Jellyfin key through these two calls. It stores
the placeholder, and Jellyfin never issues Seerr a key. The gate holds tokens only as
hashes, so it cannot hand over the real one. The core writes it straight after
initialisation (`POST /api/v1/settings/jellyfin`), which Seerr proves with
`GET /System/Info` through the gate before it saves. Until then, Seerr's Jellyfin
calls answer `401`.

**Removals are forwarded.** Seerr's *remove from Radarr* and *remove from Sonarr*
remove a title, and with `deleteFiles` its files, one id at a time. The gate builds
each removal from the id and the two named parameters, so a removal cannot carry
anything else, and records it before forwarding it. A removal it cannot record, it does
not forward. This is a removal the operator makes from Seerr. It sits beside
[H6](../../10-functional/features/h-glue/h6-library-cleanup.md)'s planned and confirmed
cleanup (`H6-R2`–`H6-R4`) rather than replacing it: H6 is lemonfiber
choosing what to remove, and this is Seerr passing on a removal somebody chose there.

**Refused, though Seerr makes them:** `POST /tag` and `PUT /tag/{id}`. Seerr makes them
only when a target tags requests by requester. The core does not turn that on.

**What the gate answers.** Every answer the gate makes itself has an empty body, except
the `503` that names an upstream version outside the supported ones (§6).

| Situation | Answer |
|-----------|--------|
| A call off the list, or on it with parameters or a body the checks refuse | `403`, not forwarded, recorded |
| A call on the list without its route's token | `401`, not forwarded, not recorded |
| The upstream file cannot be read | `503`, nothing recorded |
| A read the gate makes for its own checks is answered with an error | That status |
| The upstream does not answer, or answers a read for the gate's checks with something it cannot read | `502` |
| A sign-in answer the gate cannot read, or an administrator's whose session it cannot end | `502`, the answer goes back to nobody |
| A removal the gate cannot record | `503`, not forwarded |
| A forwarded call | The upstream's status and body, with `Content-Type`, `ETag` and `Last-Modified` and no other header |

### 4. Confinement

| Measure | What it removes |
|---------|-----------------|
| No published port. The gate sits on two `internal` networks only: `requests-gate`, shared with Seerr alone, and `gate-upstream`, shared with Sonarr, Radarr and Jellyfin. | Reaching the gate from the household network or from any other service. Reaching the internet from the gate. |
| Seerr leaves the default network. It is on `requests-gate`, and on `requests`, a bridge network shared with Homepage and Caddy that carries its published port, its egress to its metadata provider and notification services, and the two services that reach it. | Seerr reaching Sonarr, Radarr, Jellyfin, the download clients, the indexers or any admin-tier service except through the gate. Where the optional `proxy` profile runs, Seerr still reaches Jellyfin's household address through Caddy, with no credential, as any household device does. |
| Read-only root, non-root user, every kernel capability dropped, `no-new-privileges`, a memory limit | Persisting or escalating inside the gate, or exhausting the host |
| No data-root mount and no engine socket. One mount: its configuration directory, holding the upstream file (read-only), the token file (read-only) and the record (read-write) | Reading the library, or controlling the stack directly |
| A fixed list, bodies built rather than passed, and no route that forwards | Using the gate as a general path into the \*arrs or Jellyfin, which is `C6-R12`'s concern |
| One token per route, held only as hashes | Recovering a live token from the gate's files, or using the Jellyfin token against an \*arr |

**`C6-R12`'s concern, answered.** The gate is not lemonfiber's UI, but it is a proxy
in front of administrative interfaces, and a bug in it is a path to three services. What the bug can reach is
bounded three ways:

- The only caller is Seerr.
- Nothing is forwarded that the gate did not build.
- The dangerous shapes cannot be written, because the gate writes the body. That
  covers a path or root-folder change, an arbitrary command, a key operation, and
  anything aimed at a download client or an indexer.

**What this accepts.** A compromised Seerr can remove a title and its files through
the gate, one id at a time, and each removal is recorded. It cannot change a path or
a root folder, run a command off the list, touch a key, or reach a download client
or an indexer.

**Hand-over.** The core writes the upstream file: each route's upstream address and
credential. Sonarr's and Radarr's keys are the ones the core reads from `config.xml`.
Jellyfin's is a key the core mints for the gate alone
(`POST /Auth/Keys?App=lemonfiber-request-gate`), under ADR-0029 §4's reasoning:

- it can be revoked alone;
- it has one consumer;
- Jellyfin lists it by name;
- it carries a last-used date.

The files are owner-only (`A7-R8`), mounted read-only, and never passed as
environment, which `docker inspect` prints (`A7-R3`). The gate reads them on each
use. A regenerated \*arr key reaches it as it reaches every other consumer (`A7-R7`).
The gate's Jellyfin key rotates as the decline service's does (ADR-0029 §5).

**The record** holds each refused call and each forwarded removal: its time, route,
method and path. It never holds a token, a query string or a body. The doctor reads
it and reports every refusal and every removal since its last read (`C1`).

### 5. How `D1-R17` and `D1-R7` are met

**Fulfilment targets.** The core registers each fulfilling \*arr with Seerr, but at
the gate:

- `hostname` is `request-gate`, `port` is the gate's, and `baseUrl` is `/{id}`;
- `apiKey` is that route's token;
- the profile and root folder are the ones the core reads from the \*arr itself.

Seerr holds a Radarr and a Sonarr that answer everything it asks of one for
fulfilment. An \*arr absent from the stack has no route and no registration.
Duplicates are detected by the gate's address and route, not by label (`D1-R8`).
The connection is `wired` only when Seerr's own test route succeeds with it, which
exercises Seerr, the gate and the \*arr end to end (`D1-R4`, `D1-R18`).

**Identity.** The core initialises Seerr as today, with the Jellyfin address given
as the gate's Jellyfin route. The one sign-in that initialises Seerr carries the
administrator's password. The gate ends the resulting session and answers the key
mint from its own state, so Seerr keeps neither. The core then writes Seerr's Jellyfin
token (§3).

- **Rotation after initialisation.** The core then sets a new administrator
  password, so the one Seerr saw opens nothing.
- **Seerr's own key from then on.** Every later call the core makes to Seerr carries
  Seerr's own API key (`X-Api-Key`), which the core already reads from
  `settings.json`, and which Seerr answers as its owner. The administrator's password
  does not pass through Seerr again on lemonfiber's behalf.

**The stack's wiring is unchanged.** `seerr` still asks for `identity.source` and for
`library.curate` from each claimant. The gate is how the core carries those links,
not a capability of its own. A service that stands in for Seerr under
`request.intake` gets no gate route until its calls are listed and proved as §7
requires. Until then it is wired with no fulfilment targets, and the core reports
that.

### 6. Failure modes

| Situation | What happens |
|-----------|--------------|
| **The gate is down** | Seerr's calls fail to connect. A request Seerr tries to send is marked failed, as it is for an \*arr that is down. It surfaces as failing in lemonfiber's dashboard (`D4-R8`), and is sent when retried from Seerr. Its scans and download tracking fail and resume. Members cannot sign in, and Seerr sessions already open continue. The restart policy brings the gate back, and the doctor reports it from its container health. The core's own reads of Seerr do not pass through the gate and are unaffected. |
| **A token is revoked, or Seerr holds a stale one** | The gate answers `401` on that route and forwards nothing. The doctor hashes what Seerr holds and names the route whose token the gate does not accept. The next seed mints and proves a new one (§2). |
| **An upstream changes its API** | The gate reads each upstream's version: `GET /system/status` under its own key, and `GET /System/Info/Public`. It does so at start and after each change to the upstream file, and forwards only to a supported major: Servarr API v3, and the Jellyfin lines the stack declares ([ADR-0028](0028-a-supported-major-is-data-proved-by-its-own-recordings.md)), which the core writes into each Jellyfin route of the upstream file from the stack manifest. Outside them, every call on the route answers `503` naming the version found, and the doctor reports it, as `D1-R12` requires of seed. A change within a major reaches the gate only with a new pin (`E1`), and §7's recordings prove it first. |
| **Seerr calls an endpoint not on the list** | `403`, not forwarded, recorded. The doctor names the call. The feature behind it fails in Seerr, and the rest keeps working. No call is ever forwarded because it is unknown. |
| **The gate's Jellyfin key or an \*arr key stops authenticating** | The upstream answers `401` and the gate passes that status to Seerr. The doctor reports which credential failed, and the next seed re-reads or re-mints it. |

### 7. The list is proved, not asserted

The list in §3 is read from Seerr `v3.5.0`'s source. It is proved the way
ADR-0028 proves a supported major: by recordings. CI runs the pinned Seerr image
against the gate and pinned \*arrs and Jellyfin, and drives:

- an initialisation;
- a member's sign-in and sign-out;
- a request of each kind, approved;
- a removal of each kind, with its files;
- each scheduled scan;
- each settings test.

It fails on any call the gate refused that the list does not refuse on purpose. A
Seerr pin bump, or an \*arr or Jellyfin pin bump, reruns it.

### 8. Existing stacks: taking the keys back

The stack update that brings the gate in (`E1`) and the seed after it do the
following, in this order. They are journalled as a rotation (`A7-R4`–`A7-R6`), not as
seed writes:

1. **Write the gate's files** before the gate first starts: the upstream credentials,
   and the hashes of freshly minted tokens.
2. **Bring the stack up** with the gate and the new networks. From this point Seerr
   cannot reach the \*arrs or Jellyfin directly. A request it sends before step 3
   completes is marked failed and retried like any other.
3. **Re-point Seerr.**
   - Each Seerr target whose host is one of the stack's \*arrs moves to the gate's
     route and token (`PUT /api/v1/settings/{radarr,sonarr}/{id}`).
   - Seerr's Jellyfin moves to the gate's Jellyfin route and token
     (`POST /api/v1/settings/jellyfin`, which Seerr checks with `GET /System/Info`
     through the gate).
   - Each is proved through Seerr, by its test route or by that check, before
     anything is revoked.
   - A target pointing at something the stack does not run is left alone and
     reported.
4. **Revoke what Seerr holds in Jellyfin.** Delete the key named `Seerr`
   (`DELETE /Auth/Keys/{key}`). End the sessions on device `BOT_seerr`, whose token
   sits in Seerr's database.
5. **Rotate the \*arr keys.** Seerr's `settings.json` has held them, and every backup
   taken since holds them
   ([E3](../../10-functional/features/e-maintenance/e3-backup-restore.md), `E3-R2`).
   The core runs `ResetApiKey` on each \*arr, reads the new key from `config.xml`,
   and propagates it to every consumer (`A7-R7`, `A7-R6`):
   - the gate;
   - Prowlarr's application entries;
   - Bazarr;
   - the keys published for Recyclarr and Unpackerr.
6. **Rotate the Jellyfin administrator's password**, which every earlier seed sent
   through Seerr.

A consumer the core could not update is named in the report (`A7-R6`). Nothing is
revoked or rotated until step 3 is proved. A failure there leaves every credential
in place, with Seerr's targets pointing at services it cannot reach, and the
doctor reports it.

### 9. The requirements

`C6-R20` is amended in place, and the gate's own rows are `C6-R22` to `C6-R25` and
`D1-R19` to `D1-R21`. `0.17.0` locks all eight. `D1-R7` and `D1-R17` stand as written:
Seerr authenticates against Jellyfin, and each fulfilling \*arr is registered with it,
through the gate.

| Row | What it holds the build to |
|-----|----------------------------|
| `C6-R20` | No household-tier service but one holds an administrative credential or an administrator's session on another service; one that acts on another service's API does so through the gate |
| `C6-R22` | The gate's reach and confinement (§1, §4) |
| `C6-R23` | The fixed list, each request built by the gate, everything else refused (§3) |
| `C6-R24` | The upstream credentials held by the gate, and Seerr's tokens minted per route and kept as hashes (§2) |
| `C6-R25` | The record of every refusal and every removal, and the doctor reporting it (§4) |
| `D1-R19` | Seerr's targets and its Jellyfin at the gate, holding no key and no administrator's session (§5) |
| `D1-R20` | The core authenticating to Seerr with Seerr's own key, and the password rotated after initialisation (§5) |
| `D1-R21` | Taking the keys back from an existing stack (§8) |

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Keep the keys in Seerr and accept it**, naming Seerr as a second exception in `C6-R20` | Seerr is a household-facing web application with a sign-in form and outbound notification agents. The keys it would hold administer two services that mount the data root read-write, and a third whose plugins run beside the library. It makes more than twenty kinds of call, not one operation through a fixed set, so an exception for it is the end of the rule rather than a case of it. |
| **Per-service API-key scoping in the \*arrs** | None exists. Sonarr and Radarr hold one key each, valid on the whole v3 API, and the only operation on it is replacing it. Jellyfin's keys have no scope on any supported line (ADR-0029). There is nothing to configure. |
| **Replace Seerr** | The request services that fulfil through Sonarr and Radarr do it by calling their API with their key. A replacement moves the key; it does not remove it. It also costs the household the flow `D4` is written around. |
| **A path allowlist in the reverse proxy** | Caddy runs only in the optional `proxy` profile. A path rule cannot read a body: `PUT /series` with a new path, and `POST /command` with any command, share their paths with calls Seerr needs. The key still has to live in Seerr, or in Caddy, which is published to the household network. The proxy cannot end an administrator session or answer the key mint. |
| **lemonfiber performs requests itself and drops Seerr** | Fulfilment happens at any hour, and lemonfiber's surface does not run persistently by default (`G1-R5`). The household would lose the search, request and notification flow `D4` specifies, and `D4-R9` keeps the household out of lemonfiber altogether. |
| **The core answers these calls** | The same lifetime problem: the calls come whenever the stack runs, and the core's surface runs when asked. The core also holds every credential and the engine socket, so a bug in a surface Seerr reaches would reach all of it. |
| **Fold the gate into the decline service** | The decline service is published to the household network and holds one Jellyfin key and nothing else (ADR-0029). Adding the \*arr keys to it puts them behind a published port. The gate publishes nothing. |
| **Forward everything except a deny-list** | The \*arrs' API has hundreds of endpoints and gains more with each release. A deny-list is right only until the next release, and wrong silently. |
| **One token for all three routes** | Revoking it for one upstream breaks the other two. A token used on the wrong route could not be told from one used on the right one. |
| **Refuse administrator sign-ins at the gate after initialisation** | The operator could not sign in to Seerr's own settings, and nothing in lemonfiber replaces them. It keeps the administrator's password out of Seerr only for sign-ins the operator chooses to make. |
| **Initialise Seerr with a throwaway administrator the core then demotes** | Seerr's owner becomes an account nobody signs in with, and the operator's own sign-in still passes the real password through Seerr. Rotating the real password after initialisation closes the same gap with no second account. |

## Consequences

### Positive

- Seerr holds no credential of Sonarr, Radarr or Jellyfin. `C6-R20` describes the
  code.
- A compromise of Seerr yields the calls on the list: requesting, monitoring and
  searching for titles, removing a title with its files one id at a time, reading
  libraries and queues, and relaying sign-ins. It does not yield changing a path, a
  download client, an indexer, a root folder or a profile, running another command,
  touching a key, or any Jellyfin administration.
- Seerr reaches none of the download clients, the indexers or the admin-tier
  services.
- The core stops sending the Jellyfin administrator's password through Seerr, and the
  one sign-in that must is followed by a rotation.
- Each token is revocable and rotatable alone, without touching an \*arr key or any
  other consumer.
- Every refused call and every removal is recorded and reported, so a Seerr release
  that calls something new is seen rather than silently broken, and a removal nobody
  meant is seen too.

### Negative

- A new image, repository and publish pipeline, and the vulnerabilities that come with
  them.
- The gate holds three administrative credentials. A compromise of the gate is a
  compromise of Sonarr, Radarr and Jellyfin. Its containment narrows who can reach it
  and what it can reach, and does not narrow what those credentials allow.
- The gate is on the path of every member sign-in to Seerr. When it is down, nobody
  signs in to Seerr.
- Every Seerr, Sonarr, Radarr and Jellyfin pin bump reruns the recordings. A call a
  new Seerr needs fails at the gate until the list and its body checks change.
- A compromised Seerr can remove titles and their files, one id at a time, until the
  removals are seen in the record. Tagging requests by requester fails if the
  operator turns it on.
- Migration rotates the \*arr keys. The \*arrs replace a key in one step, so between
  the reset and the propagation every consumer holds the old key. `A7-R4`'s
  validate-before-destroy ordering cannot hold for a key the service regenerates.
- Seerr sees the administrator's password once, at initialisation, and at every
  sign-in the operator makes to Seerr's own settings with the administrator's account.
- The gate's body checks are a second reading of the \*arrs' resource shapes, kept in
  step with each pin.

### Neutral

- The household's experience does not change
  ([D4](../../10-functional/features/d-content/d4-request-flow.md)). Members sign in with their
  Jellyfin account and ask for things as before.
- Sonarr's and Radarr's keys are still full-API keys. The gate does not make them
  weaker, and the core and the admin-tier consumers keep using them directly.
- `stack.toml`'s `[[wiring]]` entries for `seerr` do not change. The contract
  [jellyfin-seerr-identity](../../20-architecture/contracts/jellyfin-seerr-identity.md)
  describes the arrangement this replaces, and changes with the build: the gate's
  Jellyfin route is the address Seerr is given, the gate answers the key mint, and
  the core's later calls carry Seerr's API key.
- The stack gains its first named networks. C6's tier table gains a service that
  publishes nothing, and the stack manifest's `port` is omitted for a service whose
  only listener is on internal networks; the
  [stack-manifest](../../20-architecture/contracts/stack-manifest.md) contract says so.
- D1's wiring graph rows *Jellyfin → Seerr* and *Sonarr, Radarr → Seerr* are made
  through the gate.
- A7's inventory table stops listing Seerr as a user of service API keys, and gains
  the gate's tokens and the gate's Jellyfin key.

## Revisit if

- Sonarr, Radarr or Jellyfin offer a key scoped narrower than their whole API that
  covers the calls on the list.
- A supported request service fulfils through something other than the \*arrs' API
  with their key.
- lemonfiber's surface comes to run persistently by default, which reopens whether
  the gate belongs in the core.
- A Seerr release needs a write whose body the gate cannot check against what the
  upstream holds.
- Remote access (`I1`) makes Seerr reachable off the household network.
