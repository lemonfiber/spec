---
id: J1
title: Container-engine abstraction
kind: feature
area: J
audience: operator
status: draft
tracks: v2
priority: P1
labels: [runtime, verification]
relates: [C2, C5, B1]
---

# J1 — Container-engine abstraction

**Status:** Draft · **Audience:** Operator · **Area:** J — Runtime & platform

---

## Purpose

Drive the whole stack through a single interface that speaks to more than one
container engine, so the tool is not wedded to one runtime — and prove the choice
of engine changes nothing that matters by running the *identical* verification
suite against each. The entire reason this area exists is to free the stack from
any single proprietary runtime; an abstraction that merely *ran* on two engines
but could not *prove* they behave the same would leave that freedom unearned.

## Behaviour

### It detects which engines are present and usable

lemonfiber discovers the container engines installed on the host — Docker and
Podman are the supported subjects — and reports each as present-and-usable,
present-but-unusable, or absent. Presence alone is not usability: an engine
whose socket exists but rejects the operator's commands is reported as unusable
with the reason, never treated as a working target.

### One control surface, whatever the engine

Bringing services up and down, inspecting them, executing a command inside one,
and reading health are expressed once and mapped onto whichever engine is
selected. The operator issues the same intent regardless of runtime; the mapping
to engine-specific mechanics lives below the interface, not in the operator's
hands.

### The verification suite is the same suite, unchanged

This is the load-bearing property. The VPN egress proof (compare the download
client's observed public address against the host's, and against the tunnel's
declared exit), the hardlink proof (create a file, link it, compare inodes), and
per-service health checks run **byte-for-byte the same** on every engine. They
are namespace-level and filesystem-level observations — commands run against the
running result — not readings of the compose file or trust in the engine's
report. The abstraction is judged behaviour-preserving only when these identical
proofs pass on each engine, not when the control commands merely succeed.

### A capability the engine lacks is reported, never skipped

Where an engine cannot express something the stack relies on — a forwarded port,
a shared network namespace, a health-gated dependency — lemonfiber states the gap
against that engine plainly. It does not silently drop the capability and it does
not let a proof that could not run masquerade as a proof that passed.

### Every engine path has a non-interactive equivalent

Selecting an engine, listing detected engines, and running the verification suite
against a named engine are all reachable as plain subcommands, so nothing about
multi-engine support costs the scripter the wizard-free path.

## States

| State | Meaning |
|-------|---------|
| `single-engine` | Exactly one usable engine found; it is selected automatically |
| `multi-engine` | More than one usable engine; the operator's selection or the configured default applies |
| `engine-unusable` | An engine is present but cannot be driven (permission, socket, version); named with the reason |
| `no-engine` | No usable container engine on the host; directs to install one or to the native path ([J3](j3-native.md)) |
| `verified` | The selected engine has passed the full egress, hardlink, and health suite |
| `capability-gap` | The selected engine cannot express a required capability; the gap is named, not hidden |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Engine maps a compose feature differently | Verify the resulting namespace and mounts at runtime; never trust that the config string produced the intended topology. |
| Engine present but the operator lacks permission | Report present-but-unusable with the permission reason; do not fall back silently to another engine without saying so. |
| Two engines both usable | State which was chosen and why; make the selection explicit and overridable rather than implicit. |
| Selected engine cannot forward a port | Name the capability gap against that engine; do not present the stack as fully wired. |
| Engine reports a container healthy but the egress proof fails | The proof wins; report unverified, because a green health flag is not proof the tunnel carries the traffic. |
| Engine upgraded underneath a running stack | Re-detect on next run; if behaviour shifted, the verification suite is the arbiter, not the version string. |
| One engine passes the suite, another fails it | Do not treat the abstraction as behaviour-preserving; surface the divergence and which proof diverged. |
| Engine exposes a socket but no working CLI, or vice versa | Establish usability from an actual round-trip command, not from the presence of a socket or binary alone. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **J1-R1** | The tool MUST detect the container engines installed on the host and classify each as usable, present-but-unusable, or absent. |
| **J1-R2** | Engine usability MUST be established from a successful round-trip command, not from the mere presence of a socket or binary. |
| **J1-R3** | Bring-up, teardown, inspection, in-container execution, and health reads MUST be expressed once and mapped onto the selected engine. |
| **J1-R4** | The VPN egress proof, the hardlink inode proof, and per-service health checks MUST run identically across every supported engine, with no engine-specific variation in the checks themselves. |
| **J1-R5** | The egress and hardlink proofs MUST pass on each supported engine before that engine is reported as verified. |
| **J1-R6** | Proofs MUST observe the running result — namespaces, addresses, inodes — and MUST NOT be satisfied by reading the compose file or trusting the engine's own report. |
| **J1-R7** | A capability the selected engine cannot express MUST be reported explicitly, and MUST NOT be silently skipped. |
| **J1-R8** | A proof that could not run MUST be distinguished from a proof that ran and passed. |
| **J1-R9** | When more than one engine is usable, the selection MUST be stated and MUST be overridable by the operator. |
| **J1-R10** | When no usable engine is present, the tool MUST say so and MUST NOT silently degrade. |
| **J1-R11** | A divergence in proof results between two engines MUST be surfaced rather than averaged or hidden. |
| **J1-R12** | Engine detection, selection, and running the verification suite against a named engine MUST each be reachable non-interactively. |
| **J1-R13** | Adding support for a further engine MUST NOT require changing the verification suite. |
| **J1-R14** | The operator MUST NOT need to know engine-specific commands to drive the stack through the common interface. |

## Related

- [J2 Running under Podman](j2-podman.md) — the first alternative engine this abstraction unlocks
- [J3 Running natively, without containers](j3-native.md) — the path when no engine is used at all
- [C2 VPN verification](../c-trust/c2-vpn-verification.md) — the egress proof kept identical across engines
- [C5 Storage & hardlink management](../c-trust/c5-storage.md) — the hardlink proof kept identical across engines
- [B1 Forms & partial stacks](../b-running/b1-forms.md) — the control surface the abstraction drives
