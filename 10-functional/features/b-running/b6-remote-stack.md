---
id: B6
title: Controlling a stack on another machine
kind: feature
area: B
audience: operator
status: accepted
tracks: v1
---

# B6 — Controlling a stack on another machine

**Status:** Accepted · **Audience:** Operator · **Area:** B — Running it

---

## Purpose

Many operators don't run this on the machine they sit at. The stack lives on a
NAS, a mini-PC or a home server; the operator works from a laptop.

The requirement is modest — reach the stack from elsewhere on the home network —
and the temptation is to over-build it into a client/server protocol with its own
authentication and transport. That would be a large new attack surface for
something a browser already solves.

**Scope is LAN only.** Access from outside the home network is deferred past 1.0
(see [B7 note](../README.md#b--running-it)).

## Behaviour

### Primary path: the web UI, reachable on the LAN

lemonfiber runs **on the machine hosting the stack**. Its web UI is normally
bound to loopback; binding it to the LAN is an explicit opt-in.

```
on the server:
  $ lemonfiber ui --bind lan
  ✗ refusing: LAN binding requires authentication

  $ lemonfiber auth set
  $ lemonfiber ui --bind lan
  ✓ http://nas.local:7171

from the laptop: open a browser.
```

**LAN binding cannot be enabled without authentication configured.** This is a
hard refusal, not a warning — the failure mode is an unauthenticated control
surface for the whole media stack, reachable by every device on the network
including ones the operator doesn't administer.

### Secondary path: a remote Docker context

For operators who prefer the CLI, lemonfiber honours Docker's own remote-host
mechanisms — `DOCKER_HOST`, or a named Docker context, typically over SSH. No new
transport, no new credentials: it reuses SSH keys the operator already has.

### The remote-path trap, handled explicitly

With a remote Docker host, **compose files and bind-mount paths resolve on the
remote machine, not the local one**. `lemonfiber up tv` from a laptop looks for
stack files on the server.

Unhandled, this produces a baffling error naming a path that exists perfectly
well on the machine the operator is sitting at. lemonfiber therefore detects a
remote context and:

1. Verifies the stack files exist on the remote host.
2. Refuses with an explicit explanation if they don't.
3. States, in status output, which host is being operated on.

That last point matters generally: when a remote context is active, **every
command must say which machine it affects**. Stopping the wrong stack because the
shell had a context set is an easy and unpleasant mistake.

### Whichever path, the stack runs in one place

lemonfiber does not orchestrate services across multiple machines. A stack lives
on one host; this feature is about *reaching* it.

## States

| State | Meaning |
|-------|---------|
| `local` | Operating on the local Docker daemon; UI on loopback |
| `lan-served` | Web UI bound to the LAN with authentication configured |
| `remote-context` | Operating a remote Docker daemon via context or `DOCKER_HOST` |
| `remote-unverified` | Remote context active but stack files not confirmed present |
| `refused` | LAN binding requested without authentication |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| `--bind lan` without auth configured | Refuse, and explain how to configure authentication. Never bind with a warning. |
| Remote context set, stack files absent remotely | Refuse before running anything, naming the host and the expected path. |
| Remote context set unnoticed | Every command's output names the target host. |
| Server hostname unresolvable from the laptop | Report a name-resolution failure distinctly from a connection refusal. |
| SSH key not accepted | Report it as an SSH authentication failure with the host named — not as "Docker unavailable". |
| Docker API version mismatch between hosts | Detect at connect and report both versions. |
| Two operators using the web UI at once | Serialise lifecycle operations; show that another operation is in progress. |
| Session over an unencrypted LAN connection | State plainly that traffic is unencrypted HTTP on the local network, and that credentials traverse it. Do not imply TLS where there is none. |
| Laptop sleeps mid-operation | The operation continues server-side; on reconnect the UI shows the outcome. |
| Native-mode Jellyfin on the remote host | Reported as host-managed; lemonfiber does not control the remote OS service manager. |
| Auth configured then removed while LAN-bound | Immediately revert to loopback and state why. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **B6-R1** | The web UI MUST bind to loopback by default. |
| **B6-R2** | LAN binding MUST be an explicit opt-in and MUST be refused unless authentication is configured. |
| **B6-R3** | Removing authentication while LAN-bound MUST immediately revert to loopback binding. |
| **B6-R4** | lemonfiber MUST honour `DOCKER_HOST` and named Docker contexts. |
| **B6-R5** | With a remote context active, lemonfiber MUST verify stack files exist on the remote host before executing any lifecycle operation. |
| **B6-R6** | With a remote context active, every command's output MUST name the host being operated on. |
| **B6-R7** | Name-resolution failure, connection refusal and SSH authentication failure MUST be reported distinctly. |
| **B6-R8** | Concurrent lifecycle operations from multiple clients MUST be serialised. |
| **B6-R9** | When serving over unencrypted HTTP, lemonfiber MUST state that the connection is not encrypted. |
| **B6-R10** | lemonfiber MUST NOT orchestrate services across more than one host. |
| **B6-R11** | Docker API version mismatch MUST be detected at connection and MUST report both versions. |
| **B6-R12** | Client disconnection MUST NOT abort a server-side operation already in progress. |

## Related

- [C6 Web UI security & binding policy](../c-trust/c6-web-security.md) — the authentication model
- [B2 Lifecycle control](b2-lifecycle.md) — the operations being issued remotely
- [G1 Interface tiers](../g-ux/g1-interface-tiers.md) — the web UI itself
- [ADR-0008 Hybrid Docker access](../../../00-overview/decisions/0008-hybrid-docker-access.md)
