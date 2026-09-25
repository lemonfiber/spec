# Repo: `lemonfiber-plugins`

**Status:** Accepted

The reviewed plugin catalogue. A register of where plugins are, and the revision of
each one that a person read.

It registers rather than holds. A plugin's manifest and its recordings belong to the
repository that publishes them, and a second copy here would be a second answer to
*what does this plugin declare* — with no way to tell which of the two an operator
installed. So an entry is an origin and a reviewed revision, and everything else is
read out of that revision when CI asks.

**Implements:** [F5-R1](../10-functional/features/f-extensibility/f5-plugin-catalogue.md)–[F5-R3](../10-functional/features/f-extensibility/f5-plugin-catalogue.md),
[F5-R10](../10-functional/features/f-extensibility/f5-plugin-catalogue.md),
[F5-R12](../10-functional/features/f-extensibility/f5-plugin-catalogue.md)

---

## Why this is a separate repo

It meets [ADR-0004](../00-overview/decisions/0004-four-repo-split.md)'s test on every
count: its change rate is other people's rather than ours, its review style is reading a
stranger's data rather than reviewing our own code, and its release clock belongs to
whoever contributed last. Holding it inside `lemonfiber` would mean a binary release every
time somebody added a plugin, which is the coupling
[F1-R5](../10-functional/features/f-extensibility/f1-customisation.md) exists to prevent.

It is also the one repository in the org whose contributors are mostly **not** us, and
that changes what its CI is for. Everywhere else, CI protects a maintainer from their own
mistake. Here it is the first reviewer of an untrusted contribution, and it runs before a
human spends any attention.

## What's in it

```
lemonfiber-plugins/
├── plugins/
│   └── <id>.toml            where it is, and the revision that was read
├── registry/                the checks CI runs over an entry
├── targets.toml             the lemonfiber version the checks are held to
├── justfile
└── .github/
    ├── interim/             the validation and proof programs, copied from plugin-template
    └── workflows/
```

One file per plugin, and **nothing in it that cannot be read as a diff** (`REPO-R60`).
No archives, no encoded blobs, no generated artefacts. That constraint is what makes
human review possible at all, and it is the property
[F3-R10](../10-functional/features/f-extensibility/f3-stack-manifests.md) asks for.

An entry is short on purpose: an origin and a commit. The revision is the whole of what
review means here — a person read *that* tree, and moving the plugin forward is a pull
request moving the commit, which is the same person reading again. It is also what makes
[F5-R7](../10-functional/features/f-extensibility/f5-plugin-catalogue.md)'s *where it came
from, at which revision* answerable without the catalogue being where it came from.

The fixtures stay in the plugin's own repository and CI reads them there, at the pinned
revision, because the proofs it has to run (`F5-R2`) are the plugin's proofs against the
plugin's recordings. Reading them rather than copying them is also the only way the two
cannot drift.

## What its CI does

Three things, in order, before a human looks:

0. **Fetch.** The registered revision is fetched, and what is read out of it is data:
   the manifest, the recordings, and the release the plugin says it targets. Nothing in
   the registered repository is executed, here or ever (`REPO-R62`) — a catalogue that
   ran a stranger's script to find out whether the stranger's data was acceptable would
   be answering the question by doing the thing the question is about.
1. **Schema.** Every manifest is validated against the schema the binary publishes
   (`ARCH-R92`).
2. **Proofs.** Every declared proof runs against that plugin's recorded fixtures, and a
   contribution whose proofs do not pass is refused (`F5-R2`).
3. **Reach.** The declared pairs are checked statically — no undeclared flow, no address
   literal ([ADR-0022](../00-overview/decisions/0022-a-recipe-declares-pairs-not-lists.md)).

All three run the **same commands an author runs locally** — the plain subcommands
`F3-R13` already requires — from a pinned `lemonfiber` release named in the repository
(`REPO-R56`). A catalogue that validated
against a different build than the operator runs would be vouching for something it had
not tested.

## The review, and its honest limit

A human reads the diff and merges, which is possible precisely because a plugin is data.
What that buys is stated carefully in F5: a schema that was checked, proofs that ran, a
person who read it, and a signature tying what was fetched to what was reviewed.

What it does not buy is a reading of the **image**. A manifest is forty lines and a
container image is not reviewable by anybody, here or anywhere — which is why the image is
pinned by digest rather than vouched for
([ADR-0023](../00-overview/decisions/0023-a-pin-is-a-digest.md)).

**The reviewer is one person.** `security.md` already names that as a structural cap, and
an open contribution funnel through a single gate is this design's likeliest practical
failure. It is the reason `F5-R4` keeps an operator's own source on the same technical
terms: the catalogue is the curated lane, not the only road.

## Releases, and what a signature covers

The catalogue tags on its own clock and is **not a stream the version train cuts**
(`OPS-R59`). No `repos` list in `70-operations/versions/` names it — it appears there only in
`satisfied_in`, which tags nothing — and a plugin landing here
moves no version number in this organisation.

A release is signed (`F5-R3`), and the signature covers exactly what was reviewed
(`REPO-R57`). The signing capability is owed here before `L1-R2` delivers it for release
artefacts — one capability, two consumers, and the earlier consumer sets the date
([ADR-0023](../00-overview/decisions/0023-a-pin-is-a-digest.md)).

## What it never becomes

**Not a runtime dependency.** An installed plugin keeps working with this repository
unreachable, and installing from a named source still works (`F5-R10`). So the catalogue
publishes nothing that an installed plugin resolves while running (`REPO-R58`) — the
moment it did, every operator's stack would depend on this repository's availability.

**Not a service.** No backend, no database, no state beyond the repository (`REPO-R59`).
A catalogue that needed operating would be a second product, and it would be one this
project has said it does not build.

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R54** | *Withdrawn — carried to [REPO-R60](lemonfiber-plugins.md) when the catalogue became a register of origins rather than a copy of what it registers. The number is not reused.* |
| **REPO-R55** | *Withdrawn — carried to [REPO-R61](lemonfiber-plugins.md) for the same reason: the checks are made against a fetched revision rather than against a copy held here. The number is not reused.* |
| **REPO-R56** | Those checks MUST run the same commands an author runs locally, from a `lemonfiber` release pinned and named in the repository. |
| **REPO-R57** | A catalogue release MUST be signed, and what the signature covers MUST be exactly what was reviewed. |
| **REPO-R58** | The catalogue MUST NOT publish anything an installed plugin resolves at run time. |
| **REPO-R59** | The catalogue MUST hold no service, no database and no state beyond the repository itself. |
| **REPO-R60** | The catalogue MUST register each plugin as an origin and the revision of it that was reviewed, MUST hold no copy of a registered plugin's manifest or recordings, and MUST contain nothing that cannot be reviewed as a readable diff. |
| **REPO-R61** | Its CI MUST fetch each registered revision and, from the data in that revision alone, validate the manifest against the published schema, run every declared proof against the plugin's recorded fixtures, and check its declared reach statically; a registration failing any of these MUST be refused before human review. |
| **REPO-R62** | The catalogue MUST NOT execute anything from a registered repository, and MUST read that repository as data only. |

**Affected repos** (`GOV-R7`): `lemonfiber-plugins`.

## Related

- [F5 The plugin catalogue](../10-functional/features/f-extensibility/f5-plugin-catalogue.md) — what this repository is the implementation of
- [ADR-0023](../00-overview/decisions/0023-a-pin-is-a-digest.md) — signing, and why it arrives before `L1` owes it
- [ADR-0022](../00-overview/decisions/0022-a-recipe-declares-pairs-not-lists.md) — the reach its CI checks
- [releasing](../70-operations/releasing.md) — the streams this is deliberately not one of
