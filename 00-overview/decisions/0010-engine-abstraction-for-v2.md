# ADR-0010: A container engine is a v2 detail, not a v1 assumption

**Status:** Proposed
**Date:** 2026-07-30

## Context

v1 made two coupled choices. [ADR-0001](0001-docker-compose-as-engine.md) fixed
**Docker Compose as the execution engine**, and the [vision](../vision.md#non-goals)
listed "Kubernetes / Podman / Nomad" as a non-goal — "Compose is correct at this
scale. Supporting more engines multiplies the platform matrix by three for no
user benefit." Both were right for v1: one engine kept the matrix small while the
product thesis (guided setup, forms, verification) was proven.

v2 reopens it deliberately. "Run without Docker" is a real, requested capability —
Docker Desktop's licensing on macOS/Windows, and a preference for a fully
open-source runtime, are legitimate reasons — and the ecosystem epoch is the
right place to pay the matrix cost.

What makes this non-obvious is that two v1 guarantees are **load-bearing and
engine-shaped**:

- **The VPN killswitch is topological.** The download client shares Gluetun's
  network namespace (`network_mode: service:gluetun`), so if the tunnel drops it
  has no route at all. Any engine must reproduce shared-namespace semantics, or
  the killswitch must be rebuilt from lower primitives.
- **Hardlinks require one filesystem.** This is a property of the mount, not the
  engine — it survives any runtime as long as the tree stays a single filesystem,
  the failure mode being user-namespace UID shifts, not the engine itself.

The freeing observation: **verification is engine-agnostic.** Comparing the
client's egress IP to the host's, and comparing inodes, are just commands run in
a namespace. If the tool can exec into a unit and read a socket, it can prove both
invariants no matter what runs them. That reframes "Docker-optional" as a
config-generation and capability problem, not a re-proof problem.

## Decision

For v2, introduce a **container-engine abstraction**: one control surface, several
engines, and the **same verification suite run unchanged on each**.

- **Docker Compose remains the default and reference engine.** ADR-0001 stands;
  this ADR qualifies its exclusivity, it does not supersede its choice.
- **Podman is the first alternative**, in two modes: drive the existing forms
  against Podman's Docker-compatible interface (max fidelity), and generate
  systemd-managed unit files (Quadlet) that reproduce the Gluetun-shared-namespace
  topology and health-gated ordering natively (Linux-only, boot-persistent).
- **A native, no-container profile** is offered as a power-user Linux path,
  rebuilding the killswitch from kernel primitives (a dedicated network namespace
  with the tunnel inside it and a kill rule), and re-proving it the same way.
- **The engine is behind an abstraction whose acceptance bar is the proofs**: an
  engine is supported only when the egress-IP proof and the inode proof pass on it.
- The vision non-goal is amended accordingly — from "one engine, by exclusion" to
  "one abstraction, several engines, the same proofs on each," for v2.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Stay single-engine (Docker only)** | Locks out fully open-source runtimes and forces Docker Desktop's licensing on macOS/Windows; the exact constraint v2 exists to relax. |
| **Kubernetes / Nomad** | Still overkill at a single-household scale; enormous matrix and concept cost for no user benefit. Remains a non-goal. |
| **containerd + nerdctl** | A strictly worse Podman for this stack: the same rootless-VPN pain, a thinner VPN ecosystem, no Quadlet-equivalent, and a weaker automation surface. |
| **Reimplement everything natively (drop containers entirely as the default)** | Throws away Gluetun's VPN-provider abstraction and multiplies authoring cost; correct only as an opt-in power-user profile, not the default. |
| **Abstract the engine but skip the proofs on alternatives** | Would let an engine silently break the killswitch — precisely the "looks fine, does the wrong thing" failure the whole project exists to prevent. |

## Consequences

### Positive

- The stack can run on a fully open-source runtime, and without Docker Desktop's
  licensing, on the engines people actually want.
- Quadlet gives a boot-persistent, journald-observable expression of the topology
  that maps the shared-namespace + health-gating relationship more precisely than
  Compose does.
- Because verification is engine-agnostic, the ethos ("prove it, don't assume it")
  extends to every engine at no conceptual cost.

### Negative

- The platform matrix grows. Rootless Podman conflicts with Gluetun's elevated
  network capability and tunnel device — the honest default is rootful (or a
  documented rootless recipe), with the tunnel re-proven on every start.
- The compose-shim's namespace handling is the weak seam; the resulting namespace
  must be verified at runtime, never trusted from the file.
- The native profile is high-effort and Linux-only (network namespaces do not
  exist on macOS), and it loses Gluetun's VPN-provider abstraction.

### Neutral

- On macOS and Windows every option is a Linux VM regardless — "Docker-optional"
  swaps Docker's VM for Podman's machine, it does not remove virtualization.
- The abstraction is a v2 addition; v1 remains single-engine and unaffected.

## Revisit if

- An engine cannot preserve both proofs (egress isolation and hardlinks), in which
  case it is not a supported engine rather than a reason to weaken the proofs.
- A future single runtime covers every target platform natively, which would make
  the abstraction layer redundant.
