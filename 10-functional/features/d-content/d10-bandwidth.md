---
id: D10
title: Bandwidth & scheduling
kind: feature
area: D
audience: operator
status: accepted
tracks: v1
---

# D10 — Bandwidth & scheduling

**Status:** Accepted · **Audience:** Operator · **Area:** D — Content & household

---

## Purpose

Stop the stack from ruining the household's internet.

A media stack saturates whatever connection it's given. Unconstrained, a large
grab consumes the entire uplink and downlink, and the effect is felt immediately
by everyone else in the house — video calls stutter, games lag, streaming
buffers.

This is a *social* failure more than a technical one. The operator gets blamed,
and the usual resolution is to stop running the stack during the day, or to stop
running it at all. Meanwhile seeding obligations on private trackers push in the
opposite direction.

There is also a hard constraint for many: metered connections with monthly data
caps, where uncontrolled seeding is genuinely expensive.

## Behaviour

### Limits are expressed in shares, not just numbers

Most operators don't know their connection's actual throughput in the units the
download clients expect. Limits are therefore offered as a proportion of measured
capacity as well as absolute figures, with the measured figure shown.

### Schedules follow household rhythms

The useful shape is not arbitrary cron-like rules but the pattern every household
has: constrained while people are awake and using the connection, unconstrained
overnight.

| Period | Typical |
|--------|---------|
| **Active hours** | Limited, so the connection stays usable |
| **Quiet hours** | Unlimited |

Defined once and applied to both download clients, rather than configured
separately in SABnzbd and qBittorrent with different semantics.

### Upload is limited separately, and defaults lower

Home connections are asymmetric — uplink is typically a fraction of downlink, and
saturating it degrades *everything*, including downloads, because acknowledgements
can't get out.

Uploads are the more damaging direction and get a conservative default. But
seeding is an obligation on private trackers, so throttling is preferred to
stopping, and the ratio consequence of any limit is stated.

### Data caps are tracked where declared

An operator who declares a monthly cap gets consumption tracked against it, with
a warning before exhaustion — and seeding is the usual culprit, since it continues
indefinitely without producing anything visible.

### Limits apply to the stack, not the machine

lemonfiber limits its own services. It does not attempt system-wide traffic
shaping, which would require privileges it shouldn't hold and would affect
applications it has no business touching.

### Temporary override

A one-off "unrestricted for the next hour" for when the operator wants something
now and knows nobody else is affected. Time-boxed, so it can't be forgotten and
left on.

## States

| State | Meaning |
|-------|---------|
| `unlimited` | No limits configured |
| `limited` | Limits active |
| `scheduled-active` | Within active hours; limits applied |
| `scheduled-quiet` | Within quiet hours; limits relaxed |
| `overridden` | Temporary override in force, with expiry |
| `cap-warning` | Approaching a declared data cap |
| `cap-exceeded` | Cap reached; configured behaviour applied |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Operator doesn't know their connection speed | Offer to measure, and express limits as a proportion of the result. |
| Measured speed varies | Re-measure periodically; don't pin limits to a single stale reading. |
| Schedule boundary crossed mid-transfer | Apply the new limit to the running transfer; don't wait for it to finish. |
| Clock change or daylight saving | Schedules follow local time and handle the transition without a gap or double application. |
| Seeding throttled below tracker requirements | State the consequence for ratio; never silently jeopardise standing on a private tracker. |
| Data cap declared but usage unmeasurable | Track what the stack itself transfers; state that other household usage isn't counted. |
| Cap exceeded | Apply the configured behaviour — pause, throttle heavily, or continue — as chosen in advance, not decided in the moment. |
| Override left running | Time-boxed by design; expires automatically and reports that it did. |
| Download client ignores a limit | Verify the limit was accepted; report if actual throughput exceeds it. |
| VPN adds overhead | Note that measured throughput through the tunnel is lower than raw connection speed. |
| Household member streaming from Jellyfin | Local traffic isn't limited. Only external transfers are shaped. |
| Very slow connection | Warn if limits would make transfers impractically slow. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **D10-R1** | Limits MUST be expressible as a proportion of measured capacity as well as absolute values. |
| **D10-R2** | Measured connection capacity MUST be shown alongside any proportional limit. |
| **D10-R3** | Schedules MUST support active and quiet periods, defined once and applied to all download clients. |
| **D10-R4** | Upload limits MUST be configurable separately and MUST default more conservatively than download. |
| **D10-R5** | Any limit affecting seeding MUST state the ratio consequence. |
| **D10-R6** | Schedule boundaries MUST apply to in-progress transfers immediately. |
| **D10-R7** | Schedules MUST follow local time and MUST handle daylight-saving transitions without gaps or double application. |
| **D10-R8** | Declared data caps MUST be tracked against measured stack usage, with a warning before exhaustion. |
| **D10-R9** | Cap-exceeded behaviour MUST be configured in advance, not prompted at the time. |
| **D10-R10** | Data-cap tracking MUST state that non-stack household usage is not counted. |
| **D10-R11** | Temporary overrides MUST be time-boxed and MUST report on expiry. |
| **D10-R12** | lemonfiber MUST limit only its own services and MUST NOT perform system-wide traffic shaping. |
| **D10-R13** | Applied limits MUST be verified as accepted, and actual throughput exceeding a limit MUST be reported. |
| **D10-R14** | Local playback traffic MUST NOT be subject to bandwidth limits. |

## Related

- [D5 Disk space](d5-disk-space.md) — the other finite resource
- [C7 Queue health](../c-trust/c7-queue-health.md) — distinguishing throttled from stalled
- [C2 VPN verification](../c-trust/c2-vpn-verification.md) — tunnel throughput overhead
- [B5 Notifications](../b-running/b5-notifications.md)
