# ADR-0041: Every part is a plugin, and the core speaks contracts

**Status:** Accepted
**Date:** 2026-10-09
**Decided:** 2026-10-09, by the maintainer, Wessel Verheij:
- a plugin supplies behaviour through an adapter container that speaks a published
  capability contract;
- every bundled part becomes a first-party plugin, and the core keeps no code for any
  service;
- lemonfiber's own guards are capabilities like any other;
- the egress guard gets one templated privileged shape;
- a substitution stops what it replaces and keeps its data;
- each capability is proved by a real substitute;
- first-party adapters are written in Rust, one repository per part.

**Supersedes** [ADR-0024](0024-what-opens-and-what-never-does.md) where it holds the
adapter set closed: behaviour no longer lives in lemonfiber's process at all.
**Amends**:
- [ADR-0021](0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md): one
  privileged shape, for one capability;
- [ADR-0027](0027-a-member-plays-what-the-core-authorised.md): the guard asks what the
  media server's filler declares;
- [ADR-0028](0028-a-supported-major-is-data-proved-by-its-own-recordings.md): a
  supported release is declared and proved by the adapter that speaks it;
- [ADR-0033](0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md):
  first-party plugin images ride the release train.

## Context

lemonfiber promises that a household can run what it chooses. The plugin model built
since 0.16.0 can add a service, prove what it claims, and settle it as the filler of a
capability. It cannot make a substitute *work*. Measured on 2026-10-09:

- **A plugin cannot carry behaviour.** It may name one of nine adapters compiled into
  the core (`ApiKind`), and ADR-0024 keeps that list closed. A Plex plugin has nothing
  that speaks Plex, so it can run Plex and nothing in the stack can use it.
- **The core names the parts it ships.**
  - About forty-five sites name a bundled service by id, and the media server is read
    through the concrete Jellyfin client at a dozen of them.
  - The request service, the curators, the credential registry, the wizard's choice of
    library and the two sidecars' contracts are each fixed to one product.
  - A plugin that filled `identity.source` would be settled as its filler and ignored
    by everything that reads a media server.
- **Seven parts have no capability at all.** The proxy, the dashboard, the stream guard,
  decline, the request gate, quality sync and archive extraction offer nothing to stand
  in for. The egress guard has a capability but cannot be a plugin: ARCH-R87 refuses the
  privileges it needs.
- **Substitution runs side by side.** A plugin settled as a filler leaves the part it
  replaced running, so a household meets two media servers.

The maintainer's requirement is that every part, lemonfiber's own guards included, can
be swapped for a counterpart that functions as the part it replaced, in this version.

## Decision

1. **A capability is a contract.**
   - Each capability in the vocabulary has a published, versioned HTTP contract
     (`<capability>@<major>`), generated from the core's port types as the web API's
     documents are.
   - The operations are what the core asks of whatever fills the capability: for
     `media.serve` and `identity.source`, the household's accounts and limits, setup,
     titles, the grant, progress, the byte guard and the locations a member is given.
2. **The core speaks only contracts.**
   - The core holds one client per contract and no code for any service. `ApiKind`,
     `KeySource` and the named-adapter set leave the manifests; a service declares the
     contracts it `speaks`.
   - Every answer an adapter gives is held to the contract's schema, bounded in size and
     time, and anything else fails closed. An adapter never holds lemonfiber's
     authority.
3. **A plugin supplies behaviour through an adapter.**
   - A part is two services: the upstream image, and an adapter container of the
     plugin's own that speaks the contract and translates to the upstream.
   - The adapter is reached with a key the core mints for that plugin alone, on a
     network it shares only with the core and its upstream. The upstream's credential
     reaches it as a file under its configuration directory.
   - No contributed code runs in lemonfiber's process, so F3-R6 holds as ADR-0021 reads
     it.
4. **Every bundled part is a first-party plugin.**
   - Jellyfin, the curators, the download clients, the indexers, the request service,
     the subtitle fetcher, the proxy, the dashboard, the egress guard and the helpers
     each move to a repository of their own (`plugin-<id>`). Each has its manifest, a
     Rust adapter built on the adapter kit, recordings and conformance.
   - Installing, updating, removing and validating a first-party plugin is the path an
     outsider's takes. First-party differs only in being reviewed and being the default
     filler.
   - The media stack becomes the bundle: the forms, and which first-party plugin fills
     each capability by default, pinned by release and embedded in the binary.
5. **lemonfiber's own guards are capabilities.**
   - The stream guard (`stream.guard`), decline (`invite.decline`) and the request gate
     (`request.gate`) have contracts and first-party plugins.
   - A substitute guard is held to the same conformance as the one it replaces, the
     stream guard's recorded cases included.
   - The stream guard enforces the guard the media server's filler declares: which
     paths carry bytes, what question decides them, and how a member's token is
     presented. Every location a member is given is built from the filler's declared
     templates.
6. **Seven capabilities join the vocabulary:**
   - `proxy.front`, `dashboard.show`;
   - `quality.sync` and `archive.extract`, both asking `library.curate`;
   - `stream.guard`, `invite.decline`, `request.gate`.

   Every capability is asked by something in the bundle, so none is left with nothing
   to substitute for. A plugin may ask for capabilities; it never links by name.
7. **One privileged shape, for one capability.**
   - A filler of `network.egress-guard` may take a shape the core writes: `NET_ADMIN`
     and `/dev/net/tun`, and nothing else. It is shown and approved by the operator at
     install.
   - No other capability may take it, and no plugin may widen it.
8. **A substitution replaces.**
   - Choosing a filler stops the part it replaces and takes it out of its form. Its data
     stays, so undoing the choice brings it back as it was.
   - The rehearsal says what does not carry over, such as accounts and progress held by
     the part that left.
9. **A supported upstream release is declared by its adapter.** Each adapter states the
   upstream releases it supports, each proved by its own recordings. The core compares
   no versions.
10. **Every capability is proved by a substitute.** Beside its first-party filler, each
    capability has a substitute built to the same contract. It runs end to end against
    its pinned upstream: install, recipe, conformance, substitution, the features the
    capability serves, and undo.

## Consequences

- **The core loses every service module.**
  - `jellyfin`, `servarr`, `prowlarr`, `sabnzbd`, `qbittorrent`, `seerr`, `bazarr`,
    `bindery`, `audiobookshelf` and `nzbhydra2` move to their plugins' adapters.
  - The core keeps the ports as contracts, one client per contract, and the decisions it
    makes over them.
  - An architecture check refuses any bundled service's name in core code.
- **Every call to a service is one hop further.** Adapters sit on the stack's network
  beside their upstream, and the hop is measured against today's reads before the
  version is tagged.
- **The household's security now rests on an adapter for a non-first-party media
  server.** The stream guard asks what the filler declares, and a plugin's adapter can
  answer that question. Three things hold it:
  - schema-checked answers that fail closed;
  - the conformance suite;
  - labelling an unreviewed plugin for as long as it is installed (F5-R5).
- **The per-plugin documents follow:**
  - the plugin manifest contract gains `speaks`, adapter services, plugin asks and the
    egress shape;
  - ARCH-R84, ARCH-R87 and ARCH-R143 are rewritten;
  - `contract/adapters.json` is retired;
  - F8-R11 to F8-R13 (named adapters) are withdrawn in favour of contracts.
- **A proprietary upstream remains a plugin's choice.** The default bundle stays OSI-only
  (F2-R5). A substitute shows its licence, and the operator decides.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| Declarative profiles: a plugin declares, per operation, the request to make and how to read the answer, plus named strategies for multi-step flows. | Multi-step flows, such as signing a device in or claiming a server, need a strategy per product in the core anyway, so the core would still hold vendor code. The mapping language grows into a programming language written in TOML. |
| The core ships adapters for each substitute and a plugin names one. | Every substitute becomes core code, and the core is tied to every product it speaks, the large companies' included. |
| Native adapters stay in the core, held to the contract by a conformance suite. | First-party parts would take a path outsiders cannot. A substitute would be proved against a suite the bundled part was never run through as a plugin, and the core would keep the vendor code this decision removes. |
| lemonfiber's own guards stay filler-agnostic but not swappable. | The maintainer requires every part to be swappable. A guard swapped for one that passes the same recorded cases is held to the same bar as the guard it replaced. |
| A different egress guard only through a stack fork. | It leaves one part swappable only outside the journalled, reversible path every other part takes. |

## Revisit when

- A capability's contract needs a second major. Two majors are then supported side by
  side, and the core speaks both until the older is announced and removed.
- An adapter's hop makes a household read slower than its reader's budget.
