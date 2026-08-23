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
| 6 | Branch protection: PR + signed commits + **strict** required checks (incl. SonarCloud), linear history, conversation-resolution, `enforce_admins` **on** | all | Governance is enforced, not advisory, and not exempt for the people who wrote it |
| 7 | Add `SONAR_TOKEN` secret | `lemonfiber` | Sonar scan |
| 8 | Add a token that can push to `homebrew-tap` | `lemonfiber` | Release regenerates the formula |
| 9 | Add npm publish auth (`NPM_TOKEN`) | `brand` | Publishing `@lemonfiber/brand` |
| 10 | Enable **GitHub Pages** (source: Actions) | `spec` | The redirects that stand where the book stood |
| 11 | Enable **private vulnerability reporting** | all | Security disclosure path |
| 12 | Add `CNAME docs → lemonfiber.github.io` in Cloudflare DNS, proxied; enable **GitHub Pages** (source: Actions) with custom domain `docs.lemonfiber.app` | `website-docs.lemonfiber.app` | [docs.lemonfiber.app](https://docs.lemonfiber.app) resolves and serves |
| 13 | Turn on **Always Use HTTPS** and set the zone's SSL/TLS mode to **Full** | zone | `http://docs.lemonfiber.app` answers `301` to `https://`, and the hop to GitHub stays encrypted |
| 14 | Apply the **Bulk Redirect** list for the surfaces that moved to the documentation site | zone | Every URL the marketing site published for a moved page answers `301` to its new address |

### The docs site's certificate, specifically

`docs.lemonfiber.app` is proxied by Cloudflare, like the apex, so Cloudflare
terminates TLS and GitHub's own certificate order does not complete. GitHub Pages
therefore reports `https_enforced: false` for that repository, and the setting
cannot be turned on while the record is proxied. HTTPS is served by Cloudflare's
edge certificate; the origin connection is governed by the zone's SSL/TLS mode,
which must be **Full** so the hop to GitHub stays encrypted.

Turning the proxy off would let GitHub issue and enforce its own certificate, at
the cost of moving that hostname off the redirect control plane the apex uses.

### The redirect list, specifically

A page that moves off `lemonfiber.app` leaves its URL behind, and that URL has
to keep resolving (`REPO-R53`). GitHub Pages serves no `301`, and the apex is
Cloudflare-proxied, so the redirects belong in a **Bulk Redirect list** on the
zone rather than in either repository — which also makes them survive a repo
rename.

Two shapes cover it:

- **One subpath rule with the path preserved** for `lemonfiber.app/spec`, which
  carries every document below it to `docs.lemonfiber.app/spec/…`.
- **One exact rule each** for a URL whose new address is not its old one with a
  prefix swapped: the ten `…/README` directory indexes, the sixty-eight
  `/roadmap/<feature>` pages, and `/install`, `/faq`, `/colophon` and `/rfc`.

`lemonfiber.github.io/spec/…` is not on this zone and cannot be covered here. It
is served by the `spec` repository's own Pages site, which publishes a page per
URL naming the new address as canonical.

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
