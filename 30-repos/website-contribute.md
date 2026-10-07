# Repo: `website-contribute.lemonfiber.app`

**Status:** Proposed

The contributor site at `contribute.lemonfiber.app`. Astro Starlight, static,
Hippocratic 3.0. It is for a person or an agent changing the code: how to work in the
repositories, the developer command line, the gates, and each repository's own guide.
Like the [documentation site](website-docs.md) it renders content it does not own,
pinned to a revision
([ADR-0040](../00-overview/decisions/0040-three-sites-each-with-one-reader.md)).

**Implements:** the contributor half of the *build-in-the-open* commitment of
[governance](../50-governance/); consumes [`brand`](brand.md).

---

## Why this is a separate repo

The [documentation site](website-docs.md) pins every page to a released revision,
because an operator following instructions needs the ones that match what they
installed. A contributor works against `main`, and reads the guide of the repository
they are changing at the revision they are changing it. One set of pins cannot serve
both, and a search on the documentation site should find instructions for running the
tool, not the rules for changing it.

## The one property to remember

**It renders; it does not own, and it does not render the specification.** Each page
belongs to the repository that holds what it describes and reaches this site as a git
submodule pinned to a revision, the mirror model of
[ADR-0015](../00-overview/decisions/0015-docs-site-renders-what-it-does-not-own.md):

- each repository's `README.md` and `AGENTS.md`
- [`lemonfiber/.docs/`](https://github.com/lemonfiber/lemonfiber), the architecture
  notes a contributor reads before touching the crate
- [`tool-lfdev`](tool-lfdev.md)'s own guide to its commands

The rules a contributor follows are specification pages, chiefly
[`50-governance/`](../50-governance/), and the specification is rendered on the
[frontpage](website-lemonfiber.md). This site links to each one there. What is written
here is the connective tissue: navigation, a landing page, and the task-shaped guides a
contributor needs that no repository's own page provides.

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R69** | Every page MUST be rendered from the repository that owns its source, from a revision pinned in this repository, and this repository MUST NOT hold a second copy of it. |
| **REPO-R70** | The site MUST NOT render a page of the specification; where a page names a rule the specification holds, it MUST link to that rule on the frontpage. |
| **REPO-R71** | A build MUST NOT fetch content over the network, and every link in what it renders MUST resolve, checked in CI. |
| **REPO-R72** | Every mirrored page MUST show the repository and the revision it was rendered from, and link to its source for editing. |
| **REPO-R73** | The site MUST load no font, script, style or tracker from a third party at run time, and MUST meet WCAG 2.1 AA in both themes, checked by an automated sweep on every pull request. |

## Related

- [ADR-0040 Three sites, each for one reader](../00-overview/decisions/0040-three-sites-each-with-one-reader.md)
- [ADR-0015 The documentation site renders content it does not own](../00-overview/decisions/0015-docs-site-renders-what-it-does-not-own.md)
- [website-docs.lemonfiber.app](website-docs.md), [website-lemonfiber.app](website-lemonfiber.md)
- [tool-lfdev](tool-lfdev.md) — the command line whose guide it renders
