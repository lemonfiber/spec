# ADR-0002: Profiles are facts; forms are intent

**Status:** Accepted
**Date:** 2026-07-24

## Context

The product requirement is "run the stack in different shapes" — sometimes just
an indexer search UI, sometimes a download client, sometimes everything. Compose
profiles are the obvious mechanism, but there's a modelling question underneath:
**what does a profile mean?**

The naïve approach tags each service with every profile it participates in.
Sonarr needs indexers, so Prowlarr becomes:

```yaml
prowlarr:
  profiles: [search, usenet, torrent, tv, movies, music, books, subs, full]
```

Repeat for FlareSolverr, SABnzbd, qBittorrent, Gluetun. The file becomes a
combinatorial mess, "what is this service?" is no longer answerable by reading
it, and adding a form means editing a dozen unrelated services.

There is also a hard mechanical constraint: **Compose fails when a service
`depends_on` a service whose profile is not active.** So dependency structure
and profile assignment are coupled whether we like it or not.

## Decision

Two layers, deliberately separated:

- **Profiles are atomic facts.** Each service in `compose.yml` carries **exactly
  one** profile, describing what it *is*. Sonarr is `tv`. Gluetun is `torrent`.
  Prowlarr is `search`. No service is tagged with more than one.
- **Forms are declared intent**, defined as data in `stack.toml`, each expanding
  to a set of profiles:

```toml
[[form]]
id          = "tv"
name        = "TV"
description = "Search, download and automate television"
profiles    = ["search", "usenet", "torrent", "tv", "subs"]
```

**Dependency closure lives in the form definition**, computed once, in one place.

Corollary, enforced by CI: **no `depends_on` may cross a profile boundary.** The
single exception is `qbittorrent → gluetun`, which is safe because they share
the `torrent` profile and are therefore always co-activated.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Multi-profile tagging** (service lists every profile it participates in) | Combinatorial explosion; `compose.yml` stops being readable; adding a form touches every service. |
| **One compose file per form** | Massive duplication. Changing Sonarr's image means editing six files, and they drift. |
| **Compose `include:` / fragment composition** | Better than duplication, but fragments can't express "this service participates in several forms" without the same explosion. |
| **Forms hardcoded in lemonfiber's Rust source** | Adding a form requires a lemonfiber release. Forms are stack data; they belong with the stack. Also blocks third-party stacks. |
| **Resolve dependencies dynamically at runtime** | lemonfiber would need to understand each service's semantic requirements — that Sonarr needs *an indexer* and *a downloader*. That's inference where a declaration is clearer and cheaper. |

## Consequences

### Positive

- `compose.yml` stays readable: one profile per service, and the profile *is* a
  useful description.
- Adding a form is a `stack.toml` edit — no Rust changes, no compose changes, no
  release of lemonfiber.
- lemonfiber renders its form picker from data, so it works with any conforming stack.
- The "no cross-profile `depends_on`" rule makes **any** subset of profiles
  bootable, which is precisely what makes partial stacks reliable rather than
  best-effort.

### Negative

- The mapping is indirect: reading `compose.yml` alone doesn't tell you what
  `lemonfiber up tv` starts. Mitigated by `lemonfiber forms --explain tv`, which prints the
  closure and the resulting service list (`FR-024`).
- Removing `depends_on` means services start in arbitrary order and must
  tolerate absent peers. In practice the *arrs already retry indefinitely, so
  this costs nothing real — but it must be verified per service rather than
  assumed.

### Neutral

- Forms can overlap freely; a service in an active profile starts once
  regardless of how many active forms reference it.

## Revisit if

- A service genuinely cannot tolerate an absent dependency, forcing ordering
  back into compose.
- Users want to compose forms ad-hoc (`lemonfiber up tv+music`), which would need a
  union operation over closures — additive, not a contradiction.
