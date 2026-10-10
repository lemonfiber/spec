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

Retirement and drafts are not asked of a file, for the same reason. A comment
recording that a number was withdrawn, or that a behaviour waits on a draft, has
to name it, and nothing here can tell that sentence from a citation. The trailer
is where a citation is *made*, and that is where **GOV-R8**, **GOV-R47** and
**GOV-R48** are enforced.

It does not read its own tests. `scripts/test_spec_check.py` exists to name
identifiers that do not resolve — that is what a test of *refuse an unknown
identifier* is — and reading it would have the gate refuse the change that
teaches it to refuse. The exemption is two paths and deliberately not a pattern:
a test's own title is exactly the kind of citation check 6 exists to resolve, so
`tests/` anywhere would be a hole wide enough to walk a repository through.

A repository may declare the same thing about its own fixtures, in
`.github/spec-check-fixtures` — one path per line, `#` for a comment. This gate
is not the only code with a test that must name an identifier nothing answers
to: the Rust stack renders a withdrawn requirement and asserts the
strikethrough, and refuses an id past the ceiling by asking for one. Without an
answer for those, check 6 refuses the next change that touches such a line and
the only way to satisfy it is to write the fixture out of a real requirement
number — which ties that repository's tests to whatever the spec holds this
week, and is the gate making the code worse.

Three things keep the declaration from becoming a way out:

- **Exact paths, never a pattern.** A glob is refused, for the reason above.
- **A path that is not there is refused**, naming the line to delete. A
  declaration outlives the file it was written for, and a list carrying an entry
  that stopped applying is one nobody trusts enough to shorten.
- **Every skipped path is printed** on every run. An exemption nobody sees is an
  exemption nobody revisits, and a gate reporting clean over files it never
  opened reads exactly like one that read them.

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

The first two of those run in **every** repository in the organisation, so the
explanation is called from every repository too, the way the gates themselves are:

```yaml
  explain:
    permissions:
      contents: read
      pull-requests: write
    uses: lemonfiber/spec/.github/workflows/explain.yml@<sha> # main
```

`explain.yml` is the caller that knows about those two; `explain-check.yml` is the
primitive under it, and a repository with a surprising check of its own calls that
one directly with its own wording. Neither is copied: an explanation in fifteen
places is fifteen wordings the day one of them is improved.

`explain.yml` also posts the advice `scripts/assist.py` gives, each piece under
the same rule of appearing only while it is true:

- **The citation that fits.** A first-time contributor's pull request with no
  `Spec:` line is told `GOV-R40` where it adds a proposal and, where it changes
  prose only, `GOV-R12` for a fix to wording, inside the citation explainer.
- **Where a mirrored page lives.** A first-time contributor editing a page a site
  renders from another repository, as the site's `mirrors.json` names it, is told
  the repository and the file to edit instead.
- **The tracker.** A pull request that cites a version's goals in a repository a
  version is satisfied in, and leaves its `status.toml` or `status/` as it was,
  is shown each cited goal's state there, so the row moves in the same pull
  request (`OPS-R74`).

| ID | Requirement |
|----|-------------|
| **GOV-R33** | A non-standard or PR-closing check MUST post a self-updating explainer comment describing what it does and how to satisfy it, via the shared reusable, **only when the contributor has not already satisfied the check** — and MUST remove the explainer once they do; it MUST NOT execute untrusted PR code, and it MUST find its explainer by the comment's author, the account the workflow writes as, as well as by its marker, never editing or removing a comment anybody else wrote. |

## The citation format

A `Spec:` trailer on at least one commit:

```
feat: health-gate service startup

Wait for health rather than process start before reporting a service
as running.

Spec: B2-R1, B2-R2
```

And in the PR body, the same IDs on a `Spec:` line of their own. A squash
merge in every repository takes the pull request's title and body as the commit
message, so the body is what `main` keeps: its `Spec:` line is the permanent
provenance in `git log`, and the one the release gate reads to decide that a goal
landed. The trailer on the branch's commits is what the hooks check before a pull
request exists. `spec-check` passes on a citation in either place, and
`squash-message` holds the body to it (below).

## The squash message

A squash merge writes one commit to `main`: the pull request's title as its
subject and the pull request's body as its message. GitHub then appends the
merger's sign-off, because the organisation requires a sign-off on every commit
made through the web. The branch's commit messages do not reach `main`. A body that leaves out the citation lands a commit the release gate
cannot count, and a merged commit cannot gain a trailer afterwards.

`squash-message` asks of the title and body what `main` will hold:

| # | Check | Failure |
|---|-------|---------|
| 1 | The title is a conventional subject, as `OPS-R21` holds a commit's | Fail, naming the title |
| 2 | The body carries a `Spec:` line, and every identifier on it resolves on `spec@main` | Fail, with the line to add or the identifier that does not resolve |
| 3 | The body carries a `Signed-off-by` for each human author of the pull request's commits | Fail, with the line to add for each |

A pull request a bot opened is exempt: nobody stands behind it to sign it off,
which is why `dco` exempts a bot's commits. The check reads the pull request's
title, body and commit authors and the specification, never the pull request's
code. It runs on each edit of the pull request as well as on each push, in a
workflow of its own, so fixing the body re-runs this one job rather than the
repository's CI.

| ID | Requirement |
|----|-------------|
| **GOV-R62** | A `squash-message` check MUST run on every pull request, on each edit of its title or body as well as each push, and MUST fail unless the title is a conventional subject, the body carries a `Spec:` line whose identifiers resolve on the specification's default branch, and the body carries a `Signed-off-by` line for each human author of its commits; a pull request a bot opened is exempt, and the check MUST NOT execute untrusted pull-request code. |

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

**GOV-R56**: the one click is made for them when the citation starts to resolve. A
pull request closed for citing an identifier the specification did not yet define is
waiting on that definition, not refused. When a push to the specification's `main`
defines it, the pull request is reopened with a comment saying the citation now
resolves, and `spec-check` runs again on the reopen. `reopen-on-spec-merge` does
this on every push to `main` that changes a page: it reopens a closed, unmerged pull
request only where every identifier its newest closing comment named now resolves,
and only where nobody has closed it since.

| ID | Requirement |
|----|-------------|
| **GOV-R56** | When the specification defines an identifier, a pull request that `spec-check` closed for citing it MUST be reopened automatically, with a comment saying the citation now resolves. |

## In a merge queue

A repository whose default branch merges through a **merge queue** runs its
checks twice: once on the pull request, and once on the queue's own branch — the
base branch's tip with every queued pull request applied — under the
`merge_group` event. Every context the branch requires has to report on that
event. One that does not is not read as a failure; it is read as a wait, and the
queue drops the pull request when the status-check timeout expires, naming
nothing.

Three things about that are worth writing down, because each was found the
expensive way.

**A skipped job reports success; a skipped *caller* reports nothing at all.**
The context a reusable workflow produces is `caller / callee`, and the callee
exists only if the caller ran. So `if: github.event_name == 'pull_request'` on
the caller does not leave a skipped tick on a merge group — it leaves no tick,
which is exactly the state a queue waits on. A caller of a required reusable
therefore runs on `merge_group` and lets the workflow inside decide what it can
answer.

**A gate that reads a range reads the batch's, and never skips.** `dco`,
`attribution` and `commitlint` take their range from the merge group there:
`main`'s tip to the commits the queue built, one squash per pull request, which
is exactly what `main` is about to hold. A merge group that arrives without a
range fails rather than passing over nothing, because a skipped required check
reports success and the queue merges on it. `gate / gate` asks what SonarCloud
can answer about a batch: the new-issue count of every pull request in it, and
the open count against the project (**Q-R64**). SonarCloud's own
`SonarCloud Code Analysis` status is posted by its app and never on a queue's
branch, so a repository behind a queue requires `gate / gate` in its place.

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

## The pin on a shared workflow

Every repository in the org runs its CI out of this one. `spec-check`, `dco`,
`hygiene`, `commitlint` and the rest are reusable workflows defined here once and
called from each repo's `ci.yml` (**Q-R56**), and each call names an exact commit
rather than a branch — `@main` is an instruction to run whatever was pushed here
a minute ago, on a runner holding that repository's token.

An exact commit is a copy, and a copy goes stale in silence. `workflow-pins` is
what makes it say so. It reads every
`uses: lemonfiber/spec/.github/workflows/<name>.yml@<sha>` out of the calling
repository's own `.github/workflows/`, and fails the pull request naming the
commits that pin has not taken (**Q-R68**, **Q-R70**). A pin on somebody else's
action is not its business; that one has versions, and the dependency bot does it.

**A pin is measured against the files it holds**, not against this
repository's `main`: the workflow it names, the workflows that one calls from
here, the scripts they run, and the modules beside those scripts that they
import. Measured against the branch, every pin in the organisation is behind from
the first unrelated commit after each merge, which is to say for most of every
day — and a check that is red on every pull request is a check that stops being
required. Narrowed to those files' history it is red only when something that
can reach the caller has moved.

One asymmetry is worth knowing before reading one of its logs. *Which copy of the
reader runs* is the caller's own where the caller is this repository — the same
split the `shared-files` job makes, and for the same reason: the definition under
review is the one that should be run by the review. It is also the only way a
gate like this can be introduced at all, since `main` does not hold it until the
change that adds it has merged.

**This repository does not pin itself.** Every call to one of its own reusable
workflows is `./`. The `lemonfiber/spec/…@<sha>` form aimed at your own tree is a
supply-chain pin against yourself: it runs an older copy of the file you are
looking at, and it guarantees a refusal from one commit after each merge. The
self-run therefore reports *nothing to check*, which is the honest answer rather
than a gap — the rule is about depending on **another** repository at an exact
revision, and this one does not depend on itself.

### What a stale pin actually holds back

**The workflow and the scripts it runs are pinned together.** Every one of these
workflows checks this repository's scripts out at `job.workflow_sha`, the commit
the caller pinned, and runs `spec_check.py`, `dco_check.py`,
`check_shared_files.py` from there. So a pin names everything that runs on the
caller's runner with the caller's token, and a workflow always runs the scripts
written for the arguments it passes: a script that changes what it is called
with cannot break a caller still on the workflow that calls it the old way.

What the scripts *read* is not pinned. The identifiers a citation must resolve
to, the canonical copies of shared files, the staged versions and `main`'s own
history are checked out at `main` beside the scripts, because each is a fact
about the specification as it stands: an identifier exists from the moment it
merges, and a pin that remembered an older list would refuse a citation that is
right.

A fix to what a gate decides therefore reaches a consumer when its pin moves,
and the pin moves through the release train's bump pull request, which
`workflow-pins` asks for the moment a script the workflow runs has changed. A
step added here does not run there until then either, and neither half goes
stale in silence.

### How a pin gets bumped

Dependabot does it, and `publish-pin-tag.yml` is what lets it. Its
`github-actions` updater compares **versions**: a raw commit has nothing to be
newer than, so a pin whose trailing comment names no version gives the updater
nothing to propose — and a bot that is configured and quiet is indistinguishable
from one that is configured and satisfied.

So every commit to `main` that changes a published workflow, or a script one
runs, is tagged `v1.0.N`.
The series carries no meaning beyond order, which is all the comparison needs.
Each pin names its tag in the comment beside it:

```yaml
uses: lemonfiber/spec/.github/workflows/dco.yml@<sha> # v1.0.12
```

`github-actions` is on in every one of these repositories on a daily schedule,
and it ignores `lemonfiber/spec*`: those pins are moved by the release train's one
rolling bump pull request per repository (**OPS-R85**), which `pin-only` lets
through as a move along spec's `main` (**Q-R83**), and a second bot proposing the
same move would be a second pull request to close.

Any other change under `.github/workflows/` or `.github/actions/` fails
`pin-only` until a maintainer approves it with the `workflows-approved` label,
added after the pull request's last push and only once the user has said yes to
that pull request (**Q-R83**). The label is the only way such a change merges:
`enforce_admins` stays on and is never turned off to let one through. A push, a
force push or the label's removal voids the approval, and `pin-only` fails
again until the label is added again. A label added by an account without the
`admin` or `maintain` role on the repository, a bot's included, approves nothing.
The check reads who added the label and when, and which head each of its own
runs saw, from the forge's records, never from a commit's dates, which the
pusher writes.

`workflow-pins` and the bot answer different questions and neither replaces the
other. The bot keeps a pin at the newest tag whether or not it matters; the check
refuses only a pin whose workflow or scripts have moved. A repository can sit a tag or
two behind and be entirely current.

### Could not ask is not clean

Three outcomes, and the third is the one the check exists for as much as the
first. Exit 0 is every pin current, or a repository that pins nothing of ours.
Exit 1 is drift, naming it. Exit 2 is **could not ask** — no spec checkout
arrived, or a pin that this checkout cannot resolve to a commit, which is what a
shallow clone looks like from the inside.

Exit 2 fails the run and **closes nothing**. The distinction is the same one
`spec-check` draws when it declines to close on its own fault (**GOV-R9** is about
non-conforming work, and a checkout that did not arrive is not that), and it is
load-bearing here for a plainer reason: a drift check that reports clean over a
question it failed to ask is how a pin goes unwatched for months. The history is
fetched at full depth for this reason and no other — without it the honest answer
is 2, on every run, forever.

### Two pin checks, and why both

The `pins` job in `hygiene` also looks at these revisions, and the two are not
duplicates. It reports over the wire, gates only past a threshold — thirty days,
seventy-five commits — and is deliberately a **notice**, because reddening every
repository the moment anything lands here is the check people learn to route
around. It also answers a question this one does not: *which* of the workflows a
repository runs changed in the commits it has not taken.

`workflow-pins` is the gate, and it puts the catch-up in front of the next change
rather than behind it. Its cost is the honest one and worth stating: this
repository moves, so a repository green on Friday is behind on Monday without
anyone touching it, and an author who changed none of it pays the bump. What
makes that bearable is **OPS-R48** — `fan-out-pins.yml`, which opens the bump in
every consumer rather than leaving it owed by all of them. It keeps one pull
request per repository, on `ci/take-the-shared-workflows`, rebuilt and retitled
for each number rather than opened beside the last (**OPS-R85**).

It hangs off `publish-pin-tag` rather than off the merge, because the comment
beside a pin carries the tag and the tag is what Dependabot compares: a fan-out
firing on the merge would have no number to write. It rewrites through
`workflow_pins.py`'s own reader, so it cannot bump a pin the gate would not have
named nor leave one it would. And it visits the repositories `30-repos/repos.toml`
lists rather than a second copy of that list, the map's and the ungoverned ones
alike, since a plugin repository outside the map pins the shared workflows as
much as one inside it. So the day somebody adds a fourteenth repository is not
the day the fan-out quietly stops covering the org.

The map can name a repository before it exists, and the app's token is refused
whole if one repository it is minted for is outside the app's installation. So
the fan-out first asks the installation which repositories it holds, mints only
for those, and names every one it skipped — a warning on the run and a list in
its summary. A skipped repository gets no bump until it exists and the app is
installed on it; one the installation holds and the bump fails in still fails
the run.

**It does not replace the dependency bot and is not racing it.** The bot proposes
whatever tag existed when it ran; this fires from the tag itself. The difference
is the one that cost an afternoon — see below.

**What it needs to be allowed to do it.** The app it runs as must hold
`workflows: write`, and `contents: write` is not enough. GitHub refuses a push
from an app that creates or updates anything under `.github/workflows/`, whatever
else the token may do — and every change a pin bump makes is to a file under
`.github/workflows/`, because that is what a pin on a reusable workflow is. The
refusal arrives as

```
! [remote rejected] ... refusing to allow a GitHub App to create or update
  workflow `.github/workflows/scorecard.yml` without `workflows` permission
```

which reads like a branch problem and is a permission one. It is worth knowing
before reading one of these logs: the first run, on `v1.0.10`, measured all
twelve repositories correctly, rewrote the one stale pin correctly, and failed
there. The fan-out asks for `workflows: write` by name when it mints, so an
installation without it fails at the mint, before any repository is touched, and
is answered only `The permissions requested are not granted to this
installation.` A granted permission also has to be *approved* for each
installation before it takes effect, so granting it on the app is half the job.

Until this existed the bump was done by hand, and that was the reason to keep the
check off the required list on a default branch: a gate whose remedy nothing
automates, made required, is a gate that blocks its own cure. **Q-R71** is the
form that admission takes in a repository that has to defer it, and a deferral
recorded under it names the work it waits on — which is now landed, so those are
the deferrals to review rather than to renew.

### Freshness of a vendored client reports, and the bump pull request judges

A repository can hold more than one check of this shape: *is what we pin still
what they have?* `workflow-pins` asks it of the shared workflows and is required
where it runs. `sdk-drift` and `contract-drift` ask it of a vendored client, and
run on every pull request without being required (`70-operations/required-checks.toml`).

The difference is what moves. The shared workflows change when this repository
releases them, and their pin wave is one pull request per repository. A vendored
client's upstream moves on every merge there, and the check reads the upstream's
head rather than anything the pull request changed. Required, it would gate every
change downstream on a fact none of them can affect.

So the question is answered where it belongs. When an upstream moves, its bump
bot opens the pull request that takes the new pin, and that pull request passes
or fails on every other required check run against the new client. A red drift
check on any other pull request says the pin is behind; it does not stop the
change.

## Related

- [canonical-spec.md](canonical-spec.md) · [change-lifecycle.md](change-lifecycle.md)
- [contributing.md](contributing.md) — the contributor's view
- [overrides.md](overrides.md) — including when the bot itself is broken
- [issue-routing.md](issue-routing.md)
