---
id: C9
title: Config drift detection & seed policy
kind: feature
area: C
audience: operator
status: accepted
tracks: v1
---

# C9 — Config drift detection & seed policy

**Status:** Accepted · **Audience:** Operator · **Area:** C — Trust & correctness

---

## Purpose

Resolve the direct conflict between two things the product promises.

[P6](../../../00-overview/vision.md#p6--reproducible-over-precious) says
configuration should be reproducible: delete it, run [seed](../d-content/d1-seed.md),
get a working stack back. [F1](../f-extensibility/f1-customisation.md) says the
operator can customise anything.

These fight. Seeding is idempotent — it re-asserts *lemonfiber's* view of
configuration. So an operator who spends an evening tuning Sonarr's quality
profiles, then runs seed for an unrelated reason, silently loses that work.

That is a trust-destroying outcome, and it arises from two features that are each
individually correct.

## Behaviour

### lemonfiber records what it set

Every value written into a service is recorded — the field, the value, and when.
That record is what makes drift detectable: without it, lemonfiber cannot
distinguish a value the operator changed from one it set itself.

### Three-way comparison

Like a merge, drift detection compares three states:

| Source | Meaning |
|--------|---------|
| **Expected** | What lemonfiber last wrote |
| **Actual** | What the service currently holds |
| **Desired** | What lemonfiber would write now |

| Expected | Actual | Desired | Interpretation | Action |
|----------|--------|---------|----------------|--------|
| A | A | A | Unchanged | Nothing |
| A | A | B | lemonfiber's intent changed | Apply B |
| A | **B** | A | **Operator changed it** | **Preserve B** |
| A | B | C | Both changed | **Conflict — ask** |

The third row is the whole point: a value differing from what lemonfiber wrote,
where lemonfiber's intent is unchanged, is an operator edit and must survive.

### Operator edits win by default

Seeding never silently reverts a manual change. When lemonfiber would write
something different from what it finds, it reports rather than overwrites.

Silent reversion is the worst possible behaviour — the operator's work vanishes
with no error, and they cannot tell whether they imagined making the change.

### Conflicts are presented, not resolved

Where both sides changed, the operator is shown both values and chooses. lemonfiber
does not guess. Options are keep-mine, take-lemonfiber's, and for structured
values, merge where unambiguous.

### Edits can be adopted

An operator happy with their change can promote it to lemonfiber's expected
state, so it stops reporting as drift and is preserved across future seeds and
restores. This is how customisation becomes durable rather than perpetually
flagged.

### Drift is reported, not alarming

Drift is normal and often intentional. It surfaces as information, not a failure —
warning severity only when it breaks something, such as a root folder edited to a
nonexistent path.

### Materialised stack files are covered too

The same logic applies to the compose file and stack configuration lemonfiber
writes to disk. Local modifications are detected by content hash and are never
silently overwritten on upgrade
([ADR-0005](../../../00-overview/decisions/0005-embedded-stack-assets.md)); the
operator is shown a diff.

## States

Per managed value:

| State | Meaning |
|-------|---------|
| `in-sync` | Actual matches expected |
| `drifted` | Actual differs; lemonfiber's intent unchanged. Operator edit — preserved. |
| `stale` | Actual matches expected, but lemonfiber's intent changed. Will be updated. |
| `conflicted` | Both changed. Requires a decision. |
| `adopted` | An operator edit promoted to expected state |
| `unmanaged` | Never written by lemonfiber; outside its scope entirely |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Service normalises a value on write | Compare semantically, not textually, or the value reports as permanently drifted. |
| Service regenerates its own API key | Not drift — detect and re-propagate ([A7](../a-getting-started/a7-credential-management.md)). |
| Operator edits a value lemonfiber must control for correctness | Report as conflicted with the consequence stated. Still don't overwrite silently. |
| Drifted value breaks the stack | Warning severity with the breakage named, and remediation offered. |
| First seed after adopting an existing setup | Everything is `unmanaged`. Adopt what's found as expected rather than reporting mass drift. |
| Service upgrade changes a schema | Detect the version change and re-baseline rather than reporting every field as drifted. |
| Value changed by another tool | Indistinguishable from an operator edit. Treat identically — preserve. |
| Operator wants a full reset to lemonfiber's state | Supported as an explicit, confirmed action naming what will be lost. |
| Drift in a value containing a secret | Report that it drifted without displaying either value. |
| Very many drifted values | Summarise by service with detail on request. |
| Expected-state record lost | Report that drift cannot be assessed; offer to re-baseline from current state. |
| Operator edits the materialised compose file | Detect by hash, never overwrite on upgrade, show a diff. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **C9-R1** | lemonfiber MUST record every value it writes into a service, forming an expected-state baseline. |
| **C9-R2** | Drift detection MUST compare expected, actual and desired state. |
| **C9-R3** | Seeding MUST NOT silently overwrite a value that differs from the expected baseline. |
| **C9-R4** | A value differing from expected, where lemonfiber's intent is unchanged, MUST be preserved. |
| **C9-R5** | Where both actual and desired have changed, lemonfiber MUST present the conflict and MUST NOT resolve it automatically. |
| **C9-R6** | Operator edits MUST be promotable to expected state, surviving future seeds and restores. |
| **C9-R7** | Drift MUST be reported informationally, escalating to warning only when it breaks functionality. |
| **C9-R8** | Comparison MUST be semantic where a service normalises values on write. |
| **C9-R9** | Adopting an existing setup MUST baseline from what is found rather than reporting mass drift. |
| **C9-R10** | A service schema change MUST trigger re-baselining rather than mass drift reporting. |
| **C9-R11** | Drift in a secret MUST be reported without displaying either value. |
| **C9-R12** | A full reset to lemonfiber's state MUST be available as an explicit, confirmed action naming what will be lost. |
| **C9-R13** | Locally modified materialised stack files MUST be detected by content and MUST NOT be overwritten on upgrade without a diff and confirmation. |
| **C9-R14** | Loss of the expected-state record MUST be reported, with re-baselining offered. |

## Related

- [D1 Service auto-wiring](../d-content/d1-seed.md) — what writes the baseline
- [F1 Customisation](../f-extensibility/f1-customisation.md) — the promise this protects
- [A5 Migration](../a-getting-started/a5-migration.md) — adopting an existing configuration
- [E3 Backup & restore](../e-maintenance/e3-backup-restore.md) · [C3 Auto-remediation](c3-auto-remediation.md)
