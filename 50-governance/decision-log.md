# Decision log

**Status:** Accepted

Every decision the maintainer makes, in the order it was made, and where it now
lives in this specification.

---

## How a decision is recorded

A decision is recorded in this specification on the day it is made (`GOV-R49`).
Where it decides what is built, it lands as a requirement or an
[ADR](../00-overview/decisions/README.md), and the row here points at it. Where it
decides how the work is done, the dated row here is the record. A note kept outside
a repository is not where a decision lives: nobody else can read it, nobody reviews
it, and it goes when the machine it is on does.

A row states the decision as it was made. Why it was made is the requirement's or
the ADR's to say, and a row whose decision has not reached either yet says so.

Decisions about a repository outside this organisation, such as
`nightworksio/php-mutation-gate`, are recorded in that repository.

## 2026-09-29

| Decision | Where it lives |
|---|---|
| What the phone keeps: a separate 32-byte data key in the platform keychain at its narrowest accessibility; AES-256-GCM through Laravel's `Encrypter` with that key, never the app-wide key; the payload sealed and the bookkeeping (kind, read time, shape version, a keyed hash of the stack) queryable | [ADR-0035](../00-overview/decisions/0035-what-the-phone-keeps-and-how.md), [N27](../10-functional/features/n-companion/n27-what-the-phone-keeps.md) |
| Readings kept per stack (health, what runs, updates, household), read only until a fresh reading arrives; repair offers never kept; preferences kept (lock period, notification kinds, where you were, stack order) | [N27](../10-functional/features/n-companion/n27-what-the-phone-keeps.md) |
| Markers for what is new on updates, household requests and findings, filterable per stack and in a What's new list by kind and stack | [N27](../10-functional/features/n-companion/n27-what-the-phone-keeps.md) |
| Kept readings live for 1–365 days or until the stack is forgotten, per phone, default 30; readings in an old shape are discarded and preferences migrated | [N27](../10-functional/features/n-companion/n27-what-the-phone-keeps.md) |
| Without secure storage nothing is kept between launches, and the settings screen says why; a lost key wipes the unreadable store and leaves pairings in place | [N27](../10-functional/features/n-companion/n27-what-the-phone-keeps.md) |
| Storage lives inside the module that owns it (`src/Internal/Store` and its own migrations), behind a port that module declares; no module exists only to keep data | [ADR-0035](../00-overview/decisions/0035-what-the-phone-keeps-and-how.md) |
| Finding your way (N28): the bottom bar is hidden on screens that are not tabs; Doing and Logs count as Services; Allowance is an operator screen with the full menu; the switcher is a bottom sheet; sign-in shows the switcher only; What's new and the settings rows are placeholders until N27 fills them; menu items push their screen; the drawer comes from each stack screen through the shared trait | [N28](../10-functional/features/n-companion/n28-finding-your-way.md) |
| Short state words and menu labels in English and Dutch, as approved in the N28 work | [N28](../10-functional/features/n-companion/n28-finding-your-way.md) |
| Navigation and controls carry one- or two-word labels with an icon, and sentences only where something is explained | Not yet a requirement: the plain-language pass over the app's wording needs a voice rule |

## 2026-09-30

| Decision | Where it lives |
|---|---|
| Every refusal carries a structured, machine-readable reason, and the status stays `403` | [ARCH-R138, ARCH-R139](../20-architecture/contracts/web-api.md), [N1-R75](../10-functional/features/n-companion/n1-companion-app.md), [N3-R17](../10-functional/features/n-companion/n3-household-companion.md) |
| N28: the Dutch group headings are Huishouden · Toegang · Machine · Instellingen · Hulp; a placeholder screen says "This isn't in this version of the app yet." / "Dit zit nog niet in deze versie van de app."; the ☰ screen-reader label is "Menu" | [N28](../10-functional/features/n-companion/n28-finding-your-way.md) |

## 2026-10-05

| Decision | Where it lives |
|---|---|
| NZBHydra2's authentication is seeded as `D1-R22` to `D1-R26` drafted, locked in 0.17.0 beside `F9-R2` | [D1](../10-functional/features/d-content/d1-seed.md), [0.17.0](../70-operations/versions/0.17.0.toml) |
| What `backup::REBUILT` holds moves to a per-service field in `stack.toml`, as a follow-up across the spec, the stack and the core | Not yet a requirement |
| Two core pull requests, lemonfiber#864 and #870, are held until each security flag on them is checked adversarially and fixed or shown not to apply | This row |
| A consumer of `sdk-python` vendors it and writes the vendored revision to `_vendor/lemonfiber/REVISION` as 40 hexadecimal characters | This row |
| After the first release pushes `ghcr.io/lemonfiber/lemonfiber`, the package is made public | This row |

## 2026-10-07

| Decision | Where it lives |
|---|---|
| F8's engine failure (option C): a problem with `PLUGIN-35` or `PLUGIN-36`, plus a structured per-step field on the problem, optional and absent elsewhere | [G4-R17](../10-functional/features/g-ux/g4-error-model.md) |
| The core's offer is optional (option A): refused if it has moved, and its absence acts as it does without one | spec#652 |
| Pause, resume and restart are idempotent; diagnose and update are not | [ARCH-R160](../20-architecture/contracts/web-api.md) |
| The event stream is tied to its job: the envelope carries `job`; a pull is state; the command line says `pull`; a start pulls what is missing, then brings the stack up, with Compose 2.22 or later | [web-API contract](../20-architecture/contracts/web-api.md), spec#649 |
| `N28-R6`: option A | [N28-R6](../10-functional/features/n-companion/n28-finding-your-way.md) |
| `sdk-python` lists the breaking changes it accepts in `pyproject.toml` | This row |
| Companion slice 13: D1 (b), D2 (c), D3 (a), D4 (a), D5 (a), D6 (b) | This row; the options these letters choose between are not recorded here |
| Every repository a version is satisfied in keeps its own tracker, and the release gate and the no-stubs gate read all of them | spec#654 |
| A tracker row is one requirement: its id, its state, its evidence by path and test, and optionally the commit it landed in; the binary's rows move to that shape | spec#654 |
| A report of where every goal of every unreleased version stands (met, built but unmarked, claimed, open) runs on a schedule, and `just goals <version>` writes it locally | spec#657 |
| Work is claimed by the `Spec:` lines of open and draft pull requests, and `./claim` is retired | spec#657 |
| A feature's maturity is generated from the trackers and the manifests, with the reverse check in the specification's CI first | spec#658 |
| A manifest comment never says how far a goal has got, and a lint with a narrow, tested word list refuses it with a clear message | spec#659 |
| Every decision lands as a pull request on this specification the same day, with a dated log for decisions about the process | `GOV-R49` |
| The kept-and-where half of the companion's register moves into the companion's tracker, and the register's disagreements with the code are fixed | This row |
| The policy in `AGENTS.md`, the AI contributors' rules and the working notes kept outside the repositories moves into this section; every `AGENTS.md` points first at the report, then at this section; subagents work in worktrees and the main session in the main checkout | [GOV-R50, GOV-R51](working-in-the-repositories.md) |
| `IMPLEMENTATION-STATUS.md` is no longer committed once the documentation site's roadmap reads the report, and is generated until then; a tracker stays under 1,000 lines, split into `status/<feature>.toml` where it would not | spec#654 |
| Each generation of the report is published where it stays fetchable, as a workflow artifact or release asset, with the revisions it read recorded in it; nothing is committed hourly; the documentation site vendors a copy of `state.json` with its provenance, and its format is held stable and documented | spec#657 |
| An agent checks CI on every pull request it owns while it waits on any one, and fixes reds at once | [GOV-R53](working-in-the-repositories.md) |
| The forge is read through REST only, a pull request's checks at most every ten minutes; the spec, the binary and `sdk-php` no longer require a pull request to be up to date, so a branch is rebased only on a real conflict | [GOV-R52, GOV-R54](working-in-the-repositories.md) |
| The roadmap, the board, the repositories, the work in flight, the releases and the proposals are on `lemonfiber.app`, rendered from the report's snapshot; the documentation site renders no project status. This replaces the rows above that had the documentation site's roadmap read the report and vendor `state.json`: `IMPLEMENTATION-STATUS.md` goes once the frontpage reads the snapshot and the documentation site no longer mirrors it | [REPO-R39, REPO-R64](../30-repos/website-lemonfiber.md), [REPO-R68](../30-repos/website-docs.md) |
| The changelog is published at `lemonfiber.app/releases/`, from the core's changelog JSON | [REPO-R64](../30-repos/website-lemonfiber.md) |
| The snapshot is published as the assets of a rolling `board` release in `spec`, replaced on each run, and as the run's artifact; it is a new `board.json` beside `state.json`, whose `format: 1` is unchanged | [OPS-R80, OPS-R81](../70-operations/board-format.md) |
| A repository the report cannot read is listed under `unread`, its goals read `unknown`, and the report still publishes; the release gate still refuses | [OPS-R76](../70-operations/staging.md) |
| The report runs when a manifest, the catalogue or a tracker changes on a default branch and when a release is published, and hourly | [OPS-R82](../70-operations/board-format.md) |
| Where the snapshot cannot be read, the frontpage's build fails and the previous deployment stays live; no committed copy stands in | [REPO-R40](../30-repos/website-lemonfiber.md) |
| The board's interactive parts are a framework island (Preact or Svelte), bundled with the site | [REPO-R65](../30-repos/website-lemonfiber.md) |
| The website helps a contributor compose a change and never creates anything itself: its forms build the change, and submitting opens GitHub prefilled under the person's own account, where they open the pull request, or the issue that becomes one; no bot or server acts on their behalf | [GOV-R60, GOV-R61](working-in-the-repositories.md) |
| A proposal or a gap enters as a pull request adding a Draft proposal with no identifier, and identifiers are allocated when a maintainer approves it; the RFC issue form stays an optional entry a maintainer converts | [GOV-R40 to GOV-R45](rfc-process.md) |
| A claim made with the developer command line opens with an empty signed commit carrying `Spec:` and a sign-off; a claim made from the website adds the repository's `status.toml` row as `open` | [GOV-R57](working-in-the-repositories.md) |
| A repository holds at most three open pull requests opened by people and agents, the organisation's bots not counted; the command line refuses a fourth claim, a bot comments, and the board flags the repository | [GOV-R58](working-in-the-repositories.md) |
| The report derives what the board flags about claims, so the website and the command line show the same: a repository over the cap, a goal of an unreleased version cited by more than one open pull request from people or agents, and a draft with no commit for more than fourteen days | [GOV-R58](working-in-the-repositories.md), [OPS-R80](../70-operations/board-format.md) |
| The release train's tracker and planning issues are retired: the board's version page replaces the tracker, and a release blocker is a list in the manifest | [OPS-R83, OPS-R44, OPS-R45, OPS-R55](../70-operations/staging.md) |
| Contributor material moves to a site of its own, apart from the documentation site | [ADR-0040](../00-overview/decisions/0040-three-sites-each-with-one-reader.md), [REPO-R69 to REPO-R73](../30-repos/website-contribute.md), [REPO-R80](../30-repos/website-docs.md) |
| The specification is rendered on `lemonfiber.app`, not on the documentation site | [ADR-0040](../00-overview/decisions/0040-three-sites-each-with-one-reader.md), [REPO-R79](../30-repos/website-lemonfiber.md) |
| The documentation site stays on Astro Starlight, extended | [ADR-0040](../00-overview/decisions/0040-three-sites-each-with-one-reader.md) |
| The developer command line has a repository of its own, `tool-lfdev`, and installs as `lfdev` | [tool-lfdev](../30-repos/tool-lfdev.md), [REPO-R74](../30-repos/tool-lfdev.md) |
| `lfdev` is written against Python's standard library alone | [REPO-R74](../30-repos/tool-lfdev.md) |
| The contributor site is the repository `website-contribute.lemonfiber.app`, served at `contribute.lemonfiber.app` | [website-contribute.lemonfiber.app](../30-repos/website-contribute.md) |
| `lemonfiber.app` renders the specification at the commit of `spec` the board snapshot read, and rebuilds it on the same event as the board | [REPO-R79](../30-repos/website-lemonfiber.md) |

## 2026-10-08

| Decision | Where it lives |
|---|---|
| The machinery the documentation and contributor sites share lives once, in `website-kit`, a package each site takes by commit as it takes `brand`; nothing is published to a registry | [REPO-R84, REPO-R85](../30-repos/website-kit.md) |
| What a credential buys is never released: a value captured from a call that carried or read a credential-store value is held to that credential's service as the credential is, and a `release` on it is refused | [F8-R16, F8-R17](../10-functional/features/f-extensibility/f8-recipes.md) |
| A released pair carries `from`, the service its value was read from, on the rehearsal and on the record, beside its `release` | [ARCH-R147, ARCH-R150](../20-architecture/contracts/web-api.md) |
| Every repository's `AGENTS.md` opens with the pointer to the board and the shared rules and holds no more than 120 lines, refused by `hygiene` otherwise; every repository's file is brought within it in the same release | [GOV-R50](working-in-the-repositories.md) |
| An approved proposal lands as Draft: a new feature at `status: draft`, and rows added to an existing feature each opening with `*Draft:*`; a later reviewed pull request removing the marking hardens it | [GOV-R42, GOV-R44](rfc-process.md), [GOV-R48](canonical-spec.md) |

## Requirements

| ID | Requirement |
|----|-------------|
| **GOV-R49** | A decision the maintainer makes MUST be recorded in this specification on the day it is made: as a requirement or an ADR where it decides what is built, and as a dated row in this log, pointing at that requirement or ADR or standing as the record itself, where it decides how the work is done. A decision recorded only outside a repository MUST NOT be acted on as settled. |

## Related

- [Change lifecycle](change-lifecycle.md)
- [Architecture decision records](../00-overview/decisions/README.md)
