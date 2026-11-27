# Contract: the web API

**Status:** Accepted

The interface between `lemonfiber`, which serves it, and
[`lemonfiber-web`](../../30-repos/lemonfiber-web.md), which draws it.

**Satisfies:** [G1-R1](../../10-functional/features/g-ux/g1-interface-tiers.md),
[G1-R2](../../10-functional/features/g-ux/g1-interface-tiers.md),
[G1-R7](../../10-functional/features/g-ux/g1-interface-tiers.md),
[G1-R12](../../10-functional/features/g-ux/g1-interface-tiers.md),
[C6-R9](../../10-functional/features/c-trust/c6-web-security.md),
[C6-R10](../../10-functional/features/c-trust/c6-web-security.md),
[C6-R11](../../10-functional/features/c-trust/c6-web-security.md),
[C6-R12](../../10-functional/features/c-trust/c6-web-security.md)

---

## Why this is a contract

[ADR-0011](../../00-overview/decisions/0011-web-surface-as-a-fifth-repo.md) put the web
surface in its own repo, which means the boundary between it and the core is a **published
shape** rather than a compiler check. That is the whole point: `G1-R2` says no surface may
implement behaviour independently, and a client that can only ask and draw cannot break it
by construction.

The risk a contract carries is drift, so this one is built to make drift structurally hard
rather than merely discouraged.

## It is the envelope that already exists

Machine-readable output is already a stable interface (`ARCH-R9`, [versioning](versioning.md)):

```json
{ "api_version": 1, "kind": "status", "data": { … } }
```

**The web API does not introduce a second shape.** Every endpoint answers with the identical
envelope the equivalent command emits under `--json`, byte for byte. A script piping
`lemonfiber status --json` and the web app fetching `/api/status` receive the same document.

This is the load-bearing decision in the contract, and it is worth being explicit about why.
A separate "web shape" would be a second serialisation of the same domain — two places to
change when a field is added, two sets of tests, and eventually two answers to the same
question, which is exactly what `G1-R2` exists to prevent. One shape means the surface adds
**no vocabulary of its own**.

## Reading

Each command that supports `--json` has one endpoint, named for the command, returning that
command's envelope:

```
GET /api/forms         GET /api/status         GET /api/services
GET /api/checks        GET /api/storage        GET /api/logs?…
GET /api/requests      GET /api/trace?…        GET /api/stuck
GET /api/version       GET /api/config?…       GET /api/quality
GET /api/explain?…     GET /api/backups        GET /api/bundle/{name}
GET /api/front-door    GET /api/provenance    GET /api/catalogue
GET /api/outbound      GET /api/stored       GET /api/clients
GET /api/credentials   GET /api/alerts
GET /api/space         GET /api/bandwidth
GET /api/hosting      GET /api/uninstall
GET /api/migration    GET /api/held?…        GET /api/held/{id}?…
GET /api/held/{id}/poster?…                   GET /api/held/{id}/backdrop?…
GET /api/history
GET /api/update?…
GET /api/news
GET /api/plugins       GET /api/wiring       GET /api/settings
GET /api/plugins/catalogue
GET /api/playing       GET /api/watching?…    GET /api/channels?…
GET /api/guide?…
GET /api/boot          GET /api/watcher      GET /api/queue
GET /api/askable?…      GET /api/askable/{id}/poster?…
GET /api/askable/kinds?…                      GET /api/stack
GET /api/requests/{reference}/poster?…        GET /api/notify
GET /api/notify/mine    GET /api/settled
GET /api/in-flight?…    GET /api/served
GET /api/copying
```

Query parameters mirror what the command takes, flag or argument. A command that gains one
gains a parameter; one that gains an endpoint gained a command first.

`/api/held/{id}` is one title on a member's shelf, named in the path by the id the shelf lists
it under: what it is, a series' seasons and episodes, and where each is served at the guarded
front door beside the fingerprint the door presents (D11). It is read as the member whose shelf
it is, so a title outside their limits is answered as absent, the same answer a title the
household does not hold gets. `/api/watching` is what a member was part-way through and how far,
located the same way. `/api/channels` is the live TV channels a member may watch, each with the
programme on it now, read as the member, so a channel whose programme now is outside their limits
is left out (D11-R11).

`/api/held/{id}/poster` and `/api/held/{id}/backdrop` are the two reads that answer bytes rather
than an envelope: the title's picture, read as the member and passed on as an `image/*` body of
at most 2 MiB, marked `Cache-Control: private` (D11-R9). They exist for a browser, which can
neither present a session to the guarded front door nor pin its certificate, so it fetches the
picture here with its own token and draws it from memory. A title outside the member's limits,
and a picture the media server does not hold, are answered as absent.

`/api/channels` is the live TV channels a member may watch, each with the programme on it now,
read as the member, so a channel whose programme now is outside their limits is left out and a
member whose account may not watch live TV is answered none (D11-R11). It is narrowed to the
member who asks, as the held shelf is.

`/api/guide` is the same channels, each with its programmes from now across the guide window
`LEMONFIBER_GUIDE_HOURS` holds, each programme outside the member's limits left out as a gap,
and `guide_until`, the end of the last programme the media server's guide holds inside the
window, or nothing where it holds none (D11-R17). It is narrowed to the member who asks. A
surface reads one of the two: a shelf of what is on now reads `/api/channels`, a full guide
reads `/api/guide`.

`/api/clients` takes none either, and for a different reason: what to watch on is the same answer on every machine, because the client landscape belongs to the platforms rather than to a stack. It reads nothing and asks nothing of the engine, so it answers where nothing is set up yet — which is when somebody deciding what to tell the house is most likely to ask. Naming a device would let a surface show one row and call it the answer, and the row most worth reading is the one saying a device is poorly served and what to do instead.

`/api/credentials` takes none, and it is half a word on purpose. What it answers with is
every credential the stack holds — what each is, what authenticates with it, where the value
lives and where it stands, and each grant letting it cross to a third-party plugin
(`ARCH-R325`) — and no value, because the shape it is built from has no field one could go
in. The two things that can be asked of a line of it are not offered here at all:
printing a credential over this door would put it through a browser's cache, whatever proxy is
between and the log each of them keeps, and replacing one is a write a request could be forged
into making against the credential the stack is currently working on. Both are the terminal's,
in front of the person who typed the confirmation. A parameter narrowing the list would be a
way to ask about one credential rather than the set, and the answer worth reading is the set —
the credential worth knowing about is usually the one somebody had forgotten was there.

`/api/space` takes none, and the absence is the point. What it answers with is the account of
where the disk went and an offer of what could be got back; there is no parameter choosing what
to reclaim, because that choice is never a caller's to make. A torrent still seeding is named
with what removing it costs and left with the operator, and something the operator has already
asked to be left alone is not on offer at any level of fullness — so a narrowing parameter would
be a way to ask for exactly the two things nothing here will take.

The `space` action that answers the offer can be narrowed, and only within it: `only` names
categories of what the offer says costs nothing, so an operator agrees to each one apart and
never to a set chosen for them; anything the offer did not name is refused (`ARCH-R289`).

`/api/bandwidth` takes none, and the absence draws the same line the disk's does. What it
answers with is the account of the line: what it was measured to carry, what the stack is being
held to, which side of the household's day each download client says it is on, and whether each
is actually keeping to what it was given. Declaring a limit is the action of the same name, at
the door changes are asked for — a read that could set one would be a read that changes what
everybody in the house experiences, which is the distinction the two doors exist to draw.

`/api/uninstall` takes one, and it is required in spirit rather than in shape: which of the
four removals is being read. Naming none reads the one that removes nothing, because that is
the safe reading and the one a browser opening the page has not chosen anything by; a word that
names none of the four is refused rather than read as whichever the shape would default to,
since on this subject the default that would hurt is the one that reaches the library. It is a
read and never a removal — what it answers with is the listing every container, image and path
a removal would take, and the action of the same name is where an answer to that listing goes.
The two are one command read the same way twice, so what a browser agrees to is what it was
shown.

`/api/update` takes one too, and it names the object rather than narrowing the answer: which
of the two things that can be moved forward is being read — the services the stack runs, or
lemonfiber itself. They are one command because moving something forward is one word an
operator reaches for, and the object is the whole of what tells them apart; `what=stack`
answers with what each service would move to, how large the step is, and which of the steps
migrate state and so cannot be walked back, while `what=self` answers with where this copy
stands and the exact command for whichever tool owns it. Naming none is refused rather than
answered, and this is where it parts company with the removal above: that one has a reading
that takes nothing, and here neither object is the smaller case of the other — a page that
asked about the stack and was handed the binary has been answered a question it did not ask,
and the two answers do not even resemble each other. Both are reads whichever is named.
Nothing here replaces the binary at all, and moving the services is the action of the same
name, where an answer to what the read listed goes.

`/api/hosting` takes none, because what is hosted is a property of the machine rather than
of the caller. It answers with every long-running command that could be handed to this
machine's service manager and what became of each — installed or not, running or not, and
where the words of a command with no terminal are being written. Naming one would let a
surface show a single row and call it the answer, and the row worth reading is the one
saying a guarantee the operator believes is in force is not.

`/api/front-door` takes none, because the question takes none: which one address the household
is given is derived from what the stack runs rather than asked for, so a parameter here would be
a way for one surface to be told a different door from another.

Each service it names, the door and each beside it, carries its address or why it has none,
and `reaches`: `here` where the address answers from the network the request came from,
`not-here` where it does not, and `unknown` where the core cannot tell. The core judges it from
the request's source: a request from this machine, a loopback, private, link-local or unique
local address is from the household's network, one from any other address but the shared
carrier range is from away, and one from the shared carrier range or with no source is
unknown. An address on a private or link-local number, a `.local` name or a name of one label
answers on the household's network alone, so it reaches `here` from there and `not-here` from
away; every other address is `unknown`. A member and a key scoped to one are answered with the
services facing the household alone, those facing `asking`, `watching` or a `shelf`; the
others are never gathered for them. Their answer names how the door was chosen nowhere, says
everything in the household's words, and leaves out an address that reaches `not-here`, saying
instead that it cannot be reached from where they are (`ARCH-R416`).

`/api/stack` takes none either: it answers how the stack runs without lemonfiber (`F1-R15`), as
`lemonfiber stack --json` writes it, the operator's alone. A member and a key of any scope are
refused it, because it names where this machine keeps its project and settings, and a login in
the container engine's address is withheld from the words it says.

`/api/requests` answers with the household and what each member has asked for, the same
document `lemonfiber household --json` writes. Each request carries what a member's own screen
needs to show it without asking anything else: the kind of title it is, the year that title came
out, when it arrived on the media server, and the identifier the media server holds it under,
which is the identifier `/api/held` names it by, so a request that has arrived can be found on
the shelf. A value that cannot be known is left out rather than written as an empty one: the year
until a request has been handed to the service that files it, and the arrival and the identifier
until the title is on the media server (`ARCH-R161`).

`/api/news` takes none, because what is new is decided by whoever reads it rather than by the
stack. It answers with the items a surface can mark as new, newest first within each kind: the
releases in the stack's record, each by its version; the household's requests, each by its
number; and the checks found wrong, each by its check and its onset (`C1-R17`). Each carries
the stack's own words for it. The stack keeps no record of what anybody has seen, because what
one phone has seen is not what another has, and a stack that kept it would be keeping a
person's reading habits. `lemonfiber news --json` is the same document.

`/api/bundle/{name}` is the one read that does not answer with an envelope. It answers with
the bundle itself, because a browser has no path on the host to be told and handing the file
over is the only form `--out` can take on a screen. The name is resolved beneath the bundles
directory rather than followed, so one carrying a path, or climbing out of that directory, is
refused by name.

### What became of the last restart

```
GET /api/boot
```

The `boot` envelope `lemonfiber boot --json` prints: when this machine last started, the
post-boot verification kept against that start and the newest kept against any, why a run
against it started nothing, and since when and for how many starts the stack has not come back
(`B8-R16`). It takes no parameter, because the restart worth reading about is the last one. A
verification against an earlier start is answered beside the latest start rather than as it, so
a surface can tell "passed" from "not run since the restart".

### What the outside watcher sees

```
GET /api/watcher
```

The `watcher` envelope `lemonfiber watcher --json` prints: which plugin fills `status.watch`,
whether its monitor answers and why not, when it was asked, every monitor it holds with what it
sees, and every critical service and household entry point no active monitor covers (`K2-R16`).
A monitor is paired with the service, entry point or job it covers by the record of what
lemonfiber provisioned, never by its name or its target, so an operator's own monitor carries no
`covers`. Its state is `expected-down` where the stack was stopped on purpose and
`not-reporting` where it holds no reading newer than its interval and grace. A watcher that does
not answer, or nothing filling `status.watch`, is answered `reachable: false` with everything it
should cover uncovered, never as nothing wrong. It takes no parameter.

### What the queue holds

```
GET /api/queue
```

The `queue` envelope `lemonfiber queue --json` prints (`H5-R16`): whether healing acts, the
strikes and grace window in force, every unhealthy download with its curator, release,
classification and why, its strikes, when it was added and until when it is in grace, and
what the next run would do to it where healing is on. It names every curator or download
client that could not be reached or verified, including a client that names no download by
its own id, the mount mismatch where there is one, whether the list may be short, when the
queue was last classified, and the newest runs, each with whether it was rehearsed and each
item's three acts as each came out. A record that cannot be read is refused, never answered
as a healthy queue. It takes no parameter, and running a pass is not served: `lemonfiber
queue heal` is asked for at a terminal.

### What a stop would interrupt, and how the surface is served

```
GET /api/in-flight?…    GET /api/served
```

Two reads answer the operator about the machine itself rather than about the media: what stopping would interrupt (`ARCH-R447`) and how the surface is served, certificate included (`ARCH-R448`).
Both are on [their own page](web-api-the-machine.md), with what the `config` read lists: the decisions setup made (`ARCH-R449`) and the areas declared unmanaged (`ARCH-R453`).

### What is playing

```
GET /api/playing       GET /api/watching?…
```

What the media server is playing now, and how each member is answered with their own sessions alone (`ARCH-R156`), are on [the live state's page](web-api-live-state.md#what-is-playing), beside the `playing` event that carries the same envelope.

### What a member may ask for

```
GET /api/askable?…       GET /api/askable/{id}/poster?…       POST /api/actions/ask
```

`/api/askable` is a member's search for titles the house does not hold yet, answered by the
core under that member's limits (`D4-R15`), as `lemonfiber household search --json` answers.
It takes `term`, the words searched for, two to a hundred characters once trimmed and refused
outside that as `WISH-1`; `after`, the place a previous page said the next one begins at,
refused as `WISH-2` where it is not one a page answered; and `member`, which the operator names
and a member's own request has replaced with themselves, as the held shelf does. A member, the
operator and a key scoped to a member are answered; a `read` or an `act` key is not, because
every search is a live question to the request service and to the catalogue behind it.

- **Where the titles come from.** The core asks whatever fills `request.intake`, over the
  contract where it speaks it and through the bundled adapter otherwise. The client asks the
  core and nothing else.
- **Which kinds.** The kinds a running curator can deliver now, decided by the core and named in
  the answer's `kinds` (`D4-R4`, `D4-R18`). Nothing to fetch with is refused as `WISH-4`.
- **Under whose limits.** A title with no certification is looked up for the country the media
  server's own rating table is named for, which `identity.source` answers as `country`; one
  still uncertified is held to the member's unrated policy and is never let through by default
  (`D4-R19`, `D8-R5`). A title outside the member's limits is left out, never shown as
  unavailable (`D8-R9`).
- **One page at a time.** A page holds the titles in the request service's order and `next`,
  the place the following page begins, absent on the last; no title is on two pages of one
  search (`D4-R17`).
- **What each title says.** Its id, kind, title, year where known, and where it stands: `here`,
  `partly-here`, `on-its-way` or `askable` (`D4-R5`, `D4-R10`). No title carries the location
  of its artwork; the core serves that itself (`D11-R10`). Each carries `found`, a token the core
  signs binding the member, the kind, the id and an expiry an hour on, for the ask to hand back
  (`D4-R27`).
- **What the member may ask for.** Beside the titles, `asking`: what their period allows and has
  left of each kind and when it next frees up, as the household read says it, and `approval`, a
  household sentence saying whether what they ask for waits for whoever runs the house.

`/api/askable/kinds` takes `member` as the search does, answered to the same callers with the
same refusals, and says which kinds that member may ask for now, each with the units a title of
it is asked for in (`D4-R24`): series and films where a curator of them runs, with no units, and
music or books where a curator speaking `music.curate` or `books.curate` is settled, in the units
its `profiles` answers. A kind the member's allowance takes none of is left out.

`/api/askable/{id}/poster` is the poster of a title a page offered, named by its id in the path
and its `kind` as a parameter, with `member` as the search takes it and answered to the same
callers. It answers bytes rather than an envelope, as the held shelf's pictures do: an `image/*`
body of at most 2 MiB marked `Cache-Control: private` (`D11-R10`). The core fetches it from the
location the request service gave for that title, and only where that location lies beneath the
one catalogue address the account of what leaves this machine names, over HTTPS, with no
credentials, its host resolved and refused where it stands for a loopback, private or link-local
address, and no redirect followed; the member's client is never sent to the catalogue. A title
outside the member's limits is refused as `WISH-3`, as an ask is; one with no poster, a poster
that is not a raster image or is larger, and an operator who switched posters off
(`LEMONFIBER_REACH_POSTERS`, `G8-R5`) are answered as `WISH-13`.

For music and books it takes `unit` beside `kind`, as the search does, and the id is the
curator's reference: it answers that candidate's cover (`D4-R25`), read back from its curator,
under the same setting and size cap. A cover lies wherever the curator says, so the core fetches
it from any host, but only over HTTPS with no credentials, its host resolved and refused where it
stands for a loopback, private, link-local or otherwise non-public address, and no redirect
followed. Each host it fetched a cover from is named under the posters entry of the account of
what leaves this machine.

`/api/requests/{reference}/poster` is the cover of an ask for music or books the core keeps,
named by its reference (`music-3`), served after the search that found it is gone and fetched as
a candidate's cover is. It takes `member`: a member's own request has replaced it with themselves
and reads only the covers of their own asks, the operator reads any, and a `read` or an `act` key
is not answered. A reference no kept ask goes by, or one another member made, is refused as
`WISH-3`.

`ask` takes `id` and `kind`, as a page of `/api/askable` named the title, `found` as that page
gave it, `seasons` for a series
(none names every season not already here or on its way, `D4-R11`), `name`, which the operator
names and a member's own request has replaced with themselves, and `dry_run`. It answers now,
never with a job, in the `asked` envelope `lemonfiber household ask --json` writes (`D4-R16`,
`D4-R20`):

- **The rehearsal comes first.** Under `dry_run` it checks everything the ask would and sends
  nothing, answering what the ask would leave of the member's allowance in titles of each kind,
  never as a size (`D7-R15`), and whether it would wait for approval.
- **The limits and the allowance are checked before the request service is asked.** An id the
  member's search could not have offered them, outside their limits or unknown, is refused as
  `WISH-3`, the same answer for both, so an ask reveals nothing a search would hide (`D8-R9`).
- **A title just found is looked up again.** An ask handing back a valid `found` for the title it
  names that then comes back unknown is looked up twice more, a short pause before each, and is
  refused as `WISH-15` with `Retry-After` where it is still unknown, never as `WISH-3`; with no
  `found`, or one invalid, lapsed or another member's, it is `WISH-3` (`D4-R27`).
- **One ask per title.** A title already on its way is answered `on-its-way` and nothing is
  created (`D4-R10`); one already here is refused as `WISH-5` (`D4-R5`). A title not out yet is
  asked for and says it will arrive once it is (`D4-R6`).
- **What it answers.** `outcome` is `asked`, `waiting` or `on-its-way`; `leaves` is what is left
  of each kind afterwards, absent for a kind nothing limits; `said` is the household sentence for
  all of it.
- **Sent once.** A client sends every ask with an `Idempotency-Key`, so an ask retried after no
  answer is carried out once (`ARCH-R165`).

Every refusal of any of the three carries a household sentence and a remedy beside its code, and names no
service, size, address or state of the stack (`G4-R16`):

| Code | Status | Refused because |
|---|---|---|
| `WISH-1` | `400` | the words searched for are fewer than two or more than a hundred characters |
| `WISH-2` | `400` | `after` is not a place a page answered |
| `WISH-3` | `404` | no title this member may ask for goes by that id and kind |
| `WISH-4` | `409` | the house cannot fetch that kind, or anything, right now |
| `WISH-5` | `409` | the title is already here |
| `WISH-6` | `409` | the member has asked for all their allowance lets them, until it frees up |
| `WISH-7` | `503` | the house has no room for new things, told as the house's and never as the member's limit (`D7-R15`) |
| `WISH-8` | `503` | the request service or the media server did not answer, with the operator told |
| `WISH-9` | `503` | the house has no request service or media server to ask |
| `WISH-10` | `400` | a season named is not one the title has, or seasons were named for a film |
| `WISH-11` | `400` | the operator named nobody |
| `WISH-12` | `404` | nobody in the household goes by the member named |
| `WISH-13` | `404` | the title has no picture to show |
| `WISH-14` | `409` | the member's asks wait for a yes and go through whoever runs the house, so nothing was asked for |
| `WISH-15` | `503` | a title the member's own search just found could not be looked up again, so they are asked to try again |

### When a request is refused

The body of every refusal is the error envelope, the same one `--json` renders, and its
problem's `code` names why the request was refused. The status says which kind of refusal it
is:

| Refused because | Status |
|---|---|
| What the request named, this product does not have | `404` |
| The request could not be answered as it was asked | `400` |
| The password offered at the door was wrong, or none is configured | `401` |
| Anything else about who is asking or where they asked from | `403` |
| Too many wrong answers at the door lately | `429` |
| Nothing about the request was wrong; the machine could not answer it | `500` |

A status groups refusals; the code tells them apart. Four different facts share `403`:

- The request carried nothing this run admits. Signing in again helps.
- It said it came from somewhere this server is not.
- The caller proved who they are, and this is not theirs.
- The media server could not say whether the caller is still anybody.

Each of these has its own remedy, and a client that read them from the status alone would
offer one remedy for all four. So a client decides what a refusal means from its code. It
never decides from the sentence, which is written for a person and may be reworded.

A household member's session, and a key scoped to a member, is answered with the same
envelope and the same code, worded for the household (`G4-R16`). The problem's `summary` and
`meaning` both carry the household sentence the registry declares for the code, its one
remedy is the household remedy, and `detail`, `cause` and `steps` are absent. A code the
registry declares a fault of the stack says that it is not working right now and that
whoever runs the house has been told. What stands in the way of part of a member's read is
carried the same way: each obstacle is a code, a sentence and a remedy, and a member is told
the code's household words. A member's read carries none of what is written for the
operator alone: the notes about other members, the caution about what a limit is, a
request's size, and where a refusal was passed on to. The core chooses the wording in one
place, for every route and for the member's stream alike.

That sentence is plain text, and so is every other sentence the core sends a client: a
refusal's summary and remedy, a reason, a report, and the meaning and remedy each code
carries in the registry. None carries markup. A name is written as the name, with no
backticks or emphasis around it, so a client shows the sentence exactly as it arrives and
no client has to render a markup language to be read correctly. A capability contract's
refusals and reasons are held to the same rule, because the core passes them on.

A code is one of the core's problem codes. It is stable, never recycled, and listed with
every other code the core raises. The artefact lists every code a refusal may carry, with
the status each is answered with ([the refusals it lists](web-api-artefact.md#the-refusals-it-lists)), so an SDK generates the
list rather than copying it. A refusal carrying no code, or a code the client does not
know, is read by its status alone. That is what a client meeting an older or a newer
server can still rely on.

The line between the first two is what the request was *for*. A word this product does not
explain is absent — the word is the whole of what `/api/explain` was asked for, and there is
no entry — while a parameter left out, given twice, or given a value the surface does not
offer is a request that could never have been answered as it stands. It is the same line the
write surface already draws between an action name nothing answers to and an argument it
cannot take, and the same reading `ARCH-R72` makes of a job name this run never issued.

`500` is reserved rather than incidental. A client told the machine failed will retry, and a
client told that about a word with no entry retries forever; worse, one that cannot tell the
two apart has to word a single message that is true of both, which is how "no entry" and "no
answer" reach an operator as the same sentence.

## Live state

The stream a client follows the stack on, what reaches the operator's and a member's,
and where a message goes, is on [its own page](web-api-live-state.md).

## Getting in

How a caller is admitted, by the per-run token, a session or an integration key, and the
limit wrong answers meet, is on [its own page](web-api-getting-in.md).

## Writing

```
POST /api/actions/<name>
```

Arguments mirror the command's. `G1-R1` requires every action to be available from every
surface, and this contract adds the converse: **the web API exposes nothing the CLI cannot
do.** An action that exists only here would be a behaviour implemented by a surface.

Long-running actions return a job identifier and report progress on the event stream, so a
browser tab that closes mid-repair does not orphan the work. The identifier is **redeemable**
— see [a job's outcome](web-api-wire.md#a-jobs-outcome) — because a name that cannot be turned back into an
outcome makes the reply an acknowledgement rather than an answer.

### Watching on a pass

Two actions answer where something streams from with a pass in it, and answer at once rather
than with a job (D11). `tune` takes a channel as `id` and answers kind `tuned`: the channel, the
member, the tuner's own stream as `direct` and the transcoded playlist as `transcoded`, each a
whole address at the guarded front door carrying its pass, the fingerprint of the certificate
the door presents, and when the passes lapse, or, where nothing can be located, `unlocated` with
the reason. Asked with `stream`, the live stream it answered, it asks the media server again and
renews the same passes, answering the same locations with when they now lapse, and with
`stop` as well it closes it. `play` takes a
title as `id` and the browser's `device`, and answers kind `play`: the title, the member, the
title's playlist at the stack's front door carrying an item pass as `stream_from`, and when the
pass lapses, or `unlocated` with the reason. Asked with `pass`, the pass it holds, in place of
`device`, it renews that pass and answers the same location with when it now lapses. Each is narrowed to the member who
asks, and each location is offered as a QR code wherever a surface shows it (`ARCH-R420`).

### Rehearsing

`--dry-run` is one flag over every command, and the core decides for each command how it
answers it: a read runs as it always does, a command that changes something reports what
it would do and changes nothing, and a command whose effect cannot be known without
producing it refuses the flag with its reason — a walkthrough, a searching trace and the
disruptive checks. An action takes the same request as the argument `dry_run` and
answers it as its command does. A rehearsal writes nothing and answers with the envelope
the command's rehearsal renders, and that envelope says it was a rehearsal; an action
whose command refuses the flag refuses the argument with the same reason (`ARCH-R131`).

A revocation rehearses as an action does. `DELETE /api/keys/{name}`,
`DELETE /api/device-keys/{name}` and `DELETE /api/push-endpoints/{name}` take
`{ "dry_run": true }` as their body, and given it remove nothing and answer with the envelope
the command's `--dry-run` renders, which says it was a rehearsal. Sent without a body, or with
`dry_run` false, each removes what it names, as it always has (`ARCH-R469`).

The statement is required because nothing else on the wire can stand in for it. Several
actions answer an unconfirmed request with a reading of what they would do, and that
reading carries `confirmed: false`. So does a rehearsal of the same action. A client that
inferred one from the other would label a rehearsal as a cost waiting to be agreed to, or
a reading as something that had been tried and written nothing, and each is a different
sentence to show somebody.

### A plugin, and what fills a capability

```
POST /api/actions/plugin-install    POST /api/actions/plugin-update
POST /api/actions/plugin-remove     POST /api/actions/plugin-run
POST /api/actions/plugin-prove      POST /api/actions/wiring-fill
POST /api/actions/credentials-revoke   POST /api/actions/internal-certificate-replace
```

What is installed and what the stack wires to what are read as their commands answer
them, `GET /api/plugins` and `GET /api/wiring`. A record or a wiring that cannot be read
is refused with a code the artefact lists, and is never answered with an empty list: an
empty list says nothing is installed, which is a different sentence from *this could not
be read* (`ARCH-R145`).

The eight writes take what their commands take ([ADR-0031](../../00-overview/decisions/0031-a-plugin-and-a-choice-are-web-writes-a-credential-is-not.md)):

| Action | Arguments | Answers |
|--------|-----------|---------|
| `plugin-install` | `source`, `inputs`, `dry_run`, `offer`, `approved` | a job, then `plugins` |
| `plugin-update` | `plugin`, `source`, `inputs`, `dry_run`, `offer`, `approved` | a job, then `plugins` |
| `plugin-remove` | `plugin`, `dry_run`, `offer` | a job, then `plugins` |
| `plugin-run` | `plugin`, `recipe`, `inputs`, `dry_run`, `offer`, `approved` | a job, then `plugins` |
| `plugin-prove` | `plugin`, `dry_run`, `offer` | a job, then `plugins` |
| `wiring-fill` | `capability`, `service`, `reason`, `dry_run`, `offer` | `substitution` |
| `credentials-revoke` | `plugin`, `credential`, `dry_run`, `offer` | a job, then `credentials` |
| `internal-certificate-replace` | `dry_run`, `offer` | a job, then `credentials` |

**The yes is the offer.** Each rehearsal answers an offer built from what it read, and
the write takes that offer, builds it again from what is there now, and refuses where the
two differ, naming what moved. A bare `confirm` is no yes to any of the eight (`ARCH-R146`).

`credentials-revoke` ends one grant a third-party plugin holds, as `lemonfiber credentials
revoke` does: the credential stops crossing to the plugin, whose services that read it
restart, and the plugin stays installed (`ARCH-R324`). It is a write over a grant, not over
a credential: it prints no value and replaces none, so it stays on this door while revealing
and rotating a credential stay at the terminal. A grant is given only by the install or
update offer that names it, through `approved`, as `<setting>@<plugin>` (`ARCH-R323`).

`internal-certificate-replace` replaces the certificate the media server presents at its
internal TLS port, as `lemonfiber credentials --rotate` does for it: every holder of a media
server credential is handed the new certificate's SHA-256 beside the old, the media server
serves the new one, and the old SHA-256 is withdrawn once each holder reaches it with the
new (`ARCH-R345`, `ARCH-R354`). It prints no value and its key never leaves the machine, so
unlike rotating a credential it is a write on this door.

`plugin-prove` runs the plugin's live proof again, as `lemonfiber plugin prove` does: a
pass clears every nonconforming record the plugin holds, and a failure keeps them and
names each case that failed (`F14-R16`, `ARCH-R215`).

**A source is any the command takes**: a catalogue name, a git repository or a path on
the machine ([ADR-0036](../../00-overview/decisions/0036-a-plugin-may-come-from-any-source-the-command-takes.md)).
A git source is fetched over https from a public host; a name resolving to any address
not out on the internet, as the plugin manifest contract classes addresses, is refused,
every address it answers with checked when the fetch is made, the fetch connecting only
to those, and no redirect followed (`ARCH-R152`). The rehearsal names the revision it fetched, and the offer is
built from it.

**A recipe runs on install, on demand or on claim**, as its manifest says. An install
recipe runs inside `plugin-install` and `plugin-update`; a demand recipe runs only
through `plugin-run`, which names the plugin and the recipe; a claim recipe runs once
the part its plugin claims answers `Ours`, after the install or update, or at the seed,
whose claim made it so (`F8-R20`). `inputs` carries each value a
recipe asks the operator for, as `name=value`, on `plugin-install`, `plugin-update`
and `plugin-run` alike. Until every one is given the act is refused as `PLUGIN-34`,
naming each input missing, so a client can ask the operator for exactly those; one no
recipe of that act asks for is refused the same way, naming it. An input is never part
of the offer and is never repeated back.

**What a recipe would send is agreed to as itself.** A rehearsal whose recipe would
carry a value to an external host lists each pair: the value's name, where it comes from,
and the destination by name, never a resolved address. The write takes the approval of
each pair in `approved`, apart from `offer`, and refuses where one is missing; the offer
still covers the list, so a pair that changed is refused as a moved offer (`ARCH-R147`).
A pair releasing a value a service of the stack answered with is agreed to the same way,
and the rehearsal lists it with its `release`, the sentence the manifest gives for carrying
the value away from that service, and its `from`, the service it was read from (`F8-R18`). Any other pair to a service in the stack is
listed too and carries no `approval`: what it carries neither leaves the machine nor leaves
the service it came from, so there is nothing to agree to, and an approval written for it is
refused as one no pair asks for.
An approval is given to the act that carries it and to no other: a pair approved at
install is asked for again by a demand recipe that carries it, and by each run of it.
The rehearsal lists the recipe's steps in order and names each adapter as lemonfiber's
(`ARCH-R148`), and a call refused because an external name answered from inside the
network ends with a code of its own, apart from a network that failed (`ARCH-R149`).
Every recipe, pair, destination and adapter field is present on a rehearsal and on the
record, an empty list where there is none, so *none* is never confused with *not read*;
a pair's `approval` is present exactly where the pair leaves the machine or carries a
release, and its `release` and `from` exactly where it carries one (`ARCH-R150`).

The installed plugins and the wiring each ride the event stream as their envelope: a
`plugins` event and a `wiring` event, sent when a client connects and whenever either
changes, an install that leaves a capability contested included (`ARCH-R151`).

Browsing what the catalogue offers is `GET /api/plugins/catalogue`, answered from the
verified index as `lemonfiber plugin catalogue --json` answers it, and listing nothing
the index's signature does not cover (`ARCH-R153`). What it answers, and to whom, is on
[its own page](web-api-the-catalogue.md) (`ARCH-R450`, `ARCH-R451`, `ARCH-R452`).

### Settings

```
POST /api/actions/settings-set      POST /api/actions/settings-clear
```

What the operator sets for the services and for the core, the closed list of the core's own
settings, and the two writes that change them are on [their own page](web-api-settings.md).

### Setting up

```
GET  /api/setup            POST /api/setup/answer     POST /api/setup/next
POST /api/setup/back       POST /api/setup/apply      POST /api/setup/recover
```

Named for the walk rather than for a command, because a wizard is one request read many
times: what it is standing on, an answer to that, and the movement between. `apply` is where
it stops asking and writes, and `recover` is what an apply that stopped part-way is answered
with — offered after the report has named what that apply had already written, so the choice
is made by somebody who has seen it.

These are writes and sit behind the same guard as the actions above. They are named here
because the first-run walk is where credentials are entered, and an endpoint that takes one
and is written down nowhere is the one nobody audits.

### What a stack says it can do

```
GET /api/capabilities
```

Every other surface runs on the machine the stack runs on, so it is the same version by
construction and never has to ask. A client on a phone is the first that can be older or
newer than what it is talking to, and the first that can hold several stacks at once, each
at a different version ([N1-R11](../../10-functional/features/n-companion/n1-companion-app.md)).

A version number does not answer the question. `GET /api/version` says which binary is
running; turning that into *what this stack can do* means a client carrying a table of which
release added which feature — a second copy of the changelog, on a different release cadence,
in a different repository. It goes wrong quietly: a client meeting a version its table does
not know either offers an action that fails when pressed, or hides one that works.

So the stack declares what it can do, and the client reads it rather than deduces it.

The payload is `kind: "capabilities"`, whose data maps a capability name to its state:

```json
{ "api_version": 1, "kind": "capabilities",
  "data": { "capabilities": {
      "/api/plugins":             "available",
      "/api/actions/wiring-fill": "available",
      "/api/actions/pull":        "unconfigured",
      "/api/actions/invite":      "unpermitted" } } }
```

**A capability's name is the path the surface serves the request at**: `/api/actions/<name>`
for an action and `/api/<name>` for a read. The set is generated from the lists the surface
routes by, so a request the surface gains is a capability it declares with nothing else to
keep in step, and a client already holds these names, because they are what it calls. A read
and an action may share a word, and they are two requests — reading what an uninstall would
take is not taking it — so each has a key of its own. What a client shows for one is its own
words and not the stack's.

Four answers, and the difference between them is the whole point — each is a different
sentence to show somebody:

| State | Means | What a client says |
|---|---|---|
| `available` | This stack can do it, and this credential may | offers it |
| `unconfigured` | The stack has it; something must be set up first | offers it, and says what is missing |
| `unpermitted` | The stack has it; this credential may not | says it is not theirs to do, not that it is broken |
| *absent* | This stack does not have it | says the stack is too old, naming what would provide it |

**Absence is the answer for a stack that is too old**, and it needs no coordination: a stack
that has never heard of a capability cannot name it, so a client meeting an older stack sees
the same thing it would see if the capability were removed. That is why the shape is a map
of what *is* rather than a list of flags, and why a client must treat an unknown key as
something it does not understand rather than as an error.

**The set is scoped to the credential, not only to the stack.** What a household member may
do is already the core's answer
([D6](../../10-functional/features/d-content/d6-household-identity.md),
[N3-R2](../../10-functional/features/n-companion/n3-household-companion.md)), so a capability
set that ignored who was asking would be a second permission model — the thing `N3-R2`
exists to prevent. `unpermitted` is how that answer arrives, and it is deliberately
distinguishable from `unconfigured`, because "you may not" and "nobody has set this up" are
not the same news.

**It says which stack is answering.** Beside the capabilities the data carries `stack`, the
stack's own identifier: the one pairing material carries
([N1-R62](../../10-functional/features/n-companion/n1-companion-app.md)), minted once and kept,
the same across a change of address and a replacement of the certificate. A client holding
several stacks, or meeting one again at a new address, tells them apart by it. Neither the
address nor the certificate's fingerprint can serve, because each changes in exactly the cases a
client most needs to recognise the machine, and the envelope's `host` names the machine an
answer is about rather than the stack giving it. It is carried to every credential that may read
the capabilities, a member's key included, because recognising a stack is not something a
credential's scope can make anybody unentitled to (`ARCH-R163`).

**It says whose credential asked.** The data carries `scope`: `operator`, `read`, `act` or
`member`. A client that words itself for the household, or decides what to offer, reads the
scope from it rather than inferring it from which reads came back permitted, because a read
permitted to two scopes says nothing about which one is asking, and the set of reads a scope
admits can grow (`ARCH-R179`).

**It is read, not pushed, and it can change under a client.** Configuring storage turns
`snapshots` from `unconfigured` to `available` without the session ending. So it is an
ordinary read: it carries the age every other reading carries
([N1-R9](../../10-functional/features/n-companion/n1-companion-app.md)), a client may retain
it and paint from it
([ADR-0019](../../00-overview/decisions/0019-a-screen-paints-before-it-reaches-the-stack.md)), and a client
that has not re-read it lately is holding an opinion rather than a fact.

**A revocation is a capability too.** Revoking an integration key, removing a phone's hardware
key and removing a wake address are each named by the path the surface serves them at,
`/api/keys/{name}`, `/api/device-keys/{name}` and `/api/push-endpoints/{name}`, with `{name}`
left as it is, and each is `available` or `unpermitted` exactly as the route itself decides for
this credential. A client draws no revoke control the credential cannot use, and reads which it
can rather than trying one (`ARCH-R468`).

**A capability is not a promise the action will succeed.** It says the action is offerable.
A repair may still be refused on its own terms, and that refusal is `G4`'s business, not
this endpoint's.

## What guards it

A writable API on loopback is reachable from any page the operator happens to visit — a page
cannot *read* a cross-origin response, but it can *send* a request the server acts on, and
DNS rebinding defeats a naive origin check. The CLI never had this exposure; nothing a web
page does reaches `argv`.

| Guard | Requirement |
|---|---|
| Bound to loopback, never all interfaces | [C6-R1, C6-R3](../../10-functional/features/c-trust/c6-web-security.md) |
| A per-run token, printed by the CLI at start, on every request | `ARCH-R52` |
| `Origin` and `Host` checked against the bound address | `ARCH-R53` |
| No proxying to an admin service | [C6-R12](../../10-functional/features/c-trust/c6-web-security.md) |
| Says plainly that it is unencrypted HTTP | [C6-R6](../../10-functional/features/c-trust/c6-web-security.md) |
| A loopback address, or a pinned certificate instead of one | `ARCH-R60`, `ARCH-R99` |

The token travels in a header. Never a query parameter: URLs reach logs, history and
referrers, and a credential that leaks into any of those has leaked.

## Version skew

The client declares the `api_version` it speaks. Because the built app is embedded from a
pinned submodule ([ADR-0012](../../00-overview/decisions/0012-web-assets-embedded-at-build-time.md)),
`build.rs` validates that declaration against the binary **at compile time** — the same
protection `ARCH-R6` already gives the embedded stack's `schema_version`. A mismatched pair
cannot be released.

The runtime check remains, because a browser may hold a cached older app. A mismatch there
refuses plainly and says which versions are involved, rather than rendering a page whose
fields have quietly changed meaning.

## The details two clients must agree on

The particulars two clients must agree on to talk to the same server — the token's
header, the address, the heartbeat, resuming the stream, a job's outcome, an action sent
again, the payload's type and how an instant is written — are on
[their own page](web-api-wire.md).

## Requirements

| ID | Requirement |
|----|-------------|
| **ARCH-R46** | The web API MUST carry the same `api_version` envelope as machine-readable command output. |
| **ARCH-R47** | A web API response MUST be identical to the equivalent command's machine-readable output. |
| **ARCH-R48** | The web API MUST NOT expose an action that is unavailable from the command line. |
| **ARCH-R49** | Live state MUST be served from the same gather that serves the other surfaces. |
| **ARCH-R50** | The event stream MUST emit a heartbeat, so a silent stream is distinguishable from a broken one. |
| **ARCH-R51** | A resumed event stream MUST NOT present values gathered before the gap as current. |
| **ARCH-R52** | Every request MUST carry a per-run token, delivered in a header and never in a URL; a request without it MUST be refused. |
| **ARCH-R53** | `Origin` and `Host` MUST be checked against the bound address, and a mismatch MUST be refused. |
| **ARCH-R54** | The client's declared `api_version` MUST be validated against the binary at build time. |
| **ARCH-R55** | An `api_version` mismatch at run time MUST be refused plainly, naming both versions, rather than rendering a partial view. |
| **ARCH-R56** | The contract artefact MUST be generated from the types the server serialises, never hand-written. |
| **ARCH-R57** | Regenerating the contract artefact MUST produce no diff, and CI MUST fail if it does. |
| **ARCH-R58** | An SDK's contract types MUST be generated from the artefact; hand-written response shapes MUST NOT be used. |
| **ARCH-R59** | The per-run token MUST be sent in the `X-Lemonfiber-Token` header. |
| **ARCH-R60** | A client MUST refuse a base address that does not resolve to a loopback address unless `ARCH-R99`'s condition is met, and MUST NOT refuse a loopback address for being named rather than numeric. |
| **ARCH-R61** | The event stream MUST emit a heartbeat at least every 15 seconds, and a client MUST treat twice that in silence as a broken stream. |
| **ARCH-R62** | Every event MUST carry an `id`, and a resuming client MUST send the last one it saw as `Last-Event-ID`. |
| **ARCH-R63** | A client MUST expose a payload typed by its `kind`, never as an untyped value. |
| **ARCH-R64** | The contract artefact MUST be published with every release, and an SDK MUST vendor it from an exact revision recorded beside the copy. |
| **ARCH-R65** | Generating an SDK's contract types MUST read the vendored artefact, and MUST NOT reach the network. |
| **ARCH-R66** | Regenerating an SDK's contract types MUST produce no diff, and CI MUST fail if it does. |
| **ARCH-R67** | Generation MUST refuse an artefact whose `api_version` the SDK does not implement, naming both versions, and MUST write nothing when it refuses. |
| **ARCH-R70** | A job identifier returned by a long-running action MUST be redeemable: a client MUST be able to learn from the server that the work ended and how it went, without having held a connection open since it started. |
| **ARCH-R71** | Redeeming a job identifier MUST answer finished work with the equivalent command's machine-readable output and work still in flight with the identical document the accepting reply carried; the two MUST be distinguished by status, never by a shape only this endpoint has. |
| **ARCH-R72** | A job identifier the run did not issue MUST be refused as absent, and MUST NOT be reported as still in flight. |
| **ARCH-R73** | The contract artefact MUST NOT describe a schema in a form whose meaning depends on which JSON Schema draft the reader applies, and SDK generation MUST refuse such an artefact, naming where it occurs, rather than generate from the half of it that it reads. |
| **ARCH-R74** | A refused read MUST carry a status that distinguishes what the request named and this product does not have, from a request that could not be answered as it was asked, from a failure of the machine; the body MUST be the error envelope in every case, and the status of a failure of the machine MUST NOT be given to either of the others. |
| **ARCH-R75** | The operator's password MUST be exchanged for a session by one request and MUST NOT be required by any other. |
| **ARCH-R76** | A session's secret MUST travel in the same header the per-run token does, so the surface reads one credential header. |
| **ARCH-R77** | A refusal a caller could correct by sending something else MUST be distinguished by its code from one nothing they could send would satisfy, and a refusal for too many failed attempts MUST say how long is left. |
| **ARCH-R78** | The API MUST expose the set of capabilities the stack can perform, each named by the path the surface serves it at, and a client MUST NOT derive that set from a version number. |
| **ARCH-R79** | A capability MUST be reported as available, present but unconfigured, or present but not permitted to this credential; a capability the stack does not have MUST be absent rather than reported as false. |
| **ARCH-R80** | The capability set MUST be scoped to the credential that asked, so that it carries the core's existing answer about what a household member may do rather than a second one. |
| **ARCH-R81** | A client MUST treat a capability name it does not recognise as one it does not understand, and MUST NOT refuse the payload for containing it. |
| **ARCH-R82** | The capability set MUST be readable again within a session, and MUST carry when it was read as any other reading does. |
| **ARCH-R99** | A client MUST refuse a base address that is not loopback unless it was given a certificate pin for that stack, and MUST enforce that pin during the TLS handshake so that no request is written to a peer it has not verified. A client MUST NOT offer any means of reaching a non-loopback address without a pin, or of weakening verification ([ADR-0025](../../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md)). |
| **ARCH-R129** | A definition in the contract artefact MUST NOT take a name an SDK's generator writes itself, and SDK generation MUST refuse such an artefact, naming the definition and the kind that carries it, rather than emit one name describing two shapes. |
| **ARCH-R131** | Every action whose command reports a rehearsal under `--dry-run` MUST take that rehearsal as the argument `dry_run`; given it, the action MUST write nothing and MUST answer with the envelope the command's rehearsal renders, and that envelope MUST say it was a rehearsal in a field other than `confirmed`, so that a rehearsal and an unconfirmed reading are told apart. An action whose command refuses `--dry-run` MUST refuse `dry_run` with the reason the command gives (`F1-R2`, `ARCH-R47`, `ARCH-R48`, `N13-R10`). |
| **ARCH-R132** | Work ended before it finished MUST be answered, when its name is redeemed or released, with whether the name was released or the work was let go because nothing asked about it, and MUST be told apart from work that finished, work that stopped on a failure and work still in flight (`N23-R13`). |
| **ARCH-R133** | The contract artefact MUST describe the body every web API route takes, the setup routes' included — the answer to each question setup asks, and the choice a recovery takes — generated from the types the server reads a request into, so that a client builds a request from the artefact rather than from the server's source (`ARCH-R56`, `G1-R14`). |
| **ARCH-R134** | The contract artefact MUST publish every action the web API takes, with each argument it takes, the argument's type and the consent the action asks for before it writes, generated from what the server reads; an SDK MUST generate the actions it offers from that list, so that an action or argument the core adds reaches a client as a regenerated diff (`ARCH-R47`, `ARCH-R48`, `ARCH-R58`). |
| **ARCH-R135** | Work stopped because other work held the stack MUST be answered with `409`, and MUST NOT be given the status of a failure of the machine, so that a client can say another operation is in progress (`B6-R8`) and offer the same request again once it is done. |
| **ARCH-R138** | Every refusal the web API answers with MUST carry the error envelope as its body, and its problem code MUST name why the request was refused. Refusals that share a status and call for different remedies MUST carry different codes. A client MUST decide what a refusal means from its code and MUST NOT decide it from the sentence. A client MUST read a refusal that carries no code, or a code it does not know, by its status alone. A refusal that says how long to wait before asking again MUST carry it in whole seconds both as `Retry-After` and as the problem's `retry_after`: the time left where the refusal knows it, and the wait its code declares otherwise; a problem with no wait to say MUST NOT carry `retry_after`. |
| **ARCH-R139** | The contract artefact MUST list every code a refusal may carry, with the code's registry name, the status it is answered with and its description. An SDK MUST generate its list of refusal codes from that list and MUST NOT keep one of its own. |
| **ARCH-R140** | The web API MUST answer `GET /api/news` with, for each of updates, requests and problems, the items newest first, each with its identifier — a release's version, a request's reference (`D7-R16`), a check and its onset (`C1-R17`) — and the stack's own words for it, a request being newer by when it was asked, whichever of the request service and the core keeps it, and the response MUST be identical to `lemonfiber news --json` (`ARCH-R47`). |
| **ARCH-R141** | The event stream MUST carry a `news` event naming, for each kind `ARCH-R140` lists, the identifiers of its ten newest items, sent when a client connects and whenever any of them changes. |
| **ARCH-R142** | Work refused because the consent it was given names an offer or a listing that has since moved MUST end with a problem code the artefact lists among its refusals, with the status that work is answered with when its name is redeemed, so that a client can re-offer rather than report a failure (`N2-R6`, `A5-R13`, `ARCH-R138`). |
| **ARCH-R145** | The web API MUST answer `GET /api/plugins` and `GET /api/wiring` with the envelopes `lemonfiber plugin installed --json` and `lemonfiber wiring --json` answer, and a record or a wiring that cannot be read MUST be refused with a problem code the artefact lists, and MUST NOT be answered with an empty list. |
| **ARCH-R146** | The actions `plugin-install`, `plugin-update`, `plugin-remove`, `plugin-run`, `plugin-prove` and `wiring-fill` MUST take `dry_run` and `offer`, MUST refuse a bare `confirm` as consent, and MUST end with a listed problem code when the offer they were given has moved. |
| **ARCH-R147** | A rehearsal whose recipe would carry a value to an external host, or carry a value by a pair releasing it, MUST list each pair as the value's name, its origin and the destination by name, never a resolved address, and a released pair with its release and the service it was read from; the write MUST take the approval of each such pair as an argument apart from `offer`, and MUST refuse where any is not approved. |
| **ARCH-R148** | A rehearsal MUST list the steps its recipe would run, in order, and MUST name each adapter a step uses as lemonfiber's. |
| **ARCH-R149** | A call refused because an external name resolved to a loopback, private or link-local address MUST end with a listed problem code apart from the one a failed network ends with. |
| **ARCH-R150** | Every recipe, pair, destination and adapter field MUST be present on a rehearsal and on the installed record, an empty list where there is none, except a pair's `approval`, which MUST be present exactly where the pair carries a value to an external host or carries a release, and its `release` and `from`, which MUST be present exactly where the pair carries a release. |
| **ARCH-R151** | The event stream MUST carry a `plugins` event and a `wiring` event, each with its envelope, sent when a client connects and whenever the installed record or the wiring changes. |
| **ARCH-R152** | A git source named to `plugin-install` or `plugin-update` MUST be fetched over https from a host none of whose addresses is one the plugin manifest contract classes as not out on the internet, every address checked when the fetch is made, the fetch connecting only to those and following no redirect, and a source refused so MUST end with a listed problem code. |
| **ARCH-R153** | The web API MUST answer `GET /api/plugins/catalogue` with the plugins the verified catalogue index lists, as `lemonfiber plugin catalogue --json` answers, and MUST NOT list an entry the index's signature does not cover. |
| **ARCH-R450** | The `plugin-catalogue` read MUST answer one of three states as a normal answer: `listed`, with the verified index's `published` date, its `serial`, its entries and how many entries it holds that could not be listed; `off`, with the `key` that is switched off, the `value` that turns reaching the catalogue on and the `action` that writes it; or `failed`, with the problem code and summary an install by name would be refused with. It MUST NOT answer an empty list for `off` or `failed`. |
| **ARCH-R451** | Each `plugin-catalogue` entry MUST carry the plugin's `id`, `name`, `description`, `version` and `without_it` as the verified index signs them, and, for a plugin installed on this machine, the `version` installed and whether the catalogue's version is newer by semver; it MUST NOT carry an origin, a revision, a digest, a grant or a credential. An index entry lacking any of those facts MUST be counted as unreadable rather than listed or failing the read. |
| **ARCH-R452** | The `plugin-catalogue` read MUST be answered to an operator only, as `plugin-install` is; MUST NOT reach the catalogue where reaching it is switched off; MUST refuse a verified index older than the newest this machine has verified, as `failed`; and MUST NOT write what it read, the newest serial included. |
| **ARCH-R215** | The web API MUST answer `POST /api/actions/plugin-prove`, taking `plugin`, `dry_run` and `offer`, with a job and then the `plugins` envelope, running the live proof `lemonfiber plugin prove` runs, and a passing proof MUST clear the plugin's nonconforming records while a failing one MUST keep them and name each failed case. |
| **ARCH-R156** | The web API MUST answer `GET /api/playing` with every session the media server is playing now, each naming the member watching and what they are watching, as `lemonfiber playing --json` answers. A member, and a key scoped to one, MUST be answered with their own sessions only, narrowed by the command that runs rather than filtered from every session. |
| **ARCH-R157** | A member, and a key scoped to one, MUST be admitted to the event stream narrowed to them: it MUST carry their own household row, their held shelf and what they are playing, each as the read answering it answers that member, and MUST NOT carry anything gathered for the operator. |
| **ARCH-R158** | A member's stream MUST emit the heartbeat, resume and mark values gathered before a gap as stale as the operator's does (`ARCH-R50`, `ARCH-R51`), and MUST end when the member is removed or their key is revoked. |
| **ARCH-R159** | The contract artefact MUST list every read the web API serves, each with its path, the query parameters it takes and whether each may be given more than once, and the kind it answers with or that it answers with a file, generated from the tables the surface routes and refuses reads by rather than written beside them. |
| **ARCH-R160** | Each action the artefact publishes as callable by a key MUST also say whether calling it again with the same arguments leaves the stack as calling it once did, judged by the state the stack ends in rather than by whether the work is done again. |
| **ARCH-R161** | Each request in the household document `GET /api/requests` and `lemonfiber household --json` answer with MUST carry the kind of title it asked for, the year that title came out, when it arrived on the media server, and the identifier the media server holds it under, as `GET /api/held` names it. The year MUST be absent until the request has been handed to the service that files it, and the arrival and the identifier MUST be absent until the title is on the media server, never present as null. |
| **ARCH-R162** | The event stream MUST carry an `alert` event when an alert starts and when it resolves, carrying what happened, what it means, what to do, its severity and which way it went, and an identity that is the same for an onset and the resolution that ends it and differs for each recurrence. |
| **ARCH-R163** | The capabilities answer MUST carry the stack's own identifier, the one pairing material carries (`N1-R62`), to every credential it answers, a key scoped to a member included, and MUST NOT carry the address, the certificate's fingerprint or the envelope's `host` in its place. |
| **ARCH-R164** | The rehearsal of each action the artefact publishes as callable by a key and as taking `dry_run` MUST answer an offer built from what it read. A call carrying that offer MUST be refused, with a problem code the artefact lists, where the offer built from what is there now differs, and a call carrying no offer MUST act as it would without one. Each `key_callable` entry MUST say whether the action answers an offer. |
| **ARCH-R165** | The web API MUST read an `Idempotency-Key` header on an action request as the name of the attempt it is, and MUST carry out an action request without one as an attempt of its own. |
| **ARCH-R166** | An action request carrying the key of an attempt the same caller sent and the web API still remembers MUST be answered with what that attempt was answered with — the same job name, or the same status and envelope, a failure included — and MUST NOT run the action again; one arriving while that attempt is still being carried out MUST wait for its answer. Work that ends without an answer MUST be answered `500` with a problem code the artefact lists, to the first send and to every send waiting on it, and its attempt MUST be forgotten. A request refused before its action is reached MUST NOT be kept as an attempt. |
| **ARCH-R167** | An action request carrying a key the same caller already sent with another action or other arguments MUST be refused with a problem code the artefact lists, at `400`, and MUST NOT run. |
| **ARCH-R168** | Attempts MUST be held in memory only and per caller, each for the minutes `LEMONFIBER_IDEMPOTENCY_MINUTES` names from its first send, `30` where it names none, and up to the count `LEMONFIBER_IDEMPOTENCY_KEYS` names, `256` where it names none, both read at each send; a caller's attempt past that count MUST let go of that caller's oldest answered attempt and of no other caller's, and an attempt still being carried out MUST NOT be let go, by age or for room. |
| **ARCH-R169** | An `Idempotency-Key` MUST be one to 255 visible ASCII characters given once; an action request carrying anything else under that header MUST be refused with a problem code the artefact lists, at `400`, before anything runs. |
| **ARCH-R170** | SDK generation MUST refuse a `$ref` in the contract artefact that it cannot resolve to a definition in the vendored copy, naming the reference and the file it appears in, and MUST write nothing when it refuses. |
| **ARCH-R173** | The contract artefact MUST describe the event stream: every event kind `GET /api/events` emits, with the schema of its payload, and the heartbeat's interval, generated from the types the stream serialises. |
| **ARCH-R174** | The contract artefact MUST carry one example of each kind, each read and each action, drawn from the core's golden test fixtures, and CI MUST refuse an example that does not validate against its schema. |
| **ARCH-R175** | The core MUST publish its code registry as `contract/codes.json`, each code with its family, name, severity, exit code, HTTP status, summary, meaning, remedy, the household sentence and remedy a member's session is told in their place, whether it is a fault of the stack, and the version it first appeared in (`since`), generated from the registry it raises from; `reference/error-codes.md` MUST be generated from that file, and CI MUST refuse either when it differs from what generates it. |
| **ARCH-R176** | `release-contract` MUST attach `contract-diff.json` to each release, naming every kind, definition, read, action, refusal and event kind that release's contract artefact added, removed or changed against the previous release's. |
| **ARCH-R177** | The core MUST generate `contract/web-api.openapi.json`, an OpenAPI document of the web API, from the contract artefact, and CI MUST refuse it when it differs from what the artefact generates. |
| **ARCH-R178** | The event stream MUST carry, to the operator and to a `read` or `act` key, a `playing` event with every session the media server is playing now, in the envelope `GET /api/playing` answers that credential with, sent when a client connects and again every 5 seconds, the pace a member's stream sends what they are playing at. |
| **ARCH-R179** | The capabilities answer MUST carry the scope of the credential that asked, one of `operator`, `read`, `act` or `member`, and a client MUST read the scope from it rather than infer it from which reads are permitted. |
| **ARCH-R218** | The `invitation` envelope MUST carry `join`, the join link, where `D6-R22` gives one, and `unjoinable`, the sentence `D6-R24` requires, where it gives none and the invitation is not a rehearsal. |
| **ARCH-R219** | `POST /api/session` MUST accept `claim` beside a member's `name` and `password` (`D6-R25`). It MUST refuse a claim on an invitation that is not open with `401` under one code, whether the token is unknown, spent, lapsed or declined; MUST refuse a password shorter than the minimum under a code of its own naming the minimum (`D6-R26`); MUST count a claim against the attempts a sign-in is counted against; and MUST remain the one route that answers without a token. |
| **ARCH-R441** | `POST /api/session/code` MUST answer a request carrying no token. Asked with `{}`, it MUST ask the identity source's `sign_in_by_code` for a device id the core draws and answer a `sign-in-code` envelope carrying the code, `approve_at`, `lapses_at` and `waiting`, a handle of 128 random bits the core draws, and MUST keep the id the source answered against that handle and the session the request carried, never answering or logging it. Asked with `{ "waiting": … }`, it MUST answer the same kind while the code waits and the `admission` envelope of a member's session once `signed_by_code` answers a member, spending the handle, and MUST refuse with `401` under one code a handle that is unknown, lapsed or spent, sent with a session other than the one that asked, or, with `LEMONFIBER_SIGN_IN_CODES_BY_ADDRESS` on, sent from another network address than the one that asked. It MUST refuse an ask with `429`, carrying how long is left in `Retry-After` and the problem's `retry_after` (`ARCH-R138`), from a source, the session the request carries and its network address otherwise (an IPv6 address by its `/64`), with `LEMONFIBER_SIGN_IN_CODES_WAITING` codes waiting or `LEMONFIBER_SIGN_IN_CODES_PER_PERIOD` asked within the last `LEMONFIBER_SIGN_IN_CODES_PERIOD`, while still issuing codes to every other source, and MUST NOT count finishing against either (`ARCH-R377`). |
| **ARCH-R442** | The contract artefact MUST carry `household-words.json`, named in its index as `household_words`, holding what a member's surface may not show (`G2-R16`): the name of every part the bundle pins and of every service, engine and tunnel the stack could run that it pins none for, every term for how the stack is built and run, every unit a size is written in, every mark that shows an address or a rate, every name lemonfiber declares under `G2-R14` with what it names, and examples of text a version, an address or a rate makes unfit for a member, each with what it names. It MUST be generated from the one list the core's own tests hold a member's text to, and CI MUST refuse it when it differs from what that list generates. |
| **ARCH-R220** | An envelope MUST NOT carry a drawn QR code. A surface MUST draw each code from the address, link or text the envelope carries, exactly as given (`G1-R15`). |
| **ARCH-R223** | Every sentence the core sends a client over the web API or a capability contract (a refusal's summary and remedy, a reason, a report, and each code's meaning and remedy in the registry) MUST be plain text carrying no markup, and CI MUST refuse a core sentence written with a code span or emphasis. |
| **ARCH-R254** | The web API MUST answer `GET /api/settings` as `lemonfiber settings --json` answers, with every setting in the core's settings store: its name, whose it is, each service that reads it and the variable it is read into, the declared default, and the operator's value where one is recorded; only the operator MUST be answered, and a member, a key scoped to one, and a `read` or an `act` key MUST be refused. |
| **ARCH-R255** | `POST /api/actions/settings-set` and `settings-clear` MUST take what `lemonfiber settings set` and `lemonfiber settings clear` take; each rehearsal MUST name every entry the change regenerates and every service it restarts and answer an offer, the write MUST refuse where what it would change moved since, naming what moved, and each write MUST be journalled. |
| **ARCH-R352** | `GET /api/settings`, `lemonfiber settings --json` and the `settings` event MUST carry, for each setting that declares `one_of`, every value with the `needs` it is a choice under and whether it is a choice now, for each reference its `needs` and whether they are met, and each service `ARCH-R351` keeps from starting with each setting or secret it waits for, never by value. |
| **ARCH-R256** | The settings read MUST list each secret a service's environment names, with whose it is, the services that read it, where its value came from and whether one is held, and MUST NOT carry a secret's value; neither settings write MUST take a secret, and naming one MUST be refused, naming it. |
| **ARCH-R257** | The settings MUST ride the operator's event stream as a `settings` event, sent when a client connects and whenever one changes, only to the per-run token and an operator session, and MUST NOT be sent on a member's stream or to a key of any scope. |
| **ARCH-R461** | Each setting a `settings-set` or `settings-clear` answer moves MUST carry `default`, what it falls back to while it holds no operator value: `{"of": "core", "value"}` for one of the core's own settings, `{"of": "declared", "value"}` where every reader whose `needs` are met declares the same default, `{"of": "per-reader", "readers"}` where they differ, each reader with its service, variable, default and whether its `needs` are met, and `{"of": "none"}` where nothing declares one; the default MUST be part of what the rehearsal's offer answers, so a write whose default moved since MUST be refused naming it, as any other moved part is (`ARCH-R146`); and the journal MUST keep each moved setting's default as it was at the act. |
| **ARCH-R258** | `POST /api/device-keys` MUST take `name`, `public_key` (a P-256 SubjectPublicKeyInfo in base64url), `attestation` (an object tagged by `platform`: `{"platform": "android", "chain": […]}`, the key attestation chain as each certificate's DER in base64url, the key's own certificate first, or `{"platform": "ios", "object": …}`, the App Attest attestation object's CBOR in base64url, attested with the SHA-256 of exactly the bytes `public_key` decodes to as its client data hash, hashed once) and `password` from an operator session, and MUST answer the `device-key` envelope with the name, the public half's fingerprint, its `backing` (`strongbox`, `enclave` or `tee`) and the registration time; a missing attestation, one that does not verify, one placing the key in software and one naming an app the core does not trust MUST each be refused with a code of its own listed among the artefact's refusals (`C10-R23`). |
| **ARCH-R259** | `GET /api/device-keys` MUST answer `device-keys`, listing each device key by name, fingerprint, backing, registration time and last use, and `DELETE /api/device-keys/{name}` MUST revoke one; both MUST be refused to a member session and to a key (`C10-R26`). |
| **ARCH-R260** | `POST /api/device-keys/{name}/challenge` MUST answer `device-challenge` with a fresh `challenge` and when it `expires`, from an operator session for a registered device key (`C10-R24`). |
| **ARCH-R261** | `POST /api/keys` MUST accept `device`, `challenge` and `signature` in place of `password`, the signature being ECDSA P-256 over SHA-256 of the line-feed-ended UTF-8 lines `lemonfiber-mint/1`, the challenge, the name, the scope, the purpose and `claim` or `key`, in base64url; the artefact MUST publish that form, and the refusals of `C10-R25` MUST each carry a code of its own listed among the artefact's refusals. |
| **ARCH-R293** | The `keys` envelope MUST carry `proved_by` on each key minted with a device key's signature, naming that device key, and MUST leave it out of a key minted any other way (`C10-R33`). |
| **ARCH-R294** | The `version` envelope MUST carry `attestation_status`, the instant the build's snapshot of Google's attestation status list was taken, and the refusal of an attestation whose chain that snapshot lists as revoked or suspended MUST carry a code of its own listed among the artefact's refusals (`C10-R34`). |
| **ARCH-R262** | The identities of the operator's own builds MUST be the core setting `LEMONFIBER_DEVICE_KEY_APPS`, read by `GET /api/settings` and written by `settings-set` and `settings-clear` as every setting is: a comma-separated list of `android:<package>@<SHA-256 of the signing certificate, in hex>` and `ios:<Team ID>.<bundle ID>`. A value naming an identity in neither form MUST be refused, naming it; the official identities the build ships MUST be read alongside and MUST NOT be part of the value (`C10-R30`). |
| **ARCH-R274** | Every instant the web API reads or writes, in a request, a response, an event or a link the core builds, MUST be a whole number of seconds since the Unix epoch: a JSON integer in a body, and its decimal digits in a link's query. It MUST NOT be written as a string, with a fraction, or with a zone or an offset; a command's `--json` output MUST write instants alike; and a stamp lemonfiber passes on verbatim from a service's own output MUST NOT be presented as one of its instants. |
| **ARCH-R278** | A core setting MUST be one the list under [the core's own settings](web-api-settings.md#the-cores-own-settings) names; `lemonfiber settings` and the settings writes MUST take a core setting and no other `LEMONFIBER_*` key, and `lemonfiber config` MUST take every other `LEMONFIBER_*` key and no core setting; a name either command takes, given to the other, MUST be refused naming the command and the name that take it. |
| **ARCH-R279** | The artefact MUST publish the notification kinds as a closed union, `problem`, `completion`, `update`, `backup`, `request`, `member` and `ready`, and every `alert` event MUST carry exactly one as `notification` beside its event kind: `problem` for every condition at warning or worse, at onset and resolution; `completion` for work the operator asked for finishing; `update` for an update to the stack or lemonfiber being available; `backup` for a backup that succeeded; `request` for a household member's request newly waiting on the operator; `member` for an invitation accepted, declined or lapsed; and `ready` for something a household member asked for arriving. `request` and `member` alerts MUST ride the operator's stream and wake only endpoints an operator session registered, and MUST NOT reach a member. A `ready` alert MUST be addressed to the one member whose ask arrived, MUST be raised once per ask, when the house first holds any of it, and MUST ride that member's stream and reach only that member's own push endpoints and the back-ends that member chose; its words MUST be the household's ("Something you asked for is ready"), naming the title on the member's own stream and naming no title, service or state of the stack on a push endpoint or a back-end; it MUST NOT be raised for an ask whose request service already tells that member it is available (`B5-R1`). The core MUST raise no other alert addressed to a household member. |
| **ARCH-R280** | `GET /api/alerts` MUST carry `kinds`, the notification kinds this stack raises as it is configured, each from the union `ARCH-R279` publishes. |
| **ARCH-R281** | A stream opened with `Last-Event-ID` MUST be sent, before anything said after it opened and in the order said among what `ARCH-R455` sends again, every `alert` event raised after that id, from the last 24 hours and at most the last 200, these being kept for the run alone; where the id is from another run, one the run has not reached or cannot be read, it MUST be sent every one kept. Before all of it, it MUST be sent one `replay` event carrying no id, whose `alerts` is `partial` where an alert raised after that id is no longer kept or the id is one of those, and `whole` otherwise; a `replay` event MUST NOT take a place in the run or be sent again. A stream opened without one MUST be sent no past alert and no `replay` event (`ARCH-R162`). |
| **ARCH-R282** | An operator session MUST be able to register a UnifiedPush endpoint for one device with `POST /api/push-endpoints`, taking `name`, an `https` `endpoint`, and the WebPush `p256dh` key and `auth` secret, and to list them with `GET /api/push-endpoints` and remove one with `DELETE /api/push-endpoints/{name}`; the command line MUST list and remove them too. Every answer about an endpoint, a registration's, a listing's and a removal's, on every surface, MUST name its address by `host`, the address's host alone, and `fingerprint`, the first 16 lower-case hexadecimal digits of the SHA-256 of the whole address, and MUST NOT carry the whole address. On every alert's onset and resolution the core MUST send each registered endpoint a WebPush message encrypted under RFC 8291 whose content says only that the stack has something to say and carries the wake's id, MUST record a distributor's `404` or `410` as a failed delivery and keep the endpoint, and MUST refuse an endpoint that is not `https` or whose name another holds, naming it. A member session MAY register, list and remove endpoints of its own, held under that member and woken only for `ready` alerts addressed to them; it MUST NOT see or remove another's. A key MUST NOT register, list or remove endpoints. Every registration and removal MUST be journaled. |
| **ARCH-R288** | A finding a read leaves `unverified` because checking it disturbs something MUST carry `disruptive`: what checking it disturbs, in the stack's words; `bounded` (whole seconds the disturbance is bounded to, or absent where the stack bounds none); and `only` (the check or group a `diagnose` action takes to run it); and the `diagnose` action MUST accept that `only` as given. |
| **ARCH-R289** | The `space` action MUST accept `only`, a list of categories the offer it answers names as costing nothing, and with the offer's name MUST reclaim those categories alone; a category the offer does not name MUST be refused, naming it, with nothing removed. |
| **ARCH-R290** | A `trace` that stopped at `monitored` where asking the indexers would tell nothing at the quality from nothing at all MUST carry `searchable`: what the search spends, in the stack's words, and that it covers the curator's wanted list at the quality in force; a trace that would spend no search MUST NOT carry it. The `search` action MUST accept `disruptive` absent or `true`, and the artefact MUST NOT publish a default it refuses. |
| **ARCH-R409** | Seed MUST ask each filler's `events` with the address `https://host.docker.internal:<port>/api/notify/events`, `<port>` the port the web surface was last served encrypted on where a container reaches it, or with `LEMONFIBER_EVENTS_ADDRESS` followed by `/api/notify/events` where that `https` address is set, and with the SHA-256 digest of the certificate the web surface presents, which the adapter MUST pin; the web surface MUST answer the name `host.docker.internal` at `POST /api/notify/events` and nowhere else; where neither address exists seed MUST ask no filler and MUST say why; an adapter MUST be given `host.docker.internal` as the engine's host gateway where the engine does not resolve it itself. |
| **ARCH-R420** | The web API MUST serve `GET /api/channels`, narrowed to the member who asks, with the channels `D11-R11` answers; MUST answer action `tune` taking `id` (a channel), or `stream` with an optional `stop`, with kind `tuned` carrying `channel`, `member`, `stream`, the live stream a renewal or a stop names, `direct`, `transcoded`, `fingerprint` and `lapses`, or `unlocated`; and MUST answer action `play` taking `id` and `device`, or `id` and `pass` to renew it, with kind `play` carrying `id`, `member`, `stream_from` and `lapses`, or `unlocated`; each at once and without a job, each narrowed to the member who asks, and `lemonfiber channels`, `lemonfiber tune` and `lemonfiber play` MUST answer the same. |
| **ARCH-R437** | The web API MUST serve `GET /api/guide`, narrowed to the member who asks, with the channels `D11-R11` answers them, each carrying `programmes`, each with `title`, `certificate`, `starts` and `ends`, and `guide_until`, as `D11-R17` answers them, at once and without a job, and `lemonfiber guide` MUST answer the same. |
| **ARCH-R398** | `POST /api/notify/events` MUST accept a neutral event only with the events key the core minted for the filler that sends it, MUST refuse every other caller, and MUST hand each event to B5's policy, a `failed` or `health` event as `problem` and an `imported` or `added` event as `completion`; seed MUST mint each curator's and the media server's events key, write it to that filler's adapter readable by the operator's uid alone, and ask its `events` with the core's address and that key. |
| **ARCH-R399** | The core MUST deliver every alert B5 says is worth telling to each configured back-end that is not held, each independently of the others, speaking ntfy, gotify, a webhook, an Apprise URL and UnifiedPush itself; a delivery MUST carry the alert's notification kind and summary and MUST NOT carry a member's name, what anybody is watching or a title a member asked for; each kind MUST be an outbound entry with its own switch. |
| **ARCH-R400** | `GET /api/notify` MUST answer the operator session alone with `state`, `backends` and `unread` as the section on where a message goes says, each delivery's `outcome` `confirmed`, `sent` or failed with the back-end's answer; a member session and a key MUST be refused it, and a store that cannot be read MUST refuse the read. |
| **ARCH-R401** | `lemonfiber notify add`, `set`, `test`, `remove` and `list` MUST configure, prove and list back-ends non-interactively; a back-end's secret MUST be kept in the credential store and never in its record; no back-end MUST be configured by default; a back-end on a host the core knows to be hosted MUST be refused unless added with `--hosted`, and one so added MUST carry the note that it leaves the self-hosted posture. |
| **ARCH-R402** | A back-end MUST be reported proven only once a test carrying an id it was sent is observed arriving, in an ntfy topic's or a gotify server's history or confirmed by the phone a wake went to; one whose arrival cannot be observed MUST stay unproven; each delivery to a back-end whose history is readable MUST be confirmed the same way. |
| **ARCH-R403** | A delivery that fails MUST be retried at the back-end's own attempts and delays, five at 1, 5, 15, 60 and 360 minutes unless `notify add` or `notify set` gave others, and then stand failed; a back-end answering `401` or `403`, or whose credential `notify set` changed, MUST be held, with no delivery to it, until `notify test` proves it again. |
| **ARCH-R404** | Every wake MUST carry an id inside its sealed payload, and `POST /api/actions/push-woken`, taking the endpoint's `name` and the `id`, MUST mark that wake's delivery `confirmed` for the operator session that registered the endpoint and refuse any other caller. |
| **ARCH-R405** | `lemonfiber notify set <id> --members <name>` MUST offer a back-end to the household under that name and `--no-members` withdraw it; `GET /api/notify/mine` MUST answer a member session with the back-ends offered to members, each by its household name and whether this member receives on it, and whether their own push endpoint is registered, and nothing technical; `POST /api/actions/notify-choose` MUST set which offered back-ends that member receives `ready` alerts on and refuse an id not offered; a key MUST be refused both, and a back-end withdrawn MUST stop reaching every member who chose it. |
| **ARCH-R416** | The web API MUST answer `GET /api/front-door` with `reaches` on the door and on each service beside it, `here`, `not-here` or `unknown`, judged by the core from the request's source as the section on the front door says, and with why a service has no address where it has none. A member, and a key scoped to one, MUST be answered with the services facing `asking`, `watching` or a `shelf` alone, narrowed by the command that runs rather than filtered from every service, in the household's words and without how the door was chosen, and MUST NOT be handed an address that reaches `not-here` ([G10-R12](../../10-functional/features/g-ux/g10-household-web.md), [G10-R13](../../10-functional/features/g-ux/g10-household-web.md), [N9-R10](../../10-functional/features/n-companion/n9-who-gets-in.md)). |
| **ARCH-R426** | Each request in the household document `GET /api/requests` and `lemonfiber household --json` answer with, and each request `GET /api/news` and `lemonfiber news --json` list, MUST carry `kind`, the kind of title it asks for (`tv`, `movies`, `music` or `books`), and an ask for music or books MUST carry `unit`, what it asks for (`album`, `artist`, `book`, `author` or `series`), so that a client tells a whole artist, author or series from one album or book without reading the household's words; either MUST be absent where the core cannot say, never present as null, and adding them leaves `api_version` as it is ([D7-R16](../../10-functional/features/d-content/d7-approval-quotas.md)). |
| **ARCH-R447** | `GET /api/in-flight` MUST answer the `in-flight` envelope. It lists each download still coming down inside what stopping the forms and services named by its repeatable `forms` and `services` would stop, or inside the whole stack where neither is named, with its `protocol`, its `name` and its `progress` from 0 to 100. It MUST ask only the download clients that stop would stop, MUST leave out a client that does not answer and a finished download, and MUST change nothing. It MUST be answered to an operator session and to a key whose scope reaches reads, and refused to a member session and to a key scoped to a member. `lemonfiber down` MUST ask the same question of the services it is given as of the forms. |
| **ARCH-R448** | `GET /api/served` MUST answer the `served` envelope for the run answering, the one `lemonfiber ui` settles (`G1-R2`). The envelope carries `port`, `encrypted`, `network`, `named` and `unrecorded`, and, where the run is encrypted, a `certificate` with `fingerprint` (`N1-R18`), `subject`, `subject_cut`, `issuer`, `issuer_cut`, `self_signed`, `names`, `names_more`, and `valid_from` and `valid_until` in whole seconds (`ARCH-R274`). A control or layout character in a subject, an issuer or a name MUST be written as its RFC 4514 hex pair. A subject or issuer MUST be at most 512 characters as written, cut there with its `_cut` field `true`. `names` MUST hold at most 64 whole names, each at most 512 characters as written, with every name left out, for being too many, too long to show or not written as text, counted in `names_more`. A string MUST NOT carry a remark about what was left out. It MUST be read from what the run settled, and MUST NOT make, replace or write anything. It MUST NOT carry the private key in any form, the certificate's DER or PEM encoding, a file path or the per-run token. It MUST be answered and refused as `ARCH-R447` is. |
| **ARCH-R449** | The `config` read that `GET /api/config` and `lemonfiber config --json` answer MUST carry `decisions`: one entry for each answer setup writes, in the core's order and whether or not the configuration holds it, with its `key`, its `cost` (`cheap` or `consequential`, `A4-R3`), `affects`, what changing it affects in the core's words, `held`, whether it is held, in the configuration or the settings store, `credential`, whether its value is withheld as a credential, and `setting`, the name `settings-set` takes where the answer is kept in the settings store, absent where `config-set` takes it. An entry MUST NOT carry the value, which is read where it is held, withheld there as it is. The keys MUST be a closed set the contract declares. The read MUST be answered and refused as it is without them. |
| **ARCH-R453** | The `config` read that `GET /api/config` and `lemonfiber config --json` answer MUST carry `unmanaged`: one entry for each area the operator declared unmanaged that the declaration's parser keeps, in the order written, with its `area` and its reason `why` as written, and `covers`, each thing the area covers now by the core's own rule, as its `kind`, `service`, `path` or `setting`, taken from what is covered and never from the shape of the name, and its `name`, and empty where the area covers nothing. A control or layout character in an `area` or a `why` MUST be written as `\xx`, each byte of its UTF-8 in hex; an `area` or a `why` longer than 512 characters as written MUST be its first 512, with `area_cut` or `why_cut` `true`; at most 64 entries and 64 covered things per entry MUST be listed, those left out counted in `unmanaged_more` and `covers_more`. A client MUST render `area`, `why` and `name` as plain text. The read MUST be answered and refused as it is without the field. |
| **ARCH-R454** | Every SDK MUST hand its caller every field an envelope carries beside `data`: each top-level property any kind's schema in the artefact declares, `host` and `job` among them. CI in each SDK MUST fail where a top-level property of any `kinds/<kind>.json` in its vendored copy is not one its envelope carries ([the envelope's own fields](web-api-artefact.md#the-envelopes-own-fields)). |
| **ARCH-R455** | A stream opened with `Last-Event-ID` MUST be sent, before anything said after it opened, every `step` and `log` event said after that id while it is among the last 256 `step`, `log` and `alert` events said, and, for each item a `start` or `pull` line is about, that item's newest line where it was said after the id, the newest line being kept for the last 256 items and no older line for any; a `start` line's item MUST be the job that said it, the lines no job said being one item, and a `pull` line's item the first word of the line within the job that said it. What is sent again, the alerts `ARCH-R281` sends among it, MUST be sent in the order it was said. Where the id is from another run, one the run has not reached or cannot be read, or where a `step`, `log`, `alert`, `start` or `pull` event said after it is no longer kept, the stream MUST be sent no `step`, `log`, `start` or `pull` event said before it opened. An event of any other kind MUST NOT be sent again (`ARCH-R51`, `ARCH-R62`). |
| **ARCH-R456** | `GET /api/copying` MUST answer the `copying` envelope, which `lemonfiber copying --json` writes too: the backup or restore running on this machine now, whichever process runs it and whoever started it, or none. A running one carries `what` (`backup` or `restore`), its `scope` (`N6-R2`), `job` where an accepting reply named it, `started`, `written` and `whole` in bytes, `part`, the area being written now, named, and `state`: `working`, `paced` with `limit` in bytes per second, or `stalled` with `wrote`, the instant it last wrote (`E3-R17`, `E3-R18`, `E3-R19`). It MUST be answered to an operator session and to a key whose scope reaches reads, and refused to a member session, to a key scoped to a member and to a client that proves no credential. To a key it MUST carry no more than a key reads elsewhere: no `job`, and for a copy of an existing setup a `scope` of `existing` alone and a `part` naming no host path. |
| **ARCH-R457** | The event stream MUST carry, to the operator and to a `read` or `act` key, a `copying` event in the envelope `GET /api/copying` answers that credential with, built from the same reading: sent when a client connects, when a backup or restore starts and ends, when its `state` or `part` changes, and every 5 seconds while it runs. It MUST NOT be sent on a member's stream or to a client that proves no credential, and MUST NOT be handed back to a client resuming. |
| **ARCH-R458** | Every read of an automation — cross-seeding, announce-driven grabbing, quality-profile sync, library cleanup, playback statistics and the metrics pipeline — MUST carry its proof as `proof`, one type in the artefact for all of them: `state`, which is `working` where the proof held against real data, `unproven` where it has not held or has not run, and `unknown` where it could not be told; `checked`, the instant it last ran, absent where it never has; `against`, what it ran against, named; and `why`, where it is not `working`, in the operator's words (`H1-R8`, `H2-R6`, `H3-R5`, `H8-R2`, `K1-R14`). |
| **ARCH-R459** | `GET /api/automations` MUST answer the `automations` envelope, which `lemonfiber automations --json` writes too: each automation this stack runs, with its `kind` (`cross-seed`, `announce`, `quality-sync`, `cleanup`, `playback-stats` or `metrics`), its `name` and its `proof` (`ARCH-R458`), and none it does not run. It MUST be answered to an operator session and to a key whose scope reaches reads, and refused to a member session and to a key scoped to a member. |
| **ARCH-R460** | `GET /api/watched` MUST answer a member session and a key scoped to a member with that member's own viewing history alone, and MUST be refused to an operator session and to a `read` or `act` key (`H8-R15`). It MUST answer that history is off, listing nothing, what was kept before included, where `LEMONFIBER_MEMBER_HISTORY` is `off`, and while it is off the core MUST keep nothing per member (`H8-R16`), and that it is hidden, listing nothing, while the member has hidden it. The action `watched-hide` MUST take `hidden`, `true` or `false`, from a member session alone, and MUST be refused to anybody else (`H8-R17`). |
| **ARCH-R464** | `POST /api/jobs/{job}/forget` MUST let a job's name go without ending the work it names: it MUST be answered as redeeming the name would be answered at that moment, and from then on `GET`, `DELETE` and `forget` on that name MUST refuse it as absent (`ARCH-R72`) while the work runs on to its end. What forgotten work ends with MUST NOT be kept, and work with no ending of its own MUST still be let go once nothing has asked about it for the lease (`N23-R12`). |
| **ARCH-R465** | A job MUST be bound to the caller whose request started it. `GET`, `DELETE` and `POST /api/jobs/{job}/forget` MUST answer that caller and the operator, by the per-run token or an operator session, and MUST answer every other caller exactly as they answer a name the run never issued (`ARCH-R72`). A member's session and a key scoped to that member MUST be two callers. |
| **ARCH-R467** | The contract artefact MUST list every route the web API serves as `routes`, each by its method and its path as the surface routes it, with the body it takes where it takes one (`ARCH-R133`) and the kinds it answers with, `DELETE` routes and the routes that are neither a read nor an action included, generated from what the surface routes by rather than written beside it. CI MUST fail where the surface serves a route the list does not name, and each SDK's CI MUST fail where the SDK calls a route at a method or a path the list does not give. |
| **ARCH-R468** | `GET /api/capabilities` MUST name `/api/keys/{name}`, `/api/device-keys/{name}` and `/api/push-endpoints/{name}`, the revocations the surface serves, each with the state its route answers this credential with (`ARCH-R79`), decided where that route decides it. |
| **ARCH-R469** | `DELETE /api/keys/{name}`, `DELETE /api/device-keys/{name}` and `DELETE /api/push-endpoints/{name}` MUST take an optional body `{ "dry_run": … }`; given `true`, each MUST remove nothing and MUST answer with the envelope the command's rehearsal renders, which says it was a rehearsal (`ARCH-R131`), and without a body or given `false` each MUST remove what it names. |

## The artefact

The shapes the surface exchanges are generated from the server's own types into one
artefact every SDK consumes. What it carries, the refusals it lists and how it reaches an
SDK are on [their own page](web-api-artefact.md).

## Related

- [web-api-artefact](web-api-artefact.md) — the generated artefact, and how it reaches an SDK
- [web-api-getting-in](web-api-getting-in.md) — how a caller is admitted
- [web-api-the-catalogue](web-api-the-catalogue.md) — what can be installed from the plugin catalogue, as the operator browses it
- [web-api-the-machine](web-api-the-machine.md) — what a stop would interrupt, how the surface is served, and what setup decided
- [web-api-settings](web-api-settings.md) — what the operator sets, and the closed list of the core's own settings
- [web-api-the-automations](web-api-the-automations.md) — the automations, the one answer each gives to whether it works, and what a member watched
- [web-api-wire](web-api-wire.md) — the particulars two clients must agree on, instants included
- [sdk-ts](../../30-repos/sdk-ts.md) — the TypeScript client implementing this contract
- [versioning.md](versioning.md) — `api_version` and the envelope it belongs to
- [design-tokens.md](design-tokens.md) — the other contract `lemonfiber-web` consumes
- [ADR-0011](../../00-overview/decisions/0011-web-surface-as-a-fifth-repo.md) — why the boundary is a contract
- [ADR-0012](../../00-overview/decisions/0012-web-assets-embedded-at-build-time.md) — how the built client reaches a machine
- [C6](../../10-functional/features/c-trust/c6-web-security.md) — the security policy this sits inside
