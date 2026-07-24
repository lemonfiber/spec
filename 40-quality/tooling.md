# Tooling

**Status:** Accepted

The external tools the project relies on. Every one is **free for public
repositories** or fully open source — no paid, team, or enterprise tier is
required, because none is available to an open project on a free org.

**Satisfies:** [ci-cd](ci-cd.md), [security](security.md),
[roadmap M6](../00-overview/roadmap.md#m6--release-engineering).

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
| **Code quality + coverage** | **SonarQube Cloud** | free for public | cli |
| **SAST** | **CodeQL** | free for public | cli |
| **Secret scanning** | **gitleaks** | OSS | all repos |
| **Dependency/vuln scanning** | **OSV-Scanner** | OSS | cli, brand, media-stack |
| **Supply-chain posture** | **OpenSSF Scorecard** | free for public | all repos |
| **Rust licences + advisories** | **cargo-deny** | OSS | cli |
| **Coverage generation** | **cargo-llvm-cov** | OSS | cli → Sonar |
| **Workflow lint** | **actionlint** | OSS | all repos |
| **Spell check** | **typos** | OSS | all repos |
| **Link check** | **lychee** | OSS | all repos |
| **Markdown lint** | **markdownlint** | OSS | all repos |
| **Dependency updates** | **Renovate** | free for OSS | all repos |
| **Pre-commit hooks** | **lefthook** | OSS | all repos |
| **Task runner** | **just** | OSS | all repos |
| **Changelog** | **git-cliff** | OSS | cli, brand, media-stack |
| **Release binaries** | **cargo-dist** | OSS | cli |
| **Docs site** | **mdBook** | OSS | spec |
| **Web lint + format** | **Biome** | OSS | cli (web-ui) |
| **Web accessibility** | **axe-core / pa11y** | OSS | cli (web-ui) |

## Why these, specifically

### SonarQube Cloud carries quality *and* coverage

Free for public repos, native GitHub Action, analyses Rust. It ingests the lcov
`cargo-llvm-cov` produces, so coverage lives there too — no separate Codecov.
Consistent with [Q-R28](testing-strategy.md), coverage is **reported, never a
merge gate**; Sonar's quality gate is configured to not fail on coverage
percentage.

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

### mdBook — the docs site from the spec

[Roadmap M6](../00-overview/roadmap.md#m6--release-engineering) calls for a docs
site generated from this spec. mdBook (Rust, OSS) renders the Markdown to a static
site, deployed to GitHub Pages — free for public repos. `lychee` link-checks it,
so the published site never ships a broken link.

### git-cliff — changelog from history

Because commits carry structured trailers (`Spec:`) and follow a consistent shape,
a changelog can be generated rather than hand-maintained. git-cliff (Rust, OSS)
does this at release time alongside `cargo-dist`.

### Biome — one web tool, not two

When the web UI arrives (M5), Biome (Rust, OSS) lints *and* formats JS/TS/CSS in
one fast tool, replacing ESLint + Prettier. It matches the project's "one
formatter, no arguments" posture ([code-standards](code-standards.md)). Paired
with axe-core / pa11y for the accessibility testing the
[contrast contract](../60-brand/accessibility.md) and
[G3](../10-functional/features/g-ux/g3-accessibility.md) require.

## Anti-drift

The tooling is kept consistent across repos by construction, not vigilance:

- **Reusable workflows** in the spec repo (`hygiene`, `security`, `spec-check`)
  are called by three-line wrappers in each repo. One definition each.
- **Renovate preset** in `.github` is extended, not copied.
- **`.github` repo** supplies community files org-wide.
- **lefthook and just** configs are small and per-repo, but mirror the reusable
  CI so they cannot demand something CI doesn't.

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
| **Q-R52** | Code quality and coverage MUST run through SonarQube Cloud; coverage MUST NOT be a merge gate. |
| **Q-R53** | SAST (CodeQL), secret scanning (gitleaks), and dependency vulnerability scanning (OSV-Scanner) MUST run in CI. |
| **Q-R54** | Workflow lint (actionlint), spell check (typos), link check (lychee) and markdown lint MUST run in CI. |
| **Q-R55** | Dependency-update automation MUST emit the `Spec: GOV-R12` trailer so its PRs pass `spec-check`. |
| **Q-R56** | Shared CI MUST be reusable workflows sourced from the spec repo, not copied per repo. |
| **Q-R57** | Pre-commit hooks MUST mirror CI and MUST NOT enforce anything CI does not. |
| **Q-R58** | The docs site MUST be generated from the spec and link-checked before publish. |
| **Q-R59** | A public supply-chain posture check (OpenSSF Scorecard) MUST run on each repo's default branch. |
| **Q-R60** | Any tool requiring a secret or external app MUST be documented as a one-time manual setup step. |

## Related

- [ci-cd.md](ci-cd.md) — the pipeline these tools compose
- [security.md](security.md) — the supply-chain and secret threats they address
- [50-governance/cross-repo-ci.md](../50-governance/cross-repo-ci.md) — reusable-workflow anti-drift
- [30-repos/README.md](../30-repos/README.md) — the `.github` repo
