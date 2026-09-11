# Roadmap

**Status:** Accepted

Sequenced to keep a working, demonstrable artifact at every milestone. The
ordering principle: **build the thing being wrapped before the wrapper.** lemonfiber
should target a stack that is already known-good, so that debugging is never
"is it lemonfiber or is it the stack?"

---

## The version train

Releases ship as a serial train of semver versions, each scoped by a manifest in
[`70-operations/versions/`](../70-operations/versions/) — the single source of
truth for a version's goals and status; the table below renders that truth.
**Minors** are themed feature slices; **patches** (`x.y.Z`) are hotfixes; a
**major** carries the capability that justifies the number. **No version ships a
stub** — a release refuses while a feature it locks is not yet built
([OPS-R54](../70-operations/staging.md)).

| Version | Milestone | Delivers | Status |
|---------|-----------|----------|--------|
| `0.1.0` | M2 | Core: manifest, compose driver, CLI | Released |
| `0.2.0` | M3 | Setup wizard + doctor | Released |
| `0.3.0` | M4 | Backup & restore | Released |
| `0.4.0` | M4 | Auto-wiring, seed, quality, trace and the first-content walk | Released |
| `0.5.0` | M5 | How the product speaks — errors, notifications, health, dashboard data | Released |
| `0.6.0` | M5 | Trust checks: VPN, storage, queue health | Released |
| `0.7.0` | M5 | Trust checks: providers, support bundle, auto-remediation | Released |
| `0.8.0` | M6 | Live TUI: forms, lifecycle, logs and diagnostics as surfaces | Released |
| `0.9.0` | M7 | Speaking plainly — interface tiers and the plain-language layer | Released |
| `0.10.0` | M7 | The front door, its security, and the privacy stance | Released |
| `0.11.0` | M8 | The household asks — requests, identity, client apps | Released |
| `0.12.0` | M8 | Living within limits — disk, retention, bandwidth | Released |
| `0.13.0` | M9 | Changing your mind — reconfigure, migrate, uninstall, credentials | Released |
| `0.14.0` | M9 | Keeping it running — updates, backup, rollback, the journal | Staged |
| `0.15.0` | M9 | Away from the keyboard — remote control, autostart, customisation | Planned |
| `0.16.0` | M14 | Plugins — what one is, installing one, and what that leaves readable | Planned |
| `0.17.0` | M14 | Plugins — what the bundled stack can do, and where a plugin comes from | Planned |
| `0.18.0` | M11 | Ecosystem glue: cross-seed, autobrr, quality-sync, subtitles | Planned |
| `0.19.0` | M11 | Ecosystem glue: self-healing, cleanup, transcoding, statistics | Planned |
| `0.20.0` | M12 | Safely reachable — remote access and one account | Planned |
| `0.21.0` | M13 | See everything — metrics, dashboards, uptime | Planned |
| `0.22.0` | M15 | Runs without Docker — engine abstraction, Podman, native | Planned |
| `1.0.0` | M6 | The dashboard — a bare `lemonfiber` opens it. Everything specced is built, and the interfaces stop moving. | Planned |

### Patch releases (hotfixes)

A patch (`x.y.Z`) fixes an already-released version from its tag, bypassing the
goal gate — a cited fix plus maintainer authorisation
([OPS-R37](../70-operations/staging.md)). Patches appear in the
[changelog](../10-functional/features/e-maintenance/e5-changelog.md) but never
enter the goal-locked train.

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
| Branch protection | Checks required on every repo |

**Exit criteria:** a PR citing a non-existent identifier is closed with guidance;
a PR citing a valid one passes; an override is recorded and opens a tracking
issue.

**Why before M1:** the very first commit to `lemonfiber-media-stack` should cite a
requirement. If governance arrives later, the initial history is exempt by
accident, and "we'll backfill" never happens.

---

## M1 — `lemonfiber-media-stack` works standalone (with `brand` alongside)

No Rust involved. The stack must be usable with bare `docker compose`. The
`brand` repo — tokens, marks, and its contrast CI — can be finished in parallel
here, since the web UI that consumes it doesn't arrive until M7 and nothing
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

## M4 — Seed & backup

Turns config from precious into reproducible ([P6](vision.md#p6--reproducible-over-precious)).
Spans two versions: `0.3.0` (backup & restore — a configured stack captured to
an archive) and `0.4.0` (auto-wiring & seed — the graph rebuilt from nothing).

| Deliverable | Notes |
|-------------|-------|
| `ServarrClient` | Shared API client across Sonarr/Radarr/Lidarr/Prowlarr |
| API key extraction | Parse each app's `config.xml` |
| Download client registration | SABnzbd + qBittorrent into every \*arr and Bindery |
| Root folder registration | Per media type |
| Prowlarr app sync | Push indexers to each \*arr |
| Bindery indexer wiring | **Torznab endpoints** — app sync does not cover it (`D1-R15`); **deferred**, its API cannot be pinned without a live instance to verify against |
| Jellyfin → Seerr identity | One household account, not two (`D1-R7`) |
| Homepage key injection | Widgets work on first boot |
| Drift-aware writes | Never revert an operator's manual change (`C9-R3`) |
| `lemonfiber backup` / `restore` | Quiesced, not a live SQLite copy (`E3-R1`) |

**Exit criteria:** `rm -rf config && lemonfiber up tv && lemonfiber seed` restores a working
stack in under 2 minutes. Seed is idempotent — running twice changes nothing.

---

## M5 — Trust checks

The P3 trust pillar made real (`0.5.0`–`0.7.0`): the foundations everything is
expressed in terms of, then the diagnostics that prove the stack is
safe to run, beyond the setup-time checks M3 established.

| Deliverable | Notes |
|-------------|-------|
| VPN egress proof | Continuous confirmation traffic leaves through the tunnel, not just at setup |
| Storage & hardlink verification | The data root still links; degraded capability alerted |
| Queue & provider health | Stuck queues and rotted credentials surfaced as findings |
| Auto-remediation | Where a fix is safe and unambiguous, offer to apply it |

**Exit criteria:** each trust check catches its failure on a deliberately broken
stack and states a remedy.

---

## M6 — Live TUI

The second surface (`0.8.0`, closing at `1.0.0`), ratatui over the same core the
CLI drives — the read-only dashboard **and** the interactive surfaces over it.
It is what `1.0.0` delivers, and the reason that release is a major rather than
another minor.

| Deliverable | Notes |
|-------------|-------|
| Ratatui event loop | Async, non-blocking; Docker I/O never stalls a frame |
| Dashboard | Health, VPN IP + forwarded port, transfers, disk, queue depth — the read-only screen |
| Form switcher | Interactive picker with closure preview |
| Log viewer | Streamed, filterable, scrollback |
| Doctor view | Interactive re-run, remedies inline |
| Wizard in TUI | Same state machine, richer presentation |

**Exit criteria:** dashboard sustains 1 Hz refresh at <2% CPU idle; input stays
responsive while pulling images.

---

## M7 — Web surface & UX

A third surface (`0.9.0`–`0.10.0`): a web view over the same core, plus the
cross-cutting UX that spans every surface. The view is served by `lemonfiber` as a
JSON API and drawn by a static app kept in its own repo
([ADR-0011](decisions/0011-web-surface-as-a-fifth-repo.md)).

**Exit criteria:** the web surface renders the same live state the TUI shows and
can complete setup, over the core with no surface-specific logic.

Setup is completable from the web surface
([G1-R14](../10-functional/features/g-ux/g1-interface-tiers.md)), so it writes. The
C6 goals guarding a writable loopback API are staged in `0.9.0`.

---

## M8 — Household & content

Content and household features (`0.11.0`–`0.12.0`): managing what the stack holds and who
in the household reaches it.

**Exit criteria:** a household member's request flows end to end, and content
management acts without reverting an operator's manual choices.

---

## M9 — Lifecycle & maintenance

Living with a running stack (`0.13.0`–`0.15.0`): reconfiguration, migration, uninstall,
notifications, remote control, autostart & boot persistence, hosting lemonfiber's
own long-running commands, stack and self updates, rollback, and the service
catalogue.

**Exit criteria:** every lifecycle operation is reversible or explicitly
confirmed, and an unattended stack recovers across a reboot.

---

## M10 — Release engineering

Ships with `1.0.0`: the install paths a non-contributor follows, and the gate
that ships no stubs ([OPS-R54](../70-operations/staging.md)).

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

## The rest of the way to `1.0.0` (M11–M15)

These were once sequenced behind a second epoch opening at `2.0.0`. There is no
second epoch: `1.0.0` means everything specced is built and the interfaces stop
moving, so everything below is on the way to it rather than after it. They ship as
minors on the one train, authored to the same bar as everything before them.

The plugin system comes first of them, because it changes the stack manifest and
introduces the capability vocabulary — every feature after it is then built on the
shape that ships rather than retrofitted onto it, and the schema has several minors
of use behind it before `1.0.0` freezes it.

---

## M14 — The platform

`0.16.0` and `0.17.0`. Other people's stacks, and the surface that makes them
possible. F3–F7 are Accepted; recipes (F8) are Draft and carry no version yet.

| Deliverable | Notes | Version |
|-------------|-------|---------|
| Plugin manifests | F3 — declarative data describing a service, whose container lemonfiber writes rather than accepts ([ADR-0021](decisions/0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md)) | `0.16.0` |
| The capability vocabulary | F4 — what a capability is, what its probes must show, and what happens when two things claim one | `0.16.0` |
| Plugin lifecycle | F6 — rehearse, install, prove, verify the stack around it, and reverse through the journal on either failure | `0.16.0` |
| Plugin provenance | F7 — four redundant answers to why did my stack do that | `0.16.0` |
| Capabilities of the bundled services | F9 — the nineteen declare what they can do, pass the probes, and the wiring is converted to ask rather than to name | `0.17.0` |
| The plugin catalogue | F5 — reviewed, signed, and an operator's own source on the same technical terms with unreviewed said plainly | `0.17.0` |
| Mobile client handoff | G9 — a household member's phone reaches the library in one step | `0.17.0` |
| Recipes and named adapters | F8 — the ordered calls that turn a first-run flow into data, and what they may carry where ([ADR-0022](decisions/0022-a-recipe-declares-pairs-not-lists.md)) | unscheduled |

**Recipes are held back deliberately.** A manifest describes a container whose reach
lemonfiber fixes, so the worst one can do is fail to parse. A recipe runs with
lemonfiber's own authority on behalf of a manifest a stranger wrote, and it is the
riskiest mechanism in this design — it should not arrive before anybody has operated
the simplest plugin there is. It has no version because inserting one renumbers every
release behind it, which is a decision about the train rather than about plugins.

**The capability work is split across the two**, and the difference is visible to an
operator rather than internal. `0.16.0` ships the vocabulary: a plugin can claim a
capability, be refused for claiming one it cannot demonstrate, and take over one another
*plugin* was filling. `0.17.0` ships the nineteen bundled declarations and the converted
wiring, which is what makes a plugin able to stand in for a *bundled* service. The model
has to exist before nineteen services can be described in it, and describing them is the
larger half of the work.

**Exit criteria for `0.16.0`:** a plugin authored outside this project installs, proves
itself, and adds a service to a running stack with no change to lemonfiber — and removing
it puts the stack back.

**Exit criteria for `0.17.0`:** a plugin replaces a bundled service, and nothing that
consumed that service's capability had to be changed for it to work. The first-run flows
that some substitutions need wait for F8.

---

## M11 — Ecosystem glue

`0.18.0`–`0.19.0`. The integrations a mature stack grows into, each one *verified*
rather than merely wired.

| Deliverable | Notes |
|-------------|-------|
| Cross-seeding | H1 — open-source and self-hostable, no proprietary matcher |
| Announce-driven grabbing | H2 — autobrr, for what the scheduled search misses |
| Quality-profile sync | H3 — one preset, applied everywhere it means something |
| Subtitles | H4 — fetched, matched, and checked for the right film |
| Queue self-healing | H5 — the stalls C7 categorises, fixed where fixing is safe |
| Library cleanup | H6 — what to remove, proposed and confirmed |
| Transcoding | H7 — the shape of the library that plays everywhere |
| Playback statistics | H8 — what the household actually watched |

**Exit criteria:** each integration proves its effect on a live stack, not its
presence in a configuration file.

---

## M12 — Safely reachable

`0.20.0`. Reaching the stack from outside the house without opening it to the
world.

| Deliverable | Notes |
|-------------|-------|
| Remote access | I1 — a self-hosted overlay, not a port forward |
| One account | I2 — single sign-on across the services the household touches |

**Exit criteria:** a household member reaches the library from outside with no
port exposed to the internet, signing in once.

---

## M13 — See everything

`0.21.0`. The stack's own telemetry, for the operator who wants graphs rather
than a dashboard.

| Deliverable | Notes |
|-------------|-------|
| Metrics & dashboards | K1 — exported, not screen-scraped |
| Uptime monitoring | K2 — the stack notices its own absence |

**Exit criteria:** a deliberate outage appears in the metrics and raises the
notification the trust checks already know how to send.

---

## M15 — Runs anywhere

`0.22.0`. The container engine becomes one implementation behind an
abstraction rather than an assumption, which lifts the single-engine non-goal
([ADR-0010](decisions/0010-engine-abstraction-for-v2.md)).

| Deliverable | Notes |
|-------------|-------|
| Container-engine abstraction | One port, Docker behind it; nothing above it names an engine |
| Podman | A first-class alternative, not a compatibility shim |
| Native, without containers | Services run as processes; the same manifest describes both |
| Upgrade in place | An existing install moves to `0.22.0` keeping its configuration and data |

**Exit criteria:** the same stack starts, passes doctor and serves media under
Docker, under Podman, and with no container runtime present.

## Beyond `1.0.0`

Not scheduled. Recorded so they're not rediscovered as novel.

| Idea | Note |
|------|------|
| Keyring-backed secrets | OS keychain instead of plaintext `.env` |
| GUI | Tauri; only if terminal-first proves to be the barrier |

Several former post-1.0 candidates are scheduled features on the way to `1.0.0`: autobrr/cross-seed
([H1](../10-functional/features/h-glue/h1-cross-seed.md), [H2](../10-functional/features/h-glue/h2-autobrr.md)),
Janitorr/Maintainerr ([H6](../10-functional/features/h-glue/h6-library-cleanup.md)),
transcoding ([H7](../10-functional/features/h-glue/h7-transcoding.md), open-source
Unmanic), and the plugin system ([F3](../10-functional/features/f-extensibility/f3-stack-manifests.md)),
and remote access for the household ([I1](../10-functional/features/i-remote-access/i1-remote-access.md)).

## Explicitly rejected

See [vision § non-goals](vision.md#non-goals).
