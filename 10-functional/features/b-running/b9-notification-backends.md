---
id: B9
title: Open notification back-ends
kind: feature
area: B
audience: both
status: accepted
tracks: v2
milestone: M9
priority: P2
labels: [notifications, verification]
depends: [B5, G8]
---

# B9 — Open notification back-ends

**Status:** Accepted · **Audience:** Both · **Area:** B — Running it

---

## Purpose

[B5](b5-notifications.md) decides *what* is worth telling someone and *when*.
This feature decides *how the message actually gets there* — through open,
self-hostable delivery channels rather than a hosted notification service, and,
in keeping with the project, it **confirms the message was delivered** rather
than firing it into the dark. An alert that silently fails to send is worse than
no alert, because it teaches the operator the stack is quiet when it is actually
on fire.

## Behaviour

### It refuses a hosted notification plane

Delivery MUST go through channels the household can self-host or own. A hosted
coordination service that sits between the stack and the operator's devices is
refused as a built-in back-end, for the same reason the rest of the stack avoids
proprietary control planes — it may be documented as a manual option, never
configured as a default.

### It fans out through one open abstraction

Rather than teaching each service a dozen delivery targets, notifications go
through a single open fan-out layer that speaks to many back-ends. The operator
configures the back-ends once — a self-hosted push service is the ethos default —
and every notification source points at the one endpoint.

### It confirms delivery, it does not assume it

Configuring a back-end is not complete until a test notification is **sent and
its arrival observed** — for a self-hosted push service whose history is
readable, that round-trip is provable end to end. A back-end that cannot
demonstrate a delivered-and-observed test message is reported as unproven, not as
ready.

### It wires the stack's own events in

The services that emit events — the download and automation apps, the media
server — are pointed at the fan-out endpoint as part of setup, so the household's
existing event sources reach the chosen back-ends without per-service fiddling.

### The household chooses the channel, the operator owns the policy

Which back-end a person receives on is their choice; *what* is worth sending
stays [B5](b5-notifications.md)'s policy. Delivery never becomes a second place to
re-decide severity.

### It respects the privacy stance

What a notification contains is subject to the same [privacy](../g-ux/g8-privacy.md)
posture as everything else: no household watch or request detail leaves to a
back-end the operator did not choose.

## States

| State | Meaning |
|-------|---------|
| `unconfigured` | No delivery back-end wired yet; B5 events have nowhere to go |
| `ready` | At least one back-end wired and proven by a delivered test message |
| `degraded` | A configured back-end failed its last delivery or proof |
| `unreachable` | No configured back-end is currently accepting messages |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Test message sent but never observed arriving | Report the back-end unproven; do not mark it ready on a send alone. |
| A back-end is down when an event fires | Surface the failed delivery; where the back-end supports it, retry rather than drop silently. |
| The operator selects a hosted-only service | Decline it as a built-in back-end and say why; point to the self-hostable options. |
| Several back-ends configured, one fails | Deliver to the healthy ones and mark only the failed one degraded. |
| A notification would leak household watch/request detail | Redact per the privacy stance before it leaves ([G8](../g-ux/g8-privacy.md)). |
| Delivery credentials rotated | Fail the proof loudly and hold delivery to that back-end until re-proven. |
| A flood of events | Honour B5's rate/severity policy; delivery does not re-open the decision to send. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **B9-R1** | Delivery back-ends MUST be self-hostable or operator-owned; a hosted coordination service MUST NOT be configured as a default back-end. |
| **B9-R2** | Notifications MUST fan out through a single open abstraction to the configured back-ends, so a source configures one endpoint rather than many. |
| **B9-R3** | A back-end MUST NOT be reported ready until a test notification has been sent **and** its arrival observed; a back-end whose test cannot be observed MUST be reported unproven. |
| **B9-R4** | The stack's event sources MUST be wired to the fan-out endpoint during setup, without per-service delivery configuration. |
| **B9-R5** | Which back-end a person receives on MUST be their choice; delivery MUST NOT re-decide the severity or the what-to-send policy owned by [B5](b5-notifications.md). |
| **B9-R6** | A failed delivery MUST be surfaced, and where the back-end supports retry it MUST retry rather than drop silently. |
| **B9-R7** | With several back-ends configured, a single back-end failure MUST NOT prevent delivery to the healthy ones. |
| **B9-R8** | Notification content MUST honour the [privacy stance](../g-ux/g8-privacy.md); household watch or request detail MUST NOT leave to an unchosen back-end. |
| **B9-R9** | Rotated delivery credentials MUST fail the proof loudly and hold delivery to that back-end until re-proven. |
| **B9-R10** | Configuring, testing, and proving a back-end MUST each be reachable non-interactively. |
| **B9-R11** | The default offered back-end MUST be a self-hosted push channel, not a third-party service. |
| **B9-R12** | A hosted back-end MAY be documented as a manual option, but selecting it MUST carry an explicit note that it leaves the self-hosted posture. |

## Related

- [B5 Notifications & alerting](b5-notifications.md) — what is sent and when
- [G8 Privacy stance](../g-ux/g8-privacy.md) — what a message may contain
- [C1 Diagnostics](../c-trust/c1-diagnostics.md) — a common source of events worth delivering
- [G4 Error & remedy model](../g-ux/g4-error-model.md) — how a failed delivery reads
