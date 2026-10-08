# Proposals

**Status:** Accepted

A proposal is a pull request adding one file here: a Draft proposal for a new or
changed requirement, or a report of a gap, with no identifier
([the RFC process](../../50-governance/rfc-process.md)). It is discussed and decided
on its pull request. A maintainer approves it with the `proposal:approved` label;
identifiers are allocated then, and its text moves into the feature or page it
belongs to. A declined proposal is closed unmerged, and its file never reaches
`main`.

Copy [`TEMPLATE.md`](TEMPLATE.md) to `<a-short-name>.md`: lower-case letters,
digits and hyphens. `integrity.py` holds every file here to that shape:

| Field | Holds |
|---|---|
| `kind` | `proposal`, a new or changed behaviour, or `gap`, something the specification does not say |
| `area` | The catalogue area it belongs to, one letter |
| `title` | A short noun phrase naming the capability |
| `amends` | The feature it changes, by identifier, or the page, by path from the repository root; a gap names the one that is silent |
| `status` | `draft`, always: nothing here binds |

A proposal carries a `## Proposed behaviour` section of statements, each a
bullet using MUST, SHOULD or MAY. A gap carries a `## What the specification does
not say` section. Neither defines an identifier: a requirement row here is
refused, because numbers are allocated on approval, so two proposals opened the
same day cannot take the same one.
