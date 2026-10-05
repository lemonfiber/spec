---
id: L3
title: The image for a NAS
kind: feature
area: L
audience: operator
status: accepted
maturity: planned
labels: [release]
relates: [L1, C6, E2]
---

# L3 — The image for a NAS

**Status:** Accepted · **Audience:** Operator · **Area:** L — Release & distribution

---

## Purpose

Let somebody whose server is a NAS install lemonfiber the way they install everything else
on it: as a container from a template. Unraid, TrueNAS SCALE and Synology all start apps
from a container definition, and many of their owners never open a shell.

lemonfiber runs the stack through Docker, so the container needs the host's Docker socket.
That is the same power a native install gets from the `docker` group, and the image and its
templates say so plainly
([ADR-0038](../../../00-overview/decisions/0038-lemonfiber-ships-as-an-image-that-holds-the-hosts-docker.md)).

## Behaviour

### One image per release, built from that release's binary

Once the release workflow has built a release and left it as a draft, the core repository's
`release-image.yml` builds `ghcr.io/lemonfiber/lemonfiber` for `linux/amd64` and
`linux/arm64` from that release's own binaries, after checking each against its digest and
its attestation. It signs and attests the image as it does every other artefact
([L1](l1-release-engineering.md)), and puts the templates on the draft before it is
published. The image holds the binary and the two things it runs to drive the stack, the
Docker command line and its Compose plugin, and nothing else: no shell, no package manager, no
second process.

### A template per platform, attached to the release

Each release carries a template for Unraid (added by URL), a TrueNAS SCALE custom app, a
Synology Container Manager project, and plain Compose for Portainer and anything else. Each
names the image by its digest. They live in the core repository under `packaging/`, so a
template and the image it names are versioned together.

### The stack's directory has one path

Compose resolves a bind mount on the host, not in the container that asked. So the stack's
directory is mounted at the same path inside the container as it has on the host, and so is
the data location its services mount. lemonfiber asks Docker which host path stands behind
each one and refuses to start a stack when either differs, naming the mount. A check it
cannot make, because Docker cannot be reached or does not know the container, refuses too.

### The web surface keeps C6's binding

The container shares the host's network namespace rather than having one of its own.
lemonfiber reaches the stack's services on the host's loopback, where they publish their
ports, and a container's own loopback is not the host's. So the web surface, bound to
loopback as it is everywhere, is on the host's loopback. Offering it to the LAN is the
operator's choice, and lemonfiber still refuses a binding beyond loopback until a password is
set ([C6](../c-trust/c6-web-security.md)). The terminal UI is reached with `docker exec`.

### Updating means a new image

lemonfiber in the image never replaces its own binary. Where it would offer an update
([E2](../e-maintenance/e2-self-update.md)), it says to pull the new image and recreate the
container instead.

## Edge cases

| Situation | Behaviour |
|---|---|
| The stack directory is mounted at a different path inside | lemonfiber refuses to start the stack, naming the host path and the container path. |
| The socket is not mounted | lemonfiber says it cannot reach Docker and that the template mounts the socket, and starts nothing. |
| The NAS's Docker group has an unusual GID | The templates take the GID as a setting, so the container runs as that group rather than as root. |
| Somebody publishes the web port on the LAN with no password set | The surface stays loopback-bound inside, and lemonfiber says why (C6). |
| An update is offered inside the image | The command to pull and recreate is shown; nothing is replaced in place. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **L3-R1** | Each release MUST publish an image of lemonfiber for `linux/amd64` and `linux/arm64`, built by the release workflow from that release's own binaries, signed and attested as the release's other artefacts are. |
| **L3-R2** | The image MUST contain the lemonfiber binary and what it needs to run, and no shell, package manager or second process. |
| **L3-R3** | Templates for Unraid, a TrueNAS SCALE custom app, a Synology Container Manager project and plain Compose MUST be kept in the core repository under `packaging/`, MUST name the image by digest, and MUST be attached to each release. |
| **L3-R4** | lemonfiber running in the image MUST refuse to start a stack whose directory is not mounted at the same path inside the container as on the host, naming both paths. |
| **L3-R5** | The templates MUST mount the Docker socket, MUST run the container as the host's Docker group where the platform allows rather than as root, and they and the image's documentation MUST state that the socket gives the container control of the host's Docker. |
| **L3-R6** | The templates MUST publish the web surface on the host's loopback, and lemonfiber in the image MUST keep C6's refusal of a binding beyond loopback without a password. |
| **L3-R7** | The terminal UI MUST be usable through `docker exec`. |
| **L3-R8** | lemonfiber in the image MUST NOT replace its own binary, and where it would offer an update MUST give the command to pull the new image and recreate the container. |

## Related

- [L1 Release engineering](l1-release-engineering.md) — how the image is built and signed
- [C6 Web UI security & binding policy](../c-trust/c6-web-security.md) — the binding the templates keep
- [E2 Self-update](../e-maintenance/e2-self-update.md) — why the image defers
- [ADR-0038](../../../00-overview/decisions/0038-lemonfiber-ships-as-an-image-that-holds-the-hosts-docker.md)
