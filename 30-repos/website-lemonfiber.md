# Repo: `website-lemonfiber.app`

**Status:** Proposed

The public frontpage at the root of the org. Astro, static, Hippocratic 3.0.
Its roadmap and status are **not authored here** — they are read from the org at
build time.

**Implements:** the org's public presence and the *build-in-the-open* commitment
of [governance](../50-governance/); consumes [`brand`](brand.md)
([roadmap](../00-overview/roadmap.md)).

---

## Why this is a separate repo

The same floor that made the org multi-repo
([ADR-0004](../00-overview/decisions/0004-four-repo-split.md)): the site is a
distinct artifact with its own toolchain (a Node/Astro build) and its own release
cadence (it redeploys when *any* repo changes, not when a binary ships). Folding
it into `lemonfiber` or `spec` would couple an unrelated build to theirs and blur
what each repo owns.

## The one property to remember

**The org is the motor.** A maintainer never edits this repo to move a milestone,
mark a deliverable done, or list a release. Those facts live where they are
already kept current — the GitHub API, and two Markdown files under governance's
existing discipline:

- [`00-overview/roadmap.md`](../00-overview/roadmap.md) — the sequenced milestones
- [`lemonfiber/IMPLEMENTATION-STATUS.md`](https://github.com/lemonfiber/lemonfiber/blob/main/IMPLEMENTATION-STATUS.md)
  — per-deliverable status (✅ / ◐ / ☐)

The site reads them at build time and renders them. When a maintainer pushes to
the repo that owns a fact, CI rebuilds and the site moves. This is what makes the
page trustworthy: it cannot quietly drift from reality, because it holds no copy
of reality to drift from.

## What's in it

```
website-lemonfiber.app/
├── src/lib/github.ts   the motor — build-time fetch + Markdown parse
├── src/data/seed.ts    committed fallback snapshot (never truth when live)
├── src/data/site.ts    editorial copy; the service / profile / form model
├── src/components/      Nav · Footer · Console · FormsSwitcher · RepoCard · …
├── src/pages/           index · roadmap · transparency · contribute · 404
└── src/styles/tokens.css  design tokens mirrored from brand
```

## How it stays fresh

Deployed to GitHub Pages by CI. The deploy workflow rebuilds on a daily schedule
and on a `repository_dispatch` (`rebuild-site`) that sibling repos fire after a
push or release — so a change to the roadmap propagates without anyone touching
this repo. If GitHub is unreachable during a build, the committed seed keeps the
build green and live data overrides it on the next successful run.

## Maintenance

Effectively none for content — that is the point. The only hand-written work is
the site's own structure and styling, and *that* change, like any other, cites a
spec identifier ([GOV-R2](../50-governance/canonical-spec.md#the-gov-r-namespace)).
CI reuses the shared workflows (`spec-check`, `hygiene`, `security`, `dco`,
`commitlint`, `labeler`) exactly as every other repo does (`Q-R56`).

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R39** | The roadmap, progress and repository state the site shows MUST be derived at build time from the org — the GitHub API and the canonical Markdown (`00-overview/roadmap.md`, `lemonfiber/IMPLEMENTATION-STATUS.md`) — never transcribed into this repo. |
| **REPO-R40** | Every remote fetch MUST fall back to a committed snapshot so a build succeeds offline or rate-limited; live data MUST override the snapshot whenever it is reachable. |
| **REPO-R41** | Visual tokens — colour, type, spacing — MUST mirror [`brand`](brand.md); the site MUST NOT define an independent palette or type scale. |
| **REPO-R42** | The site MUST be static and MUST load no third-party fonts, scripts or trackers at runtime. |
| **REPO-R43** | Presentation logic MUST NOT live in the data layer; the motor returns data and components render it. |
| **REPO-R44** | Deployment MUST rebuild on sibling-repo events (a `repository_dispatch`) and on a schedule, so the site tracks the org without a maintainer editing it. |

## Related

- [ADR-0004 Four-repo split](../00-overview/decisions/0004-four-repo-split.md)
- [brand](brand.md) — the tokens the site consumes
- [roadmap](../00-overview/roadmap.md) — the milestones it renders
- [50-governance](../50-governance/) — the transparency commitment it serves
