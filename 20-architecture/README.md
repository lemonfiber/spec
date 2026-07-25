# Architecture

**Status:** Accepted

How the system is put together, and why each structural choice is the one the
requirements demand.

---

## The rule this section is held to

**Every architectural decision here cites a requirement it satisfies.** A
technical choice justified by nothing is unjustified, and should be challenged in
review.

This is the practical form of writing the functional spec first: architecture is
written *against* [10-functional](../10-functional/), not alongside it. Where a
decision has no requirement behind it, one of two things is true — the
requirement is missing, or the decision is unnecessary. Both are worth finding.

## Contents

| Doc | Covers |
|-----|--------|
| [system-context.md](system-context.md) | What's inside, what's outside, trust zones, what crosses the boundary |
| [component-model.md](component-model.md) | Crate layout, the core/UI boundary, Docker access split, async model |
| [data-flow.md](data-flow.md) | Content pipeline, control flow, observation, seeding |
| [platform-matrix.md](platform-matrix.md) | The five cross-platform differences that actually bite |
| [contracts/stack-manifest.md](contracts/stack-manifest.md) | **`stack.toml`** — the lemonfiber ↔ media-stack interface, full schema |
| [contracts/versioning.md](contracts/versioning.md) | Three version identifiers, compatibility, where skew is caught |

## The `ARCH-R` namespace

Architectural requirements use `ARCH-R##`, alongside feature requirements
(`A2-R4`), governance rules (`GOV-R12`) and quality rules (`Q-R3`).

They exist because some obligations are structural rather than behavioural.
*"`lemonfiber-core` must not depend on any UI crate"* is not something a user
observes — but it's what makes *"surfaces are renderings, never capabilities"*
([G1-R2](../10-functional/features/g-ux/g1-interface-tiers.md)) true rather than
merely intended.

## The four structural decisions

Everything else follows from these:

### 1. Compose is the execution engine

Profiles are a Compose concept, and partial stacks are the product's core
proposition. Reimplementing them against the raw Docker API would mean
reimplementing Compose — and would break the guarantee that the stack runs
without lemonfiber at all.
→ [ADR-0001](../00-overview/decisions/0001-docker-compose-as-engine.md)

### 2. Reads and writes take different paths

Writes go through `docker compose` because profiles live there. Reads go through
the Docker API because a 1 Hz dashboard across 19 services cannot afford process
spawns. Neither path can serve both jobs.
→ [ADR-0008](../00-overview/decisions/0008-hybrid-docker-access.md)

### 3. The stack is data, not code

Services, profiles and forms are declared in `stack.toml`. Adding a service is a
data change with no Rust edit and no release — which is also what makes
third-party stacks possible.
→ [ADR-0002](../00-overview/decisions/0002-profiles-and-forms.md) ·
[stack-manifest](contracts/stack-manifest.md)

### 4. Logic cannot render

`lemonfiber-core` has no UI dependency of any kind. A surface cannot grow
behaviour of its own, because behaviour lives somewhere that cannot print.
→ [component-model](component-model.md#the-one-boundary-that-matters)

## Reading order

- **Implementing across the seam** → [stack-manifest](contracts/stack-manifest.md) → [versioning](contracts/versioning.md)
- **Working inside `lemonfiber`** → [component-model](component-model.md) → [data-flow](data-flow.md)
- **Chasing a platform bug** → [platform-matrix](platform-matrix.md)
- **Orienting** → [system-context](system-context.md)

## Related

- [00-overview/decisions](../00-overview/decisions/) — the contested choices
- [30-repos](../30-repos/) — per-repo detail below this level
- [40-quality](../40-quality/) — how the code is written
