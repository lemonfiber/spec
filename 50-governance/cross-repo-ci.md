# Cross-repo CI

**Status:** Accepted

The mechanical enforcement of [GOV-R2 through GOV-R5](canonical-spec.md#the-gov-r-namespace).

---

## What runs, and where

A check runs on every pull request in every repository the org governs, and on
every merge group where one merges through a queue — see [In a merge
queue](#in-a-merge-queue). The reusable workflow is called from each repo's
`ci.yml`, so a repository added later inherits it by wiring three lines rather
than by being added to a list here.
It reads the PR's commits and body, extracts citations, and resolves them against
this repository.

```mermaid
sequenceDiagram
    participant PR as PR in lemonfiber
    participant Bot as spec-check
    participant Spec as spec@main

    PR->>Bot: opened / synchronized
    Bot->>Bot: extract Spec: trailers + PR body
    alt no citation found
        Bot->>PR: close with guidance
    else citation found
        Bot->>Spec: resolve IDs at merge-base
        alt any ID unknown or withdrawn
            Bot->>PR: fail, naming the bad ID
        else all resolve
            Bot->>PR: pass
        end
    end
```

## The checks

| # | Check | Failure |
|---|-------|---------|
| 1 | At least one citation present in a commit trailer **or** the PR body | Fail |
| 2 | Every cited ID is well-formed | Fail, naming the malformed ID |
| 3 | Every cited ID **exists** in `spec@main` at the merge-base | Fail, naming the unknown ID |
| 4 | No cited requirement is `Draft` or `Withdrawn` | Fail, naming it and its status |
| 5 | Spec change merged before this PR, where behaviour changed | Fail, with the ordering explained |
| 6 | Every ID the change **writes into a file** exists in `spec@main` | Fail, naming the unknown ID |

Check 3 is what distinguishes this from a regex looking for a plausible string.
Check 5 is what makes the spec structurally incapable of falling behind.
Check 6 is what closes the gap between the two places a citation is made.

### The citation nobody declared

Checks 1 to 5 read the pull request's body and its commit messages. An identifier
written into a file — the sentence a refusal prints telling somebody what to go
and read, a page under a repository's own requirements directory, a rule's own
title — is a citation in every sense that matters to the person who follows it,
and was resolved against nothing at all. A digit slipped there names a
requirement that does not exist, on a line whose whole job is to send a reader to
one.

Check 6 reads the lines a change **adds** and nothing else. A file's existing text
is not this change's to answer for, and a gate that refused a pull request over a
line somebody wrote two years ago is a gate that gets switched off rather than
fixed.

It resolves only families the spec defines, and that is where the rule stops
rather than where it was convenient to stop. A placeholder such as `X-R…` in a
doc comment means *any requirement of any family*, and a family the spec has
never heard of is
prose about requirements rather than a citation of one. What that costs is worth
stating plainly: a slip in the family rather than the number — an `M1` where an
`N1` was meant — reads as prose here and is passed over. The number is where
the slips are, and a rule that refused every capital-letter-and-digit token would
refuse the writing that explains the rules.

Retirement is not asked of a file, for the same reason. A comment recording that a
number was withdrawn has to name it, and nothing here can tell that sentence from
a citation. The trailer is where a citation is *made*, and that is where
**GOV-R8** and **GOV-R47** are enforced.

It does not read its own tests. `scripts/test_spec_check.py` exists to name
identifiers that do not resolve — that is what a test of *refuse an unknown
identifier* is — and reading it would have the gate refuse the change that
teaches it to refuse. The exemption is two paths and deliberately not a pattern:
a test's own title is exactly the kind of citation check 6 exists to resolve, so
`tests/` anywhere would be a hole wide enough to walk a repository through.

## Surfacing what a PR cites

Enforcement is only half the loop. Alongside `spec-check`, a **spec-references**
comment is posted on each PR: it resolves every cited identifier to its defining
file and lists them as links, with the requirement text, updating the *same*
sticky comment on each push rather than adding new ones. Where `spec-check` fails a
*missing* citation, this puts a *present* one one click from its source — for the
author and the reviewer both. It reads only PR metadata and the spec repo, never
the PR's code, so it is safe on any PR.

| ID | Requirement |
|----|-------------|
| **GOV-R32** | Each PR MUST receive an automated, self-updating comment that links every cited spec identifier to its defining file; it MUST NOT execute untrusted PR code. |

## Explaining the non-standard checks

Some checks here surprise a first-time contributor: the citation gate *closes* a
PR, the DCO check *skips* merge and bot commits, the Sonar gate reads a summary
comment rather than a status. A rule that reads as arbitrary reads as hostile —
so a check likely to confuse posts a self-updating explainer comment saying what
it does and how to satisfy it, through the one shared `explain-check` reusable so
the wording lives in one place. The explainer is the courtesy that turns a closed
PR from a rejection into a sequenced next step.

| ID | Requirement |
|----|-------------|
| **GOV-R33** | A non-standard or PR-closing check MUST post a self-updating explainer comment describing what it does and how to satisfy it, via the shared reusable, **only when the contributor has not already satisfied the check** — and MUST remove the explainer once they do; it MUST NOT execute untrusted PR code. |

## The citation format

A `Spec:` trailer on at least one commit:

```
feat: health-gate service startup

Wait for health rather than process start before reporting a service
as running.

Spec: B2-R1, B2-R2
```

And in the PR body — the same IDs, so a reviewer sees them without reading
commits. The bot requires both because they serve different readers: the trailer
is permanent provenance in `git log`, the body is context for review.

## Determining whether behaviour changed

Check 5 only applies to behavioural change, so the bot needs to tell the
difference. It uses the citation itself:

| Cited | Interpretation |
|-------|----------------|
| Only `GOV-R` identifiers | Routine maintenance — ordering check skipped |
| Any requirement or ADR | Behavioural — ordering check applies |

If a requirement is cited and that requirement was added to the spec **after**
this PR's merge-base, the ordering was violated: the contributor wrote the spec
change and the implementation together, and merged them out of order.

The remedy is simply to rebase once the spec PR has landed.

## What "close" means

**GOV-R9**: non-conforming PRs are closed, not left failing.

A red check that sits indefinitely is worse for everyone — the contributor
doesn't know whether to wait, and maintainers accumulate a queue of PRs that can
never merge. Closing is a clear signal with a clear remedy, and reopening costs
one click.

The closing comment is covered in [contributing.md](contributing.md#when-your-pr-is-closed);
in short: thank them, state the rule and why, link the spec, give copy-pasteable
steps, and say explicitly that the work isn't rejected — it's sequenced.

## In a merge queue

A repository whose default branch merges through a **merge queue** runs its
checks twice: once on the pull request, and once on the queue's own branch — the
base branch's tip with every queued pull request applied — under the
`merge_group` event. Every context the branch requires has to report on that
event. One that does not is not read as a failure; it is read as a wait, and the
queue drops the pull request when the status-check timeout expires, naming
nothing.

Two things about that are worth writing down, because both were found the
expensive way.

**A skipped job reports success; a skipped *caller* reports nothing at all.**
The context a reusable workflow produces is `caller / callee`, and the callee
exists only if the caller ran. So `if: github.event_name == 'pull_request'` on
the caller does not leave a skipped tick on a merge group — it leaves no tick,
which is exactly the state a queue waits on. A caller of a required reusable
therefore runs on `merge_group` and lets the workflow inside decide what it can
answer.

**This gate asks less of a merge group, and says so.** That event carries no
pull request: no body, and no author. **GOV-R2** allows a citation to live in
the body and **Q-R55**'s Dependabot allowance keys on the author, so requiring a
trailer of the commits alone would refuse a batch for citing exactly where the
rule permits it, and would refuse every dependency update outright. So presence
is not re-asked there — it was asked of each pull request before the queue
accepted it, and a merge group does not rewrite a commit message. **GOV-R3 is**
re-asked: every identifier the batch cites is resolved against `spec@main` as it
stands now, which is the one answer that can change while a pull request waits
in a queue. The run states which half it asked rather than leaving a bare tick.

Nothing is closed on a merge group. A batch that reaches a refusal there is the
queue's rather than any one author's, and closing one of the pull requests in it
would pick a victim out of a batch. The batch is rejected, the pull requests stay
open, and their authors are told why.

## Spec-side checks

This repository runs its own checks, since **GOV-R11** subjects governance to
itself:

| Check | Purpose |
|-------|---------|
| Every cited ID resolves | No dangling internal references |
| No duplicate requirement IDs | IDs are unique and permanent (**GOV-R8**) |
| No reused withdrawn ID | Retired numbers stay retired |
| Requirement-altering PRs name affected repos | **GOV-R7** |
| Every link resolves | Same class of rot |

## Failure modes of the bot itself

Enforcement machinery that fails badly is worse than none, because it fails
*silently* and everyone assumes it's working.

| Situation | Behaviour |
|-----------|-----------|
| Spec repo unreachable | **Fail the check, do not close.** Inability to verify is not evidence of violation. |
| Bot errors unexpectedly | Report as a bot error, never as a contributor violation. |
| Rate-limited | Retry with backoff; report as unverified rather than failing. |
| PR from a fork | Same rules. Citations are public information. |
| Bot is down entirely | Merging is blocked. Use the [override](overrides.md) — that is a legitimate use. |
| Citation valid, spec changed since | Resolve at merge-base, not at HEAD. Later spec edits must not retroactively invalidate a merged PR. |
| Very large PR touching many areas | One valid citation suffices. The bot counts references, not coverage. |
| Required check absent on `merge_group` | The queue waits and then drops the pull request. A caller that skips there reports nothing at all, rather than reporting a skip — see [In a merge queue](#in-a-merge-queue). |

The last row is deliberate: requiring a citation *per file* would produce
box-ticking, and box-ticking is how a rule stops meaning anything.

## Related

- [canonical-spec.md](canonical-spec.md) · [change-lifecycle.md](change-lifecycle.md)
- [contributing.md](contributing.md) — the contributor's view
- [overrides.md](overrides.md) — including when the bot itself is broken
- [issue-routing.md](issue-routing.md)
