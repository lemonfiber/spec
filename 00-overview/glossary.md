# Glossary

**Status:** Accepted

Terms used precisely throughout this spec. Where a word has a loose colloquial
meaning and a specific meaning here, the specific one wins.

---

## Project vocabulary

### Form
A **named, user-facing combination of profiles** representing an intent —
`search`, `dl`, `hunt`, `tv`, `full`. Forms are what users select; they're
defined as data in `stack.toml` and rendered by lemonfiber.

> A form is *intent*. A profile is *fact*. `tv` is a form meaning "I want to
> automate TV," which happens to require the `search`, `usenet`, `torrent`,
> `tv`, and `subs` profiles.

See [forms model](../10-functional/forms.md).

### Profile
A **Docker Compose profile** — an atomic tag on a service declaring what it *is*.
Each service in `media-stack` carries exactly one. Profiles are never selected
directly by users.

### Profile closure
The full set of profiles a form expands to, including dependencies. Computed by
lemonfiber from `stack.toml`, not hardcoded. The `tv` form's closure includes `search`
because Sonarr is useless without indexers.

### Stack manifest
`stack.toml` in the media-stack repo. The **contract** between lemonfiber and
media-stack: declares services, profiles, forms, ports, health endpoints, and a
`schema_version`. Everything lemonfiber knows about the stack comes from here.

See [manifest contract](../20-architecture/contracts/stack-manifest.md).

### Seed
The act of **wiring services to each other via their REST APIs** — registering
download clients in Sonarr, root folders, Prowlarr→*arr app sync, injecting API
keys into Homepage. Performed by `lemonfiber seed`. Idempotent and re-runnable.

### Doctor
The diagnostic subsystem (`lemonfiber doctor`). A set of independent `Check`s, each
returning Pass/Warn/Fail **plus a remedy string**. See [security](../40-quality/security.md).

### Data root
The single directory (`DATA_ROOT`) containing both `downloads/` and `media/`,
bind-mounted into every container as `/data`. The subject of [P1](vision.md#p1--the-filesystem-contract-is-inviolable).

### Storage mode
One of `local`, `external`, `nas` — describes where the data root lives and
which capabilities can be assumed. Drives whether hardlinks are available and
therefore whether the *arrs are configured to hardlink or copy.

### Jellyfin mode
`docker` or `native`. Determines whether Jellyfin runs as a container or as a
host-installed application (for hardware transcoding on macOS/Windows).
See [ADR-0007](decisions/0007-dual-mode-jellyfin.md).

---

## Ecosystem vocabulary

### *arr / Servarr
The family of .NET automation applications sharing a common codebase, UI, and
REST API shape: **Sonarr** (TV), **Radarr** (movies), **Lidarr** (music),
**Prowlarr** (indexers), **Readarr** (books — *discontinued 2025*). Their shared
API design is what makes a single `ServarrClient` in lemonfiber viable.

### Indexer
A searchable source of release metadata. Usenet indexers return **NZB** files;
torrent indexers/trackers return magnets or `.torrent` files. Managed centrally
by Prowlarr and pushed to each *arr.

### NZB
An XML file describing where the parts of a binary file live on Usenet.
Analogous to a `.torrent`, but points at a paid Usenet provider rather than peers.

### Download client
The thing that actually fetches bytes — **SABnzbd** (Usenet) or **qBittorrent**
(BitTorrent). The *arrs delegate to these and then import the results.

### Import
The step where an *arr takes a completed download and places it in the library —
renamed, organised, and hardlinked if possible. **The step P1 protects.**

### Hardlink
A second directory entry pointing at the same inode. Costs no extra disk, and
lets a torrent keep seeding from `downloads/` while the same bytes appear in
`media/`. Requires both paths on **one filesystem** — hence the single-mount rule.

### Port forwarding (VPN)
A VPN provider assigning you an inbound port so peers can initiate connections.
Materially improves torrent performance. ProtonVPN grants it via **NAT-PMP**,
dynamically — so the port changes and must be pushed into qBittorrent on each
reconnect.

### Fail-open / fail-closed
A VPN that **fails open** keeps passing traffic when the tunnel drops — leaking
your real IP. **Fail-closed** (a killswitch) blocks everything instead. Gluetun
is fail-closed by design; `lemonfiber doctor` verifies that empirically rather than
trusting it.

### TRaSH guides
Community-maintained quality-profile definitions for the *arrs. **Recyclarr**
syncs them in automatically, replacing a large amount of manual configuration.

---

## Technical vocabulary

### Bind mount vs. volume
A **bind mount** maps a host directory into a container (`${DATA_ROOT}:/data`) —
visible and backup-able from the host. A **volume** is Docker-managed storage.
This project uses bind mounts throughout so users own their files.

### `host.docker.internal`
A DNS name resolving to the host machine from inside a container. Provided
automatically by Docker **Desktop** (macOS/Windows). On native Linux Docker it
does not exist and must be added via `extra_hosts: ["host.docker.internal:host-gateway"]`.
Load-bearing for native Jellyfin mode.

### WSL2 / drvfs / 9p
Windows Subsystem for Linux v2 runs Docker's Linux VM. Accessing Windows-side
paths (`C:\...`) from inside it crosses a **drvfs/9p** translation layer that is
slow and **does not support hardlinks correctly** — so on Windows the data root
must live inside the WSL2 filesystem. See [platform matrix](../20-architecture/platform-matrix.md).

### VirtioFS
Docker Desktop for macOS's file-sharing backend, replacing the older gRPC-FUSE.
Substantially faster and more correct for SQLite locking — which every *arr
depends on. Required.

### PUID / PGID
LinuxServer.io convention for the UID/GID a container drops privileges to.
**Genuinely important on native Linux Docker** (file ownership is real);
effectively cosmetic on Docker Desktop, which maps ownership automatically.

### Immediate-mode rendering
Ratatui's model: the entire frame is rebuilt from current state every draw,
rather than mutating a retained widget tree. Suits a telemetry dashboard.
Contrast with the Elm architecture (Bubble Tea), which suits complex input flows.

### Schema version
An integer in `stack.toml` denoting the manifest format generation. lemonfiber refuses
manifests whose `schema_version` it does not implement — turning version skew
into a clear error rather than an obscure Compose failure.
See [versioning](../20-architecture/contracts/versioning.md).
