---
id: L2
title: v2 release
kind: feature
area: L
audience: operator
status: accepted
tracks: v2
priority: P1
labels: [release, verification]
---

# L2 — v2 release

**Status:** Accepted · **Audience:** Operator · **Area:** L — Release & distribution

---

## Purpose

Ship the ecosystem to the same bar the product was shipped at. `2.0.0` closes the
v2 epoch the way [L1](l1-release-engineering.md) closed v1: not a summary of the
minors that delivered the ecosystem features, but the release *of that epoch* —
the v2 surface distributed, verified, and upgradable, through the one pipeline
that already exists rather than a second one built alongside it.

## Behaviour

### One pipeline, not two

The v2 features MUST ship through the same signed, multi-platform pipeline as v1
([L1](l1-release-engineering.md)) — the same artifacts, signatures, tap, and
installers — rather than a separate distribution path. A second pipeline is a
second thing to keep honest; there is one.

### The same bar, applied to the ecosystem

Every v2 feature MUST be installable and runnable on macOS, Linux, and Windows to
the same standard v1 was held to: run-tested on each platform, not merely
compiled, and documented on the site generated from this specification.

### A tested upgrade, not a reinstall

An operator on a v1 release MUST be able to upgrade to `2.0.0` without losing what
they configured. The upgrade MUST be tested and MUST preserve the operator's
configuration and data, so moving to the ecosystem epoch is a step forward rather
than a fresh start.

### The epoch it closes

`2.0.0` closes the v2 epoch, and a major ships no stubs: it MUST NOT be cut while
any `tracks: v2` feature is not both Accepted and implemented. The completeness
bar, not a per-feature goal list, is what a major satisfies
([OPS-R54](../../../70-operations/staging.md)).

## Edge cases

| Situation | Expected behaviour |
|-----------|--------------------|
| A v2 feature runs on two platforms but not the third | The release MUST be blocked until it runs on all three, not shipped as mostly working. |
| An upgrade from v1 would drop configuration or data | The upgrade MUST be corrected or blocked, never allowed to lose the operator's state silently. |
| A v2 feature is Accepted but not yet implemented | `2.0.0` MUST NOT ship; the completeness bar is unmet. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **L2-R1** | The v2 features MUST ship through the same signed, multi-platform pipeline as v1, not a separate distribution path. |
| **L2-R2** | Every v2 feature MUST be installed and run — not merely compiled — on macOS, Linux, and Windows before `2.0.0` ships. |
| **L2-R3** | The documentation site and the installers MUST cover the v2 features. |
| **L2-R4** | An upgrade from a v1 release to `2.0.0` MUST be tested and MUST preserve the operator's configuration and data. |
| **L2-R5** | The release pipeline MUST be reachable non-interactively, with no manual step beyond authorisation required to cut the release. |
| **L2-R6** | `2.0.0` MUST NOT be cut while any `tracks: v2` feature is not both Accepted and implemented — the epoch-completeness bar ([OPS-R54](../../../70-operations/staging.md)). |

## Related

- [L1 v1 release engineering](l1-release-engineering.md) — the pipeline this reuses rather than rebuilds
- [OPS-R54 Epoch completeness](../../../70-operations/staging.md) — the no-stub-major bar `2.0.0` must clear
- [A5 Migration](../a-getting-started/a5-migration.md) — the state an upgrade must preserve
