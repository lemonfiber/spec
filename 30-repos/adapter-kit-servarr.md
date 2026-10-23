# Repo: `adapter-kit-servarr`

**Status:** Proposed

The client the adapters in front of Sonarr, Radarr, Lidarr and Prowlarr share, written
once: a Rust library none of them publishes and each takes at an exact commit. Rust,
Hippocratic 3.0. It serves no contract, builds no image and has no binary of its own.

**Implements:** the Servarr half of
[ADR-0045](../00-overview/decisions/0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md)'s
moves, for [F14-R15](../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md);
consumes `lemonfiber-ports` and `lemonfiber-error` from [`lemonfiber`](lemonfiber.md).

---

## Why this is a separate repo

Sonarr, Radarr, Lidarr and Prowlarr speak one HTTP API: the same key header, the same
versioned prefix, the same resources for download clients, root folders, quality
profiles, the queue, history and commands. The three curators answer
`library.curate` alike, told apart by a handful of words — a path, a query parameter,
a command name. Written into each adapter, that is four copies of one client and three
of one contract's translation, and a fix to one would leave the others wrong with
nothing to say so. Held in one adapter, the other three would depend on that
adapter's internals.

## The one property to remember

**One copy, taken by commit.** Each Servarr adapter names this repository in its
`Cargo.toml` as a git dependency at an exact `rev`, the way it takes
`lemonfiber-adapter-kit` from the core. Nothing is published to a registry. The kit
and every adapter taking it name the same core commit, so the port types the kit
implements are the ones the adapter serves.

## What's in it

```
adapter-kit-servarr/
└── src/
    ├── client     the keyed, versioned Servarr client: requests, reads, the
    │              status a versioned prefix it does not serve answers with,
    │              identity and key replacement
    └── curator    library.curate as Sonarr, Radarr and Lidarr answer it: download
                   clients, root folders, quality profiles, hard links, records
                   carried between curators, the catalogue, the queue, release
                   probes and the reads a trace makes, each kind of media in the
                   Servarr words it is spoken in
```

What only one upstream answers stays in that upstream's adapter: Lidarr's music
formats in `plugin-lidarr`, Prowlarr's applications and indexers in
`plugin-prowlarr`, and each adapter's release, digest, settings and recorder in its
own repository.

## Maintenance

A change lands here with its tests, and reaches an adapter when that adapter's pin on
this repository moves. Moving an adapter's core commit moves this repository's first,
and the adapter then takes the kit commit naming the core commit it moves to. CI
reuses the shared workflows exactly as every other repository does (`Q-R56`).

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R99** | The client the Sonarr, Radarr, Lidarr and Prowlarr adapters share — the keyed, versioned Servarr client, identity and key replacement — and `library.curate` as Sonarr, Radarr and Lidarr answer it alike MUST be written here once, and MUST NOT be copied into any adapter; what only one upstream answers MUST stay in that upstream's adapter. |
| **REPO-R100** | An adapter MUST take this repository at an exact commit recorded as a git `rev` in its `Cargo.toml`, and nothing here is published to a package registry. This repository and every adapter taking it MUST name the same core commit for the core's crates, and moving an adapter's core commit MUST move this repository's first. |
| **REPO-R101** | This repository MUST serve no contract, build no image and hold no adapter's release, digest, settings, recorder or recordings; what an adapter says it is and what it was recorded against stays in that adapter. |
| **REPO-R102** | Every module under `src/` MUST be covered by tests at 100% of lines, asked over a fake HTTP transport with no service running. |

**Affected repos** (`GOV-R7`): `plugin-sonarr`, `plugin-radarr`, `plugin-lidarr`, `plugin-prowlarr`.

## Related

- [first-party plugins](first-party-plugins.md) — the four repositories that take it
- [ADR-0045](../00-overview/decisions/0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md) — every bundled part has its repository now, and its adapter later
- [website-kit](website-kit.md) — the same shape for what the sites share
