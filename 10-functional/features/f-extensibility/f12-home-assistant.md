---
id: F12
title: Home Assistant
kind: feature
area: F
audience: operator
status: accepted
maturity: built
labels: [extensibility, observability, household, web]
relates: [C10, C6, B5, G2, K1]
---

# F12 — Home Assistant

**Status:** Accepted · **Audience:** Operator, household member · **Area:** F — Extensibility

---

## Purpose

Put the stack where many households already watch their homes. Home Assistant gets the
stack's health, its alerts, a short list of controls, and a member's own library, from the
web API, with an integration key ([C10](../c-trust/c10-integration-keys.md)) rather than
the operator's password.

The integration lives in
[`integration-home-assistant`](../../../30-repos/integration-home-assistant.md) and speaks
to the stack only through [`sdk-python`](../../../30-repos/sdk-python.md). Home Assistant
installs it as a HACS custom repository. Nothing in Home Assistant itself changes.

## Behaviour

### Connecting takes what the mint reply gave

Setup asks for the stack's address, the key and the certificate pin. All three come in the
reply that minted the key, so the operator pastes what they were shown. Setup checks all
three against the stack before it creates anything, and names whichever one failed.

### What appears is what the key can see

| Key scope | Entities |
|---|---|
| `read` | Stack health, doctor findings by severity, disk free per mount, active streams, the download queue and its speed, whether the VPN is up, and updates available. Alerts arrive as Home Assistant events. |
| `act` | All of `read`'s entities, plus buttons to restart a service and to run the doctor, update entities that apply a stack update, and a switch that pauses or resumes downloads. These are exactly the actions the contract lets a key call. |
| `member:<account>` | That member's requests by state and what they are playing, in the household's words. Nothing technical. |

### It follows the stream

State comes from the event stream rather than from polling. A value gathered before a gap
in the stream is shown as unavailable until the stream says what it is now, never as
current.

### A revoked key asks to be replaced

When the stack refuses the key, Home Assistant starts its reauthentication flow and asks for
a new one. The address and pin can be changed without removing the integration.

## States

| State | Meaning |
|---|---|
| `connected` | The stream is live and entities are current |
| `stale` | The stream has a gap; entities show unavailable until it resumes |
| `refused` | The key was refused; reauthentication has been asked for |
| `unreachable` | The stack did not answer at the address, or the pin did not match |

## Edge cases

| Situation | Behaviour |
|---|---|
| The pin does not match the certificate | Refused during the handshake, before any request is written; setup names the pin. |
| The web surface is loopback-bound and Home Assistant runs elsewhere | Setup says the stack is unreachable from here and points at C6's binding, rather than reporting a wrong key. |
| A control is pressed whose action becomes uncallable by a key | The stack's refusal is shown as the control's outcome; the control is removed at the next restart of the integration. |
| An alert carries the remedy text | The event carries what happened, what it means and what to do, as B5 writes it, and never a credential. |
| A member key's account leaves the household | The key is refused and reauthentication is asked for. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F12-R1** | The integration MUST reach a stack only through `sdk-python` and only with an integration key, and MUST NOT ask for, accept or store the operator password. |
| **F12-R2** | Setup MUST take the stack's address, a key and its certificate pin, MUST verify all three against the stack before creating an entry, and MUST name whichever failed. |
| **F12-R3** | A refused key MUST start Home Assistant's reauthentication flow, and the address and pin MUST be changeable without removing the entry. |
| **F12-R4** | The integration MUST create entities only for what its key's scope admits. A member key MUST yield no technical entity. |
| **F12-R5** | With a `read` or `act` key, the integration MUST provide stack health, doctor findings by severity, disk free per mount, active streams, the download queue and its speed, whether the VPN is up, and updates available. |
| **F12-R6** | Each alert MUST be fired as a Home Assistant event at onset and at resolution, carrying what happened, what it means and what to do, and never a credential. |
| **F12-R7** | State MUST follow the event stream. A value gathered before a gap MUST be shown as unavailable until the stream resumes, and MUST NOT be shown as current. |
| **F12-R8** | With an `act` key, the integration MUST provide restart-service and run-doctor buttons, update entities that apply a stack update, and a pause/resume downloads switch, and no control for an action the contract does not list as callable by a key. Each control MUST report the outcome of the job it started. |
| **F12-R9** | With a `member:<account>` key, the integration MUST provide that member's requests by state and what they are playing, in the household's words. |
| **F12-R10** | Diagnostics MUST withhold the key, the address and the pin. |
| **F12-R11** | Every string the integration shows MUST be translated, in English and Dutch at least. |
| **F12-R12** | The integration MUST meet every rule of Home Assistant's integration quality scale up to and including Platinum. |
| **F12-R13** | The integration MUST be installable as a HACS custom repository from this organisation, and MUST NOT require any change to Home Assistant itself. |

## Related

- [C10 Integration keys](../c-trust/c10-integration-keys.md) — what it holds
- [C6 Web UI security & binding policy](../c-trust/c6-web-security.md) — whether it can reach the stack at all
- [B5 Notifications](../b-running/b5-notifications.md) — what an alert says
- [`sdk-python`](../../../30-repos/sdk-python.md) · [`integration-home-assistant`](../../../30-repos/integration-home-assistant.md)
