# AGENTS.md — spec

Orientation for a focused session in this repo.

> **Common rules for every lemonfiber repo** live in
> [50-governance/ai-contributors.md](50-governance/ai-contributors.md). This file
> is the spec-repo-specific header; the shared rules are canonical there.

## What this repo is

The **canonical specification** for lemonfiber. No code. It spans all
implementation repos and owns every cross-cutting decision. Everything else in
the org is built *against* this repo, and every change elsewhere must cite an
identifier that exists here.

Start at [README.md](README.md), then the section you need. For the mental model
in plain language first, read [how-the-spec-works.md](00-overview/how-the-spec-works.md) —
the whole system explained in five minutes.

## The load-bearing rule

**This repo is canonical.** When you change it:

- New requirements get a **new, permanent ID** — never renumber, never reuse a
  withdrawn one. Mark withdrawn ones withdrawn in place.
- A behavioural change is a new/edited requirement; a contested decision is a new
  **ADR** (immutable — supersede, never edit).
- Identifiers live in seven namespaces: feature (`A2-R4`), `GOV-R`, `ARCH-R`,
  `REPO-R`, `Q-R`, `DES-R`, `OPS-R`. They belong in commit messages and PR bodies —
  **never in code comments** (`GOV-R6`).

## Before you commit

Run `just ci` (or `python3 scripts/integrity.py`): every cited identifier must
resolve, none may be duplicated, every internal link must resolve. CI enforces the
same via `.github/workflows/integrity.yml`.

Spec PRs do **not** run `spec-check` (this repo is the source of citations, not a
consumer). They run integrity, hygiene, and the docs build.

## Layout

```
00-overview/     vision, glossary, roadmap, ADRs
10-functional/   features + reqs (counted in features/BOARD.md), 9 journeys
20-architecture/ system context, components, contracts (stack.toml, tokens, versioning)
30-repos/        per-repo specs
40-quality/      comments, standards, testing, CI/CD, security, tooling, done
50-governance/   the canonical-spec rule and its enforcement
60-brand/        brand rules, surface mapping, accessibility contract
90-appendix/     licence rationale, colophon, FAQ
scripts/         integrity.py, spec_check.py (reusable gate), gen_redirects.py
```

## House style

Dense, opinionated, tables over prose. Every doc: a one-line intent, then the
substance, then a requirements table, then Related links. Every technical claim
traces to a requirement — a decision citing nothing should be challenged.

## Conventions & preferences

- Commits carry **no** AI/Co-Authored-By attribution.
- Propose before writing; wait for approval before committing.
- Maintained by NightWorks.io · community on [Discord](https://discord.nightworks.io).
