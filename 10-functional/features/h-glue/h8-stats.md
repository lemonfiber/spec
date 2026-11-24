---
id: H8
title: Playback statistics
kind: feature
area: H
audience: both
status: accepted
maturity: planned
priority: P3
labels: [stats, verification, wiring]
relates: [D6, G8]
---

# H8 — Playback statistics

**Status:** Accepted · **Audience:** Both · **Area:** H — Ecosystem glue

---

## Purpose

Give the household the playback history and statistics Jellyfin does not ship — what
was watched, when, by whom, on which device, and how much was actually finished — the
Tautulli-equivalent that Jellyfin operators repeatedly ask for and that the media
server itself leaves as a gap. Without it, "what have we been watching?" has no
answer beyond scrolling a resume row, and cleanup and quota decisions elsewhere in
the stack have no history to lean on.

The value is proven data, not a connected dashboard: H8 confirms the media-server
credential is valid *and* that sessions are genuinely ingesting, by querying back a
known recent play. A stats page that shows nothing because nothing was ever captured
is worse than no stats page, because it looks like the truth.

## Behaviour

### It ingests live sessions and backfills history

Going forward, H8 records playback sessions as they happen. For the past, it backfills
from the media server's playback-reporting history where that capability is present —
so the picture is not blank until the day it was switched on.

### It proves ingestion, not just connection

Setup is not complete when a credential authenticates. H8 asserts a **known recent
session can be queried back** from the store it just wrote — closing the loop from the
media server, through ingestion, to a readable record. A valid credential that
produces no queryable data is reported as a broken pipeline, not a healthy one.

### Backfill depends on the reporting capability, and says so

Historical backfill needs the media server's playback-reporting capability enabled. If
it is off, H8 reports that clearly, explains that only forward-looking capture is
available until it is turned on, and does not present a truncated history as complete.

### It respects household privacy

Watch history is personal. Whose statistics a viewer may see is governed by the
privacy stance ([G8](../g-ux/g8-privacy.md)) and household identity
([D6](../d-content/d6-household-identity.md)), and children's data is handled with
the same care as elsewhere in the stack. Statistics are never shipped off the box to a
third party to be computed.

**A member sees their own history, and nobody else's.** It is told in the household's
words: what they watched, when, and how far through. Another member is never answered
it, and neither is the operator. Running the stack is not a reason to read what
somebody watched, so what the operator is answered is whether the statistics work —
ingestion, backfill and the query-back proof — and no title anybody watched. Where
cleanup gives the household's watching of a title as its evidence, it names nobody.

Two people can turn it off. The operator can turn members' history off for the whole
household, a setting that is on until they do. While it is off, nothing is kept per
member: each play is counted only into totals that name nobody, and cleanup and the
statistics work from those. Each member is told it is off, and no member is answered
a history. What was kept per member before it was turned off is answered to nobody,
and goes when the statistics' records of its age go. A member can hide their own;
hidden, it is answered to nobody, them included, until they show it again, so a phone
or a screen in a shared room shows none of it.

### It presents figures the media server does not

- **Completion, not just starts** — how much of a title was actually watched
- **Per-member and per-device patterns** — within what privacy allows
- **Trends over time** — active nights, most-watched, longest-idle titles
- **Signals other features can lean on** — history that informs cleanup and quotas

### It handles awkward reporters honestly

A device that reports playback oddly — no progress events, duplicated sessions, a
paused stream left open for hours — is reconciled rather than trusted blindly, so one
misbehaving client does not corrupt the totals.

### Every step has a non-interactive equivalent

Ingestion status, the backfill and the query-back proof are each reachable as plain
subcommands, and so is a member's own history, to that member, so stats can be wired
into reporting without a prompt.

### On the companion

*Backfill depends on the reporting capability, and says so* is `N11-R1` on this
surface ([N11](../n-companion/n11-the-record.md)): the history's horizon is
stated, and the end of what is kept is never presentable as nothing having
happened. A chart that simply begins in March is indistinguishable, on a phone,
from a household that watched nothing before March — and the operator will draw
the second conclusion unaided if the first is not said.

*It handles awkward reporters honestly* meets `N11-R9`: an empty record and a
record that could not be read are different answers. A reporter that quietly
stopped answering produces a flat line, and a flat line is the most believable
wrong figure this feature is able to produce.

## States

| State | Meaning |
|-------|---------|
| `unconfigured` | No stats source connected; offers to wire the media server |
| `verifying` | Confirming the credential and querying back a known session |
| `ingesting` | Live sessions recording and readable |
| `backfilled` | Historical import complete via the reporting capability |
| `forward-only` | Reporting capability off; only new sessions captured, stated plainly |
| `degraded` | The media server unreachable; last-known stats shown as such, not as current |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Playback-reporting capability disabled | Report that backfill is unavailable and only forward capture works; never present a partial history as complete. |
| Credential valid but nothing ingesting | Fail the query-back proof and report a broken pipeline, rather than showing an empty page as if it were the truth. |
| Multi-user household viewing another member's history | Gate visibility through the privacy stance and household identity; do not expose one member's watch data to another by default. |
| Children's watch data | Handle under the same protections as parental data elsewhere; never surface it beyond what the household's rules allow. |
| Very large library or long history | Backfill and query incrementally; never block or exhaust the host importing years of sessions at once. |
| Device reports no progress events | Record the start but mark completion unknown rather than assume fully watched or not watched. |
| Duplicated or overlapping sessions from one client | Deduplicate against the known session rather than double-count the watch. |
| Paused stream left open for hours | Reconcile the idle tail so an abandoned pause does not read as hours of viewing. |
| Media server unreachable at query time | Show last-known statistics marked as such, distinct from current, and never as live. |
| Statistics requested for a member with no history | State "no recorded playback" explicitly rather than render an empty chart as zero activity. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **H8-R1** | The tool MUST record live playback sessions from the media server and make them readable. |
| **H8-R2** | The tool MUST authenticate to the media-server API and MUST assert a known recent session can be queried back from the store, reporting a valid credential with no queryable data as a broken pipeline. |
| **H8-R3** | Historical backfill MUST use the media server's playback-reporting capability, and when that capability is disabled the tool MUST report backfill as unavailable rather than present a partial history as complete. |
| **H8-R4** | Whose statistics a viewer may see MUST be governed by the privacy stance and household identity, and one member's watch data MUST NOT be exposed to another by default. |
| **H8-R5** | Children's watch data MUST be handled under the same protections as parental data elsewhere in the stack. |
| **H8-R6** | Playback statistics MUST NOT be shipped off the box to a third party for computation. |
| **H8-R7** | The tool MUST report completion, not only that a title was started. |
| **H8-R8** | A device that reports no progress events MUST have its completion recorded as unknown rather than assumed watched or unwatched. |
| **H8-R9** | Duplicated or overlapping sessions from one client MUST be deduplicated rather than double-counted. |
| **H8-R10** | An idle or paused stream left open MUST be reconciled so it does not read as continuous viewing. |
| **H8-R11** | Backfill of a large history MUST proceed incrementally and MUST NOT block or exhaust the host. |
| **H8-R12** | When the media server is unreachable, last-known statistics MUST be shown marked as such and MUST NOT be presented as current. |
| **H8-R13** | Statistics for a member with no recorded playback MUST be stated explicitly, not rendered as an empty chart implying zero activity. |
| **H8-R14** | Ingestion status, backfill and the query-back proof MUST each be reachable non-interactively, and so MUST a member's own history, to that member (`H8-R15`). |
| **H8-R15** | A member MUST be answered their own viewing history alone — each title, when they watched it and how far through, in the household's words — and MUST NOT be answered another's. The operator MUST be answered whether the statistics work, ingestion, backfill and the query-back proof among it, and MUST NOT be answered what any member watched; the household's watching of a title, where cleanup gives it as evidence (`H6-R2`), MUST name no member. |
| **H8-R16** | The operator MUST be able to turn members' viewing history off, as a core setting that is on where none is recorded. While it is off, nothing MUST be kept per member: a play MUST be counted only into totals that name no member, and cleanup and the statistics MUST work from those; no member MUST be answered a history, and each MUST be told it is off. What was kept per member before MUST be answered to nobody, and MUST go when the statistics' records of its age go. |
| **H8-R17** | A member MUST be able to hide their own viewing history and show it again; while it is hidden, it MUST be answered to nobody, that member included. |

## Related

- [D6 Household identity & invitations](../d-content/d6-household-identity.md) — whose history is whose
- [G8 Privacy stance](../g-ux/g8-privacy.md) — the watch-data posture statistics must honour
- [D8 Parental controls](../d-content/d8-parental-controls.md) — the care owed to children's viewing data
- [H6 Library cleanup](h6-library-cleanup.md) — a consumer of watch history for cleanup decisions
- [B3 Live dashboard](../b-running/b3-dashboard.md) — the live view these statistics complement
