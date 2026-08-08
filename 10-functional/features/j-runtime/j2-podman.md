---
id: J2
title: Running under Podman
kind: feature
area: J
audience: operator
status: draft
tracks: v2
milestone: M12
priority: P2
labels: [runtime, network, verification]
relates: [J1, C2, C5]
---

# J2 — Running under Podman

**Status:** Draft · **Audience:** Operator · **Area:** J — Runtime & platform

---

## Purpose

Run the whole stack without Docker at all, on Podman — an open-source runtime
with no proprietary daemon — and prove that swapping the runtime out did not break
the two things the tool exists to guarantee: that the VPN is not leaking and that
imports hardlink. Podman is the ethos-pure default alternative precisely because
it carries no closed coordination layer; the bar for offering it is that both
proofs pass under it, not merely that services start.

## Behaviour

### Two authoring modes

lemonfiber can run the stack on Podman two ways, and the operator chooses:

| Mode | What it is | Where |
|------|-----------|-------|
| **Compatibility** | The existing forms and compose descriptions are driven against Podman's Docker-compatible interface, for maximum fidelity to the bundled topology | Any host with Podman |
| **Native units** | System-managed unit files reproduce the topology natively, boot-persistent and supervised by the init system | Linux only |

### Native units reproduce the topology, not just the containers

The native-unit mode generates systemd-managed unit files (Quadlet-style) that
express the relationships the stack depends on, not just a set of containers:

- **Shared network namespace** — the download client joins the VPN container's
  network namespace, so its only route out is through the tunnel. This
  relationship is reproduced explicitly in the units, not left to chance.
- **Health-gated ordering** — a service starts only once its dependency is
  reported HEALTHY, not merely started. "Started" is not "ready", and the
  ordering waits for ready.
- **Boot persistence** — the units survive reboot and are brought back by the
  init system without the operator re-running anything.

### It proves the tunnel on every start, in either mode

The VPN egress proof and the hardlink inode proof both run under Podman, in both
modes, and both must pass. The egress proof compares the download client's
observed public address against the host's and asserts they differ via the
tunnel; the hardlink proof creates, links, and compares inodes on the real data
root. Because the compose-compatibility shim is the weak seam for
network-namespace handling, the namespace is verified at runtime from inside the
running client — never inferred from the unit or compose file having asked for it.

### It is honest about rootless

Rootless Podman conflicts with what the VPN container needs — an elevated network
capability and access to the tunnel device. lemonfiber leads with a rootful
recipe (or a documented, explicitly-tested rootless recipe) rather than pretending
rootless is free, and re-proves the tunnel on every start rather than assuming a
recipe that worked once still holds. Where user-namespace UID shifting would break
hardlinks, it aligns UIDs across the boundary and proves the result with a
filesystem check rather than trusting the mapping.

### Every step has a non-interactive equivalent

Choosing the mode, generating the native units, and running the egress and
hardlink proofs under Podman are all reachable as plain subcommands.

## States

| State | Meaning |
|-------|---------|
| `compat-live` | Stack running via the Docker-compatible interface; both proofs passing |
| `units-live` | Native unit files installed and running under the init system; both proofs passing |
| `rootless-blocked` | Rootless configuration cannot grant the tunnel device or network capability; steered to rootful or the tested rootless recipe |
| `namespace-unverified` | The shared network namespace could not be confirmed at runtime; treated as unproven, not assumed good |
| `uid-misaligned` | User-namespace UID shifting is breaking hardlinks; imports would copy until UIDs are aligned |
| `units-unavailable` | Native-unit mode requested on a non-Linux host; unsupported and said so |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Rootless Podman cannot open the tunnel device | Report the conflict; lead with the rootful recipe or the documented tested rootless one, never a silent partial start. |
| Compatibility shim maps the shared namespace differently | Verify the namespace from inside the running download client at runtime; do not trust the compose file's request. |
| User-namespace UID shift breaks hardlinks | Align UIDs across the boundary and prove with a create-link-stat inode check; if it still copies, say so rather than reporting linked. |
| Native-unit mode requested off Linux | Refuse it and explain that system unit files are a Linux mechanism; offer the compatibility mode instead. |
| Health-gated ordering starts a dependant too early | Gate on HEALTHY, not on started; a dependant must wait for readiness, and a stuck dependency must surface, not cascade. |
| Reboot brings units back in the wrong order | The ordering and health gates must reassert on boot; re-prove the tunnel after boot rather than assuming persistence preserved correctness. |
| Egress proof passes in compatibility mode but not native units | Treat the two modes as separately proven; a pass in one is not a pass in the other. |
| Forwarded port behaves differently under Podman | Verify the port from the running client's vantage, not from the unit definition. |
| Tunnel drops mid-session under Podman | The shared-namespace relationship must leave no route out; assert no egress when the tunnel is down, as under any engine. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **J2-R1** | The tool MUST be able to run the full stack on Podman with no dependency on Docker. |
| **J2-R2** | The tool MUST offer both a Docker-compatible mode and a native system-unit mode, and let the operator choose. |
| **J2-R3** | The native-unit mode MUST reproduce the download client joining the VPN container's network namespace. |
| **J2-R4** | The native-unit mode MUST gate startup ordering on a dependency being HEALTHY, not merely started. |
| **J2-R5** | The native-unit mode MUST be boot-persistent and MUST be offered only on Linux. |
| **J2-R6** | The VPN egress proof and the hardlink inode proof MUST both pass under Podman in each mode before the stack is reported as running correctly. |
| **J2-R7** | The shared network namespace MUST be verified at runtime from inside the running client, and MUST NOT be inferred from the unit or compose file. |
| **J2-R8** | The tunnel MUST be re-proven on every start, not assumed from a previously working configuration. |
| **J2-R9** | Where rootless operation cannot grant the tunnel device or network capability, the tool MUST lead with a rootful or a documented tested rootless recipe rather than a silent partial start. |
| **J2-R10** | Where user-namespace UID shifting would break hardlinks, the tool MUST align UIDs and MUST confirm linking with a filesystem inode check. |
| **J2-R11** | A namespace or hardlink check that could not be confirmed MUST be reported as unproven, never as passed. |
| **J2-R12** | Requesting native-unit mode on a non-Linux host MUST be refused with an explanation, offering the compatibility mode instead. |
| **J2-R13** | Mode selection, unit generation, and running the egress and hardlink proofs under Podman MUST each be reachable non-interactively. |
| **J2-R14** | A tunnel drop MUST leave the download client with no route out, verified by asserting no egress while the tunnel is down. |

## Related

- [J1 Container-engine abstraction](j1-engine-abstraction.md) — the interface that makes Podman a drop-in engine
- [J3 Running natively, without containers](j3-native.md) — the next step when no container engine is used
- [C2 VPN verification](../c-trust/c2-vpn-verification.md) — the egress proof run under Podman
- [C5 Storage & hardlink management](../c-trust/c5-storage.md) — the hardlink proof and UID alignment
