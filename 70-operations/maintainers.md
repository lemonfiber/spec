# Maintainers

**Status:** Accepted

Who maintains what, how decisions are made, and where the authority to
[override governance](../50-governance/overrides.md) sits.

---

## One registry, scoped by domain

Maintainership lives in a **single file** — [`maintainers.toml`](maintainers.toml) —
but each entry is **scoped** by repo and spec domain. So the project can have a
brand maintainer, a `lemonfiber` maintainer, and a lead, all without splitting the
registry across files.

```toml
[[maintainer]]
handle  = "someone"
scope   = ["brand"]                       # which repos
domains = ["60-brand", "brand/tokens/**"] # which areas
```

Each repo's `.github/CODEOWNERS` is **generated** from this registry
(`scripts/gen_codeowners.py`) — CODEOWNERS is never edited by hand, so the single
file stays the source of truth and GitHub's review-routing follows it
automatically.

## Roles

| Role | Can | Scope |
|------|-----|-------|
| **Lead** | Everything a maintainer can, plus break ties and apply the governance [override](../50-governance/overrides.md) | The whole org |
| **Maintainer** | Review, approve, and merge PRs; triage issues; cut releases | Their `scope` repos |
| **Domain maintainer** | The above, within their `domains` | Specific areas/paths |

A single person can hold several rows; today the lead holds all scopes, which the
registry expresses as `scope = ["*"]`.

## How decisions are made

**Lazy consensus.** A change that's been open for review, cites its spec
identifier, passes CI, and draws no sustained objection, merges. Most changes need
no meeting.

Where maintainers disagree:

1. The [spec](../README.md) is the tiebreaker — if the change contradicts an
   accepted requirement, the requirement wins until a spec PR changes it.
2. If the spec is silent, the maintainers of the affected `domains` decide.
3. If they can't agree, the **lead** decides, and records why in the PR.

This is deliberately lightweight. Heavy process on a small project is how small
projects stall.

## The override authority

The governance [override](../50-governance/overrides.md) — merging ahead of a spec
change for a security fix or a broken bot — is the **lead's** by default, and any
maintainer's within their scope in a genuine emergency. Every use is recorded, per
that document; the authority to *use* it is defined here.

## Becoming a maintainer

By invitation from the lead, after sustained, high-quality contribution in an
area — enough that the existing maintainers would trust that person's review in
it. Adding someone is a change to `maintainers.toml` like any other: a PR, citing
this document, which regenerates the CODEOWNERS.

There is no application form. Contribute well in a domain, and the invitation
follows.

## Requirements

| ID | Requirement |
|----|-------------|
| **OPS-R16** | Maintainership MUST be defined in a single registry file, with entries scoped by repo and domain. |
| **OPS-R17** | Each repo's CODEOWNERS MUST be generated from the registry, never hand-edited. |
| **OPS-R18** | The override authority MUST rest with the lead by default, and with a maintainer within their scope in an emergency. |
| **OPS-R19** | Adding or changing a maintainer MUST be a change to the registry following the normal lifecycle. |

## Related

- [maintainers.toml](maintainers.toml) — the registry
- [50-governance/overrides.md](../50-governance/overrides.md) — the authority defined here, exercised there
- [project-workflow.md](project-workflow.md) — the review flow maintainers run
