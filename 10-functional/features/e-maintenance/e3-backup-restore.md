# E3 — Backup & restore

**Status:** Accepted · **Audience:** Operator · **Area:** E — Maintenance

---

## Purpose

Make configuration recoverable, so it stops being precious.

This underwrites [P6](../../../00-overview/vision.md#p6--reproducible-over-precious).
An operator who cannot recover from a mistake will not experiment, will not
update, and will not touch a working system. Fear of breaking things is what
leaves stacks running years-old versions.

Backup here means **configuration**, not media. The library may be terabytes and
is often irreplaceable, but it is not what breaks — what breaks is the small,
intricate, hard-to-recreate state in the service databases.

## Behaviour

### Databases are quiesced before capture

Every \*arr uses SQLite. Copying an SQLite database while it's being written
produces a file that may restore into a subtly corrupt state — which is worse
than no backup, because the failure appears at restore time when it's most needed.

Services are stopped, or their own backup mechanism used where one exists, before
their state is captured. Correctness outranks convenience here.

### What is captured

| Included | Excluded |
|----------|----------|
| Service configuration and databases | Media library |
| lemonfiber configuration and expected-state baseline | Downloads in progress |
| Materialised stack files and local modifications | Container images |
| Credentials **(marked sensitive)** | Logs beyond a recent window |

### Backups containing credentials are labelled as such

A configuration backup holds the VPN key, provider passwords and every API key.
It is exactly as sensitive as the credentials inside it, and operators routinely
forget this — copying a backup to cloud storage without a thought.

The label is stated at creation and recorded in the archive.

### Automatic before risky operations

Taken automatically before updates ([E1](e1-stack-updates.md)), before adopting
an existing setup ([A5](../a-getting-started/a5-migration.md)), and before
configuration removal ([A6](../a-getting-started/a6-uninstall.md)). Not offered —
taken.

### Restore is selective

Whole-stack restore is the common case, but restoring a single service is often
what's actually wanted — one \*arr's configuration mangled while the rest is fine.

### Restore verifies before replacing

The archive is validated, its version compatibility checked, and its contents
listed before anything is overwritten. A restore that fails partway is far worse
than one that refuses to start.

### Retention is bounded and predictable

A stated number of backups is kept, oldest pruned. Backups are useless if they
silently fill the disk they were protecting.

## States

| State | Meaning |
|-------|---------|
| `none` | No backups exist |
| `current` | A recent backup exists |
| `stale` | Newest backup predates significant changes |
| `creating` | Capture in progress |
| `verifying` | Validating an archive before restore |
| `restoring` | In progress |
| `restore-failed` | Failed; prior state described |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Services cannot be stopped | Use each service's own backup mechanism where available; otherwise report reduced confidence rather than capturing a live database silently. |
| Insufficient disk for a backup | Detect before starting. |
| Restore from a newer lemonfiber version | Refuse; state the version gap. |
| Restore from a much older version | Attempt with a compatibility warning; a schema-incompatible archive must be refused rather than half-applied. |
| Archive corrupt | Detect during verification, before overwriting anything. |
| Restore while the stack is running | Stop affected services first; state what will stop. |
| Restore with a different data root | Detect the path difference and offer to re-point rather than restoring paths that don't exist. |
| Backup includes credentials no longer valid | Restore them; report which fail validation afterwards. |
| Operator wants media backed up | Out of scope. State it and point at general-purpose backup tools — pretending to solve it badly is worse. |
| Backup taken mid-update | Only meaningful pre- or post-update; take it before, never during. |
| Partial restore leaves inconsistency | Re-run [seed](../d-content/d1-seed.md) after restore to reconcile inter-service wiring. |
| Retention would delete the only backup | Never prune to zero. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **E3-R1** | Service databases MUST be quiesced or captured via the service's own backup mechanism; a live SQLite file MUST NOT be copied silently. |
| **E3-R2** | Backups MUST include service configuration, lemonfiber configuration, the expected-state baseline, and materialised stack files. |
| **E3-R3** | Backups MUST NOT include the media library. |
| **E3-R4** | Backups containing credentials MUST be labelled sensitive at creation and within the archive. |
| **E3-R5** | A backup MUST be taken automatically before updates, adoption, and configuration removal. |
| **E3-R6** | Restore MUST support whole-stack and single-service scope. |
| **E3-R7** | An archive MUST be verified and its contents listed before anything is overwritten. |
| **E3-R8** | A corrupt or incompatible archive MUST be refused before modification begins. |
| **E3-R9** | Restore from a newer lemonfiber version MUST be refused with the version gap stated. |
| **E3-R10** | Restore to a different data root MUST detect the path difference and offer to re-point. |
| **E3-R11** | Retention MUST be bounded and MUST NOT prune the last remaining backup. |
| **E3-R12** | Insufficient disk space MUST be detected before capture begins. |
| **E3-R13** | Restore MUST report which restored credentials subsequently fail validation. |
| **E3-R14** | After restore, inter-service wiring MUST be reconciled by re-running seed. |
| **E3-R15** | A full backup of a typical configuration SHOULD complete within 60 seconds. |

## Related

- [E4 Rollback](e4-rollback.md) — the quick path for recent changes
- [E1 Stack updates](e1-stack-updates.md) — the mandatory pre-update backup
- [A6 Uninstall](../a-getting-started/a6-uninstall.md) · [A5 Migration](../a-getting-started/a5-migration.md)
- [A7 Credential management](../a-getting-started/a7-credential-management.md)
- [J6 Recovery](../../journeys/j6-recovery.md)
