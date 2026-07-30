---
id: E1
title: Stack updates
kind: feature
area: E
audience: operator
status: accepted
tracks: v1
milestone: M6
labels: [updates]
depends: [A5, C9, E2, E3, E4]
---

# E1 — Stack updates

**Status:** Accepted · **Audience:** Operator · **Area:** E — Maintenance

---

## Purpose

Move the stack forward without breaking it, and make the one genuinely
irreversible step visible before it's taken.

The \*arrs migrate their SQLite schema on first start of a new version, and there
is **no downgrade path**. An operator who pulls a newer image and finds it
unusable cannot simply revert — the database has already been rewritten in a
format the previous binary refuses to open.

This is the single most consequential maintenance operation in the stack, and by
default it is a one-word command with no warning.

## Behaviour

### Versions are pinned, so updating is deliberate

Images carry explicit version tags
([roadmap M1](../../../00-overview/roadmap.md)). Nothing changes because time
passed. An update happens when the operator decides it should.

The alternative — `:latest` everywhere — means an unrelated `pull` can jump six
months across a dozen services at once, with no way back.

### What's available is shown before anything is applied

Current version, available version, and the size of the jump. Where release notes
are reachable, they're linked. Where a version crosses a major boundary, that's
called out rather than left to be inferred from numbers.

### Irreversibility is stated in advance

Any update that will migrate a database says so, plainly, before proceeding:

> Sonarr 4.0.15 → 4.1.0 migrates its database on first start.
> Returning to 4.0.15 afterwards is not possible.
> A backup will be taken first.

### Backup is automatic and unconditional

Before any update that touches service state, a backup is taken
([E3](e3-backup-restore.md)). Not offered — taken. The operator can decline the
update, not the safety net.

If the backup fails, the update does not proceed.

### Updates are staged, not simultaneous

Services update one at a time with health verified between each. A failed update
stops the run rather than continuing into a half-migrated stack.

This costs time and is worth it: a single failure is diagnosable, whereas twelve
simultaneous ones are not.

### Rollback is offered where it's actually possible

For services that haven't migrated state, reverting is straightforward and
offered directly ([E4](e4-rollback.md)). Where migration has occurred, rollback
requires restoring the backup, and lemonfiber says which situation applies rather
than offering an action that cannot work.

### The stack definition updates too

New lemonfiber versions carry a new pinned stack ([ADR-0005](../../../00-overview/decisions/0005-embedded-stack-assets.md)).
Locally modified stack files are never silently overwritten — the operator is
shown a diff ([C9](../c-trust/c9-drift.md)).

## States

| State | Meaning |
|-------|---------|
| `current` | Everything at its pinned version |
| `updates-available` | Newer versions exist |
| `checking` | Querying registries |
| `backing-up` | Pre-update backup in progress |
| `updating` | Applying, service by service |
| `partial` | Some updated, one failed; run halted |
| `failed` | Update failed; prior state described |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Update available for one service only | Update just that one. Don't force a wholesale bump. |
| Major version jump | Highlight distinctly; major versions carry breaking changes far more often. |
| Update fails mid-run | Halt. Report exactly which services updated and which didn't. Never continue into unknown territory. |
| Backup fails | **Do not update.** The safety net is a precondition. |
| Registry unreachable | Report that update checking failed; leave the stack untouched. |
| Image pulled but service won't start | Report with logs; offer rollback if no migration occurred. |
| Downloads active during update | Report and offer to wait. Restarting a download client mid-transfer is usually recoverable but not always. |
| Update changes a default the operator relied on | Where detectable from release notes, call it out. Otherwise surface via [drift](../c-trust/c9-drift.md) afterwards. |
| Two services must move together | Where a dependency exists, update as a unit and say so. |
| Disk too full to pull | Detect before pulling; a failed pull from a full disk is confusing. |
| Update available for a service not in the active form | Show it; updating it is fine even when stopped. |
| Operator wants to stay on an old version indefinitely | Entirely supported. Pinning is the default posture, and lemonfiber MUST NOT nag. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **E1-R1** | All service images MUST be pinned to explicit versions; no service MAY track a floating tag. |
| **E1-R2** | Available updates MUST be shown with current version, target version, and the significance of the jump before anything is applied. |
| **E1-R3** | An update that will migrate service state MUST state that the change is irreversible before proceeding. |
| **E1-R4** | A backup MUST be taken automatically before any update touching service state. |
| **E1-R5** | If the pre-update backup fails, the update MUST NOT proceed. |
| **E1-R6** | Services MUST be updated one at a time with health verified between each. |
| **E1-R7** | A failed update MUST halt the run and MUST report which services were and were not updated. |
| **E1-R8** | Rollback MUST be offered only where it can actually succeed; where migration has occurred, restore MUST be indicated instead. |
| **E1-R9** | Locally modified stack files MUST NOT be overwritten without a diff and confirmation. |
| **E1-R10** | Major version transitions MUST be highlighted distinctly from minor and patch updates. |
| **E1-R11** | Insufficient disk space MUST be detected before pulling. |
| **E1-R12** | Active transfers MUST be reported before an update, with an option to wait. |
| **E1-R13** | Individual services MUST be updatable without updating others. |
| **E1-R14** | lemonfiber MUST NOT repeatedly prompt an operator who has chosen to remain on current versions. |

## Related

- [E3 Backup & restore](e3-backup-restore.md) — the mandatory safety net
- [E4 Rollback](e4-rollback.md) — undoing when possible
- [E2 Self-update](e2-self-update.md) — updating lemonfiber itself
- [C9 Drift detection](../c-trust/c9-drift.md) · [A5 Migration](../a-getting-started/a5-migration.md)
- [J7 Upgrading](../../journeys/j7-upgrading.md)
