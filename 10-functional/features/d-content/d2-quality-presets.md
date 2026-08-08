---
id: D2
title: Quality presets in plain language
kind: feature
area: D
audience: operator
status: accepted
tracks: v1
labels: [quality]
relates: [C9, D1, D5, G2]
---

# D2 — Quality presets in plain language

**Status:** Accepted · **Audience:** Operator · **Area:** D — Content & household

---

## Purpose

Let someone choose what quality they want without learning what a custom format
is.

Quality configuration is the deepest rabbit hole in this ecosystem. The TRaSH
guides — excellent, and the community standard — run to dozens of pages covering
custom formats, scoring, release groups, and repack handling. Configuring it
properly by hand takes an evening and real domain knowledge.

The operator's actual question is much simpler: *how good should this look, and
how much disk am I willing to spend?* Everything else is implementation.

## Behaviour

### The question is asked in the operator's terms

| Preset | Means | Roughly |
|--------|-------|---------|
| **Space-saving** | Good enough on a laptop or tablet | 720p–1080p, smaller encodes |
| **Balanced** *(default)* | Looks right on a TV, sensible file sizes | 1080p, good encodes |
| **High quality** | Best 1080p available, size secondary | 1080p, high-bitrate |
| **Maximum** | 4K where it exists, HDR preserved | 2160p, very large files |

Each preset states its practical consequence — approximate size per hour and
whether a typical client will need to transcode — because that's what the choice
actually costs.

### Presets map to community-maintained profiles

Presets are a friendly surface over Recyclarr's TRaSH-guide profiles, not a
parallel quality system. The community maintains the hard part; lemonfiber
translates the question.

This matters for durability: when release-group scoring shifts, the upstream
guides update and Recyclarr syncs it. A bespoke scoring system would rot.

### Transcoding consequences are stated up front

Choosing **Maximum** on a machine that cannot hardware-transcode means every
household member watching on a device that can't direct-play 4K HDR will hit
CPU-bound transcoding — which on Docker for macOS or Windows means it will not
work well.

lemonfiber knows the platform and the Jellyfin mode
([ADR-0007](../../../00-overview/decisions/0007-dual-mode-jellyfin.md)), so it can
say this *before* the choice rather than after the complaints.

### Per-type overrides, without leaving plain language

Different presets per media type are supported — Maximum for film, Balanced for
television is a common and sensible split, since a series is many times the
volume of a film.

### The full depth remains reachable

Presets are a starting point, not a ceiling. An operator who wants to hand-tune
custom formats does so directly in the \*arr, and [C9](../c-trust/c9-drift.md)
protects that work from being reverted.

### Changes are forward-looking

Changing a preset affects future acquisitions. It does not retroactively upgrade
an existing library unless the operator explicitly asks for that — which is a
large, bandwidth-expensive operation and must never be a side effect.

## States

| State | Meaning |
|-------|---------|
| `unset` | No preset chosen; \*arr defaults in force |
| `applied` | Preset synced and active |
| `overridden` | Per-type presets differ from the global choice |
| `customised` | Operator has hand-edited profiles; preset no longer authoritative |
| `sync-failed` | Preset could not be applied |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Maximum chosen without hardware transcoding | State the consequence for household playback before confirming. |
| Preset chosen with limited disk | Project storage need against free space and warn if implausible. |
| Operator hand-edited profiles | Report `customised`; do not overwrite. Applying a preset then requires explicit consent. |
| Upstream guides changed | Sync on schedule; report meaningful changes rather than applying silently. |
| Upstream unreachable | Keep the current profiles; report that sync is stale. Never fall back to unconfigured. |
| Preset lowered after building a library | Affects future grabs only. State this explicitly — the expectation is often the opposite. |
| Operator wants existing content upgraded | Supported as an explicit, separate action with its bandwidth and time cost stated. |
| Media type has no meaningful preset | Books and audiobooks have different quality axes; present format preferences instead of resolution. |
| Preset conflicts with an indexer's available releases | Report that few or no releases match, distinguishing it from an indexer failure. |
| Two presets produce identical profiles for a type | Collapse them rather than presenting a distinction without a difference. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **D2-R1** | Quality MUST be selectable in plain language without reference to custom formats or scoring. |
| **D2-R2** | Each preset MUST state its practical consequence — approximate size and transcoding implications. |
| **D2-R3** | Presets MUST map to community-maintained profiles rather than a bespoke scoring system. |
| **D2-R4** | Where the platform cannot hardware-transcode, selecting a preset requiring transcoding MUST warn before confirmation. |
| **D2-R5** | Per-media-type presets MUST be supported. |
| **D2-R6** | Changing a preset MUST state that it affects future acquisitions only. |
| **D2-R7** | Upgrading existing content MUST be a separate explicit action with its cost stated. |
| **D2-R8** | Hand-edited profiles MUST be detected and MUST NOT be overwritten without explicit consent. |
| **D2-R9** | An unreachable upstream guide source MUST leave existing profiles intact and MUST report staleness. |
| **D2-R10** | Projected storage requirement MUST be compared against available space, with a warning where implausible. |
| **D2-R11** | Media types without a resolution axis MUST present appropriate alternative options. |
| **D2-R12** | A preset yielding no matching releases MUST be reported distinctly from an indexer failure. |

## Related

- [D1 Service auto-wiring](d1-seed.md) — Recyclarr wiring
- [C9 Drift detection](../c-trust/c9-drift.md) — protecting hand-tuned profiles
- [D5 Disk space](d5-disk-space.md) — the storage consequence
- [ADR-0007 Dual-mode Jellyfin](../../../00-overview/decisions/0007-dual-mode-jellyfin.md)
- [G2 Plain-language layer](../g-ux/g2-plain-language.md)
