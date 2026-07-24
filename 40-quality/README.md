# Quality

**Status:** Partial — see contents

The standards a change is held to. Where [50-governance](../50-governance/)
covers *how* change enters, this covers *whether it's good enough*.

---

## Contents

| Doc | Covers | Status |
|-----|--------|--------|
| [code-comments.md](code-comments.md) | Comment policy — mechanical and judgment rules, lexer-based enforcement | **Accepted** |
| code-standards.md | MSRV, lint policy, error handling, `unsafe` prohibition, module boundaries | Not written |
| testing-strategy.md | Test pyramid, golden files, fixture discipline, what must be covered | Not written |
| ci-cd.md | Pipeline stages, three-platform matrix, `cargo-dist` release engineering | Not written |
| security.md | Threat model, secret handling, supply chain, dependency policy | Not written |
| definition-of-done.md | What "finished" means before a PR opens | Not written |

## The `Q-R` namespace

Quality requirements use `Q-R##`, distinct from feature requirements (`A2-R4`)
and governance rules (`GOV-R12`).

A change to how code is written cites a `Q-R`. A change to what the product does
cites a feature requirement. The separation matters because the two have
different review audiences and different rates of change.

## The governing principle

**Every rule here is either mechanically enforced or explicitly marked as
judgment.**

A standard that is neither is decoration. It gets cited when convenient, ignored
under deadline pressure, and produces exactly the inconsistency it was written to
prevent — while giving everyone the impression the matter is handled.

Where a rule can be checked by a machine, it is, and the check is part of CI.
Where it genuinely cannot — whether code is complex enough to deserve a comment,
whether an abstraction earns its place — the rule says so plainly and binds
contributors anyway.

The [comment policy](code-comments.md) demonstrates the split: mechanical rules
`M1`–`M7` are enforced by a lexer-based test; judgment rules `J1`–`J5` are not,
and say so.

## Related

- [50-governance](../50-governance/) — how change enters
- [30-repos](../30-repos/) — per-repo technical specs
- [10-functional](../10-functional/) — what the product should do
