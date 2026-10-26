# Repo: `lemonfiber-decline`

**Status:** Accepted

The decline service: the one image that answers an invitation's decline address.
Rust, one crate, one image.

**Implements:** [ADR-0029](../00-overview/decisions/0029-a-household-service-declines-an-invitation-with-one-key.md),
for `D6-R15`, `D6-R16`, `D6-R21` and `G5-R14`. Its place in the organisation is
[ADR-0033](../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md).

---

## What this repo is

The source of `ghcr.io/lemonfiber/decline`, which the stack runs as the service
`decline`. It answers three routes on its own origin, a page naming what would be
declined, the refusal, and its health. Once a minute it takes back every invitation
whose window has closed. It makes five fixed Jellyfin calls with the one API key
minted for it alone, and changes an account in one of two ways: it switches it off,
or, under the guards ADR-0029 §2a states, removes it.

## What it holds, and what it does not

| Holds | Does not hold |
|---|---|
| One Rust binary crate, with the core's lints, deny policy and coverage floor, depending on the core's crates at a pinned core commit | The compose entry, which is `lemonfiber-media-stack`'s |
| One Dockerfile, ending on a distroless static base as a non-root user | Any credential: the key and the invitation table arrive as files the core writes |
| Recordings of its Jellyfin calls on every supported line (ADR-0028) | Code shared with `lemonfiber-request-gate` |
| The containment ADR-0029 §6 requires, stated as what it needs from the stack | |

## Releasing

On the train ([ADR-0033](../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md) §3–§4).
Its entry in `repos.toml` carries `service = "decline"`, which is how the train knows
it. Every version that cuts the core cuts this repository and tags it at `v<version>`
before the core, and no pre-release tags it (`OPS-R86`). Each signed tag builds
`linux/amd64` and `linux/arm64` under one index with a software bill of materials and
a provenance attestation, and opens a pull request setting the service's `tag` and
`digest` in the repository's own `plugin.toml`, which the catalogue's bundle takes at
that release once it merges. The core is tagged at the same tag once the bundle it
embeds pins that release and that digest. Every commit on `main` is published too, as
`main-<commit>`, and that manifest's pin moves to it on a rolling pull request, with
every recording the manifest names taken again from the new image and `proofs.json`
written from them; a commit image is not a release and the bundle is never moved to it
(`OPS-R90`, `OPS-R91`). A commit that changes nothing but that pin, its recordings,
its proofs and its `targets.toml` publishes nothing. Nothing else is published from a
branch.
