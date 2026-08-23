# ADR-0015: The documentation site renders content it does not own

**Status:** Proposed
**Date:** 2026-08-23

## Context

The org needs a documentation site — `docs.lemonfiber.app` — for the three audiences
the interface tiers already name: someone using the tool, someone building on it, and
someone taking it apart. What it does **not** need is documentation written for it.

**The material already exists, and it is already maintained.** `lemonfiber/.docs/`
holds the architecture notes a contributor reads before touching the crate;
`brand/.docs/` holds the colour, type and logo rules; every repo's README is its own
front door; the org's `.github` repo holds the conduct, security and contributing
policy that every repo inherits. All of it is under review discipline in the repo that
owns it. A site that needs it *shown* is a different problem from a site that needs it
*written*.

**The specification already has a home.** It is rendered from this repo by mdBook to
[lemonfiber.github.io/spec](https://lemonfiber.github.io/spec/), with `integrity.py`
enforcing that every identifier resolves and every link works. Nothing about a second
renderer would make the spec more canonical, and the org has already learned what a
second renderer costs: the marketing site's `/spec` portal is being retired and
redirected to the mdBook, because two renderings of one document are two things that
can be stale and only one of them is checked.

**The org has settled this shape once already, in both directions.**
[ADR-0005](0005-embedded-stack-assets.md) pins the stack as a submodule at a tag.
[ADR-0012](0012-web-assets-embedded-at-build-time.md) then chose the same shape over
copying the files in, and said why:

> Rejected because it puts generated output under review in the consuming repo and
> makes every UI change a diff of minified bundles in `lemonfiber`'s history. The
> submodule keeps the pin without keeping the bytes.

The bytes here are prose rather than bundles, which makes the trap worse rather than
better: a copied Markdown file *looks* editable, so somebody eventually edits it, and
now the two copies disagree with no build to say so.

**[ADR-0014](0014-one-generated-contract-for-every-sdk.md) named the principle this
turns on.** Deciding where the contract artefact should live, it landed on: *"The
prose contract in `spec` stays normative for semantics; the generated artefact is
normative for shapes; neither restates the other."* A documentation site is the same
question asked about prose. One place is normative for each thing it shows, and the
site restates none of them.

The contested part is not whether to build the site. It is **whether the site holds
the words it publishes**, and every convenient answer says yes.

## Decision

**A separate repo, `website-docs.lemonfiber.app`, built with Astro Starlight, which
renders documentation owned by other repositories. Content arrives as git submodules
pinned to exact revisions and surfaced into Starlight's content collections by
symlink. No build fetches anything.**

| Content | Owned by | How it arrives |
|---------|----------|----------------|
| Architecture notes | `lemonfiber/.docs/` | submodule, pinned; symlinked into the collection |
| Brand rules | `brand/.docs/` | submodule, pinned; symlinked |
| Each repo's README | that repo | submodule, pinned; symlinked |
| Conduct, security, contributing | org `.github` | submodule, pinned; symlinked |
| **The specification** | `spec` | **not mirrored** — linked to the mdBook |
| Navigation, landing pages, task guides | here | authored, from the message catalogue |

Four consequences follow, and each one answers an objection.

**The pin is the freshness contract.** A submodule names a revision, not a branch, so
a build renders exactly what was reviewed. Bumping a pin is a pull request in this
repo — a diff somebody reads, with a date attached — rather than a silent change in
what the site says.

**A build works offline.** Everything rendered is already in the checkout.
[ARCH-R65](../../20-architecture/contracts/web-api.md) already forbids the network at
generation time for the analogous SDK case, and the reason transfers unchanged: a
build that reaches out fails differently on a bad day, and cannot be reproduced from a
tag in a year's time.

**The spec is linked, never copied.** The mdBook stays the specification's single
home. The docs site sends a reader there and does not pretend to be it.

**Prose is versioned from the first release.** Starlight's versioning is
configuration, not a rewrite, but retrofitting it means renaming every published URL —
so it is switched on before anything is published rather than after. For the same
reason the site is wired for i18n and ships English only: adding a language becomes
translating a catalogue instead of restructuring a site.

## Alternatives considered

**Copy the files in — vendor the Markdown into this repo.** One clone, no submodule
footguns, and the site owns its whole tree. Rejected for the reason ADR-0012 already
gave against exactly this shape, made worse by the medium: a vendored bundle is
obviously generated and nobody edits it by hand, whereas vendored prose reads like
prose and invites the edit that forks it. It also puts another repo's review burden
here, and gives a stale copy no way to announce itself.

**`git subtree` instead of submodules.** Genuinely close, and it removes the clone-time
sharp edges submodules have. Rejected because it *is* the copy: the files land in this
tree, editable, indistinguishable from ones authored here, and the pin becomes a merge
commit rather than a revision a reader can check against upstream in one step. It
trades a visible pin for an invisible one.

**Consume documentation as release artefacts.** Each repo publishes its docs with a
release; the site downloads them at build. Rejected on cadence: docs are corrected
between releases far more often than they are released, so a typo fix would wait for a
version bump — and it needs the network at build, which is the next alternative.

**Fetch the content over HTTP at build time.** Always current, no submodules at all.
Rejected on three counts. It breaks the authoring model: Starlight's content
collections read files from disk and type-check their frontmatter, so remote Markdown
cannot participate in MDX, in the site's link graph, or in the schema that keeps a
page well-formed. It makes the build non-reproducible — the same commit renders
different sites on different days, with nothing recording which. And it is the
network-at-build that ARCH-R65 already refuses for the SDKs, on reasoning that does
not change when the payload is prose.

**Fold the docs into the marketing site.** One Astro build, one deploy, one domain.
Rejected because the two sites have opposite relationships with time. The frontpage's
one property is that **the org is the motor** — it reads live org state at build so it
cannot drift ([REPO-R39](../../30-repos/website-lemonfiber.md)). Documentation must do the
reverse and render a pinned revision, because a reader following instructions needs
the instructions that match the release they installed. One repo cannot honour both
rules, and Starlight's sidebar, search and versioning would have to be rebuilt inside a
bespoke site that has no use for them.

**Mirror the spec as well, so everything is in one place.** Appealing, and the reason
the marketing site grew a `/spec` portal in the first place. Rejected because that
portal is being retired for cause: the spec's identifiers, integrity checks and edit
links are enforced in `spec`, and a second rendering inherits none of them while
inheriting every opportunity to disagree.

## Consequences

- **Bumping a pin is ongoing work.** The site lags upstream by however long that takes,
  which is why it must say which revision it rendered rather than implying "now".
- **A broken link in somebody else's prose fails this repo's CI.** That is the point —
  it is the only build that sees all of it at once — but it means this repo's red
  pipeline is sometimes another repo's bug.
- **CI must check out submodules everywhere**, and a contributor who clones without
  `--recursive` gets an empty site rather than an error that explains itself.
- **Two audiences, one search index.** Mirrored prose was written for the repo it lives
  in, not for a reader arriving from a search box, so the site's own authored pages
  carry the connective work.
- **Versioning from day one costs a build matrix** before there is a second version to
  put in it.
- **The site can never answer a question no repo has answered.** A gap is fixed
  upstream, in the repo that owns the subject, which is slower and is the behaviour
  worth buying.

## Revisit if

- A repo's `.docs/` starts being written for the site rather than for the repo — at
  that point the content has changed owner in practice, and the spec should say so
  rather than the arrangement pretending otherwise.
- Pin-bumping becomes the project's routine chore, which would mean the upstream docs
  move fast enough that a rendering closer to a branch tip is worth its cost.
- Starlight stops accepting symlinked sources in content collections, which would make
  the mechanism, rather than the decision, the thing to redesign.
