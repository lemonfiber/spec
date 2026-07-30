---
id: C5
title: Storage & hardlink management
kind: feature
area: C
audience: operator
status: accepted
tracks: v1
milestone: M3
labels: [storage, verification]
depends: [A2, A4, C1, D5]
---

# C5 — Storage & hardlink management

**Status:** Accepted · **Audience:** Operator · **Area:** C — Trust & correctness

---

## Purpose

Make the filesystem contract real, and make its violation visible.

[P1](../../../00-overview/vision.md#p1--the-filesystem-contract-is-inviolable) says
downloads and media live under one mount so imports hardlink rather than copy.
When that breaks, nothing announces it. Imports still succeed. The library still
fills. The only symptoms are a disk consuming twice what it should and torrents
that can't seed from the library copy — both discovered late, usually when the
disk is full.

This feature turns an invisible property into a checked, reported one.

## Behaviour

### Hardlink capability is tested, never inferred

Create a file in the data root, hardlink it, stat both, compare inode and link
count, clean up. Filesystem *type* is a hint; a successful link is a fact.

The distinction matters because the exceptions are common: exFAT can't hardlink
at all, SMB mounts on macOS won't expose them usably, and Windows' WSL2 boundary
breaks them for anything on the Windows side.

### Storage mode follows from the result

| Mode | Condition | Consequence |
|------|-----------|-------------|
| `local` | Hardlinks work | Imports link. Instant, free, seeding preserved. |
| `external` | Hardlinks work on a removable or secondary volume | Same, plus availability monitoring |
| `nas` | Hardlinks unavailable across a network mount | Imports copy. \*arrs configured accordingly. |
| `degraded` | Expected to link but no longer can | Alert — something changed |

Mode is **derived from evidence**, not chosen from a menu. The operator picks a
location; lemonfiber determines what that location can do.

### Degradation is stated in consequences, not properties

"Hardlinks unsupported" means nothing to most operators. What it means is:

> Imports will copy instead of link. Each import takes minutes rather than
> being instant, uses twice the disk while it runs, and torrents can't seed from
> the library copy — you'd need to keep both.

Then the options: choose a different location, or continue in copy mode with the
\*arrs configured to match.

### The single-mount rule is enforced structurally

Every container receives one data mount with subdirectories beneath it. Splitting
`/downloads` and `/media` into separate mounts is the anti-pattern
([ADR-0006](../../../00-overview/decisions/0006-single-data-mount.md)) and is
rejected at manifest validation — not left to be discovered in production.

### Space is projected, not just reported

Free space alone is insufficient. What matters is free space against the size of
what's queued. Projected exhaustion is computed and alerted before it happens,
because a disk that fills mid-import leaves partial files and a stalled queue.

### Availability is monitored, not assumed

External drives get unplugged; network mounts drop. A data root that vanishes
while services run is dangerous — the \*arrs may write into the now-empty mount
point, creating a phantom library on the system disk. Detect it and stop.

### Ownership and permissions are checked

Files the operator can't read, or that services can't write, produce failures far
from their cause. Checked directly, with the platform's actual semantics — real
on native Linux, largely mapped away on Docker Desktop.

## States

| State | Meaning |
|-------|---------|
| `healthy` | Present, writable, hardlinks working, adequate space |
| `copy-mode` | Present and writable; hardlinks unavailable and configured for |
| `degraded` | Previously linking, now not |
| `space-critical` | Full or projected to fill imminently |
| `unavailable` | Data root not present |
| `permission-denied` | Present but not usable by the operator or services |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| exFAT volume chosen | Detect; explain hardlinks are impossible on exFAT and that this cannot be worked around. |
| SMB mount on macOS | Detect; explain the degradation and recommend NFS where available. |
| Windows path outside WSL2 | Detect the boundary crossing; explain that the data root should live inside the WSL2 filesystem. |
| Hardlinks worked, now don't | `degraded` and alert. Usually a remount with different options. |
| Data root disappears while running | Stop services rather than let them write into an empty mount point. |
| Data root reappears | Report; do not auto-start. The operator decides whether state is trustworthy. |
| Free space adequate, projection exhausts it | Alert on the projection, not just the current figure. |
| Space reclaimed by another process | Re-evaluate rather than staying alerted on stale data. |
| Permissions correct for operator, wrong for containers | Distinguish the two. Different causes, different remedies. |
| Case-insensitive filesystem | Detect; some libraries have names differing only by case. |
| Path contains characters a service can't handle | Detect at selection, not at first import. |
| Data root inside a Docker volume | Detect; explain reduced host visibility and backup implications. |
| Symlinked data root | Resolve it; hardlink tests must run against the real filesystem. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **C5-R1** | Hardlink capability MUST be determined by creating and inspecting a hardlink, never inferred from filesystem type. |
| **C5-R2** | Storage mode MUST be derived from the observed result, not selected by the operator. |
| **C5-R3** | Loss of hardlink capability MUST be expressed as consequences — import time, disk usage, seeding — not as a filesystem property. |
| **C5-R4** | Where hardlinks are unavailable, the \*arrs MUST be configured to copy, and this MUST be stated. |
| **C5-R5** | A manifest declaring more than one mount beneath the data root MUST fail validation. |
| **C5-R6** | Projected space exhaustion MUST be computed from queued content and alerted before it occurs. |
| **C5-R7** | Data root availability MUST be monitored while services run. |
| **C5-R8** | Loss of the data root MUST stop dependent services rather than allow writes into an empty mount point. |
| **C5-R9** | A reappearing data root MUST NOT trigger automatic restart. |
| **C5-R10** | Operator-facing and service-facing permission problems MUST be reported distinctly. |
| **C5-R11** | Loss of previously working hardlink capability MUST be detected and alerted. |
| **C5-R12** | The data root path MUST be validated for service compatibility at selection time. |
| **C5-R13** | A symlinked data root MUST be resolved before capability testing. |
| **C5-R14** | Platform-specific hardlink limitations — exFAT, SMB on macOS, the WSL2 boundary — MUST be detected and named specifically. |

## Related

- [ADR-0006 Single data mount](../../../00-overview/decisions/0006-single-data-mount.md)
- [A2 Setup wizard](../a-getting-started/a2-setup-wizard.md) — where the test first runs
- [A4 Reconfiguration](../a-getting-started/a4-reconfiguration.md) — moving the data root
- [C1 Diagnostics](c1-diagnostics.md) · [D5 Disk space](../d-content/d5-disk-space.md)
