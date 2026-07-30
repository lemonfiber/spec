---
id: D4
title: Household request flow
kind: feature
area: D
audience: household
status: accepted
tracks: v1
labels: [household]
depends: [D1, D6, D7, D8, G6]
---

# D4 — Household request flow

**Status:** Accepted · **Audience:** Household · **Area:** D — Content & household

---

## Purpose

Let everyone else in the home ask for something and then watch it, without ever
encountering lemonfiber.

This is the only feature whose primary audience is not the operator. For a
partner, a housemate, or a teenager, **the product is Seerr and Jellyfin** —
they will never see a terminal, a form, or a diagnostic. Their entire experience
is: search for something, tap request, and later it's there.

If that experience is poor, the operator hears about it constantly, and the whole
stack is judged a failure regardless of how well it's engineered.

## Behaviour

### One account, one place to ask

A household member signs in with their Jellyfin account — the same credentials
that let them watch. Seerr authenticates against Jellyfin
([D1](d1-seed.md)), so there is no second registration.

### The loop is closed for the requester

The failure mode to avoid is the request disappearing into silence. From the
requester's side:

| Stage | They see |
|-------|----------|
| Requested | Confirmation that it was received |
| Approved / declined | The outcome, and a reason if declined |
| Processing | That it's being worked on |
| Available | That it's ready, and where to watch it |

Seerr sends these. lemonfiber's job is to ensure it's configured to,
because the default of silence is what generates "did you get my request?" —
which is precisely the interruption the operator installed this to avoid.

### What can be requested reflects what's actually configured

Requesting television is meaningless if Sonarr isn't running. The request surface
reflects the active configuration, so a household member is never offered
something the stack cannot deliver.

### Failures are communicated, not swallowed

A request that can't be fulfilled — nothing available, repeated download failure,
too new — must reach the requester. Silence is read as being ignored, and the
requester's next move is to ask the operator in person.

### The operator sees household activity

Pending requests, and anything failing to fulfil, surface in lemonfiber's
dashboard. The operator shouldn't need to open Seerr to know something needs
attention.

### The household never touches lemonfiber

No lemonfiber account, no lemonfiber URL, no awareness that it exists. The
boundary is deliberate: household members should be unable to affect the stack's
operation even accidentally.

## States

Per request:

| State | Meaning |
|-------|---------|
| `submitted` | Received, awaiting decision |
| `auto-approved` | Approved under policy ([D7](d7-approval-quotas.md)) |
| `approved` | Approved by the operator |
| `declined` | Refused, with a reason |
| `processing` | Handed to an \*arr, being acquired |
| `available` | In the library and playable |
| `failed` | Could not be fulfilled; reason communicated |
| `partially-available` | Some of a series present |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Requested item already in the library | Say so immediately and link to it, rather than accepting a redundant request. |
| Item not yet released | Accept and mark as awaiting release, with the date. Don't fail something that simply hasn't happened yet. |
| Nothing available at the configured quality | Communicate that specifically — not a generic failure. The operator may want to relax the preset. |
| Request fails repeatedly | Notify the requester and surface to the operator. Don't retry silently forever. |
| Requester exceeds quota | Explain the limit and when it resets ([D7](d7-approval-quotas.md)). |
| Series requested where some seasons exist | Support partial requests; don't force re-acquiring what's present. |
| Requester lacks permission for that content type | The option shouldn't be offered. Never offer then refuse. |
| Household member removed | Their requests remain visible to the operator with the requester marked as removed. |
| Seerr unreachable | Surface as a service failure to the operator. The household simply can't request — an outage, but not data loss. |
| Two people request the same thing | Deduplicate; notify both when available. |
| Item available but Jellyfin hasn't scanned | Trigger a scan before marking available, so "ready" is true when stated. |
| Requester has no notification target | Status is visible in Seerr regardless; the loop closes on next visit. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **D4-R1** | Household members MUST authenticate with their Jellyfin account; no separate registration MAY be required. |
| **D4-R2** | Requesters MUST be informed at submission, decision, and availability. |
| **D4-R3** | A request that cannot be fulfilled MUST communicate that to the requester with a reason. |
| **D4-R4** | The request surface MUST offer only content types the active configuration can deliver. |
| **D4-R5** | Content already in the library MUST be reported as such rather than accepted as a request. |
| **D4-R6** | Unreleased content MUST be accepted and marked awaiting release, not failed. |
| **D4-R7** | "Nothing available at the configured quality" MUST be communicated distinctly from a generic failure. |
| **D4-R8** | Pending and failing requests MUST surface in lemonfiber's dashboard. |
| **D4-R9** | Household members MUST NOT require any lemonfiber account or access. |
| **D4-R10** | Duplicate requests MUST be deduplicated, with all requesters notified on availability. |
| **D4-R11** | Partial series requests MUST be supported without re-acquiring existing content. |
| **D4-R12** | A library scan MUST complete before a request is reported available. |
| **D4-R13** | Content a requester lacks permission for MUST NOT be offered. |
| **D4-R14** | Repeated fulfilment failure MUST stop retrying silently and MUST notify both requester and operator. |

## Related

- [D6 Household identity](d6-household-identity.md) — how members get accounts
- [D7 Approval & quotas](d7-approval-quotas.md) — the decision policy
- [D8 Parental controls](d8-parental-controls.md) — what each member may request
- [D1 Service auto-wiring](d1-seed.md) — the Jellyfin identity connection
- [G6 Client apps](../g-ux/g6-client-apps.md) — where they watch
