---
id: A6
title: Clean uninstall
kind: feature
area: A
audience: operator
status: accepted
tracks: v1
---

# A6 — Clean uninstall

**Status:** Accepted · **Audience:** Operator · **Area:** A — Getting started

---

## Purpose

An operator must be able to remove this completely, understand exactly what was
removed, and keep their media.

Uninstall is a trust feature. Software that is hard to remove is software people
hesitate to install, and non-technical operators in particular need to know
there's a way out before they'll commit. "How do I undo this?" deserves a real
answer, not a wiki page listing eleven manual steps.

It's also the feature most projects omit, which means the operator's fallback is
guessing which containers, volumes, images, and directories belonged to us.

## Behaviour

### Removal is tiered, and the tiers are separate decisions

Conflating "stop using lemonfiber" with "delete my media" is the failure mode to avoid.
Four independent tiers, each explicitly chosen:

| Tier | Removes | Keeps |
|------|---------|-------|
| **1. Stop** | Nothing. Services stopped. | Everything |
| **2. Remove services** | Containers, networks, and pulled images | All config, all media |
| **3. Remove configuration** | Service config, lemonfiber's own state, credentials | All media |
| **4. Remove media** | The library and downloads | Nothing |

Tier 4 is never bundled with anything else and always requires a separate,
explicit confirmation naming the amount of data at stake.

### The manifest is shown before anything is removed

The operator sees precisely what will be deleted — paths, container names, image
names, and total reclaimable size — before confirming. No summary counts standing
in for the actual list.

### Media is opt-in to delete, never opt-out

The default for every tier below 4 is that media survives. Deleting a library the
operator spent years building because they wanted to try a different tool would
be unforgivable, and defaults are what people accept.

### Credentials are actively destroyed, not merely orphaned

Tier 3 removes stored credentials — VPN keys, indexer API keys, provider
passwords — and says so. Leaving secrets on disk after an uninstall is a security
failure, and the operator has no way to know they're still there.

### What lemonfiber cannot remove is stated

Docker Desktop itself, a natively-installed Jellyfin, a Tailscale client, or
anything the operator installed by hand is **out of scope** — but must be listed
with removal instructions, so the operator isn't left believing the machine is
clean when it isn't.

### Uninstall works even when things are broken

A wedged stack is a common reason to uninstall. Uninstall must not depend on the
stack being healthy, on lemonfiber's configuration being valid, or on the Docker daemon
being fully responsive. Where it can't complete a step, it reports what remains
and how to remove it by hand.

## States

| State | Meaning |
|-------|---------|
| `surveyed` | Removable items enumerated with sizes; nothing removed |
| `confirmed` | Operator selected a tier and confirmed the manifest |
| `removing` | In progress |
| `complete` | Selected tier fully removed |
| `partial` | Some items could not be removed; each named with manual instructions |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Services still running | Stop them first as part of removal; report anything that won't stop. |
| Downloads in flight | Report them and offer to wait, or to abandon and lose progress. Never silently discard. |
| Media directory contains files lemonfiber didn't create | Detect it. Refuse blanket deletion and require per-directory confirmation — the operator may have put things there. |
| Docker daemon unreachable | Remove what's removable on the filesystem; list container/image removal as manual steps. |
| Configuration is corrupt or unreadable | Fall back to well-known default paths and report reduced confidence in the manifest. |
| Media on a NAS or external volume | Report that removal affects a network or removable volume, and require an additional confirmation. |
| A natively-installed Jellyfin is present | List it as out of scope, with platform-specific removal instructions. |
| Images shared with the operator's other projects | Report which images are shared and exclude them from removal by default. |
| Household accounts exist | State that removing configuration destroys household accounts and their watch state. |
| Operator wants to reinstall later | Point at [E3 backup](../e-maintenance/e3-backup-restore.md) before removing, so the setup can be restored rather than rebuilt. |
| Insufficient permissions to delete a path | Report the specific path and the permission needed. Do not attempt privilege escalation. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **A6-R1** | Uninstall MUST offer independent tiers, and MUST NOT bundle media deletion with any other tier. |
| **A6-R2** | A complete manifest of items to be removed — paths, containers, images, and total size — MUST be shown before confirmation. |
| **A6-R3** | Media MUST be retained by default at every tier below 4. |
| **A6-R4** | Deleting media MUST require a separate confirmation stating the data volume involved. |
| **A6-R5** | Removing configuration MUST destroy stored credentials and MUST state that it has done so. |
| **A6-R6** | Items lemonfiber cannot remove MUST be listed with manual removal instructions. |
| **A6-R7** | Uninstall MUST function when the stack is unhealthy, when configuration is invalid, and when the Docker daemon is unreachable. |
| **A6-R8** | Items that could not be removed MUST be enumerated with instructions, not silently skipped. |
| **A6-R9** | Files in the media tree not created by the stack MUST be detected, and MUST prevent blanket deletion. |
| **A6-R10** | Container images shared with other projects MUST be identified and excluded by default. |
| **A6-R11** | In-flight downloads MUST be reported, with an option to wait. |
| **A6-R12** | Before configuration removal, lemonfiber MUST offer to produce a backup. |
| **A6-R13** | Uninstall MUST NOT require or attempt privilege escalation. |

## Related

- [A4 Reconfiguration](a4-reconfiguration.md) — for reducing scope rather than removing
- [A7 Credential management](a7-credential-management.md) — what credential destruction covers
- [E3 Backup & restore](../e-maintenance/e3-backup-restore.md) — the pre-uninstall safety net
- [G4 Error model](../g-ux/g4-error-model.md) — partial-removal reporting
