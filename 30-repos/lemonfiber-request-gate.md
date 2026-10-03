# Repo: `lemonfiber-request-gate`

**Status:** Accepted

The request gate: the one image through which the request service reaches the
\*arrs and the media server. Rust, one crate, one image.

**Implements:** [ADR-0032](../00-overview/decisions/0032-the-request-service-reaches-the-arrs-through-a-gate.md),
for `C6-R20` to `C6-R25` and `D1-R19` to `D1-R21`. Its place in the organisation is
[ADR-0033](../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md).

---

## What this repo is

The source of `ghcr.io/lemonfiber/request-gate`, which the stack runs as the
service `request-gate`. It publishes no port, answers only Seerr, and builds each
call on its fixed list itself rather than forwarding what it was sent. It holds
the Sonarr and Radarr keys and a Jellyfin key, and the request service holds only
the gate's tokens.

## What it holds, and what it does not

| Holds | Does not hold |
|---|---|
| One Rust binary crate, with the core's lints, deny policy and coverage floor, depending on the core's crates at a pinned core commit | The compose entry or its networks, which are `lemonfiber-media-stack`'s |
| One Dockerfile, ending on a distroless static base as a non-root user | Any credential: keys and token hashes arrive as files the core writes |
| The call list, and recordings proving it against the pinned Seerr and every supported line | Code shared with `lemonfiber-decline` |
| The containment ADR-0032 requires, stated as what it needs from the stack | |

## Releasing

On the train ([ADR-0033](../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md) §3–§4).
Its entry in `repos.toml` carries `service = "request-gate"`, which is how the train
knows it. A version that lists this repository in `repos` tags it before the core:
at `v<version>`, and at `v<version>-<identifier>` for each pre-release. Each signed
tag builds `linux/amd64` and `linux/arm64` under one index with a software bill of
materials and a provenance attestation, and opens a pull request on
`lemonfiber-media-stack` setting the service's `tag` and `digest`. The core is tagged
at the same tag once the stack it embeds pins that digest. Nothing is published from
a branch.
