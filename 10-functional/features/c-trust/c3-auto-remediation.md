# C3 — Auto-remediation

**Status:** Accepted · **Audience:** Operator · **Area:** C — Trust & correctness

---

## Purpose

When diagnostics finds something wrong, offer to fix it.

A finding that says "your download client is listening on the wrong port" is
useful to someone who knows how to change it. To everyone else it's a more
articulate form of "broken." The gap between *knowing what's wrong* and *being
able to fix it* is where non-technical operators give up.

Many findings have exactly one correct fix, and lemonfiber already knows it —
that's how it detected the problem.

## Behaviour

### Fixes are offered, never applied silently

Every remediation is proposed with what it will do and what it will affect. The
operator confirms. Automatic repair without consent produces systems whose state
nobody can account for.

The exception is narrow and stated: **re-pushing a changed VPN forwarded port**
happens automatically, because the window between reconnect and re-push is a
window of degraded operation, the action is trivially reversible, and it is
reported after the fact.

### Not every finding is remediable

Three categories, and the distinction must be visible:

| Category | Example | Behaviour |
|----------|---------|-----------|
| **Automatically fixable** | Port drift, missing root folder, broken inter-service wiring, over-permissive file mode | Offer to fix |
| **Guided** | Data root can't hardlink; Docker Desktop not set to open at login | Explain the options; the operator acts |
| **External** | Provider subscription lapsed; WireGuard key generated without port forwarding | Only the operator can act, elsewhere |

Presenting an external problem as fixable is worse than presenting it as
unfixable — it sends the operator looking for a button that cannot exist.

### Fixes are verified

After applying, the originating check is re-run. "Fixed" means the check now
passes, not that the action completed without error.

If the check still fails, that is reported plainly rather than the fix being
declared successful.

### Fixes are reversible where possible

Anything modifying configuration records enough to undo it. A remediation that
makes things worse must be retractable without a full restore.

### Batch with individual consent

Where several findings are fixable, they can be addressed in one pass — but the
operator sees the full list and can decline individually. Not all-or-nothing.

### Remediation is logged

What was found, what was applied, when, and the verification outcome. This
history is what makes later debugging tractable and is included in the
[support bundle](c4-support-bundle.md).

## States

Per finding:

| State | Meaning |
|-------|---------|
| `remediable` | An automatic fix exists |
| `guided` | Instructions exist; the operator must act |
| `external` | Requires action outside lemonfiber entirely |
| `applying` | Fix in progress |
| `fixed` | Applied and re-verified passing |
| `fix-failed` | Applied but the check still fails |
| `declined` | Offered and refused; suppressed until it recurs |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Fix succeeds, check still fails | Report `fix-failed` honestly. Do not claim success from a completed action. |
| Fix requires restarting a service | State which, and that transfers may be interrupted, before confirming. |
| Several findings share one root cause | Fix the cause once; re-verify all dependents. Don't apply five overlapping fixes. |
| Fix would overwrite an operator's manual change | Refuse. Defer to [C9 drift](c9-drift.md) — never silently revert a deliberate edit. |
| Operator declines a fix | Record it and stop offering until the condition clears and recurs. Repeated prompting is nagging. |
| Fix fails partway | Roll back what was applied where possible; report exactly what state things are in. |
| Fix requires a credential that's absent | Reclassify as `guided` and ask for the credential first. |
| Remediation run non-interactively | Require an explicit flag to apply without prompting; default to reporting only. |
| Stack not running | Apply configuration fixes; defer runtime fixes and say so. |
| Fix depends on another fix | Order them and state the dependency. |
| The same fix fails repeatedly | Stop offering it after repeated failures and escalate to a support bundle. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **C3-R1** | Remediations MUST be proposed with their effects stated and MUST require confirmation before applying. |
| **C3-R2** | Re-pushing a changed VPN forwarded port MAY be applied automatically, and MUST be reported afterwards. |
| **C3-R3** | Findings MUST be classified as automatically fixable, guided, or external, and the classification MUST be visible. |
| **C3-R4** | A fix MUST re-run its originating check, and MUST only report `fixed` if that check then passes. |
| **C3-R5** | A completed action whose check still fails MUST report `fix-failed`. |
| **C3-R6** | Configuration-modifying fixes MUST record enough information to be reversed. |
| **C3-R7** | A fix that would overwrite an operator's manual change MUST be refused and deferred to drift handling. |
| **C3-R8** | Batch remediation MUST allow individual findings to be declined. |
| **C3-R9** | A declined fix MUST NOT be re-offered until the condition clears and recurs. |
| **C3-R10** | Findings sharing a root cause MUST be remediated once, with dependents re-verified. |
| **C3-R11** | Non-interactive remediation MUST require an explicit flag; the default MUST be report-only. |
| **C3-R12** | Every remediation MUST be logged with finding, action, timestamp and verification outcome. |
| **C3-R13** | A fix that fails partway MUST report the resulting state precisely. |
| **C3-R14** | A repeatedly failing fix MUST stop being offered and MUST escalate to a support bundle. |

## Related

- [C1 Diagnostics](c1-diagnostics.md) — the findings being remediated
- [C9 Drift detection](c9-drift.md) — why some fixes must be refused
- [C4 Support bundle](c4-support-bundle.md) — escalation path
- [G4 Error model](../g-ux/g4-error-model.md)
