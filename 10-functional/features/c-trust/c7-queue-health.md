---
id: C7
title: Queue health & stuck items
kind: feature
area: C
audience: operator
status: accepted
tracks: v1
labels: [queue, verification]
requires: [B3, B5]
relates: [C1, C3, C8, D9]
---

# C7 — Queue health & stuck items

**Status:** Accepted · **Audience:** Operator · **Area:** C — Trust & correctness

---

## Purpose

Setup is a one-day problem. **Stuck items are the forever problem.**

Once running, the recurring failure isn't configuration — it's a queue that
quietly jams. A download stalls at 94%. An import fails because a file is locked,
or the release is in a format nothing can extract, or a permission is wrong. An
indexer returns nothing because the API key silently expired.

Each service knows about its own stall, and none of them tell anyone. Sonarr
shows it if you open the queue and look. The operator's experience is simply that
things stopped appearing — and their diagnosis is "it broke," with no idea where.

## Behaviour

### The queue is watched across services, not within one

The failure that matters most is the one nobody owns: an item that **downloaded
successfully and was never imported**. SABnzbd considers it finished. Sonarr never
picked it up. Neither reports a problem, because from each service's own
perspective there isn't one.

Only something watching both sees it.

### Stall categories, because remedies differ

| Category | Signal | Typical cause |
|----------|--------|---------------|
| **Stalled download** | No progress beyond a threshold | Dead torrent, no seeders, exhausted Usenet retention |
| **Completed, not imported** | Finished but absent from the library | Permissions, unparsable name, archive not extracted |
| **Repeated import failure** | Same item failing repeatedly | Structural — will not resolve itself |
| **Waiting indefinitely** | Monitored, never grabbed | No releases match, or indexers are returning nothing |
| **Orphaned download** | Present on disk, unknown to any \*arr | Manual addition, or the \*arr lost track |
| **Redownload loop** | Same item fetched repeatedly | Import silently failing and being retried forever |

The redownload loop deserves special attention: it consumes bandwidth and Usenet
quota indefinitely while appearing to be normal activity.

### Thresholds are time-based and adjustable

"Stuck" is a judgement. A torrent with no seeders may recover in a day; one that
hasn't moved in a week won't. Defaults are conservative — a false "stuck" report
trains the operator to ignore the feature.

### Findings reach the operator without being sought

Surfaced on the dashboard and, per [B5](../b-running/b5-notifications.md),
notified at warning severity. The entire problem is *not noticing*, so the
information must arrive rather than wait to be found.

### Remediation where the fix is unambiguous

Some stalls have one correct action — retry an import, remove and re-grab a dead
torrent, clean up an orphan. Offered per [C3](c3-auto-remediation.md), never
applied silently.

### Explains rather than merely reports

"3 items stuck" is a status line. What the operator needs is which items, how
long, what's blocking each, and what to do. Where the cause is knowable — a
permission denial in the import log — it is named.

## States

Per item:

| State | Meaning |
|-------|---------|
| `progressing` | Moving normally |
| `slow` | Below expectation but progressing |
| `stalled` | No progress beyond threshold |
| `awaiting-import` | Complete, not yet imported, within grace |
| `import-blocked` | Complete, import attempted and failed |
| `orphaned` | On disk, unknown to any \*arr |
| `looping` | Repeatedly re-acquired |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Legitimately slow download | Distinguish `slow` from `stalled`. A large release on a slow connection is not broken. |
| Import delayed by post-processing | Respect a grace period; extraction and repair take time. |
| Item stuck because the disk is full | Report the disk as the cause, not the item. One cause, one alert. |
| \*arr unreachable | Cannot assess its queue; report `unverified` rather than assuming health. |
| Manual download the \*arrs shouldn't own | Allow marking as intentionally unmanaged so it stops reporting as orphaned. |
| Very large queue | Report counts by category with the most significant items detailed; don't enumerate thousands. |
| Item stuck on a release the operator doesn't want | Offer to blocklist and move on, not just retry. |
| Stall clears by itself | Resolve the condition and record it. Don't leave a stale alert. |
| Seeding torrent held at 100% | Not stuck. Seeding is intentional; distinguish it from a stalled transfer. |
| Import fails from a sample or extras file | Recognise as benign where identifiable; don't escalate normal behaviour. |
| Two \*arrs claim the same item | Report the conflict; it indicates misconfigured root folders. |
| Queue empty | Say so. An empty queue and an unreadable queue are different. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **C7-R1** | Queue state MUST be assessed across download clients and \*arrs together, not per service. |
| **C7-R2** | Items downloaded successfully but never imported MUST be detected. |
| **C7-R3** | Stalls MUST be categorised, and each category MUST carry its own remedy. |
| **C7-R4** | Repeated re-acquisition of the same item MUST be detected as a loop. |
| **C7-R5** | Thresholds MUST be time-based and adjustable, with conservative defaults. |
| **C7-R6** | `slow` MUST be distinguished from `stalled`. |
| **C7-R7** | Seeding at 100% MUST NOT be reported as stuck. |
| **C7-R8** | Findings MUST surface on the dashboard and notify at warning severity without being sought. |
| **C7-R9** | Where the blocking cause is knowable, it MUST be named. |
| **C7-R10** | A stall caused by a system condition such as a full disk MUST be attributed to that condition, not to each item. |
| **C7-R11** | An unreachable \*arr MUST report `unverified` rather than implying a healthy queue. |
| **C7-R12** | Items MUST be markable as intentionally unmanaged. |
| **C7-R13** | Large queues MUST be summarised by category rather than enumerated. |
| **C7-R14** | Self-resolving stalls MUST clear their condition and be recorded. |
| **C7-R15** | An empty queue MUST be distinguishable from an unreadable one. |

## Related

- [C1 Diagnostics](c1-diagnostics.md) · [C3 Auto-remediation](c3-auto-remediation.md)
- [C8 Provider health](c8-provider-health.md) — a common upstream cause
- [D9 Pipeline trace](../d-content/d9-pipeline-trace.md) — following one item end to end
- [B3 Dashboard](../b-running/b3-dashboard.md) · [B5 Notifications](../b-running/b5-notifications.md)
