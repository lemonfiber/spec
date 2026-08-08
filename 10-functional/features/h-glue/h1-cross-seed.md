---
id: H1
title: Cross-seeding
kind: feature
area: H
audience: operator
status: accepted
tracks: v2
milestone: M7
priority: P1
labels: [seed, storage, wiring, verification]
relates: [C5, D1]
---

# H1 — Cross-seeding

**Status:** Accepted · **Audience:** Operator · **Area:** H — Ecosystem glue

---

## Purpose

An operator who already holds a file the household downloaded once is, on most
trackers, sitting on seeding potential they never claim — the same episode or
album exists on three other trackers under a different torrent, and uploading to
each would earn ratio without downloading a single byte again. Doing this by hand
means searching every tracker for every release and hoping the file layout
matches; nobody does it consistently. Cross-seeding automates the match: it finds
the other trackers' torrents that describe data already on disk and starts
seeding them by pointing at the existing files, so the household maximises its
contribution back to the ecosystem without spending extra disk or bandwidth.

## Behaviour

### It matches torrents against data already on disk

For content the household already holds, the tool searches the configured
indexers for other releases describing the *same underlying data* — same files,
same sizes, same piece hashes where the tracker exposes them — rather than merely
the same title. A title match is a candidate; a data match is a cross-seed. The
operator sees which local items gained a new tracker and which found none.

### It reuses files instead of re-downloading

A confirmed match is added to the torrent client pointed at the files that are
already on disk, linked into place so a second copy is never written. The whole
point is more seeding at zero extra storage; a cross-seed that copied its payload
would defeat itself. Where the client needs its own directory, the files are
hardlinked (or symlinked as a fallback) using the same inode discipline the
storage feature already enforces, so one set of bytes backs every torrent seeding
it.

### It proves a link will form before it commits

Before adding a match, the tool checks that the source files and the client's
seed path sit on **one filesystem** — a hardlink cannot cross a device boundary,
and a silent fall-through to copying is exactly the failure this feature exists to
avoid. If they are on different filesystems the operator is told plainly, with the
two paths, rather than discovering a doubled disk footprint later.

### It verifies the wiring empirically, not by assumption

Cross-seeding is worthless if the tool cannot actually talk to the torrent client
and the indexers, so the tool proves the path end to end: it pings the service and
each configured indexer, confirms the supplied client and indexer credentials are
accepted rather than merely present, runs a test search that must return a match
for a known local item, and confirms the resulting link shares an inode with its
source. A configuration that cannot demonstrate a real match against real local
data is reported as unproven, never as ready.

### Every step is scriptable

Triggering a cross-seed search, listing matches, and running the wiring proof are
each reachable non-interactively, so an operator can drive cross-seeding from a
cron job or a script without the interactive flow.

## States

| State | Meaning |
|-------|---------|
| `unconfigured` | No torrent client or indexers wired for cross-seeding yet |
| `ready` | Client and indexers wired and proven; searches can run |
| `searching` | A cross-seed pass is in progress |
| `seeding` | One or more cross-seeds added and actively seeding via reused files |
| `degraded` | Wired but an upstream (client or an indexer) failed its last health or credential check |
| `no-match` | Last pass completed but found no cross-seedable release |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Release has an enclosing folder, local copy does not (or vice versa) | Treat as a layout mismatch; either link with the layout the torrent expects or skip, and count it as a near-miss rather than a match. |
| Release adds small extra files (samples, NFOs) not present locally | Match the payload that exists and report the missing pieces; do not present a partial as complete. |
| Seed path is on a different filesystem from the source | Refuse to add the cross-seed and report both paths; never fall back to copying to force it. |
| Filesystem or client cannot hardlink | Attempt a symlink fallback and say which mechanism was used; if neither can form, skip rather than copy. |
| Only some pieces match (partial data) | Do not add as a full seed; report the partial match so the operator decides, and never claim bytes the household does not hold. |
| Tracker forbids cross-seeding in its rules | Honour a per-tracker exclusion; never add a cross-seed to an indexer the operator has marked off-limits. |
| Same data already seeding on that tracker | Detect the existing torrent and skip, rather than adding a duplicate. |
| Indexer unreachable mid-pass | Mark that indexer failed for the pass and continue with the rest; one indexer must not abort the run. |
| Source files move or are deleted after linking | The link breaks like any other; surface it as a broken cross-seed, not as healthy seeding. |
| Client credential rotated or revoked | Fail the credential proof loudly and stop adding torrents until re-proven; never silently no-op. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **H1-R1** | The cross-seeding service and every indexer it depends on MUST be open-source and self-hostable; the tool MUST NOT depend on any hosted or proprietary matching service. |
| **H1-R2** | The tool MUST wire the torrent client and the configured indexers via their APIs, and MUST NOT require the operator to copy credentials between web interfaces. |
| **H1-R3** | A candidate MUST be confirmed as a cross-seed by matching the underlying data (files, sizes, and piece hashes where available), not by title alone. |
| **H1-R4** | A confirmed match MUST be added by reusing the existing on-disk files; the tool MUST NOT re-download or copy the payload. |
| **H1-R5** | Before adding a match, the tool MUST verify that the source files and the seed path share one filesystem, and MUST refuse the link rather than fall back to copying across a device boundary. |
| **H1-R6** | Where a separate seed directory is required, files MUST be linked using the same inode discipline as [C5](../c-trust/c5-storage.md), and the resulting link MUST share an inode with its source. |
| **H1-R7** | The tool MUST prove the wiring empirically: a service ping, an accepted-credential check for the client and each indexer, and a test search returning a match for a known local item. |
| **H1-R8** | A configuration that cannot demonstrate a real match against real local data MUST be reported as unproven, never as ready. |
| **H1-R9** | A layout mismatch (enclosing folder present on one side, extra small files) MUST be reported as a near-miss rather than counted as a match. |
| **H1-R10** | A partial data match MUST NOT be added as a full seed, and the missing pieces MUST be reported. |
| **H1-R11** | An indexer that becomes unreachable mid-pass MUST be marked failed for that pass while the remaining indexers continue. |
| **H1-R12** | A per-tracker cross-seed exclusion MUST be honoured, and a duplicate of data already seeding on a tracker MUST be skipped. |
| **H1-R13** | A revoked or rotated client credential MUST fail the credential proof loudly and halt further additions until re-proven. |
| **H1-R14** | Triggering a search, listing matches, and running the wiring proof MUST each be reachable non-interactively. |

## Related

- [C5 Storage & hardlink management](../c-trust/c5-storage.md) — the inode and device-boundary discipline this reuses
- [D1 Service auto-wiring](../d-content/d1-seed.md) — how the torrent client and indexers are connected
- [H2 Announce-driven grabbing](h2-autobrr.md) — the other half of feeding the download clients
- [C7 Queue health & stuck items](../c-trust/c7-queue-health.md) — where a broken cross-seed surfaces
