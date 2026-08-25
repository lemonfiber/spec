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
| 3 | **Uninstall** the **Renovate** GitHub App from the org | GitHub → Org → Settings → GitHub Apps | It is installed, has never opened a pull request, and is no longer read ([ADR-0016](../00-overview/decisions/0016-dependabot-over-renovate.md)) |
| 4 | Create the org's **SonarQube Cloud** org, linked to GitHub | sonarcloud.io | Code quality + coverage |
| 5 | Add org secrets `DISCORD_ANNOUNCE_WEBHOOK`, `DISCORD_BUILD_WEBHOOK`, `DISCORD_MAINTAINERS_WEBHOOK` and org variable `DISCORD_RELEASE_ROLE_ID` (visibility: all) | GitHub → Org → Secrets/Variables → Actions | Release, build-log, and maintainer [notifications](notifications.md) |

### Per-repo (once each)

| # | Step | Repos | Needed for |
|---|------|-------|-----------|
| 6 | Branch protection: PR + signed commits + **strict** required checks (incl. SonarCloud), linear history, conversation-resolution, `enforce_admins` **on** | all | Governance is enforced, not advisory, and not exempt for the people who wrote it |
| 7 | Add `SONAR_TOKEN` secret | every repo with a Sonar job | The Sonar scan, and the `Q-R64` issue gate — which warns rather than fails where the secret is missing |
| 8 | Add a token that can push to `homebrew-tap` | `lemonfiber` | Release regenerates the formula, from `1.0.0` (`L1-R3`) |
| 9 | Add npm publish auth (`NPM_TOKEN`) | `brand` | Publishing `@lemonfiber/brand` |
| 10 | Enable **GitHub Pages** (source: Actions) | `spec` | The redirects that stand where the book stood |
| 11 | Enable **private vulnerability reporting** | all | Security disclosure path |
| 12 | Add `CNAME docs → lemonfiber.github.io` in Cloudflare DNS, proxied; enable **GitHub Pages** (source: Actions) with custom domain `docs.lemonfiber.app` | `website-docs.lemonfiber.app` | [docs.lemonfiber.app](https://docs.lemonfiber.app) resolves and serves |
| 13 | Turn on **Always Use HTTPS** and set the zone's SSL/TLS mode to **Full** | zone | `http://docs.lemonfiber.app` answers `301` to `https://`, and the hop to GitHub stays encrypted |
| 14 | Apply the **Bulk Redirect** list for the surfaces that moved to the documentation site — **outstanding**, see [the rules](#the-redirect-list-specifically) | zone | Every URL the marketing site published for a moved page answers `301` to its new address |

### The docs site's certificate, specifically

`docs.lemonfiber.app` is proxied by Cloudflare, like the apex, so Cloudflare
terminates TLS and GitHub's own certificate order does not complete. GitHub Pages
therefore reports `https_enforced: false` for that repository, and the setting
cannot be turned on while the record is proxied. HTTPS is served by Cloudflare's
edge certificate; the origin connection is governed by the zone's SSL/TLS mode,
which must be **Full** so the hop to GitHub stays encrypted.

Turning the proxy off would let GitHub issue and enforce its own certificate, at
the cost of moving that hostname off the redirect control plane the apex uses.

Step 13 is applied for that hostname and not for the whole zone.
`http://docs.lemonfiber.app` answers `301` at Cloudflare's edge, as the row
says it must; `http://lemonfiber.app` answers `200`, so the apex serves plain
HTTP. `.app` is HSTS-preloaded and a browser therefore never issues that
request, but a client that is not a browser does. Which of the two — a toggle
that is off with something narrower covering the docs hostname, or a toggle
that is on with something exempting the apex — is visible only from the zone.

### The redirect list, specifically

**Not applied.** Every URL this step covers answers `404` on the apex, so
`REPO-R53` is met by the `spec` repository's Pages site and by nothing else.
Nothing in any repository carries the rules, and nothing can: the apex is
GitHub Pages behind a Cloudflare proxy, so there is no `_redirects` file with a
host to read it and no origin able to serve a configured `301`. Whether the
list was never uploaded or was uploaded wrong is visible only from the zone,
which is why the rules are written out below rather than described.

A page that moves off `lemonfiber.app` leaves its URL behind, and that URL has
to keep resolving (`REPO-R53`). GitHub Pages serves no `301`, and the apex is
Cloudflare-proxied, so the redirects belong in a **Bulk Redirect list** on the
zone rather than in either repository — which also makes them survive a repo
rename.

Two shapes cover it.

**One subpath rule, path preserved.** Source `lemonfiber.app/spec`, target
`https://docs.lemonfiber.app/spec`, subpath matching on, path preserved. It
carries the 147 specification documents whose address is their old one with a
prefix swapped. A source without a trailing slash lands on a target without
one, and the documentation site answers that with its own `301` to the slashed
form, so those URLs resolve in two hops.

**One exact rule per retired page.** These are the marketing site's own pages,
and none of their new addresses is derivable from the old one:

| Source | Target |
|---|---|
| `lemonfiber.app/install` | `https://docs.lemonfiber.app/start/install/` |
| `lemonfiber.app/faq` | `https://docs.lemonfiber.app/spec/90-appendix/faq/` |
| `lemonfiber.app/colophon` | `https://docs.lemonfiber.app/spec/90-appendix/colophon/` |
| `lemonfiber.app/rfc` | `https://docs.lemonfiber.app/contributing/rfcs/` |
| `lemonfiber.app/roadmap` | `https://docs.lemonfiber.app/project/roadmap/` |
| `lemonfiber.app/changelog` | `https://docs.lemonfiber.app/project/changelog/` |
| `lemonfiber.app/nl/` | `https://lemonfiber.app/` |
| `lemonfiber.app/nl/install` | `https://docs.lemonfiber.app/start/install/` |
| `lemonfiber.app/nl/faq` | `https://docs.lemonfiber.app/spec/90-appendix/faq/` |
| `lemonfiber.app/nl/colophon` | `https://docs.lemonfiber.app/spec/90-appendix/colophon/` |
| `lemonfiber.app/nl/changelog` | `https://docs.lemonfiber.app/project/changelog/` |

The Dutch five are the retired locale (`/nl/…`), which published a rendering of
`90-appendix/faq` and `90-appendix/colophon` and so falls under `REPO-R53` too.
The locale was dropped rather than replaced, so each one goes to the English
page that stands where it stood.

**One exact rule per specification URL the subpath rule cannot carry.** Seventy-nine
of them, and all seventy-nine are derived from this repository's own tree: the
ten `…/README` directory indexes, whose target drops the `README` segment;
`10-functional/features/BOARD`, whose target is lowercase; and the sixty-eight
`/roadmap/<feature>` pages, whose target is the feature's path in
`10-functional/features/index.json`. Run this from the repository root to emit
them as the two-column CSV a Bulk Redirect list is uploaded from:

```sh
python3 - <<'PY'
import json, pathlib
DOCS = "https://docs.lemonfiber.app"
for section in sorted(p for p in pathlib.Path().glob("[0-9][0-9]-*") if p.is_dir()):
    for md in sorted(section.rglob("*.md")):
        route = md.with_suffix("").as_posix()
        if md.name == "README.md":
            print(f"https://lemonfiber.app/spec/{route},{DOCS}/spec/{md.parent.as_posix()}/")
        elif route != route.lower():
            print(f"https://lemonfiber.app/spec/{route},{DOCS}/spec/{route.lower()}/")
for f in json.loads(pathlib.Path("10-functional/features/index.json").read_text())["features"]:
    print(f"https://lemonfiber.app/roadmap/{f['id'].lower()},{DOCS}/spec/10-functional/features/{f['path'][:-3]}/")
PY
```

Reading the board rather than a written-out list is what keeps this honest: the
feature set grows, and a table of sixty-eight rows in this document would be
wrong the next time one is added.

`lemonfiber.github.io/spec/…` is not on this zone and cannot be covered here. It
is served by the `spec` repository's own Pages site, which publishes a page per
URL naming the new address as canonical. That half answers `200`.

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
(inherited from `.github`), the Dependabot config, the docs build, the
release pipeline. If a step isn't in the table above, it shouldn't need a human.

## Keeping this honest

Any new tool or workflow that needs a secret, an app, or a toggle **MUST** add a
row here in the same change ([Q-R60](../40-quality/tooling.md)). A setup step that
lives only in someone's memory is a setup step that gets lost.

A row is a step somebody has to take, not a claim that it was taken. Where a
step is known not to be in effect, its row says so and the section under it
carries what applying it needs, so the next person applies the step rather than
rediscovering it.

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
