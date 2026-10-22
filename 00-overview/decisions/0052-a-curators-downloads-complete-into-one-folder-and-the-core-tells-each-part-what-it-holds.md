# ADR-0052: A curator's downloads complete into one folder, and the core tells each part what it holds

**Status:** Accepted
**Date:** 2026-10-22
**Decided:** 2026-10-22, by the maintainer, Wessel Verheij:

- completed downloads go to `/data/downloads/complete/<category>`, one folder per category
  that both download clients share, so one curator's downloads land in one folder;
- `download.usenet` and `download.torrent` each gain `file_under`, which hands the client
  each category and its completed folder, and `filed`, which reads that back; the seed asks
  every client this way, a bundled client through its in-process adapter and a plugin's over
  its contract, keeps a folder the operator changed by hand in the client and reports it
  drifted; the extractor is handed the folder the client holds, as `filed` reads it;
- the core is also the asker of `dashboard.show`: over the contract where the filler speaks
  it, and where the filler is the assembled Homepage, which speaks none, through an
  in-process adapter that writes Homepage's own files, as a request gate speaking no
  contract is told through the files it reads; the page's web search box takes its address
  from a setting;
- an assembled part's `[[secret]]` whose `of` names another service is a credential that
  crosses: it is read from its holder each time and never copied into the secret store, and
  only a secret the operator enters is held there, as `<service id>:<secret id>`;
- the core confirms a live-stream pass through its own pass service, the lemonfiber binary
  run as a service of the project (`lemonfiber pass`), joined to the guard alone and holding
  the pass key read-only, so the key never leaves lemonfiber's own processes; `apply a guard`
  hands the guard that service's address as where it asks about a pass;
- a network's subnet is derived from the network's name alone, so one machine runs one
  lemonfiber stack, as a deliberate limit.

**Amends**:

- [ADR-0006](0006-single-data-mount.md): the tree under `downloads/`. Each client keeps
  its own `incomplete/`, and both complete into `downloads/complete/<category>`;
- [ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md): §6. The core
  asks `dashboard.show` too;
- [ADR-0046](0046-the-stores-are-filled-once-at-the-cutover-and-a-secret-never-enters-the-journal.md):
  §2. Of an assembled part's secrets, only one the operator enters is held in the secret
  store; one whose `of` names another service is read from its holder;
- [ADR-0051](0051-a-fresh-claimant-answers-its-probe-and-the-core-asks-what-nothing-else-does.md):
  §4. The core asks `dashboard.show` as well as `quality.sync`, `archive.extract`,
  `stream.guard` and `invite.decline`.

## Context

Measured on 2026-10-22 against the core at `36f57306`, `lemonfiber-plugins` at `116356c`
and this specification at `8779e3d`:

- **A curator's downloads land in two folders.** ADR-0006's tree gives each download
  client a `complete/` of its own, `downloads/usenet/complete/<category>` and
  `downloads/torrents/complete/<category>`. `archive.extract`'s `watch` takes one download
  folder per curator (`ARCH-R306`), so a curator taking both usenet and torrents has
  completed downloads in a folder the extractor is not told about.
- **No client is told where a category completes.** The download contracts have no
  operation naming a folder, and the core sets none on either client: SABnzbd files under
  the category's own name below its own complete directory, as its starting file leaves
  `dir` empty, and qBittorrent keeps its defaults. A folder handed to the extractor can
  only be what the core assumes each client chose.
- **Nothing applies the dashboard a panel list.** Homepage speaks no contract, no
  in-process adapter applies it `dashboard.show`'s panel list, and the core writes a
  plugin's entries straight into `config/homepage/services.yaml`.
  The page's search box is fixed in its starting `widgets.yaml` as DuckDuckGo. The request
  gate, which speaks no contract either, is told its routes by the core through the two
  files it reads (`app/gating/configured.rs`), behind the same port a contract-speaking
  gate is asked over.
- **Two secret rules disagree.** `ARCH-R275` holds every `[[secret]]` an assembled part's
  plugin declares in the secret store, and `ARCH-R277` holds that a credential crossing to
  a plugin is never copied there. Unpackerr's and Recyclarr's manifests declare the
  curators' keys as `[[secret]]` with `of` naming each curator, so both rules claim them.
- **The core cannot answer on the guard's network.** `ARCH-R291` has the core confirm a
  pass at an endpoint on the guard's network alone, and the core runs on the host and joins
  no network of the project, so no address on the guard's networks is the core's.
- **Subnets cannot be shared between two projects.** `ARCH-R310` chooses each network's
  `/29` from its name, the same on every project, and the two fixed subnets are the same
  on every project too. A second project on the machine would ask the engine for subnets
  the first holds.

## Decision

1. **A curator's downloads complete into one folder.** Each download client keeps its own
   `downloads/usenet/incomplete/` or `downloads/torrents/incomplete/`, and both file a
   completed download under `downloads/complete/<category>`, so `/data/downloads/complete/tv`
   holds every completed television download whichever client fetched it. `watch` keeps one
   folder per curator (`ARCH-R306`).
2. **A download client is told its completed folders, and read back.** `download.usenet`
   and `download.torrent` each gain two operations: `file_under`, handing the client each
   category and its completed folder, and `filed`, answering every category and the
   completed folder the client holds for it. The seed asks every client this way, through
   its in-process adapter while the client is an assembled part and over its contract once a
   plugin fills the capability. A folder the operator changed by hand in the client is kept
   and reported drifted (`D1-R3`). The extractor is handed, for each curator, the folder
   `filed` reads back for the curator's category, not the one lemonfiber wrote (`ARCH-R311`).
3. **The core asks the dashboard.** The core applies the panel list to the filler of
   `dashboard.show`: over the contract where the filler speaks it, and where the filler is
   the assembled Homepage, through an in-process adapter that writes the files Homepage
   reads and reads them back, as the request gate is told through its files. The page's web
   search box sends a search to the address the core setting `LEMONFIBER_DASHBOARD_SEARCH`
   holds (`ARCH-R308`).
4. **A crossing secret stays where it is held.** An assembled part's `[[secret]]` whose `of`
   names another service is a credential that crosses (`ARCH-R277`): it is read from the
   store that holds it each time an entry naming it is written and is never copied into the
   secret store. A secret the operator enters is held as `<service id>:<secret id>`
   (`ARCH-R275`).
5. **The core confirms a pass in a service of its own.** The pass service is the lemonfiber
   binary of the running release, run as a service of the project with `lemonfiber pass`,
   on one network it shares with the `stream.guard` filler alone, and holding the pass key
   read-only. The core issues passes and the pass service confirms them, so the key is held
   by lemonfiber's processes and by nothing else. `apply a guard` hands the guard the pass
   service's address as where it asks about a pass (`ARCH-R291`, `ARCH-R303`, `ARCH-R312`).
6. **One machine runs one stack.** Every subnet is derived from the network's name alone,
   so a second project on the machine names the subnets the first holds and the engine
   refuses its networks. This is a limit lemonfiber keeps, not a fault it hides
   (`ARCH-R310`).

## Consequences

- An extractor watches one folder per curator and sees every completed download the
  curator asked for, from either client.
- A client's completed folders are a seeded value, read back and held to drift like every
  other, and a substitute client is told them over its contract on the same terms.
- A substitute dashboard is applied the same panel list as Homepage, and the core's write
  into `services.yaml` becomes the adapter's.
- The curators' keys reach Unpackerr and Recyclarr from the store that holds them, so
  replacing a curator's key regenerates both, and no stale copy sits in the secret store.
- The project holds a service that neither a plugin nor the bundle declares, the pass
  service, and a guard asks it over the network it shares with the guard alone.
- An operator who wants two stacks runs them on two machines.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Two folders per curator in `watch`** | Every extractor would watch two trees for one curator, and the two clients' choice of folder would stay a guess. |
| **The folders written into each client's starting files** | A bundled client could be given them, a substitute could not, and nothing would read back a folder the operator changed. |
| **The completed folder overwritten on every seed** | It would undo an operator's choice, which the seed keeps for every other value (`D1-R3`). |
| **The core asking only a dashboard that speaks the contract** | The core would go on writing Homepage's files outside any port, and a substitute dashboard would be told nothing. |
| **The search box fixed in the starting files** | The operator could not change it without editing a file lemonfiber writes. |
| **Every assembled secret copied into the store** | Two copies of a curator's key, and replacing it leaves the copy stale (`ARCH-R277`). |
| **The core answering passes on a port published on the host** | Any process on the machine could reach it, and the guard would need a route to the host. |
| **The pass key given to the guard** | The guard would stop being a stock filler of `stream.guard`, and a substitute guard would hold the key. |
| **Subnets derived from the project's name as well** | Two projects would still draw from one range and could meet at one slot, so the limit would become a failure that strikes at random rather than a rule stated. |

## Revisit when

- A client cannot file a category's completed downloads under a folder it is told.
- A dashboard filler reads its configuration from somewhere no adapter can write.
- An operator needs two stacks on one machine.
