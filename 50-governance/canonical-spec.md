# Canonical spec

**Status:** Accepted

---

## The rule

Every change to `lemonfiber`, `media-stack` or `homebrew-tap` MUST cite at least one
identifier that exists in this repository on `main` at the time the change merges.

Citable identifiers are:

| Kind | Form | Lives in |
|------|------|----------|
| Requirement | `A2-R4`, `C9-R13` | [10-functional/features](../10-functional/features/) |
| Decision | `ADR-0006` | [00-overview/decisions](../00-overview/decisions/) |
| Governance rule | `GOV-R12` | This section |

## The `GOV-R` namespace

Features own requirements about the product. Some changes have nothing to do with
the product — a CI runner version, a formatting pass, this section's own rules.
Those cite `GOV-R` identifiers instead.

The namespace exists so that governance is subject to its own rule. A change to
how the bot works is itself a change, and it cites a `GOV-R`.

| ID | Requirement |
|----|-------------|
| **GOV-R1** | The spec repository is canonical. Where spec and implementation disagree, the spec is correct and the implementation is a defect. |
| **GOV-R2** | Every change to an implementation repo MUST cite at least one requirement, ADR, or governance ID. |
| **GOV-R3** | A cited identifier MUST exist on the spec repository's default branch at the implementation change's merge-base. |
| **GOV-R4** | Where a change implements new or altered behaviour, the corresponding spec change MUST be merged **before** the implementation change. |
| **GOV-R5** | Citations MUST appear in a commit trailer and in the pull request body. |
| **GOV-R6** | Citations MUST NOT appear in code comments. |
| **GOV-R7** | A spec change that alters an accepted requirement MUST state which implementation repos are affected. |
| **GOV-R8** | Requirement identifiers are permanent. A withdrawn requirement is marked withdrawn in place; its number is never reused. |
| **GOV-R9** | Non-conforming pull requests MUST be closed with an explanation and reopening instructions, not merely failed. |
| **GOV-R10** | The maintainer override MUST require a written justification and MUST be recorded permanently. |
| **GOV-R11** | Governance changes are themselves subject to these rules and MUST cite a `GOV-R` identifier. |
| **GOV-R12** | Routine maintenance — dependency updates, formatting, CI configuration, typo corrections — MUST cite a governance identifier or use the override. |

## What "canonical" means, precisely

**GOV-R1** is the load-bearing one, and it has a consequence people find
uncomfortable: if the code does something the spec doesn't describe, **the code is
wrong**, even if the code's behaviour is better.

The remedy is not to tolerate the divergence. It is to change the spec — which
takes a PR, a review, and thirty seconds of thought about whether the better
behaviour is actually better. That friction is the point. It is small enough to
pay and large enough to prevent drift accumulating unnoticed.

## Scope

**In scope:** every commit to `lemonfiber`, `media-stack`, `homebrew-tap`, and this repo.

**In scope but citing `GOV-R`:** dependency bumps, CI configuration, formatting,
typo fixes, and anything else with no product-behaviour counterpart.

**Not in scope:** forks. Anyone may fork any repo and do as they like — the
[customisation guarantee](../10-functional/features/f-extensibility/f1-customisation.md)
is explicit that the stack runs without lemonfiber at all. Governance binds this
org's repos, not the software's users.

## Why citation alone is insufficient

A rule requiring "cite a requirement" is satisfied by typing any plausible string.
It catches carelessness and nothing else.

**GOV-R3** and **GOV-R4** are what give the rule force:

- **GOV-R3** resolves the citation against the spec's actual content. An invented
  or mistyped ID fails. A *withdrawn* ID fails.
- **GOV-R4** requires the spec change to be merged *first*. This is the one that
  cannot be gamed: you cannot cite a requirement that doesn't exist yet, so the
  spec is structurally incapable of falling behind.

Together they mean the spec is never a retrospective account of what was built.

## The cost, stated honestly

This is slower than not doing it. A change that would have been one PR is
sometimes two, with a review between them.

That cost is worth paying for a project whose entire premise is that the
specification is the artefact of record — but it is a real cost, borne on every
change, and it is the reason the [override](overrides.md) exists rather than
pretending no situation ever justifies bypassing it.

## Related

- [change-lifecycle.md](change-lifecycle.md) — the ordering in practice
- [cross-repo-ci.md](cross-repo-ci.md) — mechanical enforcement
- [overrides.md](overrides.md) — the escape hatch
- [40-quality/code-comments.md](../40-quality/code-comments.md) — why GOV-R6 exists
