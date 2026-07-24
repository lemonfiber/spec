# Overrides

**Status:** Accepted

The escape hatch, and why it is deliberately uncomfortable to use.

---

## Why this exists at all

An absolutely inviolable rule sounds stronger and is weaker.

Consider an embargoed security fix. Under a rule with no exceptions, the spec PR
announcing what is being patched must merge — publicly — before the fix can land.
That is backwards, and it is the kind of situation where a rule with no give gets
routed around entirely: someone pushes to `main`, or disables the check, or
merges from a fork. At that point the rule has failed *and* left no trace.

A visible, recorded override is stronger than an absolute rule that gets broken
in the dark.

## The mechanism

A maintainer applies the `spec-override` label and posts a justification comment.
The check passes; the PR merges.

Three things then happen automatically:

1. The override is appended to `50-governance/OVERRIDES.md` in this repo — date,
   repo, PR, maintainer, and the justification verbatim.
2. A tracking issue opens in the spec repo, linked to the PR.
3. The override appears in the next periodic report.

## The record

`OVERRIDES.md` is append-only and permanent:

| Date | Repo | PR | Maintainer | Justification |
|------|------|-----|-----------|---------------|
| 2026-08-14 | cli | #212 | @… | Embargoed advisory in a transitive dependency; spec follow-up in spec#88 |

The record is the entire point. An override that leaves no trace is
indistinguishable from the rule not existing.

## What makes an override legitimate

| Situation | Legitimate? |
|-----------|-------------|
| Embargoed security fix | **Yes** — public disclosure ahead of the patch is worse |
| The enforcement bot is broken | **Yes** — inability to verify shouldn't block all work |
| Production outage needing an immediate fix | **Yes**, with the spec corrected immediately after |
| Spec repo unreachable | **Yes** |
| "The spec PR is obvious and I don't want to wait" | **No** — that's the friction working as designed |
| "This is only a small change" | **No** — size isn't the criterion |
| Routine maintenance | **No** — cite `GOV-R12` instead |
| Deadline pressure | **No** — this is precisely when drift starts |

The pattern: an override is for when following the process would cause **harm**,
not when it would cause **delay**.

## The follow-up obligation

Every override opens a tracking issue, and it stays open until the spec reflects
what was merged.

An override defers the spec change. It does not cancel it. A merged override with
no follow-up is the drift the rule exists to prevent, arrived at by a more
honest route.

## Watching the rate

Overrides are counted. A periodic report lists them, and if the rate exceeds a
threshold it opens an issue on this repo asking the obvious question: **is the
rule wrong?**

A rule requiring frequent bypass is badly designed, not virtuously strict. High
override volume is evidence, and the documented remedy is to reconsider the rule —
most likely by adding standing `GOV-R` requirements covering the change classes
that keep needing an override.

Reaching for the override repeatedly rather than fixing the rule is the failure
mode this monitoring exists to surface.

## Who may override

Maintainers with merge rights on the affected repository. There is no
self-service override for contributors — otherwise it is not an override, it is
an opt-out.

A maintainer overriding their own PR is permitted but recorded as such, since
that is the case most worth being able to see.

## Requirements

| ID | Requirement |
|----|-------------|
| **GOV-R13** | An override MUST require a written justification before it takes effect. |
| **GOV-R14** | Every override MUST be recorded permanently, with date, repo, PR, maintainer and justification. |
| **GOV-R15** | Every override MUST open a spec tracking issue that remains open until the spec reflects the merged change. |
| **GOV-R16** | Overrides MUST be applied only by maintainers with merge rights on the affected repository. |
| **GOV-R17** | An override applied by the PR's own author MUST be recorded as such. |
| **GOV-R18** | Override frequency MUST be reported periodically, and exceeding a threshold MUST raise the question of whether the rule needs changing. |
| **GOV-R19** | The override MUST NOT be usable to bypass code review, tests, or any check other than the spec-citation checks. |

**GOV-R19** matters: this override exists for **one** rule. It is not a
general-purpose merge button, and a broken build is not something it can excuse.

## Related

- [canonical-spec.md](canonical-spec.md) — the rule being overridden
- [cross-repo-ci.md](cross-repo-ci.md) — what the override bypasses
- [change-lifecycle.md](change-lifecycle.md) — the normal path
