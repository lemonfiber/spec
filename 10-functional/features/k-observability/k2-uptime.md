---
id: K2
title: Uptime monitoring
kind: feature
area: K
audience: operator
status: accepted
tracks: v2
milestone: M9
priority: P2
labels: [observability, verification]
depends: [B5, G7]
---

# K2 — Uptime monitoring

**Status:** Accepted · **Audience:** Operator · **Area:** K — Observability

---

## Purpose

Give the operator an independent, self-hosted uptime and heartbeat monitor for
each critical service and each household-facing entry point — a second opinion
distinct from the tool's own health view ([G7](../g-ux/g7-health-summary.md)). When
the stack's own reporting is the thing that has failed, an outside watcher is the
only observer that can still tell the truth.

## Behaviour

### It is a self-hosted, open-source second opinion

Uptime monitoring MUST use an open-source, self-hostable monitor, not a hosted
uptime service. Its value is precisely that it is *independent* of lemonfiber's
own status path: if the tool's telemetry channel is down, the monitor still
reports, so an outage in the reporting is not mistaken for an outage in the stack —
or worse, hidden by one.

### A monitor per critical service and per entry point

Every critical service gets a live monitor, and so does every household-facing
entry point — the paths a member actually uses to request and to watch. The
question the monitor answers is not "is the container running?" but "does this
respond to something the household would do?"

### Heartbeats for scheduled work

Jobs that are supposed to run on a schedule — the periodic maintenance a healthy
stack performs — are watched by heartbeat checks: the job is expected to check in
each interval, and a missed check-in is itself an alarm. A cron job that silently
stops is caught by its silence, not only by a downstream symptom appearing days
later.

### It is honest about how it can be configured

The chosen monitor may not expose a stable configuration API. The tool provisions
it through whatever supported mechanism the monitor actually offers and **states
that limitation plainly** rather than pretending an API exists or that
configuration is fully declarative when it is not. Where provisioning cannot be
fully file-driven, the tool says so instead of implying a guarantee it cannot keep.

### It proves detection, not just presence

A configured monitor that has never seen a failure proves nothing. The tool
asserts empirically:

- **Live coverage** — each critical service and entry point has a monitor that is
  actually checking, not merely defined.
- **Detection works** — a deliberately induced failure is detected by the monitor
  and surfaced, so the operator knows the alarm path fires before a real outage
  tests it.

### Alerts route without duplicating notifications

When the monitor detects a failure it surfaces it, and its alert routing is
reconciled with the stack's own notifications ([B5](../b-running/b5-notifications.md))
so the operator is not paged twice for one event, nor left unsure which channel is
authoritative.

## States

| State | Meaning |
|-------|---------|
| `unconfigured` | No uptime monitor provisioned; offers to wire monitors for services and entry points |
| `watching` | Monitors live and checking; all covered targets currently up |
| `alarm` | One or more monitored targets down; the failure has been surfaced |
| `heartbeat-missed` | A scheduled job failed to check in within its interval |
| `monitor-down` | The monitor itself is unreachable; coverage is currently blind and this is stated |
| `expected-down` | A target is intentionally stopped ([a stopped form](../b-running/b2-lifecycle.md)); suppressed, not alarmed |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| The monitor itself goes down | State that coverage is blind rather than implying all-clear; an absent watcher MUST NOT read as everything healthy. |
| False positive on a slow link | Require a check to fail consistently before alarming, so a single slow response on a congested line does not page the operator. |
| A service intentionally down | Treat an intentionally stopped service as expected-down and suppress the alarm; a deliberate stop is not an outage. |
| Alert routing overlaps B5 notifications | Reconcile routing with the stack's notifications ([B5](../b-running/b5-notifications.md)) so one event does not produce two alerts, and the authoritative channel is clear. |
| Monitor lacks a stable configuration API | Provision through a supported mechanism and state the limitation, rather than presenting configuration as declarative when it is not. |
| Heartbeat job legitimately skipped | Distinguish a job that ran and reported nothing to do from a job that never checked in; only genuine silence is an alarm. |
| Entry point reachable internally but not from the household path | Monitor the path a member actually uses; internal reachability MUST NOT be reported as household reachability. |
| Monitor and metrics stack disagree | Report both honestly rather than hiding the disagreement; an independent second opinion is worthless if silently overridden. |
| Flapping target | Report the flap as flapping rather than as a stream of separate up/down events, so the operator sees instability, not noise. |
| Notification channel for alerts is itself down | Surface that alerts could not be delivered; an undeliverable alarm MUST NOT be recorded as delivered. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **K2-R1** | Uptime monitoring MUST use an open-source, self-hostable monitor, and MUST NOT depend on a hosted uptime service. |
| **K2-R2** | The monitor MUST be independent of lemonfiber's own health path, so a failure in the tool's reporting does not blind or falsify uptime coverage. |
| **K2-R3** | Every critical service MUST have a live monitor, and every household-facing entry point MUST have one. |
| **K2-R4** | Jobs expected to run on a schedule MUST be watched by heartbeat checks, and a missed check-in MUST itself raise an alarm. |
| **K2-R5** | The tool MUST assert that each critical service and entry point has a monitor that is actively checking, not merely defined. |
| **K2-R6** | The tool MUST assert that a deliberately induced failure is detected by the monitor and surfaced. |
| **K2-R7** | Where the monitor lacks a stable configuration API, the tool MUST provision it through a supported mechanism and MUST state the limitation rather than implying an API exists. |
| **K2-R8** | An unreachable monitor MUST be reported as blind coverage and MUST NOT be rendered as all-clear. |
| **K2-R9** | A monitored target MUST fail consistently before alarming, so a single slow response does not raise a false positive. |
| **K2-R10** | An intentionally stopped service MUST be treated as expected-down and MUST NOT raise an outage alarm. |
| **K2-R11** | Alert routing MUST be reconciled with the stack's notifications ([B5](../b-running/b5-notifications.md)) so a single event does not produce duplicate alerts. |
| **K2-R12** | An entry point MUST be monitored over the path the household actually uses, and internal reachability MUST NOT be reported as household reachability. |
| **K2-R13** | An alert that could not be delivered MUST be surfaced as undelivered rather than recorded as delivered. |
| **K2-R14** | Provisioning monitors and running the detection proof MUST each be reachable non-interactively. |

## Related

- [B5 Notifications](../b-running/b5-notifications.md) — the alert path uptime routing must not duplicate
- [G7 Health summary](../g-ux/g7-health-summary.md) — the tool's own view this deliberately second-guesses
- [K1 Metrics & dashboards](k1-metrics.md) — the trend view alongside this reachability check
- [B2 Lifecycle](../b-running/b2-lifecycle.md) — the stopped-form state that reads as expected-down
