---
id: F1
title: Customisation & escape hatches
kind: feature
area: F
audience: operator
status: accepted
tracks: v1
labels: [extensibility]
depends: [C9, F2]
---

# F1 — Customisation & escape hatches

**Status:** Accepted · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Let an experienced operator change anything, and guarantee that lemonfiber is
never the thing standing between them and their stack.

This audience matters disproportionately. They're the ones who evaluate the
project publicly, who answer questions in forums, and whose objection — *"it
hides what's actually happening"* — kills adoption among exactly the people
newcomers ask for advice.

They are also right to be suspicious. A tool that wraps a system in an opaque
layer, then breaks or is abandoned, leaves its users with something they cannot
operate.

## Behaviour

### The stack runs without lemonfiber

`media-stack` is a real Compose project. Clone it, set a few variables, run
`docker compose --profile tv up`, and it works with no Rust binary anywhere
([ADR-0001](../../../00-overview/decisions/0001-docker-compose-as-engine.md)).

This is the load-bearing guarantee. Everything else in this feature is
convenience; this is the property that makes adopting lemonfiber a low-risk
decision, because abandoning it is always possible.

### Every command shows its work

`--dry-run` prints the exact underlying invocation without executing it. Nothing
is generated that the operator cannot read.

### A local stack can be substituted wholesale

`--stack-dir` points at a fork ([ADR-0005](../../../00-overview/decisions/0005-embedded-stack-assets.md)).
The operator maintains their own compose file and manifest; lemonfiber operates
it, validating only the manifest contract.

### Materialised files are editable and respected

Files lemonfiber writes may be edited directly. Modifications are detected by
content and never silently overwritten on upgrade — the operator is shown a diff
and chooses ([C9](../c-trust/c9-drift.md)).

### Adding a service requires no Rust

A new service is a compose entry plus a manifest entry plus inclusion in whichever
forms should carry it. No lemonfiber change, no release
([ADR-0002](../../../00-overview/decisions/0002-profiles-and-forms.md)).

### Everything interactive is also non-interactive

Every action available in the TUI or web UI has a flag-driven equivalent that
runs unattended and exits with a meaningful status. This is what makes lemonfiber
scriptable, and what stops the friendly interface from becoming a cage.

### Opting out of a managed area is supported

An operator can declare a service, or a specific configuration area, unmanaged.
lemonfiber then reports its state but never writes to it — and stops reporting
drift for it.

## States

Per managed area:

| State | Meaning |
|-------|---------|
| `managed` | lemonfiber maintains it |
| `modified` | Locally edited; preserved, reported |
| `unmanaged` | Operator opted out; observed only |
| `forked` | Operating from an external stack directory |
| `contract-invalid` | External stack fails manifest validation |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Forked stack fails manifest validation | Refuse with the specific violation and location named — not "invalid manifest". |
| Forked stack uses an unsupported schema version | Refuse, naming both versions ([versioning contract](../../../20-architecture/contracts/versioning.md)). |
| Operator adds a service lemonfiber doesn't know | Lifecycle and status work generically. Features needing specific knowledge — seeding, queue health — report as unsupported for that service rather than failing. |
| Operator removes a service lemonfiber depends on | Report which features become unavailable; don't refuse. |
| Edited file conflicts with an upgrade | Show a diff; the operator chooses. Never auto-merge. |
| Operator wants lemonfiber to stop managing everything | Supported — a fully unmanaged stack that lemonfiber only observes. |
| Fork diverges far from the manifest contract | Validation reports every violation at once, not one per run. |
| Operator scripting against output | Machine-readable output is a stable interface and MUST be versioned. |
| Compose file edited to break the single-mount rule | Report the consequence ([C5](../c-trust/c5-storage.md)); do not refuse. It's their system. |
| Operator wants to run two stacks on one host | Supported via distinct project names and non-overlapping ports; port conflicts detected. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F1-R1** | The stack MUST be fully operable with plain `docker compose` and no lemonfiber binary. |
| **F1-R2** | Every command MUST support a dry-run mode printing the exact underlying invocation. |
| **F1-R3** | An external stack directory MUST be usable in place of the embedded stack. |
| **F1-R4** | Locally modified materialised files MUST be detected by content and MUST NOT be overwritten without a diff and confirmation. |
| **F1-R5** | Adding a service to the stack MUST NOT require a lemonfiber code change or release. |
| **F1-R6** | Every interactive action MUST have a non-interactive equivalent with a meaningful exit status. |
| **F1-R7** | Services and configuration areas MUST be markable as unmanaged, after which lemonfiber MUST observe but never write. |
| **F1-R8** | Unmanaged areas MUST NOT be reported as drift. |
| **F1-R9** | Manifest validation failures MUST name the specific violation and its location, and MUST report all violations in one pass. |
| **F1-R10** | An unknown service MUST still support generic lifecycle and status operations. |
| **F1-R11** | Features requiring service-specific knowledge MUST report unsupported for unknown services rather than failing. |
| **F1-R12** | Machine-readable output MUST be a versioned, stable interface. |
| **F1-R13** | A configuration violating internal guidance MUST be reported with its consequence, and MUST NOT be refused. |
| **F1-R14** | Multiple independent stacks MUST be supportable on one host, with port conflicts detected. |

## Related

- [ADR-0001 Compose as engine](../../../00-overview/decisions/0001-docker-compose-as-engine.md)
- [ADR-0002 Profiles and forms](../../../00-overview/decisions/0002-profiles-and-forms.md)
- [ADR-0005 Embedded stack assets](../../../00-overview/decisions/0005-embedded-stack-assets.md)
- [C9 Drift detection](../c-trust/c9-drift.md) — how edits are protected
- [F2 Service catalogue](f2-service-catalogue.md) · [J8 Customising](../../journeys/j8-customising.md)
