# ADR-0016: Dependabot updates the dependencies, and the gate cites for it

**Status:** Proposed
**Date:** 2026-08-25

## Context

Every change in this org cites a spec identifier, and `spec-check` refuses one
that does not ([GOV-R2](../../50-governance/canonical-spec.md)). A dependency bump
is routine maintenance, so the identifier it cites is `GOV-R12`.

Renovate was chosen for exactly that reason: its commit body is templatable, so
the org preset set `commitBody: "Spec: GOV-R12\n\nSigned-off-by: …"` and its pull
requests passed both `spec-check` and `dco` unattended. `Q-R55` was written to
require it.

**It never ran.** The app is installed on the org, eleven repositories carry a
`renovate.json` extending the preset, and between them they have produced no pull
request, no branch and no dependency dashboard. The configuration was elaborate —
four regex custom managers, a docker-compose manager, four `packageRules` — and
none of it ever executed. `sdk-php`'s `renovate.json` extends
`local>lemonfiber/.github:renovate-config`, a preset file that does not exist,
and nothing reported it, because nothing read it.

Dependabot is native to GitHub. It needs a committed `.github/dependabot.yml` and
no app install, no token and no org-level grant — which removes the failure mode
that produced two years of silence.

Its one incompatibility is the reason Renovate was picked. **Dependabot composes
its own commit message and pull request body and offers no way to add a line to
either.** `commit-message` sets a prefix and a scope; there is no body, no
trailer, no template. So a Dependabot pull request cites nothing, and `spec-check`
refuses it — forever, on all eleven repositories.

`dco` does not have this problem: `dco_check.py` already exempts a commit whose
author is a bot, because GitHub authors such commits and there is no human to
attest.

## Decision

**Dependabot replaces Renovate, and `spec_check.py` supplies `GOV-R12` for the
pull requests Dependabot opens.**

The gate does not skip the check for the bot. It adds the citation the bot cannot
write and then runs the check unchanged, so `GOV-R3` — the cited identifier must
exist on `spec@main` — stays in force, and the run still prints what it accepted.

The exemption keys on `github.event.pull_request.user.login`, GitHub's own record
of who opened the pull request. Nothing the pull request carries is consulted: not
a label, not the title, not the branch name, not a commit's author, all of which
are writable by whoever opened it. Obtaining the citation therefore requires
opening a pull request as `dependabot[bot]`.

`Q-R55` moves with it: the requirement is that a dependency bot's pull requests
satisfy `spec-check` unattended, not that the bot emit the trailer itself.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Keep Renovate and make it run** | The preset is not the reason it is silent — the app is installed and produces nothing. Debugging a hosted app that has never emitted a log is open-ended, and the self-hosted fallback workflow needs an App token, a schedule and a runner to do what GitHub does natively for free. |
| **Exempt Dependabot from `spec-check` entirely** | Turns `GOV-R3` off for that path: a renamed governance namespace would stop failing these pull requests, and the run would print nothing about what it accepted. Supplying the citation costs one line and keeps the gate whole. |
| **Key the exemption on a label or the title** | Both are writable by whoever opens the pull request, so the gate would be off for anyone who can type. |
| **Have a workflow rewrite Dependabot's PR body to add the trailer** | A second bot editing the first bot's pull requests, needing `pull-requests: write` on eleven repositories, to write a constant the gate can supply itself. |
| **Accept the friction and edit each PR body by hand** | The friction automation exists to remove; and an unattended gate that needs a human is a gate people route around. |

## Consequences

### Positive

- Dependency updates start arriving. Nothing was being watched before.
- No app install, no org grant, no token, no runner. The config is committed, so a
  new repository is covered by copying a file.
- Dependabot commits through the GitHub API, so they are signed and satisfy the
  signed-commit branch protection — the thing the self-hosted Renovate workflow
  needed `RENOVATE_PLATFORM_COMMIT` to achieve.
- `dco` needs no change at all.

### Negative

- **Four things the preset watched by regex are no longer watched by anything.**
  Dependabot has no regex manager. See
  [40-quality/tooling.md](../../40-quality/tooling.md#what-dependabot-does-not-watch)
  for the list, what it costs, and what would have to change to bring each back
  under a manager Dependabot has.
- No lockfile-maintenance pass, no dependency dashboard, and no pinning of semver
  ranges to exact versions. Same section.
- Grouping is by name pattern rather than by update type, so a group is declared
  per ecosystem in each repo rather than once in a shared preset. There is no
  Dependabot equivalent of an org-level preset: the policy now lives in eleven
  copies of a file instead of one.

## Related

- [40-quality/tooling.md](../../40-quality/tooling.md) — the toolchain, and what stops being watched
- [ADR-0009](0009-action-pinning.md) — the pinning this bot now advances
- [50-governance/canonical-spec.md](../../50-governance/canonical-spec.md) — `GOV-R12`
- [70-operations/setup-registry.md](../../70-operations/setup-registry.md) — the app to uninstall
