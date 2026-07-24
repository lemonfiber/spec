# Setup registry

**Status:** Accepted

Every one-time manual step to operate the org, in one place. Most of the project
runs from committed config; a handful of things **can't** be scaffolded because
they need a secret, an app install, or a UI toggle. Those are all here.

If you're standing the org up (or handing it over), this is the checklist.

---

## Why a registry

These steps are otherwise scattered across [tooling](../40-quality/tooling.md),
[releasing](releasing.md), and [ci-cd](../40-quality/ci-cd.md) as footnotes. A
maintainer shouldn't have to reconstruct them from six documents — a public
project should be operable from one page.

## The checklist

### Per-org (once)

| # | Step | Where | Needed for |
|---|------|-------|-----------|
| 1 | Verify `info@nightworks.io` as an account email | GitHub → Settings → Emails | Signed-commit attribution shows *Verified* |
| 2 | Register the SSH **signing** key | GitHub → Settings → SSH keys → *signing* | Commit signatures verify |
| 3 | Install the **Renovate** GitHub App on the org | github.com/apps/renovate | Automated dependency PRs |
| 4 | Create the org's **SonarQube Cloud** org, linked to GitHub | sonarcloud.io | Code quality + coverage |
| 5 | Add org secrets `DISCORD_ANNOUNCE_WEBHOOK`, `DISCORD_BUILD_WEBHOOK`, `DISCORD_MAINTAINERS_WEBHOOK` and org variable `DISCORD_RELEASE_ROLE_ID` (visibility: all) | GitHub → Org → Secrets/Variables → Actions | Release, build-log, and maintainer [notifications](notifications.md) |

### Per-repo (once each)

| # | Step | Repos | Needed for |
|---|------|-------|-----------|
| 6 | Branch protection: PR required, signatures required, **required checks** | all | Governance is enforced, not advisory |
| 7 | Add `SONAR_TOKEN` secret | `lemonfiber` | Sonar scan |
| 8 | Add a token that can push to `homebrew-tap` | `lemonfiber` | Release regenerates the formula |
| 9 | Add npm publish auth (`NPM_TOKEN`) | `brand` | Publishing `@lemonfiber/brand` |
| 10 | Enable **GitHub Pages** (source: Actions) | `spec` | The docs site |
| 11 | Enable **private vulnerability reporting** | all | Security disclosure path |

### The required-checks step, specifically

Step 5's "required checks" can only be set **after the first PR runs**, because a
reusable-workflow check reports its context name (e.g. `ci / spec-check`) only
once it has run. The sequence:

1. Open any PR against the repo.
2. Let CI run; note the exact check names that report.
3. Add those as required status checks (strict) on `main`.

Until this is done, a PR that *fails* `spec-check` can still be merged — the rule
is documented but not binding. Doing it is what makes governance real
([GOV-R2](../50-governance/canonical-spec.md)).

## What is NOT manual

Everything else is committed config and runs on its own: the reusable CI
workflows, the label set (applied by script), the community health files
(inherited from `.github`), the Renovate policy preset, the docs build, the
release pipeline. If a step isn't in the table above, it shouldn't need a human.

## Keeping this honest

Any new tool or workflow that needs a secret, an app, or a toggle **MUST** add a
row here in the same change ([Q-R60](../40-quality/tooling.md)). A setup step that
lives only in someone's memory is a setup step that gets lost.

## Requirements

| ID | Requirement |
|----|-------------|
| **OPS-R7** | Every one-time manual setup step MUST be listed in this registry. |
| **OPS-R8** | A change introducing a step that needs a secret, app, or UI toggle MUST add its row here in the same change. |
| **OPS-R9** | Required status checks MUST be enabled on every repo's default branch once check names are known, so a failing `spec-check` blocks merge. |

## Related

- [releasing.md](releasing.md) — the release secrets (8, 9) in context
- [40-quality/tooling.md](../40-quality/tooling.md) — the tools these enable
- [50-governance/cross-repo-ci.md](../50-governance/cross-repo-ci.md) — what the required checks enforce
