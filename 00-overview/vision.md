# Vision

**Status:** Accepted

---

## The problem

Self-hosted media automation works well once it's running. Getting there is the
problem, and it's a problem with three distinct faces:

**1. Setup is an afternoon of undocumented tribal knowledge.**
The canonical path is: find a Reddit compose file, paste it, fix the paths,
discover your imports are copying instead of hardlinking, read the TRaSH guides,
redo the paths, generate API keys by hand, wire six services together through
six different settings UIs, and then never touch it again out of fear. None of
that difficulty is essential — it's the absence of a setup tool.

**2. It's all-or-nothing.**
Most stacks are a single compose file with a dozen services. Wanting to *just
search for an NZB* means booting a media server, a request portal, a subtitle
daemon, and four automation services. That's not a resource problem so much as a
conceptual one: the tooling has no vocabulary for "I only need part of this
right now."

**3. Failures are silent and occasionally consequential.**
A VPN container that fails open still shows as `Up`. Imports that degrade from
hardlink to copy still "work" — they just quietly consume double the disk and
break seeding. A stack that reports green while doing the wrong thing is worse
than one that crashes.

## The product

**A media stack you can run in slices, driven by a binary that sets itself up.**

```
$ lemonfiber
  ┌─ lemonfiber ────────────────────────────────┐
  │  No configuration found.                    │
  │  Run first-time setup?              [Y/n]   │
  └─────────────────────────────────────────────┘

$ lemonfiber up search      # Prowlarr + NZBHydra2. Nothing else.
$ lemonfiber up tv          # + Sonarr, downloaders, subtitles
$ lemonfiber doctor         # prove the VPN isn't leaking
```

Three commitments:

| Commitment | What it means concretely |
|------------|--------------------------|
| **No proprietary components** | Every bundled service is OSI-licensed and self-hosted. No Plex, no paid tiers, no phone-home. See [service inventory](../30-repos/media-stack.md#service-inventory). Our own code is [Hippocratic 3.0](../90-appendix/license-rationale.md) — source-available and ethical-source, deliberately *not* OSI-approved. |
| **Runs in slices** | Named *forms* map to sets of Compose profiles. `search` is 2 containers; `full` is 16. Same config, same data, no separate install. |
| **Correct by construction** | The setup wizard tests hardlinks rather than assuming them. `doctor` compares public IPs to prove VPN isolation. Ports bind to loopback by default. |

## Who it's for

Someone technical enough to run Docker but not interested in becoming an expert
in six web UIs — plus the friend they hand it to afterwards, and the contributor
who wants to add a service without touching Rust.

Where those needs conflict, **ease of first setup wins**. Existing tools already
serve the tinkerer well; nothing serves the newcomer. That priority is why the
wizard is a headline feature rather than a convenience, and why every
interactive action must also have a non-interactive flag equivalent — so
serving the newcomer never costs the scripter.

## Design principles

These are load-bearing. When a decision is contested, resolve it against this list in order.

### P1 — The filesystem contract is inviolable
Downloads and media live under **one** mount point so hardlinks and atomic moves
work. Any design that risks breaking this is rejected regardless of other merits.
Violating it turns every import into a full copy: slow, disk-doubling, and it
breaks seeding by changing the inode. See [ADR-0006](decisions/0006-single-data-mount.md).

### P2 — Partial stacks are first-class, not degraded
`lemonfiber up search` is a supported mode with its own docs and tests, not "the full
stack minus things." No service may hard-depend on a service outside its own
profile. See [ADR-0002](decisions/0002-profiles-and-forms.md).

### P3 — The tool proves things rather than assuming them
Where a claim is checkable, check it. Hardlink support: create one and stat it.
VPN isolation: compare public IPs from inside both containers. Port availability:
bind it. Assumptions stated in a README are documentation; assertions in
`doctor` are engineering.

### P4 — Errors carry remedies
Every user-facing failure names the fix. `Error: hardlinks unsupported` is a
dead end. `DATA_ROOT is on an exFAT volume, which cannot hardlink — imports will
copy instead. Move it to an APFS volume, or accept slower imports (Settings →
Media Management → Copy).` is a tool.

### P5 — Secure by default, not by configuration
Services bind to `127.0.0.1`, not `0.0.0.0`. Only Gluetun gets `NET_ADMIN`.
Image tags are pinned. Nothing is exposed to the LAN unless explicitly asked for.
The default posture must be the safe one, because defaults are what people run.

### P6 — Reproducible over precious
`rm -rf` the config directory and rebuild in two minutes via `lemonfiber seed`. State
that can be regenerated doesn't need to be feared. This is what makes upgrades
and experimentation safe.

## Non-goals

Named explicitly so they're rejected on purpose rather than forgotten.

| Non-goal | Why |
|----------|-----|
| Remote access / reverse tunnels | Orthogonal concern. Tailscale does it better. |
| Multi-user / multi-tenant | This is a single-household tool. Auth belongs to Jellyfin. |
| Kubernetes / Podman / Nomad | Compose is correct at this scale. Supporting more engines multiplies the platform matrix by three for no user benefit. |
| Managing content acquisition policy | lemonfiber wires the tools together. What you point them at is yours. |
| Being a general Docker manager | Lazydocker exists. lemonfiber knows about *this* stack, and that knowledge is the value. |
| Windows without WSL2 | Docker Desktop requires it. Supporting Hyper-V-only setups isn't worth the matrix. |

## What success looks like

1. A competent developer who has never used Sonarr gets to a working TV setup in
   **under 15 minutes**, without opening a service web UI to wire anything up.
2. `lemonfiber doctor` catches a leaking VPN **before** any torrent traffic flows.
3. Deleting the config directory and re-running `lemonfiber seed` restores a working
   stack in **under 2 minutes**.
4. The same binary and the same commands work on macOS, Linux, and Windows.

## Related

- [Glossary](glossary.md) — terms used precisely throughout
- [Roadmap](roadmap.md) — sequencing
- [Decisions](decisions/) — the reasoning behind each choice
