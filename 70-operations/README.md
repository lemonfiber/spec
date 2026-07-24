# Operations

**Status:** Accepted

How the **project** is run day to day, across all repos — releasing, the one-time
setup a maintainer needs, the branching and label conventions, issue automation,
and who maintains what.

This is distinct from [50-governance](../50-governance/), which defines *how a
change is decided and gated* (the canonical-spec rule). Operations is the
*mechanics*: cut a release, set up the org, name a branch, triage an issue.

---

## Contents

| Doc | Covers |
|-----|--------|
| [releasing.md](releasing.md) | The release process — tag → build → publish → formula → changelog → docs |
| [setup-registry.md](setup-registry.md) | Every one-time manual step to operate the org — secrets, apps, protections |
| [project-workflow.md](project-workflow.md) | Branching model, the canonical label set, milestones, issue automation |
| [notifications.md](notifications.md) | Discord release/build/maintainer automation and the maintainer action queue |
| [maintainers.md](maintainers.md) | Roles, decision-making, and the single maintainers registry that CODEOWNERS derives from |

## The `OPS-R` namespace

Operations requirements use `OPS-R##` — the seventh namespace, alongside feature
(`A2-R4`), `GOV-R`, `ARCH-R`, `REPO-R`, `Q-R`, `DES-R`. They cover obligations
about running the project rather than the product's behaviour or the code's
quality.

## Why this is its own section

Releasing, branching and maintainer policy are neither *product* (10-functional),
*architecture* (20), *code quality* (40), nor *the rule of change* (50). They're
the project's operational surface, and a public project lives or dies on whether
that surface is clear. Folding release engineering into "quality" undersold it;
it has its own home here.

## Related

- [50-governance](../50-governance/) — the rules of change these mechanics serve
- [20-architecture/contracts/versioning.md](../20-architecture/contracts/versioning.md) — the version model releasing applies
- [40-quality/ci-cd.md](../40-quality/ci-cd.md) · [tooling.md](../40-quality/tooling.md) — the pipeline and tools
- The [`.github` repo](../30-repos/README.md) — where org-wide templates and automation live
