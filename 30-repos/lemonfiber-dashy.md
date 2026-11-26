# Repo: `lemonfiber-dashy`

**Status:** Accepted

The image of the offered dashboard: Dashy, with a patch so that its server reaches only
the addresses its page names, and pings nothing. One Dockerfile and the patch.

**Implements:** `OPS-R93`. Its place in the organisation is
[an image lemonfiber builds](README.md#an-image-lemonfiber-builds-has-a-repository-of-its-own).

---

## What this repo is

The source of `ghcr.io/lemonfiber/dashy`, which [`plugin-dashy`](first-party-plugins.md)
runs as the upstream its adapter speaks `dashboard.show` for. Dashy's own image answers
anybody who reaches the page: `/cors-proxy` forwards any request to any address, and
`/status-check` and `/ping-check` reach any host. On a page the household reaches without
signing in, that is a way into every service on the stack's internal network. This image
holds `/cors-proxy` and `/status-check` to the addresses the page names (each entry's
status check and each status-page widget's two addresses), and its `/ping-check` refuses
every host.

## What it holds, and what it does not

| Holds | Does not hold |
|---|---|
| One Dockerfile, from Dashy's image pinned by digest | The plugin's manifest, its recordings or its adapter, which are `plugin-dashy`'s |
| The patch, a unified diff of Dashy's server applied with `patch --forward` in a build stage, so a Dashy whose code the patch no longer fits fails the build | Any credential |

## Releasing

Every commit on `main` that changes what the image is built from builds `linux/amd64`
and `linux/arm64` under one index with a software bill of materials and a provenance
attestation, tagged `main-<commit>`, and moves `plugin-dashy`'s pin to it on a rolling
pull request there, with every recording its manifest names taken again from the new
image (`OPS-R93`). Its entry in `repos.toml` carries `pinned_in = "plugin-dashy"`, which
is how that is known. The train never tags this repository: `plugin-dashy`'s release
pins the image its `main` holds, as any plugin pins its upstream.
