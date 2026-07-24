# Platform matrix

**Status:** Accepted

Where the three platforms genuinely differ, and what lemonfiber must do about it.

Most cross-platform work is trivial — paths and line endings. The differences
below are not: each one changes behaviour, and getting any of them wrong produces
a silent failure rather than an error.

---

## The four environments

Three operating systems, but **four** environments, because Linux has two Docker
deployments that behave differently:

| Environment | Docker | Detection |
|-------------|--------|-----------|
| **macOS** | Docker Desktop (VM + VirtioFS) | `cfg!(target_os = "macos")` |
| **Linux native** | Docker Engine directly | Linux, no Desktop context |
| **Linux Desktop** | Docker Desktop (VM) | Linux, Desktop context reported by daemon |
| **Windows** | Docker Desktop (WSL2) | `cfg!(target_os = "windows")` |

Linux-native versus Linux-Desktop matters because file ownership is real in one
and mapped in the other — so `PUID`/`PGID` is load-bearing in one and cosmetic in
the other.

## The matrix

| Concern | macOS | Linux native | Linux Desktop | Windows (WSL2) |
|---------|-------|--------------|---------------|----------------|
| **Hardlinks** | ✅ APFS/HFS+ | ✅ ext4/btrfs/xfs | ✅ | ⚠️ **only inside WSL2** |
| **Jellyfin HW transcode in Docker** | ❌ | ✅ `/dev/dri` or NVIDIA | ✅ | ❌ |
| **Native Jellyfin worth offering** | ✅ VideoToolbox | ❌ pointless | ❌ pointless | ✅ QSV/NVENC |
| **`host.docker.internal`** | ✅ built in | ❌ **needs `host-gateway`** | ✅ | ✅ |
| **PUID/PGID** | cosmetic | **real** | cosmetic | cosmetic |
| **Docker autostart at login** | ❌ **manual** | ✅ systemd | ❌ manual | ❌ **manual** |
| **Docker API transport** | Unix socket | Unix socket | Unix socket | **named pipe** |
| **Bind-mount performance** | VirtioFS, good | native | VirtioFS | poor across the boundary |
| **`/dev/net/tun` for VPN** | ✅ | ✅ | ✅ | ✅ |

## The five that actually bite

### 1. The Windows data-root boundary

Docker Desktop on Windows runs via WSL2. A bind mount from a Windows path
(`C:\Media`) crosses the drvfs/9p translation layer, where **hardlinks do not work
correctly** and I/O is slow.

So on Windows the data root must live **inside** the WSL2 filesystem. This is not
a preference — the entire import model
([ADR-0006](../00-overview/decisions/0006-single-data-mount.md)) depends on it.

lemonfiber detects the boundary crossing during setup and explains it in
consequences rather than in filesystem terminology (`C5-R14`).

### 2. Hardware transcoding is a Linux-only Docker capability

The common claim "Docker means no hardware transcoding" is **false on Linux**,
where `/dev/dri` passthrough or the NVIDIA runtime works fully.

It's true on macOS and Windows, where the VM cannot reach the encoder.

Consequence: native-mode Jellyfin
([ADR-0007](../00-overview/decisions/0007-dual-mode-jellyfin.md)) is offered only
where it buys something (`A2-R7`). Offering it on Linux would add a deployment
model for no gain; withholding it on macOS would leave 4K users stuck.

### 3. `host.docker.internal` doesn't exist on native Linux

It's a Docker Desktop convenience. On native Linux Docker it must be added
explicitly:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Without it, native-mode Jellyfin silently fails to be reachable from Seerr — the
container cannot resolve the name, and the symptom is "Seerr can't see my
library" with nothing in any log explaining why.

### 4. Autostart differs three ways

The [reboot hole](../10-functional/features/b-running/b8-autostart.md):

| Platform | What must happen |
|----------|------------------|
| **macOS** | Docker Desktop set to open at login — **off by default** |
| **Linux native** | `docker.service` enabled — usually already true |
| **Linux Desktop** | Docker Desktop at login — off by default |
| **Windows** | Docker Desktop at login, WSL2 up first — off by default |

On three of four environments, the default is that **nothing comes back after a
reboot**, with no error anywhere. Container restart policies don't help, because
the daemon itself isn't running.

lemonfiber verifies the setting rather than assuming it, and reports
`enabled-unverified` where it cannot confirm (`B8-R3`, `B8-R4`) — the state where
an operator *believes* they have autostart and doesn't.

### 5. PUID/PGID flips from cosmetic to load-bearing

On Docker Desktop, file ownership is mapped by the VM's sharing layer and these
values change nothing observable. On native Linux Docker, they determine who owns
every file the stack writes — and getting them wrong produces permission failures
far from their cause.

So the wizard asks **only on native Linux** (`A2-R6`). Asking elsewhere would be
a question the operator cannot meaningfully answer, violating the rule that every
question must earn its place.

## Requirements

| ID | Requirement |
|----|-------------|
| **ARCH-R27** | lemonfiber MUST distinguish four environments, including Linux-native from Linux-Desktop. |
| **ARCH-R28** | On Windows, a data root outside the WSL2 filesystem MUST be detected and its consequence explained. |
| **ARCH-R29** | Native Jellyfin mode MUST be offered only where Docker cannot hardware-transcode. |
| **ARCH-R30** | On Linux, `/dev/dri` presence MUST be detected and passthrough enabled where available. |
| **ARCH-R31** | On native Linux Docker, `host.docker.internal` MUST be provided via `host-gateway` where native Jellyfin is used. |
| **ARCH-R32** | Autostart MUST be configured per environment, and the prerequisite verified rather than assumed. |
| **ARCH-R33** | PUID/PGID MUST be requested only on native Linux Docker. |
| **ARCH-R34** | The Docker API transport MUST adapt to named pipes on Windows and Unix sockets elsewhere. |
| **ARCH-R35** | Platform detection MUST be a single component; per-platform behaviour MUST NOT be scattered through call sites. |

**ARCH-R35** is the maintainability one: `cfg!` checks sprinkled across modules
are how a codebase becomes untestable on any single machine. One component
decides, everything else asks it — and it can be faked in tests, so all four
environments are exercisable from one laptop.

## Related

- [ADR-0006](../00-overview/decisions/0006-single-data-mount.md) · [ADR-0007](../00-overview/decisions/0007-dual-mode-jellyfin.md)
- [C5 Storage](../10-functional/features/c-trust/c5-storage.md) · [B8 Autostart](../10-functional/features/b-running/b8-autostart.md)
- [component-model.md](component-model.md) — where `platform` lives
