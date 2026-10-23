---
id: N31
title: Asking the indexers
kind: feature
area: N
audience: operator
status: accepted
maturity: built
priority: P2
labels: [mobile, queue, verification]
requires: [N1, N2, N8, D9]
relates: [D2, D3, N23, N24]
---

# N31 — Asking the indexers

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

A trace that stops at *monitored, nothing grabbed* leaves one question the stack cannot
answer from what it holds: is there nothing at the quality chosen, or nothing at all? The
command line answers it by asking the indexers, which spends one search of their daily
allowance. This page puts that question on the phone, under the trace that raised it, on
the terms the stack sets (`N1-R2`).

## Behaviour

### Asked under the trace that needs it, and only there

Where a trace stopped at *monitored* and the stack says a search would settle it, the
trace on the phone offers asking the indexers, carrying the same title and season the trace
was read with. The stack says so on the trace itself, with what the search spends
(`ARCH-R290`); a trace that stopped anywhere else offers nothing, because the stack would
spend nothing and answer the same trace again.

Pressed, it asks first: that this spends one search of the indexers' daily allowance, and
that the search covers what the curator wants at the quality in force, not this title alone
(`N2-R8`). There is no rehearsal: a rehearsed search would still spend the search.

### The answer is the trace, told more exactly

Agreed, the app sends `search`, follows the job, and draws the trace again as it came back:
*nothing at your quality* told apart from *nothing at all*, and a search that settled nothing
— an indexer failing — said as that and never as an absence (`D2-R12`, `N24-R8`). Account
trouble the stack attaches to the stall, an indexer capped or resting, is drawn with it.

### A season is followed, as the command line follows one

The trace read takes a season, and the phone sends the season a trace was opened on, so a
search after it asks about the same season.

## States

| State | Meaning |
|---|---|
| Can be asked | The trace stopped at *monitored*; the stack says a search would settle it and what it spends. |
| Asking | What the search spends and covers, before it is sent. |
| Running | The job the stack accepted, followed until it ends. |
| Answered | The trace again: nothing at the quality, nothing at all, or unsettled. |
| Refused | The stack's refusal and remedy, drawn as a refusal. |

## Edge cases

| Situation | Behaviour |
|---|---|
| The indexers' allowance is spent | The stack's own finding says so; the app adds nothing of its own. |
| The trace moved on before the answer | The answer is drawn as the stack returned it, with the stage it reached. |
| A member's view | Never offered: the trace is the operator's (`N8-R8`). |

## Requirements

| ID | Requirement |
|---|---|
| **N31-R1** | A trace the stack says a search would settle MUST offer asking the indexers, with the title and season the trace was read with, and no other trace MUST offer it (`ARCH-R290`). |
| **N31-R2** | Before a search is sent, the app MUST state what it spends and that it covers what the curator wants at the quality in force, as the stack reports them, and MUST NOT offer a rehearsal (`N2-R8`). |
| **N31-R3** | A search MUST be followed to its end and the trace drawn again as it came back, telling nothing at the quality chosen from nothing at all, and an unsettled search from either (`D2-R12`, `N24-R8`). |
| **N31-R4** | A trace MUST be read with the season it was opened on, and a search after it MUST carry that season. |

## Related

- [N8](n8-what-comes-in.md) — what a trace shows
- [N2](n2-operator-companion.md) — a disruptive action says what it disturbs first
- [D9](../d-content/d9-pipeline-trace.md) — the trace
- [D2](../d-content/d2-quality-presets.md) — nothing at the quality is not an indexer failing
