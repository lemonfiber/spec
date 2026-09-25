---
id: N26
title: What the glue is doing
kind: feature
area: N
audience: both
status: accepted
maturity: planned
priority: P3
labels: [mobile, verification, observability, stats, ux]
requires: [N1, H1, H2, H3, H6, H8, K1]
relates: [N2, N3, N4, N8, N11, N12, N16, N24]
---

# N26 — What the glue is doing

**Status:** Draft · **Audience:** Both · **Area:** N — Companion

---

## Purpose

Area H is the automation people bolt onto a media stack by hand — cross-seeding,
announce-driven grabbing, quality-profile sync, library cleanup, playback
statistics — and [K1](../k-observability/k1-metrics.md) is the metrics pipeline
beside it. Five of the six share one rule: **they prove the wiring rather than
trusting it**, and a configuration that has not proven itself is *unproven*,
never *ready*. Cleanup has a gate in its place — a dry run, then a confirmation.

That rule is the one a small screen loses first. An automation that is running
looks, from a phone, exactly like one that is working, and every one of these
fails by looking fine. So what this page asks of the app is mostly the same
thing each time: show the proof, keep *unproven* apart from *ready*, and offer the
acts each feature makes reachable without a terminal.

Queue self-healing ([H5](../h-glue/h5-queue-selfheal.md)) is not here:
[N16](n16-nobody-was-looking.md) already shows what it would do and did
(`N16-R8` to `N16-R11`), and keeps its acts off the app (`N16-R12`).

## Behaviour

### Unproven is its own answer, everywhere on this page

Five of these end their wiring with a proof against real data — a match for a
real local item, a real announce line through a test filter, a read-back of the
scores that were written, a known recent play queried back, a series present in
the store. Where the proof has not held, the feature is unproven, and the app
shows that as its own state. *Running* is never shown in its place.

### Cross-seeding: a match is the data, not the name

A candidate is a match only when the files, sizes and pieces agree
([H1](../h-glue/h1-cross-seed.md)). A near-miss — an extra folder, a stray small
file — is a near-miss, and a partial match is partial with its missing pieces
named. Neither is added as a seed, and neither is counted as one here. An indexer
that failed during a pass is named as failed for that pass while the others go
on; a client credential that failed its proof halts additions, and the app says
additions are halted rather than that nothing was found.

The operator can start a search, list what it matched and run the proof from here.

### Announce-driven grabbing: a quiet channel and a dead one are different

Each announce channel has a connection state and an idle time
([H2](../h-glue/h2-autobrr.md)). A disconnected watcher looks like a quiet night
until a missed release proves otherwise, so the app shows both, per channel, and
never shows a disconnected channel as watching.

A filter that has matched nothing over its window is a dead rule until shown
otherwise. A filter at its grab cap is holding, not failing. A match whose
destination was unreachable is held, not dropped. Each is shown as itself. The
operator can reload filters, replay an announce line through them, and run the
proof from here.

### Quality-profile sync: the preview is the decision, and the read-back is the result

A sync is previewed before it is applied — every create, update and, where
pruning is on, every removal, with the score it changes
([H3](../h-glue/h3-quality-sync.md)). The app shows the preview and applies only
the plan that was previewed. Afterwards, success is what the read-back confirmed,
instance by instance: a write the service accepted and the read-back did not
find is a failure, and another tool rewriting the same instance is a conflict,
not a reason to apply again.

### Library cleanup: the evidence travels with the candidate

A cleanup candidate is chosen from what the household watched and asked for, and
carries the rule that chose it, the room it gives back and the evidence behind it
([H6](../h-glue/h6-library-cleanup.md)). The app shows all three with each
candidate, and shows only the evidence the stack gave: a child's viewing is not
evidence the stack gives, and the app has no other source. A series is shown as
its members, each with its own evidence, never as one row to delete. A
confirmation covers the plan it was given; where the stack re-presents a plan
because the candidates changed, it is a new plan asking for a new confirmation.

[N12](n12-making-room.md) already forbids the app proposing a set, pre-selecting,
or acting on a threshold (`N12-R4`, `N12-R9`).

### Playback statistics: whose, and how sure

What was watched, by whom and how far through is the household's most personal
record ([H8](../h-glue/h8-stats.md)). Whose statistics a person may see is the
core's answer for the identity signed in, and the app holds no rule of its own
about it (`N3-R2`). A device that reports no progress gives *unknown*, not
*watched* and not *unwatched*. Somebody with no recorded playback is said to have
none rather than shown an empty chart, and a history that begins where backfill
could not reach says where it begins (`N11-R1`).

What somebody watched is never in a notification and never drawn behind the
lock.

### Metrics: the pipeline's proof is shown here; the dashboards are not

The metrics pipeline proves three things: each target is up in the collector,
each service's series are present in the store, and each curated dashboard's
panels resolve against real data ([K1](../k-observability/k1-metrics.md)). The
app shows each, per target and per dashboard, with the remedy for each failure.
A running exporter is not a healthy target, a service with no exporter is
unmonitored rather than covered, and a collector scraping without retaining is
not a healthy pipeline. The retention bound and the projected growth of the store
are shown. Regenerating targets and dashboards, and running the proof, are
offered from here.

**The dashboards themselves are not drawn in the app.** They are a bundled
renderer's own screens, generated as files from the stack's definition
(`K1-R4`), and lemonfiber's other surfaces do not draw them either. Drawing them
here would mean the app holding a second copy of every provisioned query, which
drifts from the first the day a dashboard is regenerated, and the app renders the
core's answers rather than keeping copies of its own (`N1-R1`). Where the stack
gives the renderer's address, the app offers it as that address; it never builds
one.

## States

| State | Meaning |
|-------|---------|
| Unproven | Wired, and the proof has not held. Never shown as ready or running. |
| Ready | The proof held against real data. |
| Holding | A cap or an unreachable destination is holding matches. Not failing. |
| Near-miss | A cross-seed candidate that differs in layout. Not a match. |
| Previewed | A sync or cleanup plan shown. Nothing applied. |
| Conflict | Another tool wrote the same instance. Not re-applied. |
| Unmonitored | A service with no exporter. Not covered. |
| Unknown | The state could not be read. Never shown as ready. |

## Edge cases

- **A cross-seed pass where one indexer drops mid-way.** That indexer is failed
  for the pass; the matches the others found stand.
- **A filter authored to match everything.** Still capped; the cap is shown
  holding rather than the filter shown as healthy.
- **A catalogue source unreachable during a sync.** Nothing was applied, and the
  instance is shown untouched rather than partly synced.
- **A cleanup item removed by hand before the plan ran.** Already gone, not a
  failed deletion.
- **A member with no recorded playback.** Said, not charted as zero.
- **A target inside the VPN namespace.** Its state is the collector's, across the
  path it is scraped on; it is not shown down for being inside the tunnel.

## Requirements

| ID | Requirement |
|----|-------------|
| **N26-R1** | Where one of these features reports a proof that has not held, the app MUST show it as unproven, and MUST NOT show it as ready or as running (`H1-R8`, `H2-R6`, `H3-R5`, `H8-R2`, `K1-R14`). |
| **N26-R2** | The app MUST offer starting a cross-seed search, listing its matches and running its wiring proof (`H1-R14`). |
| **N26-R3** | A cross-seed near-miss and a partial match MUST each be shown as such, the partial one with its missing pieces, and neither MUST be counted as a match (`H1-R9`, `H1-R10`). |
| **N26-R4** | An indexer that failed during a pass MUST be named as failed for that pass, and a failed client credential MUST be shown as halting additions (`H1-R11`, `H1-R13`). |
| **N26-R5** | Each announce channel MUST be shown with its connection state and idle time, and a disconnected channel MUST NOT be shown as watching (`H2-R9`). |
| **N26-R6** | A filter that has matched nothing over its window, a filter holding at its cap, and a match held for an unreachable destination MUST each be shown as itself, and MUST NOT be flattened into healthy or failed (`H2-R7`, `H2-R11`, `H2-R13`). |
| **N26-R7** | The app MUST offer reloading filters, replaying an announce line through them, and running the wiring proof (`H2-R14`). |
| **N26-R8** | The app MUST offer previewing a quality-profile sync, showing every create, update and removal with its score change, and MUST offer applying only the plan that was previewed (`H3-R3`, `H3-R7`, `H3-R14`). |
| **N26-R9** | A sync MUST be shown as succeeded, instance by instance, only where the read-back confirmed it, and a conflict with another tool MUST be shown as a conflict (`H3-R4`, `H3-R10`, `H3-R11`). |
| **N26-R10** | A cleanup candidate MUST be shown with the rule that selected it, the space it reclaims and the evidence the stack gave, and the app MUST NOT show evidence from any other source (`H6-R2`, `H6-R9`). |
| **N26-R11** | A series or collection MUST be shown as its members, each with its evidence, and an item already removed by other means MUST be shown as already gone rather than as a failed deletion (`H6-R12`, `H6-R13`). |
| **N26-R12** | A confirmation MUST cover only the cleanup plan it was given; a plan the stack re-presents MUST be confirmed afresh, and a run with no candidates MUST be said to have none (`H6-R3`, `H6-R11`, `H6-R15`). |
| **N26-R13** | Whose playback statistics are shown MUST be the core's answer for the identity signed in, and the app MUST NOT hold a rule of its own about it (`H8-R4`, `N3-R2`). |
| **N26-R14** | Completion a device did not report MUST be shown as unknown, a person with no recorded playback MUST be said to have none, and where backfill is unavailable the app MUST say where the history begins (`H8-R3`, `H8-R8`, `H8-R13`, `N11-R1`). |
| **N26-R15** | What somebody watched MUST NOT appear in a notification or in anything drawn while the app is locked (`H8-R5`, `N4-R10`, `N4-R24`). |
| **N26-R16** | The metrics pipeline MUST be shown per target and per dashboard as up, series present and rendering, each failure with its remedy; a service with no exporter MUST be shown as unmonitored, and a collector that scrapes without retaining MUST NOT be shown as healthy (`K1-R5`, `K1-R6`, `K1-R7`, `K1-R11`, `K1-R12`). |
| **N26-R17** | The metrics store's retention bound and projected growth MUST be shown (`K1-R9`). |
| **N26-R18** | The app MUST offer regenerating scrape targets and dashboards, and running the pipeline proof (`K1-R13`). |
| **N26-R19** | The app MUST NOT draw the metrics dashboards or their series, and MUST say that they are the renderer's own screens; it MUST offer the renderer's address only where the stack gives one, and MUST NOT construct one. Drawing them would hold a second copy of every provisioned query (`K1-R4`), and the app renders the core's answers rather than copies of them (`N1-R1`). |

## Notes

**The contract carries none of this.** Every feature on this page is planned, and
no envelope the stack publishes is about any of them: nothing names a cross-seed
match, an announce channel, a profile sync, a cleanup candidate, a playback or a
metric. Every row here waits on the contract, and `N1-R17` stops the work until
it carries what the row needs. Nearby envelopes are not substitutes:

| Feature | Nearest envelope | Why it does not answer |
|---|---|---|
| `H1` | `stop-seeding` | One torrent's standing and ratio. Nothing about matches, near-misses or the proof |
| `H2` | — | Nothing |
| `H3` | `quality`: `customised`, `overwritten` | The preset's configuration and whether it was hand-edited. No diff of custom formats or scores, no read-back |
| `H6` | `space` | Candidates for reclaiming room by standing. Not chosen from watch data, and no rule or evidence |
| `H8` | `history` | The record of changes to the stack, not of playback |
| `K1` | `dashboard.telemetry` | Whether the dashboard screen is current. Not a metric, a target or a series |

`N26-R19` is the one exclusion on this page, and it is written as one because
parity is otherwise the rule (`N1-R2`). The pipeline's *proof* is offered here in
full; the *dashboards* are a bundled service's own screens, which no lemonfiber
surface draws.

## Related

- [N1](n1-companion-app.md) — parity, and rendering the core's answers
- [N12](n12-making-room.md) — removal, and what the app may not propose
- [N16](n16-nobody-was-looking.md) — queue self-healing
- [N11](n11-the-record.md) — a record's horizon
- [N3](n3-household-companion.md) — what a member sees
- [N4](n4-native-integration.md) — notifications and the lock
- [N24](n24-choosing-and-trying.md) — choosing a quality preset
- [H1](../h-glue/h1-cross-seed.md), [H2](../h-glue/h2-autobrr.md), [H3](../h-glue/h3-quality-sync.md), [H6](../h-glue/h6-library-cleanup.md), [H8](../h-glue/h8-stats.md) — the glue
- [K1](../k-observability/k1-metrics.md) — metrics and dashboards
