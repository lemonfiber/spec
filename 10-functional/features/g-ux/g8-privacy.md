# G8 — Privacy stance

**Status:** Accepted · **Audience:** Both · **Area:** G — Cross-cutting UX

---

## Purpose

State, as a testable property rather than a promise, that lemonfiber does not
report on its users.

People self-host media precisely to avoid systems that watch them. A tool
introduced into that context carrying telemetry — however benign, however
anonymised — betrays the reason it was chosen. And it would be trivial to add
almost invisibly, which is why the prohibition belongs in the specification with
requirements attached rather than in a README.

The commitment is also *verifiable*: the source is public, and the network
behaviour is observable and testable.

## Behaviour

### No telemetry, at all

lemonfiber collects no usage data, sends no analytics, reports no crashes
automatically, and includes no identifier that would allow an installation to be
recognised across requests.

Not opt-out. Not anonymised-and-aggregated. **None.**

### Network requests are enumerable and justified

Every outbound request lemonfiber itself makes has a stated purpose, and can be
listed:

| Request | Purpose | Avoidable |
|---------|---------|-----------|
| Container registry | Pull and check image versions | Only by not updating |
| Update check | Determine if a newer lemonfiber exists | Yes — disableable |
| IP echo service | Verify VPN egress ([C2](../c-trust/c2-vpn-verification.md)) | Yes — disables leak detection |
| TRaSH guide source | Sync quality profiles | Yes — disables preset sync |

Nothing else. The list is short by design and is testable.

Requests made by the *services* — indexer queries, metadata lookups — are theirs
and are documented as such rather than claimed as lemonfiber's.

### The update check is minimal and optional

It asks a version endpoint what the latest version is. It transmits no identifier,
no configuration, no usage. It is disableable, and disabling it produces no
degradation beyond not knowing about updates.

### Nothing leaves the machine without an explicit act

The [support bundle](../c-trust/c4-support-bundle.md) is written locally and never
transmitted. Backups stay local. Logs stay local. Any sharing is the operator
carrying a file somewhere themselves.

### Local data is disclosed

What lemonfiber stores, where, and why: configuration, credentials, the
expected-state baseline, the change journal, and backups. The operator can inspect
all of it, and [uninstall](../a-getting-started/a6-uninstall.md) removes it.

### Household privacy within the home

Watch history is per-account and visible to the operator, because Jellyfin's
administration exposes it — that's a property of the underlying software, and it
is disclosed rather than glossed. A household member should know that the person
running the server can see what they watched.

### The claim is tested, not asserted

A test verifies that no unexpected outbound connection occurs. A privacy claim
maintained by good intentions decays; one maintained by a failing test does not.

## States

| State | Meaning |
|-------|---------|
| `default` | Update check enabled; no telemetry |
| `offline` | All outbound requests by lemonfiber disabled |
| `air-gapped` | No network expected; update checks silent |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Operator wants zero outbound requests | Fully supported; state what stops working (update checks, VPN leak detection, guide sync). |
| Crash occurs | Report locally. Never transmit. Offer a support bundle the operator may choose to share. |
| Update check fails | Silent after the first report. Never retried noisily. |
| Air-gapped installation | Detect repeated failure and stop attempting. |
| Operator asks what was sent | Answerable — outbound requests are logged locally and inspectable. |
| Third-party service changes terms | Only the IP-echo and guide sources are third-party; both are replaceable and disableable. |
| Household member asks who can see their activity | Disclosed: the operator can, via Jellyfin's administration. |
| A dependency introduces telemetry | Prohibited. Dependency review MUST check for it. |
| Operator wants to contribute usage data | Not offered. There is no mechanism, deliberately. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **G8-R1** | lemonfiber MUST NOT collect or transmit usage data, analytics, or crash reports. |
| **G8-R2** | lemonfiber MUST NOT generate or transmit any persistent installation identifier. |
| **G8-R3** | Every outbound request lemonfiber makes MUST have a documented purpose and MUST be enumerable by the operator. |
| **G8-R4** | The update check MUST transmit no identifier, configuration, or usage information. |
| **G8-R5** | All outbound requests MUST be individually disableable, and the consequence of disabling each MUST be stated. |
| **G8-R6** | Support bundles, backups and logs MUST remain local and MUST NOT be transmitted automatically. |
| **G8-R7** | lemonfiber MUST disclose what it stores locally, where, and why. |
| **G8-R8** | Uninstall MUST remove all locally stored lemonfiber data. |
| **G8-R9** | An automated test MUST verify that no unexpected outbound connection occurs. |
| **G8-R10** | Repeatedly failing update checks MUST stop being attempted and MUST NOT report noisily. |
| **G8-R11** | Dependencies introducing telemetry MUST be rejected, and dependency review MUST check for it. |
| **G8-R12** | Requests made by stack services MUST be documented as theirs, not attributed to lemonfiber. |
| **G8-R13** | Operator visibility of household watch history MUST be disclosed to household members. |
| **G8-R14** | Outbound requests MUST be logged locally so the operator can verify what was sent. |

## Related

- [C4 Support bundle](../c-trust/c4-support-bundle.md) — local by construction
- [E2 Self-update](../e-maintenance/e2-self-update.md) — the update check
- [A6 Uninstall](../a-getting-started/a6-uninstall.md) — complete removal
- [A7 Credential management](../a-getting-started/a7-credential-management.md)
- [C2 VPN verification](../c-trust/c2-vpn-verification.md) — the IP echo dependency
