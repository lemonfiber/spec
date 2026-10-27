# Repo: `lemonfiber-caddy`

**Status:** Accepted

The image of the proxy: Caddy, rebuilt without the file capability its own image carries
on its binary, so it starts under `standard`. One Dockerfile and its configuration.

**Implements:** `OPS-R93`. Its place in the organisation is
[ADR-0033](../00-overview/decisions/0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md).

---

## What this repo is

The source of `ghcr.io/lemonfiber/caddy`, which [`plugin-caddy`](first-party-plugins.md)
runs as the upstream its adapter speaks `proxy.front` for. It listens on 8080 and 8443, which the stack publishes as 80 and 443.

## What it holds, and what it does not

| Holds | Does not hold |
|---|---|
| One Dockerfile, from Caddy's image pinned by digest | The plugin's manifest, its recordings or its adapter, which are `plugin-caddy`'s |
| The configuration the image starts with | Any credential |

## Releasing

Every commit on `main` builds `linux/amd64` and `linux/arm64` under one index with a
software bill of materials and a provenance attestation, tagged `main-<commit>`, and
moves `plugin-caddy`'s pin to it on a rolling pull request there, with every recording
its manifest names taken again from the new image (`OPS-R93`). Its entry in
`repos.toml` carries `pinned_in = "plugin-caddy"`, which is how that is known. The train
never tags this repository: `plugin-caddy`'s release pins the image its `main` holds,
as any plugin pins its upstream.
