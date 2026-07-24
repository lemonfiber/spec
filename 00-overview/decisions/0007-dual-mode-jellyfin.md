# ADR-0007: Jellyfin supports both Docker and native modes

**Status:** Accepted
**Date:** 2026-07-24

## Context

Jellyfin transcodes when a client can't direct-play a file. Hardware
acceleration makes the difference between a 4K HDR stream working and pinning
every CPU core. Whether it's available **depends on the platform in a way that
cuts across our Docker-everything default**:

| Platform | Jellyfin in Docker | Jellyfin native |
|----------|-------------------|-----------------|
| **Linux** | ✅ Full HW accel via `/dev/dri` (VAAPI/QSV) or NVIDIA runtime | ✅ Same |
| **macOS** | ❌ **CPU only** — VideoToolbox is unreachable from the Docker VM | ✅ VideoToolbox |
| **Windows** | ❌ CPU only — WSL2 GPU passthrough for encode is unreliable | ✅ QSV/NVENC |

So the naïve rule "Docker means no hardware transcoding" is **false on Linux**,
where Docker is fully capable. Forcing native mode everywhere would be a
significant regression in deployment uniformity for Linux users, who are the
ones least likely to need it.

Meanwhile a macOS user with a 4K library has a legitimate need that Docker
cannot serve at all.

## Decision

**Support both, selected by a single `.env` variable.**

```bash
JELLYFIN_MODE=docker   # default
JELLYFIN_MODE=native   # host-installed
```

The insight making this cheap: **the only things that actually differ are a URL
and a path prefix.** Seerr and Homepage need `JELLYFIN_URL`; Jellyfin needs
to find the library.

| | `docker` | `native` |
|---|---|---|
| `JELLYFIN_URL` | `http://jellyfin:8096` | `http://host.docker.internal:8096` |
| Library path | `/data/media` | `${DATA_ROOT}/media` (host path) |
| Compose | `jellyfin` service active | `jellyfin` service **excluded** |
| Install | Pulled by Compose | `brew` / `apt` / MSI, by the user |

Native mode is a **subtraction, not a fork**: it drops one service from the
active profile set. Everything else is byte-identical. There is one compose file.

lemonfiber's responsibilities:
- Detect the platform and **only offer native mode where it buys something**
  (macOS/Windows). On Linux it recommends Docker and explains why.
- On native mode, add `extra_hosts: ["host.docker.internal:host-gateway"]` for
  native Linux Docker, where that name doesn't otherwise exist.
- Verify reachability in `doctor` — native mode's failure mode is Seerr
  silently unable to see Jellyfin.
- On Linux Docker mode, detect `/dev/dri` and enable passthrough if present.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Docker only** | Leaves macOS/Windows 4K users with an unusable experience and no path forward. |
| **Native only** | Throws away deployment uniformity for everyone, including Linux users who gain nothing. Also makes backup/upgrade a separate manual process. |
| **Two compose files** | They would drift. The delta is genuinely one URL and one path. |
| **Auto-detect and switch silently** | Violates least-surprise; installing Jellyfin natively is a user action with real consequences and must be a deliberate choice. |

## Consequences

### Positive
- Each platform gets its best option without forking the design.
- One compose file, one config tree, one mental model.
- Switching modes later is an `.env` edit plus a library re-point, not a rebuild.
- Linux users stop being told about a limitation that doesn't apply to them.

### Negative
- Native mode puts Jellyfin outside `lemonfiber up/down` — it can start, stop, and
  check health, but lifecycle belongs to the OS service manager. The dashboard
  must render this distinctly rather than pretending it's a container.
- Native mode installation is platform-specific and only partly automatable.
  lemonfiber prints exact commands rather than executing package managers on the
  user's behalf.
- Doubles the Jellyfin-related test matrix.

### Neutral
- Seerr, Homepage and Bazarr are unaffected — they consume `JELLYFIN_URL`
  and don't care what's behind it.

## Revisit if

- Docker Desktop gains GPU passthrough for encode on macOS or Windows, which
  would make native mode unnecessary.
