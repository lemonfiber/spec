---
id: J3
title: Running natively, without containers
kind: feature
area: J
audience: operator
status: draft
tracks: v2
milestone: M12
priority: P3
labels: [runtime, network, verification]
relates: [J1, C2]
---

# J3 — Running natively, without containers

**Status:** Draft · **Audience:** Operator (advanced) · **Area:** J — Runtime & platform

---

## Purpose

Give the power user a path that runs the services as native host services with no
containers at all, on Linux — and still prove the two properties the whole
project is built on: that the VPN cannot leak, and that imports hardlink. The
isolation a container's shared network namespace used to provide is rebuilt from
kernel primitives directly, and the proofs that made it trustworthy run
unchanged, because a proof that only works inside a container was never really a
proof about the traffic.

## Behaviour

### Services run under the host init system

Each service runs as a native host service supervised by the init system, started
and stopped and health-checked like any other system service. There is no
container engine in the path; the operator has chosen to trade the container's
packaging for direct host control.

### VPN isolation is rebuilt from kernel primitives

What a shared network namespace gave for free is reconstructed explicitly:

- **A dedicated network namespace** holds the VPN interface, so the tunnel lives
  in its own isolated network stack.
- **The download client is bound into that namespace**, so its only route to the
  internet is through the tunnel — exactly the guarantee the container topology
  provided.
- **A kill rule inside the namespace** ensures that if the tunnel interface drops,
  there is no route out at all: no tunnel, no traffic.

### Hardlinks are native and trivial

With no container filesystem boundary and no UID shifting, downloads and media
share one host mount and imports hardlink directly. This is the one thing the
native path makes easier rather than harder — and it is still proven, not assumed.

### It proves both properties inside the rebuilt isolation

The same egress-IP proof runs inside the dedicated namespace: observe the public
address seen from within the namespace, compare it against the host's own public
address, and assert they differ — the traffic leaves via the tunnel, not the bare
host. The killswitch is proven the honest way: bring the tunnel interface down and
assert there is then *no* egress at all. Hardlinks are proven by creating a file,
linking it, and comparing inodes on the real data root.

### It is honest about what this path costs

The native path is the highest-effort option and lemonfiber says so. It costs the
operator the VPN-provider abstraction the container gave — the provider's
configuration, endpoint rotation and reconnection logic that the VPN container
packaged now become the operator's to manage. It is Linux-only: network
namespaces do not exist on macOS, so there is no native path there, and the tool
refuses rather than pretending. GPU passthrough, by contrast, is genuinely easier
here, because there is no container boundary for the device to cross.

### Every step has a non-interactive equivalent

Standing up the namespace, binding the client, installing the kill rule, and
running the egress and hardlink proofs are all reachable as plain subcommands.

## States

| State | Meaning |
|-------|---------|
| `native-live` | Services running under the init system; namespace isolation and both proofs passing |
| `killswitch-proven` | Tunnel-down was tested and confirmed to leave zero route out |
| `namespace-degraded` | The dedicated namespace or client binding could not be confirmed; traffic isolation treated as unproven |
| `leaked` | The egress proof shows the client's public address equals the host's; halted, because this is the failure the project exists to prevent |
| `unsupported-host` | Non-Linux or non-init host where network namespaces are unavailable; refused with the reason |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Tunnel interface drops | The kill rule must leave zero route out; prove it by asserting no egress while the interface is down, not by trusting the rule exists. |
| A service escapes the namespace | Detect that the client's traffic is not confined to the namespace and halt; an unconfined download client is a leak. |
| Egress inside the namespace equals the host address | Treat as a leak and stop; the whole point of the namespace is that these must differ. |
| macOS or other host without network namespaces | Refuse the native path and explain that network namespaces are a Linux kernel mechanism absent there. |
| Non-systemd or otherwise unsupported init | State it is unsupported rather than half-configuring host services that will not be supervised. |
| GPU passthrough needed | Note it is easier natively than in a container; the device is on the host already. |
| VPN provider endpoint changes | The operator owns reconnection here; surface that the provider abstraction is theirs now, and re-prove egress after any change. |
| Reboot | Isolation, binding, and kill rule must reassert on boot; re-prove egress after boot rather than assuming persistence preserved it. |
| Host firewall rules conflict with the kill rule | Verify the resulting behaviour by test, not by reading the ruleset; the assertion is no-egress-when-down. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **J3-R1** | The tool MUST be able to run the services as native host services under the init system with no container engine in the path, on Linux. |
| **J3-R2** | VPN isolation MUST be rebuilt as a dedicated network namespace holding the VPN interface, with the download client bound into that namespace. |
| **J3-R3** | A kill rule inside the namespace MUST ensure that if the tunnel drops there is no route out. |
| **J3-R4** | The egress-IP proof MUST run inside the dedicated namespace, comparing the address seen there against the host's, and MUST assert they differ. |
| **J3-R5** | The killswitch MUST be proven by bringing the tunnel interface down and asserting there is then no egress at all. |
| **J3-R6** | Hardlinking MUST be proven by creating a file, linking it, and comparing inodes on the real data root. |
| **J3-R7** | An egress address inside the namespace equal to the host's MUST be treated as a leak and MUST halt the stack. |
| **J3-R8** | A namespace or client binding that cannot be confirmed MUST be reported as unproven, never as isolated. |
| **J3-R9** | The tool MUST state that the native path forfeits the VPN-provider abstraction the container gave, making provider configuration and reconnection the operator's responsibility. |
| **J3-R10** | The tool MUST state that the native path is the highest-effort option. |
| **J3-R11** | The native path MUST be refused on hosts without network namespaces, with the reason given, and MUST NOT be offered on macOS. |
| **J3-R12** | Standing up the namespace, binding the client, installing the kill rule, and running the egress and hardlink proofs MUST each be reachable non-interactively. |
| **J3-R13** | Isolation, client binding, and the kill rule MUST reassert after reboot, with egress re-proven rather than assumed. |
| **J3-R14** | Egress MUST be re-proven after any change to the VPN provider configuration. |

## Related

- [J1 Container-engine abstraction](j1-engine-abstraction.md) — the interface the native path plugs into without a container engine
- [J2 Running under Podman](j2-podman.md) — the container path that still packages the provider abstraction
- [C2 VPN verification](../c-trust/c2-vpn-verification.md) — the egress and killswitch proofs run inside the namespace
