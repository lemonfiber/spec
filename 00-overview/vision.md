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
| **No proprietary components** | Every bundled service is OSI-licensed and self-hosted. No Plex, no paid tiers, no phone-home. See [service inventory](../30-repos/media-stack.md#the-service-inventory). Our own code is [Hippocratic 3.0](../90-appendix/license-rationale.md) — source-available and ethical-source, deliberately *not* OSI-approved. |
| **Runs in slices** | Named *forms* map to sets of Compose profiles. `search` is 3 containers; `full` is 18. Same config, same data, no separate install. |
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

The default posture must be the safe one, because defaults are what people run.

Binding is **two-tier**: administrative surfaces — the \*arrs, download clients,
and lemonfiber's own control surface — bind to `127.0.0.1`. Household-facing
surfaces — Jellyfin, Seerr, the book and audiobook readers — bind to the
LAN, because they are useless if a television cannot reach them.

Nothing binds to all interfaces. Exposing the control surface beyond loopback is
**refused** unless authentication is configured, rather than warned about. Only
Gluetun gets `NET_ADMIN`. Image tags are pinned.

See [C6](../10-functional/features/c-trust/c6-web-security.md).

### P6 — Reproducible over precious

`rm -rf` the config directory and rebuild in two minutes via `lemonfiber seed`. State
that can be regenerated doesn't need to be feared. This is what makes upgrades
and experimentation safe.

## Non-goals

Named explicitly so they're rejected on purpose rather than forgotten.

| Non-goal | Why |
|----------|-----|
| Multi-tenant operation | Several *households* sharing one stack. A single household with several members **is** in scope — see below. |
| Kubernetes / Podman / Nomad | Compose is correct at this scale. Supporting more engines multiplies the platform matrix by three for no user benefit. |
| Managing content acquisition policy | lemonfiber wires the tools together. What you point them at is yours. |
| Being a general Docker manager | Lazydocker exists. lemonfiber knows about *this* stack, and that knowledge is the value. |
| Windows without WSL2 | Docker Desktop requires it. Supporting Hyper-V-only setups isn't worth the matrix. |
| Media backup | Configuration is backed up; a terabyte library is a job for a general-purpose backup tool. |

### Deferred, not rejected

| Deferred | Status |
|----------|--------|
| **Remote access for the household** | Watching from outside the home. Every candidate mechanism either has a proprietary control plane (Tailscale) or is substantially harder to set up (Headscale) — neither fits alongside "everyone can use it with ease" *and* "everything open source" in 1.0. Household features are **LAN-only**. See [roadmap](roadmap.md#post-10-candidates). |

### Formerly non-goals

Household support was originally out of scope. It isn't: for a partner or
housemate, **the product is Seerr and Jellyfin**, and they never see
lemonfiber at all. That audience is now first-class — see
[D4](../10-functional/features/d-content/d4-request-flow.md),
[D6](../10-functional/features/d-content/d6-household-identity.md) and
[J9](../10-functional/journeys/j9-household.md).

## What success looks like

1. A competent developer who has never used Sonarr gets to a working TV setup in
   **under 15 minutes**, without opening a service web UI to wire anything up.
2. `lemonfiber doctor` catches a leaking VPN **before** any torrent traffic flows.
3. Deleting the config directory and re-running `lemonfiber seed` restores a working
   stack in **under 2 minutes**.
4. A household member is watching on their own device having received **one
   link**, with **one account**, and having never encountered lemonfiber.
4. The same binary and the same commands work on macOS, Linux, and Windows.

## Related

- [Glossary](glossary.md) — terms used precisely throughout
- [Roadmap](roadmap.md) — sequencing
- [Decisions](decisions/) — the reasoning behind each choice
