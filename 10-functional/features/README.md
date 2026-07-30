# Feature catalogue

**Status:** Accepted

**v1** is 47 features across seven areas (A–G) — the contract the technical spec
is written against, where every architecture and implementation decision must
trace to a feature requirement here, not the other way round. **v2 — the
ecosystem epoch** — adds four areas (H–K) plus F3, each tagged `tracks: v2`;
those features are catalogued below the v1 areas and ship after 1.0.

## How to read a feature doc

Each follows the same shape:

| Section | Contains |
|---------|----------|
| **Purpose** | What problem it solves, for whom. One paragraph. |
| **Behaviour** | What the user sees and does. Functional only — no crates, no env vars, no module names. |
| **States** | The states it can be in and what moves between them. |
| **Edge cases** | What happens when it goes wrong. Usually the longest section, deliberately. |
| **Acceptance criteria** | Numbered, testable, RFC 2119. `A1-R1`, `A1-R2`, … |

### Requirement IDs

Requirements live **inside** their feature — there is no separate requirements
tree. An ID is `<feature>-R<n>`: `A1-R3` is the third acceptance criterion of
feature A1.

IDs are **permanent**. A requirement that's removed is marked *Withdrawn* in
place; its number is never reused. Tests and commits cite these IDs.

## Audiences

Two, and they need naming because most features serve only one:

| Audience | Who | What they touch |
|----------|-----|-----------------|
| **Operator** | The person who sets it up and keeps it running | lemonfiber (CLI/TUI/web), occasionally a service admin UI |
| **Household** | Everyone else in the home | Seerr to request, Jellyfin to watch. **Never lemonfiber.** |

A household member has exactly **one** account — their Jellyfin login, which
Seerr authenticates against. The multi-account problem is an operator
problem only.

---

## A — Getting started

The hardest part of the product, and where most users are lost today.

| ID | Feature | Audience |
|----|---------|----------|
| [A1](a-getting-started/a1-prerequisites.md) | Prerequisites & account guidance | Operator |
| [A2](a-getting-started/a2-setup-wizard.md) | Setup wizard | Operator |
| [A3](a-getting-started/a3-credential-validation.md) | Credential validation | Operator |
| [A4](a-getting-started/a4-reconfiguration.md) | Reconfiguration | Operator |
| [A5](a-getting-started/a5-migration.md) | Migration from an existing stack | Operator |
| [A6](a-getting-started/a6-uninstall.md) | Clean uninstall | Operator |
| [A7](a-getting-started/a7-credential-management.md) | Credential management & rotation | Operator |

## B — Running it

| ID | Feature | Audience |
|----|---------|----------|
| [B1](b-running/b1-forms.md) | Forms & partial stacks | Operator |
| [B2](b-running/b2-lifecycle.md) | Lifecycle control | Operator |
| [B3](b-running/b3-dashboard.md) | Live dashboard | Operator |
| [B4](b-running/b4-logs.md) | Log viewing | Operator |
| [B5](b-running/b5-notifications.md) | Notifications & alerting | Both |
| [B6](b-running/b6-remote-stack.md) | Controlling a stack on another machine | Operator |
| [B8](b-running/b8-autostart.md) | Autostart & boot persistence | Operator |

> **B7 (remote access for the household) is deferred past 1.0** — household
> features are **LAN-only** in 1.0. It returns in **v2 as [I1](i-remote-access/i1-remote-access.md)**,
> once a self-hosted overlay control plane (Headscale + self-hosted relay) makes
> it possible without the proprietary control plane that blocked it (Tailscale).
> See [ADR-0010](../../00-overview/decisions/0010-engine-abstraction-for-v2.md) for the
> related runtime decision and the [roadmap](../../00-overview/roadmap.md#post-10-candidates).

## C — Trust & correctness

Features that exist because [P3](../../00-overview/vision.md#p3--the-tool-proves-things-rather-than-assuming-them)
demands the tool prove things rather than assume them.

| ID | Feature | Audience |
|----|---------|----------|
| [C1](c-trust/c1-diagnostics.md) | Diagnostics (doctor) | Operator |
| [C2](c-trust/c2-vpn-verification.md) | VPN verification | Operator |
| [C3](c-trust/c3-auto-remediation.md) | Auto-remediation | Operator |
| [C4](c-trust/c4-support-bundle.md) | Support bundle | Operator |
| [C5](c-trust/c5-storage.md) | Storage & hardlink management | Operator |
| [C6](c-trust/c6-web-security.md) | Web UI security & binding policy | Operator |
| [C7](c-trust/c7-queue-health.md) | Queue health & stuck items | Operator |
| [C8](c-trust/c8-provider-health.md) | Provider health & quota tracking | Operator |
| [C9](c-trust/c9-drift.md) | Config drift detection & seed policy | Operator |

## D — Content & household

| ID | Feature | Audience |
|----|---------|----------|
| [D1](d-content/d1-seed.md) | Service auto-wiring | Operator |
| [D2](d-content/d2-quality-presets.md) | Quality presets in plain language | Operator |
| [D3](d-content/d3-first-content.md) | First-content walkthrough | Operator |
| [D4](d-content/d4-request-flow.md) | Household request flow | Household |
| [D5](d-content/d5-disk-space.md) | Disk space management | Operator |
| [D6](d-content/d6-household-identity.md) | Household identity & invitations | Both |
| [D7](d-content/d7-approval-quotas.md) | Request approval & quotas | Both |
| [D8](d-content/d8-parental-controls.md) | Parental controls | Both |
| [D9](d-content/d9-pipeline-trace.md) | "Where is my show?" pipeline trace | Both |
| [D10](d-content/d10-bandwidth.md) | Bandwidth & scheduling | Operator |

## E — Maintenance

| ID | Feature | Audience |
|----|---------|----------|
| [E1](e-maintenance/e1-stack-updates.md) | Stack updates | Operator |
| [E2](e-maintenance/e2-self-update.md) | lemonfiber self-update | Operator |
| [E3](e-maintenance/e3-backup-restore.md) | Backup & restore | Operator |
| [E4](e-maintenance/e4-rollback.md) | Rollback | Operator |

## F — Extensibility

| ID | Feature | Audience |
|----|---------|----------|
| [F1](f-extensibility/f1-customisation.md) | Customisation & escape hatches | Operator |
| [F2](f-extensibility/f2-service-catalogue.md) | Service catalogue | Operator |
| [F3](f-extensibility/f3-stack-manifests.md) · *v2, draft* | Third-party stack manifests | Operator |

## G — Cross-cutting UX

These are not screens; they are **properties every other feature must exhibit**.
G4 and G5 in particular are the connective tissue that makes 47 features read as
one product.

| ID | Feature | Audience |
|----|---------|----------|
| [G1](g-ux/g1-interface-tiers.md) | Interface tiers (CLI / TUI / web) | Both |
| [G2](g-ux/g2-plain-language.md) | Plain-language layer & in-product help | Both |
| [G3](g-ux/g3-accessibility.md) | Accessibility | Both |
| [G4](g-ux/g4-error-model.md) | Error & remedy model | Both |
| [G5](g-ux/g5-front-door.md) | The front door | Both |
| [G6](g-ux/g6-client-apps.md) | Client app guidance | Household |
| [G7](g-ux/g7-health-summary.md) | Overall health summary | Operator |
| [G8](g-ux/g8-privacy.md) | Privacy stance | Both |

---

# v2 — Ecosystem epoch

Everything below is `tracks: v2`: authored to the same falsifiable-requirement
bar, delivered after 1.0, and gated by the same rule (no stubs when 2.0.0 is cut).
The through-line is the project's wedge applied outward — not just *wiring* these
services, but **proving the wire works** (a health check, a valid upstream
credential, and a synthetic action read back), the thing no adjacent tool does.

Areas **H, I and K are Accepted**. The runtime pillar (**J**) and **F3** are
**Draft** — proposed and open for comment: they reopen a v1 non-goal
([ADR-0010](../../00-overview/decisions/0010-engine-abstraction-for-v2.md)) and
carry the most design risk, so they are not binding until reviewed.

## H — Ecosystem glue

The tools the community bolts on, bundled and — the differentiator — verified.

| ID | Feature | Audience |
|----|---------|----------|
| [H1](h-glue/h1-cross-seed.md) | Cross-seeding | Operator |
| [H2](h-glue/h2-autobrr.md) | Announce-driven grabbing | Operator |
| [H3](h-glue/h3-quality-sync.md) | Quality-profile sync | Operator |
| [H4](h-glue/h4-subtitles.md) | Subtitles | Both |
| [H5](h-glue/h5-queue-selfheal.md) | Queue self-healing | Operator |
| [H6](h-glue/h6-library-cleanup.md) | Library cleanup | Both |
| [H7](h-glue/h7-transcoding.md) | Transcoding | Operator |
| [H8](h-glue/h8-stats.md) | Playback statistics | Both |

## I — Remote access & identity

Reaching the stack from outside the home, and the one-account gate it requires —
both without a proprietary control plane.

| ID | Feature | Audience |
|----|---------|----------|
| [I1](i-remote-access/i1-remote-access.md) | Remote access for the household | Both |
| [I2](i-remote-access/i2-identity.md) | Household identity & single sign-on | Both |

## J — Runtime & platform · *Draft*

Freeing the stack from a single container runtime, while keeping both proofs
(VPN egress, hardlinks) passing on every engine ([ADR-0010](../../00-overview/decisions/0010-engine-abstraction-for-v2.md)).

| ID | Feature | Audience |
|----|---------|----------|
| [J1](j-runtime/j1-engine-abstraction.md) | Container-engine abstraction | Operator |
| [J2](j-runtime/j2-podman.md) | Running under Podman | Operator |
| [J3](j-runtime/j3-native.md) | Running natively, without containers | Operator |

## K — Observability

Open-source-native metrics and monitoring — a second opinion, delivery-confirmed.

| ID | Feature | Audience |
|----|---------|----------|
| [K1](k-observability/k1-metrics.md) | Metrics & dashboards | Operator |
| [K2](k-observability/k2-uptime.md) | Uptime monitoring | Operator |

> **Also v2, as extensions to existing areas:** [F3](f-extensibility/f3-stack-manifests.md)
> (third-party stack manifests), plus planned additions to
> [B5](b-running/b5-notifications.md) (open notification back-ends) and
> [G6](g-ux/g6-client-apps.md) (mobile handoff).

---

## Traceability

Three links, all of which CI checks:

```
Journey  ──exercises──▶  Feature  ──contains──▶  Requirement  ◀──implements──  Code
                                                      ▲
                                                      └──cites──  Architecture doc
```

1. Every [journey](../journeys/) names the features it exercises.
2. Every feature owns numbered requirements.
3. Every architecture and per-repo doc cites the requirement IDs it satisfies.

**A technical decision that cites no requirement is unjustified**, and should be
challenged in review. That's the rule that keeps the technical spec written
*against* the features rather than alongside them.
