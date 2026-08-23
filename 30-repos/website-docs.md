# Repo: `website-docs.lemonfiber.app`

**Status:** Proposed

The documentation site at `docs.lemonfiber.app`. Astro Starlight, static,
Hippocratic 3.0. Almost nothing it publishes is **written here** — the pages are
each repo's own documentation, pinned to a revision and rendered
([ADR-0015](../00-overview/decisions/0015-docs-site-renders-what-it-does-not-own.md)).

**Implements:** the org's user-facing documentation and the *build-in-the-open*
commitment of [governance](../50-governance/); consumes [`brand`](brand.md)
([roadmap](../00-overview/roadmap.md)).

---

## Why this is a separate repo

The same floor that made the org multi-repo
([ADR-0004](../00-overview/decisions/0004-four-repo-split.md)), plus one thing the
frontpage cannot give it. The two sites have opposite relationships with time: the
[frontpage](website.md) reads live org state at build so that it *cannot* lag
(`REPO-R39`), while documentation must render a **pinned** revision, because a reader
following instructions needs the instructions that match the release they installed.
One repo cannot honour both rules. Folding this into `website-lemonfiber.app` would
also mean rebuilding Starlight's sidebar, search and version switcher inside a bespoke
site that has no use for them.

It is not folded into `spec` either. The spec is the specification's single home and
is published from there by mdBook; this site links to it and does not restate it.

## The one property to remember

**It renders; it does not own.** Every page of documentation belongs to the repository
that also holds the thing it describes, and reaches this site as a git submodule
pinned to an exact revision, symlinked into a Starlight content collection. Nothing is
fetched during a build.

- [`lemonfiber/.docs/`](https://github.com/lemonfiber/lemonfiber) — the architecture
  notes a contributor reads before touching the crate
- [`brand/.docs/`](https://github.com/lemonfiber/brand) — colour, type and logo rules
- each repo's `README.md` — its own front door
- [`.github`](https://github.com/lemonfiber/.github) — conduct, security, contributing

The **specification is not mirrored**. It stays at
[lemonfiber.github.io/spec](https://lemonfiber.github.io/spec/), where its identifiers
are checked and its edit links point somewhere real; the site links out to it. This is
what makes the pages trustworthy: they cannot quietly drift from the repo they
document, because they are that repo's files at a revision the site names on the page.

What *is* written here is the connective tissue — navigation, landing pages, and the
task-shaped guides that mirrored prose does not provide because it was written for a
repository rather than for a reader arriving from a search box.

## What's in it

```
website-docs.lemonfiber.app/
├── .gitmodules            the pins — one per repo whose docs are shown
├── vendor/                the submodules themselves, never edited here
├── src/content/docs/      the collection; mirrored trees enter by symlink
├── src/content/authored/  this site's own pages — guides, landings, nav copy
├── src/i18n/en.json       the message catalogue; every authored string
├── src/components/        Provenance · VersionPicker · RepoBadge · …
└── astro.config.mjs       Starlight: sidebar, versions, search, one locale
```

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

## Related

- [ADR-0015 The documentation site renders content it does not own](../00-overview/decisions/0015-docs-site-renders-what-it-does-not-own.md)
- [ADR-0004 Four-repo split](../00-overview/decisions/0004-four-repo-split.md)
- [website](website.md) — the frontpage, which reads live state rather than a pin
- [brand](brand.md) — the tokens the site consumes
- [50-governance](../50-governance/) — the transparency commitment it serves
