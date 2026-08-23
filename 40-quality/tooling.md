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
| **Dependency updates** | **Renovate** | free for OSS | all repos |
| **Pre-commit hooks** | **lefthook** | OSS | the repos with a `justfile`; the npm and Composer repos use `core.hooksPath .githooks` |
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

### Renovate over Dependabot — because of governance

Every dependency bump must cite `GOV-R12` ([canonical-spec](../50-governance/canonical-spec.md)).
Renovate's commit message and PR body are templatable, so its PRs **carry the
`Spec: GOV-R12` trailer automatically** and pass `spec-check` unattended.
Dependabot cannot customise the trailer, so its PRs would fail the gate until a
human intervened — friction the whole point of automation is to avoid.

A shared Renovate **preset** lives in the `.github` repo; each repo's
`renovate.json` extends it, so the policy has one home.

### lefthook, not pre-commit

A single Go binary, no Python runtime to install. It runs the fast checks —
`rustfmt`, `clippy`, `typos`, the comment-policy gate — before a push, so CI
rejects less and the loop is tighter. The hooks mirror CI exactly; nothing is
enforced locally that CI doesn't also enforce.

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
- **Renovate preset** in `.github` is extended, not copied.
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

## What needs a human, once

Two things can't be scaffolded and must be set in repo settings after creation:

| Action | Where |
|--------|-------|
| Add `SONAR_TOKEN` secret | Each repo running Sonar → Settings → Secrets |
| Enable the Renovate GitHub App | Org → install Renovate on the repos |

Both are one-time and free. Everything else runs from committed config.

## Requirements

| ID | Requirement |
|----|-------------|
| **Q-R51** | Every tool in the pipeline MUST be free for public repositories or open source; no paid tier MAY be required. |
| **Q-R52** | Code quality and coverage MUST run through SonarQube Cloud, which ingests the `cargo-llvm-cov` report; the applicable-code coverage gate is enforced per Q-R61. |
| **Q-R53** | SAST (CodeQL), secret scanning (gitleaks), and dependency vulnerability scanning (OSV-Scanner) MUST run in CI. |
| **Q-R54** | Workflow lint (actionlint), spell check (typos), link check (lychee) and markdown lint MUST run in CI. |
| **Q-R55** | Dependency-update automation MUST emit the `Spec: GOV-R12` trailer so its PRs pass `spec-check`. |
| **Q-R56** | Shared CI MUST be reusable workflows sourced from the spec repo, not copied per repo. |
| **Q-R57** | Pre-commit hooks MUST mirror CI and MUST NOT enforce anything CI does not. |
| **Q-R58** | The docs site MUST render the specification from a pinned revision of `spec`, MUST link-check every page it publishes, authored and mirrored, and MUST be the only published rendering of the specification. |
| **Q-R59** | A public supply-chain posture check (OpenSSF Scorecard) MUST run on each repo's default branch. |
| **Q-R60** | Any tool requiring a secret or external app MUST be documented as a one-time manual setup step. |

## Related

- [ci-cd.md](ci-cd.md) — the pipeline these tools compose
- [security.md](security.md) — the supply-chain and secret threats they address
- [50-governance/cross-repo-ci.md](../50-governance/cross-repo-ci.md) — reusable-workflow anti-drift
- [30-repos/README.md](../30-repos/README.md) — the `.github` repo
