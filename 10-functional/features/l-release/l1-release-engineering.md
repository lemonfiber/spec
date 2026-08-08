---
id: L1
title: v1 release engineering
kind: feature
area: L
audience: operator
status: accepted
tracks: v1
milestone: M6
priority: P1
labels: [release, cli, verification]
---

# L1 — v1 release engineering

**Status:** Accepted · **Audience:** Operator · **Area:** L — Release & distribution

---

## Purpose

Turn the built product into something a stranger can install and run. Every v1
feature is delivered in a minor release; `1.0.0` is the release *of the product
itself* — signed, cross-platform artifacts, the paths people actually install
through, and the proof that they work on a machine that is not a contributor's.
It is the one version whose deliverable is the distribution rather than a
feature, so it carries its own scope rather than standing in for the minors that
came before it.

## Behaviour

### Signed, multi-platform artifacts

Every release MUST produce artifacts for macOS (arm64 and x86_64), Linux (gnu and
musl), and Windows, built by the release pipeline rather than by hand. Each
artifact MUST carry a checksum and a verifiable signature, so an operator can
confirm that what they downloaded is what was published and not something
substituted in transit.

### The paths people install through

A binary in a release page is not a distribution. The tool MUST be installable
the ways its audience already installs things: a Homebrew tap, published
automatically by CI so it is never a manual step that drifts; and one-line
installers for shell (`curl … | sh`) and PowerShell (`irm … | iex`) that fetch,
verify, and place the binary. An installer MUST refuse an artifact whose signature
does not verify rather than run it anyway.

### Proven on a machine that is not a contributor's

Compiling is not running. Each release MUST be exercised — installed and run, not
merely built — on macOS, Linux, and Windows before it ships, so a platform-specific
break is caught before an operator meets it rather than after.

### Documentation that ships with the release

A documentation site MUST be generated from this specification and published with
each release, so the docs describe the version in hand and cannot drift from it.

### The epoch it closes

`1.0.0` closes the v1 epoch, and a major ships no stubs: it MUST NOT be cut while
any `tracks: v1` feature is not both Accepted and implemented. The completeness
bar, not a per-feature goal list, is what a major satisfies
([OPS-R54](../../../70-operations/staging.md)).

## Edge cases

| Situation | Expected behaviour |
|-----------|--------------------|
| A downloaded artifact's signature does not verify | The installer MUST refuse it and say why, rather than installing an unverified binary. |
| A platform compiles but fails to run | The release MUST be blocked by the run-test, not shipped on the strength of a green compile. |
| The Homebrew tap publish fails mid-release | The release MUST surface the failure rather than record a partial publish as done. |
| A v1 feature is Accepted but not yet implemented | `1.0.0` MUST NOT ship; the completeness bar is unmet. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **L1-R1** | Each release MUST produce artifacts for macOS (arm64, x86_64), Linux (gnu, musl), and Windows, built by the release pipeline rather than by hand. |
| **L1-R2** | Every release artifact MUST carry a checksum and a verifiable signature. |
| **L1-R3** | A Homebrew tap MUST be published automatically by CI on each release, with no manual step. |
| **L1-R4** | One-line installers MUST be provided for shell (`curl … \| sh`) and PowerShell (`irm … \| iex`), and each MUST verify an artifact's signature before placing it. |
| **L1-R5** | An installer MUST refuse an artifact whose signature does not verify rather than run it. |
| **L1-R6** | Each release MUST be installed and run — not merely compiled — on macOS, Linux, and Windows before it ships. |
| **L1-R7** | A documentation site MUST be generated from this specification and published with each release. |
| **L1-R8** | A non-contributor MUST be able to install and run lemonfiber on all three platforms following only the README. |
| **L1-R9** | The release pipeline MUST be reachable non-interactively, with no manual step beyond authorisation required to cut a release. |
| **L1-R10** | `1.0.0` MUST open the dashboard on a bare invocation — the capability the v1 epoch builds toward — and MUST NOT be cut while any `tracks: v1` feature is not both Accepted and implemented. |

## Related

- [OPS-R54 Epoch completeness](../../../70-operations/staging.md) — the no-stub-major bar `1.0.0` must clear
- [A2 Setup wizard](../a-getting-started/a2-setup-wizard.md) — what the operator reaches once installed
- [L2 v2 release](l2-v2-release.md) — the same discipline applied when the v2 epoch closes
