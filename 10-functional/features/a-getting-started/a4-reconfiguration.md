---
id: A4
title: Reconfiguration
kind: feature
area: A
audience: operator
status: accepted
tracks: v1
labels: [ux]
relates: [A2, A5, C5, C9, E4]
---

# A4 — Reconfiguration

**Status:** Accepted · **Audience:** Operator · **Area:** A — Getting started

---

## Purpose

Every decision made during setup must be changeable afterwards, without starting
over and without hand-editing configuration files.

Setup asks fifteen questions when the operator knows least about the system.
Some answers will be wrong. Without a first-class way to revise them, the
operator's only options are to edit files they were never meant to see, or to
tear everything down and re-run setup — which risks their library.

An unchangeable decision is a trap, and a product full of traps teaches people
not to touch it.

## Behaviour

### Any setup answer can be revisited individually

The operator changes one thing without being walked through the other fourteen.
Reconfiguration presents the current configuration as a set of editable
decisions, each showing its present value and what changing it will affect.

### Consequences are stated before the change is applied

Reconfiguration divides sharply into two kinds, and the distinction must be
visible:

| Kind | Examples | Behaviour |
|------|----------|-----------|
| **Cheap** | Timezone, quality preset, notification targets, bandwidth schedule | Applied with a restart of the affected services |
| **Consequential** | Data location, storage mode, Jellyfin mode, protocols | Requires confirmation, may require moving data, may invalidate library paths |

Changing the data location is the sharpest example: every *arr holds absolute
paths to its root folders. Moving `DATA_ROOT` without updating them leaves a
library that points at nothing. lemonfiber MUST detect this and either update the
paths or refuse and explain — never apply the change and leave the operator to
discover the breakage.

### Adding a capability later is a supported path, not a repair

The most common reconfiguration is additive: someone starts library-only, then
wants Usenet; or starts Usenet-only, then wants torrents. Each of these opens
exactly the prerequisites and credentials that the new capability needs, and
nothing else.

Someone who began with zero paid services should be able to grow into a full
stack incrementally, one decision at a time.

### Removing a capability is equally supported

Dropping torrents stops and removes the download client and VPN, and disables the
forms that required them — while explicitly *not* touching downloaded content.
The operator is told what will stop, what will be removed, and what will be kept.

### Nothing is applied until confirmed

The same rule as [A2](a2-setup-wizard.md): a review step showing the diff between
current and proposed configuration, and no writes before confirmation.

## States

| State | Meaning |
|-------|---------|
| `clean` | Configuration matches what lemonfiber last wrote |
| `pending` | Changes staged, not applied |
| `applying` | Writing and restarting affected services |
| `drifted` | Configuration was changed outside lemonfiber — see [C9](../c-trust/c9-drift.md) |
| `blocked` | A staged change cannot be applied safely; reason stated |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Data location changed with an existing library | Detect it. Offer to move the data, or to re-point the configuration at the existing location. **Never** silently leave the *arrs pointing at absent paths. |
| New data location can't hardlink but the old one could | Warn that imports will degrade to copies, and require confirmation. |
| Protocols reduced while downloads are active | Report what's in flight and offer to wait, or to stop and lose progress. Don't silently discard active work. |
| Jellyfin switched docker→native | Config and library paths must be migrated; state exactly what the operator must install and do by hand, since a package manager action can't be taken on their behalf. |
| VPN credentials replaced | Validate the new ones **before** discarding the old, so a bad paste doesn't leave the operator with no working tunnel. |
| Configuration was edited by hand outside lemonfiber | Detected as `drifted`. Show the difference and let the operator choose which side wins. Never silently overwrite their edit. |
| Change requires a service that isn't running | State it and offer to start it, rather than failing obscurely. |
| Operator reduces quality preset with existing library | Clarify that it affects future grabs only; existing files are untouched unless an upgrade is separately requested. |
| Timezone change | Applied cheaply, but note that *arr schedules shift accordingly. |
| Household disabled after invitations were sent | Existing accounts are retained by default; deleting them is a separate, explicit action. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **A4-R1** | Every decision made during [A2](a2-setup-wizard.md) MUST be individually revisable without re-running the full wizard. |
| **A4-R2** | Each change MUST state its consequences before being applied. |
| **A4-R3** | Changes MUST be classified as cheap or consequential, and consequential changes MUST require explicit confirmation. |
| **A4-R4** | A review step MUST show the diff between current and proposed configuration; nothing MAY be written before confirmation. |
| **A4-R5** | Changing the data location MUST detect existing library paths and MUST either update them or refuse with an explanation. |
| **A4-R6** | Adding a protocol MUST open only the prerequisites and credentials that protocol requires. |
| **A4-R7** | Removing a protocol MUST NOT delete downloaded or imported content, and MUST state what is kept. |
| **A4-R8** | Replacement credentials MUST be validated before the previous ones are discarded. |
| **A4-R9** | Reconfiguration MUST detect out-of-band configuration edits and MUST NOT silently overwrite them. |
| **A4-R10** | Reducing capability while work is in flight MUST report what is active and offer to wait. |
| **A4-R11** | A change that cannot be applied safely MUST leave configuration unmodified and MUST state why. |
| **A4-R12** | Quality preset changes MUST state that they affect future acquisitions only. |

## Related

- [A2 Setup wizard](a2-setup-wizard.md) — where these decisions originate
- [A5 Migration](a5-migration.md) — adopting an existing setup
- [C5 Storage management](../c-trust/c5-storage.md) — data location mechanics
- [C9 Drift detection](../c-trust/c9-drift.md) — out-of-band changes
- [E4 Rollback](../e-maintenance/e4-rollback.md) — undoing a bad reconfiguration
