# ADR-0065: A partial share holds a requirement open

**Status:** Accepted
**Date:** 2026-11-25
**Decided:** 2026-11-25, by the maintainer, Wessel Verheij: the release gate reads a
requirement as done only when every searched repository whose tracker records it records it
`done`, and at least one does. A `partial` or `open` row in any searched repository holds it
open, and the gate names the repository holding it.

**Amends** [ADR-0039](0039-each-repository-records-what-it-built.md): a requirement is done
where every searched tracker recording it records it done, rather than where any one does.

## Context

A version is satisfied in several repositories (`satisfied_in`), and the release gate and
the no-stubs gate read every one of their trackers
([OPS-R74](../../70-operations/staging.md)). One requirement is often built in more than one
of them: the core serves a read, and each SDK and each plugin carries its own share of it.
Each repository records its own share in its own row.

Read as "done where any tracker records it done", one repository's `done` outvotes another's
`partial`. A requirement whose core share is finished and whose plugin share is not reads as
met, and the gate passes a version carrying it, while the repository recording `partial` says,
in the record the gate exists to read, that the requirement is not finished.

## Decision

A requirement is done only where at least one searched repository's tracker records it
`done` and none records it in another state. A `partial` or `open` row in any searched
repository holds it open, whatever the others record.

- The release gate's verdict names, for each goal, the repositories holding it open: in its
  per-goal line, and as `held_in` in its JSON.
- The no-stubs gate reads the same set of done requirements, so a requirement held open is
  not built.
- The report of where every goal stands reads a held goal as not met and names the holders
  as `held_in` ([OPS-R76](../../70-operations/staging.md)). Its verdicts keep their names: a
  held goal that is cited reads `unmarked`, one recorded done and cited nowhere `uncited`.
- A repository with no row for a requirement holds nothing: it records no share of it.

## Alternatives

| Alternative | Why not |
|---|---|
| Done where any tracker records it done | A finished share in one repository hides an unfinished share in another, and the gate passes what a searched repository records as not finished. |
| Only `partial` holds a requirement open, and `open` does not | An `open` row is a repository saying its share has not started, which is further from done than `partial`. |
| A manifest names, per goal, which repositories carry a share | A second record of the same fact the trackers hold, kept by hand and out of step with them the first time a share moves. |
| A new verdict, `held`, in the report | The report's verdicts are read by other repositories by name; `held_in` says the same beside the verdicts they already know. |

## Consequences

- A goal met by one repository's row is held open the moment another searched repository
  records its share `partial` or `open`, and stays held until that row reads `done` or the
  repository is no longer searched.
- Versions already released keep their status; the report shows each goal of theirs that a
  searched repository records as not done.

## Related

- [OPS-R34, OPS-R54, OPS-R74, OPS-R76](../../70-operations/staging.md)
- [ADR-0039](0039-each-repository-records-what-it-built.md)
