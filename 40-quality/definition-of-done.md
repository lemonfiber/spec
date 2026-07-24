# Definition of done

**Status:** Accepted

What "finished" means before a PR opens. The single checklist a change is held to,
gathering the obligations scattered across this section into one place.

---

## The principle

**Production-ready always.** Shipped code is finished — no deferral notes, no
"come back to this", no `TODO` ([comment policy](code-comments.md)). If work
remains, the work is not done, and the PR is not ready.

This is not a high bar arbitrarily set. A codebase where "done" means "mostly
done" accumulates a second, invisible backlog inside the code itself, and that
backlog is never paid down because it isn't visible.

## The checklist

A change is done when **all** of these hold:

### Spec

- [ ] Cites a spec identifier that exists on the spec's `main` (`GOV-R2`, `GOV-R3`)
- [ ] If it changed behaviour, the spec PR merged **first** (`GOV-R4`)
- [ ] Citation is in a commit trailer **and** the PR body (`GOV-R5`)
- [ ] No requirement ID appears in any code comment (`GOV-R6`)

### Correctness

- [ ] The cited requirements are actually satisfied — not approximately
- [ ] New behaviour has tests; the [must-cover paths](testing-strategy.md#what-must-be-covered) are covered
- [ ] Every new user-facing error carries a remedy (`Q-R16` — it won't compile otherwise)
- [ ] No `unwrap`/`expect`/`panic` in non-test code (`Q-R12`)

### Checks

- [ ] `rustfmt`, strict `clippy`, arch tests, unit, golden, integration all pass (`Q-R30`)
- [ ] No lint suppression added to `src/` (`Q-R13`)
- [ ] `cargo-deny` clean; no new advisory or disallowed licence (`Q-R32`)
- [ ] No secret in any tracked file, tests included (`Q-R33`)

### Documentation

- [ ] Public items documented (`Q-R20`)
- [ ] Comments obey the [policy](code-comments.md) — why not what, 2–4 line blocks, no IDs
- [ ] Repo-specific *how* is in `.docs/`, linked from code, not inline (`Q-R10`)

### Cross-cutting

- [ ] Interactive additions have a non-interactive equivalent (`F1-R6`)
- [ ] User-facing output obeys the [error model](../10-functional/features/g-ux/g4-error-model.md) and [accessibility](../10-functional/features/g-ux/g3-accessibility.md)
- [ ] Platform-conditional code goes through the platform component, not scattered `cfg!` (`ARCH-R35`)

## What "done" explicitly excludes

Stated so they can't be smuggled in as done:

| Not done | Why |
|----------|-----|
| "Works on my machine, untested elsewhere" | The platform matrix is a promise; a change that only works on one is unfinished |
| "Passing but with a suppressed lint" | The suppression is the unfinished part (`Q-R13`) |
| "Feature works, error path panics" | A panic is an unhandled error with no remedy (`Q-R12`, `G4`) |
| "Spec change to follow" | That's drift with a promise attached — the exact thing governance prevents |
| "TODO for the edge case" | Shipped code is finished; handle it or scope it out explicitly |

## The reviewer's job

The checklist is the author's; the reviewer verifies it, and answers two
questions CI cannot:

1. **Does the code actually satisfy the cited requirement?** CI confirms the
   citation resolves; only a human confirms the behaviour matches it.
2. **Is anything here a judgment-rule violation?** Redundant comments,
   premature abstraction, a runtime check where a type would do — none are
   machine-detectable, all are review-blocking.

A review that only re-runs what CI already ran adds nothing. The value is in the
two questions above.

## Definition of done for the spec itself

A spec change is done when:

- [ ] Every new requirement has a permanent, unique ID (`GOV-R8`)
- [ ] Every cited identifier resolves (spec-side CI)
- [ ] A requirement-altering change names the affected repos (`GOV-R7`)
- [ ] Every internal link resolves
- [ ] The doc carries a status (Draft / Accepted / Superseded)

## Requirements

| ID | Requirement |
|----|-------------|
| **Q-R47** | A change MUST satisfy every item on the done checklist before its PR is marked ready. |
| **Q-R48** | "Done" MUST NOT include deferred work, suppressed lints, panicking paths, or promised follow-up spec changes. |
| **Q-R49** | Review MUST verify that code satisfies the cited requirement, beyond CI confirming the citation resolves. |
| **Q-R50** | A spec change MUST satisfy the spec definition of done before merge. |

## Related

- [code-standards.md](code-standards.md) · [testing-strategy.md](testing-strategy.md) · [ci-cd.md](ci-cd.md) · [security.md](security.md)
- [code-comments.md](code-comments.md)
- [50-governance/contributing.md](../50-governance/contributing.md) — the same, from the contributor's side
