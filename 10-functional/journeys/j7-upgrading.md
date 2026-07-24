# J7 — Upgrading

**Status:** Accepted · **Audience:** Operator

**Exercises:** [E1](../features/e-maintenance/e1-stack-updates.md) ·
[E3](../features/e-maintenance/e3-backup-restore.md) ·
[E4](../features/e-maintenance/e4-rollback.md)

---

## The journey

```
$ lemonfiber update --check

  sonarr      4.0.15 → 4.0.16   patch
  jellyfin   10.10.3 → 10.11.0  minor · release notes ↗
  prowlarr    1.28.1 → 2.0.0    MAJOR · release notes ↗

  ⚠ Sonarr and Prowlarr migrate their databases on first start of a
    new version. Returning to the current versions afterwards is not
    possible.

    A backup will be taken automatically before updating.
```

## The one genuinely irreversible operation

The \*arrs migrate their SQLite schema on first start, and **there is no
downgrade path**. Pull a newer image, find it unusable, and you cannot simply
revert — the database has already been rewritten in a format the previous binary
refuses to open.

By default this is a one-word command with no warning. Stating it in advance
(`E1-R3`) is the single highest-value thing this journey does.

## Why versions are pinned at all

Nothing changes because time passed (`E1-R1`). An update happens when the
operator decides one should.

The alternative — floating tags — means an unrelated `pull` can jump six months
across a dozen services simultaneously, with no way back and no way to tell which
of twelve changes broke things.

## Backup is a precondition, not an offer

```
$ lemonfiber update

  Backing up…                     ✓ 41 MB · config-2026-07-24T19-12.tar
  sonarr    4.0.15 → 4.0.16       ✓ healthy in 6s
  prowlarr  1.28.1 → 2.0.0        ✗ failed to start

  Update halted. jellyfin was not updated.
  prowlarr is not healthy — see logs below.
```

Two properties doing real work:

- **If the backup fails, the update does not proceed** (`E1-R5`). The safety net
  is a precondition.
- **Services update one at a time, health verified between each** (`E1-R6`). A
  single failure is diagnosable; twelve simultaneous ones are not. The run halts
  rather than continuing into a half-migrated stack (`E1-R7`).

## What recovery looks like from here

| Situation | Path |
|-----------|------|
| Service updated, no migration | Rollback — repin and restart (`E4-R3`) |
| Service migrated its database | **Restore from the pre-update backup.** Rollback is refused, with the reason stated (`E4-R5`) |
| Update never started | Nothing to undo |

lemonfiber offers only the path that can actually work.

## Where it goes wrong

| Situation | Behaviour |
|-----------|-----------|
| Registry unreachable | Update check fails; stack untouched |
| Disk too full to pull | Detected before pulling — a failed pull from a full disk is confusing (`E1-R11`) |
| Downloads active | Reported, with an option to wait (`E1-R12`) |
| Only one service needs updating | Update just that one (`E1-R13`) |
| Operator wants to stay put indefinitely | Fully supported. **lemonfiber must not nag** (`E1-R14`) |
| Locally edited stack files | Never silently overwritten; a diff is shown (`E1-R9`) |

## Related

- [J6 Recovery](j6-recovery.md) — when an update goes wrong
- [E1 Stack updates](../features/e-maintenance/e1-stack-updates.md) · [E2 Self-update](../features/e-maintenance/e2-self-update.md)
- [A5 Migration](../features/a-getting-started/a5-migration.md) — why adoption refuses to downgrade
