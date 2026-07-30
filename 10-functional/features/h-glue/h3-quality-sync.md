---
id: H3
title: Quality-profile sync
kind: feature
area: H
audience: operator
status: accepted
tracks: v2
milestone: M7
priority: P1
labels: [quality, wiring, verification, stats]
depends: [D2]
---

# H3 — Quality-profile sync

**Status:** Accepted · **Audience:** Operator · **Area:** H — Ecosystem glue

---

## Purpose

Getting Sonarr and Radarr to grab the *right* release means custom formats and
quality profiles — dozens of them, scored just so — and the community already
maintains the definitive catalogue (the TRaSH-Guides). Hand-copying that catalogue
into each instance is a day of tedious, error-prone clicking that goes stale the
moment the guides update. Quality-profile sync applies the community catalogue to
the \*arr apps declaratively, so the operator names the profile they want and the
tool makes the instance match — then proves it matched, rather than trusting that
the writes stuck.

## Behaviour

### It applies the community catalogue declaratively

The operator selects which community-maintained custom formats and quality profiles
they want; the tool reconciles each instance to that selection — creating what is
missing, updating what has drifted, and leaving unmanaged items alone unless the
operator opts into pruning. The operator declares the desired state; the tool makes
the instance match it.

### It shows the diff before it writes

Before applying anything, the tool presents a preview: which custom formats and
profiles would be created, which updated, which (if pruning is enabled) removed,
and how scores would change. A dry run applies nothing. The operator sees the blast
radius before a single write, because a sync that silently rewrites scoring is
exactly what erodes trust in automation.

### It proves the result, not the request

This is the crux. A competitor stops at "the API accepted the write" — but an
accepted write is not a present, correctly-scored custom format. After a sync the
tool queries the \*arr API and asserts that the specific custom formats and profiles
now **exist** and carry the **expected scores**, reading back the effect rather than
trusting the acknowledgement. A sync whose read-back does not match the intended
state is reported as failed, even if every write returned success.

### It verifies the wiring and the source

The tool checks that each \*arr instance is reachable and its credential accepted,
and that the community catalogue source is reachable and readable, before it
reconciles anything. It builds on the plain-language quality presets ([D2](../d-content/d2-quality-presets.md)):
those choose *what quality the household wants*; this feature realises that choice
as the concrete formats and scores inside each \*arr.

### It can explain a grab decision *(stretch)*

Given a release the \*arr scored, the tool can explain *why* — which custom formats
matched, what each contributed, and how the total compared to the profile's cutoff
— so a surprising grab (or a surprising skip) becomes legible instead of magic.

### Every step is scriptable

Previewing a sync, applying it, and running the read-back proof are each reachable
non-interactively, so the catalogue can be reconciled on a schedule.

## States

| State | Meaning |
|-------|---------|
| `unconfigured` | No \*arr instances selected for sync, or no profiles chosen |
| `in-sync` | Last sync applied and read-back confirmed the instance matches the selection |
| `drift` | Instance diverges from the selection; a preview is available |
| `previewed` | A dry run computed a diff that has not been applied |
| `failed` | A sync applied but read-back did not confirm the expected formats or scores |
| `source-unavailable` | The community catalogue source is unreachable |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Another tool writes the same instance and reverts changes | Detect the divergence at the next read-back and report a fight over the instance rather than silently re-applying in a loop. |
| Pruning would remove formats the operator added by hand | Never prune unless explicitly enabled; when enabled, list every unmanaged item that would be removed in the preview first. |
| Catalogue source unreachable | Enter `source-unavailable` and leave the instance untouched; never apply a partial or empty catalogue over a working one. |
| Catalogue updated upstream since last sync | Show the changed formats and scores in the diff so the operator sees what moved before applying. |
| Write accepted but format absent on read-back | Report `failed`; an accepted write is not proof the format exists. |
| Score written but read back different | Report `failed` with the expected and observed scores, not success. |
| Instance credential invalid | Fail the credential check before any write; never write with an unverified credential. |
| Profile references a custom format the instance lacks | Create the format before the profile that depends on it, or report the unmet dependency; never leave a profile referencing a missing format. |
| Two instances (Sonarr and Radarr) with divergent catalogues | Reconcile each to its own selection independently; a failure on one must not block the other. |
| Operator applies without previewing | Still compute and record the diff so the change is auditable after the fact. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **H3-R1** | The catalogue source MUST be an open, community-owned quality catalogue; the tool MUST NOT depend on a proprietary or closed quality source. |
| **H3-R2** | The tool MUST wire each \*arr instance via its API and reconcile it to the operator's selected custom formats and profiles declaratively. |
| **H3-R3** | The tool MUST present a preview diff — creates, updates, and (if enabled) removals with score changes — before applying, and a dry run MUST apply nothing. |
| **H3-R4** | After a sync, the tool MUST query the \*arr API and assert that the intended custom formats and profiles exist and carry the expected scores; it MUST NOT treat an accepted write as proof. |
| **H3-R5** | A sync whose read-back does not confirm the expected formats and scores MUST be reported as failed, even if every write returned success. |
| **H3-R6** | The tool MUST verify each instance's reachability and accepted credential, and the catalogue source's reachability, before reconciling. |
| **H3-R7** | The tool MUST NOT prune unmanaged custom formats unless pruning is explicitly enabled, and when enabled MUST list every item that would be removed in the preview. |
| **H3-R8** | If the catalogue source is unreachable, the tool MUST leave the instance untouched and MUST NOT apply a partial or empty catalogue. |
| **H3-R9** | A custom format a profile depends on MUST be created before the profile, or the unmet dependency MUST be reported; a profile MUST NOT be left referencing a missing format. |
| **H3-R10** | Divergence caused by another tool writing the same instance MUST be reported as a conflict rather than driving a silent re-apply loop. |
| **H3-R11** | Each \*arr instance MUST be reconciled independently, so a failure on one does not block the others. |
| **H3-R12** | The tool SHOULD be able to explain a release's score by naming the custom formats that matched and their contributions relative to the profile cutoff. |
| **H3-R13** | Applying without an explicit preview MUST still compute and record the diff so the change is auditable. |
| **H3-R14** | Previewing, applying, and running the read-back proof MUST each be reachable non-interactively. |

## Related

- [D2 Quality presets in plain language](../d-content/d2-quality-presets.md) — the household-facing choice this realises as concrete formats and scores
- [D1 Service auto-wiring](../d-content/d1-seed.md) — how the \*arr apps are connected
- [C9 Configuration drift](../c-trust/c9-drift.md) — the broader drift model this sync participates in
- [H2 Announce-driven grabbing](h2-autobrr.md) — a consumer of the scoring these profiles define
