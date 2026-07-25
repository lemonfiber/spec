# Roadmap

**Status:** Accepted

Sequenced to keep a working, demonstrable artifact at every milestone. The
ordering principle: **build the thing being wrapped before the wrapper.** lemonfiber
should target a stack that is already known-good, so that debugging is never
"is it lemonfiber or is it the stack?"

---

## M0 — Specification ✅

This repo. Decisions recorded, contracts defined, standards set.

**Exit criteria:** all sections Accepted; `stack.toml` schema defined precisely
enough to implement against.

---

## M0.5 — Governance in force

Before any implementation repo exists, the rules that bind it must. Standing this
up after code has already landed means retrofitting citations onto history, which
nobody does.

| Deliverable | Notes |
|-------------|-------|
| `50-governance` accepted | Done — the rules themselves |
| `spec-check` workflow | Citation extraction, merge-base resolution, ordering check |
| Repo templates | Issue templates, PR template with the `Spec:` trailer, `SECURITY.md` |
| `OVERRIDES.md` | Append-only override record, initially empty |
| Spec-side CI | Duplicate-ID, withdrawn-ID reuse, link resolution, affected-repo declaration |
| Branch protection | Checks required on all four repos |

**Exit criteria:** a PR citing a non-existent identifier is closed with guidance;
a PR citing a valid one passes; an override is recorded and opens a tracking
issue.

**Why before M1:** the very first commit to `media-stack` should cite a
requirement. If governance arrives later, the initial history is exempt by
accident, and "we'll backfill" never happens.

---

## M1 — `media-stack` works standalone (with `brand` alongside)

No Rust involved. The stack must be usable with bare `docker compose`. The
`brand` repo — tokens, marks, and its contrast CI — can be finished in parallel
here, since the web UI that consumes it doesn't arrive until M5 and nothing
gates on it earlier.

| Deliverable | Notes |
|-------------|-------|
| `compose.yml` + `compose/` | All 19 services, one fragment per profile, one atomic profile each, pinned image tags |
| `stack.toml` | Manifest: services, profiles, forms, ports, health endpoints |
| `.env.example` | Every variable documented inline |
| Storage overlay | `stacks/compose.storage.nas.yml` |
| Service configs | `recyclarr/`, `homepage/`, `caddy/` |
| CI | Per-form `docker compose config`; manifest ↔ compose parity; mount, binding, killswitch and tag lints, each with a negative test |
| `README.md` | Standalone usage without lemonfiber |

**Exit criteria:** every form starts cleanly via raw `docker compose --profile …`;
hardlink import verified end-to-end; VPN killswitch verified by hand.

**Why first:** proves the profile model empirically. If partial stacks don't
actually boot, that invalidates [ADR-0002](decisions/0002-profiles-and-forms.md)
and everything downstream.

---

## M2 — `lemonfiber` core: manifest, compose driver, CLI

Headless. No TUI yet — every capability reachable as a plain subcommand, which
keeps it scriptable and testable.

| Deliverable | Notes |
|-------------|-------|
| Workspace + `cargo-dist` scaffold | Three-platform CI matrix from day one |
| `stack.toml` parser + validation | Compile-time `schema_version` check in `build.rs` |
| Embedded assets | Submodule + `include_dir!` + `--stack-dir` override |
| Platform detection | macOS / Linux-native / Linux-Desktop / Windows-WSL2 |
| Compose command builder | Pure function, golden-file tested |
| Form closure + **composition** | Union of closures, intersected with configured protocols (`B1-R4`, `B1-R5`) |
| `lemonfiber up/down/restart/ps/logs/pull` | Non-interactive |
| `.env` read/write | Comment- and order-preserving |

**Exit criteria:** `lemonfiber up tv` matches hand-written `docker compose` exactly;
golden tests cover every form on every platform.

> **Form composition is in 1.0**, not deferred. `lemonfiber up full proxy` is a
> set union over profiles — trivial to implement — and it is what makes `proxy`
> viable as a form rather than a special-cased flag.

---

## M3 — Setup wizard + doctor

The milestone that delivers the actual product thesis.

| Deliverable | Notes |
|-------------|-------|
| Wizard state machine | Explicit steps, back-navigation, resumable |
| Preflight checks | Docker present, Compose ≥ minimum, daemon reachable |
| **Empirical hardlink test** | Create, `stat`, compare inode/link count |
| Storage-mode detection | Filesystem type, network mount, exFAT, WSL2 boundary |
| ProtonVPN guidance | Explicitly covers the NAT-PMP-at-key-generation gotcha |
| Jellyfin mode selection | Platform-aware; only offers native where it helps |
| `lemonfiber doctor` | Check trait; every failure carries a remedy |
| **VPN leak test** | `exec` into gluetun + qbittorrent, compare public IPs |

**Exit criteria:** a fresh machine reaches a running `tv` form in under 15
minutes with no service web UI opened. Leak test provably catches a
misconfigured VPN.

---

## M4 — Seed

Turns config from precious into reproducible ([P6](vision.md#p6--reproducible-over-precious)).

| Deliverable | Notes |
|-------------|-------|
| `ServarrClient` | Shared API client across Sonarr/Radarr/Lidarr/Prowlarr |
| API key extraction | Parse each app's `config.xml` |
| Download client registration | SABnzbd + qBittorrent into every \*arr and Bindery |
| Root folder registration | Per media type |
| Prowlarr app sync | Push indexers to each \*arr |
| Bindery indexer wiring | **Torznab endpoints** — app sync does not cover it (`D1-R15`) |
| Jellyfin → Seerr identity | One household account, not two (`D1-R7`) |
| Homepage key injection | Widgets work on first boot |
| Drift-aware writes | Never revert an operator's manual change (`C9-R3`) |
| `lemonfiber backup` / `restore` | Quiesced, not a live SQLite copy (`E3-R1`) |

**Exit criteria:** `rm -rf config && lemonfiber up tv && lemonfiber seed` restores a working
stack in under 2 minutes. Seed is idempotent — running twice changes nothing.

---

## M5 — TUI

| Deliverable | Notes |
|-------------|-------|
| Ratatui event loop | Async, non-blocking; Docker I/O never stalls a frame |
| Dashboard | Health, VPN IP + forwarded port, transfers, disk, queue depth |
| Form switcher | Interactive picker with closure preview |
| Log viewer | Streamed, filterable, scrollback |
| Doctor view | Interactive re-run, remedies inline |
| Wizard in TUI | Same state machine, richer presentation |

**Exit criteria:** dashboard sustains 1 Hz refresh at <2% CPU idle; input stays
responsive while pulling images.

---

## M6 — Release engineering

| Deliverable | Notes |
|-------------|-------|
| `cargo-dist` release workflow | mac (arm64/x86_64), Linux (gnu/musl), Windows |
| `homebrew-tap` | Auto-published by CI |
| Shell + PowerShell installers | `curl \| sh`, `irm \| iex` |
| Real Windows + Linux testing | Not just "it compiles" |
| Docs site | Generated from this spec |

**Exit criteria:** a non-contributor installs and runs on all three platforms
following only the README.

---

## Post-1.0 candidates

Not scheduled. Recorded so they're not rediscovered as novel.

| Idea | Note |
|------|------|
| Autobrr / cross-seed | Substantial sub-project each |
| Janitorr / Maintainerr | Library pruning; needs a library worth pruning first |
| Tdarr | Transcode automation; weak fit without HW accel on two platforms |
| Third-party stack manifests | Would generalise lemonfiber beyond media |
| **Remote access for the household** | Watching from outside the home. Deferred because every candidate mechanism either has a proprietary control plane (Tailscale) or is substantially harder to set up (Headscale). Household features are LAN-only in 1.0. |
| Keyring-backed secrets | OS keychain instead of plaintext `.env` |
| GUI | Tauri; only if terminal-first proves to be the barrier |

## Explicitly rejected

See [vision § non-goals](vision.md#non-goals).
