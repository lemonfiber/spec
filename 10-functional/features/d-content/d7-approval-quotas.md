---
id: D7
title: Request approval & quotas
kind: feature
area: D
audience: both
status: accepted
maturity: shipped
shipped: 0.12.0
labels: [household]
relates: [D4, D5, D6, D8]
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

### On the companion

Removing a person and the queue they leave behind are one decision seen from two
ends, and `N13-R3` requires the first to show the second: before a person is
removed, what they have outstanding, and whether they ask through the request
service at all ([N13](../n-companion/n13-taking-away.md)). An operator deciding
from a phone is the one most likely to remove an account without ever having seen
its queue.

*Declining requires a reason* and *quota exhaustion is explained, not just
enforced* are the same principle the companion applies to refusals everywhere:
`N13-R9` requires a refusal carried with the stack's own reason rather than
rendered as an error to retry. A quota that answers *no* without saying it was a
quota is indistinguishable, from the other end, from a request service that is
broken — and the household member's next move is to ask again.

*Long-pending requests remind the operator and expire* is two halves, and the
companion owns only one of them. The reminder is the stack's to deliver:
`N17-R1` forbids the app operating a notification service of its own, so an app
that decided a request had waited long enough and told somebody would be the
thing that rule exists to prevent. What the app owes is the figure the reminder
would be about — how long each request has been waiting — because a request
approaching expiry is a different decision from one made this morning, and
`N2-R11` surfaces a request *with enough to decide on*, which is this page.

That figure is carried, and it is absent for two different reasons: a request
somebody has already ruled on was not waiting, and a request whose service date
could not be read is waiting for nobody knows how long. An app rendering both
as *no age* tells an operator the second is the first.

They are told apart by the state beside it, not by the figure. A request still
waiting for approval says so, so an absent age there is an age that could not be
read, and is shown as one. An age absent on a request already ruled on is the
figure correctly declining to count.

The one case neither field settles is a request whose state is itself absent,
which is what the contract says about a status this build does not recognise. An
app has nothing to go on there and `N2-R14` is what it does about it: state
neither, rather than pick the reading that makes the screen tidier.

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
