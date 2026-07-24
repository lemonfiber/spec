# J6 — Recovering after breaking something

**Status:** Accepted · **Audience:** Operator

**Exercises:** [D1](../features/d-content/d1-seed.md) ·
[E3](../features/e-maintenance/e3-backup-restore.md) ·
[E4](../features/e-maintenance/e4-rollback.md) ·
[C9](../features/c-trust/c9-drift.md)

**Target:** back to working in under two minutes.

---

## The journey

```
$ lemonfiber down
$ rm -rf ~/.local/share/lemonfiber/config
$ lemonfiber up tv
$ lemonfiber seed

  ✓ api keys extracted        5 services
  ✓ download clients          sabnzbd, qbittorrent → sonarr
  ✓ root folders              /data/media/tv
  ✓ prowlarr app sync         sonarr
  ✓ bazarr                    sonarr, radarr
  ✓ seerr                jellyfin (identity), sonarr
  ✓ homepage keys written

  Seeded in 41s.
```

**Media is untouched throughout.** Only configuration is regenerated.

## Why this journey is load-bearing

It underwrites [P6](../../00-overview/vision.md#p6--reproducible-over-precious),
and P6 exists because of a behavioural problem, not a technical one: **an
operator who can't recover won't experiment.** They won't update, won't try a
different quality preset, won't touch a working system. That's why so many
self-hosted stacks run years-old versions — not laziness, but rational fear.

Making recovery cheap changes what the operator is willing to do.

## Three depths of recovery

| Depth | Use | Cost |
|-------|-----|------|
| **Rollback** ([E4](../features/e-maintenance/e4-rollback.md)) | Undo one recent change | Seconds |
| **Restore** ([E3](../features/e-maintenance/e3-backup-restore.md)) | Return to a known-good state | ~1 minute |
| **Rebuild** (above) | Regenerate from nothing | ~2 minutes |

Rebuild is the deepest, and it works because seeding is deterministic — the
wiring is derived from configuration, not accumulated by hand.

## The tension this journey sits on

Rebuild regenerates **lemonfiber's** view of configuration. So what happens to
the evening the operator spent tuning Sonarr's quality profiles?

Without an answer, P6 (reproducible) actively destroys
[F1](../features/f-extensibility/f1-customisation.md) (customisable) — two
individually-correct features producing a trust-destroying outcome.

The answer is [C9](../features/c-trust/c9-drift.md): a three-way comparison
between what lemonfiber last wrote, what's actually there, and what it would
write now. **A value differing from lemonfiber's baseline, where its intent
hasn't changed, is an operator edit and is preserved** (`C9-R4`).

After a full rebuild there's no baseline to compare against — so hand-tuning that
matters should be adopted into the baseline (`C9-R6`), which is what makes it
survive.

## Where it goes wrong

| Situation | Behaviour |
|-----------|-----------|
| A service isn't running | Seed skips it and says so; re-running completes it (`D1-R6`) |
| Seed interrupted partway | Every completed connection is valid; re-run finishes the rest (`D1-R13`) |
| Backup restored from a newer version | Refused, with the version gap stated (`E3-R9`) |
| Restore to a different data root | Path difference detected; offers to re-point rather than restoring paths that don't exist (`E3-R10`) |
| Rollback target no longer available | Reported explicitly, not failed obscurely (`E4-R10`) |
| Rollback of a database-migrating update | **Refused** — points at the pre-update backup instead (`E4-R5`) |

That last row matters: offering an action that cannot succeed would cost the
operator time in a moment of stress.

## Related

- [J7 Upgrading](j7-upgrading.md) — where backups are taken automatically
- [J8 Customising](j8-customising.md) — the work drift protects
- [E3](../features/e-maintenance/e3-backup-restore.md) · [E4](../features/e-maintenance/e4-rollback.md) · [C9](../features/c-trust/c9-drift.md)
