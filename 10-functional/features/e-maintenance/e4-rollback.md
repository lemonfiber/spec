---
id: E4
title: Rollback
kind: feature
area: E
audience: operator
status: accepted
tracks: v1
labels: [updates]
relates: [A4, C3, C9, E1, E3]
---

# E4 — Rollback

**Status:** Accepted · **Audience:** Operator · **Area:** E — Maintenance

---

## Purpose

Undo a recent change quickly, without a full restore.

[E3](e3-backup-restore.md) recovers from disasters. Rollback handles the far more
common case: something was changed a few minutes ago and it made things worse. A
preset was adjusted, a service updated, a remediation applied, a data root moved.

Requiring a full restore for a small regret is heavy enough that operators don't
bother — they live with the regression, or they poke at it manually until the
state is something nobody designed. Making undo cheap is what makes the system
feel safe to touch.

## Behaviour

### Changes are journaled

Every change lemonfiber makes is recorded: what changed, from what to what, when,
and why. That journal is what makes targeted undo possible, and it doubles as an
answer to "what happened to my stack?"

### Rollback is per-change, not global

The operator reverts *the thing they regret*, not everything since a point in
time. Rolling back an update should not also revert an unrelated preset change
made afterwards.

### What can and cannot be rolled back is stated plainly

| Change | Rollback |
|--------|----------|
| Configuration values | Yes — restore prior values |
| Quality preset | Yes |
| Service version, **no migration** | Yes — repin and restart |
| Service version, **migration occurred** | **No** — requires restore from backup |
| Applied remediation | Yes, where it recorded prior state |
| Data root move | Partially — path re-pointed; moved data is not moved back automatically |
| Seed operations | Yes — prior values restored |
| Uninstall | No |

The migration row is the important one. Offering an action that cannot succeed is
worse than stating the limitation: the operator would attempt it, fail, and have
lost time in a moment of stress.

### The distinction is explained, not just enforced

When rollback is unavailable because a database migrated, lemonfiber says *why*
and points at the backup taken automatically before that update
([E1-R4](e1-stack-updates.md)) — which is precisely the situation that backup
exists for.

### Rollback is itself journaled

A rollback is a change, and can be rolled back. Undoing an undo must be possible;
operators overshoot.

### History is browsable

What changed, when, by which operation. Answers "why is this different from last
week?" without archaeology.

## States

Per journaled change:

| State | Meaning |
|-------|---------|
| `applied` | In effect |
| `reversible` | Can be rolled back automatically |
| `irreversible` | Cannot; reason stated |
| `partially-reversible` | Some aspects revert; others stated |
| `rolled-back` | Reverted |
| `superseded` | A later change replaced it; rolling back needs care |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Later change depends on the one being rolled back | Detect and report the dependency; require explicit confirmation or refuse. |
| Value changed manually since | Treat as drift ([C9](../c-trust/c9-drift.md)) — don't silently overwrite the operator's later edit. |
| Rollback target no longer valid | A prior image tag pulled from the registry can't be restored; report rather than fail obscurely. |
| Rollback of a data root move | Re-point configuration; state clearly that data itself is not moved back. |
| Journal unavailable or corrupt | Report that rollback is unavailable and direct to restore. |
| Very old change | Journal is bounded; state the horizon. |
| Rollback fails partway | Report the exact resulting state. Never leave it ambiguous. |
| Rollback of a change made by another tool | Not journaled, so not rollable. Report as unmanaged. |
| Service running during rollback | Stop, revert, restart; state what will be interrupted. |
| Rollback would reintroduce a known problem | Note it, and proceed if confirmed — the operator may have a reason. |
| Multiple changes in one operation | Roll back as a unit, since they were applied as one. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **E4-R1** | Every change lemonfiber makes MUST be journaled with prior value, new value, timestamp and originating operation. |
| **E4-R2** | Rollback MUST operate on individual changes, not only on points in time. |
| **E4-R3** | Each journaled change MUST be classified as reversible, irreversible, or partially reversible. |
| **E4-R4** | Rollback MUST NOT be offered where it cannot succeed. |
| **E4-R5** | Where rollback is unavailable due to a database migration, lemonfiber MUST state the reason and point at the pre-update backup. |
| **E4-R6** | A rollback MUST itself be journaled and MUST be rollable. |
| **E4-R7** | Rolling back a change with dependent later changes MUST detect the dependency and require confirmation or refuse. |
| **E4-R8** | A value manually changed since MUST be treated as drift and MUST NOT be silently overwritten. |
| **E4-R9** | Rolling back a data root move MUST state that data is not moved back. |
| **E4-R10** | An unavailable rollback target MUST be reported explicitly. |
| **E4-R11** | Journal history MUST be browsable, showing what changed and when. |
| **E4-R12** | A partially failed rollback MUST report the exact resulting state. |
| **E4-R13** | Journal retention MUST be bounded and the horizon MUST be stated. |
| **E4-R14** | Changes applied as one operation MUST roll back as one unit. |

## Related

- [E3 Backup & restore](e3-backup-restore.md) — the heavier recovery path
- [E1 Stack updates](e1-stack-updates.md) — where irreversibility originates
- [C3 Auto-remediation](../c-trust/c3-auto-remediation.md) — reversible fixes
- [C9 Drift detection](../c-trust/c9-drift.md) · [A4 Reconfiguration](../a-getting-started/a4-reconfiguration.md)
