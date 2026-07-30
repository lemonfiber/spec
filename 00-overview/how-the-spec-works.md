# How this spec works — the short version

**Status:** Accepted

New here? This page explains the whole system in plain language before you dive
into any one document. Five minutes, no jargon. The dense reference lives in the
[README](../README.md) and [50-governance](../50-governance/); this is the map you
read first.

---

## The one idea

**The spec is the source of truth, and it comes first.** Every line of code in
every other repo has to point back to a decision written down here — by citing
its identifier. If a change can't name the requirement it serves, that's the
signal to stop and write the requirement first. Nothing is "obvious"; it's either
written down or it isn't real yet.

Think of it like an issue tracker that the code is legally bound to, except the
"issues" are permanent, reviewed, and never disappear.

## The building blocks (biggest to smallest)

```
Area  ─contains─▶  Feature  ─contains─▶  Requirement  ◀─implements─  Code
(A–K)              (an epic)             (an issue)                  (a PR)
```

- **Area** — a big theme, a single letter. `A` is getting started, `C` is trust &
  correctness, `H` is ecosystem glue, and so on. Areas `A–G` are the v1 product;
  `H–K` are the v2 ("ecosystem") additions.
- **Feature** — one capability, like an *epic*. `B3` is the live dashboard. Each
  feature is one markdown file with a fixed shape: **Purpose → Behaviour → States
  → Edge cases → Acceptance criteria → Related**.
- **Requirement** — one testable rule, like an *issue*. `B3-R1` is the first
  acceptance criterion of feature `B3`. Requirements use
  [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) words — **MUST**, **SHOULD**,
  **MAY** — so "required" and "nice to have" are never ambiguous.

**IDs are permanent.** `B3-R1` means the same thing forever. A requirement that's
dropped is marked *Withdrawn* in place; its number is never reused, because
commits and tests refer to it by number.

## The labels on each feature (the "issue tracker" fields)

Every feature file opens with a small machine-readable block (YAML frontmatter) —
the fields you'd expect from any tracker, so both humans and tools can filter and
sort without reading prose:

```yaml
id: B3
title: Live dashboard
kind: feature          # epic-level item
area: B                # component
audience: operator     # who it's for: operator | household | both
status: accepted       # draft → accepted → superseded → withdrawn
tracks: v1             # which epoch: v1 or v2
milestone: M5          # roadmap milestone
priority: P1           # P0..P3
labels: [tui, telemetry, resilience]
depends: [B2, C2, G7]  # related features
```

`status` is the important one: **Draft** means "proposed, not binding — don't
build it yet"; **Accepted** means "agreed, cite it and build." That single flag is
what makes the *request-for-comments* phase possible — Draft items are what the
community is invited to weigh in on before they become binding.

## The other kinds of documents

- **ADRs** ([decisions/](decisions/)) — a *contested* choice and why the
  alternatives lost. They're immutable: to change your mind you write a new ADR
  that supersedes the old one. The record of changing your mind is the point.
- **Journeys** ([journeys/](../10-functional/journeys/)) — end-to-end stories
  ("a fresh machine to a working TV setup") that act as the acceptance tests; each
  names the features it exercises.
- **Contracts, standards, governance, operations** — the numbered sections
  `20`–`70`, each owning its own `-R` identifiers (`ARCH-R`, `Q-R`, `OPS-R`, …).

## How versions work (the release train)

Work ships in a **serial train** of versions, each described by one small file in
[70-operations/versions/](../70-operations/versions/) that lists the exact
requirement IDs it must satisfy:

- **Minor** (`0.4.0`, `0.5.0`, …) — a themed slice of features. This is the normal
  unit of release.
- **Patch** (`x.y.Z`) — a hotfix on an already-released version.
- **Major** (`1.0.0`, `2.0.0`) — an **epoch** boundary. `1.0.0` is the whole v1
  product (areas A–G); `2.0.0` is v2 (the ecosystem). A major only ships when its
  epoch is *complete* — no half-finished features left behind.

A version's goals are **locked** before the work starts, and the release refuses
to ship until every goal is both cited in a merged PR *and* ticked off as done.
The file is the single source of truth — you read a version's `status` to know
where it is, never someone's memory.

## How a change gets in

1. **Propose** — open a PR that adds or edits a requirement (or an ADR for a
   contested call). Review answers one question: *should the product do this?*
2. **Accept** — merge it. Now it's binding and has a permanent ID.
3. **Implement** — open the code PR in the relevant repo, citing that ID in a
   `Spec:` trailer. A bot checks the citation resolves.

Code and spec are reviewed *separately and in that order* on purpose: a design
reviewed next to working code tends to get rubber-stamped. Separating them keeps
the question honest. Full detail:
[change-lifecycle](../50-governance/change-lifecycle.md).

## Everything you see is generated from this

The roadmap, the changelog, and the public progress pages are **built from the
files above**, not hand-maintained — so they can't drift from the truth. Draft
requirements and open PRs are what surface as *requests for comments*. When you
read a rendered page, you're reading these documents, joined together.

## Where to go next

- Understand the product → [vision](vision.md) → [journeys](../10-functional/journeys/)
- See what it does → [feature catalogue](../10-functional/features/)
- Why it's built this way → [decisions/](decisions/)
- Contribute → [contributing](../50-governance/contributing.md)
