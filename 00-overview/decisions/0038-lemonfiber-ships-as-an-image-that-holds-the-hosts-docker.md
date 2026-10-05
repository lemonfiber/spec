# ADR-0038: lemonfiber ships as an image that holds the host's Docker

**Status:** Accepted
**Date:** 2026-10-05
**Decided:** 2026-10-05, by the maintainer, Wessel Verheij: an image built by the release, with the socket and the stack's directory mounted at one path, and templates for Unraid, TrueNAS SCALE, Synology and Compose kept in the core repository.

## Context

A NAS is a common home for a media stack, and its owners install software as containers
from templates. lemonfiber runs the stack by driving Docker. A container of lemonfiber
therefore needs the Docker socket, and the socket is control of the host's Docker: whoever
holds it can start a privileged container that mounts the host's root.

Two facts bound the decision. A native install already holds that power, because running
Docker without root means membership of the `docker` group, which is the same socket. And
Compose resolves every bind mount on the host, so a lemonfiber inside a container that hands
Compose a path it sees inside writes the stack against a path the host may not have.

## Decision

**The release publishes an image, and its templates mount the socket and keep one path.**

1. The image is built by the release workflow from the release's own binaries, for
   `linux/amd64` and `linux/arm64`, and is signed and attested as every artefact is
   ([L1](../../10-functional/features/l-release/l1-release-engineering.md)). It holds the
   binary and nothing else, so the socket is reachable by lemonfiber alone rather than by a
   shell somebody could open beside it.
2. The stack's directory is mounted at the same path inside as outside, and lemonfiber
   refuses to start a stack when it is not. A path Compose resolves is then the path
   lemonfiber meant.
3. The templates live in the core repository under `packaging/` and name the image by
   digest, so a template and its image cannot drift apart across releases. They run the
   container as the host's Docker group, not as root, where the platform allows.
4. The socket's power is stated in the templates and in the documentation, in those words.
   It is not wrapped in something that implies less.

## Alternatives considered

**A socket proxy that filters the Docker API.** Compose must create containers with bind
mounts, which is itself root on the host, so the filter would let through the one thing
worth stopping. Rejected as a restriction that would mainly be for show.

**No image, and a guide per NAS for the static binary.** The least to secure, but it asks
the people this is for to use the shell they chose a NAS to avoid.

**Templates in their own repository.** Workable with digests, but it puts a second
repository on the release train for files that change only when the image does.

## Consequences

- [L3](../../10-functional/features/l-release/l3-nas-image.md) gains its requirements.
- The container shares the host's network namespace. lemonfiber reaches the stack's
  services on the host's loopback, and a container's own loopback is not the host's, so the
  templates run it on the host's network and the web surface's loopback binding is the
  host's loopback.
- The image carries the Docker command line and its Compose plugin beside the binary,
  because lemonfiber drives the stack by running `docker compose`.
- Self-update defers inside the image, as it does under a package manager
  ([E2](../../10-functional/features/e-maintenance/e2-self-update.md)).
- App-store listings (Unraid Community Applications, the TrueNAS catalogue) are requests to
  other projects, and this organisation does not make those. The templates are offered from
  our own releases, by URL.
