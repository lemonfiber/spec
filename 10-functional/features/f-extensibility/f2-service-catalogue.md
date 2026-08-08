---
id: F2
title: Service catalogue
kind: feature
area: F
audience: operator
status: accepted
tracks: v1
labels: [extensibility]
relates: [B1, F1, G2]
---

# F2 — Service catalogue

**Status:** Accepted · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Say what each service is for, in terms of what it does *for the operator* rather
than what it is.

A stack of nineteen services is opaque. "Prowlarr" and "Bazarr" convey nothing;
the operator sees a list of names, cannot tell which matter, and cannot judge
whether a failure is serious. When something breaks they don't know whether
they've lost subtitles or lost everything.

The catalogue is also the criteria by which anything new is judged. Nineteen
services is already a lot, and every addition costs memory, attack surface,
update burden, and cognitive load.

## Behaviour

### Every service is described by its job

| Service | What it does for you | Without it |
|---------|---------------------|------------|
| **Prowlarr** | Holds your indexer accounts in one place and shares them with everything else | Every app needs indexers configured separately |
| **FlareSolverr** | Gets past bot-protection on some indexers | Those indexers return nothing |
| **NZBHydra2** | A search box across all your Usenet indexers at once | Search one indexer at a time |
| **SABnzbd** | Downloads from Usenet | No Usenet downloads |
| **qBittorrent** | Downloads torrents | No torrent downloads |
| **Gluetun** | Routes torrent traffic through your VPN and blocks it if the VPN drops | **Your home IP is visible to every peer** |
| **Sonarr** | Watches for new episodes and fetches them | Find and download episodes yourself |
| **Radarr** | Same, for films | Find and download films yourself |
| **Lidarr** | Same, for music | — |
| **Bindery** | Same, for books and audiobooks | — |
| **Bazarr** | Finds and downloads subtitles | No automatic subtitles |
| **Jellyfin** | Plays your library on TVs, phones and browsers | Files on disk, no way to watch them |
| **Seerr** | Where the household asks for things | Requests come to you in person |
| **Calibre-Web-Automated** | Reading and organising your ebook library | — |
| **Audiobookshelf** | Listening to audiobooks, with progress synced | — |
| **Recyclarr** | Keeps quality settings in line with community guidance | Tune quality profiles by hand |
| **Unpackerr** | Extracts archived releases so they can be imported | Some downloads never import |
| **Homepage** | One page linking everything, with live status | Remember a dozen URLs and ports |
| **Caddy** *(optional)* | Friendly hostnames instead of ports | Use `localhost:8989` and friends |

The "without it" column is what makes this useful: it converts an inventory into
a judgement about severity.

### Criticality is stated

| Level | Meaning | Services |
|-------|---------|----------|
| **Critical** | Failure has consequences beyond the stack | Gluetun |
| **Core** | Stack cannot do its job | Prowlarr, download clients, the \*arr for the media type in use |
| **Important** | Significant capability lost | Jellyfin, Seerr |
| **Enhancing** | Quality of life | Bazarr, Recyclarr, Unpackerr, Homepage, FlareSolverr, NZBHydra2 |
| **Optional** | Off unless asked for | Caddy |

Gluetun is alone at critical, and for the reason stated throughout: it is the
only service whose failure can affect the operator outside their own machine.

### Provenance is visible

Each service's licence, upstream project, and pinned version — so the operator
can verify the open-source claim rather than take it on faith.

**Every bundled service is OSI-licensed**: GPL-3.0 (Prowlarr, Sonarr, Radarr,
Lidarr, Bazarr, Calibre-Web-Automated, Homepage), GPL-2.0 (Jellyfin, SABnzbd,
qBittorrent), MIT (Seerr, Gluetun, FlareSolverr, Recyclarr, Unpackerr,
Bindery, Audiobookshelf), Apache-2.0 (NZBHydra2, Caddy).

### Inclusion criteria are explicit

A service enters the stack only if it is open source under an OSI-approved
licence, publishes native `linux/arm64` and `linux/amd64` images, is actively
maintained, does something no included service already does, and works without a
paid tier.

Stating the criteria makes "why isn't X included?" answerable, and makes
additions a judgement against a standard rather than a matter of taste.

### Maintenance signals are tracked, not discovered late

Each service records the date of its last upstream release in the manifest's
`last_release` field, reviewed whenever a pin is bumped. A service going quiet is
not itself a problem — a mature application may simply not need frequent releases
— but it is a signal worth holding, because the alternative is discovering an
abandoned dependency only when it breaks.

The recorded date is the latest release **upstream** has published, not the date
the pinned version shipped. Those diverge precisely when the signal matters: a
project that released six times since your pin is alive, and one that has
released nothing since is the case worth noticing. A date ahead of upstream's
actual latest release is not a stale record but a wrong one, and fails
validation.

The table below carries only services whose signal needs a judgement recorded
against it; the dates themselves are manifest data, so they version with the
stack rather than with this document.

| Service | Signal |
|---------|--------|
| **Lidarr** | Slowest-moving in the stack; roughly eight months between releases as of mid-2026. Not archived, still functional, and **no viable successor exists** — see exclusions. Retained, watched. |

### Notable exclusions are recorded

| Not included | Why |
|--------------|-----|
| Plex | Not open source |
| Readarr | Discontinued upstream in 2025; Bindery replaces it |
| **Melodarr** | Presents itself as an actively maintained Lidarr successor. It is a fork with **two days of commits, no releases, no published image, and no activity since April 2026**. Investigated and rejected — a dead fork is worse than a slow-moving working project. |
| Beets, Headphones | Beets is a tagger and organiser, not acquisition automation; Headphones is effectively dead. Neither replaces Lidarr. |
| Autobrr, cross-seed | Substantial sub-projects; deferred |
| Tdarr | Transcode automation; weak fit without hardware acceleration on two of three platforms |
| Authelia, Authentik | Admin surfaces are loopback-only, so SSO solves a problem the stack doesn't have |
| Watchtower | Automatic updates of state-migrating services is the failure mode [E1](../e-maintenance/e1-stack-updates.md) exists to prevent |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Operator asks what a failing service does | Description available inline at the point of failure, not only in documentation. |
| Service description drifts from reality | The catalogue lives with the stack manifest so they version together. |
| Operator adds an unknown service | Show it with an unknown description rather than hiding it. |
| Upstream project is abandoned | Record it; treat replacement as a spec change with an ADR. |
| Licence changes upstream | Detect at pin-bump time; a non-OSI licence disqualifies the service. |
| Service dropped from the stack | Record why and what replaced it. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F2-R1** | Every service MUST carry a plain-language description of what it does for the operator. |
| **F2-R2** | Every service MUST state the consequence of its absence. |
| **F2-R3** | Every service MUST carry a criticality level. |
| **F2-R4** | Every service MUST record its licence, upstream project, and pinned version. |
| **F2-R5** | Every bundled service MUST be under an OSI-approved licence. |
| **F2-R6** | Every bundled service MUST publish native `linux/arm64` and `linux/amd64` images. |
| **F2-R7** | Inclusion criteria MUST be stated explicitly. |
| **F2-R8** | Notable exclusions MUST be recorded with reasons. |
| **F2-R9** | Service descriptions MUST be available inline where a service is referenced, not only in documentation. |
| **F2-R10** | The catalogue MUST be versioned with the stack manifest. |
| **F2-R11** | An unknown service MUST be displayed with an unknown description rather than hidden. |
| **F2-R12** | An upstream licence change away from OSI approval MUST disqualify the service at pin-bump time. |
| **F2-R13** | Removal of a service MUST record the reason and any replacement. |
| **F2-R14** | Each service MUST record its last upstream release date, reviewed whenever its pin is bumped. |
| **F2-R15** | A candidate service's maintenance status MUST be established from its commit and release history, never from its own self-description. |

## Related

- [B1 Forms](../b-running/b1-forms.md) — how services group into profiles
- [F1 Customisation](f1-customisation.md) — adding services
- [G2 Plain-language layer](../g-ux/g2-plain-language.md) — how descriptions are written
- [90-appendix licence rationale](../../../90-appendix/license-rationale.md)
