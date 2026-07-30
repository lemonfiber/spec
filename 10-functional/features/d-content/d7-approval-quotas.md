---
id: D7
title: Request approval & quotas
kind: feature
area: D
audience: both
status: accepted
tracks: v1
---

# D7 — Request approval & quotas

**Status:** Accepted · **Audience:** Both · **Area:** D — Content & household

---

## Purpose

Decide what happens when a household member asks for something — without the
operator becoming a bottleneck, and without the disk filling because someone
requested an entire nineteen-season procedural.

Two failure modes sit at opposite ends. Approve everything and the operator's
disk and bandwidth are at the mercy of anyone in the house. Approve nothing
automatically and the operator becomes a manual queue — every request waits on
them, household members chase them, and the promise of self-service evaporates.

## Behaviour

### Policy is chosen once, in plain terms

| Policy | Behaviour |
|--------|-----------|
| **Trusted household** *(default)* | Everything auto-approved within quota |
| **Approve large requests** | Auto-approve unless it exceeds a size or item threshold |
| **Approve everything** | Every request waits on the operator |
| **Per person** | Different policy per household member |

"Approve large requests" is the default recommendation: it removes the operator
from routine decisions while catching the case that actually matters — someone
requesting something enormous without realising.

### Quotas are per person and per period

Expressed in terms people understand — requests per week, or gigabytes per month
— rather than internal counters. A quota's purpose is to prevent accidental
excess, not to ration.

### Cost is visible before requesting

A household member sees the approximate size of what they're asking for. Most
excessive requests are innocent: nobody intends to ask for 800 GB, they just
didn't know a complete series in 4K is that large.

Showing the number prevents most of the problem without any policy at all.

### Decisions are fast and reachable

Pending requests appear in lemonfiber's dashboard and can be notified
([B5](../b-running/b5-notifications.md)). Approval must not require opening
Seerr — friction there is what turns "approve everything" into the only
workable setting.

### Declining requires a reason

The reason reaches the requester ([D4](d4-request-flow.md)). A silent decline is
indistinguishable from being ignored and produces exactly the in-person follow-up
the system exists to prevent.

### Quota exhaustion is explained, not just enforced

The member is told the limit, what they've used, and when it resets — at the
point of requesting, not after submitting.

## States

Per request: `auto-approved`, `pending`, `approved`, `declined`, `quota-blocked`,
`expired` (undecided beyond a period).

Per member: `within-quota`, `near-quota`, `quota-exhausted`, `unlimited`.

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Request exceeds remaining quota | Block at submission with the limit and reset time stated. Never accept then silently drop. |
| Size unknown before grabbing | Estimate from typical size for the type and quality; label it an estimate. |
| Actual size far exceeds the estimate | Complete it — retroactive rejection is worse — but count the real figure and note the discrepancy. |
| Request pending a long time | Remind the operator; expire after a period with the requester informed. |
| Operator unavailable for a long period | Consider raising the policy. Suggest it rather than silently changing behaviour. |
| Quota reset mid-request | Apply the quota at submission time only; don't re-evaluate in flight. |
| Season-by-season requests circumventing a per-request limit | Quotas are per period, not per request, so accumulation is caught. |
| Member requests something already requested | Deduplicate; don't charge quota twice. |
| Disk critical | Requests blocked regardless of quota, with the reason stated as disk, not quota. |
| Member removed with pending requests | Cancel and inform the operator. |
| Operator requests something | Not quota-limited. |
| Partially available series requested | Charge quota only for the missing portion. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **D7-R1** | Approval policy MUST be selectable in plain language, with per-member override supported. |
| **D7-R2** | Quotas MUST be expressed in terms the household understands — requests per period or volume per period. |
| **D7-R3** | Estimated size MUST be shown before a request is submitted. |
| **D7-R4** | Estimates MUST be labelled as estimates. |
| **D7-R5** | A request exceeding remaining quota MUST be blocked at submission, stating the limit and reset time. |
| **D7-R6** | Pending requests MUST be approvable from lemonfiber without opening Seerr. |
| **D7-R7** | Declining MUST require a reason, and that reason MUST reach the requester. |
| **D7-R8** | Long-pending requests MUST remind the operator and MUST expire with the requester informed. |
| **D7-R9** | Actual size exceeding the estimate MUST NOT retroactively cancel an approved request. |
| **D7-R10** | Quota MUST be evaluated at submission and MUST NOT be re-evaluated in flight. |
| **D7-R11** | Duplicate requests MUST NOT consume quota more than once. |
| **D7-R12** | Partially available content MUST charge quota only for the missing portion. |
| **D7-R13** | Critical disk state MUST block requests with disk stated as the reason, distinct from quota. |
| **D7-R14** | Operator requests MUST NOT be quota-limited. |

## Related

- [D4 Household request flow](d4-request-flow.md) — the requester's experience
- [D5 Disk space](d5-disk-space.md) — what quotas ultimately protect
- [D6 Household identity](d6-household-identity.md) — who has a quota
- [D8 Parental controls](d8-parental-controls.md) — a separate axis of restriction
