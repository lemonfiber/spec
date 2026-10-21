# Repo: `lemonfiber-media-stack`

**Status:** Accepted

The stack's manifest, its service files, each part's starting configuration and the
recordings its claims are proved against. TOML, Hippocratic 3.0.

**Implements:** the stack side of [B1](../10-functional/features/b-running/b1-forms.md),
the [manifest contract](../20-architecture/contracts/stack-manifest.md), and
[F2](../10-functional/features/f-extensibility/f2-service-catalogue.md).

---

lemonfiber writes the stack's Compose project from `stack.toml` and the service files it
includes
([ADR-0043](../00-overview/decisions/0043-the-core-writes-every-compose-entry-from-one-typed-service-model.md)),
and this repository holds no Compose file. The repository retires once nothing reads
it ([ADR-0042](../00-overview/decisions/0042-the-bundle-is-first-party-plugins-pinned-and-embedded.md)
§6), and what follows describes the repository as it stands.

## What this repo is

The stack's manifest, its service files, each part's starting configuration and the
recordings its claims are proved against, until each moves to its part's plugin. What
runs, with lemonfiber or without it, is the project lemonfiber writes, from the files it
names and the `.env` beside it (`F1-R1`).

`lemonfiber` embeds this repo as a submodule pinned to a commit
([ADR-0005](../00-overview/decisions/0005-embedded-stack-assets.md)), but the two
develop and version independently.

## Layout

```
lemonfiber-media-stack/
├── stack.toml                  the manifest's root — see contract
├── services/
│   └── <id>.toml               one file per service, named by stack.toml's `include`
├── .env.example                every variable the operator sets, documented inline
├── config/                     seeded config templates
│   ├── recyclarr/recyclarr.yml
│   ├── homepage/{services,widgets,settings}.yaml
│   ├── caddy/Caddyfile
│   └── door/Caddyfile
├── recordings/                 the answers each claim is proved against
├── scripts/                    the checks CI runs
├── README.md                   running the project lemonfiber writes, without it
└── .github/                    CI
```

## The service inventory

23 services, all verified `linux/arm64` + `linux/amd64`. Every one lemonfiber
does not build is OSI-licensed (2026-07); the request gate and the decline
service, whose images lemonfiber builds from its own code, carry
`Hippocratic-3.0` (`F2-R5`). Full descriptions in
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
| `media` | jellyfin, door, seerr, request-gate, decline, calibre-web-automated, audiobookshelf, navidrome |
| `tuning` | recyclarr, unpackerr |
| `dash` | homepage |
| `proxy` | caddy |

## The rules a service file must obey

These are not style preferences — each is enforced, and each has a spec requirement
behind it:

| Rule | Why | Requirement |
|------|-----|-------------|
| One profile per service | Profiles are facts, forms are intent | `B1-R1` |
| No `depends_on`; the one start-order edge is `network.via` | Any subset must boot | `B1-R14`, `ARCH-R236` |
| A service declares whether it takes data, and lemonfiber writes the one `/data` mount | Hardlinks | `ADR-0006`, `ARCH-R227` |
| Pinned by index digest, a non-floating tag beside it | Nothing changes because time passed | `E1-R1` |
| `bind` matches the manifest's tier | Two-tier security | `C6-R1`, `C6-R2` |
| Kernel capabilities come from a shape; only Gluetun takes `egress-guard` | Least privilege | `ARCH-R237`, `C6` |
| qBittorrent runs inside the egress guard's network, `network = { via = "network.egress-guard" }` | Killswitch isolation | `C2-R12` |

### The single-mount rule, concretely

A service file says only whether the service takes data; lemonfiber writes the
mount, once, at `/data`:

```toml
# services/sonarr.toml
takes_data = true
```

There is no field for a second mount beneath the data root, so the split that
silently turns every import into a copy cannot be written (`C5-R5`).

## NAS mode

In [NAS mode](../10-functional/features/c-trust/c5-storage.md) lemonfiber writes
each library service's `/data` as an NFS-backed volume from the operator's export.
Making the \*arrs copy instead of hardlink is an application setting, written over
each app's API during seeding, not something the project does.

## CI

| Check | Enforces |
|-------|----------|
| Manifest validation | The full [contract](../20-architecture/contracts/stack-manifest.md#validation) ruleset, the service model's container rules among it (`ARCH-R246`) |
| A change's own diff | A moved pin carries a reviewed date, a removal its reason (`F2-R13`, `F2-R14`) |
| SPDX licence check | Every service OSI-licensed, or `Hippocratic-3.0` where its image is under `ghcr.io/lemonfiber/` (`F2-R5`) |
| arm64 + amd64 index per pin | `F2-R6`, `E1-R1` |
| Every claim against its recordings | Judged by lemonfiber's own judge at a pinned commit (`ARCH-R137`) |
| Every profile starts | The project the lemonfiber binary writes, started with plain `docker compose` (`F1-R1`, `REPO-R93`) |
| The door refuses what it must | Started at the addresses the project fixes, in front of a stand-in for the media server (`D11-R2`) |
| Negative tests for each manifest rule | `REPO-R37` |

### The checks are themselves tested

A lint nobody has watched fail is a lint nobody knows works, and a green gate
over a stack that already complies proves nothing — it goes on proving nothing
until the first violating change merges. Each rule therefore has a negative test
that breaks exactly that rule in a throwaway copy of the stack and asserts the
violation is reported (`REPO-R37`). The same reasoning as the comment policy's
fixture tree (`Q-R7`), applied to configuration.

CI has the lemonfiber binary, built from the judge's commit with this tree laid
over the stack it embeds, write the project, starts the profile groups
`scripts/check_runs.py --plan` names with plain `docker compose` in its directory,
and checks each service answers the probe `stack.toml` declares. A profile that
cannot start without real credentials or a real provider is named in
`check_runs.py` with the reason and left out: `torrent`, whose gluetun needs a VPN
tunnel and whose qbittorrent waits on gluetun.

## Adding a service

Three data edits, no Rust (`F1-R5`):

1. A `[[service]]` in `services/<id>.toml` — its container in the service model, ports,
   health, api, criticality, licence.
2. Its file added to `include` in `stack.toml`.
3. Its profile added to whichever forms should carry it.

lemonfiber writes its Compose entry, and CI holds it to every rule above. This is
the whole of [J8](../10-functional/journeys/j8-customising.md)'s "add a service"
path.

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R16** | *Superseded by [ARCH-R224](../20-architecture/contracts/plugin-manifest.md): lemonfiber generates the stack's Compose project from its manifest, and the stack carries no Compose file of its own. The number is not reused.* |
| **REPO-R17** | *Superseded by [ARCH-R246](../20-architecture/contracts/stack-manifest.md): there is no Compose file in the stack for CI to resolve; each service is held to the manifest's validation. The number is not reused.* |
| **REPO-R18** | *Superseded by [ARCH-R246](../20-architecture/contracts/stack-manifest.md): the manifest is the only description of a service, so there is no second one to hold it to. The number is not reused.* |
| **REPO-R19** | *Superseded by [ARCH-R246](../20-architecture/contracts/stack-manifest.md) and [ARCH-R227](../20-architecture/contracts/plugin-manifest.md): there is no `depends_on` and no second data mount to declare, and a floating tag is refused by the manifest's own validation (`E1-R1`). The number is not reused.* |
| **REPO-R20** | CI MUST verify every service declares an OSI licence, or `Hippocratic-3.0` where lemonfiber builds its image from its own code (`F2-R5`), and publishes arm64 + amd64 images. |
| **REPO-R21** | *Superseded by [ARCH-R251](../20-architecture/contracts/capability-contracts.md): the egress guard's filler reports the forwarded port and the core sets it on the torrent client, so no up/down command pair or script is mounted into the guard. The number is not reused.* |
| **REPO-R22** | Port forwarding MUST default off and activate only for capable providers. |
| **REPO-R23** | Adding a service MUST require only data edits — its service file, the manifest's `include`, forms — and no code change. |
| **REPO-R34** | *Superseded by [ARCH-R224](../20-architecture/contracts/plugin-manifest.md): there is no `compose.yml` and no fragment to assemble. The number is not reused.* |
| **REPO-R35** | *Superseded by [ARCH-R224](../20-architecture/contracts/plugin-manifest.md): every service is in the one project lemonfiber generates. The number is not reused.* |
| **REPO-R36** | *Superseded by [ARCH-R246](../20-architecture/contracts/stack-manifest.md): the manifest is checked as it is read, and there is no Compose model beside it. The number is not reused.* |
| **REPO-R37** | Every stack rule enforced in CI MUST have a negative test that breaks the rule and asserts the violation is reported. |
| **REPO-R38** | *Superseded by [ARCH-R251](../20-architecture/contracts/capability-contracts.md): the port crosses through the core over two contracts, the guard holds none of the client's credentials, and a port that could not be set is said to be unpassed. The number is not reused.* |
| **REPO-R93** | The stack's CI MUST run each service's pinned image under the posture its manifest declares, `standard` unless it declares `confined` ([ARCH-R234](../20-architecture/contracts/plugin-manifest.md)), and MUST refuse a change under which one fails to start or to pass its health check; the version that first writes the stack's services from the model MUST NOT ship before every image has passed. |

**Affected repos** (`GOV-R7`): `lemonfiber-media-stack`.

## Related

- [stack-manifest contract](../20-architecture/contracts/stack-manifest.md)
- [F2 Service catalogue](../10-functional/features/f-extensibility/f2-service-catalogue.md)
- [C2](../10-functional/features/c-trust/c2-vpn-verification.md) · [C5](../10-functional/features/c-trust/c5-storage.md)
- [J8 Customising](../10-functional/journeys/j8-customising.md)
