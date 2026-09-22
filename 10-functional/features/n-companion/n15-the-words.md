---
id: N15
title: The words, and watching it happen
kind: feature
area: N
audience: operator
status: draft
maturity: planned
priority: P3
labels: [mobile, ux, queue]
requires: [N1, G2]
relates: [A2, A4, D3, D9, N2, N8]
---

# N15 — The words, and watching it happen

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Three things that make the difference between a surface somebody can use and one
they put down, and none of them is a feature anybody asks for by name.

The **words**: lemonfiber has a vocabulary of its own and a glossary that
explains it, and a phone is where somebody meets an unfamiliar word with nobody
beside them to ask.

**Watching something happen**: a job moves through named stages, and the first
acquisition is narrated end to end. A progress bar says a thing is happening; a
stage says what.

**What setup settled**: where the library lives, which protocols are on, who the
stack runs as. Reading those is not performing setup, and the difference matters
because it is easy to read `N1-R4` as putting the whole subject off the phone.

## Behaviour

### Reading what setup settled is not offering setup

`N1-R4` forbids the app **offering** first-run setup, for a structural reason: a
phone cannot perform the act that makes a phone able to perform acts. It does not
forbid showing what setup decided, and it says so by pairing with
[A4](../a-getting-started/a4-reconfiguration.md), which is offered in full.

So the data root, the protocols and the service user are shown as facts about the
stack. Changing them is reconfiguration and is offered; performing first-run
setup is not, and where an operator arrives at it the refusal carries the reason
rather than the option simply being absent.

### An unfamiliar word explains itself where it is used

The glossary is on the wire — each word with a short gloss, a longer one, and
what else it is called. A word explained on a page the operator has to go and
find is a word that does not get looked up on a phone.

The short form is what appears in place. The longer one is available and does not
lead.

### What a thing is also called is part of what it means

The vocabulary carries alternative names, and they are what somebody arriving
from another tool will search for. Showing only the term lemonfiber prefers makes
the glossary useful to people who already know the answer.

### A stage is not a percentage

A job is choosing, searching, grabbing, downloading, importing, scanning, or
available. Those are the answer to *what is it doing*, and a bar that fills
without them answers *is it stuck* at best.

Where the contract gives a stage, the stage is what is shown.

### The first one is narrated, and the narration is kept

The first acquisition is walked through end to end, and what it said is carried
rather than reconstructed. An operator who looked away does not get a different
story when they look back.

Where it finished, what to do next is named — the handover the contract carries
rather than a dead end at the moment somebody has just succeeded at something.

### Already here is an outcome, not a failure

Asking for something the stack already has is a normal thing to do and the
contract says so. It is reported as what it is, rather than as a search that
found nothing.

### Nothing here invents a word

The app renders the vocabulary it is given. It does not translate lemonfiber's
terms into its own, and it does not explain a word the glossary does not carry —
a second vocabulary is a second thing to keep in step, and the one that falls
behind is the one on the phone (`N1-R1`).

## States

| State | Meaning |
|-------|---------|
| Running | A job is at a named stage. |
| Narrating | A walkthrough is in progress, with what it has said so far. |
| Already here | What was asked for was already present. Reported as such. |
| Settled | Setup's decisions are shown as facts; changing them is reconfiguration. |
| Unknown | A stage, the glossary or setup's state could not be read. Never rendered as idle. |

## Edge cases

- **A word used in a finding that the glossary does not carry.** Shown as it
  came, unexplained, rather than given a definition the app made up.
- **A walkthrough that ran while the app was closed.** Its lines are shown as a
  record, not replayed as though they were arriving.
- **A job that moved backwards a stage.** Shown as the stage it is at; the app
  does not treat progress as monotonic when the contract does not.
- **An operator reaching first-run setup from the app.** Declined with the
  reason, per `N1-R4`, and never rendered as a missing feature.

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N15-R1** | What setup settled MUST be shown as facts about the stack, and showing them MUST NOT be treated as offering first-run setup. |
| **N15-R2** | Where an operator reaches first-run setup, it MUST be declined with the reason (`N1-R4`) rather than being absent. |
| **N15-R3** | A word the glossary carries MUST be explainable where it is used, with the short form in place and the longer one available without leading. |
| **N15-R4** | What a word is also called MUST be shown, and MUST be searchable. |
| **N15-R5** | Where the contract gives a job's stage, the stage MUST be shown, and a progress indicator MUST NOT stand in for it. |
| **N15-R6** | A walkthrough's lines MUST be carried as given and MUST NOT be reconstructed or reordered. |
| **N15-R7** | Where a walkthrough names what to do next, that MUST be shown. |
| **N15-R8** | *Already here* MUST be reported as its own outcome and MUST NOT be rendered as a search that found nothing. |
| **N15-R9** | The app MUST NOT define a word the glossary does not carry, and MUST NOT substitute its own term for one the vocabulary gives. |
| **N15-R10** | A stage, glossary or setup state that could not be read MUST be told apart from idle. |

## Related

- [N1](n1-companion-app.md) — parity, and why first-run setup stays at the machine
- [N2](n2-operator-companion.md) — findings, which use these words
- [N8](n8-what-comes-in.md) — where a thing got to, in the operator's terms
- [G2](../g-ux/g2-plain-language.md) — the vocabulary and the glossary
- [A2](../a-getting-started/a2-setup-wizard.md) — setup, performed at the machine
- [A4](../a-getting-started/a4-reconfiguration.md) — changing what setup settled
- [D3](../d-content/d3-first-content.md) — the first acquisition, narrated
