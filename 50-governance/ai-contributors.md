# Working with AI agents

**Status:** Accepted

The canonical rules for AI-assisted contribution, across **every** repo in the
org. Each repo carries an **`AGENTS.md`** — the tool-agnostic standard that
Cursor, Codex, Aider, Claude Code and others all read — with a thin `CLAUDE.md`
pointing to it. That file is a short repo-specific header that points *here* —
this is the single source, so the rules cannot drift between repos or favour one
agent.

These bind AI agents and the humans directing them equally. Nothing here is
AI-specific in principle; it is gathered in one place because AI agents need it
stated explicitly and consistently.

---

## The five rules

### 1. The spec is canonical — cite it

Every change references an identifier that already exists on `spec@main` — a
requirement (`A2-R4`), an ADR (`ADR-0006`), or a governance rule (`GOV-R12`). If
you're changing behaviour, the spec change merges **first**. This is enforced by
`spec-check`; see [contributing](contributing.md).

An agent must not invent a plausible-looking ID to satisfy the gate. If no
requirement fits, the spec has a gap — open a spec PR describing what should
happen, then implement against it.

### 2. Identifiers never appear in code comments

`GOV-R6`. A requirement ID, ADR number, or phase reference in a comment is
provenance, and provenance rots when the artefact it names is superseded.
Citations go in **commit trailers and PR bodies**; code links to the repo's
`.docs/`, and those pages cite the spec. An agent must never be instructed to
write an ID into a comment, and must refuse if asked.

### 3. Comments explain *why*, never *what*

The [comment policy](../40-quality/code-comments.md) is strict and enforced: no
lone one-line comments (an informative comment is a 2–4 line block), no narration
of what the next line does, no `TODO`. **Over-commenting is a defect, not
thoroughness** — the single most common failure of AI-generated code. Write
self-documenting code; reserve comments for a non-obvious *why*.

### 4. Production-ready always

Shipped code is finished. No deferral notes, no "come back to this", no stubs
left behind, no suppressed lints. If work remains, it isn't done — meet the
[definition of done](../40-quality/definition-of-done.md) before opening a PR.
An agent that cannot complete something says so plainly rather than leaving a
`TODO`.

### 5. No AI attribution in commits

Commits carry **no** `Co-Authored-By` trailer and no reference to the tool that
produced them. The work is attributed to its author; how it was written is not
recorded in the history. Keep commit messages about the change, citing the spec.

## What an agent should read first

For any repo:

1. That repo's `AGENTS.md` — what the repo is, its one load-bearing property.
   (`CLAUDE.md` points to the same file.)
2. The repo's spec section under [`30-repos/`](../30-repos/) and whatever
   feature/architecture sections it implements.
3. This document and [contributing](contributing.md).

Do **not** start editing before the cited requirement is identified. The spec is
large; the right move is to find the requirement the change serves, then work
backward from it.

## House style, briefly

- Match the surrounding code — new code should be indistinguishable from what's
  there.
- Prefer the type system over runtime checks; an invariant in a type can't be
  violated.
- No premature abstraction — a trait with one implementation is usually a
  function.
- Tables over prose in docs; every doc states its intent in one line, then the
  substance, then its requirements.

## Requirements

| ID | Requirement |
|----|-------------|
| **GOV-R26** | Each repo MUST carry an `AGENTS.md` (the tool-agnostic standard) that points to this document rather than restating it, with `CLAUDE.md` pointing to `AGENTS.md`. The guide MUST NOT be specific to one agent. |
| **GOV-R27** | AI-generated contributions MUST meet the same standards as any other — citation, comment policy, definition of done — with no exemption for being machine-authored. |

## Related

- [contributing.md](contributing.md) — the human-facing version
- [canonical-spec.md](canonical-spec.md) — the rule and the `GOV-R` namespace
- [40-quality/code-comments.md](../40-quality/code-comments.md) — the comment policy
- [40-quality/definition-of-done.md](../40-quality/definition-of-done.md)
