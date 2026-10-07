# ADR-0039: Each repository records what it built, one row per requirement

**Status:** Accepted
**Date:** 2026-10-07
**Decided:** 2026-10-07, by the maintainer, Wessel Verheij: a `status.toml` in every repository a version is satisfied in, in one shape, read by the release gate and the no-stubs gate together; one short row per requirement naming its state, its evidence by path and test, and optionally the commit it landed in; the binary's deliverable rows migrated to that shape; no Markdown copy of a tracker committed, the generated report being the page a person reads; and each tracker under a thousand lines, split into one file per feature where it would not be.

## Context

The release gate counts a goal met when a merged commit cites it and the
implementation-status tracker marks it done ([OPS-R34](../../70-operations/staging.md)).
There was one tracker, `IMPLEMENTATION-STATUS.md` in `lemonfiber`, written from a
`status.toml` arranged by milestone and deliverable. A row named the requirements it
covered and described in prose what was true.

Two things went wrong with that, and both were found when 0.18.0's 308 goals were
read against the code.

**Work outside the binary could not be recorded where it was done.** The rule was to
update the tracker in the pull request that did the work, and the tracker lived in
one repository. A pull request in the companion, the web surface or Home Assistant
could not touch it. Eighty-four of 0.18.0's goals were built and cited in those
repositories, and no row ticked them, so the gate called them unmet.

**A row per deliverable answered the gate's question only by being read.** The gate
asks about one requirement at a time. A deliverable row named several, described all
of them in one paragraph, and could tick one by naming it in a sentence about another.
`status_lint.py` grew seven checks to keep that reading honest.

## Decision

**Every repository named in some version's `satisfied_in` keeps a `status.toml` at its
root** ([OPS-R74](../../70-operations/staging.md)), in one shape, and changes it in the
pull request that changes what it says. The release gate and the no-stubs gate read
every searched repository's tracker from the checkouts they already read citations
from, and a requirement is done where any tracker records it done.

**A row is one requirement.** It names the requirement, its state (`done`, `partial` or
`open`), the evidence that holds it — the code and the test, by path, with `::text`
naming a test inside a file and `repo:path` a file in another repository — and,
optionally, the commit it landed in where no commit cites it. Prose about why the code
is the way it is belongs beside the code.

**A row is checked** ([OPS-R75](../../70-operations/staging.md)): the requirement exists
and appears once, a retired one only where a version locked it first; a done row names
evidence and the evidence exists; and a landed commit is in that repository's history.
A done row no version locks yet is recorded like any other, since work done ahead of
its version is still a fact. `scripts/status_check.py` holds the shape and the checks.

The binary's milestone-arranged rows move to this shape, each requirement taking the
evidence its deliverable row linked to. **No Markdown copy of a tracker is committed**:
`IMPLEMENTATION-STATUS.md` goes, and the page a person reads is the generated report of
where every version stands, which reads every tracker at once. **A tracker stays under a
thousand lines**: a row is one line, and a repository with more rows than that keeps one
`status/<feature>.toml` per feature, each holding only its own feature's rows.

## Alternatives

| Option | Why not |
|---|---|
| One tracker in the binary, with a follow-up pull request there for work done elsewhere | It is the arrangement that left eighty-four goals unticked. A follow-up nobody is made to open is one nobody opens. |
| One tracker in the specification | The same problem from the other side: the work and the record of it would still be two pull requests in two repositories. |
| A `Satisfies:` trailer, and no tracker deciding done | A merged commit cannot be corrected, so a trailer that claimed too much could never be withdrawn, and the human attestation OPS-R34 asks for would be gone. |
| Keep rows per deliverable and add an evidence column | A deliverable row still answers the gate's per-requirement question only by being read, and still lets one row tick a requirement by mentioning it. |

## Consequences

- A builder records their work in the repository they built it in, in the same pull
  request, so the record and the work cannot be two pull requests apart.
- "Is requirement X built, and where" is answered by searching every repository's
  `status.toml` for one identifier, which a person and a script do the same way.
- Evidence is checked against the tree, so a renamed file or test fails the check
  instead of leaving a link that no longer points at anything.
- A requirement built across two repositories can have a row in each. Either one
  recording it done satisfies the gate.

## Related

- [OPS-R34](../../70-operations/staging.md), [OPS-R54](../../70-operations/staging.md),
  [OPS-R73](../../70-operations/staging.md), [OPS-R74](../../70-operations/staging.md),
  [OPS-R75](../../70-operations/staging.md)
- [Version manifests](../../70-operations/versions/README.md)
