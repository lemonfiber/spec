---
id: A5
title: Migration from an existing stack
kind: feature
area: A
audience: operator
status: accepted
tracks: v1
labels: [ux, storage]
relates: [A2, A4, C5, E3, F1]
---

# A5 — Migration from an existing stack

**Status:** Accepted · **Audience:** Operator · **Area:** A — Getting started

---

## Purpose

Many prospective operators already run some of this. They have a hand-rolled
compose file, a Sonarr instance with 400 monitored series, indexers configured
over three years, and — most importantly — **a library they will not risk**.

For them the question isn't "how do I set this up," it's "can I adopt this
without losing what I have?" If the answer requires starting over, they won't
adopt. And the loudest voices in the community are exactly these people.

Migration is also the lowest-risk way to earn trust: an operator who sees lemonfiber
correctly identify their existing setup, without touching it, believes the rest
of the tool.

## Behaviour

### Detect first, change nothing

Migration begins as a **read-only survey**. lemonfiber looks for evidence of an
existing setup and reports what it found before proposing anything:

| Evidence | What it tells us |
|----------|------------------|
| A running container matching a known service image | Which services exist, on which ports |
| An existing `config.xml` or app database | API keys, root folders, download client wiring |
| A compose file in the working directory | The current topology and volume layout |
| Media directories with recognisable structure | Where the library lives and how it's organised |

The survey output is a plain statement of findings. Nothing is modified.

### Adoption, not replacement

The default posture is **adopt**: keep the operator's existing services, config,
and library, and place lemonfiber in front of them as a control surface. Wholesale
replacement is offered but never preselected.

| Mode | What happens |
|------|--------------|
| **Adopt** *(default)* | lemonfiber manages the existing containers and reads their configuration. Nothing is recreated. |
| **Import** | lemonfiber creates its own stack but copies indexers, root folders, and monitored items across via API. |
| **Replace** | lemonfiber stands up a clean stack; the operator's old one is stopped but not deleted. |
| **Side-by-side** | lemonfiber runs on alternative ports alongside the existing setup so it can be evaluated without commitment. |

Side-by-side deserves emphasis: it lets a cautious operator evaluate with zero
risk, which is exactly what this audience wants.

### The library is never moved without explicit instruction

The library is the irreplaceable part — often years of accumulated content. lemonfiber
may *read* it, *index* it, and *point at* it. It must never move, rename, or
reorganise it as part of migration.

If the existing layout violates the [single-mount rule](../../../00-overview/decisions/0006-single-data-mount.md),
lemonfiber reports the consequence and offers a remedy — but the operator decides.
Correctness does not outrank their data.

### What cannot be migrated is stated plainly

Some things won't transfer: bespoke custom formats, per-indexer tuning, scripts
hooked into an *arr's event system. lemonfiber enumerates what it could **not** carry
across, rather than implying a complete migration and leaving the operator to
discover gaps.

## States

| State | Meaning |
|-------|---------|
| `none-detected` | No existing setup found; normal setup proceeds |
| `surveyed` | Existing setup found and described; nothing changed |
| `plan-proposed` | A migration mode selected and its actions listed |
| `migrating` | Executing the plan |
| `adopted` | lemonfiber is managing pre-existing services |
| `imported` | Configuration copied into a lemonfiber-managed stack |
| `partial` | Some items migrated, some could not; unmigrated items enumerated |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Existing services on ports lemonfiber wants | Detect before proposing anything. Offer adopt, or remap lemonfiber's ports for side-by-side. |
| Existing setup uses separate `/downloads` and `/media` mounts | Report that hardlinks are not working today and quantify the cost. Offer a remedy; do not require it. |
| Existing *arr version newer than the pinned one | **Refuse to downgrade.** The database has already migrated and older binaries cannot open it. Offer to adopt at the existing version instead. |
| Existing *arr version much older | Warn that adoption will migrate the database irreversibly, and require a backup first. |
| Config files present but services not running | Read config, report findings, offer import without needing the services up. |
| Two conflicting existing setups | Report both and require the operator to choose. Don't guess. |
| Library layout unrecognisable | Report honestly that structure could not be determined; offer manual root-folder specification. |
| Existing setup uses a different download client (NZBGet, Transmission, Deluge) | Adopt it where it is supported; otherwise state clearly that it is unsupported and what the alternatives are. |
| Existing Plex installation | Detect and report it. Explain that Jellyfin is a separate server and the two can coexist; offer library-path reuse. Do not disparage the choice. |
| Docker volumes rather than bind mounts | Report that the library is inside Docker-managed storage, which limits host visibility, and describe what adoption can and cannot do. |
| Migration fails partway | Leave the original setup functional. This is the non-negotiable property: **a failed migration must never break what already worked.** |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **A5-R1** | Migration MUST begin with a read-only survey that modifies nothing. |
| **A5-R2** | The survey MUST report every detected service, config source, and library location before any plan is proposed. |
| **A5-R3** | Adopt MUST be the default mode; replacement MUST NOT be preselected. |
| **A5-R4** | lemonfiber MUST NOT move, rename, or reorganise existing media as part of migration. |
| **A5-R5** | Side-by-side evaluation on alternative ports MUST be supported. |
| **A5-R6** | lemonfiber MUST refuse to downgrade an existing *arr database and MUST explain why. |
| **A5-R7** | An upgrade of an existing *arr database MUST require a backup first. |
| **A5-R8** | Items that could not be migrated MUST be enumerated explicitly. |
| **A5-R9** | A failed or abandoned migration MUST leave the pre-existing setup functional. |
| **A5-R10** | An existing layout that breaks hardlinks MUST be reported with its cost quantified, and a remedy offered but not forced. |
| **A5-R11** | Port conflicts with existing services MUST be detected before any plan is proposed. |
| **A5-R12** | Unsupported existing components MUST be named as unsupported rather than silently ignored. |

## Related

- [A2 Setup wizard](a2-setup-wizard.md) — the path when nothing exists
- [A4 Reconfiguration](a4-reconfiguration.md) — changing decisions post-migration
- [C5 Storage management](../c-trust/c5-storage.md) — the hardlink assessment
- [E3 Backup & restore](../e-maintenance/e3-backup-restore.md) — the pre-migration safety net
- [F1 Customisation](../f-extensibility/f1-customisation.md) — for operators keeping their own compose file
