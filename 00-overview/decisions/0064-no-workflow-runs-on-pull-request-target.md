# ADR-0064: No workflow runs on `pull_request_target`

**Status:** Accepted
**Date:** 2026-11-16
**Decided:** 2026-11-16, by the maintainer, Wessel Verheij: every workflow that ran on
`pull_request_target` is split into an unprivileged relay on `pull_request` and a privileged
follow-up on `workflow_run` from the default branch; no Actions event policy allows the old
trigger back. `pin-only`'s verdict is posted as a check run by this run's token by default, or
by the release App where a repository sets `check-source: app`, and spec posts its own by the
App.
**Amended:** 2026-11-17, by the maintainer, Wessel Verheij: the verdict is posted as a commit
status by this run's token, and as a check run only by the release App; where the App may not
write checks, it is posted as a status too.

## Context

GitHub blocks `pull_request_target` in public repositories from 2026-12-02 unless an
organisation's Actions event policy allows it, and ran brownouts before that. During the
brownout on 2026-11-16, 16:00 to 18:00 UTC, every `pull_request_target` run in the
organisation ended in `startup_failure`. `pin-only / pin-only`, which every repository
requires, could not report, so no pull request anywhere could merge.

Three workflows ran on that trigger. `pin-only` (`Q-R83`) judges whether a pull request
changes what its checks run; it needs the base branch's copy of itself, since a pull
request's own copy could be rewritten to pass. `awaiting-maintainer` (`OPS-R26`) took its
label off a closed pull request, which on a fork's pull request needs a token that can
write. `proposal-approve` (`GOV-R41` to `GOV-R43`) moves an approved proposal into the
specification with the release App.

## Decision

### 1. A relay and a follow-up

A workflow a pull request's event starts runs on `pull_request`, as the pull request's own
copy, with no token permissions and no secrets. Where something needs a token that writes
or a secret, a second workflow runs on `workflow_run` when that run completes. It runs
from the default branch, so the pull request cannot rewrite it; it checks out and runs
nothing of the pull request; and it trusts nothing the relay's run carries that the pull
request could have written: an artifact, a job's output or a run's name. What it reads is
what the forge sets on the run, the head commit and the repository and branch the head came
from, and the forge's own API. The open pull request is the one into this repository whose
head is that commit on that branch of that repository (`run_pull.py`). No artifact crosses
from the relay at all, which leaves nothing to validate.

A pull request that rewrites or removes its relay can only fail itself: a relay run that
never starts is a verdict never posted, and branch protection waits for it.

### 2. `pin-only`

Each repository's `pin-only.yml` is the relay, still named `pin-only`, run for `opened`,
`synchronize`, `reopened`, `labeled` and `unlabeled`; its one job, `pin-only`, runs one
step that does nothing. `pin-only-verdict.yml` runs on `workflow_run` for it and calls
spec's reusable `pin-only.yml`, which refuses any run other than the relay's on a pull
request, judges the head as before and posts `pin-only / pin-only` on it as a commit status.
The required check keeps its name, so branch protection is unchanged.

The verdict is a status because a check run this run's token posts is filed under the first
of GitHub Actions' check suites on the head, often the relay's first run on it. Once the
relay runs again on the same head, for a label or a reopen, the forge counts only that
workflow's newest suite, so the verdict filed in the older one is never counted and branch
protection waits for a check that already passed. A status belongs to no suite, and the newest
status of a name is the one counted. The release App posts a check run, `check-source: app`,
since an App's check runs share one suite on a head that nothing supersedes; where its
installation is not granted Checks: write, the verdict is posted as a status by this run's
token instead, and a key that mints no token fails the run.

A reusable job holds no permission its caller's job does not grant, so each caller grants
`statuses: write` where it granted `checks: write`, and the fan-out that moves a caller's pin
on `pin-only.yml` sets that job's permissions to exactly what the verdict's job asks for at
the tag, in the same commit.

The approval's head is read from the relay's runs, each stamped by the forge with its head
and time. A label event starts a relay run, which starts a verdict, so adding or removing
`workflows-approved` is judged again as before. The label, the seconds a head must be held
before a label approves it and the check's name are inputs, defaulting to today's values.

One verdict runs at a time for a branch and none is cancelled, so an older verdict is never
posted over a newer one. A newer verdict waiting replaces the one waiting before it, and each
reads the pull request as it is when it starts.

Dependabot's pull requests need nothing more. The relay needs no token, and a `workflow_run`
that Dependabot's run started gets the follow-up's own token.

### 3. Who posts the verdict

| `check-source` | Posted by | What it protects against |
|---|---|---|
| `actions`, the default | This run's token, as the GitHub Actions app | A pull request's own copy of `pin-only` rewritten to pass. It does not protect against a pull request that adds a `pull_request` job named so that it reports `pin-only / pin-only`, since both checks come from the same app. Branch protection needs no change. |
| `app` | The release App, from `RELEASE_APP_KEY` | That too, once branch protection takes `pin-only / pin-only` from the App alone: a fork's pull request gets no secrets and cannot post as the App. A writer's branch can still read the organisation's secret, as it can do anything else a writer can. |

Spec decides every other repository's checks, so its own verdict uses `app`. Any other
repository moves to `app` with one input once the App holds the Checks permission and its
branch protection names the App as the check's source.

### 4. `awaiting-maintainer`

The close event runs on `pull_request`. On a fork's pull request its token cannot edit
labels, so it says so. Each `workflow_run` evaluation then takes the label off any closed
pull request still carrying it. The flag is re-evaluated whenever a listed workflow
completes. A verdict flipped by a label alone waits for the next one, and a maintainer
adding that label is already on the pull request.

### 5. `proposal-approve`

It runs on `workflow_run` for spec's relay. The relay's run name says which label an event
added. The pull request could write that name, so it only decides whether a runner starts.
The approval itself is read from the forge:

- the label is on the pull request now;
- it was last added by an account with write access;
- the branch held the head being approved when the label was added, for as long as
  `pin-only` asks, read from the relay's runs;
- the run that started this was created at or after the label.

A push after the label is a head nobody approved. Only then is the App's token minted.

## Alternatives

- **An Actions event policy allowing `pull_request_target`.** One setting, and nothing else
  changes. Rejected: it keeps the most dangerous trigger GitHub has, and the next default
  change starts the outage over.
- **`pin-only` as the relay's own check.** No second workflow. Rejected: the pull
  request's own copy runs, so the check would be the pull request's to answer.
- **An artifact carrying the pull request's number.** It is common practice, but rejected:
  it is data the pull request writes. The forge already names the head, branch and
  repository, so the artifact would add nothing worth validating.
- **The verdict dispatching `awaiting-maintainer` after a label-only flip.** Rejected for
  now. It adds `actions: write` and a dispatch trigger to save a notification that a
  maintainer acting on the pull request does not need.

## Consequences

- Each pull request event takes two runners where it took one. The relay's run lasts
  seconds.
- The verdict is a commit status on the head, not a check run under the relay's run or the
  verdict's own; the release App's verdict is a check run in the App's suite.
- Every repository carries two pin-only files: the relay and the verdict caller. The
  shared-files check refuses any workflow `pull_request_target` starts, and any verdict
  caller without its concurrency block.

## Related

- [Q-R83, Q-R84](../../40-quality/ci-cd.md)
- [OPS-R26](../../70-operations/notifications.md)
- [GOV-R41](../../50-governance/rfc-process.md)
- [Cross-repo CI](../../50-governance/cross-repo-ci.md)
