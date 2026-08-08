---
id: D9
title: '"Where is my show?" pipeline trace'
kind: feature
area: D
audience: both
status: accepted
tracks: v1
labels: [verification, ux]
relates: [B4, C3, C7, D3, D4]
---

# D9 — "Where is my show?" pipeline trace

**Status:** Accepted · **Audience:** Both · **Area:** D — Content & household

---

## Purpose

Follow one item across every service, end to end, and answer the question people
actually ask.

"Where is my show?" is the most common question in any household running this,
and answering it currently requires opening four web interfaces and correlating
timestamps by hand: was it found? grabbed? did it download? did it import? Each
service holds one fragment and none of them link.

For a non-technical operator the question is effectively unanswerable, and the
household member asking has no visibility at all.

Nothing in this ecosystem does this well. It is the clearest opportunity for
lemonfiber to be *better* than a hand-rolled stack rather than merely easier to
set up.

## Behaviour

### One item, every stage, one view

```
  The Expanse · Season 4 · Episode 3

  ✓ Monitored          Sonarr            3 days ago
  ✓ Found              Prowlarr          2 days ago    47 results, best: 1080p WEB
  ✓ Grabbed            SABnzbd           2 days ago    2.4 GB
  ✓ Downloaded         SABnzbd           2 days ago    took 4m 12s
  ✗ Import failed      Sonarr            2 days ago
       Permission denied writing to /data/media/tv/The Expanse
       → the media directory isn't writable by the container
       [Fix this]
```

Each stage names the service, the time, and the outcome. The failing stage
carries the reason and a remedy.

### Sources are correlated automatically

The correlation is the hard part and the whole value: a release name in Prowlarr,
a job in SABnzbd, a queue item in Sonarr, and a file on disk are four different
identifiers for one thing. lemonfiber joins them so the operator doesn't have to.

### Searchable in the terms people use

By show name, film title, or a household member's request — not by internal
identifiers. Someone asking "where's the thing I asked for on Tuesday?" should be
able to find it.

### It works for items that never started

The most confusing case is content that simply never appears. The trace must
distinguish:

- Not monitored — nobody asked for it
- Monitored, never found — indexers returned nothing
- Found, never grabbed — nothing met the quality preset
- Grabbed, never downloaded — download client rejected or lost it
- Downloaded, never imported — the silent failure from [C7](../c-trust/c7-queue-health.md)

These look identical from outside — nothing happened — and each has a completely
different cause and remedy.

### Household members see their own requests

A simplified view via Seerr showing their request's progress. They don't get
the operator's diagnostic detail, but they aren't left in silence either.

### It becomes the natural landing point for a stuck item

Anything reported by queue health links here, so "3 items stuck" leads directly
to per-item explanations rather than to a list the operator must investigate.

## States

Per traced item, the furthest stage reached: `not-monitored`, `monitored`,
`searching`, `found`, `grabbed`, `downloading`, `downloaded`, `importing`,
`imported`, `available`.

Plus a failure flag naming the stage where it stopped and why.

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Item known to some services but not others | Show what each knows; gaps are themselves diagnostic. |
| Release renamed between stages | Correlate on stable identifiers where available; fall back to fuzzy matching and mark confidence. |
| Multiple attempts for the same item | Show the history — repeated failed grabs are a pattern worth seeing. |
| Item imported then deleted | Show the full history including removal, and by what. |
| Service logs rotated away | Report what's known and that earlier detail is unavailable; don't infer. |
| Very old item | Bound retained history; state the horizon. |
| Item from before lemonfiber was installed | Show current state; note that pre-installation history is unavailable. |
| Manual import outside the \*arrs | Show it as present with unknown provenance. |
| Two services disagree about state | Show both and flag the disagreement — that's a real finding, not a display bug. |
| Correlation is uncertain | State the uncertainty rather than presenting a guess as fact. |
| Item requested by a household member who was removed | Trace still available to the operator. |
| Season or series-level query | Aggregate per-episode states with a summary. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **D9-R1** | A single item MUST be traceable across every service that handled it, in one view. |
| **D9-R2** | Each stage MUST name the service, the time, and the outcome. |
| **D9-R3** | A failing stage MUST carry the reason and a remedy. |
| **D9-R4** | Items MUST be searchable by human-meaningful terms, not internal identifiers. |
| **D9-R5** | The trace MUST distinguish not-monitored, never-found, never-grabbed, never-downloaded and never-imported. |
| **D9-R6** | Correlation across services MUST be automatic. |
| **D9-R7** | Uncertain correlation MUST be marked as uncertain rather than presented as fact. |
| **D9-R8** | Disagreement between services MUST be surfaced as a finding. |
| **D9-R9** | Repeated attempts for the same item MUST be shown as history. |
| **D9-R10** | Unavailable historical detail MUST be reported as unavailable, never inferred. |
| **D9-R11** | Items reported by queue health MUST link directly to their trace. |
| **D9-R12** | Household members MUST be able to see progress of their own requests in simplified form. |
| **D9-R13** | Series and season level queries MUST aggregate per-item states with a summary. |
| **D9-R14** | Retained history MUST be bounded, and the horizon MUST be stated. |

## Related

- [C7 Queue health](../c-trust/c7-queue-health.md) — what links here
- [D3 First-content walkthrough](d3-first-content.md) — the same visibility, live
- [D4 Household request flow](d4-request-flow.md) — the household's simplified view
- [B4 Log viewing](../b-running/b4-logs.md) — the underlying detail
- [C3 Auto-remediation](../c-trust/c3-auto-remediation.md) — acting on a failed stage
