---
id: C1
title: Diagnostics
kind: feature
area: C
audience: operator
status: accepted
tracks: v1
---

# C1 — Diagnostics

**Status:** Accepted · **Audience:** Operator · **Area:** C — Trust & correctness

---

## Purpose

Answer "is this actually working?" with evidence rather than optimism.

Every serious failure mode in this ecosystem is **silent**. A VPN that failed
open still reports `Up`. Imports that degraded from hardlink to copy still
succeed. An indexer returning nothing looks identical to an indexer with nothing
to return. The stack reports green while doing the wrong thing, and the operator
finds out weeks later — from a full disk, a tracker ban, or a letter.

Diagnostics is the direct expression of
[P3](../../../00-overview/vision.md#p3--the-tool-proves-things-rather-than-assuming-them):
where a claim is checkable, check it.

## Behaviour

### Checks prove, they don't infer

A check that reads configuration and concludes "hardlinks should work" is
worthless. A check that creates a hardlink, stats it, and compares inode and link
count has established a fact.

| Weak | Strong |
|------|--------|
| Filesystem is APFS, so hardlinks work | Created a link; inode matched; link count 2 |
| Gluetun container is running | Compared public IP inside qBittorrent and Gluetun; identical |
| Port 8989 is configured | Bound it; it was free |
| API key is present | Called the API; it answered with the service identity |

### Every result carries a remedy

A finding without a remedy is a dead end. Findings state what was observed, what
it means, and what to do — per [G4](../g-ux/g4-error-model.md).

### Severity is honest

| Severity | Meaning |
|----------|---------|
| `pass` | Verified working |
| `warn` | Working, but degraded or risky |
| `fail` | Not working; something is broken |
| `unverified` | **Could not be checked.** Not a pass. |

`unverified` is the most important and the most often omitted. A killswitch that
hasn't been tested is not a working killswitch; reporting it green would be a
lie of exactly the kind this feature exists to prevent.

### Checks are independent

One check failing never prevents others from running. A stopped Docker daemon
makes container checks impossible, but filesystem and configuration checks still
run and still report.

### Runnable in whole or in part

The full suite, a single check, or a category. Checks are re-runnable at any
time and cheap enough to run often.

### Non-disruptive by default

Some checks can only be performed by disturbing the system — proving a killswitch
actually blocks traffic requires dropping the tunnel. Those are **opt-in**, never
part of a default run, and state what they will disturb and for how long.

### Check catalogue

| Category | Checks |
|----------|--------|
| **Environment** | Docker present, daemon reachable, Compose version, platform detected, virtualisation backend |
| **Storage** | Data root exists and is writable, single-filesystem, hardlink test, free space, projected exhaustion, permissions |
| **Network** | Port availability, port conflicts, service reachability, LAN binding matches policy |
| **VPN** | Tunnel up, egress match, forwarded port assigned, port matches client, killswitch *(disruptive)* |
| **Credentials** | Each credential still valid, freshness |
| **Services** | Health, crash loops, version skew, inter-service wiring intact |
| **Providers** | Quota remaining, subscription validity, indexer responsiveness |
| **Queue** | Stuck items, repeated import failures, orphaned downloads |
| **Config** | Drift from lemonfiber-managed state, file permissions, manifest validity |

### Machine-readable output

Diagnostics emit structured output as well as human output, so results can be
scripted, monitored, or attached to a [support bundle](c4-support-bundle.md).

## States

Per check: `pass`, `warn`, `fail`, `unverified`, `skipped` (not applicable).

Overall: `healthy` (all pass), `degraded` (warnings only), `broken` (any
failure), `unknown` (checks could not run).

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Docker daemon unreachable | Run every check that doesn't need it; mark the rest `unverified`, not `fail`. |
| Check times out | `unverified` with the elapsed time. Never hang the suite. |
| Check would disturb the system | Excluded from default runs; `unverified` with an explanation of how to run it. |
| Stack not running | Static checks still run. Runtime checks are `skipped`, not failures. |
| Check needs a credential that's absent | `skipped` with the reason, not `fail`. |
| Two checks find the same root cause | Report both, and indicate the shared cause so the operator fixes one thing rather than five symptoms. |
| Transient network failure | Retry once before reporting; distinguish transient from persistent. |
| Check itself errors unexpectedly | Report the check as errored. **A bug in diagnostics must never present as a finding about the stack.** |
| Disruptive check run while downloads are active | Warn about the interruption and require confirmation. |
| Very slow storage | Use generous timeouts for filesystem checks; a NAS is not a local SSD. |
| Operator runs diagnostics during setup | Supported and encouraged — setup uses the same checks. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **C1-R1** | Every check MUST establish its finding empirically, not infer it from configuration. |
| **C1-R2** | Every non-passing result MUST carry a remedy stating what to do. |
| **C1-R3** | `unverified` MUST be distinct from `pass`, and a check that could not run MUST NOT report as passing. |
| **C1-R4** | Checks MUST be independent; one failing MUST NOT prevent others running. |
| **C1-R5** | Checks that disturb the running system MUST be opt-in and MUST state what they disturb and for how long. |
| **C1-R6** | The suite, a category, or a single check MUST be individually runnable. |
| **C1-R7** | Every check MUST have a bounded timeout and MUST report `unverified` on expiry. |
| **C1-R8** | An error inside a check MUST be reported as a check error, never as a finding about the stack. |
| **C1-R9** | Diagnostics MUST emit machine-readable output alongside human-readable output. |
| **C1-R10** | Findings sharing a root cause MUST indicate that relationship. |
| **C1-R11** | Checks whose prerequisites are absent MUST report `skipped` with a reason, not `fail`. |
| **C1-R12** | A full non-disruptive run SHOULD complete within 30 seconds. |
| **C1-R13** | Setup MUST use the same checks as diagnostics, not a parallel implementation. |
| **C1-R14** | Filesystem check timeouts MUST accommodate network and external storage. |

## Related

- [C2 VPN verification](c2-vpn-verification.md) · [C5 Storage](c5-storage.md) · [C7 Queue health](c7-queue-health.md) · [C8 Provider health](c8-provider-health.md) · [C9 Drift](c9-drift.md)
- [C3 Auto-remediation](c3-auto-remediation.md) — acting on findings
- [G4 Error model](../g-ux/g4-error-model.md) · [G7 Health summary](../g-ux/g7-health-summary.md)
- [J5 VPN verification](../../journeys/j5-vpn-verification.md)
