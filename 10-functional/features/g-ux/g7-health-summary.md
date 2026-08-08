---
id: G7
title: Overall health summary
kind: feature
area: G
audience: operator
status: accepted
tracks: v1
labels: [verification, ux]
requires: [B5]
relates: [B3, C1, G4]
---

# G7 — Overall health summary

**Status:** Accepted · **Audience:** Operator · **Area:** G — Cross-cutting UX

---

## Purpose

Answer "is it working?" in one line.

The operator's most frequent question has, at present, only an expensive answer:
read nineteen container states, check the VPN, look at the queue, check disk, and
synthesise. That's a skilled judgement, made repeatedly, and it's exactly the work
a tool should do.

Nineteen green dots is not an answer — it's raw material. And it's misleading,
because the failures that matter here don't turn a dot red. A leaking VPN, imports
degraded to copies, and a queue jammed for three days all present as a fully green
service list.

## Behaviour

### One line, at the top, always

```
✓ Everything's fine · 12 services · 3 downloading · 480 GB free
```

```
! 2 things need attention · VPN leak detected · disk 94% full
```

The healthy case is as important as the unhealthy one: an operator who can glance
and see everything is fine stops checking obsessively, which is what makes a
self-hosted system tolerable to live with.

### Severity of the summary is the highest severity present

One critical finding makes the summary critical, regardless of how much else is
healthy. Averaging or counting would let the one thing that matters be diluted by
eighteen things that don't.

### It reflects consequences, not component states

The summary is computed from the findings that actually affect the operator —
[diagnostics](../c-trust/c1-diagnostics.md), [VPN state](../c-trust/c2-vpn-verification.md),
[queue health](../c-trust/c7-queue-health.md), [provider capacity](../c-trust/c8-provider-health.md),
[disk](../d-content/d5-disk-space.md) — not from a count of running containers.

A stack with every container up and a leaking VPN is **not** fine, and must not
say it is.

### It expands to the detail

The summary is a starting point: the affected items are reachable from it, and
from there their remedies. Never a dead end.

### Consistent across every surface

The same summary, from the same computation, in the TUI, the web UI, and CLI
status. It's the product's single most repeated statement and must not vary by
where it's read.

### Unknown is not fine

Where health cannot be determined — telemetry unavailable, checks unable to run —
the summary says so. Reporting "everything's fine" when nothing could be verified
is the failure this entire product argues against.

### Available without a running stack

Even stopped, the summary states that clearly rather than reporting a degenerate
green.

## States

| State | Line reads |
|-------|-----------|
| `healthy` | Everything's fine |
| `advisory` | Everything's working, with notes |
| `attention` | *n* things need attention |
| `critical` | Urgent, naming the critical condition |
| `unknown` | Health can't be determined right now |
| `stopped` | Not running |
| `unconfigured` | Not set up yet |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Everything up, VPN leaking | `critical`. Container states are irrelevant to this. |
| Some checks can't run | `unknown` for that aspect; never absorbed into a green summary. |
| Many findings sharing one cause | Count causes, not symptoms. "1 thing needs attention" for a full disk producing eleven failures. |
| Stack deliberately stopped | `stopped`, not `critical`. |
| Only optional services failing | `advisory`, not `attention` — Homepage being down doesn't stop anything. |
| Findings acknowledged but unresolved | Reflect acknowledgement without pretending they're resolved. |
| Transient failure | Debounce, consistent with [B5](../b-running/b5-notifications.md). Don't flap the summary. |
| Very long list of conditions | Summarise by count and severity; the top item named. |
| Health computed during startup | `unknown` while services are starting, not `critical`. |
| Household member views it | They don't. This is an operator surface. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **G7-R1** | A single-line health summary MUST be available on every surface. |
| **G7-R2** | The summary MUST be computed from operator-affecting findings, not from a count of running containers. |
| **G7-R3** | The summary's severity MUST equal the highest severity present, never an average. |
| **G7-R4** | A stack with all containers running but a critical finding MUST NOT report as healthy. |
| **G7-R5** | Where health cannot be determined, the summary MUST report `unknown` and MUST NOT report healthy. |
| **G7-R6** | Findings sharing a root cause MUST be counted once. |
| **G7-R7** | The summary MUST expand to the affected items and their remedies. |
| **G7-R8** | The summary MUST be identical across surfaces, from one computation. |
| **G7-R9** | A deliberately stopped stack MUST report `stopped`, not a failure state. |
| **G7-R10** | Failures confined to non-essential services MUST report as advisory rather than requiring attention. |
| **G7-R11** | The summary MUST be debounced so transient conditions do not cause it to flap. |
| **G7-R12** | During startup the summary MUST report `unknown` rather than a failure state. |
| **G7-R13** | A healthy summary MUST be as clearly presented as an unhealthy one. |

## Related

- [C1 Diagnostics](../c-trust/c1-diagnostics.md) — the findings it summarises
- [B3 Dashboard](../b-running/b3-dashboard.md) — where it sits
- [G4 Error model](g4-error-model.md) — severity levels and cause grouping
- [B5 Notifications](../b-running/b5-notifications.md) — the same conditions, pushed
