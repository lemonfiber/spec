---
id: H4
title: Subtitles
kind: feature
area: H
audience: both
status: accepted
tracks: v2
priority: P1
labels: [subtitles, wiring, verification, quality]
relates: [D1]
---

# H4 — Subtitles

**Status:** Accepted · **Audience:** Both · **Area:** H — Ecosystem glue

---

## Purpose

A library grabbed without subtitles is a library the hard-of-hearing household
member, the language learner, and anyone watching a foreign-language film cannot
fully use. Fetching subtitles by hand — per episode, per language, from a handful
of provider sites — is exactly the repetitive chore automation exists to remove.
This feature fetches and manages subtitles for the Sonarr and Radarr libraries from
open subtitle providers, per the household's language profile, so the right
subtitles arrive alongside the content without anyone hunting for them.

## Behaviour

### It follows the libraries

The tool tracks what Sonarr and Radarr hold and seeks subtitles for it, per the
languages the household wants. New content acquires subtitles as it arrives;
existing content is backfilled. The household sees which items have their wanted
languages and which are still missing.

### It honours a language profile

Which languages to fetch is a household choice, not a per-file one. The tool reads
the language profile — the wanted languages, in preference order — and seeks those,
rather than grabbing whatever a provider offers. If no language profile is set,
there is nothing to fetch *for*, and the tool says so plainly instead of guessing.

### It fetches from open providers

Subtitles come from open subtitle providers configured by the operator. Where a
provider needs an account the operator supplies it, and the tool uses it within the
provider's limits. The household member never sees the plumbing — they see whether
their language is present.

### It proves the wiring end to end

The tool proves the path rather than assuming it: it checks each provider's status,
asserts that Sonarr and Radarr are actually linked and that a language profile is
set, and performs a **test fetch for a known item** that must complete — downloading
a real subtitle for a real library item and confirming it landed. A configuration
that cannot complete a test fetch is reported as unproven, not ready.

### It manages, not just fetches

Subtitles that are the wrong language, badly mistimed, or duplicated are a
management problem, not just a fetching one. The tool tracks what it placed so it can
replace a bad subtitle rather than pile a second one beside it, and so a household
member can flag one as wrong.

### Every step is scriptable

Triggering a fetch, listing missing languages, and running the wiring proof are each
reachable non-interactively.

## States

| State | Meaning |
|-------|---------|
| `unconfigured` | No providers wired, or Sonarr/Radarr not linked |
| `no-profile` | Linked, but no language profile is set, so nothing is sought |
| `ready` | Providers, library links, and language profile proven; fetching can run |
| `fetching` | A subtitle pass is in progress |
| `complete` | Wanted languages present for tracked items |
| `degraded` | Wired but a provider failed its status or credential check, or is rate-limited |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Provider rate-limits or returns a temporary block | Back off and report the provider as rate-limited; do not hammer it or present the pass as failed for lack of subtitles. |
| Provider outage | Mark that provider unavailable and continue with the others; one provider down must not stall the rest. |
| Fetched subtitle is the wrong language despite its label | Track placements so a mislabelled grab can be replaced, and let a household member flag it as wrong. |
| Fetched subtitle is mistimed against the release | Prefer a better-matching candidate where available; surface a poor match rather than silently leaving a mistimed file. |
| No language profile set | Enter `no-profile` and say so; never guess a language or fetch arbitrarily. |
| Wanted language unavailable from any provider for an item | Report the item as missing that language rather than substituting a different one. |
| Provider credentials invalid | Fail the provider's credential check loudly and skip it until re-proven; never treat an unauthenticated provider as working. |
| Duplicate subtitles from multiple providers | Keep the preferred one per language and avoid piling redundant files beside the media. |
| Library item removed after subtitles fetched | Do not leave orphaned subtitle files misrepresenting the library's state. |
| Household member requests a language outside the profile | Treat the profile as the source of truth; a one-off request is a profile change, surfaced as such. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **H4-R1** | The subtitle service and its configured providers MUST be open-source or open subtitle providers; the tool MUST NOT depend on a proprietary or closed subtitle service. |
| **H4-R2** | The tool MUST wire Sonarr and Radarr and the subtitle providers via their APIs, and MUST NOT require the household to fetch subtitles by hand. |
| **H4-R3** | The tool MUST fetch only the languages named in the household's language profile, in its preference order. |
| **H4-R4** | If no language profile is set, the tool MUST enter a no-profile state and say so, and MUST NOT guess a language or fetch arbitrarily. |
| **H4-R5** | The tool MUST prove the wiring: each provider's status, an assertion that Sonarr and Radarr are linked and a language profile is set, and a test fetch for a known item that completes. |
| **H4-R6** | A configuration that cannot complete a test fetch MUST be reported as unproven, never as ready. |
| **H4-R7** | An invalid provider credential MUST fail its check loudly and cause that provider to be skipped until re-proven. |
| **H4-R8** | A rate-limited provider MUST be backed off from and reported as rate-limited, not presented as failed for lack of results. |
| **H4-R9** | A provider outage MUST mark only that provider unavailable, leaving the others fetching. |
| **H4-R10** | The tool MUST track the subtitles it places so a wrong or mistimed subtitle can be replaced rather than duplicated. |
| **H4-R11** | A wanted language unavailable for an item MUST be reported as missing, and the tool MUST NOT substitute a different language. |
| **H4-R12** | A household member MUST be able to flag a placed subtitle as wrong so it can be re-fetched. |
| **H4-R13** | Removing a library item MUST NOT leave orphaned subtitle files that misrepresent the library. |
| **H4-R14** | Triggering a fetch, listing missing languages, and running the wiring proof MUST each be reachable non-interactively. |

## Related

- [D1 Service auto-wiring](../d-content/d1-seed.md) — how Sonarr, Radarr, and the providers are connected
- [D2 Quality presets in plain language](../d-content/d2-quality-presets.md) — the household quality and language choices this follows
- [H3 Quality-profile sync](h3-quality-sync.md) — the sibling that manages release scoring
- [C8 Provider health & quota tracking](../c-trust/c8-provider-health.md) — the provider-limit model this respects
