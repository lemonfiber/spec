# Sign-off & inbound licensing

**Status:** Accepted

Every contribution is signed off, and every contribution is made under the repo's
own licence. This page states both, because a public project under a **non-OSI**
licence needs its inbound terms to be unambiguous.

---

## Inbound = outbound

Contributions are licensed under the **same licence as the repo they land in** —
[Hippocratic 3.0](../90-appendix/license-rationale.md) for code, CC BY-SA 4.0 for
docs, the split for `brand`. By opening a PR you agree your contribution is
provided under that licence.

There is **no CLA** (no copyright assignment). You keep your copyright; you licence
the contribution inbound on the same terms the project ships outbound. This is the
lightest arrangement that keeps the licensing coherent, and the one most OSS
projects use.

Because the licence is ethical-source rather than OSI-approved, this is stated
explicitly rather than assumed: a contributor should know, before contributing,
that their work ships under Hippocratic 3.0.

## The Developer Certificate of Origin

Every commit carries a **DCO sign-off** — a `Signed-off-by` line asserting you
have the right to submit the work under the project's licence:

```
Signed-off-by: Wessel Verheij <info@nightworks.io>
```

Added automatically with `git commit -s`. It is the
[Developer Certificate of Origin 1.1](https://developercertificate.org/) — a
lightweight, well-understood assertion, not a contract you sign.

### Why DCO and not a CLA

A CLA asks contributors to assign or broadly licence rights, needs storage and
tracking, and deters casual contributors. The DCO asserts the one thing that
matters — *"I wrote this, or have the right to submit it, under this licence"* —
with a single trailer and no paperwork. For a project this size it is the right
weight.

### Enforcement

A `dco` check runs on every PR ([project-workflow](../70-operations/project-workflow.md))
and fails if any commit lacks a valid `Signed-off-by` matching its author. Like
`spec-check`, it closes the gap between a documented rule and an enforced one.

The sign-off is **separate from the cryptographic signature**: signing
([required on `main`](../70-operations/setup-registry.md)) proves *who* authored
the commit; the DCO asserts they had the *right* to contribute it. A commit needs
both.

## Interaction with the canonical-spec rule

Sign-off is orthogonal to citation. A PR must both cite a spec identifier
([GOV-R2](canonical-spec.md)) **and** be signed off. Neither substitutes for the
other.

## Requirements

| ID | Requirement |
|----|-------------|
| **GOV-R28** | Contributions MUST be licensed inbound under the same licence as the repo they land in; there MUST be no CLA or copyright assignment. |
| **GOV-R29** | Every human commit MUST carry a valid DCO `Signed-off-by` line matching its author. Merge commits and bot-authored commits are exempt — GitHub authors them, so there is no human to attest. |
| **GOV-R30** | A `dco` check MUST run on every PR and MUST fail when any non-exempt commit lacks a valid sign-off. |
| **GOV-R31** | The inbound licensing terms MUST be stated explicitly, given the licence is not OSI-approved. |

## Related

- [contributing.md](contributing.md) — the contributor flow, including `-s`
- [90-appendix/license-rationale.md](../90-appendix/license-rationale.md) — the licence itself
- [70-operations/project-workflow.md](../70-operations/project-workflow.md) — the DCO check
- [70-operations/setup-registry.md](../70-operations/setup-registry.md) — signing setup
