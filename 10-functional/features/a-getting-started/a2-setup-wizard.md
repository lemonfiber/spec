---
id: A2
title: Setup wizard
kind: feature
area: A
audience: operator
status: accepted
tracks: v1
labels: [ux, wiring]
requires: [G4]
relates: [A1, A3, A4, G1]
---

# A2 — Setup wizard

**Status:** Accepted · **Audience:** Operator · **Area:** A — Getting started

---

## Purpose

Turn "clone a compose file and hope" into a guided conversation that ends in a
working stack. This is the feature the product is judged on: if setup fails or
confuses, nothing else in the catalogue matters.

The wizard's job is not merely to collect values. It is to **make decisions the
operator cannot reasonably make themselves**, by detecting the environment,
testing assumptions, and only asking questions whose answers it genuinely cannot
determine.

## Behaviour

### It runs when there's nothing to run

Invoking lemonfiber with no configuration present offers setup. It is never a hidden
command the operator has to discover.

### Every question earns its place

A question is asked only if all three hold:

1. lemonfiber cannot determine the answer by detection.
2. The answer changes behaviour.
3. The operator can plausibly answer it.

This is why timezone is *detected and confirmed* rather than asked, why
PUID/PGID is asked **only on native Linux** (elsewhere it's meaningless), and
why native-mode Jellyfin is offered only on platforms where it buys something.
A question the operator can't answer is not thoroughness; it's abdication.

### Steps

| # | Step | Asks or detects |
|---|------|-----------------|
| 1 | Welcome | Nothing. States what's about to happen and roughly how long. |
| 2 | Environment preflight | Detects OS, Docker presence, Compose version, daemon reachability |
| 3 | Protocols | Usenet, torrents, or neither |
| 4 | Prerequisites | [A1](a1-prerequisites.md) — the account checklist, derived from the protocol choice |
| 5 | Data location | Proposes a default; **empirically tests hardlinks** ([C5](../c-trust/c5-storage.md)) |
| 6 | Credentials | [A3](a3-credential-validation.md) — validated as entered |
| 7 | Quality preference | [D2](../d-content/d2-quality-presets.md) — plain language, not custom formats |
| 8 | Library serving | Whether to run Jellyfin; if so, [mode](../../../00-overview/decisions/0007-dual-mode-jellyfin.md) |
| 9 | Household | Whether others will use it; drives [D6](../d-content/d6-household-identity.md) |
| 10 | Autostart | Whether to start on boot ([B8](../b-running/b8-autostart.md)) |
| 11 | Review | Complete summary. **Nothing has touched disk yet.** |
| 12 | Apply | Writes config, creates directories, materialises stack files |
| 13 | Start | Pulls images with progress, starts the chosen form, waits for health |
| 14 | Wire | [D1](../d-content/d1-seed.md) — connects everything via API |
| 15 | Finish | Prints URLs; offers the [first-content walkthrough](../d-content/d3-first-content.md) |

### Nothing is written until Review is confirmed

Steps 1–11 are read-only. The operator can abandon at any point and leave no
trace beyond a resumable progress file. This matters because a half-applied
setup is worse than none — it produces a state nobody designed.

### Time is set honestly

Image pulls are multiple gigabytes. Step 1 states the expected duration, and
step 13 shows real per-image progress. Silent multi-minute waits read as a hang
and prompt operators to kill the process mid-write.

### It is resumable, not restartable

Quitting mid-wizard preserves answers. Returning resumes at the same step. The
operator is never made to re-answer eleven questions because step 12 failed.

## States

| State | Meaning |
|-------|---------|
| `absent` | No configuration; wizard offered |
| `in-progress` | Partially answered, nothing applied. Resumable. |
| `reviewing` | All answers collected, awaiting confirmation |
| `applying` | Writing config and starting services. The only non-atomic phase. |
| `applied` | Configuration on disk and valid |
| `failed-apply` | Apply was interrupted. **Must be recoverable, not wedged.** |

`failed-apply` is the dangerous state and gets explicit handling: on next run
lemonfiber detects the partial state, reports exactly what was written, and offers to
resume, roll back, or start over.

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Docker not installed | Platform-specific install instructions and exit. Never a stack trace. |
| Docker installed but daemon stopped | Distinguish from "not installed" — the remedies differ entirely (start Docker Desktop vs. install it). |
| Compose version too old | Name the found version, the required version, and the upgrade path. |
| Chosen data location can't hardlink | Explain the consequence in concrete terms (slower imports, double disk, broken seeding), then offer: choose elsewhere, or continue in copy mode. Never silently degrade. |
| Data location already contains media | Detect it, don't overwrite. Offer to adopt it as the existing library — this is the [migration](a5-migration.md) path. |
| Port already bound | Name the conflicting process where the OS permits, and offer a remap. |
| Interrupted during `applying` | On next run, detect and offer resume / roll back / start over. |
| Image pull fails partway | Retry the failed image only. Don't restart the whole pull. |
| A service fails its health check | Report *which*, show its logs inline, and offer to continue without it where the form permits. |
| Operator declines both protocols | Valid — a library-only configuration. Skip all download-related steps entirely. |
| Run non-interactively (piped/CI) | Fail with a clear message naming what would have been asked, and point at the flag-driven equivalent. Never hang waiting on stdin. |
| Configuration already exists | Don't offer setup. Point at [A4 reconfiguration](a4-reconfiguration.md) instead. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **A2-R1** | Invoking lemonfiber with no configuration MUST offer setup without requiring a subcommand. |
| **A2-R2** | Steps preceding Review MUST NOT write to disk, except a resumable progress file. |
| **A2-R3** | Review MUST show every value that will be written before anything is applied. |
| **A2-R4** | Progress MUST survive quitting, and the wizard MUST resume at the step reached. |
| **A2-R5** | lemonfiber MUST NOT ask any question whose answer it can reliably detect. |
| **A2-R6** | PUID/PGID MUST be requested only where file ownership is user-visible (native Linux Docker). |
| **A2-R7** | Native Jellyfin mode MUST be offered only on platforms where it enables hardware transcoding. |
| **A2-R8** | Hardlink capability MUST be tested empirically, never inferred from filesystem name. |
| **A2-R9** | "Docker absent" and "Docker present but unreachable" MUST produce distinct messages and remedies. |
| **A2-R10** | An interrupted apply MUST be detected on next run and MUST offer resume, roll back, or start over. |
| **A2-R11** | Image pull progress MUST be shown per image, with an expected-duration statement beforehand. |
| **A2-R12** | Declining both protocols MUST be a supported path that skips all download configuration. |
| **A2-R13** | In a non-interactive context, the wizard MUST fail with a message naming the required flags, and MUST NOT block on stdin. |
| **A2-R14** | When configuration already exists, lemonfiber MUST direct the operator to reconfiguration rather than re-running setup. |
| **A2-R15** | Total elapsed time for an operator with prerequisites in hand SHOULD be under 15 minutes ([NFR](../../../00-overview/vision.md#what-success-looks-like)). |

## Related

- [A1 Prerequisites](a1-prerequisites.md) · [A3 Credential validation](a3-credential-validation.md)
- [A4 Reconfiguration](a4-reconfiguration.md) — changing answers later
- [G1 Interface tiers](../g-ux/g1-interface-tiers.md) — the wizard renders in TUI and web
- [G4 Error model](../g-ux/g4-error-model.md) — how every failure above is presented
- [J1 First run](../../journeys/j1-first-run.md)
