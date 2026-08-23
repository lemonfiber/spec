# Notifications & maintainer automation

**Status:** Accepted

How the project talks to two audiences without anyone doing it by hand: the
**public** (releases and build activity, in the community server) and the
**maintainers** (the queue of things that need a human decision).

Everything here runs on Discord **incoming webhooks** — no bot to host — and every
integration is **dormant until its webhook secret exists**, so a fork or a fresh
clone never fails for lacking one.

---

## The three channels

| Channel | Audience | Posts | Secret |
|---------|----------|-------|--------|
| `#releases` | public | A published release, with notes and install line | `DISCORD_ANNOUNCE_WEBHOOK` |
| `#build-log` | public | Every workflow run, on completion (pass/fail) | `DISCORD_BUILD_WEBHOOK` |
| `#awaiting-maintainer-action` | maintainers (private) | Items needing a decision: triage, review, main-branch breakage | `DISCORD_MAINTAINERS_WEBHOOK` |

Release pings an **opt-in role** rather than `@everyone`: if the org variable
`DISCORD_RELEASE_ROLE_ID` is set, the announcement mentions it; otherwise it posts
silently. People who want release notifications self-assign the role.

`#releases` is a **Forum** channel, so each release is its own thread — the
announcement opens it (role ping and link on that first post), and a long
changelog continues as replies inside the same thread rather than flooding the
channel. That also makes each release a place to discuss it. `#build-log` and
`#awaiting-maintainer-action` stay plain text channels; they pass no thread name
and post normally.

## The public address

The channels above are how the project talks outward. The way *in* is a single
address — <https://discord.nightworks.io> — a redirect NightWorks controls, and
the only form any published link takes.

An invite code is not a stable identifier. It can expire, be revoked, or be
regenerated, and when it is, every link carrying it dies at once: in READMEs, in
forks, in release notes already published, in repository metadata nobody thinks
to re-check. The code itself is fine. Publishing it is what makes it fragile.

The redirect moves that fragility somewhere it can be repaired. The invite code
then exists in exactly one place — whatever the redirect resolves to — and
replacing it is one edit rather than a sweep of every repository. This has
already failed once here: five repositories carried a `homepageUrl` pointing at a
superseded invite long after the documented link had moved on, because metadata
is not where anyone looks when they update a link.

A link checker cannot catch this. Discord answers *any* invite path with 200,
including codes that never existed, so a dead invite is indistinguishable from a
live one over HTTP. The check is therefore on the text rather than the response:
the shared `hygiene` workflow refuses a tracked file containing an invite code.

## Secrets, safety, and forks

The webhook URLs are org-level secrets (`--visibility all`). Two rules keep them
safe, both checkable:

1. **No secret reaches fork-PR code.** Notifiers trigger on `workflow_run` or on
   base-repo events (`issues`, `pull_request_review`, `push`, release) — never on
   `pull_request` from a fork, where a contributor's code could read the secret.
2. **No injection.** Every dynamic value (issue title, branch, commit message)
   is passed through `env:` into `jq --arg`, never interpolated into a shell line.

Both live in the single reusable `discord-notify.yml`, so there is one place to
audit, not one per repo.

## The maintainer queue

Two labels encode "a maintainer needs to act", applied by automation so the queue
is a saved search, not a memory game:

| Label | Applied when | Removed when |
|-------|-------------|--------------|
| `needs-triage` | An issue is opened or reopened | A maintainer triages it (by hand) |
| `awaiting-maintainer` | A PR passes CI and has no approving review | The PR is reviewed, or the PR closes |

`awaiting-maintainer` skips PRs opened **by a maintainer** — a maintainer's own PR
is not awaiting one. As non-maintainers begin contributing, their green PRs surface
automatically. The live queue is
`is:open label:needs-triage,awaiting-maintainer`.

A closed pull request is not awaiting a maintainer, and neither is a merged one.
Because the queue is scoped to `is:open`, a flag left behind does not distort the
queue itself — it survives on the closed PR permanently instead, so any
label-filtered history reads as though that work shipped unreviewed, and
reopening restores a flag that no longer describes the PR's state. The label
therefore clears on closure as well as on review, merged or not.

## Assignment

Assignment reads the [maintainers registry](maintainers.md) — no second source:

- **Issues** are assigned, on open, to the maintainer(s) whose scope covers the
  repo, read from the generated `.github/CODEOWNERS` (itself generated from
  `maintainers.toml`).
- **PRs** already request review from the owning maintainer by changed path, via
  CODEOWNERS — GitHub-native, no workflow.

So maintainership is edited in exactly one place ([maintainers.toml](maintainers.toml)),
and both review-routing and issue-assignment follow it.

## Requirements

| ID | Requirement |
|----|-------------|
| **OPS-R23** | A published release MUST announce to the public announcement channel, mentioning the opt-in role when `DISCORD_RELEASE_ROLE_ID` is set and never `@everyone`. |
| **OPS-R24** | Every workflow run MUST post its completion status (pass/fail) to the public build-log channel. |
| **OPS-R25** | A newly opened issue MUST be labelled `needs-triage` and assigned the covering maintainer from the generated CODEOWNERS. |
| **OPS-R26** | A PR that passes CI without an approving review MUST be labelled `awaiting-maintainer`, unless its author is a maintainer; the label MUST be removed once the PR is reviewed or closed. |
| **OPS-R27** | Items needing maintainer action MUST post to the private maintainer channel when its webhook is configured. |
| **OPS-R28** | Every Discord integration MUST be gated on its webhook secret's presence, MUST NOT run in fork-PR context with the secret available, and MUST pass all event-derived text through the environment rather than a shell interpolation. |
| **OPS-R53** | A notification body over Discord's embed limit MUST be split at line boundaries rather than truncated; where the channel is a Forum, the overflow MUST post as replies within one thread and the role ping MUST ride only the opening message. |
| **OPS-R56** | Every published reference to the community server — documentation, repository metadata, site data, and issue-template contact links — MUST address it as `https://discord.nightworks.io`, and MUST NOT publish an invite code. CI MUST reject a tracked file containing one. |

## Related

- [maintainers.md](maintainers.md) — the registry these read from
- [project-workflow.md](project-workflow.md) — the canonical label set and branching model
- [releasing.md](releasing.md) — where the release announcement is triggered
- [50-governance/cross-repo-ci.md](../50-governance/cross-repo-ci.md) — the reusable-workflow model
- [40-quality/security.md](../40-quality/security.md) — the no-secret-in-fork-PR rule
