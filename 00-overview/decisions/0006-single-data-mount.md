# ADR-0006: One `/data` mount, subdirectories beneath

**Status:** Accepted
**Date:** 2026-07-24

## Context

An *arr "imports" a completed download by moving it from the download client's
output directory into the media library. Whether that operation is cheap or
ruinous depends entirely on how the paths are mounted.

The intuitive layout — separate mounts for what are conceptually separate things —
looks tidy and is **wrong**:

```yaml
# ANTI-PATTERN
volumes:
  - ${DATA_ROOT}/downloads:/downloads
  - ${DATA_ROOT}/media:/media
```

Inside the container these are two distinct mount points, so the kernel treats
them as different filesystems even when they share a host volume. Consequences:

- `rename(2)` fails with `EXDEV`, so the *arr falls back to copy-then-delete.
- Import time scales with file size instead of being instant.
- Peak disk usage doubles during every import.
- **Seeding breaks**: the library copy is a different inode, so keeping the
  torrent seeding means keeping two full copies.

This failure is silent. Everything still "works" — it just quietly costs disk,
time, and ratio. It is the single most common misconfiguration in self-hosted
media stacks, and it is invisible until someone notices their disk is full.

## Decision

**Every container receives exactly one data mount**, with the split expressed as
subdirectories *inside* it:

```yaml
volumes:
  - ${DATA_ROOT}:/data
  - ./config/<service>:/config
```

```
${DATA_ROOT}/
├── downloads/
│   ├── usenet/{incomplete,complete/{tv,movies,music,books}}/
│   └── torrents/{incomplete,complete/{tv,movies,music,books}}/
└── media/{tv,movies,music,books}/
```

Config is a deliberately separate tree: small, precious, frequently written,
and with entirely different backup semantics from media.

This rule is **[P1](../vision.md#p1--the-filesystem-contract-is-inviolable)**,
and it outranks other considerations.

Three enforcement mechanisms:

1. **CI lint** on `lemonfiber-media-stack` rejects any service declaring more
   than one mount under `DATA_ROOT`.
2. **Setup wizard** creates a hardlink in the chosen data root and `stat`s it —
   an empirical test, not an assumption ([P3](../vision.md#p3--the-tool-proves-things-rather-than-assuming-them)).
3. **`lemonfiber doctor`** re-runs that test and reports degradation.

Where hardlinks are genuinely unavailable (exFAT, SMB, Windows drvfs), lemonfiber sets
storage mode accordingly and configures the *arrs to **Copy**, then states
plainly what was given up.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Separate `/downloads` and `/media` mounts** | The anti-pattern above. Tidier-looking, silently expensive. |
| **Single mount, but document the requirement** | Documentation doesn't prevent misconfiguration; it only assigns blame afterwards. |
| **Always copy; don't attempt hardlinks** | Predictable but wasteful, and gives up seeding entirely. |
| **Reflinks / CoW (btrfs, APFS clones)** | Excellent where available, but not portable across the three target platforms and not what the *arrs implement. Could complement hardlinks later. |

## Consequences

### Positive

- Imports are instant and free where the filesystem allows it.
- Torrents seed from the same bytes the library serves.
- One mount line per service; less to get wrong.
- Degradation is *detected and reported* rather than silently absorbed.

### Negative

- Users cannot put downloads and media on different physical disks — a real
  limitation for people with a fast SSD scratch disk and a slow bulk array. The
  honest answer is that they must choose between split disks and hardlinks;
  lemonfiber surfaces the choice rather than deciding silently.
- Paths inside containers (`/data/media/tv`) differ from host paths, which can
  confuse manual configuration. Mitigated by `lemonfiber seed` setting root folders
  automatically.

### Neutral

- Native-mode Jellyfin uses host paths instead of `/data` — handled by the mode
  switch in [ADR-0007](0007-dual-mode-jellyfin.md).

## Revisit if

- The *arrs gain portable reflink support.
- A credible design emerges for split-disk setups that preserves atomic imports.
