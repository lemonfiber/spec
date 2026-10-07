# Repo: `website-contribute.lemonfiber.app`

**Status:** Proposed

The contributor site at `contribute.lemonfiber.app`. Astro Starlight, static,
Hippocratic 3.0. It is where somebody who wants to change lemonfiber reads how the
project is run: how a change gets in, the rules every repository keeps, how each
repository is built, and the brand. Almost nothing it publishes is **written
here** — the pages are the governance pages of `spec` and each repository's own
documentation, pinned to a revision and rendered, the way the
[documentation site](website-docs.md) renders a user's
([ADR-0015](../00-overview/decisions/0015-docs-site-renders-what-it-does-not-own.md)).

**Implements:** the contributor's half of the org's documentation and the
*build-in-the-open* commitment of [governance](../50-governance/); consumes
[`brand`](brand.md) ([roadmap](../00-overview/roadmap.md)).

---

## Why this is a separate repo

The [documentation site](website-docs.md) is read by somebody running lemonfiber or
building on it, and the contributor's material — the citation rule, the sign-off,
the gates, the architecture notes — is noise to that reader and was found by
neither reader when the two shared one navigation. Two readers with nothing in
common get two sites, each with a search index that answers only its own reader's
questions. The [frontpage](website-lemonfiber.md) is where a contributor chooses
work, from the board; this site is where they learn how to do it.

## The one property to remember

**It renders; it does not own.** Every page belongs to the repository that also holds
the thing it describes, and reaches this site as a git submodule pinned to an exact
revision, symlinked into a Starlight content collection. Nothing is fetched during a
build.

- [`spec/50-governance/`](../50-governance/) — how change gets in, the rules for
  people and agents, sign-off, proposals, where an issue goes, and working in the
  repositories
- [`spec/30-repos/README.md`](README.md) — the map of the repositories
- [`lemonfiber/.docs/`](https://github.com/lemonfiber/lemonfiber) — the
  architecture notes a contributor reads before touching the crate
- [`brand/.docs/`](https://github.com/lemonfiber/brand) — colour, type and logo
  rules
- each repository's `README.md` — its own front door
- [`.github`](https://github.com/lemonfiber/.github) — conduct, security, support

What *is* written here is the connective tissue: navigation and a landing page that
sends a reader to the board for something to pick up.

## What's in it

```
website-contribute.lemonfiber.app/
├── .gitmodules            the pins — one per repository whose pages are shown
├── vendor/                the submodules themselves, never edited here
├── mirrors.json           the route table — which upstream file each page is
├── src/content/docs/      the collection; this site's own pages, and mirrored
│                          trees entering by symlink beside them
├── src/lib/               the mirror loader: routes, provenance, link rewriting
├── messages/en.json       the message catalogue; every authored string
└── astro.config.ts        Starlight: sidebar, one locale, link validation
```

## How it stays fresh

Deployed to GitHub Pages by CI, from a checkout that includes submodules. A pin moves
by pull request, opened by the same automation that moves the documentation site's
pins, and a pin left behind on a file a page renders refuses every pull request once
its window has passed (`Q-R68`). Every rendered page carries the revision it was
rendered from and that revision's date.

## Maintenance

Bumping pins, and the site's own structure and styling. A wrong sentence is fixed in
the repository that owns it. CI reuses the shared workflows exactly as every other
repository does (`Q-R56`), and adds a link check that reads mirrored prose as well as
authored prose.

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R73** | Every page MUST be rendered from the repository that owns its source, pinned to an exact upstream revision recorded in this repository and never to a branch; this repository MUST NOT hold a second copy of it. |
| **REPO-R74** | A build MUST NOT fetch content over the network; everything it renders MUST already be in the checkout. |
| **REPO-R75** | Every mirrored page MUST show the upstream revision it was rendered from, and that revision's date. |
| **REPO-R76** | Every link in mirrored content MUST resolve to a page on this site or to a document that is reachable elsewhere, and CI MUST fail on one that does not. |
| **REPO-R77** | Every user-facing string authored in this repository MUST come from the message catalogue and MUST NOT be written into a template. |
| **REPO-R78** | The published site MUST load no font, script, style or tracker from a third party at run time. |
| **REPO-R79** | The site MUST publish the material a contributor needs and the documentation site does not carry: the governance pages of `spec`, the map of the repositories, each repository's own documentation for working in it, and the brand rules. |
| **REPO-R80** | The build MUST publish a provenance index mapping every route to its repository, path and revision. |
| **REPO-R81** | A URL this site publishes and later retires MUST continue to resolve, by redirect, to the page that replaced it. |

## Related

- [ADR-0015 The documentation site renders content it does not own](../00-overview/decisions/0015-docs-site-renders-what-it-does-not-own.md)
- [website-docs.lemonfiber.app](website-docs.md) — the documentation site, for a reader running lemonfiber or building on it
- [website-lemonfiber.app](website-lemonfiber.md) — the frontpage, where a contributor chooses work from the board
- [50-governance](../50-governance/) — the pages this site renders first
