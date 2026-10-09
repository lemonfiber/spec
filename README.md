<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/logo-on-ink.svg">
    <img alt="lemonfiber" src=".github/logo.svg" height="72">
  </picture>
</p>

<h1 align="center">Specification</h1>

Lemonfiber is a fully open-source, self-hosted media automation stack you can
run in narrow parts — "just search", "just download", "everything" — driven by
one binary that sets itself up. This repository is its specification: what the
product must do, why it is built the way it is, and the standards every
repository in the organisation is held to.

It contains **no code**. Every change to the code cites a requirement written
here first.

**Looking for how to install or use lemonfiber?** That is
[docs.lemonfiber.app](https://docs.lemonfiber.app), which also renders this
specification, searchable, at [docs.lemonfiber.app/spec](https://docs.lemonfiber.app/spec/).

<p align="center">
  <a href="https://github.com/lemonfiber/spec/actions/workflows/integrity.yml"><img alt="integrity" src="https://github.com/lemonfiber/spec/actions/workflows/integrity.yml/badge.svg"></a>
  <a href="https://github.com/lemonfiber/spec/actions/workflows/docs.yml"><img alt="docs" src="https://github.com/lemonfiber/spec/actions/workflows/docs.yml/badge.svg"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/lemonfiber/spec"><img alt="OpenSSF Scorecard" src="https://api.scorecard.dev/projects/github.com/lemonfiber/spec/badge"></a>
</p>

---

## The repositories

[30-repos](30-repos/README.md) lists every repository this specification
governs, what each one is, and how they depend on each other. That table is
generated from [`30-repos/repos.toml`](30-repos/repos.toml), so it is always
complete.

---

## How to navigate

> **New here? Read [How this spec works](00-overview/how-the-spec-works.md) first** —
> the whole system (features, requirements, versions, how change gets in) in plain
> language, about five minutes. Then use the map below.

Sections are numbered so they sort in reading order. Start at `00`, skip ahead
freely.

| Section | Contents | Read this if… |
|---------|----------|---------------|
| **[00-overview](00-overview/)** | Vision, glossary, roadmap, and all Architecture Decision Records | …you want the *why* behind any choice |
| **[10-functional](10-functional/)** | The 112-feature catalogue, numbered requirements, and nine user journeys | …you're deciding what to build or verifying it got built |
| **[20-architecture](20-architecture/)** | System context, component model, platform matrix, inter-repo contracts | …you're implementing across the lemonfiber ↔ lemonfiber-media-stack seam |
| **[30-repos](30-repos/)** | Per-repo technical specs | …you're working inside one repo |
| **[40-quality](40-quality/)** | Code standards, comment policy, testing, CI/CD, security | …you're writing or reviewing a PR |
| **[50-governance](50-governance/)** | How change enters the org. The spec is canonical — **read this before your first PR** | …you're contributing to any repo |
| **[60-brand](60-brand/)** | Brand rules, surface mapping (web/TUI/CLI), the accessibility contract | …you're building the web UI or touching visuals |
| **[70-operations](70-operations/)** | Releasing, maintainer setup, branching, labels, maintainers | …you're running the project or cutting a release |
| **[90-appendix](90-appendix/)** | Licence rationale, colophon, FAQ | …you're chasing a citation |

### Fast paths

- **"I want to understand the product"** → [vision](00-overview/vision.md) → [journeys](10-functional/journeys/) → [forms](10-functional/features/b-running/b1-forms.md)
- **"What does it actually do?"** → [feature catalogue](10-functional/features/), counted on the [board](10-functional/features/BOARD.md)
- **"I'm implementing lemonfiber"** → [lemonfiber spec](30-repos/lemonfiber.md) → [TUI spec](30-repos/lemonfiber-tui.md) → [code standards](40-quality/code-standards.md)
- **"I'm implementing lemonfiber-media-stack"** → [lemonfiber-media-stack spec](30-repos/lemonfiber-media-stack.md) → [stack manifest contract](20-architecture/contracts/stack-manifest.md)
- **"Why is it built this way?"** → [decisions/](00-overview/decisions/)
- **"I want to contribute"** → [contributing](50-governance/contributing.md) — every change must cite a spec identifier that already exists

---

## Conventions used throughout

| Convention | Meaning |
|------------|---------|
| **MUST / SHOULD / MAY** | [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) keywords. `MUST` is a hard requirement; violating it is a bug. |
| `<feature>-R<n>` | A product requirement, e.g. `A2-R4`. Requirements live **inside** their feature — there is no separate requirements tree. |
| `GOV-R<n>` | A [governance](50-governance/) rule — how change enters the org. |
| `ARCH-R<n>` | An [architectural](20-architecture/) requirement — structural rather than behavioural. |
| `Q-R<n>` | A [quality](40-quality/) rule — how code is written. |
| `DES-R<n>` | A [brand](60-brand/) requirement — the checkable visual constraints. |
| `OPS-R<n>` | An [operations](70-operations/) requirement — running the project. |
| `REPO-R<n>` | A [per-repo](30-repos/) requirement — one repository's structure or tooling. |
| `J<n>` | A [user journey](10-functional/journeys/). Journeys are the acceptance tests; each names the features it exercises. |
| `ADR-####` | Architecture Decision Record. Immutable once accepted; superseded rather than edited. |
| **Status: Draft / Accepted / Superseded** | Every doc carries one at the top. |

All identifiers are **permanent and never reused**. A withdrawn one is marked
withdrawn in place, because commits and CI reference them. They belong in commit
trailers and PR bodies — **never in code comments**
([GOV-R6](50-governance/canonical-spec.md#the-gov-r-namespace)).

## Spec status

| Section | Status | Contents |
|---------|--------|----------|
| 00-overview | Accepted | Vision, glossary, roadmap, 41 ADRs |
| 10-functional | Accepted | The [feature board](10-functional/features/BOARD.md) — features, requirements, areas — and 9 journeys |
| 20-architecture | Accepted | System context, component model, data flow, platform matrix, 10 contracts |
| 30-repos | Accepted | A page per repository, and the [repository map](30-repos/README.md) |
| 40-quality | Accepted | Comment policy, code standards, testing, CI/CD, security, definition of done |
| 50-governance | Accepted | Canonical spec rule, change lifecycle, cross-repo CI, contributing |
| 60-brand | Accepted | Brand rules, surface mapping, accessibility contract |
| 70-operations | Accepted | Releasing, setup registry, project workflow, maintainers |

Each feature page states its own status at the top; the
[feature board](10-functional/features/BOARD.md) shows them all in one place.
Implementation is under way: the [roadmap](00-overview/roadmap.md) plans the
releases up to 1.0, and the
[releases](https://github.com/lemonfiber/lemonfiber/releases) show how far it
has got.

This is a spec-first project: the functional spec landed before the technical one
deliberately, so that **every architectural decision can be justified against a
requirement** rather than alongside one. A technical choice citing no requirement
is unjustified and should be challenged in review.

---

## Changing this spec

**This repository is canonical.** No change lands in any implementation repo
unless it cites an identifier that already exists here — enforced mechanically.
See [50-governance](50-governance/).

1. Contested decisions need a new ADR in `00-overview/decisions/`.
2. Requirements get a **new number**; they are never renumbered, because commits
   and CI reference them. A withdrawn requirement is marked withdrawn in place.
3. Superseding an ADR means writing a new one that links back — never editing
   the old one. The record of *why you changed your mind* is the valuable part.
4. Requirement IDs belong in commit messages and PR bodies. **Never in code
   comments** — see the [comment policy](40-quality/code-comments.md).

## Licence

Documentation is [CC BY-SA 4.0](LICENSE.md). Code in sibling repos is the
**Hippocratic License 3.0** — an ethical-source licence that is deliberately
*not* OSI-approved. This has real practical consequences; see
[licence rationale](90-appendix/license-rationale.md) before depending on it.

---

<p align="center">
  <a href="https://nightworks.io">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset=".github/nightworks-white.png">
      <img alt="NightWorks.io" src=".github/nightworks-dark.png" height="20">
    </picture>
  </a>
  &nbsp;&middot;&nbsp;<a href="https://discord.nightworks.io"><img alt="Discord" src=".github/discord.svg" height="20"></a>
</p>
