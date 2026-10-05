---
id: D1
title: Service auto-wiring
kind: feature
area: D
audience: operator
status: accepted
maturity: building
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

**NZBHydra2 is the other exception.** It starts with no authentication at all, and in that
state it answers a read of its whole configuration to anyone who can reach it, including the
indexer accounts it holds and their keys. An indexer account is an account somebody paid
for. Loopback binding keeps the network out, but not every other container on the stack's
network, a plugin's among them. So lemonfiber turns authentication on: it names an
administrator, generates the password, and records it under the service's own
administrator-password setting (`NZBHYDRA2_ADMIN_PASSWORD`), as it does for the media server.
It then proves the change by asking the same read again presenting nothing, and being
refused (`D1-R22`). The connections that reach NZBHydra2 with its API key are not affected:
the key is a separate credential, and nothing that searches through it changes.

An NZBHydra2 already running with no authentication, which is every stack seeded before
this, is adopted rather than rebuilt. Authentication is turned on in place, keeping every
indexer, setting and history it holds, and the indexers it held before are read back
afterwards (`D1-R23`). An operator who later turns it off, or changes it, has made a choice.
Seed keeps that choice and reports it as drift, like any other value (`D1-R3`, `D1-R24`). The
doctor still says what that choice exposes (`D1-R26`), and a reset turns authentication back
on. A password lemonfiber no longer holds, or one NZBHydra2 refuses, is reported as refused,
naming the setting. lemonfiber never turns authentication off, or replaces the service's
administrator, to get back in (`D1-R25`).

### The wiring graph

| From | To | What |
|------|-----|------|
| lemonfiber | qBittorrent | **WebUI password** — generated, set, and recorded for the forwarded-port push |
| lemonfiber | NZBHydra2 | **Authentication** — an administrator set, its password generated and recorded |
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

### On the companion

Seed makes the thirty connections, and the companion may run it
([N7](../n-companion/n7-moving-in.md)). That is safe from a phone for two
reasons this feature already requires: a second run with nothing changed writes
nothing (`D1-R2`), and a value the operator set is kept rather than overwritten
(`D1-R3`). `N7-R15` offers the run and shows each connection in the state it
ended in; `N7-R16` forbids offering to overwrite the operator's value.

*Partial success is reported precisely* is the property that has to survive a
small screen. `N7-R1` requires what could not be carried shown with a reason for
each, and not subordinated to a success message — twenty-eight connections of
thirty is a success by any count, and the two that failed are the entire content
of the report. Because seed is re-runnable, `N7-R9` requires a run that carried
nothing told apart from one that has not run; with no shell to check, those look
identical.

*Verified, not assumed* is what gives the app something honest to render. Where a
connection was read back it is sound; where it could not be read back, `N7-R7`
requires that shown as its own answer rather than as sound, because an
unverifiable wiring rendered green is worse than showing nothing. Where the stack
attaches a severity, `N7-R8` requires both what would break and what would put it
right — away from the machine, the second is the only half that can be acted on.

Idempotence is not rehearsal. Running seed twice changing nothing is a property
of the operation; a run that deliberately writes nothing is a rehearsal, and
`N7-R10` holds it to the labelling `N6-R1` requires everywhere else.

### The request service reaches the \*arrs through a gate

Seerr is household tier, and a key to Sonarr, Radarr or Jellyfin is administration
of that service. So the connections *Sonarr, Radarr → Seerr* and *Jellyfin → Seerr*
are made through the request gate
([ADR-0032](../../../00-overview/decisions/0032-the-request-service-reaches-the-arrs-through-a-gate.md)).
Seerr is registered with each \*arr at the gate's route for it and holds a token
lemonfiber minted for that route; the gate holds the \*arr's key (`D1-R19`). Once
Seerr is initialised, lemonfiber speaks to it with Seerr's own key, and the
administrator's password the initialising sign-in carried is rotated (`D1-R20`). A
stack whose Seerr already holds the keys has them taken back, each move proved
through Seerr before anything is revoked (`D1-R21`).

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
| NZBHydra2 found without authentication | Turn it on, keeping everything it holds; read the indexers back. |
| The operator turned NZBHydra2's authentication off | Keep it, report it as drift, and the doctor reports the exposure; a reset turns it back on. |
| The recorded NZBHydra2 password is missing or refused | Report it as refused, naming the setting; never turn authentication off to get back in. |
| NZBHydra2's health check reads a page authentication now guards | The stack's check reads a path NZBHydra2 answers without a credential, so turning authentication on never reads as unhealthy. |
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
| **D1-R19** | The request service MUST reach each fulfilling \*arr and Jellyfin only through the request gate: each \*arr MUST be registered with it at the gate's route for that \*arr and with the token lemonfiber minted for that route, never with the \*arr's own key, and it MUST be left holding no Jellyfin API key and no Jellyfin administrator's session ([ADR-0032](../../../00-overview/decisions/0032-the-request-service-reaches-the-arrs-through-a-gate.md)). |
| **D1-R20** | Once the request service is initialised, lemonfiber MUST authenticate to it with the request service's own API key and MUST NOT send it the media server administrator's password; the password the initialising sign-in carried MUST be rotated once that sign-in completes. |
| **D1-R21** | Where the request service is found holding a credential of an \*arr or of Jellyfin, lemonfiber MUST move it to the request gate and prove the move through the request service before revoking anything, MUST then revoke or rotate every credential the request service held, and MUST report any consumer the rotation could not update. |
| **D1-R22** | Seeding MUST turn on NZBHydra2's authentication, with an administrator lemonfiber names and a password it generates and records under that service's own administrator-password setting, and MUST then prove that a read of its configuration or of the indexers it holds, presenting nothing, is refused. |
| **D1-R23** | Where NZBHydra2 is found running without authentication that lemonfiber has no record of having set, seeding MUST turn it on without removing or changing any indexer, setting or history the service holds, and MUST prove after the change that every indexer it held before is still held. |
| **D1-R24** | Where authentication lemonfiber turned on in NZBHydra2 has since been turned off or changed, seeding MUST keep it and report it as drift, and a reset MUST turn it back on. |
| **D1-R25** | Where the password lemonfiber recorded for NZBHydra2 is missing or refused, seeding MUST report the connection as refused, naming the setting, and MUST NOT turn the service's authentication off or replace its administrator. |
| **D1-R26** | The doctor MUST report an NZBHydra2 that answers a read of its configuration to a caller presenting nothing, naming the service, what the read exposes, and that a seed or a reset turns its authentication on. |

## Related

- [C9 Drift detection](../c-trust/c9-drift.md) — what protects operator edits
- [A7 Credential management](../a-getting-started/a7-credential-management.md) — service-generated keys
- [D2 Quality presets](d2-quality-presets.md) — what Recyclarr syncs
- [E3 Backup & restore](../e-maintenance/e3-backup-restore.md) · [J6 Recovery](../../journeys/j6-recovery.md)
