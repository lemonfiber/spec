---
id: E5
title: Changelog & release notes
kind: feature
area: E
audience: operator
status: accepted
tracks: v1
priority: P2
labels: [updates, verification]
relates: [E1, E2]
---

# E5 — Changelog & release notes

**Status:** Accepted · **Audience:** Operator · **Area:** E — Maintenance

---

## Purpose

An operator deciding whether to update needs to know *what changed and whether it
affects them* — not read a diff. A changelog answers that, but only if it is
trustworthy: hand-written notes drift from what shipped, omit the boring-but-
breaking change, and never say which feature a line belongs to. This feature makes
the changelog a **generated, traceable record** — every entry derived from the
commits that shipped, and linked back to the requirement and the version it
served — so "what changed" is answered the same way everywhere the operator meets
it: the release page, `lemonfiber` telling them an update exists, and the stack
update flow.

## Behaviour

### It is generated from what shipped, not written by hand

The changelog for a version is produced from that version's commits, grouped by
area, rather than maintained as prose someone remembers to edit. Because commits
already name the requirement they satisfy, the generator has the identifiers it
needs; nothing is added to the changelog that did not ship, and nothing that
shipped is silently absent.

### Each entry traces to a feature and a version

An entry names the feature area it belongs to and links the requirement it
satisfied and the version that shipped it. The mapping is the point: an operator
reading "the VPN panel now shows the forwarded port" can reach the feature it
came from and the release it landed in, and a maintainer can see every change a
given feature has accrued across releases.

### The operator meets it where the decision is made

The same changelog surfaces at the moments an operator weighs an update: when
[lemonfiber offers its own update](e2-self-update.md), and when it offers a
[stack update](e1-stack-updates.md). "What changed" is one record, shown in
context, not a link the operator must go hunting for.

### Hotfixes and withdrawals are visible, with their reason

A patch release appears with the fix it carried; a yanked release appears marked
withdrawn with why. A changelog that quietly omits a hotfix or hides a withdrawal
is worse than none, because it teaches the operator not to trust it.

### It reads in plain language

Entries are written for the operator, not the committer: the human-facing summary
leads, and the identifiers are the link target, not the headline
([G2](../g-ux/g2-plain-language.md)).

## States

| State | Meaning |
|-------|---------|
| `current` | The changelog matches the shipped releases; every release has notes |
| `pending` | A release exists whose notes have not yet been generated |
| `stale` | The changelog and the release record disagree — flagged, not shown as current |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| A commit cites no requirement | It is a maintenance/chore entry; group it as such rather than dropping it, so the record stays complete. |
| A requirement shipped across several releases | Each release's entry links the same requirement; the feature view shows the full history. |
| A release with no user-facing change | Say so explicitly (e.g. "internal only") rather than emitting an empty release. |
| A yanked release | Mark it withdrawn with the reason; never silently remove it from the record. |
| A hotfix off an old tag | Appears against the patched version, not the current train, with its cited fix. |
| The generated notes and the release tags disagree | Enter `stale` and flag it; never present a changelog that contradicts what shipped. |
| A requirement was withdrawn after it shipped | The historical entry stays (it did ship); the withdrawal is recorded, not erased. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **E5-R1** | Every release MUST have changelog notes, and they MUST be generated from that release's commits rather than hand-maintained. |
| **E5-R2** | The generator MUST NOT include a change that did not ship, and MUST NOT omit a change that did. |
| **E5-R3** | Each entry MUST identify the feature area it belongs to and link the requirement it satisfied. |
| **E5-R4** | Each entry MUST link the version that shipped it, and a requirement spanning several releases MUST link each. |
| **E5-R5** | A commit that cites no requirement MUST still appear, grouped as maintenance, so the record is complete. |
| **E5-R6** | The changelog MUST be shown in the [self-update](e2-self-update.md) and [stack-update](e1-stack-updates.md) flows, not only on a release page. |
| **E5-R7** | A patch/hotfix release MUST appear with its cited fix, against the version it patched. |
| **E5-R8** | A yanked release MUST appear marked withdrawn with its reason, and MUST NOT be removed from the record. |
| **E5-R9** | Entries MUST lead with a plain-language summary; identifiers MUST be the link target, not the headline ([G2](../g-ux/g2-plain-language.md)). |
| **E5-R10** | A release with no user-facing change MUST be stated as such rather than emitted as an empty release. |
| **E5-R11** | When the generated changelog and the release tags disagree, the changelog MUST be flagged stale and MUST NOT be presented as current. |
| **E5-R12** | A requirement withdrawn after it shipped MUST retain its historical entry; the withdrawal MUST be recorded, not erased. |
| **E5-R13** | Generating and showing the changelog MUST each be reachable non-interactively. |

## Related

- [E1 Stack updates](e1-stack-updates.md) — one place the changelog is shown
- [E2 lemonfiber self-update](e2-self-update.md) — the other
- [G2 Plain-language layer](../g-ux/g2-plain-language.md) — how entries read
- [roadmap — the version train](../../../00-overview/roadmap.md#the-version-train) — what each version shipped
