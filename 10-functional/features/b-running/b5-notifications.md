---
id: B5
title: Notifications & alerting
kind: feature
area: B
audience: both
status: accepted
tracks: v1
---

# B5 — Notifications & alerting

**Status:** Accepted · **Audience:** Both · **Area:** B — Running it

---

## Purpose

Tell the operator when something needs their attention — and tell household
members when the thing they asked for has arrived.

Those two are almost opposite requirements, and conflating them is what ruins
notification systems. The operator wants **silence to mean healthy**; a channel
carrying forty "download complete" messages a day gets muted within a week, and
takes "your VPN is leaking" down with it.

## Behaviour

### Division of labour: lemonfiber alerts, services notify

lemonfiber does **not** reimplement what the stack already does well. Seerr
already notifies a requester when their request is approved and when it becomes
available; the \*arrs have their own connection systems.

| Owner | Events |
|-------|--------|
| **lemonfiber** | Problems, and cross-service conditions no single service can see |
| **Seerr** (configured by lemonfiber) | Household request approved, denied, now available |

lemonfiber's unique contribution is the conditions **nothing else observes**: a
VPN leak, hardlink degradation, an item downloaded but never imported, a disk
that will fill before the queue drains.

### Appetite is chosen during setup

The wizard asks once, offering three presets rather than a checklist:

| Preset | Notifies on |
|--------|-------------|
| **Problems only** | Failures and risks. Silence means healthy. |
| **Problems + completions** | The above, plus successful downloads and imports |
| **Everything** | The above, plus advisories such as available updates |

Every individual event remains configurable afterwards through
[reconfiguration](../a-getting-started/a4-reconfiguration.md). The preset sets
the starting point; it is not a ceiling.

### Event catalogue

| Severity | Event | In preset |
|----------|-------|-----------|
| **Critical** | VPN tunnel down or egress mismatch detected | all |
| **Critical** | Disk full, or projected to fill within 24h | all |
| **Critical** | Data root became unavailable | all |
| **Warning** | Queue item stuck beyond threshold | all |
| **Warning** | Provider quota exhausted or subscription lapsed | all |
| **Warning** | Service crash-looping | all |
| **Warning** | Imports degraded from hardlink to copy | all |
| **Warning** | Credential validation now failing | all |
| **Warning** | Backup failed | all |
| **Info** | Download completed | completions, everything |
| **Info** | Import succeeded | completions, everything |
| **Advisory** | Stack or lemonfiber update available | everything |
| **Advisory** | Backup succeeded | everything |

### Delivery channels

| Channel | Notes |
|---------|-------|
| **In-app** | Dashboard and health summary. Always on, no configuration, no dependency. The irreducible baseline. |
| **Desktop** | Native OS notification when lemonfiber runs on the operator's own machine. Useless headless. |
| **ntfy** | Push to phone. Apache-2.0 and self-hostable, so it fits the open-source commitment. A single HTTP request. |
| **Apprise** | Bridge to 100+ services (Discord, Telegram, email, Gotify, Pushover). One integration covers everything else. |

In-app is unconditional — an alert must never exist *only* on a channel that
might be misconfigured.

### Alerts are stateful, not repeated

An ongoing condition notifies **once** on entry and once on resolution. It does
not re-fire every poll. Repetition is how alerting becomes noise, and noise is
how alerts get ignored.

### Every alert carries its remedy

Consistent with [G4](../g-ux/g4-error-model.md): an alert states what happened,
what it means, and what to do. "VPN check failed" is a notification; "VPN tunnel
dropped — torrent traffic is halted by the killswitch, no leak occurred; restart
Gluetun to resume" is useful.

## States

Per alert condition:

| State | Meaning |
|-------|---------|
| `clear` | Condition not present |
| `firing` | Present and notified |
| `acknowledged` | Operator has seen it; suppressed until it clears and recurs |
| `resolved` | Cleared; a resolution notice sent if the onset was notified |
| `suppressed` | Muted by configuration or an active quiet period |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Condition flaps rapidly | Debounce. Require the condition to hold for a minimum period before notifying. |
| Many alerts fire at once | Coalesce into a digest rather than sending twenty messages. A disk-full event cascades into many downstream failures. |
| Delivery channel unreachable | Retry with backoff; never lose the alert — in-app always has it. Report channel failure as its own condition. |
| Notification would contain a credential | Redact. Same rules as the support bundle. |
| Alert fires while the stack is intentionally stopped | Suppress operational alerts when the operator stopped things deliberately. |
| Quiet hours configured | Hold non-critical alerts; critical ones always deliver. |
| Household member has no notification target | Seerr handles this; lemonfiber does not chase it. |
| Same condition on multiple services | Group into one alert naming all affected services. |
| Alert resolves before being read | Still show it in history — a transient VPN drop matters even after recovery. |
| Operator disables all channels | Permitted. In-app remains, and lemonfiber states that external delivery is off. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **B5-R1** | lemonfiber MUST NOT duplicate notifications that Seerr or the \*arrs already send to their own users. |
| **B5-R2** | Setup MUST ask notification appetite once, offering presets rather than an event checklist. |
| **B5-R3** | Every individual event MUST remain configurable after setup. |
| **B5-R4** | In-app delivery MUST be unconditional and MUST NOT require configuration. |
| **B5-R5** | An ongoing condition MUST notify once on onset and once on resolution, never repeatedly. |
| **B5-R6** | Conditions MUST be debounced so flapping does not generate repeated alerts. |
| **B5-R7** | Simultaneous alerts MUST be coalesced into a digest. |
| **B5-R8** | Every alert MUST state what happened, what it means, and what to do. |
| **B5-R9** | Alerts MUST NOT contain credentials, subject to the same redaction as the support bundle. |
| **B5-R10** | Channel delivery failure MUST itself be surfaced, and MUST NOT cause alert loss. |
| **B5-R11** | Critical alerts MUST bypass quiet-hours suppression. |
| **B5-R12** | Deliberate operator-initiated stops MUST suppress the resulting operational alerts. |
| **B5-R13** | Alert history MUST retain conditions that resolved before being read. |
| **B5-R14** | The same condition across several services MUST produce one grouped alert. |

## Related

- [B3 Dashboard](b3-dashboard.md) — in-app delivery surface
- [C1 Diagnostics](../c-trust/c1-diagnostics.md) — the checks producing most conditions
- [C7 Queue health](../c-trust/c7-queue-health.md) · [C8 Provider health](../c-trust/c8-provider-health.md)
- [D4 Household request flow](../d-content/d4-request-flow.md) — Seerr's side
- [G4 Error model](../g-ux/g4-error-model.md)
