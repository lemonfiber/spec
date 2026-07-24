# ADR-0009: Pin every action to a SHA, including our own reusables

**Status:** Accepted
**Date:** 2026-07-25

## Context

The project uses GitHub Actions heavily: reusable workflows **we own** (in the
spec repo — `spec-check`, `hygiene`, `security`, `dco`, `commitlint`, `labeler`,
`stale`, `discord-notify`, `label-sync`) called by every repo, and **third-party**
actions inside them (`actions/checkout`, `ossf/scorecard-action`, …).

Supply-chain hygiene says pin actions to an immutable commit SHA, not a moving tag
or branch — either can be repointed at malicious code. **SonarCloud** (on every
repo) flags an unpinned `uses:` as a MAJOR vulnerability that fails its
Security-Rating gate; **OpenSSF Scorecard** flags the same under
Pinned-Dependencies.

It is tempting to exempt our **own** reusables and keep them on `@main` as an
anti-drift mechanism — one definition, followed live. But a `@main` ref is
mutable: whoever can move `main` changes what every consumer runs, unreviewed at
the consumer. That is exactly the supply-chain surface pinning removes, and it
applies to our own repo as much as anyone's. The anti-drift benefit is preserved a
different way — by **Renovate**, which advances pinned digests as reviewable,
CI-gated PRs.

## Decision

**Pin every `uses:` reference to an immutable commit SHA, with a trailing `# <ref>`
comment — our own reusables included.** No `@main`, `@v3`, or other moving ref in
any `uses:`.

```yaml
uses: lemonfiber/spec/.github/workflows/spec-check.yml@4eb85bd… # main
uses: actions/checkout@3d3c42e5… # v7.0.1
```

Renovate keeps the digests at the latest of their tracked ref, so "pinned" never
means "stale". The single-definition model is preserved — there is still one
`spec-check.yml` — only the *reference* is now immutable and advanced by a bot PR
that runs the consumer's CI first, instead of silently.

Rolling refs that have no releases (`dtolnay/rust-toolchain@stable`,
`taiki-e/install-action@<tool>`) keep their semantic ref but are pinned to its
current SHA; Renovate advances them too.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Exempt our reusables, keep them on `@main`** | Two scanners flag it, and a mutable ref is a real supply-chain surface even for our own repo; Renovate already solves the drift it was meant to avoid. |
| **Pin nothing (tags/branches everywhere)** | The supply-chain risk itself — a repointed tag or branch runs arbitrary code in CI. |
| **Pin our reusables to a spec release tag** | The spec isn't released on a cadence; a SHA + Renovate gives the same immutability without inventing a release train. Revisit if the spec starts tagging. |

## Consequences

### Positive

- One rule for every `uses:` ref — no exceptions to remember.
- SonarCloud Security Rating and OpenSSF Pinned-Dependencies both pass; no mutable
  supply-chain surface anywhere.
- A change to a shared reusable reaches consumers as a Renovate PR that runs their
  CI first, rather than landing unreviewed.

### Negative

- A shared-workflow change is not picked up by consumers until Renovate bumps the
  digest (hours), versus instantly under `@main`. Accepted: the delay buys a
  reviewable, CI-gated propagation, and an urgent change can be bumped by hand.
- More digest-bump PRs. Mitigated: Renovate groups them.

## Related

- [50-governance/cross-repo-ci.md](../../50-governance/cross-repo-ci.md) — the reusable-workflow model
- [40-quality/tooling.md](../../40-quality/tooling.md) — Renovate, Scorecard, SonarCloud
- [70-operations/setup-registry.md](../../70-operations/setup-registry.md) — Renovate app install
