# ADR-0060: The request gate asks a curator over its contract, and answers Emby beside Jellyfin and Plex

**Status:** Accepted
**Date:** 2026-11-06
**Decided:** 2026-11-06, by the maintainer, Wessel Verheij:

- the request gate reaches each curator over `library.curate`, through the curator's
  adapter, rather than in Sonarr's and Radarr's own API, so a series or a film is
  requested from whatever curator files it;
- the gate's identity-source ask names Emby beside Jellyfin and Plex, and the gate
  answers an Emby route.

**Amends**:

- [ADR-0032](0032-the-request-service-reaches-the-arrs-through-a-gate.md): §1, a curator's
  route is named by the media type it files and reaches the curator's adapter, and the
  media server's route may be an Emby route; §2, the gate presents a request key to each
  curator's adapter and holds no curator's own key; §3, each Sonarr- or Radarr-shaped call
  is answered by the gate itself or built as a `library.curate` operation; §4, the gate
  shares a network with each curator's adapter and with no curator; §6, a curator's route
  is supported where its adapter speaks the request operations; §7, the calls are proved
  against each curator that files series or films.

## Context

The request service, Seerr, files a request for a series with a Sonarr and a request for
a film with a Radarr. It knows no other curator. The gate stands between them
([ADR-0032](0032-the-request-service-reaches-the-arrs-through-a-gate.md)) and builds each
call in Servarr API v3 under the curator's own key.

Every part is a plugin, and the core speaks contracts
([ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md)). The gate's
`library.curate` ask names no `native`, so it is filled by each curator's adapter
(`ARCH-R253`). A curator whose upstream speaks another API, as Medusa does, fills
`library.curate` for series, and `F14-R14` proves `library.curate` by Medusa standing in
for Sonarr. While the gate speaks Servarr to the upstream, a series request reaches no
curator once Medusa files series.

The gate also answers Seerr in the media server's own API: a Jellyfin route and a Plex
route. Seerr signs its household in against Jellyfin, Plex or Emby. Emby proves
`media.serve` and `identity.source` for `F14-R14`, so the gate needs an Emby route for a
member to sign in to the request service on a stack whose media server is Emby.

**What Seerr asks of a curator.** Read from the pinned image's source (`seerr-team/seerr`
`v3.5.0`: `server/api/servarr/`, `server/lib/scanners/sonarr`, `server/lib/scanners/radarr`,
`server/lib/availabilitySync.ts`, `server/lib/downloadtracker.ts`,
`server/subscriber/MediaRequestSubscriber.ts`, `server/routes/service.ts`,
`server/routes/media.ts`):

- **Settings and request options:** the system status, of which it reads the version's
  major and `urlBase`; the quality profiles; the root folders; the tags; and, where the
  major is `3` or lower, the language profiles.
- **Scans and availability:** every title held, each by its TheTVDB or TMDB id, with its
  id, title and slug; per series, each season's monitored flag, files and episode count;
  per film, whether it has its file and is monitored. One title by id answers `404` where
  it is not held, and Seerr reads that as gone.
- **A request:** the title looked up by `tvdb:<id>` or `tmdb:<id>`; added where not held,
  at a profile, a root folder and the seasons asked; where held, monitored with the
  seasons asked, with every unmonitored episode of them, read through `GET /episode` and
  written through `PUT /episode/monitor`; then searched for.
- **Download tracking:** `RefreshMonitoredDownloads`, then the queue, each item by the
  title's id, with its size, what is left, its estimated completion, its status, its
  title, the download client's id for it and, for an episode, the episode.
- **A removal:** the title by its catalogue id, then removed with its files and no import
  exclusion.
- **A title lookup** by name, which Seerr hands its page to choose a series by.

## Decision

**The gate answers Seerr in Servarr API v3, as ADR-0032 lists the calls, and builds each
call as a `library.curate` operation of the curator that files the route's media type,
asked of its adapter under a request key the core mints for the gate on that adapter.
The gate holds no curator's own key and reaches no curator's upstream.**

### 1. Routes

A curator's route answers under the media type it files, `/tv` or `/movies`, and Seerr is
told the route as a Sonarr for `/tv` and a Radarr for `/movies`, at the gate's host and
port. The route reaches the adapter of the curator that fills `library.curate` for that
media type, at the address the gate's ask settles to (`ARCH-R253`).

The media server's route is the one for the API the media server declares as its
`native`, among those the gate's ask names: `jellyfin`, `emby` or `plex`
(`ARCH-R380`, `ARCH-R387`).

### 2. The request key

The core mints one request key for the gate on each curator's adapter, writes it beside
the plugin's own key in the adapter's configuration directory, and hands it to the gate
as the route's credential. The adapter kit admits it on the request operations alone, and
answers `disallowed` to it on every other operation of every contract (`ARCH-R386`). It
is rotated as ADR-0032 §2 rotates a token: the new key is admitted beside the old one,
proved by Seerr's own test of the route, and only then is the old one revoked.

### 3. The request operations

`library.curate@1` declares them from minor `1`, each taking a kind of media (`tv` or
`movies`) and asked, by its cases, once for each kind the curator files (`ARCH-R320`).
A title is named by its catalogue reference: its TheTVDB id for a series, its TMDB id for
a film (`ARCH-R385`).

| Operation | Answers or does |
|---|---|
| `catalogued` | The title its catalogue holds by a reference, with the curator's own id where it holds it, or none |
| `titles` | Every title it holds |
| `held_title` | One title it holds, by its own id, or none |
| `request` | Adds a title it does not hold, at a root folder and a quality profile it holds, monitoring the seasons named and no other, numbering it as anime where asked and monitoring seasons that air later where asked; monitors a title it holds, the seasons named and every unmonitored episode of them, changing nothing else; searches for what it then wants where asked; answers the title |
| `search` | Searches for what it wants of one title it holds |
| `remove` | Removes one title it holds, with its files, excluding nothing from a later import |
| `downloading` | What it is downloading of one kind: for each, the title's id, the release's name, its size and what is left in bytes, when it is expected to complete, its state (`queued`, `paused`, `downloading`, `completed`, `warning` or `failed`), the download client's id for it, and for an episode its season, number and title |

A title answers its reference, the curator's id where held, its name, its year, whether
it is monitored, how many files it holds, and, for a series, each season's number,
whether it is monitored, how many of its episodes have files and how many episodes it has.
`quality_profiles`, `root_folders` and `lookup` are also asked under the request key.

### 4. Each call Seerr makes, and what answers it

| Seerr's call | What the gate does |
|---|---|
| `GET /system/status` | Answers itself, with the version of the API the route presents, `4` on `/tv` and `5` on `/movies`, so Seerr asks no language profile, and an empty `urlBase` |
| `GET /qualityProfile` | `quality_profiles` |
| `GET /rootfolder` | `root_folders`, each answered with no free or total space and no unmapped folder |
| `GET /tag` | Answers itself, an empty list |
| `GET /languageprofile` | Refused, as every call off the list is |
| `GET /series/lookup`, `GET /movie/lookup` with `tvdb:<id>` or `tmdb:<id>` | `catalogued` |
| `GET /series/lookup` with a name | `lookup` |
| `GET /series`, `GET /movie` | `titles`; with `tvdbId` or `tmdbId`, the title of that reference among them alone |
| `GET /series/{id}`, `GET /movie/{id}` | `held_title`, and `404` where it answers none |
| `POST /series`, `POST /movie` | `request`, from the reference, the profile, the root folder, the seasons the body monitors, `seriesType` `anime` as anime, `monitorNewItems` `all` as later seasons monitored, and the search the body asks; the profile and root folder must be ones `quality_profiles` and `root_folders` answer, and the title must not be held |
| `PUT /series`, `PUT /movie` | `request` for the title the body names, held, with the seasons the body monitors; a film must be held unmonitored and without its file |
| `GET /episode` | Answers itself, an empty list, since `request` monitors the episodes of the seasons it names |
| `PUT /episode/monitor` | Refused, as every call off the list is |
| `POST /command` `RefreshMonitoredDownloads` | Answers itself, accepted, since `downloading` answers as of when it is asked |
| `POST /command` `MissingEpisodeSearch`, `MoviesSearch` | `search`, for the series or each film named |
| `GET /queue` | `downloading`, each answered with the title's id as `seriesId` or `movieId`, its time left from when it is expected to complete, and its episode where it names one |
| `DELETE /series/{id}`, `DELETE /movie/{id}` | `remove`, only with `deleteFiles` true and `addImportExclusion` false, recorded before it is asked as ADR-0032 §3 records a removal |

Each answer is held to the contract before the gate reads it, and an adapter answering
`unsupported` to a request operation makes the route answer `503` with the plain-text body
`The curator filing <media type> does not take requests`, which the doctor reports.

### 5. What Seerr still sees

Seerr reads the same requests, availability, download progress and removals it read of a
Sonarr and a Radarr, from whichever curator files the media type. It no longer sees:

- the curator's own version and `urlBase`: the route answers the API it presents;
- free space on a root folder, or folders the curator has not mapped;
- tags, so tagging requests by requester stays off as ADR-0032 §3 keeps it;
- its settings for language profile, season folders and a film's minimum availability,
  which reach no curator: the curator files and grabs by its own;
- a link to the curator's own page that opens: the slug it answers is the reference.

### 6. The Emby route

The media server's route is an Emby route where the media server declares `native =
"emby"`. Seerr speaks to Emby as it speaks to Jellyfin, with its own `Version` of `1.0.0`,
so the route answers the calls ADR-0032 §3 lists for Jellyfin, on the same terms, under
`/emby`, in Emby's own API, with the gate's key on the media server minted over
`media.serve` as the Jellyfin route's is. Emby's supported majors are the stack's, as a
Jellyfin route's are (ADR-0032 §6). The identity source the core hands the request
service names the protocol `emby` and the gate's Emby route (`ARCH-R387`).

### 7. Proof

ADR-0032 §7's recordings run against each curator that files series or films, so Seerr's
calls are proved through the gate against Sonarr, Medusa and Radarr, and its sign-ins
against Jellyfin, Emby and Plex.

## Consequences

### Positive

- A series or a film is requested from whatever curator files it, so a substitute for a
  curator keeps the household's requests working, and `F14-R14` proves it.
- The gate holds no curator's key. A compromised gate can ask each curator's adapter the
  request operations and nothing else: no download client, indexer, root folder or key
  is reachable from it.

### Negative

- Every curator filing series or films speaks seven more operations, and the adapter kit
  admits a second key.
- Seerr's settings that only a Sonarr or a Radarr takes reach nothing, so the operator
  sets a film's minimum availability and the season folders in the curator.

### Neutral

- The gate answers four calls itself rather than forwarding them.

## Alternatives considered

| Option | Why it lost |
|---|---|
| The gate's curator ask names `native = "servarr"` | A substitute curator speaking another API leaves series requests unfilled, and the substitution's reading says so; the user chose requests that follow any curator |
| The gate presents the plugin's own key to the adapter | That key opens every operation of every contract the adapter speaks |
| Leave Seerr's sign-in out of the Emby proof | The household's sign-in to the request service on an Emby stack stays unproved |

## Related

- [ADR-0032](0032-the-request-service-reaches-the-arrs-through-a-gate.md)
- [ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md)
- [ADR-0057](0057-plex-serves-the-household-without-handing-out-its-owners-token.md)
- [C6](../../10-functional/features/c-trust/c6-web-security.md): `C6-R22` to `C6-R24`, `C6-R29`, `C6-R30`
- [capability contracts](../../20-architecture/contracts/capability-contracts.md): `ARCH-R305`, `ARCH-R380`, `ARCH-R385` to `ARCH-R387`
- [F14](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md): `F14-R14`
