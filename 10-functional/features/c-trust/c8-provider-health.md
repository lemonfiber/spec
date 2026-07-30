---
id: C8
title: Provider health & quota tracking
kind: feature
area: C
audience: operator
status: accepted
tracks: v1
---

# C8 — Provider health & quota tracking

**Status:** Accepted · **Audience:** Operator · **Area:** C — Trust & correctness

---

## Purpose

Watch the third-party accounts the stack depends on, because when they lapse the
symptom is indistinguishable from a broken installation.

A Usenet block account runs out of data. An indexer subscription expires. A daily
API hit limit is reached at midday. In every case the stack is functioning
perfectly and nothing downloads — and the operator, reasonably, concludes the
software is broken. They restart services, re-run setup, and post asking why
lemonfiber stopped working.

The account is the problem, and only the account knows it.

## Behaviour

### Capacity is tracked, not just validity

Credentials being valid is necessary and insufficient. A working login on an
exhausted account authenticates fine and downloads nothing.

| Provider type | Tracked |
|---------------|---------|
| **Usenet provider** | Data remaining on block accounts, connection limit vs. usage, subscription expiry |
| **Usenet indexer** | API hits used against the daily cap, grabs against the cap, subscription expiry |
| **Torrent indexer** | Reachability, authentication validity, ratio requirements where exposed |

### Depletion is warned about before it bites

An account at 5% remaining is a scheduled outage. The operator is told while
they can still act, not when downloads have already stopped.

Block accounts are the clearest case: they deplete steadily and predictably, and
lemonfiber can project when they'll run out from observed consumption.

### API caps are tracked against the day

Indexer API limits are the sneakiest failure: everything works each morning and
stops each afternoon, which reads as intermittent unreliability rather than a
quota. Naming it converts a baffling symptom into an obvious one.

### Exhaustion is distinguished from breakage

Three states that look identical from the outside and have entirely different
remedies:

| Observation | State | Remedy |
|-------------|-------|--------|
| Authenticates, no capacity | `exhausted` | Top up or wait for reset |
| Rejects credentials | `invalid` | Re-authenticate; check the subscription |
| No response | `unreachable` | Provider outage or local network |

Collapsing these is what makes the operator restart services when their account
needs topping up.

### Only what providers actually expose

Some report quota via API; some only on a web dashboard; some not at all. Where
capacity can't be read, lemonfiber says so rather than presenting an estimate as
fact. An inferred figure treated as authoritative is worse than an honest gap.

### Contributes to explanation, not just monitoring

When nothing is downloading, provider health is among the first things checked —
it turns "nothing works" into "your indexer hit its daily limit four hours ago,
resetting in eight."

## States

Per provider:

| State | Meaning |
|-------|---------|
| `healthy` | Reachable, authenticated, capacity available |
| `depleting` | Capacity below a warning threshold |
| `exhausted` | Authenticated but no capacity |
| `capped` | Rate or hit limit reached; resets at a known time |
| `invalid` | Credentials rejected |
| `unreachable` | No response |
| `unknown` | Provider exposes no usable capacity information |
| `expiring` | Subscription ends soon |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Provider exposes no quota API | `unknown`. State it; do not estimate and present as fact. |
| Block account depleting rapidly | Project exhaustion from observed rate and warn with the projection. |
| Daily cap reached | State the reset time, not just that the cap was hit. |
| Provider outage | Distinguish from credential rejection. Retry with backoff; don't declare credentials invalid on a timeout. |
| Multiple indexers, one down | Report per indexer. The stack still works, degraded. |
| All indexers down | Escalate — likely a local network or DNS problem rather than simultaneous provider failure. |
| Connection limit exceeded | Report as a configuration mismatch: the download client is set higher than the plan allows. |
| Subscription auto-renews | Don't warn about expiry where renewal is detectable. |
| Provider reports quota inconsistently | Prefer the most recent reliable reading; note instability. |
| Operator uses an unlimited plan | Capacity tracking is not applicable; don't display an empty meter. |
| Indexer rate-limits health checks | Back off. Monitoring must not itself consume the quota it measures. |
| Provider removed from configuration | Stop monitoring and clear its conditions. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **C8-R1** | Provider capacity MUST be tracked in addition to credential validity. |
| **C8-R2** | `exhausted`, `invalid` and `unreachable` MUST be distinguished, each with its own remedy. |
| **C8-R3** | Depletion MUST be warned about before capacity is exhausted. |
| **C8-R4** | Block-account exhaustion MUST be projected from observed consumption. |
| **C8-R5** | Indexer API and grab caps MUST be tracked, and the reset time MUST be reported when a cap is reached. |
| **C8-R6** | Where a provider exposes no capacity information, lemonfiber MUST report `unknown` and MUST NOT present an estimate as fact. |
| **C8-R7** | Health checks MUST NOT consume a meaningful share of the quota they measure. |
| **C8-R8** | Provider health MUST be checked when diagnosing an absence of downloads. |
| **C8-R9** | A timeout MUST NOT be reported as invalid credentials. |
| **C8-R10** | Per-indexer status MUST be reported individually. |
| **C8-R11** | All indexers failing simultaneously MUST escalate to a suspected local network problem. |
| **C8-R12** | A download client configured above the provider's connection limit MUST be reported as a mismatch. |
| **C8-R13** | Subscription expiry MUST be warned about where the provider exposes it. |
| **C8-R14** | Removing a provider MUST stop its monitoring and clear its conditions. |

## Related

- [A1 Prerequisites](../a-getting-started/a1-prerequisites.md) — where these accounts are acquired
- [A3 Credential validation](../a-getting-started/a3-credential-validation.md) — initial validation
- [C7 Queue health](c7-queue-health.md) — the downstream symptom
- [B5 Notifications](../b-running/b5-notifications.md)
