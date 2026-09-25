---
id: N24
title: Choosing how good, and trying one
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P2
labels: [mobile, quality, transcoding, ux]
requires: [N1, D2, D3]
relates: [N8, N15, N19]
---

# N24 — Choosing how good, and trying one

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Two acts that decide what the stack fetches, and both are questions an operator
answers in the evening, on a sofa, with the television in front of them.

[D2](../d-content/d2-quality-presets.md) asks *how good should this look, and how
much disk am I willing to spend*. [N8](n8-what-comes-in.md) already says how a
choice is shown: by what an hour of it costs (`N8-R1`), by whether this machine
must transcode it (`N8-R2`), and by what became of it (`N8-R3`). This page is the
choosing.

[D3](../d-content/d3-first-content.md) proves the pipeline end to end by
fetching one thing and narrating it. [N15](n15-the-words.md) already says how the
narration is carried (`N15-R5` to `N15-R8`). This page is starting one, leaving
it, and what a walk that stopped owes the operator.

## Behaviour

### A preset is chosen here, overall and per kind of media

The operator picks a preset in plain language, for everything or for one kind of
media set apart from the rest. Media with no resolution — music — is chosen in
its own terms, its format and what that means, and is never offered as a
resolution.

### A choice this machine cannot play smoothly is held, and asked about again

Where a preset would have this machine transcode in software, the stack holds the
choice rather than recording it, and says why. The app shows the hold and its
reason and asks for the confirmation separately. Viewing a held choice is not
agreeing to it.

### Choosing is for what comes next; upgrading is its own act

A new preset shapes what is fetched from now on. Fetching better copies of what
is already in the library is a different act with a different cost, and the app
offers it apart — described first, per kind of media, and carried out only when
it is confirmed.

### A hand-edited configuration is not put back from here

Where the operator edited the quality configuration by hand, the stack treats
the preset as no longer in charge until it is deliberately re-asserted. The app
shows the configuration as edited and respected (`N19-R3`) and does not offer the
re-assert: its only purpose is to overwrite what the operator changed, which
`N19-R4` keeps off this surface.

### A walkthrough starts here, whenever it is wanted

It is not only the end of setup (`D3-R13`). The operator names something to
fetch, or names nothing and lets the stack pick something likely to work, and
starts it. A stack that acquires nothing is offered the walk that fits it.

### Leaving does not stop it

A walkthrough the operator walks away from goes on: whatever was downloading keeps
downloading. The app says so when it is left, and on returning shows where it got
to rather than starting again (`D3-R7`).

### A walk that stopped says where, why, and the one thing to try

The stack names the step, the reason, the remedy, and what the services involved
were saying at the time. All four are shown together, the logs inline. *Nothing
matched* and *the indexers would not answer* are different reasons and are never
one message (`D3-R5`).

### A copy is not a link, and the difference costs room

Where the import copied the file rather than linking it, it now exists twice and
every import costs its size again. The app shows which happened (`D3-R8`).

## States

| State | Meaning |
|-------|---------|
| Held | A preset needs confirming because this machine would transcode it. |
| Recorded | The stack took the choice. |
| Upgrade described | What upgrading would come to, per kind of media. Nothing started. |
| Walking | A walkthrough is at a named step. |
| Left | The operator left; what was in flight is still in flight. |
| Stopped | At a named step, with the reason, the remedy and the logs. |
| Complete | In the library and playable. |

## Edge cases

- **A preset chosen for films only.** Television keeps the overall choice, and
  both are shown.
- **A walkthrough asked for with an empty library and nothing named.** The stack
  picks, and its suggestions are shown if it could not.
- **A walkthrough started, the app closed, the thing arrived.** The finished walk
  is shown as a record, not replayed (`N15`).
- **An upgrade described and never confirmed.** Nothing was fetched.

## Requirements

| ID | Requirement |
|----|-------------|
| **N24-R1** | The app MUST offer choosing a quality preset for everything and for a single kind of media, in the stack's plain terms (`D2-R1`, `D2-R5`). |
| **N24-R2** | Media the stack reports without a resolution MUST be offered in the terms the stack gives it, and MUST NOT be offered as a resolution (`D2-R11`). |
| **N24-R3** | A choice the stack held because this machine would transcode it MUST be shown with the reason, and confirming it MUST be an act distinct from viewing it (`D2-R4`). |
| **N24-R4** | Upgrading what is already in the library MUST be offered as its own act, apart from choosing a preset, and MUST be described per kind of media before it is confirmed (`D2-R6`, `D2-R7`). |
| **N24-R5** | Where the quality configuration was edited by hand, the app MUST show it as edited and respected (`N19-R3`), and MUST NOT offer re-asserting the preset over it (`N19-R4`). |
| **N24-R6** | The app MUST offer starting a walkthrough at any time, for an item the operator names or for one the stack picks, and MUST offer the walk the stack gives for a stack that acquires nothing (`D3-R9`, `D3-R13`). |
| **N24-R7** | Leaving a walkthrough MUST NOT cancel it; the app MUST say so when it is left, and MUST show where it got to when it is returned to (`D3-R7`). |
| **N24-R8** | A walkthrough that stopped MUST show the step, the reason, the remedy and the services' logs together, and *nothing matched* MUST NOT be rendered as the indexers failing (`D3-R4`, `D3-R5`). |
| **N24-R9** | Where an import copied rather than linked, the app MUST say so (`D3-R8`). |
| **N24-R10** | A rehearsed choice MUST be labelled as a rehearsal (`N6-R1`), and MUST NOT be presented as recorded. |

## Notes

**What the contract carries.**

| Row | Carried | Not carried |
|---|---|---|
| `N24-R1` | `quality-set`, taking a preset and a media type; `quality` lists the choices in force, overall first | — |
| `N24-R2` | `quality.music` and `music`: `format`, `means`, `size_per_hour` | — |
| `N24-R3` | `disposition: held`, and `needs_transcoding_here` and `transcoding` per choice | — |
| `N24-R4` | `quality-upgrade`, unconfirmed and confirmed; `upgrade` per media type: `preset`, `size_per_hour`, `outcome` | What an upgrade costs in total. `D2-R7` asks for the cost stated; the contract carries a rate per hour, not a sum. A statement that choosing affects future acquisitions only (`D2-R6`) is not carried as words |
| `N24-R5` | `customised` | — |
| `N24-R6` | `walkthrough`, with an optional item; `shape`: `pipeline` or `library-only`; `suggestions` | — |
| `N24-R7` | `in_background`, and `state: abandoned` — *whatever was in flight stays in flight* | — |
| `N24-R8` | `stopped`: `step`, `reason`, `remedy`, `logs`; `reason` keeps `nothing-matched` apart from `indexers-failed` | — |
| `N24-R9` | `link`: `hardlinked` or `copied` | — |
| `N24-R10` | `disposition: rehearsed` | — |

**D2-R10 is not a row.** Comparing a preset's projected size with the room
there is asks for a sum the contract does not carry: `size_per_hour` is a rate,
and nothing says how many hours a library is. `N2-R14` forbids the app working
one out.

**`quality-reapply` is not offered, and `N24-R5` is why.** The stack offers it
at other surfaces; its whole effect is overwriting a hand-edit, and `N19-R4` is
the requirement that says the app does not offer that.

## Related

- [N1](n1-companion-app.md) — parity, and what the app may claim
- [N8](n8-what-comes-in.md) — how a quality choice is shown
- [N15](n15-the-words.md) — how a walkthrough's narration is carried
- [N19](n19-getting-underneath-it.md) — an edited file is respected
- [D2](../d-content/d2-quality-presets.md) — quality presets in plain language
- [D3](../d-content/d3-first-content.md) — the first-content walkthrough
