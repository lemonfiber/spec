# Repos: the first-party plugins

**Status:** Accepted

One page for every bundled part's repository. Each is a first-party plugin, written in
the same manifest as anybody's, pinned by the default bundle and embedded in the binary.

**Implements:** [ADR-0045](../00-overview/decisions/0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md),
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
| `plugin-prowlarr` | the indexer manager | no |
| `plugin-flaresolverr` | the solver that gets past an indexer's bot protection | no |
| `plugin-nzbhydra2` | the Usenet indexer search | no |
| `plugin-sabnzbd` | the Usenet download client | no |
| `plugin-gluetun` | the egress guard | no |
| `plugin-qbittorrent` | the torrent client | no |
| `plugin-sonarr` | the television curator | no |
| `plugin-radarr` | the film curator | no |
| `plugin-lidarr` | the music curator | no |
| `plugin-bindery` | the book curator | no |
| `plugin-bazarr` | the subtitle fetcher | no |
| `plugin-recyclarr` | quality sync | no |
| `plugin-unpackerr` | archive extraction | no |
| `plugin-seerr` | the request service | no |
| `plugin-calibre-web-automated` | the book library | no |
| `plugin-audiobookshelf` | the audiobook server | no |
| `plugin-navidrome` | the music server | no |
| `plugin-homepage` | the dashboard | no |
| `plugin-jellyfin` | the media server, with its adapter | yes |
| `plugin-door` | the guarded door | yes |
| `plugin-caddy` | the proxy | yes |

Two parts keep the repositories they already have:
[`lemonfiber-decline`](lemonfiber-decline.md) and
[`lemonfiber-request-gate`](lemonfiber-request-gate.md) each declare their service in a
`plugin.toml` of their own beside the image they build (`REPO-R94`).

## What each holds

| Path | What it is |
|---|---|
| `plugin.toml` | The manifest: the part's service, its claims, asks and proofs |
| `config/<id>/` | The part's starting files, written into its configuration directory ([ARCH-R271](../20-architecture/contracts/plugin-manifest.md)) |
| `recordings/<id>/` | The recordings its claims and proofs name, each taken from the pinned image |
| `conformance/` | Where the plugin speaks a contract, the cases it is held to |
| `targets.toml` | The core release, or the core commit on `main`, it is validated and proved against (`OPS-R89`) |

The paths are the ones the media stack held these files at, so the catalogue's copy of
a part reproduces them and every materialised file keeps its path (`ARCH-R267`). A part
with no adapter declares one service, the bundle assembles it into the stack the core
ships, and its in-process adapter is the core's; the release whose bundle installs the
part deletes that adapter (`ARCH-R266`).

## What its CI runs

- **The manifest**, against the schema the core it targets publishes.
- **Its claims and proofs**, against its recordings, and every image digest resolved on
  both platforms.
- **Each image under its posture**, the image started under what its manifest declares,
  healthy and answering its probes ([ARCH-R250](../20-architecture/contracts/plugin-manifest.md)),
  and each run proof run live: recorded again with `lemonfiber plugin record` and held
  to the recording committed beside the manifest ([ARCH-R285](../20-architecture/contracts/plugin-manifest.md)).
- **The organisation's shared gates and hooks**, as `shared/adoption.toml` states them.

A repository that builds an image also builds and publishes it from every commit on its
`main` and from each train tag (`OPS-R90`, `OPS-R91`). The guarded door's and the
proxy's images are Caddy's, rebuilt with the file capability removed, so they start
under `standard` (ADR-0045).

## Releasing

Only a repository that builds an image is a stream the train cuts: every version that
cuts the core cuts it and tags it before the core (`OPS-R86`). One whose image is the
upstream's is never tagged. The bundle pins it by revision and the digest of its tree,
and the pin moves by a reviewed pull request on the catalogue
([lemonfiber-plugins](lemonfiber-plugins.md)).

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R94** | Every bundled part MUST have a repository of its own named `plugin-<id>`, `<id>` being both its plugin id and the id of the stack service it takes the place of, listed in `30-repos/repos.toml` with `plugin = "<id>"` and `image` saying whether it builds an image; decline and the request gate MUST instead declare their service in a `plugin.toml` in `lemonfiber-decline` and `lemonfiber-request-gate`. |
| **REPO-R95** | A first-party plugin's repository MUST hold `plugin.toml` at its root, its starting files under `config/<id>/`, the recordings its claims and proofs name under `recordings/<id>/`, `conformance/` where it speaks a contract, and `targets.toml`. |
| **REPO-R96** | A first-party plugin's CI MUST validate its manifest against the schema the core it targets publishes, judge its claims and proofs against its recordings, resolve every image digest on both platforms, and run each image under the posture its manifest declares, recording each run proof again and refusing a recording the run does not reproduce. |
| **REPO-R97** | A first-party plugin's repository that builds an image MUST be a stream the train tags; one that builds none MUST NOT be tagged, and the bundle MUST pin it by revision and tree digest alone. |

**Affected repos** (`GOV-R7`): every `plugin-<id>` repository listed above, `lemonfiber-decline` and `lemonfiber-request-gate`.

## Related

- [ADR-0045](../00-overview/decisions/0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md) — every bundled part has its repository now, and its adapter later
- [bundle.md](../20-architecture/contracts/bundle.md) — how the bundle pins each of these
- [lemonfiber-plugins](lemonfiber-plugins.md) — where the bundle lives, and the CI that holds each copy to its origin
- [releasing](../70-operations/releasing.md) — `OPS-R86`, `OPS-R90`, `OPS-R91`
