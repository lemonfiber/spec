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
| Each release's contract artefact describes the event stream, carries an example of every kind, read and action from the core's golden fixtures validated in CI, and is accompanied by the code registry as `contract/codes.json`, a `contract-diff.json` against the previous release and a generated OpenAPI document (D24, D25, D26) | [ARCH-R173 to ARCH-R177](../20-architecture/contracts/web-api.md) |

## 2026-10-08

| Decision | Where it lives |
|---|---|
| The machinery the documentation and contributor sites share lives once, in `website-kit`, a package each site takes by commit as it takes `brand`; nothing is published to a registry | [REPO-R84, REPO-R85](../30-repos/website-kit.md) |
| What a credential buys is never released: a value captured from a call that carried or read a credential-store value is held to that credential's service as the credential is, and a `release` on it is refused | [F8-R16, F8-R17](../10-functional/features/f-extensibility/f8-recipes.md) |
| The documentation keeps every minor from 0.16.0 on, plus `next` | [REPO-R89](../30-repos/website-docs.md) |
| Stable documentation renders the commits each release recorded; a repository the release recorded nothing for is rendered at its default branch's last commit on or before the release date | [REPO-R88](../30-repos/website-docs.md) |
| A released pair carries `from`, the service its value was read from, on the rehearsal and on the record, beside its `release` | [ARCH-R147, ARCH-R150](../20-architecture/contracts/web-api.md) |
| Every repository's `AGENTS.md` opens with the pointer to the board and the shared rules and holds no more than 120 lines, refused by `hygiene` otherwise; every repository's file is brought within it in the same release | [GOV-R50](working-in-the-repositories.md) |
| An approved proposal lands as Draft: a new feature at `status: draft`, and rows added to an existing feature each opening with `*Draft:*`; a later reviewed pull request removing the marking hardens it | [GOV-R42, GOV-R44](rfc-process.md), [GOV-R48](canonical-spec.md) |
| The web console lists, mints and revokes integration keys: the operator's password is typed for each mint and never kept, and the secret is shown once, in a panel that drops it when closed or on reload | [C10-R2, C10-R3](../10-functional/features/c-trust/c10-integration-keys.md) |
| The web console installs, updates and removes plugins, bound to the offer: it draws the offer's whole manifest (what it writes, what it reaches, its verification, every released pair with its `release` and `from`) before the yes, and the yes names that offer | [F6-R15, F6-R17](../10-functional/features/f-extensibility/f6-plugin-lifecycle.md) |
| The web console takes the operator's side of a mobile hand-off now; the member's side gets a design of its own later | [G9](../10-functional/features/g-ux/g9-mobile-handoff.md); the member's side is not yet a requirement |
| The web console explains a domain term inline wherever it appears (option b): its own words and every glossary word or form found in what lemonfiber writes, with a switch kept per browser to turn explanations off | [G2-R1, G2-R7](../10-functional/features/g-ux/g2-plain-language.md) |
| The web console draws the scannable hand-off code with one small, zero-dependency, MIT-licensed QR encoder taken as a runtime dependency, pinned exactly and rendered as inline SVG; the companion uses the same choice for its pairing code | This row, [G9-R2](../10-functional/features/g-ux/g9-mobile-handoff.md) |
| `sdk-ts` is kept by the web console's agent, which adds its client calls for the setup routes once the contract describes their bodies | This row; the bodies are [ARCH-R133](../20-architecture/contracts/web-api.md) |
| The core publishes the setup routes' bodies in the contract (option a): `wizard::Answer` and `recovery::Choice` derive their schema, and the six setup routes are described with them | [ARCH-R133](../20-architecture/contracts/web-api.md) |
| What's new (`news`, `news-items`) stays with the companion, and the web console does not mark new items | [N27](../10-functional/features/n-companion/n27-what-the-phone-keeps.md) |
| The documentation site cuts a release's frozen build on its own nightly run after the release's day ends; release-finalize sends it no dispatch, since on the release day there is nothing it may cut | [REPO-R88, REPO-R89](../30-repos/website-docs.md) |
| The companion keeps what it implements only in its `status/<feature>.toml` tracker: its `.docs/requirements` pages are retired once the tracker holds every requirement they named, and the prose still worth keeping moves into the docblocks of the code that keeps each requirement | [OPS-R74](../70-operations/staging.md); this row |
| The companion installs a plugin as drafted for N5, N20 and N25: it rehearses the install in full, approves each value that would leave the machine on its own and agrees to the install separately, and takes the source in one text field that explains the three shapes it may take | [N5](../10-functional/features/n-companion/n5-connecting-the-stack.md), [N20](../10-functional/features/n-companion/n20-what-a-plugin-may-send.md), [N25](../10-functional/features/n-companion/n25-a-plugin-after-it-lands.md) |
| The companion takes no recipe inputs: a plugin whose recipe asks for one is rehearsed in full, and its install says the inputs are given at the web console or the terminal | [N17-R6](../10-functional/features/n-companion/n17-where-a-message-goes.md); this row |
| The companion's plugin work lands in two pull requests: the list, installing, the rehearsal, agreeing and following first, then updating and removing | This row |
| The documentation site's stack-manifest pages keep only what an operator does with a stack and link the field reference to the contract on the frontpage; once the core publishes `contract/stack-manifest.schema.json`, as it does the plugin manifest's, the site renders the field tables from it | [REPO-R82](../30-repos/website-docs.md), [ARCH-R172](../20-architecture/contracts/stack-manifest.md) |
| The organisation requires a sign-off on every commit made through the web, so GitHub appends the merger's sign-off to a squash merge | This row, [GOV-R29](dco.md) |
| A squash merge in every repository takes the pull request's title and body as the commit message, and a required `squash-message` check, shared like `dco`, holds the title to a conventional subject and the body to the `Spec:` line and each author's sign-off | [GOV-R5](canonical-spec.md), [GOV-R29](dco.md), [GOV-R62](cross-repo-ci.md) |
| The frontpage shows all twenty-two services the stack runs, lemonfiber's own request gate and decline service among them, and its build fails where its list and the stack manifest's `include` differ | This row, [ARCH-R171](../20-architecture/contracts/stack-manifest.md) |
| The frontpage offers a claim on a page per goal, `/claim/<id>/`, linked from the work to pick up and from the requirement's row: a claimed goal names its pull requests and their authors and offers nothing, a met one says so, each repository shows its open pull requests against the cap and offers nothing at it, and the claim is offered as `lfdev claim <id>` and as the tracker row to paste in GitHub's editor, with the pull request's title and the `Spec:` and sign-off lines its body ends with | This row, [GOV-R57](working-in-the-repositories.md), [GOV-R58](working-in-the-repositories.md), [GOV-R62](cross-repo-ci.md) |
| The frontpage's propose and gap forms are proved end to end from an account outside the organisation, by a checklist in the website's README that the maintainer runs | This row, [GOV-R60](working-in-the-repositories.md) |
| The release train keeps one bump pull request per repository, on one branch rebuilt from `main` for each version and retitled to it; the pin fan-out's per-version pull requests are closed in favour of it | [OPS-R85](../70-operations/staging.md) |
| The shared checks that run in seconds are one job per pull request, `gates`, each a step that runs whatever the others concluded, its summary listing every result and branch protection requiring it as one context; what writes to a pull request is a second job that judges nothing; the tests, coverage, CodeQL's analysis and Sonar stay jobs of their own | [Q-R82](../40-quality/ci-cd.md) |
| The plugin reading lists each recipe input a plugin asks the operator for, with its name, its question and whether it is a secret, so a surface collects it before the yes; a secret input is never shown back | [F8-R19](../10-functional/features/f-extensibility/f8-recipes.md) |
| On a stack with no configuration the web console shows the setup wizard in place of everything else until setup is applied | [A2-R1](../10-functional/features/a-getting-started/a2-setup-wizard.md) |
| Where configuration already exists the web console offers no wizard: it works as usual, and a "Change setup" entry leads to the reconfiguration screens | [A2-R14](../10-functional/features/a-getting-started/a2-setup-wizard.md), [A4](../10-functional/features/a-getting-started/a4-reconfiguration.md) |
| An apply that stopped part-way opens the web console's wizard on a recovery screen first, naming what was written and offering resume, roll back and start over | [A2-R10](../10-functional/features/a-getting-started/a2-setup-wizard.md) |
| The web console's wizard ends on a "Setup written" screen that starts the stack, then connects its services as `seed` does, with the console one press away throughout | [A2-R13, A2-R17](../10-functional/features/a-getting-started/a2-setup-wizard.md) |
| Until lemonfiber reports what a setup step that only informs has found, the web console's wizard says what that step is for and claims no finding | [A2-R5, A2-R9](../10-functional/features/a-getting-started/a2-setup-wizard.md) |
| Going without a VPN in the web console's wizard is sent only once the operator has ticked a sentence saying everyone they share with will see their home address | [A2](../10-functional/features/a-getting-started/a2-setup-wizard.md) |
| A plugin reading lists each input its recipes ask the operator for, with its name, its question and whether it is a secret; no client sends a secret input, the companion takes no input at all, and the web console takes the ones that are not secret | [F6-R17](../10-functional/features/f-extensibility/f6-plugin-lifecycle.md) |

## 2026-10-09

| Decision | Where it lives |
|---|---|
| No step of `gates` runs code out of a pull request's tree: each action it calls is one known to read the tree as data; markdownlint is handed the tracked Markdown, read out of git, and the canonical configuration, never a configuration of the pull request's; OSV-Scanner runs in a container given the tree read-only and nothing of the job's, with every call analysis off; and a workflow edits or removes a sticky comment only where its own token wrote it | [Q-R82](../40-quality/ci-cd.md), [GOV-R33](cross-repo-ci.md) |
| A pull request cannot change what its repository's checks run on its own say (option A): `pin-only`, run from the base branch on `pull_request_target` with a read-only token and nothing of the pull request checked out, fails any change under `.github/workflows/` or `.github/actions/` other than spec's pins moving forward along `main`, and such a change is merged by a maintainer by choice; it is required in every repository once that repository calls it | [Q-R83](../40-quality/ci-cd.md) |

## Requirements

| ID | Requirement |
|----|-------------|
| **GOV-R49** | A decision the maintainer makes MUST be recorded in this specification on the day it is made: as a requirement or an ADR where it decides what is built, and as a dated row in this log, pointing at that requirement or ADR or standing as the record itself, where it decides how the work is done. A decision recorded only outside a repository MUST NOT be acted on as settled. |

## Related

- [Change lifecycle](change-lifecycle.md)
- [Architecture decision records](../00-overview/decisions/README.md)
