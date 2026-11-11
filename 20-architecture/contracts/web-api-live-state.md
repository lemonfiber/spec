# Contract: the web API's live state

**Status:** Accepted

Part of the [web API contract](web-api.md): the stream a client follows the stack on, what
reaches the operator's and a member's, and where a message goes. The requirements it
describes are listed with the rest of the contract's, under
[Requirements](web-api.md#requirements).

## Live state

```
GET /api/events        text/event-stream
```

The SSE event name is the envelope's `kind`, and the payload is the envelope. Three
properties are required rather than incidental:

**It is the same gather.** `G1-R12` requires concurrent surfaces to agree, and two
independent gathers are two chances to disagree — so the stream is fed by the gather that
already serves the dashboard, not a second one built for the web.

**A silent stream is distinguishable from a broken one.** Without a heartbeat, "nothing has
changed" and "the connection died twenty minutes ago" look identical to a client, which is
the same confusion `Reading::Stale` exists to prevent one layer down.

**A resumed stream does not lie about what it missed.** On reconnect a client may hold values
gathered before the gap. Those are `Stale` by definition, and must be presented as such
rather than as current.

**What is newest rides the stream, and the items do not.** A `news` event names the newest few
identifiers of each kind `/api/news` lists, when any of them changes and when a client
connects. A surface that marks what is new can then say whether anything is, and how much,
from the stream it already holds, and reads `/api/news` only on the screen that lists the
items — rather than reading three answers for every stack on every frame of every screen to
draw a mark on a tab.

**An alert rides the stream as it happens.** An `alert` event is sent when an alert starts and
again when it resolves, carrying what the dashboard's alert says: what happened, what it means
for the household, what to do, how much it matters and which way it went. It also carries an
identity that names the alert rather than the event, the same on an onset and on the resolution
that ends it and different for the next time the same thing goes wrong, so a client can close
what it opened without comparing sentences. A client connecting is not sent the alerts already
said; the dashboard's own list is where those are (`ARCH-R162`).

**An alert names its notification kind, from a closed list.** Beside its event kind, which is
open and grows with every check, an alert carries `notification`: one of `problem`,
`completion`, `update`, `backup`, `request` or `member`, the list the artefact publishes as a closed union. A new
kind is a contract change. `GET /api/alerts` carries `kinds`, the ones this stack raises, so a
client offers a switch for each of those and for nothing else (`ARCH-R279`, `ARCH-R280`,
[ADR-0047](../../00-overview/decisions/0047-a-phone-hears-its-stacks-without-a-vendors-push-service.md)).

**A resumed stream replays the alerts it missed.** A stream opened with `Last-Event-ID` is sent
every `alert` event raised after that id, oldest first, from the last 24 hours and at most the
last 200, before anything else, so a phone the platform woke an hour later hears what was said
while it slept. An id older than that is answered from the oldest kept, and the replay says
`partial` so the client knows it missed some (`ARCH-R281`).

**A phone can ask to be woken.** A phone that cannot hold the stream while it is closed
registers a UnifiedPush endpoint, and the core sends it a WebPush message, encrypted to the
phone, on every alert's onset and resolution, carrying nothing but that the stack has something
to say. The phone then reads the stream over its own connection, so the distributor learns when
a stack spoke and never what it said. The endpoints are the operator's to see and remove, at the
command line as here (`ARCH-R282`):

```
POST /api/push-endpoints        GET /api/push-endpoints        DELETE /api/push-endpoints/{name}
```

**Where a message goes.** The core is the one fan-out between what the stack has to say and
the back-ends it is said on (`B9-R2`). What reaches it is B5's own alerts and the events the
curators and the media server send it (`ARCH-R397`), at an address only they hold a key to:

```
POST /api/notify/events        GET /api/notify        POST /api/actions/push-woken
```

`/api/notify/events` takes one neutral event from a filler, with the events key the core minted
for that filler when it seeded it, and nothing else; B5's policy decides whether it is worth
telling, exactly as it does for the core's own alerts (`B9-R5`), and a failure or a health
problem is told as `problem` and an import or an addition as `completion`.

**Where a filler reaches it.** A container reaches this machine as `host.docker.internal`, so
the address seed hands each filler is `https://host.docker.internal:<port>/api/notify/events`,
at the port the web surface was last served encrypted on where a container reaches it: on the
network, or on an engine that forwards that name to this machine's own loopback. It is handed
with the digest of the certificate the surface presents, which the adapter pins, so the key it
sends crosses no connection in clear and reaches nothing but this core. The surface answers
that name at this door and at no other. `LEMONFIBER_EVENTS_ADDRESS`, an `https` address the
web surface is reached at, takes the place of `host.docker.internal` and its port, with the
same certificate pinned. Where neither exists, seed asks no filler and says why. On an engine
that does not resolve `host.docker.internal` by itself, each adapter is told it is the
engine's host gateway (`ARCH-R409`).

The core delivers each alert worth telling to every back-end that is not held, each on its own,
so one that fails costs the others nothing (`B9-R7`). It speaks each kind itself: ntfy, gotify,
a webhook, an Apprise URL, and UnifiedPush through the phones' push endpoints. A delivery carries
the alert's notification kind and its summary as B5 words it, and never a member's name, what
anybody is watching or the title a member asked for (`B9-R8`). Each kind is an entry of its own
in the account of what leaves this machine, with a switch of its own.

`/api/notify` is what the core keeps of it, the operator's alone: a member session and a key of
any scope are refused it. It carries `state` (`unconfigured`, `ready`, `degraded` or
`unreachable`), `backends` in the order they were added, and `unread`, each back-end whose
record could not be read with why; a store that cannot be read at all refuses the read rather
than answering none. Each back-end carries its `id`, its `kind`, `where` it reaches (host and
topic or path, never a credential), `chosen_by`, `hosted` (its host and what leaves for it)
where it is hosted, `proof` (`unproven`, proven at an instant, or held with why), `last`, its
newest delivery, `failures`, every failed delivery since its last confirmed one, newest first,
and `retry` where one is pending. A delivery carries `at`, its notification kind and its
`outcome`: `confirmed` where its arrival was observed, `sent` where the back-end took it and
its arrival was not observed, or failed with what the back-end answered.

**A back-end is proven, not assumed.** `lemonfiber notify test` sends a test carrying an id, and
a back-end is proven only once that id is seen arriving: in an ntfy topic's or a gotify server's
own history, or confirmed by the phone a wake went to. A webhook and an Apprise URL keep no
history the core can read, so they stay unproven, and a back-end is `ready` only when at least
one is proven (`B9-R3`). Each delivery to a back-end whose history is readable is confirmed the
same way.

**A member hears what they asked for, and nothing else.** The operator marks which of their
back-ends a member may receive on, with `lemonfiber notify set <id> --members`, under a name the
household reads. A member's own session lists those by that name alone, with no address, kind or
state, and chooses among them; it may also register its own phone's push endpoint. Only `ready`
reaches a member: something they asked for has arrived (`ARCH-R279`). A health problem, a
failure, an import, another member's ask and anything about the stack never does.

```
GET /api/notify/mine        POST /api/actions/notify-choose
```

`/api/notify/mine` answers a member session with the back-ends offered to members, each by
its household name and whether this member receives on it, and with whether their own phone is
registered. `notify-choose` takes the ids this member receives on from now on, each one offered
to members, and refuses any other. A key is refused both. Each back-end's `chosen_by` in
`/api/notify` names the operator, or the member who chose it.

**A phone confirms its wake.** Every wake carries an id inside the sealed payload. The phone
sends it back over its own pinned connection with `push-woken`, taking the endpoint's `name` and
the `id`, and that delivery is then `confirmed`. A distributor's `404` or `410` is a failed
delivery shown as such; the endpoint stays registered until the phone or the operator removes it
(`N4-R30`).

**What is playing rides the stream.** A `playing` event carries every session the media server
is playing now, in the envelope `GET /api/playing` answers the same credential with, and it is
sent again every 5 seconds, the pace a member's stream sends what they are playing at. A client
that shows what is playing, a home automation's sensor among them, follows it from the stream
it already holds rather than polling the read (`ARCH-R178`).

**A line names the work that said it.** A `start`, `pull` or `step` event said by work an
accepting reply named carries that name as `job`, at the top of the envelope beside `kind` and
`data`, and an event no job said carries none — a run at a terminal, the server starting:

```json
{ "api_version": 1, "kind": "pull", "job": "9f2c1a7e04b3d815", "data": "Pulling sonarr" }
```

The name sits on the envelope rather than in `data`, so what a kind carries is the same
whoever said it, and a client ties each line to the start, fetch or walk it asked for by the
name the accepting reply gave it (`B2-R19`, `D3-R14`). The lines the container engine writes
while pulling images are `pull` events, for a fetch and for a start that pulls, and the
command line's `--json` says them under the same kind (`B2-R18`, `ARCH-R48`). A start fetches
the images it lacks before it starts anything and then starts with nothing left to fetch, so
its `pull` lines all come before its `start` lines and a fetch that failed is said before
anything was started. A `pull` line is
state, as a `start` line is: a client connecting is given the newest, because the line says
where the work has got to and a fetch says hundreds of them. A `step` is a record, because a
step missed is a hole in the walk.

### A member's stream

The stream above is the operator's view: the dashboard, the log lines, what setup is doing.
None of it is narrowed to anybody, so it is never handed to a member. A member, and a key
scoped to one, are admitted to a stream of their own instead. It carries their household row,
their held shelf and what they are playing, each as the read that answers it answers that
member, and nothing gathered for the operator (`ARCH-R157`).

It is the same stream in every other respect. It beats at the same interval, it resumes from
the same event id, and a value gathered before a gap is stale on it as on the operator's. It
ends when the member is removed or their key is revoked, as the operator's ends when the
operator's credential does (`ARCH-R158`).
