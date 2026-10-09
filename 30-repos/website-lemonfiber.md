# Repo: `website-lemonfiber.app`

**Status:** Proposed

The public frontpage at the root of the org. Astro, static, Hippocratic 3.0.
It is the project's home: the pitch, the roadmap, the board of features and
requirements, the repositories, the work in flight, the releases, the proposals
and the specification itself. None of that is **authored here** — it is read from
the org at build time.

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

**The org is the motor.** A maintainer never edits this repo to release a version,
mark a requirement built, or list a pull request. Those facts live in the
repositories that own them, and the specification's report joins them into one
[snapshot of where every version stands](../70-operations/staging.md#where-every-version-stands):
the version manifests, the catalogue of features and requirements, every
repository's tracker, every open pull request and what it cites, and the
releases, each with the revision it was read at.

The site reads that snapshot at build time and renders it; it computes nothing
but sorting, filtering and counting what the snapshot holds. When a fact changes
in the repository that owns it, the report publishes a new snapshot, the site
rebuilds, and the page moves. Every fact it shows links to the file in git that
owns it, so a reader can check it and a contributor can change it there.

Where the snapshot cannot be read, the build fails and the published site stays
as it was. A committed copy of the snapshot would be a second record of the same
facts, and it would go stale the first time nobody regenerated it.

## Views

| Route | Answers |
|---|---|
| `/roadmap/`, `/roadmap/<version>/` | every version in train order, its status and the verdict on each of its goals |
| `/board/` | the features by maturity: planned, building, built, shipped |
| `/features/<id>/` | one feature and every requirement it defines, with the verdict, evidence, citations and claims for each |
| `/repos/`, `/repos/<name>/` | what each repository has built, its tracker and its open pull requests |
| `/in-flight/` | every open pull request in the org and what it cites |
| `/pick/` | the goals of the version in flight and the next that nobody has claimed |
| `/releases/`, `/releases/<version>/` | what each release delivered, from the core's changelog |
| `/proposals/` | Draft features and requirements, open proposal pull requests and open `rfc` issues |
| `/spec/` | the specification, every page with an anchor per requirement, at the commit of `spec` the snapshot read |

The specification is rendered here, not on the documentation site
([ADR-0040](../00-overview/decisions/0040-three-sites-each-with-one-reader.md)): a
requirement on the board and its text on the specification page are then the same
revision. `spec` stays its home, where it is written, checked and edited.

Every view is a page that works without script, and a filter is part of its
address, so a filtered view is a link. An interactive part is a framework island
bundled with the site and served from it.

## What's in it

```
website-lemonfiber.app/
├── src/lib/            the readers — the snapshot, and the GitHub API for what it does not hold
├── src/data/site.ts    site metadata, tagline and promises; the service / profile / form model
├── src/i18n/           the rest of the site's copy
├── src/components/      Nav · Footer · Console · FormsSwitcher · RepoCard · …
├── src/pages/           index · the views above · transparency · contribute · 404
└── src/styles/tokens.css  design tokens mirrored from brand
```

## How it stays fresh

Deployed by CI to Cloudflare, as an assets-only Worker that `wrangler.jsonc`
declares and wrangler uploads, and to GitHub Pages while the domain still points
there; the headers the host sends are in the `_headers` file the build carries.
The deploy workflow rebuilds when the
specification's report publishes a snapshot whose content changed, which it
announces with a `repository_dispatch` (`rebuild-site`), and on a schedule as the
backstop. Every view states when the snapshot was generated, so a reader can see
how old it is.

## Maintenance

Effectively none for content — that is the point. The only hand-written work is
the site's own structure and styling, and *that* change, like any other, cites a
spec identifier ([GOV-R2](../50-governance/canonical-spec.md#the-gov-r-namespace)).
CI reuses the shared workflows (`spec-check`, `hygiene`, `security`, `dco`,
`commitlint`, `labeler`) exactly as every other repo does (`Q-R56`).

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R39** | The roadmap, the board, progress and repository state the site shows MUST be rendered at build time from the snapshot of where every version stands that the specification publishes, never transcribed into this repo. |
| **REPO-R40** | Where the snapshot cannot be read, or names a `format` the site does not know, the build MUST fail and the published site MUST stay as it was; no committed copy of what the snapshot holds MAY stand in for it. A read of the GitHub API for a fact the snapshot does not hold MAY fall back to a committed snapshot. |
| **REPO-R41** | Visual tokens — colour, type, spacing — MUST mirror [`brand`](brand.md); the site MUST NOT define an independent palette or type scale. |
| **REPO-R42** | The site MUST be static and MUST load no third-party fonts, scripts or trackers at runtime. |
| **REPO-R43** | Presentation logic MUST NOT live in the data layer; the motor returns data and components render it. |
| **REPO-R44** | Deployment MUST rebuild when the specification reports a snapshot whose content changed, and on a schedule, so the site tracks the org without a maintainer editing it. |
| **REPO-R64** | The site MUST publish the roadmap, the board, a page per feature with its requirements, a page per repository, the open pull requests, the unclaimed goals, the releases and the proposals, and each MUST state when the snapshot it renders was generated and the revisions it was read at. |
| **REPO-R65** | Every view MUST be usable without script, and every filter MUST be expressed in the address so that a filtered view can be linked; script MUST be bundled with the site and served from it. |
| **REPO-R66** | Every fact the site renders from the snapshot MUST link to the file in git that owns it. |
| **REPO-R67** | The site MUST meet WCAG 2.1 AA in both themes, checked by an automated sweep on every pull request. |
| **REPO-R79** | The specification MUST be rendered on this site, from the commit of `spec` the board snapshot read, rebuilt with the board, with an anchor for every requirement and an edit link to its source in `spec`; it MUST NOT be published from any second site. |

## Related

- [ADR-0004 Four-repo split](../00-overview/decisions/0004-four-repo-split.md)
- [brand](brand.md) — the tokens the site consumes
- [roadmap](../00-overview/roadmap.md) — the milestones the versions serve
- [where every version stands](../70-operations/staging.md#where-every-version-stands) — the report whose snapshot it renders
- [ADR-0040 Three sites, each for one reader](../00-overview/decisions/0040-three-sites-each-with-one-reader.md)
- [website-docs.lemonfiber.app](website-docs.md) — the documentation, which renders no project status
- [website-contribute.lemonfiber.app](website-contribute.md) — the contributor site, which links here for the rules
- [50-governance](../50-governance/) — the transparency commitment it serves
