---
id: H2
title: Announce-driven grabbing
kind: feature
area: H
audience: operator
status: accepted
tracks: v2
milestone: M7
priority: P1
labels: [wiring, queue, verification, notifications]
depends: [D1, C7]
---

# H2 — Announce-driven grabbing

**Status:** Accepted · **Audience:** Operator · **Area:** H — Ecosystem glue

---

## Purpose

The *arr apps find releases by polling indexers on an interval — good enough for a
library, too slow for a contested release where the first grabbers take the
freeleech or the only seeded copy. An operator who wants a specific release the
instant it lands has to watch tracker announce channels by hand, which nobody can
sustain. Announce-driven grabbing watches the announce channels and feeds in real
time, matches each new line against filters the operator defines, and pushes the
matches straight to the download clients and *arr apps the moment they appear —
turning a minutes-late poll into a sub-second reaction.

## Behaviour

### It watches announces in real time

The tool connects to the configured trackers' announce channels and feeds and
reads each release as it is announced, rather than waiting for the next poll
cycle. The operator sees which channels are connected and, for each, when it last
delivered a line — a silent channel and a connected-but-idle channel are not the
same thing.

### It matches releases against operator filters

Each announced release is tested against filters the operator authors — resolution,
codec, group, size bounds, category, tracker. A match is pushed onward; a non-match
is dropped. The operator can see, for any recent announce, which filter caught it
or why none did.

### It hands matches to the download path

A matched release is delivered to its destination — a download client directly, or
the relevant *arr app so the release is imported and tracked like any other grab.
Which destination a filter uses is part of the filter. Nothing is grabbed that no
filter selected.

### It respects tracker limits

Filters carry limits so an eager rule cannot breach a tracker's snatch cap or grab
a burst it will be penalised for: a filter can cap grabs per window, and when a cap
is reached further matches are held rather than pushed. The operator is told a cap
was hit, not left to discover it from the tracker.

### It proves the wiring before trusting it

The tool proves the path rather than assuming a connected channel means working
grabs: it checks service health, validates each download-client connection by an
accepted-credential check, and re-processes a known real announce line through a
test filter to assert the match decision the operator expects — proving the filter
engine actually fires, not merely that the process is up. A configuration whose
test line does not produce the expected decision is reported as unproven.

### Connection health is surfaced, not hidden

Announce channels drop, get kicked, or go quiet. The tool surfaces each channel's
connection state and idle time so a dead channel is visible immediately, because a
silently disconnected announce watcher looks identical to a quiet night until a
missed release proves otherwise.

### Every step is scriptable

Reloading filters, replaying an announce line through the filter engine, and
running the wiring proof are each reachable non-interactively.

## States

| State | Meaning |
|-------|---------|
| `unconfigured` | No announce channels or filters defined yet |
| `ready` | Channels connected, filters loaded, wiring proven |
| `watching` | Connected and actively matching announces |
| `holding` | A filter's grab cap is reached; further matches held until the window rolls |
| `degraded` | One or more announce channels disconnected, or a download client failed its check |
| `disconnected` | No announce channel is currently connected |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Filter matches far more than expected (over-grabbing) | Enforce the filter's per-window cap and hold the surplus; report the cap hit rather than breaching the tracker. |
| Many announces arrive at once, exceeding a filter's limit | Apply the limit deterministically and hold or drop the overflow per the filter; never silently exceed it. |
| Filter authored to match nothing (typo, impossible bound) | Surface that the filter has matched nothing over a window so a dead rule is visible, not assumed working. |
| Filter authored to match everything | Treat as a likely mistake worth flagging; still honour caps so an over-broad rule cannot flood a tracker. |
| Announce channel disconnected or kicked | Surface the channel as disconnected with its idle time; attempt reconnect and never present it as watching. |
| Announce line malformed or from an unknown tracker template | Skip the line and record it as unparsed rather than grabbing wrongly on a bad parse. |
| Download client unreachable when a match fires | Hold the match and report the destination as failed; do not drop a wanted release silently. |
| Two filters match the same release | Resolve deterministically (single grab) so the release is not fetched twice. |
| Snatch cap reached at the tracker itself | Honour the tracker's rejection and stop pushing to it rather than retrying into a penalty. |
| Credentials for a client rotated | Fail the client check loudly and hold pushes to it until re-proven. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **H2-R1** | The announce-watching service MUST be open-source and self-hostable; the tool MUST NOT depend on any hosted or proprietary announce or matching service. |
| **H2-R2** | The tool MUST wire the indexers, download clients, and the *arr apps via their APIs, and MUST NOT require the operator to copy credentials between web interfaces. |
| **H2-R3** | Each announced release MUST be evaluated against the operator's filters in real time, and only filter matches MUST be pushed onward. |
| **H2-R4** | A matched release MUST be delivered to the destination its filter specifies — a download client or the relevant *arr app. |
| **H2-R5** | The tool MUST prove the wiring empirically: service health, an accepted-credential check for each download-client connection, and re-processing of a known real announce line through a test filter asserting the expected match decision. |
| **H2-R6** | A configuration whose test announce line does not produce the expected match decision MUST be reported as unproven, never as ready. |
| **H2-R7** | A filter MUST be able to cap grabs per time window, and reaching a cap MUST hold further matches rather than breach a tracker's snatch limit. |
| **H2-R8** | A tracker's own rejection of a grab MUST be honoured; the tool MUST NOT retry into a penalty. |
| **H2-R9** | Each announce channel's connection state and idle time MUST be surfaced so a disconnected watcher is visible immediately. |
| **H2-R10** | A malformed or unrecognised announce line MUST be recorded as unparsed and skipped, never grabbed on a bad parse. |
| **H2-R11** | A filter that has matched nothing over a window MUST be surfaced so a dead rule is visible rather than assumed working. |
| **H2-R12** | When two filters match one release, the tool MUST resolve to a single grab and MUST NOT fetch the release twice. |
| **H2-R13** | A download client that is unreachable when a match fires MUST cause the match to be held and reported, never silently dropped. |
| **H2-R14** | Reloading filters, replaying an announce line through the filter engine, and running the wiring proof MUST each be reachable non-interactively. |

## Related

- [D1 Service auto-wiring](../d-content/d1-seed.md) — how indexers, clients, and *arr apps are connected
- [C7 Queue health & stuck items](../c-trust/c7-queue-health.md) — where grabbed releases are tracked once handed off
- [H1 Cross-seeding](h1-cross-seed.md) — the complementary way the household maximises the same files
- [C8 Provider health & quota tracking](../c-trust/c8-provider-health.md) — tracker limits this must respect
