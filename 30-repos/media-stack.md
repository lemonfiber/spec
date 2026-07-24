# Repo: `media-stack`

**Status:** Accepted

The Docker Compose definitions, service profiles, manifest, and app configs.
YAML/TOML, Hippocratic 3.0.

**Implements:** the stack side of [B1](../10-functional/features/b-running/b1-forms.md),
the [manifest contract](../20-architecture/contracts/stack-manifest.md), and
[F2](../10-functional/features/f-extensibility/f2-service-catalogue.md).

---

## What this repo is

A **standalone, runnable Compose project**. Cloned and run with plain
`docker compose --profile tv up`, it works with no `lemonfiber` binary anywhere
(`F1-R1`). That is the load-bearing property of this repo, not a side effect: it
is what makes adopting lemonfiber a reversible decision.

`lemonfiber` embeds a pinned tag of this repo as a submodule
([ADR-0005](../00-overview/decisions/0005-embedded-stack-assets.md)), but the two
develop and version independently.

## Layout

```
media-stack/
├── compose.yml                 all 19 services, one profile each
├── stack.toml                  the manifest — see contract
├── .env.example                every variable documented inline
├── stacks/
│   ├── compose.storage.nas.yml overlay: NAS/copy mode
│   └── compose.proxy.yml        overlay: Caddy
├── config/                     seeded config templates
│   ├── recyclarr/recyclarr.yml
│   ├── homepage/{services,widgets,settings}.yaml
│   └── caddy/Caddyfile
├── README.md                   standalone usage, no lemonfiber
└── .github/                    CI
```

## The service inventory

19 services, all verified `linux/arm64` + `linux/amd64`, all OSI-licensed
(2026-07). Full descriptions in
[F2](../10-functional/features/f-extensibility/f2-service-catalogue.md); the
canonical data is in `stack.toml`.

| Profile | Services |
|---------|----------|
| `search` | prowlarr, flaresolverr, nzbhydra2 |
| `usenet` | sabnzbd |
| `torrent` | gluetun, qbittorrent |
| `tv` / `movies` / `music` | sonarr / radarr / lidarr |
| `books` | bindery |
| `subs` | bazarr |
| `media` | jellyfin, seerr, calibre-web-automated, audiobookshelf |
| `tuning` | recyclarr, unpackerr |
| `dash` | homepage |
| `proxy` | caddy |

## The rules `compose.yml` must obey

These are not style preferences — each is enforced by CI and each has a spec
requirement behind it:

| Rule | Why | Requirement |
|------|-----|-------------|
| One profile per service | Profiles are facts, forms are intent | `B1-R1` |
| No `depends_on` across a profile boundary | Any subset must boot | `B1-R14` |
| Exactly one `${DATA_ROOT}:/data` mount per service | Hardlinks | `ADR-0006` |
| Pinned image tags, never floating | Nothing changes because time passed | `E1-R1` |
| `bind` matches the manifest's tier | Two-tier security | `C6-R1`, `C6-R2` |
| Only Gluetun holds `NET_ADMIN` | Least privilege | `C6` |
| qBittorrent uses `network_mode: service:gluetun` | Killswitch isolation | `C2-R12` |

### The single-mount rule, concretely

```yaml
# ✓ required
volumes:
  - ${DATA_ROOT}:/data
  - ./config/sonarr:/config

# ✗ CI rejects — two mounts under DATA_ROOT breaks hardlinks
volumes:
  - ${DATA_ROOT}/downloads:/downloads
  - ${DATA_ROOT}/media:/media
```

The second form looks tidier and silently turns every import into a copy. CI's
manifest lint rejects it (`C5-R5`).

### The VPN wiring, concretely

```yaml
gluetun:
  cap_add: [NET_ADMIN]
  devices: ["/dev/net/tun:/dev/net/tun"]
  environment:
    VPN_SERVICE_PROVIDER: ${VPN_PROVIDER}
    VPN_TYPE: wireguard
    VPN_PORT_FORWARDING: ${VPN_PORT_FORWARDING:-off}
    VPN_PORT_FORWARDING_PROVIDER: ${VPN_PROVIDER}
    VPN_PORT_FORWARDING_UP_COMMAND: >-
      /bin/sh -c 'wget -qO- --post-data
      "json={\"listen_port\":{{PORT}}}"
      http://127.0.0.1:8081/api/v2/app/setPreferences'
    VPN_PORT_FORWARDING_DOWN_COMMAND: >-
      /bin/sh -c 'wget -qO- --post-data
      "json={\"listen_port\":0}"
      http://127.0.0.1:8081/api/v2/app/setPreferences'

qbittorrent:
  network_mode: "service:gluetun"
  depends_on: [gluetun]
```

Two things worth stating, both verified against Gluetun's own docs:

- **The `UP_COMMAND`/`DOWN_COMMAND` pair is how the dynamic forwarded port
  reaches qBittorrent** — on acquire *and* on release. The DOWN command is not
  optional: without it qBittorrent won't re-acquire correctly after a reconnect
  (`C2-R19`).
- **`VPN_PORT_FORWARDING` defaults to `off`** and is enabled only for
  port-forwarding-capable providers. On NordVPN, Mullvad and the rest it stays
  off, and the port machinery simply doesn't run (`C2-R16`).

## Storage overlay

`stacks/compose.storage.nas.yml` adjusts mounts and drops hardlink-dependent
wiring for [NAS mode](../10-functional/features/c-trust/c5-storage.md), where the
\*arrs are configured to copy. Applied via `--stack-dir` composition or by
lemonfiber when it detects the mode.

## CI

| Check | Enforces |
|-------|----------|
| `docker compose config` per form | Every form is structurally valid |
| Manifest ↔ compose parity | Every service in one is in the other (`stack.toml` contract) |
| Manifest validation | The full [contract](../20-architecture/contracts/stack-manifest.md#validation) ruleset |
| No cross-profile `depends_on` | `B1-R14` |
| Single-mount lint | `ADR-0006` |
| No floating tags | `E1-R1` |
| SPDX licence check | Every service OSI-licensed (`F2-R5`) |
| arm64 + amd64 manifest present | `F2-R6` |

CI does **not** boot the stack — that needs real credentials and providers.
Structural validity is what's checkable in CI; end-to-end runs are an M1 exit
criterion done by hand.

## Adding a service

Three data edits, no Rust (`F1-R5`):

1. A service block in `compose.yml`, one profile.
2. A `[[service]]` in `stack.toml` — ports, health, api, criticality, licence.
3. Add its profile to whichever forms should carry it.

CI then holds it to every rule above. This is the whole of
[J8](../10-functional/journeys/j8-customising.md)'s "add a service" path.

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R16** | The stack MUST run under plain `docker compose` with no lemonfiber binary. |
| **REPO-R17** | CI MUST validate every form with `docker compose config`. |
| **REPO-R18** | CI MUST verify manifest ↔ compose parity. |
| **REPO-R19** | CI MUST reject cross-profile `depends_on`, multi-mount services, and floating tags. |
| **REPO-R20** | CI MUST verify every service declares an OSI licence and publishes arm64 + amd64 images. |
| **REPO-R21** | The VPN port-forwarding up/down command pair MUST push and release the client's listen port. |
| **REPO-R22** | Port forwarding MUST default off and activate only for capable providers. |
| **REPO-R23** | Adding a service MUST require only data edits — compose, manifest, forms — and no code change. |

## Related

- [stack-manifest contract](../20-architecture/contracts/stack-manifest.md)
- [F2 Service catalogue](../10-functional/features/f-extensibility/f2-service-catalogue.md)
- [C2](../10-functional/features/c-trust/c2-vpn-verification.md) · [C5](../10-functional/features/c-trust/c5-storage.md)
- [J8 Customising](../10-functional/journeys/j8-customising.md)
