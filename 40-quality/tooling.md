# Tooling

**Status:** Accepted

The external tools the project relies on. Every one is **free for public
repositories** or fully open source — no paid, team, or enterprise tier is
required, because none is available to an open project on a free org.

**Satisfies:** [ci-cd](ci-cd.md), [security](security.md),
[roadmap M10](../00-overview/roadmap.md#m10--release-engineering).

---

## The constraint that shapes every choice

The org is on GitHub's free plan. That rules out org-level rulesets, required
workflows, and other Enterprise features — so **branch protection is configured
per repo**, and anything org-wide is achieved through mechanisms free plans do
have: the [`.github` repo](../30-repos/README.md) for inherited community files,
[reusable workflows](../50-governance/cross-repo-ci.md) sourced from the spec, and
shared config presets.

Every tool below was chosen to work within that constraint.

## The toolchain

| Concern | Tool | Free basis | Where |
|---------|------|-----------|-------|
| **Governance gate** | `spec-check` (in-repo) | our own | all repos |
| **Spec integrity** | `integrity.py` (in-repo) | our own | spec |
| **Code quality + coverage** | **SonarQube Cloud** | free for public | all repos |
| **SAST** | **CodeQL** | free for public | the repos whose language or workflow surface it can analyse |
| **Secret scanning** | **gitleaks** | OSS | all repos |
| **Dependency/vuln scanning** | **OSV-Scanner** | OSS | all repos, via the shared `security.yml` |
| **Supply-chain posture** | **OpenSSF Scorecard** | free for public | each repo that publishes an artefact or the specification; the newest four are outstanding (`Q-R59`) |
| **Rust licences + advisories** | **cargo-deny** | OSS | lemonfiber |
| **Coverage generation** | **cargo-llvm-cov** | OSS | lemonfiber → Sonar |
| **Workflow lint** | **actionlint** | OSS | all repos |
| **Spell check** | **typos** | OSS | all repos |
| **Link check** | **lychee** | OSS | all repos |
| **Markdown lint** | **markdownlint** | OSS | all repos |
| **Dependency updates** | **Dependabot** | native to GitHub | all repos |
| **Pre-commit hooks** | none — git's own | — | `.githooks/`, turned on per clone; see below (`OPS-R51`) |
| **Pre-push guard** | [`.githooks/pre-push`](../shared/hooks/pre-push) | our own | all eight code repos, via `core.hooksPath` |
| **Task runner** | **just** | OSS | the Rust, spec, stack, brand and site repos; the npm and Composer repos use their own script runner |
| **Changelog** | **git-cliff** | OSS | lemonfiber, sdk-ts, sdk-php |
| **Release binaries** | **cargo-dist** | OSS | lemonfiber |
| **Docs site** | **Astro Starlight** | OSS | website-docs.lemonfiber.app |
| **Web lint** | **ESLint** (`typescript-eslint`) | OSS | lemonfiber-web, sdk-ts |
| **Web format** | **Prettier** | OSS | lemonfiber-web, sdk-ts |
| **Web accessibility** | **axe-core / pa11y** | OSS | lemonfiber-web |

## Why these, specifically

### SonarQube Cloud carries quality *and* coverage

Free for public repos, native GitHub Action, analyses Rust. It ingests the lcov
`cargo-llvm-cov` produces, so coverage lives there too — no separate Codecov.
Per [Q-R61](testing-strategy.md#coverage--100-where-it-applies), coverage on
**applicable** code is a merge gate: `cargo-llvm-cov` enforces 100% over that set
locally and in CI, and Sonar surfaces the same number. The scope — not a lax gate —
is what keeps it honest; the excluded categories are annotated in the source
([Q-R62](testing-strategy.md)).

The free plan's own quality gate cannot be raised to this standard, so both the
coverage gate and a zero-open-issues gate are enforced in CI directly rather than
by Sonar's gate ([ci-cd](ci-cd.md#sonarcloud--enforced-in-ci-not-by-the-plan-gate),
`Q-R64`).

Requires a one-time `SONAR_TOKEN` secret, added to the repo after it exists.

### Dependabot, and the gate that cites for it

Every dependency bump must cite `GOV-R12` ([canonical-spec](../50-governance/canonical-spec.md)).
Dependabot cannot write a trailer: `commit-message` sets a prefix and a scope, and
there is no body, no template and no way to add a line to the pull request. So
`spec_check.py` **supplies `GOV-R12`** for a pull request GitHub says
`dependabot[bot]` opened, and then runs the existence check unchanged — the
identifier still has to exist on `spec@main`, and the run still prints what it
accepted. The exemption reads `pull_request.user.login` and nothing the pull
request carries; see [ADR-0016](../00-overview/decisions/0016-dependabot-over-renovate.md).

`dco` needed no change — `dco_check.py` already exempts a bot-authored commit,
because GitHub authors it and there is no human to attest.

Each repo carries its own `.github/dependabot.yml`. There is no org-level preset:
unlike Renovate, Dependabot cannot extend a shared config, so the policy lives in
one copy per repo and the copies are kept alike by review.

The policy those copies carry: minor and patch bumps travel as one grouped pull
request per ecosystem, a major is left out of the group so it arrives on its own
carrying the `major` label, and the `lemonfiber/spec` shared-workflow pins are
their own group, excluded from the three-day release-age wait — a fixed gate
reaches its consumers without one. Security updates are exempt from the wait by
construction and are never grouped, so each vulnerability arrives as its own pull
request.

### What Dependabot does not watch

Renovate was configured to watch four things by regular expression and three more
by mechanisms Dependabot has no equivalent of. **Renovate never ran**, so nothing
here regressed in practice — but the intent was real. The two scanner versions
are now watched again, by the two different means below; the rest is not.

| What | Where it lives now | Who notices it going stale | To bring it back |
|------|--------------------|----------------------------|------------------|
| `gitleaks` CLI version | `.github/workflows/security.yml` — `GITLEAKS_VERSION`, read both by the step that downloads it and by the step that checks it | **The step that checks it**, which fails the run once the release it names has been superseded for more than 30 days | Done, but not by Dependabot — see below |
| `osv-scanner` version | `.github/workflows/security.yml` — the `google/osv-scanner-action/osv-scanner-action` pin | **Dependabot**, under `github-actions` | Done. The action is a container action, so the `uses:` pin is what fixes the scanner version |
| `python-version:` written inline in workflows | nine sites, all `"3.12"` — seven here, one in `lemonfiber`, one in `brand` | **Nobody**, until 3.12 leaves support in Oct 2028 | No Dependabot manager reads it; a scheduled check, or `.python-version` + a linter that reads it |
| `node-version:` written inline in workflows | **nowhere** — every repo uses `node-version-file: .nvmrc` | n/a | The manager watched nothing; it can simply go |
| `.nvmrc` | four repos — `lemonfiber-web`, `sdk-ts`, `website-docs.lemonfiber.app`, `website-lemonfiber.app` | **Nobody.** `engines: node >=26` in `package.json` is a floor, not a bump | No Dependabot manager reads `.nvmrc` |
| Lockfile maintenance (a weekly refresh with no manifest change) | n/a | **Nobody.** Transitive dependencies drift until a direct bump moves them | No equivalent; `npm update` / `cargo update` on a schedule |
| Semver ranges pinned to exact versions (`:pinAllExceptPeerDependencies`) | n/a | n/a | No equivalent. Dependabot updates within a range and widens it; it does not pin |
| The dependency dashboard | n/a | n/a | No equivalent. The closest thing is each repo's Dependabot alerts tab |

Two of the three that matter are now closed. The third, `python-version:`, is
not, and stays as written above.

### The two scanners, and why they are watched differently

Both tools publish a GitHub Action, and calling one turns an unwatched string in
a `run:` block into a pinned `uses:` that Dependabot already tracks under
[ADR-0009](../00-overview/decisions/0009-action-pinning.md). That worked for one
of them.

**osv-scanner** is called as `google/osv-scanner-action/osv-scanner-action`,
pinned by SHA. It is a container action, so the pin selects the scanner image as
well as the action, and Dependabot advances both together. The hand-written
exit-code arm that treated `128` as "no package sources, nothing to scan" is now
the scanner's own `--allow-no-lockfiles` flag; the action's entrypoint maps `128`
to success either way, and warns when the flag is absent.

**gitleaks** cannot be. `gitleaks/gitleaks-action` requires a `GITLEAKS_LICENSE`
secret for any repository an organisation owns — still true at v3.0.0, and this
org owns every repository here. The key is free to obtain, but it is a
registration, a secret each caller of the shared workflow would have to forward,
and a licence check against a third-party server standing on the critical path of
a required gate. The action is also not open source: since v2.0.0 it ships under a
Gitleaks LLC end-user licence agreement, where the CLI stays MIT. `gitleaks/gitleaks`
itself publishes no action, and Dependabot's `github-actions` parser skips a
`uses: docker://…` reference, so the published container is no route either.

So the CLI stays fetched by hand, and a step beside the scan reads the latest
gitleaks release and compares it to the version that just scanned. Being behind is
a notice for the first month and a failure after it — the same split, for the same
reason, as `pins` in `hygiene.yml`. An answer that cannot be read after three
attempts is a failure, not a pass: a watch that says nothing when it could not look
is the failure it exists to prevent.

### The hooks, and why there is no hook manager

`OPS-R51` asks for a pre-commit hook running the fast CI-blocking checks. lefthook
was chosen for it once — a single Go binary, no runtime to install — and six repos
carried a `lefthook.yml` written to that brief. **None ever installed it.** No
recipe or package script ran `lefthook install`, so the configs described hooks
that had never run, and one of them named a `scripts/guards.mjs` that had been
renamed underneath it.

They could not have been installed alongside the other local hook anyway. The
pre-push guard needs `core.hooksPath .githooks`, and git then reads that directory
**only** — anything a manager wrote to `.git/hooks` is ignored. lefthook 2.x
detects the setting, refuses to install, and offers `--reset-hooks-path`, which
turns the guard off. The one command that repairs the dead config disables the
working one.

So the hooks are files in `.githooks/`, and there is no manager:

| file | what it does | shared? |
|------|--------------|---------|
| [`pre-push`](../shared/hooks/pre-push) | refuses a push that would leave a branch carrying no commit `origin/main` does not — the shape of a mistake that destroyed two branches and closed their pull requests in one day — and a push straight to `main` | yes, byte-identical |
| [`commit-msg`](../shared/hooks/commit-msg) | says now what `commitlint`, `dco` and `spec-check` would say after a push: a conventional subject, a sign-off, a `Spec:` citation | yes, byte-identical |
| `pre-commit` | the fast checks that repository runs — formatting, typos, lint on staged files | no, per repo |

The first two are the same everywhere, so they live in [`shared/`](../shared/) and
`check_shared_files.py` holds each copy to the original. The third is not: `cargo
fmt` and `prettier` are not the same command, and pretending otherwise would put a
tool in a repository that does not have it.

Each skips a check whose tool is absent, so a contributor without `typos`
installed gets CI's answer rather than a hook that cannot run. None of them
duplicates a slow gate (`Q-R57`): tests, clippy and coverage stay in `just ci`,
because a hook that takes a minute is a hook people turn off, and one that is off
enforces nothing.

Enabling is the hard part regardless, because `core.hooksPath` is per-clone local
config that no commit can carry. Each repo sets it from a command a contributor
already runs — `just ci`, `npm install`/`npm ci`, `composer install` — and a clone
nobody has installed dependencies into is genuinely unprotected. What is enabled
where, and where it still does not reach, is in
[shared/README.md](../shared/README.md#turning-it-on).

### actionlint would have caught a real bug

The workflow-injection guidance exists because untrusted event data in a `run:`
block is exploitable. `actionlint` detects exactly that class, plus shellcheck on
embedded scripts. It runs over every repo's workflows.

### just — the task runner

A `justfile` per repo gives named tasks (`just test`, `just ci`, `just check`)
that mirror CI locally, so a contributor runs the same commands the pipeline does.
It matches the CLI's own ergonomics: discoverable, self-documenting, no hidden
make magic.

### Astro Starlight — one docs site for the whole org

[Roadmap M10](../00-overview/roadmap.md#m10--release-engineering) calls for a published
docs site. It is `website-docs.lemonfiber.app`, and it renders this specification
alongside each repo's own documentation rather than restating either
([ADR-0015](../00-overview/decisions/0015-docs-site-renders-what-it-does-not-own.md)).
Starlight (Astro, OSS) builds it to a static site on GitHub Pages — free for public
repos — with Pagefind search that runs in the browser and no third-party origin.
`lychee` and `starlight-links-validator` check every link, authored and mirrored, so
the published site never ships a broken one.

### git-cliff — changelog from history

Because commits carry structured trailers (`Spec:`) and follow a consistent shape,
a changelog can be generated rather than hand-maintained. git-cliff (Rust, OSS)
does this at release time alongside `cargo-dist`.

### ESLint and Prettier — because the rules that matter are type-aware

Web work — [`lemonfiber-web`](../30-repos/lemonfiber-web.md) and
[`sdk-ts`](../30-repos/sdk-ts.md) — lints with ESLint and formats with Prettier.

The rule set doing the work is `typescript-eslint`'s `strictTypeChecked`, which asks
the type checker rather than reading the syntax tree: a floating promise, an `any`
crossing a boundary, an `await` on something that was never a promise. Those cannot be
answered from a parse, so a linter that only parses cannot implement them, however
fast it is. This is the same bar the Rust side sets with `clippy::pedantic` and
`-D warnings`, which is why the two repos are held to it identically
([lemonfiber-web](../30-repos/lemonfiber-web.md)).

Prettier formats and ESLint does not — its formatting rules stay off, so the "one
formatter, no arguments" posture ([code-standards](code-standards.md)) holds with one
tool deciding layout rather than two arguing about it.

Paired with axe-core / pa11y for the accessibility testing the
[contrast contract](../60-brand/accessibility.md) and
[G3](../10-functional/features/g-ux/g3-accessibility.md) require.

## Anti-drift

The tooling is kept consistent across repos by construction, not vigilance:

- **Reusable workflows** in the spec repo (`hygiene`, `security`, `spec-check`)
  are called by three-line wrappers in each repo. One definition each.
- **Dependabot config** is one file per repo. It is the one thing here that *is*
  copied: Dependabot cannot extend a shared preset, so the copies are kept alike
  by review rather than by construction ([ADR-0016](../00-overview/decisions/0016-dependabot-over-renovate.md)).
- **`.github` repo** supplies community files org-wide.
- **`shared/`** in the spec repo holds the files that must be copied because a tool
  or GitHub reads them from the tree it is given — the two lint configs and the
  brand assets a README shows. The `shared-files` job in the hygiene gate fails a
  copy that has drifted from the one here.
- **lefthook and just** configs are small and per-repo, but mirror the reusable
  CI so they cannot demand something CI doesn't.

The distinction worth keeping straight: a reusable workflow is *not* copied, so it
cannot drift. A lint config **is** copied, because the gate checks out the calling
repository and lints that tree — the org's copy never arrives. Those two need
different machinery, and conflating them is how four different
`.markdownlint.jsonc` files came to be live at once.

## A pin is a copy, and a copy goes stale

Anti-drift above covers what the tooling copies. It does not cover what a
repository pins on purpose, and most of the arrows between these repos are exactly
that: the stack and the web surface reach `lemonfiber` as submodules at a revision,
`lemonfiber-web` reaches `lemonfiber` through a client it takes at a revision,
every repo reaches the docs site the same way, and every `uses:` in every workflow
names a SHA ([ADR-0009](../00-overview/decisions/0009-action-pinning.md)). An exact
revision is immutable, which is the point of it and also the failure: nothing about
a pin changes because the thing it names moved on.

Renovate was what was meant to notice. It was configured on every repo and opened
no pull request on any of them, so the true answer to "what is watching this pin"
was **nothing**, for every pin here, from the first one written until Dependabot
replaced it ([ADR-0016](../00-overview/decisions/0016-dependabot-over-renovate.md)).

Dependabot watches the `uses:` pins and the package manifests. It does not watch a
submodule revision — that stays with the `pins` notice each consuming repo runs —
and it does not watch a version written inline in a `run:` block, which is the gap
[above](#what-dependabot-does-not-watch).

Two things went wrong under that within a day of each other, and both passed every
gate:

- **The console was drawn through a client from before four of that client's own
  bugs were fixed**, so all four were live in it. A stale key read as "lemonfiber is
  not answering" — the client checked `401` and the binary answers `403`, so the page
  reported the server down and never asked for the one thing that would have fixed
  it. The event stream never handed over an arrival. A refusal's own sentence was
  discarded. The vendored contract predated a kind. Somebody building against the
  console found one of them again by hand, hours after it had been fixed upstream.
- **The same repository's lockfile named a client it was not built from.**
  `package-lock.json` sat behind `package.json`; `npm ci` installs what the lockfile
  names and the build then overwrites it, so the output was right and the record was
  wrong. That is the worse half. A wrong build fails somewhere eventually; a wrong
  record is what anybody reading the repository believes in the meantime.

Neither is a check behaving badly — both are the absence of one. A pin is not a
version any scanner ranks, and a lockfile disagreeing with the manifest beside it is
not a state the installer has any reason to object to.

So a pin is watched, and what a build resolved is held to what the repository
declared.

The watching fires on the dependency's own change rather than on a calendar. A
weekly sweep is a floor, not a first notice, and seven days is long enough for the
stale copy to be the one somebody installs. And the report names the commits not
taken rather than counting them: most commits on a client change nothing its
consumer reaches, so "behind by eleven" reads as an emergency where the list reads
as a decision.

`OPS-R48` already does this for one pin — when `spec`'s reusable workflows move, an
automated PR bumps the `@SHA` in every consumer in lockstep — and the hygiene gate's
`pins` job already reports, in each repo, what shared revision that repo is running.
Neither is peculiar to the release train or to shared CI. This is the general case
of both.

Three notifiers carry it between the repos that pin each other. `lemonfiber` tells
each SDK when the contract artefact it vendors has moved, and fails when an SDK
could not be told (`contract-moved.yml`). `sdk-ts` tells `lemonfiber-web` on every
push to its own main (`sdk-moved.yml`). `lemonfiber-web` compares the revision its
manifest pins against that main and names the commits it has not taken
(`sdk-drift.yml`). The first two are on their repositories' `main`; the third is not
yet merged, so the console's pin is watched by the notifier that fires at it before
it is watched by the check that answers.

The two that dispatch fail rather than report success when they cannot reach the
repository they are telling. A notifier that cannot notify, quietly, leaves the
calendar as the only thing looking — which is the state all three exist to end.

## What needs a human, once

These can't be scaffolded and must be set by hand after creation:

| Action | Where |
|--------|-------|
| Add `SONAR_TOKEN` secret | Each repo running Sonar → Settings → Secrets |
| Enable Dependabot **security updates** | Each repo → Settings → Advanced Security. Version updates need no toggle — `.github/dependabot.yml` is enough |
| Uninstall the Renovate GitHub App | Org → Settings → GitHub Apps. It is still installed and no longer read |

All are one-time and free. Everything else runs from committed config.

## Requirements

| ID | Requirement |
|----|-------------|
| **Q-R51** | Every tool in the pipeline MUST be free for public repositories or open source; no paid tier MAY be required. |
| **Q-R52** | Code quality and coverage MUST run through SonarQube Cloud, which ingests the `cargo-llvm-cov` report; the applicable-code coverage gate is enforced per Q-R61. |
| **Q-R53** | SAST (CodeQL), secret scanning (gitleaks), and dependency vulnerability scanning (OSV-Scanner) MUST run in CI. |
| **Q-R54** | Workflow lint (actionlint), spell check (typos), link check (lychee) and markdown lint MUST run in CI. |
| **Q-R55** | A dependency-update bot's pull requests MUST pass `spec-check` unattended; where the bot cannot emit the trailer, the gate MUST supply `GOV-R12` for it, keyed on the pull request's author and on nothing the pull request carries. |
| **Q-R56** | Shared CI MUST be reusable workflows sourced from the spec repo, not copied per repo. |
| **Q-R57** | Pre-commit hooks MUST mirror CI and MUST NOT enforce anything CI does not. |
| **Q-R58** | The docs site MUST render the specification from a pinned revision of `spec`, MUST link-check every page it publishes, authored and mirrored, and MUST be the only published rendering of the specification. |
| **Q-R59** | A public supply-chain posture check (OpenSSF Scorecard) MUST run on each repo's default branch. |
| **Q-R60** | Any tool requiring a secret or external app MUST be documented as a one-time manual setup step. |
| **Q-R68** | Where a repository depends on another repository in this org at an exact revision, an automated check MUST report a pin that is behind that dependency's default branch, naming the commits it has not taken. |
| **Q-R69** | A lockfile or equivalent record of what a build resolved MUST name the same revision as the declaration it resolves, and CI MUST fail where the two disagree. |

## Related

- [ci-cd.md](ci-cd.md) — the pipeline these tools compose
- [security.md](security.md) — the supply-chain and secret threats they address
- [50-governance/cross-repo-ci.md](../50-governance/cross-repo-ci.md) — reusable-workflow anti-drift
- [30-repos/README.md](../30-repos/README.md) — the `.github` repo
- [70-operations/staging.md](../70-operations/staging.md) — `OPS-R48`, the one pin the release train fans out itself
