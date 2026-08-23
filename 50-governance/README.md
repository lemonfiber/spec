# Governance

**Status:** Accepted

How change enters the lemonfiber org, and why the rules are shaped this way.

This section is **binding on every repo in the org**, including this one. It is not
advice.

---

## The constitutional rule

> **The spec is canonical. No change lands in `lemonfiber`, `media-stack` or
> `homebrew-tap` unless it references something in this repository, and that
> reference already exists on `main` here.**

Everything else in this section follows from that sentence.

## Why

A specification that trails its implementation is not a specification — it's
documentation, and stale documentation at that. The failure is gradual and
familiar: code ships, the spec is updated "later", later doesn't come, and within
a few months the spec describes a system nobody is running. At that point it
actively misleads, and the rational response is to stop reading it — which is the
end of it having any authority at all.

The rule exists to make that decay impossible rather than merely discouraged.
Enforcement is mechanical because the alternative — good intentions under
deadline pressure — is exactly what fails.

There's a second benefit, and it may matter more: **being required to write the
spec change first forces the thinking to happen before the code.** Several
decisions in this specification only became visible while writing them down —
the drift-versus-reproducibility conflict ([C9](../10-functional/features/c-trust/c9-drift.md)),
the two-tier binding policy, the fact that most VPN providers cannot port-forward.
None of those would have surfaced while writing an implementation.

## Contents

| Doc | Covers |
|-----|--------|
| [canonical-spec.md](canonical-spec.md) | What "canonical" means; the `GOV-R` requirement namespace; scope |
| [change-lifecycle.md](change-lifecycle.md) | Spec PR first, then implementation. The ordering that makes it real. |
| [cross-repo-ci.md](cross-repo-ci.md) | What the bot verifies, and what it does when a PR doesn't conform |
| [contributing.md](contributing.md) | The human-facing guide — what to do, in order |
| [ai-contributors.md](ai-contributors.md) | The canonical rules for AI agents — referenced by every repo's `AGENTS.md` |
| [dco.md](dco.md) | Sign-off (DCO) and inbound=outbound licensing |
| [overrides.md](overrides.md) | The maintainer override, its audit trail, and when it's legitimate |
| [issue-routing.md](issue-routing.md) | Which repo an issue belongs in, and how it moves |
| [rfc-process.md](rfc-process.md) | The community RFC flow — issue as source of truth, maintainer approval, auto-scaffolded Draft PR |

## The two reference paths

Spec references appear in exactly two places, and **never in code comments**:

```
  commit / PR body  ──cites──▶  spec requirement ID
                                      ▲
  source code  ──links──▶  lemonfiber/.docs/ ─┘
```

1. **Commits and PRs** cite requirement IDs directly. This is provenance for the
   change.
2. **Code** links to `lemonfiber/.docs/` pages; those pages cite requirement IDs. This is
   documentation of the system.

Code comments carry **no requirement IDs, no ticket references, no phase
numbers** — see the [comment policy](../40-quality/code-comments.md). Provenance
in a comment rots the moment the artefact it names is superseded, and the next
reader gains nothing from it.

## What this section does not do

It governs *how* change enters, not *what* is correct. Technical standards live
in [40-quality](../40-quality/); what the product should do lives in
[10-functional](../10-functional/).
