# Repo: `lemonfiber-fence`

**Status:** Accepted

The image of the fence: a small container that holds a fenced service's network namespace
and refuses every connection that service opens to a private address. One Dockerfile and
the program that installs the rules.

**Implements:** `ARCH-R363`. Its place in the organisation is
[ADR-0033](../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md).

---

## What this repo is

The source of `ghcr.io/lemonfiber/fence`, which lemonfiber runs beside each service that
declares [`network.fenced`](../20-architecture/contracts/plugin-manifest-service.md#fenced-from-every-private-address--networkfenced).
At start it installs nftables rules in the namespace it holds and reports healthy once
every rule is in place. The rules refuse new connections to loopback, the private and
carrier-grade NAT ranges, link-local and metadata addresses, multicast, IPv6 unique-local
and link-local, and each host address lemonfiber hands it. They pass the engine's
resolver and the answers to connections other services opened. It then holds the
namespace and does nothing else. It exits, and so reports unhealthy, where any rule
cannot be installed, so the service behind it never starts unfenced.

## What it holds, and what it does not

| Holds | Does not hold |
|---|---|
| One Dockerfile, from a base image pinned by digest | Any plugin's manifest, recordings or adapter |
| The program that installs the rules and holds the namespace | Any credential |
| Tests that start it and prove each range refused and the resolver passed | Any rule a manifest writes: the ranges are this image's alone |

## Releasing

It is on the release train, as every image lemonfiber builds for the stack is
([ADR-0033](../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md)):
a version that lists it tags it first, and the bundle's `[fence]` pin moves to the image
that tag published in the same release. Each image is built for `linux/amd64` and
`linux/arm64` under one index, with a software bill of materials and a provenance
attestation. Its entry in `repos.toml` carries `service = "fence"`, which is how the
train knows it.
