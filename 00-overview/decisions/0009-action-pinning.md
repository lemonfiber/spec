# ADR-0009: First-party workflows on `@main`, third-party actions SHA-pinned

**Status:** Accepted
**Date:** 2026-07-24

## Context

The project uses GitHub Actions heavily: reusable workflows **we own** (in the
spec repo — `spec-check`, `hygiene`, `security`, `dco`, `commitlint`, `labeler`,
`stale`) called by every repo, and **third-party** actions inside them
(`actions/checkout`, `ossf/scorecard-action`, `gitleaks/gitleaks-action`, …).

Supply-chain hygiene says pin actions to an immutable commit SHA, not a moving tag
or branch — a tag can be repointed at malicious code. An automated security review
flagged our `@main` references for exactly this.

But our reusable workflows are referenced as `lemonfiber/spec/...@main` **on
purpose**: `@main` is the anti-drift mechanism ([ADR-0002 is the analog for the
stack](0002-profiles-and-forms.md); the reusable-workflow model is described in
[cross-repo-ci](../../50-governance/cross-repo-ci.md)). Pinning those to a SHA
would mean every workflow change requires updating the SHA in six repos — the
exact drift the single-definition model removes.

So the two cases have opposite correct answers, and the decision is to treat them
differently rather than apply one rule to both.

## Decision

| Reference | Pinning | Why |
|-----------|---------|-----|
| **Our own reusable workflows** (`lemonfiber/spec/.github/workflows/*@…`) | **`@main`** | Anti-drift: one definition, followed live. The "risk" is us changing our own workflow, which governance already gates. |
| **Third-party actions** (everything else) | **SHA-pinned, at the latest release**, with the version in a trailing comment | Immutable and current. `# v7` documents what the SHA is. |

Kept current by **Renovate**, configured to update action digests — so the SHAs
stay at the latest release automatically, as PRs that pass CI, rather than rotting.
"Secure **and** current" rather than a trade-off.

Rolling refs that have no releases (`dtolnay/rust-toolchain@stable`,
`taiki-e/install-action@<tool>`) keep their semantic ref but are pinned to its
current SHA; Renovate advances them too.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Pin everything, including our reusables** | Reintroduces the drift the single-definition model exists to remove; a spec workflow fix becomes six SHA-bump PRs. |
| **Pin nothing (tags/branches everywhere)** | The supply-chain risk the review flagged; a repointed third-party tag runs arbitrary code in CI. |
| **Pin our reusables to a spec release tag** | Better than `@main` in theory, but the spec isn't released on a cadence, and it still couples every consumer to a version bump. Revisit if the spec starts tagging releases. |

## Consequences

### Positive
- Third-party actions are immutable and auditable; OpenSSF Scorecard's
  pinned-dependencies check passes.
- Our shared CI still has one definition, changed in one place.
- Renovate keeps the pins at latest, so "pinned" doesn't mean "stale".

### Negative
- Two mental models for `uses:` refs. Mitigated: the rule is simple (ours =
  `@main`, theirs = SHA) and this ADR records why.
- A malicious change to *our own* `@main` workflow would propagate immediately.
  Accepted: it's our repo under our branch protection and signing; the same trust
  we place in the spec itself.

## Revisit if

- The spec repo starts cutting releases on a cadence — then pinning reusables to a
  release tag beats `@main`.
- GitHub ships first-class immutable-yet-followable reusable-workflow refs.

## Related

- [50-governance/cross-repo-ci.md](../../50-governance/cross-repo-ci.md) — the reusable-workflow model
- [40-quality/tooling.md](../../40-quality/tooling.md) — Renovate, Scorecard
- [70-operations/setup-registry.md](../../70-operations/setup-registry.md) — Renovate app install
