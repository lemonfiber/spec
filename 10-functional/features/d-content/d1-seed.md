---
id: D1
title: Service auto-wiring
kind: feature
area: D
audience: operator
status: accepted
tracks: v1
labels: [seed, wiring]
relates: [A7, C9, D2, E3]
---

# D1 — Service auto-wiring

**Status:** Accepted · **Audience:** Operator · **Area:** D — Content & household

---

## Purpose

Connect the services to each other, so the operator never copies an API key
between two web interfaces.

A working stack requires roughly thirty connections: each \*arr needs both
download clients registered, each needs root folders, Prowlarr must push indexers
to every \*arr, Bazarr needs Sonarr and Radarr, Seerr needs Jellyfin plus
Sonarr and Radarr, Homepage needs an API key from all of them. Every one is
configured by hand, in a different UI, by copying a value from somewhere else.

That's the half-hour of clicking that defines the current experience — and it
must be redone from scratch after any configuration loss, which is why people are
afraid to touch a working stack.

## Behaviour

### Keys are read, not asked for

Each service generates its own API key on first start and writes it to its
configuration. lemonfiber reads them directly. The operator never sees or handles
them — the copying *is* the problem being solved.

**qBittorrent is the exception, and it runs the other way.** It mints a
*temporary* WebUI password on every start and asks for it to be replaced, so
there is nothing durable to read. lemonfiber therefore generates the password,
sets it, and records it where the VPN's forwarded-port push can authenticate with
it (`D1-R16`). Without that step the tunnel acquires a port on every connect and
cannot apply it, which reports as healthy and costs the operator the peer
connectivity port forwarding exists to buy.

### The wiring graph

| From | To | What |
|------|-----|------|
| lemonfiber | qBittorrent | **WebUI password** — generated, set, and recorded for the forwarded-port push |
| SABnzbd, qBittorrent | Sonarr, Radarr, Lidarr, Bindery | Download client registration with categories |
| Prowlarr | Sonarr, Radarr, Lidarr | Indexer sync (native app sync) |
| Prowlarr | Bindery | Indexer endpoints (**manual — see below**) |
| Root folders | Every \*arr | Per media type, under `/data/media` |
| Sonarr, Radarr | Bazarr | Subtitle provider wiring |
| Jellyfin | Seerr | **Identity source** — one household account |
| Sonarr, Radarr | Seerr | Request fulfilment targets |
| Every service | Homepage | API keys for live widgets |
| Recyclarr | Sonarr, Radarr | Quality profile synchronisation |

> **Bindery is wired differently.** Prowlarr's app sync supports a fixed set of
> Servarr applications and Bindery isn't among them. It consumes Prowlarr's
> Torznab endpoints instead, which works but must be configured explicitly rather
> than via the same sync path. A real asymmetry, specified rather than glossed.

**This table is a promise, not an illustration** (`D1-R18`). Every row of it is a
connection the operator is entitled to have made for them, and a row nothing makes
is a stack that starts, reports healthy, and quietly does not work — because each of
these is exactly the step whose absence is invisible until somebody asks for
something and nothing happens.

That is not hypothetical. Two of these rows were declared here and obliged by no
acceptance criterion, and both turned out never to have worked: the request
service's identity was refused on every run it ever made, and the download client
was refused by SABnzbd. Both had passing tests, because a test over a fake proves
what the author believed the service wanted rather than what it wants. Neither had
a criterion, so nothing counted them as missing.

A row added to this table therefore arrives already obliged, and one that cannot be
made yet belongs in the prose as an asymmetry — the way Bindery does above — rather
than sitting in the table unmade.

### Jellyfin as household identity is wired unconditionally

Connecting Seerr's authentication to Jellyfin is one API call and it's the
difference between a household member having one account or two. It is never
optional.

### The fulfilment targets decide what can be asked for

Seerr does not discover the \*arrs; it is told about them. Until it is, a request
reaches nothing — the household asks, the ask is accepted, and no downloader ever
hears about it, which is the failure mode this whole feature exists to prevent.

The second half matters as much as the first. Seerr offers what its configured
targets can deliver, so registering only the \*arrs actually in the stack is what
makes [D4](d4-request-flow.md)'s promise true: television is not offered where
Sonarr is not running. Registering one that is absent would offer the household a
thing that cannot arrive.

### Idempotent, and drift-aware

Running seed twice changes nothing. Crucially, it does **not** re-assert values
the operator has since changed — that's [C9](../c-trust/c9-drift.md), and it's
what makes seed safe to run on a stack someone has tuned.

### Partial success is reported precisely

Some services will be unavailable — not in the active form, still starting,
unhealthy. Seed wires what it can, reports exactly what it couldn't and why, and
is re-runnable to complete the rest. It does not fail wholesale because Lidarr
isn't running.

### Verified, not assumed

After writing, each connection is read back. "Registered SABnzbd in Sonarr" means
Sonarr was asked and confirmed it.

### Fast enough to be routine

The target is under a minute. Seed being cheap is what makes configuration
disposable — and disposable configuration is what makes the stack safe to
experiment with.

## States

Per connection:

| State | Meaning |
|-------|---------|
| `pending` | Not yet attempted |
| `wired` | Written and read back successfully |
| `already-wired` | Present and correct; no action taken |
| `drifted` | Present but differing from lemonfiber's baseline — preserved |
| `skipped` | Prerequisite service unavailable |
| `failed` | Attempted and rejected |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Service still starting | Wait briefly, then `skipped` with a note that re-running will complete it. |
| Service in the stack but not the active form | `skipped`, not `failed`. Expected and normal. |
| API key not yet generated | Service hasn't completed first start. Wait, then skip. |
| Service rejects a value | Report the service's own error message; don't paraphrase it into something vaguer. |
| Root folder path doesn't exist | Create it if within the data root; refuse and explain if outside. |
| Operator changed a wired value | Preserve it ([C9](../c-trust/c9-drift.md)); report as drift, don't revert. |
| Download client already registered under a different name | Detect by connection details, not by label. Don't create duplicates. |
| Seed run before any content exists | Fine. Wiring is independent of content. |
| Seerr already using local accounts | Report the conflict; switching identity sources affects existing users, so it needs consent. |
| Two \*arrs claiming the same root folder | Refuse and explain — this causes import conflicts later. |
| Service upgraded with a changed API | Detect the version and report unsupported rather than writing something malformed. |
| Seed interrupted partway | Safe. Each connection is independent; re-running completes the rest. |
| Native-mode Jellyfin | Wire via its host address; verify reachability first and report clearly if unreachable. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **D1-R1** | Service API keys MUST be read from service configuration, never requested from the operator. |
| **D1-R2** | Seed MUST be idempotent; a second run with no changes MUST make no writes. |
| **D1-R3** | Seed MUST NOT overwrite values that have drifted from lemonfiber's baseline. |
| **D1-R4** | Each connection MUST be read back and verified after writing. |
| **D1-R5** | Unavailable prerequisites MUST produce `skipped`, not `failed`. |
| **D1-R6** | Partial completion MUST report exactly which connections were not made and why, and MUST be resumable by re-running. |
| **D1-R7** | Seerr MUST be configured to authenticate against Jellyfin. |
| **D1-R8** | Existing connections MUST be detected by connection details rather than label, to avoid duplicates. |
| **D1-R9** | Root folders MUST be created when within the data root, and refused with an explanation when outside it. |
| **D1-R10** | Two \*arrs sharing a root folder MUST be refused with an explanation. |
| **D1-R11** | Service-reported errors MUST be surfaced verbatim rather than paraphrased. |
| **D1-R12** | An unsupported service API version MUST be reported rather than written to. |
| **D1-R13** | Interruption MUST leave every completed connection intact and valid. |
| **D1-R14** | A full seed against a healthy stack SHOULD complete within 60 seconds. |
| **D1-R15** | Bindery MUST be wired via Torznab endpoints, and the absence of Prowlarr app sync MUST be documented in-product. |
| **D1-R16** | Seeding MUST replace qBittorrent's temporary WebUI password with a generated one and record it where the forwarded-port push reads it. |
| **D1-R17** | Each \*arr that fulfils requests MUST be registered with the request service as a fulfilment target, and one absent from the stack MUST NOT be. |
| **D1-R18** | Every connection named in the wiring graph MUST be made where the services at both ends are in the stack, and each MUST be proven against the service that received it rather than against a stand-in for it. |

## Related

- [C9 Drift detection](../c-trust/c9-drift.md) — what protects operator edits
- [A7 Credential management](../a-getting-started/a7-credential-management.md) — service-generated keys
- [D2 Quality presets](d2-quality-presets.md) — what Recyclarr syncs
- [E3 Backup & restore](../e-maintenance/e3-backup-restore.md) · [J6 Recovery](../../journeys/j6-recovery.md)
