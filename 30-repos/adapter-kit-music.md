# Repo: `adapter-kit-music`

**Status:** Proposed

What the adapters in front of the stack's music curators share, written once:
`music.curate` as a music curator answers it, a Rust library none of them publishes and
each takes at an exact commit. Rust, Hippocratic 3.0. It serves no contract of its own,
builds no image and has no binary.

**Implements:** `music.curate@1` ([ARCH-R395](../20-architecture/contracts/capability-contracts.md))
for the music curators' adapters, for [D4-R22](../10-functional/features/d-content/d4-request-flow.md);
consumes `lemonfiber-ports` and `lemonfiber-error` from [`lemonfiber`](lemonfiber.md), and
the Servarr client from [`adapter-kit-servarr`](adapter-kit-servarr.md).

---

## Why this is a separate repo

A member asks a music curator for an album or a whole artist over `music.curate`, and
that translation is the same for every music curator speaking one API: the lookup of a
release group or an artist by words, the request that monitors it, the profiles a
request is made with. Written into each adapter it would be one copy per curator. Held
in `adapter-kit-servarr`, it would put a contract only music curators speak beside the
client every Servarr adapter takes. Lidarr is the first curator it answers for, in
Lidarr's own v1 API.

## The one property to remember

**One copy, taken by commit, and the Servarr client by dependency.** Each music
curator's adapter names this repository in its `Cargo.toml` as a git dependency at an
exact `rev`. Where a curator speaks the Servarr API, this repository takes the client
from `adapter-kit-servarr` as a dependency, at the commit naming the same core commit,
and copies none of it.

## What's in it

```
adapter-kit-music/
└── src/
    └── curator    music.curate as a music curator answers it: lookup of an album
                   or an artist by words, a page at a time; request, monitoring an
                   album alone or an artist with every album and those that come
                   later, then searching where asked; the root folders, quality
                   and metadata profiles a request is made with
```

What only one upstream answers stays in that upstream's adapter, with its release,
digest, settings and recorder.

## Maintenance

A change lands here with its tests, and reaches an adapter when that adapter's pin on
this repository moves. Moving an adapter's core commit moves `adapter-kit-servarr`'s
first, then this repository's, and the adapter then takes the kit commits naming the core
commit it moves to. CI reuses the shared workflows exactly as every other repository
does (`Q-R56`).

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R104** | `music.curate` as the music curators answer it alike MUST be written here once and MUST NOT be copied into any adapter; what only one upstream answers MUST stay in that upstream's adapter, and the Servarr client MUST be taken from `adapter-kit-servarr` as a dependency, never copied. |
| **REPO-R105** | An adapter MUST take this repository at an exact commit recorded as a git `rev` in its `Cargo.toml`, and nothing here is published to a package registry. This repository, `adapter-kit-servarr` where it takes it, and every adapter taking it MUST name the same core commit for the core's crates. |
| **REPO-R106** | This repository MUST serve no contract of its own, build no image and hold no adapter's release, digest, settings, recorder or recordings. |
| **REPO-R107** | Every module under `src/` MUST be covered by tests at 100% of lines, asked over a fake HTTP transport with no service running. |

**Affected repos** (`GOV-R7`): `plugin-lidarr`.

## Related

- [adapter-kit-servarr](adapter-kit-servarr.md) — the Servarr client it takes
- [first-party plugins](first-party-plugins.md) — the adapters that take it
- [capability contracts](../20-architecture/contracts/capability-contracts.md) — `music.curate@1`
