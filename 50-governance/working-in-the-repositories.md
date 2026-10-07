# Working in the repositories

**Status:** Accepted

How work moves through the organisation's repositories, for a person and for an
agent alike: where to start, where to work, how a pull request is taken from
opened to merged, and what is asked of the maintainer.

---

## Where to start

Start at where every goal of every unreleased version stands: the
[roadmap and board on lemonfiber.app](../30-repos/website-lemonfiber.md), rendered
from the snapshot the `state` workflow publishes, or `just goals <version>` from
local checkouts. They say what is met, what is built but not marked, what an open
pull request is working on, and what nobody has started. Pick work from it.

Then this section: [the rules for agents](ai-contributors.md), the
[change lifecycle](change-lifecycle.md), [contributing](contributing.md) and
this page. A repository's own `AGENTS.md` adds only what is true of that
repository, and points here first (`GOV-R50`).

## Where the work happens

| Who | Where |
|-----|-------|
| The main session | The main checkout of each repository, so the maintainer sees the files change as they are written |
| A subagent | A worktree of its own, one per repository it works in |

A worktree belongs to one repository. A task that spans repositories works in a
worktree of each, and an agent never writes in a checkout it was not sent to:
not by `cd`, not by `git -C`, and not through a path that climbs out of its
tree. Paths are staged by name, never with `git add -A`, because another
agent's uncommitted file beside yours is the normal state of a shared checkout.
A worktree is removed once its pull request merges (`GOV-R51`).

## Claiming work

Work is claimed by opening a pull request, a draft one included, whose commits
carry the `Spec:` lines of the requirements it works on. The report reads every
open pull request in every repository and shows the requirement as claimed.
There is no other register: a claim that is not a pull request is invisible to
everyone else.

A pull request needs a commit before it can open. A claim made with the developer
command line opens with an empty signed commit carrying the `Spec:` line and a
sign-off; a claim made from the website adds the requirement's row to the
repository's tracker as `open`, which is true while the work is in progress and
which the same pull request turns `done` with its evidence (`GOV-R57`).

## At most three open pull requests

A repository holds at most three open pull requests opened by people and agents;
the organisation's bots (`dependabot`, the release App) are not counted. The cap
keeps the shared CI moving and every pull request owned. It is held softly: the
developer command line refuses to open a fourth, a bot comments on one that is
opened anyway, and the board flags the repository (`GOV-R58`). Before opening a
pull request, merge or close one.

## The developer command line

What contributors repeat in every repository is one tool, `lfdev`, kept in
[`tool-lfdev`](../30-repos/tool-lfdev.md): reading the board, finding something to
pick up, claiming it, proposing a change or reporting a gap, recording that a
requirement is built, reading a pull request's checks, asking what blocks it, and
recording a decision (`GOV-R59`). It reads the project from the published board
snapshot, the same file the website renders, and reads and writes the forge
through REST.

## Contributing from the website

The website helps a contributor compose a change and creates nothing itself. Its
forms build the change, a proposal or a tracker row, and submitting opens GitHub,
prefilled, under the person's own account, where they open the pull request, or
the issue that becomes one. No bot or server acts on their behalf (`GOV-R60`).
Every action it offers is also a command of `lfdev`, named beside the action, so
the website is never the only way to do anything (`GOV-R61`).

## Commits

- Signed, with the key the repository's history verifies.
- Ending in a `Spec:` trailer naming what the change serves, and a DCO
  `Signed-off-by` ([DCO](dco.md)).
- Crediting no tool ([`GOV-R46`](ai-contributors.md)).
- Through the repository's hooks: a hook is never skipped.

A branch is squashed onto its merge base, `git merge-base HEAD origin/main`,
never onto `origin/main` itself, which after a fetch would revert whatever
landed in between. It is rebased locally and signed; the forge's update-branch
button writes unsigned commits and is not used. A branch is rebased when it
conflicts with its base, not to bring it up to date: required checks do not
ask for an up-to-date branch, and there is no merge queue (`GOV-R52`).

## Opening a pull request

1. The static gates run locally before every push: formatter, linter, type
   checker, and the targeted tests for what changed. Full suites, coverage,
   mutation and the slow gates run in CI, which runs them on a shared cache and
   in parallel; mutation testing never runs locally.
2. The author reviews the change until a whole pass finds nothing, for
   correctness, security, performance and constants. For each value: is it a
   constant, an enumeration, a policy or configuration, and is it already
   declared somewhere else?
3. The spec change it depends on has merged. A pull request citing an
   identifier that is not on `spec@main` is closed by `spec-check`.
4. It opens ready for review. A draft is for work that is unfinished.
5. Auto-merge is armed only once the pull request shows as blocked on its
   checks and its base is a protected default branch. A stacked pull request's
   base is not protected, so auto-merge would merge it at once.

## Owning a pull request

Opening a pull request is taking responsibility for getting it green and
merged. Its author:

- checks CI on every pull request they own while they wait on any one, and
  fixes a red check at once, before starting anything new (`GOV-R53`);
- rebases, resolves and pushes a pull request the forge reports as conflicted
  as soon as it is;
- fixes the thing a gate refuses, and never weakens the gate or merges past it;
- names the blocker and hands the pull request over deliberately when they
  cannot land it.

A pull request belongs to whoever opened it: nobody else merges, closes,
retitles, rebases or arms auto-merge on it. When its author has stopped, the
main session takes it over and lands it. A branch other pull requests are based
on is not deleted until they are retargeted, because deleting a base closes
every pull request stacked on it.

## Using the forge within its capacity

The organisation's CI runs on a fixed number of concurrent jobs, and every push
to a pull request queues every check it has. A push carries finished work, so
fixes are batched rather than pushed one at a time. A check is read through the
forge's REST interface rather than its GraphQL interface: the two have separate
quotas, and the GraphQL one is spent by every agent on the account at once.
`gh pr checks`,
`gh pr view` and `gh pr list` spend GraphQL, and `gh api repos/…/commits/<sha>/check-runs`
does not. A pull request's checks are read at most once every ten minutes, and
never in a loop that runs until they finish (`GOV-R54`).

## What goes to the maintainer

| Decided by the maintainer | Decided by whoever does the work |
|---------------------------|----------------------------------|
| Design and architecture, a promise the spec makes, a security trade-off | Wording: pull request text, commit messages, refusal sentences, documentation |
| A repository or organisation setting, a ruleset, a secret | Which tests prove a change, and how the code is arranged within the rules |
| Accepting an ADR, merging where an agent may not | Unblocking: rebasing a conflicted branch, resuming stopped work |
| Anything published, released or announced | |

A question for the maintainer comes with its options and a recommendation, and
work that does not depend on the answer goes on meanwhile. The answer is
recorded in this specification the day it is given ([decision log](decision-log.md)).

## What an agent never does

- An agent never opens an issue: what it finds, it fixes. Nothing is filed
  upstream; a defect in a dependency is patched in the repository that vendors
  it, by the install step that applies the patch.
- A workflow never calls a language model. A check that reads as smart is
  static analysis and rules.
- A secret is never printed, echoed, logged or written into a file that is
  committed or shared.
- A repository or organisation setting is never changed without the
  maintainer (`GOV-R55`).

## Standing traps

Facts about the tools, each of which has produced a wrong conclusion:

- A local checkout that has not been fetched measures an old tree. Compare
  against `origin/main` before quoting a number, and cite a file at the
  revision on the default branch rather than a sibling checkout's branch.
- Worktrees of one repository that share a build cache can read each other's
  artefacts. A surprising local result is rebuilt before it is believed.
- During a rebase, `--ours` and `--theirs` are swapped against a merge.
  Check out a path from a named ref and read it, rather than reasoning about
  sides.
- A failure on the default branch reddens every pull request at once. Before
  fixing a red check on a branch, look at whether `main` has it too.
- Pushing to a branch whose pull request has merged puts work on a dead line.

## Requirements

| ID | Requirement |
|----|-------------|
| **GOV-R50** | Every repository's `AGENTS.md` MUST point first at the generated report of where every unreleased version stands and then at this section, and MUST NOT restate a rule this section or [ai-contributors.md](ai-contributors.md) holds. |
| **GOV-R51** | The main session MUST work in each repository's main checkout and a subagent MUST work in a worktree of its own; an agent MUST NOT write in a checkout it was not given, and MUST stage paths by name. |
| **GOV-R52** | A branch MUST be rebased locally with signed commits, and only where it conflicts with its base; it MUST NOT be updated through the forge, which leaves the commits unsigned, and MUST be squashed onto its merge base rather than onto the default branch. |
| **GOV-R53** | The author of a pull request MUST check CI on every pull request they own while they wait on any one, and MUST fix a red check at once, before starting new work. |
| **GOV-R54** | An agent MUST read a pull request's checks through the forge's REST interface, at most once every ten minutes, and MUST NOT poll in a loop. |
| **GOV-R57** | A claim made with the developer command line MUST open its pull request with an empty signed commit carrying the claimed `Spec:` line and a sign-off; a claim made from the website MUST add the requirement's row to the repository's tracker as `open`. |
| **GOV-R58** | A repository MUST NOT hold more than three open pull requests opened by people and agents, the organisation's bots not counted; the developer command line MUST refuse to open a fourth, a bot MUST comment on a fourth that is opened anyway, and the board MUST flag the repository. |
| **GOV-R59** | The operations contributors repeat (reading the board, finding work, claiming, proposing, reporting a gap, recording status, reading checks, asking what blocks a pull request, recording a decision) MUST be commands of one developer command line kept in an organisation repository, tested like the gates, and reading the forge through REST only. |
| **GOV-R60** | The organisation's website MUST NOT create a branch, commit, issue or pull request itself: it MUST compose the change in the visitor's browser and open the forge, prefilled, under the visitor's own account, and no bot or server MUST act on the visitor's behalf. |
| **GOV-R61** | Every action the organisation's website offers a contributor MUST also be a command of the developer command line, and the website MUST name that command beside the action. |
| **GOV-R55** | An agent MUST NOT open an issue, file a report upstream, call a language model from a workflow, print a secret, or change a repository or organisation setting without the maintainer. |

## Related

- [ai-contributors.md](ai-contributors.md): the rules for agents
- [change-lifecycle.md](change-lifecycle.md): spec first, then implementation
- [contributing.md](contributing.md): the human-facing guide
- [decision-log.md](decision-log.md): every maintainer decision, dated
