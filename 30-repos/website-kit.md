# Repo: `website-kit`

**Status:** Proposed

What the [documentation site](website-docs.md) and the
[contributor site](website-contribute.md) both run, written once: an npm package
neither site publishes and each takes at an exact commit. TypeScript, Hippocratic
3.0. It has no pages and no routes of its own.

**Implements:** the machinery behind
[ADR-0015](../00-overview/decisions/0015-docs-site-renders-what-it-does-not-own.md)
for every site that renders what it does not own; consumes [`brand`](brand.md).

---

## Why this is a separate repo

Both sites render pinned submodules into Starlight, stamp each page with the revision
it came from, rewrite the links inside mirrored prose, refuse prose written into a
template, check every address a page sends a reader to, say when a pin has gone
behind on a file a page renders, move those pins by pull request, and hold the
installed brand tokens to the brand pin, and sweep every page kind for accessibility in both themes. Written into each site, that is two copies
of the same rules, and a fix to one would leave the other wrong with nothing to say
so. Held in either site, the other would depend on a site's internals.

## The one property to remember

**One copy, taken by commit.** Each site names this repository in its `package.json`
as `github:lemonfiber/website-kit#<commit>`, the way it takes `brand`, and the
automation that moves a site's submodule pins moves this pin too. Nothing is
published to a registry.

## What's in it

```
website-kit/
├── src/      the rules and the readers: mirror routes, titles, link rewriting
│             and provenance; the content loader; the guards on a site's own
│             code and chrome; the outbound link check; the pin checks and the
│             pull request that moves them; the brand check; the table
│             regions, the page policy and the layout probe
├── styles/   the look every site is drawn in: the Starlight theme on brand's
│             tokens, and brand's faces with their licences
├── run/      the runners a site's scripts call, which hand those rules the
│             process, the console and the network
└── dist/     what the two compile to, committed, because a site installs this
              repository by commit with its install scripts off
```

## Maintenance

A change lands here with its tests, and reaches a site when that site's pin on this
repository moves. CI reuses the shared workflows exactly as every other repository
does (`Q-R56`).

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R84** | The machinery the project's sites share — the mirror loader and provenance, link rewriting, the guards on authored chrome, the outbound link check, the pin checks and the pin bump, the brand package check, the accessibility sweep and the layout probe, the theme on brand's tokens and brand's faces, the table regions and the Content-Security-Policy each page carries — MUST be written here once, and MUST NOT be copied into any site. |
| **REPO-R85** | A site MUST take this repository at an exact commit recorded in its `package.json`, and the automation that moves the site's submodule pins MUST move that commit too; nothing here is published to a package registry. The compiled code a site runs MUST be committed, and CI MUST refuse it where it differs from what the source builds. |
| **REPO-R86** | This repository MUST hold no site's pages, route table or message catalogue; what a site renders and says stays in that site. |
| **REPO-R87** | Every module under `src/` MUST be covered by tests at 100% of lines, branches, functions and statements; the runners under `run/`, which hand those modules the process, the console and the network, MUST be type-checked and linted. |

## Related

- [website-docs.lemonfiber.app](website-docs.md) and [website-contribute.lemonfiber.app](website-contribute.md) — the two sites that take it
- [brand](brand.md) — the tokens its brand check holds a site to
