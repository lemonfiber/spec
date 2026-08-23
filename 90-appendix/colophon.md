# Colophon

**Status:** Accepted

What lemonfiber is built on. Almost none of the value here is ours — the project
is a setup tool and an orchestrator wrapped around other people's excellent
work, and this page says so by name.

This is the canonical list. Consumers that show credits — the website's
`/colophon` page — render it from here rather than keeping their own copy, so
the credits cannot drift from what is actually used (GOV-R34).

---

## The orchestrated services

The nineteen services `lemonfiber-media-stack` composes. Every one is
OSI-licensed and runs
on the user's own hardware; the licence breakdown is in
[license-rationale.md](license-rationale.md#note-on-bundled-services), and the
pinned images are in [`stack.toml`](../30-repos/lemonfiber-media-stack.md#the-service-inventory).

| Project | What it does |
|---------|--------------|
| Prowlarr | Indexer manager. One place to configure trackers and Usenet indexers, which then syncs them into every \*arr. |
| FlareSolverr | Proxy that solves the browser challenges some indexers put in front of their search endpoints. |
| NZBHydra2 | Meta-indexer that fans one Usenet search out across many indexers and merges the results. |
| SABnzbd | Usenet downloader. Handles the par2 repair and unpacking that makes Usenet usable. |
| Gluetun | VPN gateway container. Everything torrent-related routes through it, and it is the only container granted `NET_ADMIN`. |
| qBittorrent | Torrent client. Runs inside Gluetun's network namespace so it has no route to the internet if the tunnel drops. |
| Sonarr | Television automation — searches, grabs, renames and files episodes. |
| Radarr | The same, for films. |
| Lidarr | The same, for music. |
| Bindery | The same, for ebooks. |
| Bazarr | Finds and syncs subtitles for whatever Sonarr and Radarr have filed. |
| Jellyfin | The media server. The household-facing surface everyone else in the house actually uses. |
| Seerr | Request portal. Lets the household ask for something without touching an \*arr. |
| Calibre-Web-Automated | Ebook library and reader. |
| Audiobookshelf | Audiobook and podcast server. |
| Recyclarr | Syncs TRaSH-guide quality profiles into the \*arrs, so quality settings are maintained upstream rather than by hand. |
| Unpackerr | Extracts archives the download clients leave behind, so imports do not stall on them. |
| Homepage | The dashboard that gives the stack a single front door. |
| Caddy | Reverse proxy with automatic certificates, for the optional `proxy` form. |

## The binary

`lemonfiber` is Rust. The dependency set is deliberately small — this is a tool
that shells out to Docker, not a framework.

| Project | What it does |
|---------|--------------|
| tokio | Async runtime. The stack is I/O bound on Docker and the network, which is what it is for. |
| bollard | Docker Engine API client. Talks to the daemon directly rather than shelling out to the CLI. |
| clap | Command-line parsing, with the derive feature so the CLI surface is declared alongside the types. |
| serde | Serialisation. Everything read from disk or the Docker API lands in a typed struct. |
| toml | Parses `stack.toml`, the manifest that defines the services, profiles and forms. |
| color-eyre | Error reporting. Chosen because P4 requires every user-facing failure to carry a remedy, and it makes the context chain legible. |
| thiserror | Typed errors in the library crates, where a caller has to match on the variant. |
| etcetera | Resolves the per-platform config and data directories, so paths are correct rather than guessed. |
| sysinfo | Disk inspection for the preflight checks. |
| include\_dir | Embeds the bundled manifest and templates in the binary, so a single file is the whole install. |
| async-trait | Async methods in the traits the Docker layer is abstracted behind. |
| tokio-stream | Streaming container logs and events without buffering them whole. |

## The specification and the site

| Project | What it does |
|---------|--------------|
| mdBook | Renders this specification into the published docs site. |
| Astro | Static site generator behind lemonfiber.app. Ships no JavaScript unless a page asks for it. |
| Bricolage Grotesque | The display and body typeface, served from the site's own origin rather than a font CDN. |
| JetBrains Mono | The monospace face, for terminal output and identifiers. |

## The toolchain

The tools every repository in the organisation runs. The full rationale, and the
requirement that each be free for public repositories, is in
[40-quality/tooling.md](../40-quality/tooling.md).

| Project | What it does |
|---------|--------------|
| Docker | The engine the whole stack runs on. lemonfiber orchestrates Compose; it does not reimplement it. |
| just | Task runner. The same commands work locally and in CI. |
| lefthook | Git hooks that mirror CI, so a failure is found before it is pushed. |
| typos | Spell check across every repository. |
| lychee | Link check. Nothing in this spec may point at a page that does not exist. |
| CodeQL | Static analysis for security defects. |
| OpenSSF Scorecard | Public supply-chain posture score on each default branch. |
| OSV-Scanner | Dependency vulnerability scanning against the OSV database. |
| gitleaks | Secret scanning. |
| SonarQube Cloud | Code quality and coverage, fed by `cargo-llvm-cov`. |
| Renovate | Dependency updates, emitting the trailer that lets its pull requests pass `spec-check`. |
| git-cliff | Generates release notes from the commit log, so the changelog cannot disagree with what shipped. |
| cargo-dist | Builds and publishes the signed multi-platform release artefacts and the Homebrew formula. |

## Requirements

| ID | Requirement |
|----|-------------|
| **GOV-R34** | Public-facing reference content that restates project facts — the colophon and the FAQ — MUST be authored in `90-appendix/` and rendered by consumers at build time. A consumer MUST NOT maintain a parallel copy. |
| **GOV-R35** | When such content is unreachable at build time, a consumer MUST link to the source here rather than render a cached copy, so a reader is never shown credits or answers that have silently gone stale. |

## Related

- [license-rationale.md](license-rationale.md) — the licence of each of these, and of ours
- [40-quality/tooling.md](../40-quality/tooling.md) — why each tool is in the pipeline
- [30-repos/lemonfiber-media-stack.md](../30-repos/lemonfiber-media-stack.md) — the service inventory and pinned tags
- [00-overview/vision.md](../00-overview/vision.md) — the commitment that every bundled service is open
