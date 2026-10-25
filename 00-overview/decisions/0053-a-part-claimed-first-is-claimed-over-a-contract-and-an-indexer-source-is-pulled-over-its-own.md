# ADR-0053: A part claimed first is claimed over a contract, and an indexer source is pulled over its own

**Status:** Accepted
**Date:** 2026-10-25
**Decided:** 2026-10-25, by the maintainer, Wessel Verheij:

- a part that belongs to whoever claims it first is claimed over a new contract,
  `owner.claim@1`, which the Usenet indexer aggregator and the listening server speak;
- a curator that reads its indexers from an aggregator is told the aggregator over a new
  contract, `indexer.pull@1`, which the curator of books speaks;
- both are facets the core asks of every service that speaks them, never chosen among
  fillers, spoken and never provided, and each is proved by its speakers' conformance
  rather than by a substitute;
- an operation an upstream cannot perform answers `unsupported`, conformance passes it,
  and the core treats it as not offered.

**Amends** [ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md): §10.
A facet the core asks of every provider is proved by its speakers' conformance, and has no
substitute.

## Context

[ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md) moves every
service module out of the core and into a plugin's adapter, and the core speaks only
contracts. Three parts were still asked something no contract carried, measured against
the core at `2924e33d` and this specification at `7ad6c1e`:

- **The Usenet indexer aggregator starts open.** NZBHydra2 serves its configuration to
  anybody until authentication is turned on. The core turns it on with an administrator it
  names and a password it mints, restarts it, and checks that an anonymous read is then
  refused. It fills `indexer.search`, and no `indexer.search` operation says any of this.
- **The listening server has no account until one is made.** Audiobookshelf answers
  whether it holds an account, and makes its first one for whoever asks first. The core
  makes it at first run. It fills `media.serve`, which has nothing of the kind.
- **The curator of books reads its indexers from an aggregator.** Bindery is told
  Prowlarr's address and key and pulls its indexers from there. The operations that say
  so sit in `indexer.search@1`'s `Aggregators` group, the indexer's contract, which
  Prowlarr answers `unsupported`.

A contract has no optional operations: an adapter answers every case of every operation
of each contract it speaks, and a refusal the contract declares counts as an answer.
Adding these operations to the contracts the three parts fill would hold every other
speaker of those contracts to them.

## Decision

1. **`owner.claim@1` says who holds a part, and claims it.** `owner()` answers `Open`,
   `Settling`, `Ours` or `Theirs`. `claim()` claims an `Open` part with the credential in
   the adapter's `upstream.json` and answers what it then is; it changes nothing that is
   `Ours` or `Theirs`. The credential is the plugin's minted secret and never crosses a
   call.
2. **The core claims every speaker.** It asks `claim` at install's first run and on every
   seed, and waits out `Settling` within its patience. A part `Open` after a claim it
   recorded is drift; a part `Theirs` is refused, naming the plugin's secret. One doctor
   check asks `owner()` of every speaker, and reset puts a claim back.
3. **`indexer.pull@1` tells a curator where to pull its indexers from.** `aggregators()`
   lists the aggregators it reads from, and `add_aggregator` adds one by name, address,
   protocol and key. The protocol is the aggregator's native API, so a curator is never
   handed an aggregator it cannot read.
4. **The core pushes where it can and pulls where it must.** Where the indexer's app sync
   serves a curator's media, the indexer is told about the curator; otherwise a curator
   speaking `indexer.pull@1` is told about the indexer whose native API matches. An
   `unsupported` answer leaves the two unpaired.
5. **A facet is asked of every speaker.** `owner.claim` and `indexer.pull` are asked by
   the core of every service that speaks them, never chosen among fillers. A facet is
   spoken and never provided, so it has no entry in the capability vocabulary, whose
   capabilities are what a filler is chosen for. Each speaker's conformance proves its
   facet, so neither has a substitute.
6. **An operation an upstream cannot perform answers `unsupported`.** Conformance passes
   it, and the core treats the operation as not offered for that filler, by the answer's
   type alone. An operation added to a contract holds every speaker to record again.

## Consequences

- **The core loses three more service modules.** The NZBHydra2, Bindery and
  Audiobookshelf clients, and the guarding, claiming and aggregator steps written for
  each, give way to one claim step and one pull rule over every speaker.
- **Three adapters are written.** NZBHydra2's speaks `owner.claim@1` and `indexer.search@1`;
  Audiobookshelf's speaks `owner.claim@1` and `media.serve@1`; Bindery's speaks
  `indexer.pull@1` and `library.curate@1`, its key minted. Each answers `unsupported`
  where its upstream has no equivalent.
- **`indexer.search@1` keeps its `Aggregators` group** until its next major, which drops
  it.
- **The media server's first run fits the same shape.** `identity.source@1`'s
  `startup_completed` and `create_admin` are a claim, and can move to `owner.claim` at
  that contract's next major.

## Alternatives considered

| Alternative | Why not |
|---|---|
| **A claim group inside each capability** | The same pattern written into `indexer.search` and `media.serve`, and every other speaker of them held to it. |
| **NZBHydra2 shipped with authentication already on** | It cannot take over a running instance that is open, it rewrites the file it would ship, and the listening server would still need a contract. |
| **The `Aggregators` group moved into `library.curate@1`** | Every curator of `library.curate` would answer it, for one curator that pulls. |
| **Optional groups in a contract** | A second axis through `speaks`, conformance, the recorder and the choice of filler, for what `unsupported` already says. |
| **The three kept in the core, reached through `native`** | The core keeps three service modules, against the core speaking only contracts. |

## Revisit when

- a fourth part needs a claim that `owner()` and `claim()` cannot say;
- adapters answer `unsupported` to most of a contract, which would make optional groups
  worth their cost.
