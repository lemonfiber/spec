# FAQ

**Status:** Accepted

The questions people actually ask, answered canonically. These are the answers
the website renders and the answers a support conversation should reuse, so they
live here rather than in three places that drift (GOV-R34).

Two rules for editing this page. Each answer must **stand alone** — a search
result or a chat reply shows one answer with none of the surrounding context.
And each answer must be true of what has **shipped**, not of what is planned; if
a capability is on the roadmap, the answer says so.

---

## What it is

### What is lemonfiber?

A media stack you can run in slices, driven by a binary that sets itself up. It
orchestrates nineteen open-source services — Jellyfin, the \*arr applications,
indexers and download clients — as one Docker Compose stack, boots only the part
you asked for, and verifies its own work rather than reporting green and hoping.

### Is lemonfiber a media server?

No. Jellyfin is the media server; lemonfiber is the tool that installs, wires
and supervises it along with eighteen other services. If you already run a
working stack and are happy with it, lemonfiber has little to offer you. It
exists for the setup and the proof, not the playback.

### How is this different from a Compose file I copy off Reddit?

Three things a pasted file cannot do. It sets itself up, including generating
and cross-wiring the API keys between six services. It runs in named slices, so
wanting to search an indexer does not require booting a media server and a
request portal. And it checks the things that silently go wrong — that imports
actually hardlink rather than copy, and that the torrent client's public IP
really is the VPN's.

### What does "runs in slices" mean?

A **form** is a named subset of the stack. `lemonfiber up search` starts three
containers. `lemonfiber up tv` starts eight — search, downloading, Sonarr and
subtitles. `lemonfiber up full` starts eighteen. Same configuration, same data
directory, no separate installation. Partial stacks are a supported mode with
their own tests, not the full stack with pieces missing.

### What does it check that other setups do not?

Hardlink support is tested by creating a hardlink and inspecting it, not assumed
from the filesystem type. VPN isolation is tested by comparing the public IP
seen from inside the torrent container against the one seen from the host. Port
availability is tested by binding the port. Where a claim is checkable, it gets
checked — an assumption written in a README is documentation, while an assertion
in `doctor` is engineering.

## Running it

### What do I need to run it?

Docker, and a single mount point with room for your media. That mount point is
not negotiable: downloads and the media library must live under one filesystem
so imports can hardlink and move atomically. Splitting them across volumes turns
every import into a full copy, which is slow, doubles disk use, and breaks
seeding by changing the inode.

### Which platforms are supported?

macOS and Linux, and Windows through WSL2. Windows without WSL2 is not
supported, because Docker Desktop requires it and supporting Hyper-V-only setups
would multiply the platform matrix for no user benefit.

### Can I run it on Kubernetes, Podman or Nomad?

Kubernetes and Nomad, no, and that is deliberate rather than pending: they
multiply the platform matrix without making anything better at household scale.

Podman is different. It, and a container-free native profile, are v2 features
([J2](../10-functional/features/j-runtime/j2-podman.md),
[J3](../10-functional/features/j-runtime/j3-native.md)) behind an engine
abstraction whose acceptance bar is that the VPN-egress proof and the hardlink
proof pass unchanged on each engine ([ADR-0010](../00-overview/decisions/0010-engine-abstraction-for-v2.md)).
Today the tool drives Docker Compose and nothing else.

### Is it safe to expose to the internet?

Nothing binds to all interfaces by default. Administrative surfaces — the
\*arrs, the download clients and lemonfiber's own control surface — bind to
loopback. Household-facing surfaces — Jellyfin, Seerr, the book and audiobook
readers — bind to the LAN, because a television cannot reach them otherwise.
Exposing the control surface beyond loopback is refused unless authentication is
configured, rather than warned about.

### What happens if I delete the configuration directory?

You rebuild it in about two minutes. State that can be regenerated is not
precious, and that is what makes upgrading and experimenting safe rather than
frightening.

### Does it phone home?

No. There is no telemetry, no account, and no server the project operates. The
only network traffic is between your machine and the services you configured it
to talk to.

## The project

### Is lemonfiber open source?

The code is public, buildable, forkable and modifiable, under the Hippocratic
License 3.0. That licence adds ethical-use clauses, which is exactly what stops
it being OSI-approved — so "source-available" is accurate and "open source" is
not, even though every line is readable. The full reasoning, and the practical
costs of that choice, are in the
[licence rationale](license-rationale.md). Every service the stack orchestrates
is separately OSI-licensed open source.

### Why is the logo proprietary if the code is not?

For the same reason Rust, Mozilla, Python and Docker do it. Anyone may use, fork
and redistribute the code; nobody may ship their fork under this project's name
and logo, because that would let a fork impersonate the project. The design
tokens are openly licensed, because the interface embeds them and a fork needs
them. Only the marks themselves are reserved.

### Is it finished?

No. The specification is complete and the binary is in active development. The
roadmap is published, and a per-deliverable implementation status names the pull
request that made each claim true, so a claim there is checkable rather than
asserted — check them before depending on a capability.

### Can I add a service?

That is meant to be possible without writing Rust. Services, profiles and forms
are declared in a manifest rather than compiled in, so adding one is a manifest
change. The contributor who wants to add a service without touching the binary
is one of the three audiences the project is designed around.

### Who makes it?

NightWorks.io, with a community on [Discord](https://discord.nightworks.io). It
is maintained in the open: the specification, the roadmap and the implementation
status are all public, and the website is generated from them rather than
written separately.

## Requirements

| ID | Requirement |
|----|-------------|
| **Q-R65** | Each FAQ answer MUST be self-contained and MUST NOT depend on surrounding questions for its meaning, because consumers render answers individually as structured data. |

## Related

- [00-overview/vision.md](../00-overview/vision.md) — the problems these answers come from
- [00-overview/roadmap.md](../00-overview/roadmap.md) — what is shipped and what is not
- [license-rationale.md](license-rationale.md) — the long answer on licensing
- [colophon.md](colophon.md) — what it is built on
