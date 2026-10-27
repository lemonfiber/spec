# ADR-0050: A contract hands its filler all it enforces, and reads back no secret

**Status:** Accepted
**Date:** 2026-10-20
**Amended:** 2026-10-21, by the maintainer, Wessel Verheij: `invite.decline`'s `held`
answers the key's SHA-256, the hash the decline service already reports, rather than a
fingerprint short enough for a second key to share. `request.gate`'s `the routes it admits`
answers each route's credential by its SHA-256 for the same reason: the core tells by it
which of the media server keys filed under the gate's name the gate holds.
**Decided:** 2026-10-20, by the maintainer, Wessel Verheij:

- `stream.guard`'s `apply a guard` carries an envelope: the media server filler's
  declaration verbatim, the one proxy address the guard trusts and where it asks the core
  about a live-stream pass; `the guard it enforces` reads all of it back;
- `media.serve`'s declaration names the paths the guard refuses without asking anything,
  and, per byte path, the query parameters that name another item, each refused or asked
  about too;
- a `request.gate` route carries its upstream's credential and the hashes of the tokens
  it admits, so applying the routes applies the tokens; `the routes it admits` answers
  each credential's fingerprint, never its value;
- the core asks `network.egress-guard`'s forwarded port every minute while the stack
  runs, at start and after a reconnect the doctor observes, and acts when the answer
  differs from the last;
- a capability whose contract says its fillers listen on nothing may declare a probe that
  is a run of the filler image's own program, and `quality.sync` is that capability;
- `archive.extract`'s `watch` takes each curator's address, key and download folder, and
  `working` answers what it is extracting now;
- `invite.decline` holds the media server key it switches an invitation off with, answers
  that key's fingerprint, and is applied the invitations it may decline;
- `dashboard.show`'s panel list is groups of entries, with page widgets and per-entry
  widgets the core names, none reading a credential.

**Amended** by [ADR-0054](0054-a-media-server-credential-crosses-the-stack-only-over-tls-the-core-pins.md): §3 and §7. The media server's gate route and `invite.decline`'s `hold` carry the SHA-256 of each certificate the media server's internal TLS port may present.

**Amends**:

- [ADR-0029](0029-a-household-service-declines-an-invitation-with-one-key.md): §5. The
  key and the invitations reach the decline service over `invite.decline`;
- [ADR-0032](0032-the-request-service-reaches-the-arrs-through-a-gate.md): §2 and §4.
  Each route's credential and token hashes reach the gate in the routes applied over
  `request.gate`;
- [ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md): §5. The
  stream guard enforces the declaration inside an envelope that also names the proxy it
  trusts and where it asks about a live-stream pass;
- [ADR-0048](0048-a-part-without-a-port-is-proved-by-running-its-own-program.md): §1. A
  capability whose contract says its fillers listen on nothing may declare a run probe.

## Context

`F14-R8` puts `proxy.front`, `dashboard.show`, `quality.sync`, `archive.extract`,
`stream.guard`, `invite.decline` and `request.gate` in the vocabulary, each with a
contract. The rows [capability-contracts](../../20-architecture/contracts/capability-contracts.md)
gives them name their operations and not what the operations carry. Measured on
2026-10-20 against `main` of each repository:

- **The door refuses what no declaration names.** `plugin-door`'s `Caddyfile` (`7d9458e`)
  answers `403` without asking Jellyfin anything to a picture found by a name rather than
  an id (under `Artists`, `Genres`, `MusicGenres`, `Persons` and `Studios`) and to the
  splash screen, which Jellyfin composes from every library. On a byte route it refuses a
  query's `itemId` and `LiveStreamId`, under which Jellyfin serves another item than the
  one in the path, and on a trickplay playlist it asks about the item `MediaSourceId`
  names as well as the one in the path. `media.serve`'s declaration (`ARCH-R206`) carries
  byte paths, a question, a token presentation, location templates and ports, so a guard
  enforcing exactly it serves all of these.
- **The guard needs two things the declaration does not hold.** `ARCH-R244` tells the
  guard the proxy address it trusts, and `ARCH-R291` has it ask the core about every
  live-stream pass. `ARCH-R207` gives it the declaration "and nothing it was not
  declared", which leaves neither a way to reach it.
- **Recyclarr answers nothing.** It publishes no port and listens on nothing; its one
  proof runs its own program (`plugin-recyclarr` `c4762c4`,
  [ADR-0048](0048-a-part-without-a-port-is-proved-by-running-its-own-program.md)). A claim
  probe is a request (`ARCH-R283`), so it cannot fill `quality.sync` through a claim, and
  [capability-vocabulary](../../20-architecture/contracts/capability-vocabulary.md) lists
  it, Unpackerr, Homepage and Caddy as declaring nothing, against `F14-R8` and ADR-0041
  §6.
- **The rows read more than one way.**
  - `request.gate`'s "apply the routes it admits" says nothing of the tokens the gate
    admits or the credentials it presents, which the core (`3a35e1cf`) writes as two
    files, `upstreams.json` and `tokens.json`.
  - `archive.extract`'s "hand a finished extraction back" reads as a call the core
    makes, where `plugin-unpackerr`'s manifest (`4bf47dd`) gives Unpackerr each
    curator's address and key so that it tells the curator itself.
  - `invite.decline`'s "hold a key for the request service" names a key the request
    service never holds, and the row has no way for the invitations to arrive.
  - `dashboard.show`'s "widgets the core names" names none, where the media stack's
    `widgets.yaml` (`0d99145`) shows the machine's resources and a web search box, and
    its `services.yaml` holds groups of entries, each with an icon, a link, a
    description and a keyless reachability check.
- **The forwarded port has no way to be reported.** The section on it has the core read
  the port "whenever the guard's filler reports a change", and the contract has no
  operation by which a filler reports anything. The media stack pushes it from Gluetun's
  up command (`0d99145`), with a script mounted into the guard and qBittorrent's username
  and password in the guard's environment, which `ARCH-R251` refuses.

## Decision

1. **The guard is applied an envelope.** `apply a guard` carries the media server
   filler's declaration verbatim, the one proxy address the guard trusts
   (`ARCH-R244`), and where it asks the core about a live-stream pass (`ARCH-R291`).
   `the guard it enforces` answers all three back. "Nothing it was not declared" means
   the declaration unaltered and nothing added to it, inside the envelope (`ARCH-R207`,
   `ARCH-R303`).
2. **The declaration names what the guard refuses.** It gains two parts:
   - refused paths, patterns the guard answers `403` to without asking anything, such as
     pictures found by a name and the splash screen;
   - per byte path, the query parameters that name another item, each refused (Jellyfin's
     `itemId` and `LiveStreamId`) or asked about too (a trickplay playlist's
     `MediaSourceId`).

   The refusals at install stay (`ARCH-R206`, `ARCH-R304`).
3. **A gate route carries its credential and its tokens.** In `apply the routes it
   admits`, each route holds its upstream's credential and the hashes of the tokens it
   admits, so applying the routes applies the tokens. `the routes it admits` answers each
   credential's fingerprint and never its value, as the journal records a secret
   ([ADR-0046](0046-the-stores-are-filled-once-at-the-cutover-and-a-secret-never-enters-the-journal.md)
   §3). The contract keeps its two operations (`ARCH-R305`).
4. **The core asks for the forwarded port.** It asks `network.egress-guard`'s filler for
   the forwarded port every minute while the stack runs, when the stack starts, and
   after a reconnect the doctor observes, and acts when the answer differs from the last.
   Nothing is mounted into the guard and no endpoint is opened for it (`ARCH-R251`).
5. **A capability with no listening filler is probed by a run.** Its vocabulary probe may
   be a run of the filler image's own program, ADR-0048's bounded run judged on `exit` and
   `stdout_starts_with`, allowed only for a capability whose contract says its fillers
   listen on nothing. `quality.sync` is that capability. Recyclarr, Unpackerr, Homepage
   and Caddy each provide the capability `F14-R8` names for them (`ARCH-R309`, with
   `ARCH-R283`, `ARCH-R109` and `ARCH-R136` binding a run probe with `run`).
6. **The extractor is told whom to hand back to.** `archive.extract`'s `watch` takes, per
   curator, named by the media type it files, its address, its key and its download
   folder, which is whom a finished extraction is handed back to. `working` answers what
   it is extracting now (`ARCH-R306`).
7. **Decline holds one key and the invitations.** `invite.decline`'s `hold` gives it the
   media server key it switches an invitation off with, `held` answers that key's
   fingerprint, and `apply the invitations it may decline` gives it each invitation's
   token hash, its account and when it lapses. The household's decline address stays the
   filler's own page (`ARCH-R307`).
8. **The dashboard shows groups and named widgets.** `dashboard.show`'s panel list is
   groups of entries, each with a name, an icon, a link, a description, an optional
   reachability check and an optional widget. Widgets are ones the core names: page
   widgets (the machine's resources, a web search box) and per-entry widgets, every one
   reading no credential (`C6-R20`, `ARCH-R308`).

## Consequences

- A substitute guard is told everything the door enforces and is held to it by the same
  read-back, so a media server's own refusals travel with its declaration rather than
  with the guard that happens to front it.
- A substitute media server declares its own refused paths and item-naming parameters,
  and a guard enforces those and no others.
- The gate's credentials and tokens, and the decline service's key and invitations,
  reach their fillers over contract operations, and nothing the core reads back from
  either holds a secret's value.
- A forwarded port that changes reaches the torrent client within a minute, and at once
  after a reconnect the doctor observes.
- Quality sync is the one capability probed by a run, and a claim binds that probe with
  `run`; every other capability's probes stay requests, and every bundled part provides a
  capability.
- A `[[claim.probe]]` and a `[[service.claim.probe]]` take `run` where their probe is a
  run probe, and the generated vocabulary says which kind each probe is.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **The declaration alone, with the proxy address and the pass endpoint in the guard's environment** | Two channels for one guard, the second not read back, and a substitute guard learns half of what it enforces from somewhere the contract does not name. |
| **Refusals as rules of the guard's own** | They are the media server's: Jellyfin's by-name pictures and `itemId` mean nothing to another server, and a substitute guard would drop them without any check noticing. |
| **A third gate operation for the tokens, read back in full** | Routes and tokens applied apart can disagree, a token admitted on a route that is gone, and a full echo puts each upstream's credential in an answer the core reads. |
| **The guard calling a core endpoint from its port-forward hook** | It opens an endpoint on the core for the guard to reach, gives the guard something to present to it, and asks every substitute guard for a hook Gluetun happens to have. |
| **Recyclarr demonstrated by a contract, or sitting out** | A contract needs a listening adapter that cannot show the program runs; sitting out leaves `quality.sync` with no filler in the bundle, against `F14-R8`, and its vocabulary entry fails generation (`ARCH-R107`). |
| **A hand-back call the core makes** | The core would have to learn when each extraction finishes and relay it, where the extractor given the curator's address and key tells it directly. |
| **The core declining through the filler** | The decline address must answer at any hour from a service the stack keeps running (`D6-R15`), and the core's surface does not run persistently (`G1-R5`). |
| **Page widgets only** | An entry could show nothing but its link and its reachability, though per-entry widgets reading no credential keep the same `C6-R20` bar. |

## Revisit when

- A media server serves bytes for an item named somewhere the declaration has no part
  for.
- A forwarded port that changes reaches a client too late at a minute's polling.
- A second capability's fillers listen on nothing.
