# Repo: `lemonfiber-media-stack`

**Status:** Archived

The repository that held the stack's manifest, its service files, each part's starting
configuration and the recordings its claims were proved against.

---

Every part it held is a first-party plugin's repository, pinned by the catalogue's
default bundle and embedded in the binary
([ADR-0045](../00-overview/decisions/0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md),
[the first-party plugins](first-party-plugins.md),
[bundle.toml](../20-architecture/contracts/bundle.md)). lemonfiber assembles the stack it
ships from that bundle; the train neither tags nor pins this repository; and a released
version's manifest still names it where that release cut it, searched it or embedded it
(`30-repos/repos.toml`'s `[[retired]]`).

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R16** | *Superseded by [ARCH-R224](../20-architecture/contracts/plugin-manifest.md): lemonfiber generates the stack's Compose project from its manifest, and the stack carries no Compose file of its own. The number is not reused.* |
| **REPO-R17** | *Superseded by [ARCH-R246](../20-architecture/contracts/stack-manifest.md): there is no Compose file in the stack for CI to resolve; each service is held to the manifest's validation. The number is not reused.* |
| **REPO-R18** | *Superseded by [ARCH-R246](../20-architecture/contracts/stack-manifest.md): the manifest is the only description of a service, so there is no second one to hold it to. The number is not reused.* |
| **REPO-R19** | *Superseded by [ARCH-R246](../20-architecture/contracts/stack-manifest.md) and [ARCH-R227](../20-architecture/contracts/plugin-manifest.md): there is no `depends_on` and no second data mount to declare, and a floating tag is refused by the manifest's own validation (`E1-R1`). The number is not reused.* |
| **REPO-R20** | *Withdrawn — every bundled part is a first-party plugin, held to [F2-R5](../10-functional/features/f-extensibility/f2-service-catalogue.md) and [F2-R6](../10-functional/features/f-extensibility/f2-service-catalogue.md) as every bundled service is, its images resolved on both platforms by its own CI ([REPO-R96](first-party-plugins.md)). The number is not reused.* |
| **REPO-R21** | *Superseded by [ARCH-R251](../20-architecture/contracts/capability-contracts.md): the egress guard's filler reports the forwarded port and the core sets it on the torrent client, so no up/down command pair or script is mounted into the guard. The number is not reused.* |
| **REPO-R22** | *Withdrawn — the egress guard is `plugin-gluetun`'s, whose manifest defaults port forwarding off, and what lemonfiber does with a provider's capability is [C2-R15](../10-functional/features/c-trust/c2-vpn-verification.md), [C2-R16](../10-functional/features/c-trust/c2-vpn-verification.md) and [C2-R18](../10-functional/features/c-trust/c2-vpn-verification.md). The number is not reused.* |
| **REPO-R23** | *Withdrawn — a part is added as a first-party plugin, a repository of its own and a pin in the bundle, with no change to lemonfiber's code ([F1-R5](../10-functional/features/f-extensibility/f1-customisation.md), [REPO-R94](first-party-plugins.md)). The number is not reused.* |
| **REPO-R34** | *Superseded by [ARCH-R224](../20-architecture/contracts/plugin-manifest.md): there is no `compose.yml` and no fragment to assemble. The number is not reused.* |
| **REPO-R35** | *Superseded by [ARCH-R224](../20-architecture/contracts/plugin-manifest.md): every service is in the one project lemonfiber generates. The number is not reused.* |
| **REPO-R36** | *Superseded by [ARCH-R246](../20-architecture/contracts/stack-manifest.md): the manifest is checked as it is read, and there is no Compose model beside it. The number is not reused.* |
| **REPO-R37** | *Withdrawn — the rules a part is held to are the plugin manifest's and the bundle contract's, enforced by each plugin's CI ([REPO-R96](first-party-plugins.md)) and the catalogue's ([REPO-R92](lemonfiber-plugins.md)). The number is not reused.* |
| **REPO-R38** | *Superseded by [ARCH-R251](../20-architecture/contracts/capability-contracts.md): the port crosses through the core over two contracts, the guard holds none of the client's credentials, and a port that could not be set is said to be unpassed. The number is not reused.* |

`REPO-R93`, running each image under its posture, is a first-party plugin's CI's, in
[the first-party plugins' requirements](first-party-plugins.md#requirements).

**Affected repos** (`GOV-R7`): `lemonfiber-media-stack`.

## Related

- [The first-party plugins](first-party-plugins.md)
- [`lemonfiber-plugins`](lemonfiber-plugins.md) and [the bundle contract](../20-architecture/contracts/bundle.md)
- [stack-manifest contract](../20-architecture/contracts/stack-manifest.md)
