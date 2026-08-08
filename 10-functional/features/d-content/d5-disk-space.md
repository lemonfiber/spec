---
id: D5
title: Disk space management
kind: feature
area: D
audience: operator
status: accepted
tracks: v1
labels: [storage]
requires: [B5]
relates: [C5, C7, D2]
---

# D5 — Disk space management

**Status:** Accepted · **Audience:** Operator · **Area:** D — Content & household

---

## Purpose

Stop the disk filling, and make it obvious what's consuming it.

A media stack's natural trajectory is to fill any disk given to it. Nothing in
the default configuration pushes back: the \*arrs acquire what they're told to,
downloads accumulate, torrents seed indefinitely, and unpacked archives leave
copies behind.

A full disk is the worst common failure because it breaks everything at once —
downloads stall, imports fail, service databases can't write, and some corrupt.
Recovery is manual and the cause is often unclear.

## Behaviour

### Projection, not just measurement

Free space is a lagging indicator. What matters is free space against **what's
already committed** — the queue, active downloads, and seeding obligations.

Warning arrives when exhaustion is predicted, not when it happens.

### Consumption is attributed

"You have 40 GB free" prompts the question the operator can't easily answer:
*what's using the rest?* So it's broken down by category, and by the things that
are actually reclaimable:

| Category | Reclaimable? |
|----------|-------------|
| Library, by media type | Only by deleting content |
| Active downloads | No — in progress |
| Completed downloads still seeding | Yes, at the cost of ratio |
| Completed downloads no longer needed | **Yes — usually the easy win** |
| Orphaned files unknown to any \*arr | **Yes — pure waste** |
| Extracted archives where the source remains | **Yes** |
| Service data and logs | Marginally |

The three marked as easy wins are typically where a surprisingly large amount of
space has quietly gone.

### Cleanup is suggested, never automatic

lemonfiber identifies reclaimable space and offers to reclaim it. It does not
delete anything on its own. Automatic deletion of media is unacceptable — the
operator may have obtained something irreplaceable, and no heuristic is worth
that risk.

Seeding torrents get special care: removing them affects ratio and standing on
private trackers, which can carry real consequences. Never removed without the
tracker implication stated.

### Hardlink awareness prevents wrong answers

With hardlinks working, a file appearing in both `downloads/` and `media/`
occupies space **once**. Naive summation double-counts it and produces both wrong
totals and misleading cleanup suggestions.

Space accounting must be inode-aware, or every figure it reports is wrong on a
correctly configured system.

### Thresholds escalate

| Level | Behaviour |
|-------|-----------|
| Advisory | Noted on the dashboard |
| Warning | Notified; cleanup suggested |
| Critical | Notified urgently; pausing new acquisitions offered |
| Exhausted | Acquisitions halted to protect service databases |

Halting at exhaustion is a safety measure: a database that cannot write may
corrupt, turning a space problem into a data-loss problem.

## States

| State | Meaning |
|-------|---------|
| `ample` | Comfortable headroom |
| `advisory` | Below comfortable, not urgent |
| `warning` | Projected to exhaust within the horizon |
| `critical` | Nearly exhausted |
| `exhausted` | Full; acquisitions halted |
| `unknown` | Usage cannot be determined |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Hardlinks in use | Count shared inodes once. Report logical and physical usage distinctly. |
| Data root on a different volume from service config | Track both; either filling causes failure. |
| Network volume reporting stale figures | Report the reading time; don't present cached figures as live. |
| Space freed externally | Re-evaluate promptly; clear the condition. |
| Seeding torrents dominate usage | Report separately with the ratio implication, never bundled with generic cleanup. |
| Very large single item | Highlight it — a 90 GB remux is often unintentional. |
| Snapshots or versioning on the filesystem | Deletion may not free space immediately. State it where detectable. |
| Quota rather than physical limit | Report the effective limit, not the underlying device size. |
| Multiple libraries on one volume | Attribute per library so the operator knows where growth is. |
| Cleanup would break seeding | State the ratio consequence and require confirmation. |
| Orphaned files that are intentional | Respect the unmanaged marker from [C7](../c-trust/c7-queue-health.md). |
| Disk fills mid-import | Halt, report the partial state, and offer cleanup before retrying. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **D5-R1** | Exhaustion MUST be projected from committed content, not reported only when free space is low. |
| **D5-R2** | Space accounting MUST be inode-aware so hardlinked content is counted once. |
| **D5-R3** | Logical and physical usage MUST be reported distinctly where they differ. |
| **D5-R4** | Consumption MUST be attributed by category, identifying what is reclaimable. |
| **D5-R5** | lemonfiber MUST NOT delete media automatically under any threshold. |
| **D5-R6** | Cleanup affecting seeding torrents MUST state the ratio consequence and require confirmation. |
| **D5-R7** | Thresholds MUST escalate, and exhaustion MUST halt new acquisitions to protect service databases. |
| **D5-R8** | Both the data root and the service config volume MUST be monitored. |
| **D5-R9** | Stale readings from network volumes MUST be reported with their reading time. |
| **D5-R10** | Space freed externally MUST clear the condition promptly. |
| **D5-R11** | Filesystem quotas MUST be reported in preference to underlying device capacity. |
| **D5-R12** | Unusually large individual items MUST be highlighted. |
| **D5-R13** | A disk filling mid-import MUST halt, report the partial state, and offer cleanup before retry. |
| **D5-R14** | Files marked intentionally unmanaged MUST NOT be reported as orphaned waste. |

## Related

- [C5 Storage management](../c-trust/c5-storage.md) — the underlying filesystem contract
- [C7 Queue health](../c-trust/c7-queue-health.md) — orphan detection
- [D2 Quality presets](d2-quality-presets.md) — the largest lever on consumption
- [B5 Notifications](../b-running/b5-notifications.md)
