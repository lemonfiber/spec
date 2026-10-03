# Repo: `lemonfiber-decline`

**Status:** Accepted

The decline service: the one image that answers an invitation's decline address.
Rust, one crate, one image.

**Implements:** [ADR-0029](../00-overview/decisions/0029-a-household-service-declines-an-invitation-with-one-key.md),
for `D6-R15`, `D6-R16` and `G5-R14`. Its place in the organisation is
[ADR-0033](../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md).

---

## What this repo is

The source of `ghcr.io/lemonfiber/decline`, which the stack runs as the service
`decline`. It answers three routes on its own origin, a page naming what would be
declined, the refusal, and its health, and makes three fixed Jellyfin calls with
the one API key minted for it alone.

## What it holds, and what it does not

| Holds | Does not hold |
|---|---|
| One Rust binary crate, with the core's lints, deny policy and coverage floor, depending on the core's crates at a pinned core commit | The compose entry, which is `lemonfiber-media-stack`'s |
| One Dockerfile, ending on a distroless static base as a non-root user | Any credential: the key and the invitation table arrive as files the core writes |
| Recordings of its three Jellyfin calls on every supported line (ADR-0028) | Code shared with `lemonfiber-request-gate` |
| The containment ADR-0029 §6 requires, stated as what it needs from the stack | |

## Releasing

On the train ([ADR-0033](../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md) §3–§4).
Its entry in `repos.toml` carries `service = "decline"`, which is how the train
knows it. A version that lists this repository in `repos` tags it before the core:
at `v<version>`, and at `v<version>-<identifier>` for each pre-release. Each signed
tag builds `linux/amd64` and `linux/arm64` under one index with a software bill of
materials and a provenance attestation, and opens a pull request on
`lemonfiber-media-stack` setting the service's `tag` and `digest`. The core is tagged
at the same tag once the stack it embeds pins that digest. Nothing is published from
a branch.
