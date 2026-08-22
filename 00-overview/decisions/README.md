# Architecture Decision Records

**Status:** Accepted

An ADR captures a decision that was *contested* — where a reasonable engineer
could have chosen otherwise. It records the alternatives and why they lost, so
that revisiting the decision later starts from evidence rather than from scratch.

## Rules

1. **ADRs are immutable once Accepted.** To change a decision, write a new ADR
   that supersedes the old one and link both ways. The record of changing your
   mind is the valuable part.
2. **Only genuinely contested decisions get an ADR.** "We use `serde` for JSON"
   is not a decision, it's a default.
3. Numbers are permanent and never reused.

## Index

| # | Decision | Status |
|---|----------|--------|
| [0001](0001-docker-compose-as-engine.md) | Docker Compose as the execution engine | Accepted |
| [0002](0002-profiles-and-forms.md) | Profiles are facts; forms are intent | Accepted |
| [0003](0003-rust-ratatui-for-cli.md) | Rust + Ratatui for the CLI/TUI | Accepted |
| [0004](0004-four-repo-split.md) | Four repos rather than a monorepo | Accepted |
| [0005](0005-embedded-stack-assets.md) | lemonfiber embeds the stack at build time | Accepted |
| [0006](0006-single-data-mount.md) | One `/data` mount, subdirectories beneath | Accepted |
| [0007](0007-dual-mode-jellyfin.md) | Jellyfin supports both Docker and native | Accepted |
| [0008](0008-hybrid-docker-access.md) | Compose CLI for writes, Docker API for reads | Accepted |
| [0009](0009-action-pinning.md) | First-party workflows on @main, third-party actions SHA-pinned | Accepted |
| [0010](0010-engine-abstraction-for-v2.md) | A container engine is a v2 detail, not a v1 assumption | Proposed |
| [0011](0011-web-surface-as-a-fifth-repo.md) | The web surface is a fifth repo behind the JSON contract | Proposed |

> **Not here:** licensing. It's a project-governance choice, not an
> architectural one — no component's design depends on it. See
> [licence rationale](../../90-appendix/license-rationale.md).

## Template

```markdown
# ADR-NNNN: <title>

**Status:** Proposed | Accepted | Superseded by ADR-NNNN
**Date:** YYYY-MM-DD

## Context
What forces are at play? What makes this non-obvious?

## Decision
What we're doing, stated plainly.

## Alternatives considered
| Option | Why it lost |

## Consequences
### Positive
### Negative
### Neutral

## Revisit if
Concrete conditions that would justify a new ADR.
```
