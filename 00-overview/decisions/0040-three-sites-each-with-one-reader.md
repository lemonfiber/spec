# ADR-0040: Three sites, each for one reader, and the specification on the frontpage

**Status:** Accepted
**Date:** 2026-10-07
**Decided:** 2026-10-07, by the maintainer, Wessel Verheij: the roadmap, the board and
everything else about where the project stands are on `lemonfiber.app`; contributor
material moves to a site of its own, `contribute.lemonfiber.app`; the specification is
rendered on `lemonfiber.app`, at the revision the board snapshot read, and not on the
documentation site; the documentation site keeps Astro Starlight.

**Supersedes** [ADR-0015](0015-docs-site-renders-what-it-does-not-own.md) where it puts
the specification and contributor material on the documentation site. Its mirror
model, the pin as the freshness contract and the offline build stand.

## Context

ADR-0015 made `docs.lemonfiber.app` the one place every reader goes: someone running the
tool, someone building on it, and someone taking it apart. The specification came with
it, as the largest body of prose the organisation has, and the contributor guides
followed.

Three readers sharing one site went wrong in three ways.

**The pins answer one reader and fail the others.** A reader following instructions
needs the instructions that match the release they installed, so the documentation
renders pinned revisions. The specification and the project's state move on every
merge. The docs site pinned `spec` 157 commits behind `main` on 2026-10-07, so a
contributor citing a requirement read a text the specification no longer held, and the
roadmap on the same site showed a version train that had moved on.

**Governance drowned the instructions.** The specification mirror is the largest part
of the sidebar, and a search for how to do something landed in a requirement table as
often as in a guide.

**Project state had two homes.** The frontpage already reads the organisation live, and
the docs site rendered a second roadmap from a different revision of the same files.

## Decision

Three sites, each with one reader and one relationship with time.

| Site | Reader | Renders | At |
|---|---|---|---|
| `lemonfiber.app` | anyone asking what lemonfiber is and how far it has got | the pitch, the roadmap, the board, the repositories, the work in flight, the releases, the proposals, and the specification | the revisions the board snapshot read |
| `docs.lemonfiber.app` | an operator or an integrator following instructions | *Use* and *Build on*: installing, running, fixing, the commands, the web API, the SDKs, plugins | revisions pinned by pull request |
| `contribute.lemonfiber.app` | a person or an agent changing the code | how to work in the repositories, the developer command line, the gates, each repository's own guide and architecture notes | revisions pinned by pull request |

**The specification is rendered on the frontpage**, at the commit of `spec` the board
snapshot read, and rebuilt on the same event as the board. The requirement a feature
page on the board names and the text the specification page shows are then the same
revision, and both are the newest the report has read. `spec` stays the
specification's home: it is authored, checked and edited there.

**The contributor site renders no specification page.** The rules a contributor needs
are specification pages (`50-governance/`), and a page has one home. The contributor
site links to them on the frontpage, and renders what is not the specification: the
guides written for a contributor, each repository's `README.md` and `AGENTS.md`, and the
architecture notes, mirrored the way ADR-0015 mirrors.

**The documentation site renders no project status and no specification.** It keeps
Starlight, its mirror machinery and its pins. A route it published for either redirects
to the page that replaced it.

## Alternatives considered

| Option | Why it lost |
|---|---|
| One documentation site with three topics: *Use*, *Build on*, *Contribute* | One search and one build, but one set of pins: either the instructions stop matching the installed release or the specification stops matching `main`. |
| The specification on the contributor site | Contributors are its largest audience, but the board links each requirement to its text, and two sites rendering two revisions of one requirement is the disagreement this decision ends. |
| The specification on the documentation site, as ADR-0015 has it | It is the revision problem above, measured: 157 commits behind. |
| Contributor material on the frontpage | The frontpage is for the project and renders live state; a guide to the gates is instructions, and instructions are pinned. |

## Consequences

### Positive

- Each site's pins, or the absence of them, suit its one reader.
- A requirement on the board and on its specification page are the same revision.
- A search on the documentation site finds instructions.

### Negative

- Three sites to build, deploy and keep in brand, and a third repository's CI.
- The specification's URLs move a second time; every route the documentation site
  published for it needs a redirect (`REPO-R53`).

### Neutral

- The mirror loader, provenance and offline link checking are reused by the
  contributor site rather than rewritten.

## Revisit if

- The frontpage's build time with the specification rendered passes what a rebuild on
  every snapshot can afford.
- A fourth reader appears whose relationship with time matches none of the three.

## Related

- [ADR-0015](0015-docs-site-renders-what-it-does-not-own.md), the decision this supersedes in part
- [website-lemonfiber.app](../../30-repos/website-lemonfiber.md),
  [website-docs.lemonfiber.app](../../30-repos/website-docs.md),
  [website-contribute.lemonfiber.app](../../30-repos/website-contribute.md)
- [The board snapshot](../../70-operations/board-format.md)
