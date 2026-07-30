---
id: K1
title: Metrics & dashboards
kind: feature
area: K
audience: operator
status: accepted
tracks: v2
milestone: M9
priority: P2
labels: [observability, verification]
depends: [B3, G7]
---

# K1 — Metrics & dashboards

**Status:** Accepted · **Audience:** Operator · **Area:** K — Observability

---

## Purpose

Give the operator the open-source-native metrics and dashboards they would
otherwise assemble by hand — a time-series store, a dashboard renderer, and a
per-service exporter for each app — wired, provisioned and proven rather than
left as a weekend of glue. The live dashboard ([B3](../b-running/b3-dashboard.md))
answers "what is my stack doing right now?"; this answers "what has it been doing,
and is it trending somewhere I should care about?"

## Behaviour

### It refuses a hosted metrics plane

Metrics collection and dashboards MUST use open-source, self-hostable components
only. The stack's operational data is not shipped to a proprietary or hosted
observability service; the collector, the store and the dashboards all run inside
the household's own infrastructure.

### A collector scrapes exporters, a dashboard renders them

A metrics collector scrapes per-service exporters for the \*arr apps and the
download client on a schedule, retaining the samples so trends survive a restart.
A dashboard renderer reads that store and presents the series. The operator gets
queue depth, throughput, error rates and resource use over time, not just an
instantaneous number.

### Everything is provisioned as code

Scrape targets and dashboards are generated configuration, not click-ops. The set
of things being scraped, and the dashboards shown against them, are declared and
regenerated from the stack's own definition — so a rebuilt or moved stack comes
back with the same observability, and the next operator can read what is being
watched without reverse-engineering a UI's saved state.

### It ships a curated dashboard set

Rather than an empty renderer, the tool provisions a starting set of dashboards
that render against the real exporters in the stack. Adding a service that has an
exporter adds it to the scrape config and, where applicable, to the relevant
dashboard, so coverage tracks the stack rather than drifting behind it.

### It proves the pipeline, not the container

A running exporter container proves nothing about whether useful metrics arrive.
After wiring, the tool asserts empirically:

- **Targets up** — the collector reports each configured target as up, not merely
  that its container is running.
- **Series present** — the expected per-service metric series actually exist in
  the store, so an exporter that starts but emits nothing is caught.
- **Dashboards render** — the curated dashboards resolve their queries against
  real data rather than showing "No data" panels.

A target whose container is healthy but whose series are absent is a failure, and
is reported as one.

### Non-interactive equivalents exist

Provisioning the collector, regenerating scrape targets and dashboards, and
running the pipeline proof are each reachable as plain subcommands, so the scripter
is never forced through a UI.

## States

| State | Meaning |
|-------|---------|
| `unconfigured` | No metrics stack provisioned; offers to wire the collector, store and dashboards |
| `healthy` | All targets up, expected series present, dashboards rendering |
| `partial` | Collector up but one or more targets down or missing series; names which |
| `stale` | Collector reachable but not scraping; last sample is older than the interval |
| `unconfigured-store` | Provisioned but the time-series store is unavailable, so nothing is being retained |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Exporter present but the target is down | Report the target as down explicitly; a running exporter container MUST NOT be reported as a healthy target. |
| Metric series missing after an upstream version change | Fail the series-present check and name the missing series, rather than silently rendering an empty panel. |
| Metrics store disk growth | Enforce a retention bound and surface projected growth, so the observability stack does not quietly fill the disk it is meant to watch. |
| Scrape target behind the VPN namespace | Scrape it across the correct network path; a target reachable only inside the tunnel MUST NOT be reported down for being unroutable from the wrong namespace. |
| Dashboard query references a renamed metric | Surface the broken panel on the render proof rather than shipping a dashboard that shows "No data" as if it were zero. |
| Collector up but store unavailable | Distinguish "scraping but not retaining" from "healthy"; a lost store is not a healthy pipeline. |
| A service with no available exporter | State that it is unmonitored rather than implying coverage; absence of an exporter is reported, not hidden. |
| Clock skew between store and dashboard | Derive ranges from a single clock source so a panel never renders a gap or a future sample. |
| Operator edits a dashboard by hand | Configuration is authoritative; regeneration restores the declared set and the hand-edit is reported as drift, not silently kept. |
| High-cardinality series from a busy stack | Bound cardinality so the store is not overwhelmed; drop or aggregate rather than degrade the whole pipeline. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **K1-R1** | Metrics collection, storage and dashboards MUST use open-source, self-hostable components, and MUST NOT ship operational data to a proprietary or hosted observability plane. |
| **K1-R2** | A collector MUST scrape per-service exporters for the \*arr apps and the download client on a schedule. |
| **K1-R3** | Scrape targets MUST be file-provisioned as generated configuration, not configured by click-ops. |
| **K1-R4** | Dashboards MUST be file-provisioned as generated configuration, not saved by hand in the renderer. |
| **K1-R5** | The tool MUST assert that the collector reports each configured target as up, and MUST NOT treat a running exporter container as a healthy target. |
| **K1-R6** | The tool MUST assert that the expected per-service metric series are present in the store, catching an exporter that starts but emits nothing. |
| **K1-R7** | The tool MUST ship a curated dashboard set and assert that its panels resolve their queries against real data rather than rendering as empty. |
| **K1-R8** | Adding a service that has an exporter MUST add it to the scrape configuration so coverage tracks the stack. |
| **K1-R9** | The metrics store MUST enforce a retention bound and MUST surface projected disk growth. |
| **K1-R10** | A target reachable only inside the VPN namespace MUST be scraped across the correct network path and MUST NOT be reported down for a namespace mismatch. |
| **K1-R11** | A collector that is scraping but not retaining MUST be distinguished from a healthy pipeline. |
| **K1-R12** | A service with no available exporter MUST be reported as unmonitored rather than implied to be covered. |
| **K1-R13** | Provisioning, regenerating targets and dashboards, and running the pipeline proof MUST each be reachable non-interactively. |
| **K1-R14** | A failed target, series or render check MUST be distinguished from success, and each failure MUST carry a remedy ([G4](../g-ux/g4-error-model.md)). |

## Related

- [B3 Live dashboard](../b-running/b3-dashboard.md) — the instantaneous view this complements with history
- [G7 Health summary](../g-ux/g7-health-summary.md) — the single-line verdict metrics feed
- [K2 Uptime monitoring](k2-uptime.md) — the independent second opinion on reachability
- [C5 Storage](../c-trust/c5-storage.md) — the disk the metrics store must not quietly consume
