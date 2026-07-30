---
id: G4
title: Error & remedy model
kind: feature
area: G
audience: both
status: accepted
tracks: v1
labels: [ux]
depends: [C1, C3, C4, G2]
---

# G4 — Error & remedy model

**Status:** Accepted · **Audience:** Both · **Area:** G — Cross-cutting UX

---

## Purpose

One consistent shape for everything that goes wrong, everywhere in the product.

This is the connective tissue. Forty-seven features can fail in hundreds of ways;
without a shared model each one invents its own, and the operator faces a product
that behaves like a dozen different tools stitched together.

It also implements [P4](../../../00-overview/vision.md#p4--errors-carry-remedies)
— the principle that an error without a remedy is a dead end. That principle is
easy to state and easy to violate one message at a time; a mandatory structure is
what makes it hold.

## Behaviour

### Every error has four parts

| Part | Answers |
|------|---------|
| **What happened** | Stated plainly, no jargon, no stack trace |
| **What it means** | The consequence for the operator |
| **What to do** | A concrete next action |
| **Where to look** | Optional: the failing service, the relevant log, the underlying detail |

```
✗ Imports are copying instead of hardlinking

  Your data folder is on an exFAT volume, which cannot create hardlinks.

  Every import will duplicate the file rather than linking it — so each
  one takes minutes instead of being instant, uses twice the disk while
  it runs, and torrents can't seed from the library copy.

  → Move your data folder to an APFS or ext4 volume, or
  → Continue in copy mode (the *arrs will be configured to match)

  Detail: lemonfiber doctor --only storage
```

Compare with what this ecosystem normally produces: `EXDEV: cross-device link`.

### Severity is small and meaningful

| Severity | Meaning | Requires |
|----------|---------|----------|
| **Critical** | Consequences outside the machine, or data at risk | Immediate action |
| **Error** | Something is broken | Action to restore function |
| **Warning** | Degraded or risky, still working | Attention, not urgency |
| **Advisory** | Informational | Nothing |

Four levels. More would not be used consistently, and inconsistent severity is
worse than coarse severity.

### Cause is distinguished from symptom

Where several failures share a root cause, the cause is reported and the symptoms
attributed to it. A full disk producing eleven failures is one problem, not
eleven.

Reporting symptoms as independent problems is how an operator is led to fix the
wrong thing repeatedly.

### The underlying detail is never hidden, never leading

The operator sees the plain explanation first, with the raw error, exit code, or
service response available on request. Hiding it would obstruct the experienced
operator; leading with it would lose everyone else.

### Errors never blame the operator

"Invalid configuration" implies fault and offers nothing. "This path doesn't
exist yet — shall I create it?" is the same information, actionable.

### Every error is identifiable

A stable identifier per error kind, so an operator can search for it and find
consistent answers, and so documentation can address specific failures.

### Unknown failures are honest

Not every failure will have a good remedy. Where lemonfiber genuinely doesn't
know, it says so and offers the [support bundle](../c-trust/c4-support-bundle.md)
rather than inventing plausible advice. **Confident wrong guidance is worse than
admitted ignorance** — it costs the operator time and trust.

### Errors never leak secrets

Subject to the redaction rules in [A7](../a-getting-started/a7-credential-management.md)
and [C4](../c-trust/c4-support-bundle.md). Verbose errors containing a request URL
with an embedded API key are the classic leak.

## States

| State | Meaning |
|-------|---------|
| `actionable` | Remedy available |
| `guided` | Operator must act, elsewhere |
| `remediable` | lemonfiber can fix it ([C3](../c-trust/c3-auto-remediation.md)) |
| `unknown` | No known remedy; escalation offered |
| `suppressed` | Acknowledged; not re-shown until it recurs |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Same error repeatedly | Report once with a count. Never repeat identical messages. |
| Error during error handling | Fail simply and safely; never loop. |
| Error message would be very long | Lead with one sentence; depth on request. |
| Error from an underlying service | Surface the service's own words verbatim as detail, with lemonfiber's interpretation leading. |
| Error with several plausible causes | List them by likelihood; don't assert one as certain. |
| Error in non-interactive mode | Full message to stderr, meaningful exit code, no prompting. |
| Error containing a file path | Show the full path; abbreviating produces unfindable files. |
| Error occurring in the household surface | Household-facing wording is Seerr's and Jellyfin's; lemonfiber doesn't rewrite it. |
| Transient error | Retry before reporting; report only if it persists. Distinguish transient from persistent. |
| Error the operator has already declined to fix | Suppress until it recurs after clearing. |
| Multiple errors at once | Group by root cause; report the cause first. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **G4-R1** | Every user-facing error MUST state what happened, what it means, and what to do. |
| **G4-R2** | Errors MUST use exactly the four defined severity levels. |
| **G4-R3** | Errors sharing a root cause MUST be grouped, with the cause reported rather than each symptom independently. |
| **G4-R4** | Plain explanation MUST lead; underlying technical detail MUST be available but MUST NOT lead. |
| **G4-R5** | Errors MUST NOT attribute fault to the operator. |
| **G4-R6** | Every error kind MUST carry a stable identifier. |
| **G4-R7** | Where no remedy is known, lemonfiber MUST say so and MUST offer escalation rather than speculating. |
| **G4-R8** | Errors MUST NOT contain credentials or secrets. |
| **G4-R9** | Repeated identical errors MUST be reported once with a count. |
| **G4-R10** | A failure during error handling MUST NOT loop or cascade. |
| **G4-R11** | Errors originating in a service MUST include that service's own message verbatim as detail. |
| **G4-R12** | Multiple plausible causes MUST be listed by likelihood rather than asserted as certain. |
| **G4-R13** | Non-interactive errors MUST go to stderr with a meaningful exit code and MUST NOT prompt. |
| **G4-R14** | File paths in errors MUST be shown in full. |
| **G4-R15** | Transient failures MUST be retried before reporting, and distinguished from persistent ones. |

## Related

- [P4 Errors carry remedies](../../../00-overview/vision.md#p4--errors-carry-remedies)
- [C1 Diagnostics](../c-trust/c1-diagnostics.md) — findings use this shape
- [C3 Auto-remediation](../c-trust/c3-auto-remediation.md) — acting on remedies
- [C4 Support bundle](../c-trust/c4-support-bundle.md) — escalation
- [G2 Plain-language layer](g2-plain-language.md) — the wording
