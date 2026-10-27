# Repo: `lemonfiber-door`

**Status:** Accepted

The image of the guarded door: Caddy, rebuilt without the file capability its own image carries
on its binary, so it starts under `standard`. One Dockerfile and its configuration.

**Implements:** `OPS-R93`. Its place in the organisation is
[ADR-0033](../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md).

---

## What this repo is

The source of `ghcr.io/lemonfiber/door`, which [`plugin-door`](first-party-plugins.md)
runs as the upstream its adapter speaks `stream.guard` for. Its configuration is the guard's: it serves the media server's byte routes over TLS and refuses what no question about an item covers.

## What it holds, and what it does not

| Holds | Does not hold |
|---|---|
| One Dockerfile, from Caddy's image pinned by digest | The plugin's manifest, its recordings or its adapter, which are `plugin-door`'s |
| The configuration the image starts with | Any credential |

## Releasing

Every commit on `main` builds `linux/amd64` and `linux/arm64` under one index with a
software bill of materials and a provenance attestation, tagged `main-<commit>`, and
moves `plugin-door`'s pin to it on a rolling pull request there, with every recording
its manifest names taken again from the new image (`OPS-R93`). Its entry in
`repos.toml` carries `pinned_in = "plugin-door"`, which is how that is known. The train
never tags this repository: `plugin-door`'s release pins the image its `main` holds,
as any plugin pins its upstream.
