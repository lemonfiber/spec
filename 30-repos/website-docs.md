# Repo: `website-docs.lemonfiber.app`

**Status:** Proposed

The documentation site at `docs.lemonfiber.app`. Astro Starlight, static,
Hippocratic 3.0. It is for an operator or an integrator following instructions, in
two topics: *Use* and *Build on*. Almost nothing it publishes is **written here** — the
pages are each repo's own documentation, pinned to a revision and rendered
([ADR-0015](../00-overview/decisions/0015-docs-site-renders-what-it-does-not-own.md)).
The specification is rendered on the [frontpage](website-lemonfiber.md) and contributor
material on the [contributor site](website-contribute.md)
([ADR-0040](../00-overview/decisions/0040-three-sites-each-with-one-reader.md)).

**Implements:** the org's user-facing documentation and the *build-in-the-open*
commitment of [governance](../50-governance/); consumes [`brand`](brand.md)
([roadmap](../00-overview/roadmap.md)).

---

## Why this is a separate repo

The same floor that made the org multi-repo
([ADR-0004](../00-overview/decisions/0004-four-repo-split.md)), plus one thing the
frontpage cannot give it. The two sites have opposite relationships with time: the
[frontpage](website-lemonfiber.md) reads live org state at build so that it *cannot* lag
(`REPO-R39`), while documentation must render a **pinned** revision, because a reader
following instructions needs the instructions that match the release they installed.
One repo cannot honour both rules. Folding this into `website-lemonfiber.app` would
also mean rebuilding Starlight's sidebar, search and version switcher inside a bespoke
site that has no use for them.

It is not folded into `spec` either. `spec` is where the specification is written and
checked; what an operator follows is written in the repositories that build it.

## The one property to remember

**It renders; it does not own.** Every page of documentation belongs to the repository
that also holds the thing it describes, and reaches this site as a git submodule
pinned to an exact revision, symlinked into a Starlight content collection. Nothing is
fetched during a build.

- the core's generated command reference and its contract artefacts
- each SDK's guide, and the plugin template
- [`.github`](https://github.com/lemonfiber/.github) — conduct, security, where to ask

This is what makes the pages trustworthy: they cannot quietly drift from the repo they
document, because they are that repo's files at a revision the site names on the page.

Every authored page declares which of the two topics it serves, and the navigation is
built per topic from that declaration. A page that restates a page another repository
owns is a second copy that drifts; that page is mirrored instead.

What *is* written here is the connective tissue — navigation, landing pages, and the
task-shaped guides that mirrored prose does not provide because it was written for a
repository rather than for a reader arriving from a search box.

**Project status is not here.** The roadmap, the board, what is built and the list of
releases change whenever the org does, and they live on the
[frontpage](website-lemonfiber.md), which reads them live. This site renders pinned
revisions for a reader following instructions, so a page of project status here would
be as old as its pins. A route that held one redirects to the frontpage's page for it.

## What's in it

```
website-docs.lemonfiber.app/
├── .gitmodules            the pins — one per repo whose docs are shown
├── vendor/                the submodules themselves, never edited here
├── mirrors.json           the route table — which upstream file each page is
├── src/content/docs/      the collection; this site's own pages, and mirrored
│                          trees entering by symlink beside them
├── src/lib/               the mirror loader: routes, provenance, link rewriting
├── messages/en.json       the message catalogue; every authored string
├── src/components/        VersionTrain · VersionPill · StatusPill · …
└── astro.config.ts        Starlight: sidebar, one locale, link validation
```

Authored and mirrored pages share one collection rather than sitting in separate
trees: Starlight's sidebar is built from route, so a split would mean two sources
for one navigation. A mirrored page is a symlink into `vendor/`, which is what
makes "this site holds no second copy" (`REPO-R45`) a property of the filesystem
rather than a habit.

## How it stays fresh

Deployed to GitHub Pages by CI, from a checkout that includes submodules. A pin moves
by pull request in this repo, which is what makes the change reviewable and dated: the
diff says which revision the site will start showing, and every rendered page carries
that revision and its date so a reader can tell how old the words are. A build fetches
nothing, so it succeeds offline and renders the same site from the same commit a year
later.

The versions of the prose are built as a matrix from the first release, rather than
retrofitted — switching versioning on later renames every published URL.

## Maintenance

Bumping pins, and the site's own structure and styling. Nothing else: a wrong sentence
is fixed in the repo that owns it, which is slower and is the behaviour worth buying.
Structural change, like any other, cites a spec identifier
([GOV-R2](../50-governance/canonical-spec.md#the-gov-r-namespace)). CI reuses the
shared workflows (`spec-check`, `hygiene`, `security`, `dco`, `commitlint`, `labeler`)
exactly as every other repo does (`Q-R56`), and adds a link check that reads mirrored
prose as well as authored prose — this is the only build that sees all of it at once.

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R45** | Every documentation page MUST be rendered from the repository that owns its source; this repository MUST NOT hold a second copy of it. |
| **REPO-R46** | Mirrored content MUST be pinned to an exact upstream revision recorded in this repository, never to a branch. |
| **REPO-R47** | A build MUST NOT fetch content over the network; everything it renders MUST already be in the checkout. |
| **REPO-R48** | Every link in mirrored content MUST resolve to a page on this site or to a document that is reachable elsewhere, and CI MUST fail on one that does not. |
| **REPO-R49** | Every mirrored page MUST show the upstream revision it was rendered from, and that revision's date. |
| **REPO-R50** | Every user-facing string authored in this repository MUST come from the message catalogue and MUST NOT be written into a template. |
| **REPO-R51** | The published site MUST load no font, script, style or tracker from a third party at run time. |
| **REPO-R52** | *Superseded by [REPO-R79](website-lemonfiber.md): the specification is rendered on the frontpage, at the revision the board snapshot read. The number is not reused.* |
| **REPO-R53** | A URL that this site or a retired rendering of the specification published MUST continue to resolve, by redirect, to the page that replaced it, including a page that moved to the frontpage. |
| **REPO-R68** | The site MUST NOT render project status: the roadmap, the board, what is built and the list of releases are the frontpage's to publish. |
| **REPO-R80** | The site MUST NOT render the specification or contributor material; a route it published for either MUST redirect to the page that replaced it on the frontpage or the contributor site. |
| **REPO-R81** | Every authored page MUST declare its topic, `use` or `build`; the navigation MUST be built per topic from that declaration, and a check MUST refuse a page with none or one under the other topic's tree. |
| **REPO-R82** | An authored page MUST NOT restate a normative page another repository owns; that page MUST be mirrored instead. |
| **REPO-R83** | The build MUST publish a provenance index mapping every route it renders to the repository, the path and the revision it was rendered from. |

## Related

- [ADR-0015 The documentation site renders content it does not own](../00-overview/decisions/0015-docs-site-renders-what-it-does-not-own.md)
- [ADR-0004 Four-repo split](../00-overview/decisions/0004-four-repo-split.md)
- [ADR-0040 Three sites, each for one reader](../00-overview/decisions/0040-three-sites-each-with-one-reader.md)
- [website-lemonfiber.app](website-lemonfiber.md) — the frontpage, which reads live state rather than a pin, and renders the specification
- [website-contribute.lemonfiber.app](website-contribute.md) — the contributor site
- [brand](brand.md) — the tokens the site consumes
- [50-governance](../50-governance/) — the transparency commitment it serves
- [website-kit](website-kit.md) — the mirror machinery this site takes by commit
