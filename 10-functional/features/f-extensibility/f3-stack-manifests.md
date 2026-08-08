---
id: F3
title: Third-party stack manifests
kind: feature
area: F
audience: operator
status: draft
tracks: v2
milestone: M10
priority: P2
labels: [extensibility, verification, wiring]
relates: [F1, F2]
---

# F3 — Third-party stack manifests

**Status:** Draft · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Let the community contribute service definitions so lemonfiber can orchestrate and
verify stacks beyond the bundled media set — generalising the tool without turning
it into a code-execution vector. A contributed stack is declarative data, not a
program: a service fragment, the wiring to other services, and, uniquely, the
service's own declared verification probes. Because the manifest also declares the
proofs, verification itself becomes contributable — and a stack whose declared
proofs do not pass is simply not installed.

## Behaviour

### A contributed stack is declarative data

A manifest describes three things and nothing executable by default:

- **The service fragment** — the container/compose description of what runs.
- **The wiring** — how this service connects to the others in the stack.
- **The declared proofs** — the health and verification checks lemonfiber should
  run to decide whether this service is actually working, expressed as data the
  existing verification engine already knows how to run.

Because a manifest is readable data, a contribution reviews like any other diff:
a human reads what it declares, line by line, rather than auditing opaque code.

### Verification is contributable — and gating

This is the killer property. A manifest carries its *own* proofs, and lemonfiber's
existing verification engine runs them the same way it runs the bundled ones. A
manifest that declares proofs which do not pass is **not installed** — declaring a
check and failing it is a rejection, not a warning. Contributors extend not just
what the tool can run but what it can *prove*, and the proof is the acceptance
bar.

### It validates against a published schema before anything runs

Every manifest is validated against a published schema before lemonfiber acts on
it. A manifest that does not conform is rejected outright — it is never partially
applied and its declarations are never executed on the strength of hope. The
catalogue that serves manifests is community-owned and git-hosted, so provenance
and history are visible.

### The code escape hatch is reserved, opt-in, and sandboxed

Some logic pure data cannot express. For those rare cases a code escape hatch is
*reserved* — but it is opt-in, capability-restricted, sandboxed, and separately
vetted, never arbitrary native plugins and never executed by default. The default
posture is that a manifest is inert data; running any contributed logic is a
deliberate, separately-reviewed exception, not the norm.

### Supply chain is defended, not assumed

Trust in a contributed stack rests on stated mechanisms, not goodwill: schema
validation runs in the catalogue's CI so malformed or over-reaching manifests are
caught before merge; human review reads the diff; and images are signed and
pinned rather than floating on a mutable tag. An unpinned or unsigned image is a
finding, not a default-accept.

### Every step has a non-interactive equivalent

Fetching a manifest, validating it against the schema, and running its declared
proofs are all reachable as plain subcommands, so adding a community stack never
forces the wizard on a scripter.

## States

| State | Meaning |
|-------|---------|
| `schema-valid` | The manifest conforms to the published schema and may be considered |
| `schema-rejected` | The manifest fails schema validation; refused outright, nothing executed |
| `proofs-passing` | The manifest's declared proofs ran and passed; the stack is installable |
| `proofs-failing` | Declared proofs ran and did not pass; the manifest is not installed |
| `image-unpinned` | A referenced image is unsigned or floating on a mutable tag; flagged, not silently accepted |
| `code-escape-pending` | The manifest requests the sandboxed code escape hatch; held for separate opt-in vetting |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Malicious or broken manifest | Reject at schema validation; never execute contributed code by default, whatever the manifest claims about itself. |
| Manifest declares proofs that fail | Do not install it; a declared-but-failing proof is a rejection, not an advisory. |
| Manifest references an unpinned or untrusted image | Flag the image as unpinned/unsigned and refuse to treat it as trusted; pinning and signing are the bar. |
| Manifest over-reaches what it may touch | Confine it to what its declared wiring and capabilities permit; an over-reaching manifest is rejected, not accommodated. |
| Manifest requests the code escape hatch | Route to the sandboxed, capability-restricted, opt-in path with separate vetting; never run it inline as ordinary data. |
| Catalogue itself is untrusted or unsigned | Trust flows from a signed, git-hosted, community-owned catalogue; an unverifiable source is treated as untrusted. |
| Manifest's declared proof cannot run at all | Report it as unproven rather than passed; an unrunnable check is not a satisfied one. |
| A manifest conflicts with a bundled service's wiring | Surface the conflict at validation; do not silently override the bundled topology. |
| Schema evolves after a manifest was written | Validate against the published schema version; a manifest that no longer conforms is rejected until updated. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F3-R1** | A contributed stack MUST be expressed as declarative data — a service fragment, its wiring, and its declared verification probes — not as executable code. |
| **F3-R2** | Every manifest MUST be validated against a published schema before lemonfiber acts on it, and a non-conforming manifest MUST be rejected outright. |
| **F3-R3** | A manifest's own declared proofs MUST be runnable by the existing verification engine, the same way the bundled proofs are run. |
| **F3-R4** | A manifest whose declared proofs do not pass MUST NOT be installed. |
| **F3-R5** | A declared proof that cannot be run MUST be reported as unproven and MUST NOT be treated as passed. |
| **F3-R6** | Contributed code MUST NOT be executed by default; any code path MUST be opt-in, capability-restricted, sandboxed, and separately vetted. |
| **F3-R7** | Arbitrary native plugins MUST NOT be a supported extension mechanism. |
| **F3-R8** | Referenced images MUST be signed and pinned; an unpinned or unsigned image MUST be flagged rather than silently accepted. |
| **F3-R9** | The manifest schema MUST be validated in the catalogue's CI so malformed contributions are caught before merge. |
| **F3-R10** | A contributed manifest MUST review as a readable diff, with no opaque or obfuscated content required to understand what it does. |
| **F3-R11** | A manifest MUST NOT reach beyond what its declared wiring and capabilities permit, and one that over-reaches MUST be rejected. |
| **F3-R12** | The manifest catalogue MUST be community-owned and git-hosted, with provenance verifiable rather than taken on trust. |
| **F3-R13** | Fetching a manifest, validating it against the schema, and running its declared proofs MUST each be reachable non-interactively. |
| **F3-R14** | A manifest that conflicts with the bundled topology MUST surface the conflict at validation rather than silently overriding it. |

## Related

- [F1 Customisation & escape hatches](f1-customisation.md) — the escape-hatch posture this narrows to declarative data
- [F2 Service catalogue](f2-service-catalogue.md) — the bundled catalogue this generalises to community stacks
- [C2 VPN verification](../c-trust/c2-vpn-verification.md) — the verification engine that runs a manifest's declared proofs
