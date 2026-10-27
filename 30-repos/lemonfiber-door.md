# Repo: `lemonfiber-door`

**Status:** Accepted

The guarded door: the one service the household reaches the media server's bytes
through, holding each request to the declaration the core applies. Rust, one crate, one
image.

**Implements:** `OPS-R93`, and fills `stream.guard` (`ARCH-R207`, `ARCH-R303`,
`ARCH-R304`) as its own upstream (`ARCH-R344`), as
[ADR-0056](../00-overview/decisions/0056-the-guarded-door-is-a-rust-service-that-checks-the-request-it-forwards.md)
decides. Its place in the organisation is
[ADR-0033](../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md).

---

## What this repo is

The source of `ghcr.io/lemonfiber/door`, which [`plugin-door`](first-party-plugins.md)
runs as the service `door`. It serves the media server's household ports, plain and
encrypted with the certificate the core writes, and speaks `stream.guard@1` on a
contract port of its own (`ARCH-R343`). Each request's target is checked as its bytes
arrived and as it reads decoded once, against the normal form, the token's presentation,
the refused paths, the byte and live paths and the parameters naming another item; the
question is asked of the media server or the pass service as the declaration says; and
what goes on is the target that was checked, byte for byte.

## What it holds, and what it does not

| Holds | Does not hold |
|---|---|
| One Rust binary crate, with the core's lints, deny policy and coverage floor, depending on the core's crates at a pinned core commit | The manifest and its recordings, which are `plugin-door`'s |
| Unit tests of every check, with a corpus of the normal form's edges | Any media server's routes: what it enforces is the declaration it is applied |
| One Dockerfile, ending on a distroless static base as a non-root user | Any credential: a member's token is passed on, never kept |

## Releasing

A commit on `main` that changes what the image is built from builds `linux/amd64` and
`linux/arm64` under one index with a software bill of materials and a provenance
attestation, tagged `main-<commit>`, and moves `plugin-door`'s pin to it on a rolling
pull request there, with every recording its manifest names taken again from the new
image (`OPS-R93`). Its entry in `repos.toml` carries `pinned_in = "plugin-door"`, which
is how that is known. The train never tags this repository, and `plugin-door` builds no
image, so the bundle pins the revision of `plugin-door` whose manifest pins this image.
