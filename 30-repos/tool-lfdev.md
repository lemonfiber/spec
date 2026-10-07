# Repo: `tool-lfdev`

**Status:** Proposed

The developer command line, installed as `lfdev`. Python, standard library only,
Hippocratic 3.0. It does what a contributor repeats in every repository: reading the
board, finding something to pick up, claiming it, proposing a change, recording that a
requirement is built, reading a pull request's checks, asking what blocks one, and
checking that a clone is set up to commit.

**Implements:** the contributor flows of
[working in the repositories](../50-governance/working-in-the-repositories.md); reads
the [board snapshot](../70-operations/board-format.md).

---

## Why this is a separate repo

The tool is used in every repository and released on its own clock. Kept inside `spec`
it would ride the specification's pins and its CI, and every fix to a command would be
a change to the repository whose pull requests every other repository's gates read.

## The one property to remember

**It changes nothing a pull request did not.** Every write the tool makes is a branch,
a commit and a pull request in an organisation repository, made under the person's own
credentials. What it reads about the project, it reads from the published board
snapshot, the same file the frontpage renders, so the two cannot disagree.

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R74** | The tool MUST be written against Python's standard library alone and MUST install as one command, `lfdev`. |
| **REPO-R75** | The tool MUST read and write the forge through its REST API only, and MUST NOT read a pull request's checks more often than once every ten minutes. |
| **REPO-R76** | Whatever the tool reports about versions, goals, claims or repositories MUST be read from the published board snapshot. |
| **REPO-R77** | Every change the tool makes MUST be a branch, a signed commit carrying a `Spec:` line and a sign-off, or a pull request, made with the person's own credentials. |
| **REPO-R78** | Every command MUST be tested, and CI MUST hold the tool at 100% line coverage. |

## Related

- [Working in the repositories](../50-governance/working-in-the-repositories.md)
- [The board snapshot](../70-operations/board-format.md)
- [website-contribute.lemonfiber.app](website-contribute.md) — renders its guide
