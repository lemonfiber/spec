---
id: E2
title: lemonfiber self-update
kind: feature
area: E
audience: operator
status: accepted
tracks: v1
milestone: M6
labels: [updates]
depends: [C4, E1, G8]
---

# E2 — lemonfiber self-update

**Status:** Accepted · **Audience:** Operator · **Area:** E — Maintenance

---

## Purpose

Keep lemonfiber itself current, across three platforms and several installation
methods, without breaking whichever one the operator used.

A single binary distributed via Homebrew, Scoop, shell installers, `cargo
install` and direct download has a real hazard: replacing itself in a way that
conflicts with the package manager that installed it. An operator who installed
via Homebrew and then let the binary overwrite itself now has a Homebrew
installation that disagrees with what's on disk, and the next `brew upgrade`
produces something confusing.

## Behaviour

### Update method follows installation method

lemonfiber detects how it was installed and either performs the update or defers
to the tool that owns it:

| Installed via | Behaviour |
|---------------|-----------|
| Homebrew | Defer — print the `brew` command. Never self-replace. |
| Scoop / winget | Defer — print the command |
| Cargo | Defer — print the command |
| Shell installer / direct download | Self-update in place |
| Package manager (distro) | Defer |

Deferring is not a failure. Fighting the package manager is the failure.

### Update availability is advisory

An available update is surfaced quietly. It is not a modal, not repeated, and not
a precondition for anything. The stack keeps working on an old lemonfiber.

### The stack keeps running regardless

Updating lemonfiber does not stop, restart or alter the stack. The binary is a
control surface; containers run independently of it. This is a deliberate
property — an operator must be able to update the tool without touching a working
system.

### Compatibility is checked before, not after

A new lemonfiber carries a new pinned stack, and the manifest contract has a
schema version ([ADR-0005](../../../00-overview/decisions/0005-embedded-stack-assets.md)).
Where an update would require materialising a newer stack, that's stated up front,
along with whether any service update is implied.

### Version and provenance are always answerable

lemonfiber reports its version, the stack version it carries, and how it was
installed. Bug reports are otherwise unactionable.

### Downgrade is possible

Unlike service databases, lemonfiber holds no irreversibly-migrating state.
Reverting to a previous version is supported, which makes updating low-risk.

## States

| State | Meaning |
|-------|---------|
| `current` | Latest known version |
| `update-available` | Newer version exists |
| `managed-externally` | Installed by a package manager; update deferred to it |
| `updating` | Replacement in progress |
| `restart-required` | Updated; the running instance is still the old one |
| `check-failed` | Could not determine availability |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Installed via a package manager | Defer with the exact command. Never self-replace. |
| Update check fails | Report and continue. Never block operation on a version check. |
| Binary not writable | Report the permission problem with the path; do not attempt escalation. |
| Update while lemonfiber is serving a web UI | Complete the download, then require a restart. Don't replace a running executable underneath itself. |
| Interrupted mid-replacement | The previous binary must remain functional. Replacement is atomic or it doesn't happen. |
| New version carries a newer stack schema | State it before updating, including any implied service updates. |
| Operator on an unsupported platform | Report that no artifact exists for their platform rather than failing obscurely. |
| Air-gapped machine | Update checking must be disableable, and must not retry noisily. |
| Multiple lemonfiber binaries on PATH | Report which is running, with its path. |
| Downgrade requested | Supported; state whether the older version can read the current configuration. |
| Configuration written by a newer version | Refuse to operate on configuration from a future version, rather than corrupting it. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **E2-R1** | lemonfiber MUST detect its installation method and MUST defer to an owning package manager rather than self-replacing. |
| **E2-R2** | When deferring, the exact command for that package manager MUST be printed. |
| **E2-R3** | Update availability MUST be advisory and MUST NOT block any operation. |
| **E2-R4** | Update notices MUST NOT be repeated persistently. |
| **E2-R5** | Updating lemonfiber MUST NOT stop, restart or modify the running stack. |
| **E2-R6** | Binary replacement MUST be atomic; an interruption MUST leave the previous version functional. |
| **E2-R7** | A running instance MUST NOT be replaced in place; a restart MUST be required and stated. |
| **E2-R8** | lemonfiber MUST report its own version, the stack version it carries, and its installation method. |
| **E2-R9** | An update requiring a newer stack schema MUST state this, including implied service updates, before proceeding. |
| **E2-R10** | Downgrade MUST be supported, and compatibility with existing configuration MUST be stated. |
| **E2-R11** | Configuration written by a newer version MUST be refused rather than modified. |
| **E2-R12** | Update checking MUST be disableable and MUST NOT retry noisily when unavailable. |
| **E2-R13** | Insufficient permission to replace the binary MUST be reported with the path, and MUST NOT attempt privilege escalation. |
| **E2-R14** | Where several lemonfiber binaries exist on PATH, the running one MUST be identifiable by path. |

## Related

- [E1 Stack updates](e1-stack-updates.md) — updating the services
- [ADR-0005 Embedded stack assets](../../../00-overview/decisions/0005-embedded-stack-assets.md)
- [G8 Privacy stance](../g-ux/g8-privacy.md) — what an update check transmits
- [C4 Support bundle](../c-trust/c4-support-bundle.md) — version provenance in reports
