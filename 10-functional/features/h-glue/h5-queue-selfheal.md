---
id: H5
title: Queue self-healing
kind: feature
area: H
audience: operator
status: accepted
tracks: v2
priority: P2
labels: [queue, verification, wiring]
relates: [C7]
---

# H5 — Queue self-healing

**Status:** Accepted · **Audience:** Operator · **Area:** H — Ecosystem glue

---

## Purpose

Keep the download queue moving without daily babysitting, by detecting the
downloads that have wedged — stalled, crawling, failed, stuck fetching metadata,
or orphaned because the \*arr that requested them has moved on — and clearing them
so a fresh search can succeed. A queue that quietly fills with dead entries is the
single most common reason a stack stops delivering while every service still
reports "running"; this is the automation layer that acts on that state instead of
merely surfacing it.

Where [C7](../c-trust/c7-queue-health.md) only *reads* queue health and shows what
is stuck, H5 *decides and acts* — but only after an item has proven itself dead
across several checks, never on a single bad reading.

## Behaviour

### It classifies why an item is wedged

Each queued download is sorted into a reason, because the reason dictates the
remedy:

| Condition | What it means |
|-----------|---------------|
| **Stalled** | Connected but no bytes are moving and no seeds/sources are available |
| **Slow** | Moving, but so slowly it will never finish before it matters |
| **Failed** | The download client reports an unrecoverable error |
| **Stuck on metadata** | A torrent that has not resolved its metadata to begin transferring |
| **Orphaned** | Still downloading in the client, but the \*arr no longer has a matching queue record |

An item that does not match any condition is healthy and is left untouched.

### It acts only after consecutive strikes

A download is never removed the first time it looks bad. It must be flagged for the
same reason on **N consecutive checks** before any action is taken — a strikes
model — so a healthy download that dipped during a momentary speed spike, a
provider hiccup, or a swarm reshuffle is given time to recover. A single good check
resets the count to zero.

### It removes, blocklists, then re-searches

When an item has struck out, the healing action is a single reversible motion:
remove the wedged download, blocklist that specific release so the same dead copy
is not immediately grabbed again, and trigger a new search for the wanted item. The
content is not abandoned — it is returned to the queue as a fresh attempt at a
different release.

### It shows what it would do before it does it

Every run can be asked for a **dry-run** that lists exactly which items would be
removed, the reason each was flagged, and how many strikes it carries — without
touching the queue. Removal is a plan the operator can read first, not a surprise
discovered after the fact.

### It proves it can reach what it manages

Before acting, H5 confirms it can authenticate to every \*arr queue endpoint it
manages and to the download client itself, and reports any it cannot reach. It does
not blocklist against, or remove from, a service it only assumed was connected — a
credential that no longer works is reported, not silently skipped.

### It respects a grace window

Newly-added downloads are exempt for a configurable grace period so a torrent still
finding peers, or a Usenet job still queued behind others, is not judged before it
has had a fair chance to start.

### Every step has a non-interactive equivalent

The classification report, the dry-run, and the healing run are each reachable as
plain subcommands, so the operator can wire self-healing into a schedule without a
prompt.

## States

| State | Meaning |
|-------|---------|
| `idle` | No wedged items; the queue is healthy |
| `watching` | One or more items flagged but below the strike threshold; nothing removed |
| `dry-run` | A removal plan produced without acting |
| `healing` | Struck-out items being removed, blocklisted and re-searched |
| `degraded` | One or more \*arr queues or the download client unreachable; acts only on what it can prove it reaches |
| `paused` | Self-healing switched off; classification still readable |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Slow-but-healthy download during a speed spike | Strikes reset on the next good check; a single slow reading never triggers removal. |
| Grace window too short | A just-added torrent still finding peers is exempt until the grace period elapses, not struck on arrival. |
| Download client and \*arr on different volume mounts | Self-healing MUST share the same mount layout the \*arr apps see, or removals target the wrong paths; a mount mismatch is reported and acting is refused rather than risking the wrong file. |
| Download client lacks a remove-and-blocklist capability | Fall back to the strongest supported action, name the limitation, and never claim a blocklist that the client cannot honour. |
| Orphaned item that the \*arr is about to re-adopt | Treat orphan detection conservatively; require the strike count before removing, so a brief record gap does not delete an active transfer. |
| \*arr queue reachable but download client unreachable | Enter `degraded`; classify from what is readable but do not remove, since removal needs the client. |
| Same release re-grabbed after blocklist | The blocklist entry prevents an immediate re-grab of the identical dead release; a genuinely different release is allowed. |
| Operator runs a live heal without a dry-run first | Permitted, but the run still records what it removed and why, so the action remains auditable after the fact. |
| Every candidate is within its grace window | Report "nothing actionable yet" rather than an empty success that reads as "queue clean". |
| Removal of a shared/season-pack download | Only the wedged item is targeted; a multi-file grab is not torn down wholesale on one bad member. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **H5-R1** | The tool MUST classify each queued download as stalled, slow, failed, stuck-on-metadata, orphaned, or healthy, and MUST leave healthy items untouched. |
| **H5-R2** | An item MUST be flagged for the same reason on N consecutive checks before any removal, and a single healthy check MUST reset its strike count. |
| **H5-R3** | Newly-added downloads MUST be exempt from removal for a configurable grace window. |
| **H5-R4** | The healing action MUST remove the wedged download, blocklist that specific release, and trigger a fresh search for the wanted item. |
| **H5-R5** | The tool MUST offer a dry-run that lists every item it would remove and the reason for each, without modifying the queue. |
| **H5-R6** | The tool MUST authenticate to every managed \*arr queue endpoint and to the download client, and MUST report any it cannot reach rather than acting on an assumed connection. |
| **H5-R7** | The tool MUST NOT remove from, or blocklist against, a service whose credential it could not verify. |
| **H5-R8** | Where the download client cannot share the \*arr volume mount layout, the tool MUST refuse to act and report the mismatch rather than target the wrong path. |
| **H5-R9** | Where the download client lacks remove-or-blocklist support, the tool MUST fall back to the strongest supported action and MUST NOT claim an action the client cannot perform. |
| **H5-R10** | Orphan detection MUST require the full strike count before removal, so a transient queue-record gap does not delete an active transfer. |
| **H5-R11** | When the download client is unreachable, the tool MUST NOT remove items, even where the \*arr queue is readable. |
| **H5-R12** | Every healing run, dry-run or not, MUST record which items it removed and why, so the action is auditable ([G4](../g-ux/g4-error-model.md)). |
| **H5-R13** | Because removal is followed by a blocklist and re-search, the remedy for a wrongly-removed item MUST be a fresh search that can re-acquire it — no wanted content is abandoned by a removal. |
| **H5-R14** | Classification, dry-run, and healing MUST each be reachable non-interactively. |
| **H5-R15** | Self-healing MUST be able to be switched off while classification remains readable, so the operator can observe without acting. |

## Related

- [C7 Queue health & stuck items](../c-trust/c7-queue-health.md) — the read-only state layer this automates
- [B3 Live dashboard](../b-running/b3-dashboard.md) — where queue depth and stalls surface
- [G4 Error & remedy model](../g-ux/g4-error-model.md) — how flagged items and failures carry a remedy
- [H6 Library cleanup](h6-library-cleanup.md) — the sibling reversible-deletion automation
