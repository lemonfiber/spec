# Repos: the first-party plugins

**Status:** Accepted

One page for every bundled part's repository, and for each first-party plugin the bundle
offers rather than ships. Each is a first-party plugin, written in the same manifest as
anybody's, pinned by the default bundle and embedded in the binary.

**Implements:** [ADR-0041](../00-overview/decisions/0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md)
and [the bundle's shape](../20-architecture/contracts/bundle.md#why-it-is-shaped-this-way),
for [F14-R7](../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md)
and [F14-R15](../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md).
The manifest is [plugin.toml](../20-architecture/contracts/plugin-manifest.md) and the
pin is [bundle.toml](../20-architecture/contracts/bundle.md).

---

## Which repositories

Every bundled part has a repository of its own, named `plugin-` followed by the id of
the stack service it takes the place of, which is also its plugin id. The container,
the configuration directory, the settings and the journal therefore keep their names
when a part's source moves. `30-repos/repos.toml` lists each with `plugin = "<id>"` and
says with `image` whether it builds an image.

| Repository | The part | Builds an image |
|---|---|---|
| `plugin-prowlarr` | the indexer manager, with its adapter | yes |
| `plugin-flaresolverr` | the solver that gets past an indexer's bot protection | no |
| `plugin-nzbhydra2` | the Usenet indexer search, with its adapter | yes |
| `plugin-sabnzbd` | the Usenet download client, with its adapter | yes |
| `plugin-gluetun` | the egress guard | no |
| `plugin-qbittorrent` | the torrent client, with its adapter | yes |
| `plugin-sonarr` | the television curator, with its adapter | yes |
| `plugin-radarr` | the film curator, with its adapter | yes |
| `plugin-lidarr` | the music curator, with its adapter | yes |
| `plugin-bindery` | the book curator, with its adapter | yes |
| `plugin-bazarr` | the subtitle fetcher, with its adapter | yes |
| `plugin-recyclarr` | quality sync | no |
| `plugin-unpackerr` | archive extraction | no |
| `plugin-seerr` | the request service, with its adapter | yes |
| `plugin-calibre-web-automated` | the book library | no |
| `plugin-audiobookshelf` | the audiobook server, with its adapter | yes |
| `plugin-navidrome` | the music server | no |
| `plugin-homepage` | the dashboard | no |
| `plugin-jellyfin` | the media server, with its adapter | yes |
| `plugin-door` | the guarded door | no |
| `plugin-caddy` | the proxy | yes |

Two parts keep the repositories they already have:
[`lemonfiber-decline`](lemonfiber-decline.md) and
[`lemonfiber-request-gate`](lemonfiber-request-gate.md) each declare their service in a
`plugin.toml` of their own beside the image they build (`REPO-R94`).

`plugin-ntfy` is a first-party plugin the bundle offers and does not ship, pinned as an
`[[offered]]` and installed only where the operator asks
([ARCH-R394](../20-architecture/contracts/bundle.md)). It runs the stack's own push
server, ntfy, the self-hosted channel offered first for notifications
([B9-R11](../10-functional/features/b-running/b9-notification-backends.md)), and builds
no image. Its repository is held to everything below as a part's is.

`plugin-emby` and `plugin-medusa` are offered the same way, each a second filler of what a
part fills: Emby in Jellyfin's place as the media server and identity source, and Medusa in
Sonarr's as the television curator. `plugin-plex` puts Plex in the media server's place and
is neither shipped nor offered: the operator installs it from its repository. Each builds an
adapter image, so the train tags it, and each repository is held to everything below as a
part's is.

`plugin-transmission`, `plugin-nzbget` and `plugin-byparr` are offered the same way, each a
second filler of what a part fills: Transmission in qBittorrent's place as the torrent client,
NZBGet in SABnzbd's as the Usenet download client, and Byparr in FlareSolverr's as the solver
an indexer's bot protection is passed with. Each builds an adapter image, so the train tags it,
and each repository is held to everything below as a part's is.

`plugin-dashy` is offered the same way, Dashy in Homepage's place as the dashboard. It runs
`lemonfiber-dashy`'s image as its upstream, which it pins (`OPS-R93`), and builds an adapter
image, so the train tags it, and its repository is held to everything below as a part's is.

`plugin-traefik` is offered the same way, Traefik in Caddy's place as the proxy. It runs
Traefik's own image, pinned by tag and digest, and builds an adapter image, so the train tags
it, and its repository is held to everything below as a part's is.

`plugin-configarr` is offered the same way, Configarr in Recyclarr's place as quality sync. It
runs Configarr's own image as a scheduled service, which runs to completion at the times its
schedule names, and builds an adapter image, so the train tags it, and its repository is held
to everything below as a part's is.

`plugin-uptime-kuma` puts Uptime Kuma in the outside watcher's place, filling `status.watch`
([ADR-0061](../00-overview/decisions/0061-the-outside-watcher-is-a-capability-the-core-provisions.md)),
and is neither shipped nor offered, as Plex is: the operator installs it from its repository.
It builds an adapter image, so the train tags it, and its repository is held to everything
below as a part's is.

## What each holds

| Path | What it is |
|---|---|
| `plugin.toml` | The manifest: the part's service, its claims, asks and proofs |
| `config/<id>/` | The part's starting files, written into its configuration directory ([ARCH-R271](../20-architecture/contracts/plugin-manifest.md)) |
| `recordings/<id>/` | The recordings its claims and proofs name, each taken from the pinned image |
| `conformance/` | Where the plugin speaks a contract, the cases it is held to |
| `targets.toml` | The core release, or the core commit on `main`, it is validated and proved against (`OPS-R89`) |

The catalogue's copy of a part reproduces these paths, so every materialised file
keeps its path (`ARCH-R267`). A part
with no adapter declares one service, the bundle assembles it into the stack the core
ships, and its in-process adapter is the core's; the release whose bundle installs the
part deletes that adapter (`ARCH-R266`).

The adapters in front of Sonarr, Radarr, Lidarr and Prowlarr take the client they share
from [`adapter-kit-servarr`](adapter-kit-servarr.md) at a commit, and hold only what their
own upstream alone answers (`REPO-R99`).

## What its CI runs

- **The manifest**, against the schema the core it targets publishes.
- **Its claims and proofs**, against its recordings, and every image digest resolved on
  both platforms.
- **Each image under its posture**, the image started under what its manifest declares,
  healthy and answering its probes ([ARCH-R250](../20-architecture/contracts/plugin-manifest.md)),
  and each run proof run live, wherever a change moves a service's image, digest,
  posture, environment or user (`REPO-R93`).
- **Its recordings, taken again from the commit**: the image built from the plugin's own
  `Dockerfile` wherever it has one, and `lemonfiber plugin record --check` at the
  lemonfiber `targets.toml` names held to every recording committed beside the manifest
  ([ARCH-R285](../20-architecture/contracts/plugin-manifest.md)), given that image as
  `--adapter` where a service of the plugin `fronts` one and as `--built` where no
  service speaks a contract and the plugin's own service runs the image published from
  that `Dockerfile`, or, before its first pin, exactly the image and digest its last
  `FROM` builds on; a revision recorded so ships nothing, and neither a train tag nor
  the bundle takes it (`scripts/first_pin.py`). A change to what the
  adapter answers is recorded with `lemonfiber plugin record --adapter <that image>` in the
  same pull request, and the pull request that moves the adapter's pin to the image its
  `main` published holds every recording to that pin. The plugin holds no recorder of its
  own.
- **The organisation's shared gates and hooks**, as `shared/adoption.toml` states them.
- **Its upstream pins**, moved every week by `upstream-pins` where its manifest runs an
  upstream's image (below).

A repository that builds an image also builds and publishes it from every commit on its
`main` and from each train tag (`OPS-R90`, `OPS-R91`). `manifest-pin` moves the
manifest's pin to each, with every recording taken again from the new image as an
upstream's pin is below. Its tag, `main-<commit>` or the train's version, does not name
the release of what it is built on, so where a service declares `built_on`, the tag the
`Dockerfile`'s last `FROM` names is that release: `first-party-image` reads it from the
`Dockerfile` it built and hands it to `manifest-pin`, which writes it into
`built_on.release` and into each proof of that service expecting the release it was
built on, the way an upstream's release moves below, so `caddy.version` expects
`v2.11.8` and a space once `lemonfiber-caddy` builds on `caddy:2.11.8`; and a commit that changes nothing but the pin, its recordings,
its proofs and its `targets.toml` publishes no image. The proxy's image is Caddy's,
rebuilt with the file capability removed, so it starts under `standard` ([lemonfiber-caddy](lemonfiber-caddy.md)), and
the guarded door's is a Rust service of its own (ADR-0056); each is built in a
repository of its own and pinned in its plugin's (`OPS-R93`).

## How its upstream pins move

A plugin whose manifest runs an image not under `ghcr.io/lemonfiber/` calls `spec`'s
reusable `upstream-pins` workflow on a weekly schedule (`REPO-R98`).
lemonfiber's own images move when their repository publishes one (`OPS-R90`).

| Step | What happens |
|---|---|
| Which tag | The newest the registry publishes in the pinned tag's spelling and major, so `v3.41.3` follows `v3.40.0`, a fixed build such as `4.0.21.3020-ls327` follows `4.0.20.3014-ls326`, and a major is never crossed (`E1-R10`) |
| Which digest | The tag's multi-architecture index, publishing `linux/amd64` and `linux/arm64` (`E1-R1`). The tags are read newest first, and a newer one whose index lacks either is passed over and named as a warning. A digest that moved under the same tag is a rebuild, and is taken |
| What is written | Each service running the image gets the new `digest` and `tag`, through the rewrite `manifest-pin` uses for lemonfiber's own images. Where the release the tag names moves, its dotted numbers without the tag's prefix and suffix, so `v3.8.0` names `3.8.0`, a proof asking a service that runs the image expects the new release wherever it expected the old one, written whole, in its `stdout_starts_with`, its `body_starts_with` or a string value of its `json`, so it goes on proving exactly the release pinned: `Configarr Version: v1.39.2` becomes `Configarr Version: v1.40.0` as `1.39.2` becomes `1.40.0`. Nothing else in `plugin.toml` changes: a comment, a `why`, a `json` member's name, a longer number such as `11.39.2` and another service's proof keep the old release |
| Its recordings | Taken again by `lemonfiber plugin record` at the lemonfiber `targets.toml` names, and `proofs.json` written from them (`ARCH-R285`) |
| Who writes it | The image runs and lemonfiber is built in a job holding no secret; the job holding the release App's token works the move out again from the registry and main's manifest, and commits only plain files: the manifest with exactly that move, byte for byte, `proofs.json`, and recordings the manifest names taken from that pin |
| Its pull request | One rolling branch per image, `upstream-pin/<the first service running it>`, opened or edited through `rolling-pull-request` (`OPS-R87`) |
| When it merges | Armed where no recording still names the image it replaces and no proof's expectation was left naming the old release, and merged once the required checks pass on its commit; otherwise disarmed, naming each recording and proof left behind. An expectation is left as written where it names the old release only through an escape, such as `\u0031.39.2`, or at a place whose replacement would change more than it: the release cannot be replaced there with certainty. A proof that fails at the new release fails the plugin check, which names it |

One mover holds each upstream's pin: the plugin's own call of `upstream-pins`.

Recording again is part of moving a pin, because a recording naming any digest but the
manifest's pin is refused (`ARCH-R121`, `ARCH-R217`). Moving the pin and listing the
stale recordings would leave every bump red until somebody recorded by hand, and the
bot's next rebuild of the branch would discard what they pushed. Dependabot's docker
manager edits no `plugin.toml`, records nothing and rebuilds its own branches. A recorder
in `spec`, or in the plugin template's reader, would hold a first-run recipe for every
part, written a second time beside the adapters that already perform each first run, so
the recordings are taken by `lemonfiber plugin record`
([what a recording is](../20-architecture/contracts/plugin-manifest-proof.md#what-a-recording-is)).

## Releasing

Only a repository that builds an image is a stream the train cuts: every version that
cuts the core cuts it and tags it before the core, and no pre-release tags it
(`OPS-R86`). So are `lemonfiber-decline` and `lemonfiber-request-gate`. One whose image is the
upstream's is never tagged. The bundle pins it by revision and the digest of its tree,
and the pin moves by a reviewed pull request on the catalogue
([lemonfiber-plugins](lemonfiber-plugins.md)).

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R93** | A first-party plugin's CI MUST run each image its manifest runs under the posture the manifest declares, `standard` unless it declares `confined` ([ARCH-R234](../20-architecture/contracts/plugin-manifest.md)), and MUST refuse a change under which one fails to start, to pass its health check or to answer its probes. It MUST run them where a change moves a service's image, digest, posture, environment or user, decided by a job-level `if:` on what change detection found, never by a workflow's `paths:` filter. |
| **REPO-R94** | Every bundled part MUST have a repository of its own named `plugin-<id>`, `<id>` being both its plugin id and the id of the stack service it takes the place of, listed in `30-repos/repos.toml` with `plugin = "<id>"` and `image` saying whether it builds an image; decline and the request gate MUST instead declare their service in a `plugin.toml` in `lemonfiber-decline` and `lemonfiber-request-gate`. |
| **REPO-R95** | A first-party plugin's repository MUST hold `plugin.toml` at its root, its starting files under `config/<id>/`, the recordings its claims and proofs name under `recordings/<id>/`, `conformance/` where it speaks a contract, and `targets.toml`. |
| **REPO-R96** | A first-party plugin's CI MUST validate its manifest against the schema the core it targets publishes, judge its claims and proofs against its recordings, resolve every image digest on both platforms, and run each image under the posture its manifest declares, recording each run proof again and refusing a recording the run does not reproduce. |
| **REPO-R97** | A first-party plugin's repository that builds an image MUST be a stream the train tags; one that builds none MUST NOT be tagged, and the bundle MUST pin it by revision and tree digest alone. |
| **REPO-R98** | A first-party plugin's repository whose manifest runs an image not under `ghcr.io/lemonfiber/` MUST call `spec`'s `upstream-pins` workflow on a weekly schedule, and that workflow MUST move each such image's pin to the newest tag its registry publishes in the pinned tag's spelling and major whose index publishes `linux/amd64` and `linux/arm64`, resolved to the digest of that multi-architecture index (`E1-R1`), naming each newer tag it passes over, and to a digest that moved under the same tag, and MUST NOT cross a major (`E1-R10`); each image MUST move on a rolling branch of its own with every recording taken again by `lemonfiber plugin record` at the lemonfiber its `targets.toml` names and `proofs.json` written from them, opened or edited through `rolling-pull-request` (`OPS-R85`, `OPS-R87`); the image MUST run and lemonfiber MUST be built in a job holding no secret, and the job holding the release App's token MUST run nothing that job wrote, MUST work the move out again from the manifest on `main` and the registry, and MUST commit only plain files, read through no link: that manifest with exactly that move, `proofs.json`, and recordings the manifest names taken from exactly that pin; that move MUST also replace the release the old tag names, its dotted numbers without the prefix and suffix the tag is spelled with, by the release the new tag names at every place it is written whole in the `stdout_starts_with`, the `body_starts_with` or a string value of the `json` of the expectation of a proof asking a service that runs the image, moving such a value only where every place it names that release is written in the manifest so that replacing it changes that value and nothing else, and MUST change nothing else in the manifest; the pull request MUST be armed to merge only where no recording still names the image it replaces and no such value was left naming the old release, decided by that job alone, and disarmed, naming each, where one does. |

**Affected repos** (`GOV-R7`): every `plugin-<id>` repository listed above, `lemonfiber-decline` and `lemonfiber-request-gate`.

## Related

- [ADR-0041](../00-overview/decisions/0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md) — every part is a plugin, and the core speaks contracts
- [bundle.md](../20-architecture/contracts/bundle.md) — how the bundle pins each of these
- [adapter-kit-servarr](adapter-kit-servarr.md) — the client the Servarr adapters share
- [lemonfiber-plugins](lemonfiber-plugins.md) — where the bundle lives, and the CI that holds each copy to its origin
- [releasing](../70-operations/releasing.md) — `OPS-R86`, `OPS-R90`, `OPS-R91`
- [plugin-manifest-proof](../20-architecture/contracts/plugin-manifest-proof.md#what-a-recording-is) — how `lemonfiber plugin record` takes every recording again when a pin moves
