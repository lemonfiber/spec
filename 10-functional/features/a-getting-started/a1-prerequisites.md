---
id: A1
title: Prerequisites & account guidance
kind: feature
area: A
audience: operator
status: accepted
tracks: v1
labels: [verification, ux]
relates: [A2, A3, C8, G2]
---

# A1 — Prerequisites & account guidance

**Status:** Accepted · **Audience:** Operator · **Area:** A — Getting started

---

## Purpose

Before any of this works, the operator needs third-party accounts that we cannot
create for them: a Usenet provider, at least one indexer, and — if they want
torrents — a VPN. Most of these cost money. Some are invite-only.

Every existing guide assumes these already exist. That assumption is the single
biggest wall a non-technical operator hits, and they hit it *after* installing
everything, when nothing downloads and no error explains why.

This feature makes the prerequisites **explicit, ordered, costed, and validated
before anything else is configured**. It is the first thing the operator sees.

## Behaviour

### The dependency map is shown before any credential is requested

The operator is shown what they need, derived from what they said they want:

| If they want… | They need |
|---------------|-----------|
| **To watch an existing library** | *Nothing.* No accounts, no subscriptions. |
| **Usenet downloads** | A Usenet provider **and** at least one Usenet indexer |
| **Torrent downloads** | At least one torrent indexer **and** a VPN |
| **Both** | All of the above |

The "nothing required" row is stated first and prominently. Someone with a
folder of existing media can reach a working Jellyfin with zero spend, and that
is a legitimate and valuable end state — not a degraded one.

### Categories are explained; specific vendors are not endorsed

lemonfiber explains **what each thing is, what it does, and what to look for**. It does
not recommend or rank specific commercial providers, because that would age
badly, invites accusations of affiliate bias, and varies by region.

For each prerequisite the operator sees: what it is in plain language, why it's
needed, the rough price band, and the selection criteria that actually matter
(for a Usenet provider: retention, connections, backbone, whether it's a block
or unlimited account).

### One selection criterion is called out specifically: VPN port forwarding

For torrents, whether a VPN offers **port forwarding** is the single criterion
with a lasting functional consequence, and it is the one most operators don't
know to ask about when subscribing.

Without it, peers cannot initiate connections: downloads still work, but
throughput is lower and seeding is substantially worse — which matters on private
trackers where ratio affects standing.

Only a minority of providers offer it, and several have withdrawn it. lemonfiber
therefore states the criterion at the point of choosing, while the operator can
still act on it, rather than after they've paid for a year of something that
cannot do it. Consistent with [A1-R5](#acceptance-criteria), it describes the
capability rather than recommending vendors.

### Order is enforced, because it matters

Provider → indexer → protocol config. Configuring an indexer before a provider
exists produces a confusing partial state. The checklist enforces sequence and
explains why each step precedes the next.

### Each credential is validated before it is stored

Delegated to [A3](a3-credential-validation.md). Nothing is persisted until it
has been proven to work against the live service. A wrong API key must fail
*here*, with a clear message, not three screens later as an empty search result.

### Progress is resumable

Acquiring accounts takes time — sign-ups, payment, email confirmation, invite
waits. The operator can leave, obtain what they need, and return to the same
checklist with prior entries intact.

## States

Per prerequisite:

| State | Meaning |
|-------|---------|
| `not-required` | Their protocol choices don't need it |
| `required` | Needed, nothing supplied yet |
| `supplied` | Credential entered, not yet validated |
| `validated` | Proven working against the live service |
| `failed` | Validation attempted and rejected — carries a remedy |
| `skipped` | Explicitly deferred by the operator; dependent features disabled |

Overall gate: setup may proceed when every `required` item is `validated`, or
the operator has explicitly accepted a reduced configuration with the
consequences stated.

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Operator has no accounts at all | Offer the zero-cost path: `library` form only, working Jellyfin over existing files. Prerequisites can be revisited later via [A4](a4-reconfiguration.md). |
| Operator wants torrents but no VPN | **Warn clearly and require explicit confirmation.** Do not silently allow it, and do not refuse outright — it's their machine and their decision. State plainly that their home IP will be visible to peers. |
| Indexer is invite-only and they're waiting | Mark `skipped`, continue setup, and surface a reminder. Don't block the whole install on a queue that may take weeks. |
| Provider is temporarily down during validation | Distinguish "credentials rejected" from "couldn't reach the service." Different causes, different remedies; conflating them sends the operator hunting the wrong problem. |
| Credential is valid but the account has no capacity | Surface it as its own state — a valid login on an exhausted block account looks like success and behaves like failure. See [C8](../c-trust/c8-provider-health.md). |
| Operator supplies a Usenet provider but no indexer | Explain the distinction, which is the most commonly confused pair in the whole domain: the **provider** stores the files; the **indexer** tells you where they are. Both are required. |
| Operator pastes a full config file instead of a key | Accept it and extract what's needed where the format is unambiguous. Don't punish reasonable behaviour. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **A1-R1** | lemonfiber MUST present the full list of required third-party accounts **before** requesting any credential. |
| **A1-R2** | The list MUST be derived from the operator's stated protocol choices, and MUST NOT show prerequisites for protocols they declined. |
| **A1-R3** | lemonfiber MUST state that a library-only configuration requires no third-party accounts, and MUST offer it as a supported end state. |
| **A1-R4** | For each prerequisite, lemonfiber MUST explain in plain language what it is, why it is needed, and its approximate cost band. |
| **A1-R5** | lemonfiber MUST NOT recommend, rank, or link to specific commercial providers. It MUST describe selection criteria instead. |
| **A1-R6** | lemonfiber MUST distinguish a Usenet *provider* from a Usenet *indexer* wherever both are referenced. |
| **A1-R7** | No credential MAY be persisted before validating successfully — see [A3-R1](a3-credential-validation.md). |
| **A1-R8** | Checklist progress MUST survive quitting and MUST be restored on next run. |
| **A1-R9** | If the operator selects torrents without a VPN, lemonfiber MUST warn explicitly and require confirmation, and MUST NOT refuse to proceed. |
| **A1-R10** | Validation failures MUST distinguish rejected credentials from unreachable services, with a distinct remedy for each — see [G4](../g-ux/g4-error-model.md). |
| **A1-R11** | Any prerequisite MAY be skipped; skipping MUST disable only the dependent features, and MUST state which. |
| **A1-R12** | Where torrents are selected, VPN port-forwarding support MUST be stated as a selection criterion **before** the operator is asked for VPN credentials. |
| **A1-R13** | The consequence of a provider without port forwarding — reduced peer connectivity and seeding — MUST be stated in plain language. |

## Related

- [A2 Setup wizard](a2-setup-wizard.md) — the flow this feature opens
- [A3 Credential validation](a3-credential-validation.md) — the validation mechanism
- [C8 Provider health](../c-trust/c8-provider-health.md) — ongoing monitoring of the same accounts
- [G2 Plain-language layer](../g-ux/g2-plain-language.md) — how the explanations are written
- [J1 First run](../../journeys/j1-first-run.md)
