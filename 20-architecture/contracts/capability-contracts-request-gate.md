# Contract: the request gate's routes

**Status:** Accepted

Part of the [capability contracts](capability-contracts.md): the routes the filler of
`request.gate` admits, what a curator and a member reach through it, and what a filler
tells the core. The requirements it describes are listed with the rest of the contract's,
under [Requirements](capability-contracts.md#requirements).

## The request gate's routes

`apply the routes it admits` gives the filler of `request.gate` every route at once, one
for each curator, named by the media type it files, and one for the media server. A route
holds the path segment it answers under, its upstream's address, the upstream's majors the
stack supports (the gate forwards to no other, and a curator's route names none), the
credential the gate presents to that upstream, the SHA-256 hash of each token the gate
admits on it, and, on the media server's
route, the SHA-256 of each certificate the media server's internal TLS port may present,
the one port the gate reaches it at (`ARCH-R345`). Applying the routes applies the tokens:
a token whose hash no applied route holds is refused, and a rotation applies the new hash
beside the old until the new token is proved
([ADR-0032](../../00-overview/decisions/0032-the-request-service-reaches-the-arrs-through-a-gate.md) §2).

Where Plex is the media server, the media server's route is a Plex route. The gate answers
it at a bare host and port, port `32400` on the stack's network, in Plex's own API, rather
than under a path segment. The route holds:

- the request service's own managed account token as the credential the gate presents to
  Plex (`ARCH-R370`);
- the SHA-256 of each certificate Plex's internal TLS port may present;
- the link mode `PLEX_LINK_MODE` names (`C6-R26`), which says what else it holds and what
  the gate admits:
  - `managed`: the hash of that token;
  - `owner`: the plex.tv account id of the account that claimed Plex, and the gate admits
    a token plex.tv answers as that account;
  - `fronted`: the hash of the gate token, the request service's own account as plex.tv
    knows it, each household member by the plex.tv id and the name `identity.source`'s
    `household` answers, and the server's name and identifier as `listed_as` answers them,
    which the gate answers plex.tv's calls from, each member with this server's identifier
    (`C6-R28`).

The core applies the route on every seed, so the household it holds follows the household
(`ARCH-R380`).

A curator's route answers under the media type the curator files, `tv` or `movies`. Its
upstream is the curator's adapter, reached at the address the gate's ask settles to, and
its credential is the request key the core minted for the gate on that adapter, never the
curator's own key. The gate builds each of the request service's calls on it as a request
operation of `library.curate`, as [ADR-0060](../../00-overview/decisions/0060-the-request-gate-asks-a-curator-over-its-contract.md) maps them (`C6-R29`).

Where the media server declares `native = "emby"`, the media server's route is an Emby
route, answered under `emby` in Emby's own API, on the terms the Jellyfin route is
answered on (`C6-R30`).

### A curator's requests

`library.curate@1` declares, from minor `1`, the operations the request gate asks a
curator on the request service's behalf. Each takes a kind of media, `tv` or `movies`, and
is asked once for each the curator files (`ARCH-R320`). A title is named by its catalogue
reference, its TheTVDB id for a series and its TMDB id for a film, as `lookup` answers it
for those kinds too, and answered with that
reference, the curator's own id where it holds the title, its name, its year, whether it
is monitored, how many files it holds and, for a series, each season's number, whether it
is monitored, how many of its episodes have files and how many episodes it has.

| Operation | Answers or does |
|---|---|
| `catalogued` | The title its catalogue holds by a reference, or none |
| `titles` | Every title it holds |
| `held_title` | One title it holds, by its own id, or none |
| `request` | Adds a title it does not hold at a root folder and a quality profile it holds, monitoring the seasons named and no other, numbering it as anime and monitoring later seasons where asked; or monitors a title it holds, the seasons named and every unmonitored episode of them, changing nothing else; then searches where asked, and answers the title |
| `search` | Searches for what it wants of one title it holds |
| `remove` | Removes one title it holds with its files, excluding nothing from a later import |
| `downloading` | What it is downloading of one kind, each with the title's id, the release's name, its size and what is left in bytes, when it is expected to complete, its state (`queued`, `paused`, `downloading`, `completed`, `warning` or `failed`), the download client's id for it, and an episode's season, number and title |

A request naming a root folder or a quality profile the curator does not hold is refused,
as is a `search` or a `remove` of a title it does not hold. The core asks none of these:
the request gate does, under the request key (`ARCH-R385`, `ARCH-R386`).

### A member's music and books

`music.curate@1` and `books.curate@1` carry what a household member asks for of music and
of books, which the request service does not carry (`D4-R22`). The core asks them on the
member's behalf, under the key its install minted for the core. Everything else a curator
of either does, its download clients, folders, queue and pipeline, stays on
`library.curate@1`, whose title operations stay series and films alone. Each operation
takes a unit: for music an `album` (a release group) or an `artist`, for books a `book`, an
`author` or a `series`. A candidate is named by a reference the curator's adapter gives it,
a string, which the adapter may compose from what its curator knows the candidate by, so that
`candidate` can find it again, with its name, its artist or author, its year, a cover where it has one, for a
book the format the household files it in, and its state: `here` where the house holds all of
it, `partly-here` where it holds some of an artist, an author or a series, `asked` where the
curator already wants it, or `may-ask`.

| Operation | Answers or does |
|---|---|
| `lookup` | A page of candidates of one unit found by words, each with where the next page begins until there is none |
| `candidate` | One candidate of one unit by the curator's reference for it, as `lookup` would answer it, or nothing where its catalogue holds no such reference |
| `request` | Asks for one candidate by its unit and reference, at a root folder and the profiles it holds, monitoring an album or a book alone, or every one of an artist, an author or a series and those that come later, then searching where asked; answers the candidate as it now stands |
| `profiles` | The units of its medium it answers for as it is configured now, and the root folders and the profiles a request may name: quality, and for music metadata |
| `remove` | Removes one candidate it holds by its unit and reference with its files, excluding nothing from a later import: an album or a book alone, or an artist, an author or a series with every title of theirs it holds; an artist or an author `request` added only to hold an album or a book goes with it where nothing else of theirs is held |

A request naming a root folder or a profile the curator does not hold is refused, as is
one whose reference its catalogue does not hold, and a `remove` of a candidate it does not
hold.

The core journals every ask it sends, whether at once or once the operator approves it.
Undoing one asks `remove` for it where the curator held none of it before the ask, and takes
the ask the core keeps off the household list; an ask for the rest of an artist, an author or
a series held in part is journalled with nothing to undo, and the history says so.

A curator that cannot carry an ask exactly as asked MAY carry it as near as it can, and its
plugin MUST say how in its documentation: a request it cannot make without searching searches,
and a series whose later books it can follow only through each author's own series follows them
that way. A unit it cannot answer at all, or cannot answer as it is configured, is refused as
unsupported, with a sentence naming what it lacks, and is left out of the units `profiles`
answers.

### Telling the core what happened

`library.curate@1` and `media.serve@1` carry `events`, so the stack's own event sources reach
the back-ends the household chose without anybody configuring a service's notifications by hand
(`B9-R4`). `events` takes the core's address, the digest of the certificate the core presents
there, which the adapter pins, and a key the core minted for that one filler. From
then on the adapter hears what its upstream did, by push or by poll as the section below
says, and sends each happening to that address with that key as one of
the neutral events below, refusing any connection that presents another certificate. Asked
again it replaces the address, the digest and the key; asked with none of them it stops. The adapter sends nothing it was not asked to.

| Event | Sent by | When |
|---|---|---|
| `imported` | a curator | A title, an episode, an album or a book it fetched is imported into the library |
| `failed` | a curator | A grab or an import failed, with the upstream's own reason |
| `health` | a curator or the media server | The upstream raised a problem about itself, or cleared one, with its own words |
| `added` | the media server | A title was added to a library |

Each event names the title by the curator's or the server's reference and its name, never a
member, an account or what anybody is watching. The media server sends nothing of playback.

#### How an adapter hears its upstream

An adapter hears its upstream one of two ways, and `events` answers which, so seed can say it
beside the wiring (`ARCH-R411`):

- **Push**, where the upstream's own notification connection can reach the adapter and is
  configured or configurable without installing anything into it. The adapter registers one
  connection pointing at itself, at a path carrying a random secret it made for that
  connection, and accepts a push nowhere else. Each push it hears is checked against the
  upstream's own API before it is sent on, so a forged push sends nothing the upstream did not
  do. On its own start, and once a day, it also reads the upstream's history from its cursor
  and sends whatever push missed while it was down.
- **Poll**, where no push is configured: the upstream offers no notification connection, its
  connection cannot carry a request to an arbitrary address, or it needs something nobody
  installed or paid for. The adapter reads the upstream's own history or activity, newest
  after its cursor, every `every` seconds the core asked for (`ARCH-R412`).

An adapter never installs a plugin into its upstream, enables a paid feature or turns on a
notification type that carries what anybody watches, in order to push. Where push becomes
available later, a plugin installed or a licence added, the next `events` ask moves it to push.

**The cursor.** In either way, the adapter keeps a cursor: the upstream's own position of
the newest happening it has sent, an id where the upstream numbers its history and its own
timestamp with the item's id where it does not. The cursor sits in a file beneath the
adapter's configuration directory, written after each send the core answered, so a restart
neither repeats nor loses one. A first ask, with no cursor kept, sets the cursor at the
upstream's newest happening and sends nothing older, so wiring a stack never sends its whole
library. A cursor naming a position the upstream no longer holds, its history pruned or
reset, moves to the upstream's newest happening and the adapter says so in its log. After
time away, everything after the cursor is sent oldest first, a page at a time, with no limit
on how far back. Asked with none of address, digest and key, the adapter stops and drops
its cursor, so a later ask starts from the newest happening again. Asked again with another
address, digest or key, it keeps its cursor.

**The interval.** `every` is the poll interval the core asks, in whole seconds, from 15 to
3600; the core asks `LEMONFIBER_EVENTS_POLL`, 60 where unset (`ARCH-R412`). An adapter
hearing by push takes it as the interval of nothing and keeps the daily reconcile.

| Upstream | Push, where | Poll, otherwise | Cursor |
|---|---|---|---|
| Jellyfin | Its webhook plugin, where installed: one generic destination carrying `ItemAdded` alone | Items sorted by when they were added, newer than the cursor, for `added`; activity-log entries naming no user at a warning or error, for `health` | The newest item's added time with its id; the newest activity entry's id |
| Emby | Never: its webhooks need Emby Premiere, and its documented API neither registers a webhook nor says whether Premiere is active | As Jellyfin, by Emby's own items and activity log | As Jellyfin |
| Medusa | Never: its notifiers post only to fixed services' addresses | History, newer than the cursor: `Downloaded` as `imported`, `Failed` as `failed`; it sends no `health`, as its API names no problem with itself | The history row id |
| Sonarr, Radarr, Lidarr | A Connect webhook, which every one of them carries: on import, on import or download failure, on a health issue and its restoring | History since the cursor, and the health list compared with the last one read | The history record id |
| Bindery | Its webhook: `bookImported`, `downloadFailed` and `health` alone | History since the cursor, and its health | The history record id |
| Plex | Its webhooks, where the server's owner holds Plex Pass: `library.new` alone | Recently added, newer than the cursor; it sends no `health` | The newest item's added time with its key |
| Audiobookshelf | Never: its notifications reach Apprise alone | Each library's items sorted by when they were added, newer than the cursor; no `health` | The newest item's added time with its id |
| Navidrome | Never: it has no notification connection | Albums newest first, newer than the cursor; no `health` | The newest album's created time with its id |

### The outside watcher

`status.watch@1` is the contract of the monitor that watches the stack from outside it
([ADR-0061](../../00-overview/decisions/0061-the-outside-watcher-is-a-capability-the-core-provisions.md)).

| Operation | Answers or does |
|---|---|
| `reachable` | Whether the monitor answers, and why not where it does not |
| `monitors` | Every monitor it holds: its id, its tag where lemonfiber made it, its name, its kind (`http`, `keyword`, `port`, `ping`, `dns`, `docker` or `heartbeat`), its target, whether it is active, a heartbeat's interval and grace in seconds and its last check-in, its state (`up`, `down`, `pending` or `paused`) and since when, and its last reading |
| `provision` | Makes or updates the one monitor holding a tag, of a kind, at a target, at an interval, a heartbeat's grace and a count of failed checks before it alarms; answers its id, and what it watches instead and why where it could not watch what it was asked to |
| `retire` | Removes the monitor holding a tag, and nothing where none does |
| `check_in` | Records a check-in of the heartbeat holding a tag, as the job it watches makes one each interval; refused where no heartbeat holds the tag |

Every instant is whole Unix seconds (`ARCH-R274`).

### Acting on a stuck item

From minor `2`, `stuck_items` answers each item with the curator's id for its queue entry,
the title's id and the release's fingerprint: the SHA-256 of the curator's own identity for
the release, in lower-case hexadecimal. An indexer's identity for a release can carry its
key, so the fingerprint is all that leaves the curator and all the journal keeps.

| Operation | Answers or does |
|---|---|
| `unqueue` | Removes one queue entry, by its id, from the download client holding it, blocklisting its release where asked, and answers the release's fingerprint; refused for an entry it does not hold |
| `grab` | Lifts the blocklist entry of the release with a fingerprint for one title it holds, searches the indexers for that title, and grabs the release whose fingerprint matches; answers `gone` where no indexer offers it any more |

The core asks `unqueue` and then `search` for an item queue self-healing has struck out,
where `LEMONFIBER_STUCK_SEARCH_AGAIN` is on, and `grab` only to put that act back
(`C7-R16`, `H5-R4`).

### What a download client says of each transfer

From minor `2`, `transfers` of `download.torrent@1` and `download.usenet@1` answers each
item with its id in the client, the category it is filed under, its state (`downloading`,
`stalled`, `metadata`, `error`, `queued` or `paused`) and when it was added, in whole Unix
seconds. An item under a curator's category that no curator's queue holds is orphaned.

From minor `3`, `downloading` of `library.curate@1` answers each entry with the curator's id
for its queue entry, `queued`, the id `unqueue` takes, beside the client's id for the
download. The core acts on an item it classified from the client's view by that id alone
(`ARCH-R392`). The core pairs a
curator's queue entry with the client's item by that id and never by name, and classifies
an item queue self-healing judges from both
([ADR-0063](../../00-overview/decisions/0063-the-queue-heals-by-strikes-over-the-curator-and-the-client.md)).

`the routes it admits` answers each route as the gate holds it, with each credential's
SHA-256, in lower-case hexadecimal, in place of its value. The core tells by it which of
the media server keys filed under the gate's name the gate holds, keeps that one and
revokes the rest, so the answer is exact rather than the short fingerprint the journal
shows. No answer of the gate's holds a credential's value (`ARCH-R305`).
