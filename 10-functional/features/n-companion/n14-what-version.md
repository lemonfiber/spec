---
id: N14
title: What is running, and what is newer
kind: feature
area: N
audience: operator
status: draft
maturity: planned
priority: P3
labels: [mobile, updates, ux]
requires: [N1, E2]
relates: [E1, E5, N2, N11]
---

# N14 — What is running, and what is newer

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

`N2` covers updating the **services** — an update is a decision, it says what it
disturbs, and undoing is part of the offer. It does not cover updating
**lemonfiber itself**, which is a different act with a different risk and one
constraint that makes it genuinely awkward from a phone.

The constraint is that how lemonfiber was installed decides how it can be
updated, and it is not always something lemonfiber can do. A binary put there by
a distribution's package manager is that package manager's to replace. An app
offering a button that cannot work is worse than an app offering nothing, because
the operator stops looking for the thing that would have worked.

## Behaviour

### How it was installed is the first fact, not a detail

Homebrew, scoop, winget, cargo, a distribution, the installer, or somewhere the
stack cannot identify. The contract says which, and it decides everything else on
this screen.

Where it cannot identify how, that is said. An unknown installation is not
assumed to be one lemonfiber can replace.

### Where it cannot update itself, it says what would

The contract carries the command that would do it. An app that cannot perform the
update shows what to run rather than a disabled control with no explanation — the
operator is not at the machine, and a command they can read now is one they can
run when they are.

### A withdrawn release is never offered

A release can be withdrawn, and the contract says so. Offering one is offering
software somebody pulled, and an operator who installs it because a phone told
them to has been actively misled.

### The changelog leads with what an operator would notice

Releases carry whether they are user-facing. Both are shown, but a list that
opens with internal churn buries the one line somebody wanted, and the question
being asked is *should I take this*.

### What it carries, and what changes afterwards

An update carries a version of the stack with it, and something happens after it
is applied — a restart, a migration, a reconfiguration. Both are stated before
the decision, on the same argument `N2` makes about services: what it disturbs
and for how long is part of the offer rather than a surprise.

### Nothing here updates without being asked

The app does not apply an update because one exists, and does not apply one
while the operator is elsewhere. The decision is theirs and is taken at a moment
they chose.

## States

| State | Meaning |
|-------|---------|
| Current | What is running is the newest that is not withdrawn. |
| Newer available | There is a newer one, with what it carries and what happens after. |
| Not updatable here | Installed by something lemonfiber does not control, with the command that would. |
| Unknown installation | How it was installed could not be determined. Never rendered as updatable. |
| Unknown | The version or the changelog could not be read. Never rendered as current. |

## Edge cases

- **A newer release that is withdrawn and a newer one that is not.** The
  withdrawn one is not offered and not counted as available.
- **An installation method the contract names that the app has no path for.** The
  command is shown; no control is offered that would not work.
- **A version newer than anything in the changelog.** Shown as running, with the
  changelog silent about it, rather than as unknown.
- **The stack unreachable while an update is being considered.** The decision is
  not offered against a reading that could not be taken.

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N14-R1** | How lemonfiber was installed MUST be shown, and where it cannot be determined that MUST be said rather than assumed. |
| **N14-R2** | Where lemonfiber cannot replace itself, the app MUST NOT offer a control that would not work, and MUST show the command that would. |
| **N14-R3** | A withdrawn release MUST NOT be offered and MUST NOT be counted as an available update. |
| **N14-R4** | The changelog MUST distinguish user-facing releases from those that are not. |
| **N14-R5** | An update MUST state what version of the stack it carries and what happens after it is applied, before it is agreed to. |
| **N14-R6** | The app MUST NOT apply an update that was not asked for, and MUST NOT apply one on a schedule of its own. |
| **N14-R7** | A version or changelog that could not be read MUST be told apart from being current. |
| **N14-R8** | This surface MUST NOT be used to update the services, which is `N2`'s and carries a different offer. |

## Related

- [N1](n1-companion-app.md) — connecting, parity, and what the app may claim
- [N2](n2-operator-companion.md) — updating the services, which this is not
- [N11](n11-the-record.md) — what was done, and what is running
- [E2](../e-maintenance/e2-self-update.md) — lemonfiber replacing itself
- [E1](../e-maintenance/e1-stack-updates.md) — updating the services
- [E5](../e-maintenance/e5-changelog.md) — what a release says it changed
