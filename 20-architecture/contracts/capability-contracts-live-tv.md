# Contract: live TV

**Status:** Accepted

Part of the [capability contracts](capability-contracts.md): the pass a live stream's bytes
are served on, what the core asks of a media server's live TV, and how live TV is answered
over Plex. The requirements it describes are listed with the rest of the contract's, under
[Requirements](capability-contracts.md#requirements).

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
- **The pass.** The core draws two keys from its pass key with HKDF-SHA256, one for
  live-stream passes and one for item passes, so neither kind of pass is ever good as the
  other. A live-stream pass names the member it was issued to and the moment it lapses,
  and carries an HMAC-SHA256 under the live-stream key over the live stream it is for,
  that member and that moment, written `<member>.<lapses>.<mac>`. An item pass, which a
  browser plays on, seals with AES-256-GCM under the item key, behind a nonce drawn for
  it, the member and the token of a session on the member's own account, with the item
  it is for and the moment it lapses as the data it is bound to, written
  `<nonce>.<lapses>.<sealed>`. Every part but the moment is base64url without padding.
  A pass lapses five minutes after it is issued, and the client renews it before then.
  A player keeps asking at the address it started from, so a renewal holds the same pass
  good for longer rather than issuing another: the core writes, beside the key and the
  paths, the renewals file, holding for each pass it renewed the pass's MAC or sealed
  part's SHA-256, never the pass, and the moment it now lapses. The pass service holds a
  pass good past its own moment only to the later moment the renewals file names for it,
  and the core drops a removed member's entries at once. It travels in the `lfpass` query parameter, the one place a player fetching a
  playlist's parts carries it unaltered, and the guard writes it into every address of a
  playlist it serves on a pass and takes it off what it forwards (`ARCH-R314`,
  `ARCH-R418`).
- **The answer.** The pass service answers `GET /pass`, asked with the request the guard
  forwards named in `X-Forwarded-Uri`. On a live-stream path it answers `204` where the
  pass in that request's `lfpass` is good for the live stream the path names and has not
  lapsed. On a byte path it answers `204` where the pass opens under the item key for the
  item the path names and has not lapsed, with the session's token in
  `Lemonfiber-Session`, which the guard asks its item question with and presents to the
  upstream as it does a token a client presents, and writes nowhere else. It answers `403`
  for anything else. The live stream or item a path names is the one a live-stream path
  or a byte path of the declaration places in it; a path neither covers names none, and
  is answered `403`.
- **The image.** The pass service runs `ghcr.io/lemonfiber/lemonfiber` at the running
  release, pinned by the digest resolved when the project is written, as every other image
  of the project is pinned. A build no image was published for writes the project without
  the pass service and says so.

## Live TV

From minor `4`, a filler of `media.serve` answers three operations for live TV, so a
server recorded before them passes their cases as `unsupported` (`ARCH-R421`):

- `channels` answers the live TV channels one member may watch, each with its id, its
  name, its number where it has one, and the programme on it now with its title, its
  certificate and when it ends. It answers none where the member's own account may not
  watch live TV. The adapter reads that from the member's own standing at the server,
  never from what its own credential may watch.
- `tune` opens one channel's live stream on one member's account where that account may
  watch live TV and that channel, and answers the id the live stream is closed by and two
  paths at the upstream: the tuner's own stream and a transcoded playlist naming the live
  stream in its query, each one a live-stream path of the declaration covers. It answers
  none where the account may not watch it.
- `untune` closes a live stream by the id `tune` answered.
- `allow_origins` replaces every origin a browser may read the server from with the ones
  it is given, never none and never a wildcard. The core gives it the front door's origin
  and the console's, which `lemonfiber ui` records owner-only when it starts, so a browser
  on the console plays from the front door.

From minor `5`, `guide` takes one member and a number of hours, and answers each channel
that member may watch with the programmes its guide holds on it from now across those
hours, each with its title, certificate, start and end, and none past where the guide ends
(`ARCH-R436`). From minor `6`, it leaves out each programme the server's own policy keeps
from that member's account, as its maximum parental rating and blocked tags do on Jellyfin
and Emby and a share's television filter and a Home account's restriction profile do on
Plex, and answers each channel's `until`: the end of the last programme the server's
guide holds on it across those hours before any is left out, or none where it holds none.
It is taken before anything is left out on purpose: it says no more than the gaps already
show, and no title, certificate or time of a programme left out reaches the core beyond
that.

The core asks `channels` and `tune` for the member who asked, reads each programme's
certificate against the member's limits, and leaves out a channel whose programme now is
outside them. It asks `guide` with the hours `LEMONFIBER_GUIDE_HOURS` holds, keeps the
channels `channels` admitted, and leaves out each programme outside the member's limits as
a gap, so a programme is left out by the server's policy and by the core's limits alike.
Where the guide ends on a channel is its `until`, or the end of the last programme
answered where the adapter speaks a minor below `6` (`D11-R17`). It issues a pass for each path `tune` answered, for the live stream a
live-stream path places in it, and refuses a path no live-stream path covers, so no pass
is issued for bytes the guard would not ask about. Asked to renew, it asks `channels`
again for that member and refuses where the channel is gone or its programme now is
outside their limits. It keeps, owner-only, each live stream it opened: the member, the
channel, the id it is closed by, the live streams its paths name and when its last pass
lapses, and no pass. It asks `untune` for each whose pass lapsed unrenewed, every minute
while it serves the web API and whenever the household is read, for one the client says
it stopped, and for every one a removed member opened (`D11-R12`).

## Live TV over Plex

`media.serve`'s live TV over Plex (`ARCH-R421`, `ARCH-R436`) reads each member's own
standing with the member's own server token: a share's, as plex.tv lists it on the shared
server, and a Home account's, as switching to that account hands it. The account that
claimed the server may always watch live TV. Any other account may where its entry among
the server's shares lets it use the server's tuners, its `allowTuners` other than `0`; an
account with no such entry, or one whose entry cannot be read, may not. Plex is asked with
the member's token, and the adapter also leaves out what the account's share or
restriction profile keeps from it, so a programme is left out whether or not Plex applies
that policy to live TV itself:

| Operation | Answered over Plex |
|---|---|
| `channels` | The channels of each DVR's lineup, each with its id, name and number, and the programme on it now from the guide, read with the member's token; none where the account may not watch live TV |
| `guide` | Each of those channels' guide, read one day at a time from its DVR's guide provider, merged and held to the hours asked, a day that cannot be read refusing the guide. Read once with the owner's token for each channel's `until`, before anything is left out, and once with the member's for what it holds, leaving out each programme whose certificate the share's television filter does not admit or the Home account's restriction profile places above it, each carrying a label the filter refuses, and each with no certificate where unrated content is held back |
| `tune` | The channel tuned on its DVR with the member's token, answering the live session's own playlist and a transcoded playlist of it whose `session` is the live session's id and whose `path` is that live session's playlist |
| `untune` | The live session terminated; one the server no longer holds is closed already |

Plex's declaration covers the live session's own playlist and segments by the live
session's id in their path, and the transcoder's start by its `session` parameter with
its `path` bound to the same live session. The transcoder's segments sit under a session
id in their path, as an item transcode's do, so its live-stream path is covered only
where the request carries `session`, which the guard writes into every address of a
playlist it serves on a live-stream pass; an item transcode's segments, carrying none,
are not covered by it. That path also holds the session id its route names, and a
request whose path and `session` name different live streams is refused; where they
name the same, the route names that live stream and no item, and where no byte path
covers it no item question is asked (`ARCH-R417`).
