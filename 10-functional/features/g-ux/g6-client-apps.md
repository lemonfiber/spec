---
id: G6
title: Client app guidance
kind: feature
area: G
audience: household
status: accepted
tracks: v1
labels: [household, ux]
depends: [D2, D6, D8, G5]
---

# G6 — Client app guidance

**Status:** Accepted · **Audience:** Household · **Area:** G — Cross-cutting UX

---

## Purpose

Get household members watching on the devices they actually use.

Everything up to this point delivers files to a server. Nobody watches a server.
The last step — installing a Jellyfin client on a TV, phone or tablet and pointing
it at the right address — is entirely outside lemonfiber's control, and is where a
successful setup can still end in "it doesn't work."

It is also the step most likely to be attempted by the least technical person in
the house, unsupervised, on a television remote.

## Behaviour

### The right client for the device is named

Jellyfin's client landscape is uneven and it matters which one is used:

| Device | Situation |
|--------|-----------|
| **Android / iOS** | Official apps, good |
| **Android TV / Fire TV** | Official app, good — the common living-room case |
| **Apple TV** | Official app available; third-party clients also widely used |
| **Web browser** | Always works, no installation. **The reliable fallback.** |
| **Smart TVs (LG, Samsung)** | Varies by platform and vintage — the weakest area |
| **Kodi** | Plugin available |

Naming the browser as an always-available fallback matters: it means nobody is
ever fully blocked, whatever their TV runs.

### Honest about the hard cases

Where support is poor — an older smart TV, an unusual platform — lemonfiber says
so and suggests alternatives (a cheap streaming stick, or casting from a phone)
rather than sending someone into an hour of failure.

### Connection details are handed over, not recited

The server address is a LAN address the household member must type into a TV app,
with a remote control. That is genuinely unpleasant.

So the invitation carries a QR code, the address is shown wherever it's needed,
and an mDNS name is preferred where available because it's shorter and stable.

### Transcoding consequences are surfaced here

If the operator chose a quality preset the platform cannot transcode
([D2](../d-content/d2-quality-presets.md)), the symptom appears at playback on a
client that can't direct-play — buffering, stuttering, or failure to start.

Guidance names the likely cause rather than leaving it as an unexplained playback
problem, because the operator will otherwise look everywhere except at the
quality setting.

### lemonfiber does not install anything

It provides guidance. It cannot and must not reach into someone's television.
Where a link or store page can be offered, it is; the rest is instructions.

### Scope is honest

Playback works on the home network. Watching from elsewhere is not supported in
1.0 ([B7 deferred](../README.md#b--running-it)). Said up front rather than
discovered at a friend's house.

## States

Per household member:

| State | Meaning |
|-------|---------|
| `not-connected` | Account exists; never signed in from a client |
| `connected` | Has signed in from at least one device |
| `playback-verified` | Has successfully played something |
| `playback-problems` | Playback attempted with repeated failures or transcoding stress |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Device has no Jellyfin client | Suggest the browser, casting, or an inexpensive streaming device. |
| Client can't find the server | Distinguish wrong address, device on a different network, and server not running. Three different fixes. |
| Device on guest Wi-Fi | Common and confusing — guest networks isolate clients. Name it as a likely cause. |
| Playback starts then buffers | Likely transcoding. Point at the quality preset and the platform's transcoding capability. |
| Client shows an empty library | Distinguish a library that hasn't scanned from permissions that hide everything. |
| Household member signed in but never watched | Not an error. Surfaced only if the operator asks. |
| Older TV client with limited codec support | Note that direct play may fail and transcoding will be needed. |
| Multiple people on one device | Jellyfin supports profile switching; mention it. |
| Address changed | Clients cache it; guidance covers updating a saved server. |
| Household member outside the home | Clearly explained as unsupported in 1.0, not presented as a fault. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **G6-R1** | Client guidance MUST name the appropriate client per device category. |
| **G6-R2** | A browser MUST be presented as an always-available fallback requiring no installation. |
| **G6-R3** | Poorly supported platforms MUST be identified as such, with alternatives suggested. |
| **G6-R4** | The server address MUST be provided as a QR code as well as text. |
| **G6-R5** | An mDNS name MUST be preferred over a raw IP where available. |
| **G6-R6** | Where the chosen quality preset requires transcoding the platform cannot perform, playback guidance MUST name that as the likely cause of playback problems. |
| **G6-R7** | lemonfiber MUST NOT attempt to install software on a household member's device. |
| **G6-R8** | Guidance MUST state that playback is limited to the home network in 1.0. |
| **G6-R9** | Connection failures MUST distinguish wrong address, wrong network, and server unavailable. |
| **G6-R10** | Guest-network isolation MUST be named as a likely cause where a client cannot reach the server. |
| **G6-R11** | An empty library MUST distinguish an unscanned library from permission restrictions. |
| **G6-R12** | Guidance MUST cover updating a saved server address on a client. |
| **G6-R13** | Household members who have never connected MUST be visible to the operator on request. |

## Related

- [G5 The front door](g5-front-door.md) — where they start
- [D6 Household identity](../d-content/d6-household-identity.md) — invitations carrying the address
- [D2 Quality presets](../d-content/d2-quality-presets.md) — the transcoding consequence
- [D8 Parental controls](../d-content/d8-parental-controls.md) — why a library may appear empty
