---
id: D6
title: Household identity & invitations
kind: feature
area: D
audience: both
status: accepted
tracks: v1
labels: [household, security]
depends: [C6, D1, D4, D7, D8, G6]
---

# D6 — Household identity & invitations

**Status:** Accepted · **Audience:** Both · **Area:** D — Content & household

---

## Purpose

Get everyone else in the home an account, without the operator learning Jellyfin's
user administration.

Adding a household member currently means: open Jellyfin, find user management,
create a user, set a password, decide library access and parental limits, then
tell the person their credentials over a messaging app — which is both awkward
and a poor way to handle a password.

The operator does this a handful of times, always from a cold start, always
having forgotten where the settings are.

## Behaviour

### One account per person, covering everything

A household member's Jellyfin account is their identity for both watching
(Jellyfin) and requesting (Seerr, authenticating against it). One credential,
created once.

### Invitations rather than credential handover

The operator creates an invitation; the household member sets their own password.

```
$ lemonfiber invite ana
  ✓ invitation created

  Send this link — expires in 48 hours:
  http://192.168.1.20:8096/invite/7f3a…

  [QR code]
```

The operator never chooses or transmits someone else's password. The invitee sets
their own, and the link expires.

The QR code matters more than it looks: the recipient is usually holding the
phone they'll watch on, and typing a LAN URL and credentials on a phone keyboard
is exactly the friction that makes people give up.

### Access is decided at invitation, in plain terms

Which libraries, and any age limit ([D8](d8-parental-controls.md)) — asked as
"what should Ana be able to see?", not as a permissions matrix.

### Household members are listed and manageable in one place

Who exists, what they can access, when they last watched, and what they've
requested — without opening two web UIs.

### Removal is complete and honest

Removing someone revokes access to both Jellyfin and Seerr, and states what
happens to their watch history and outstanding requests. Partial removal — no
longer able to watch but requests still arriving — is a confusing state to leave
behind.

### LAN-only, and said plainly

Household access works on the home network. Watching from elsewhere is not
supported in 1.0 ([B7 deferred](../README.md#b--running-it)), and the invitation
states this rather than letting someone discover it at a friend's house.

## States

Per household member:

| State | Meaning |
|-------|---------|
| `invited` | Invitation issued, not yet accepted |
| `expired` | Invitation lapsed unused |
| `active` | Account created and usable |
| `restricted` | Active with content or library limits |
| `suspended` | Access temporarily withdrawn; account retained |
| `removed` | Access revoked everywhere |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Invitation link intercepted on the LAN | Single-use and short-lived. State that it grants account creation to whoever opens it. |
| Invitation expires unused | Re-issuable without recreating the account definition. |
| Invitee sets a weak password | Enforce a minimum; keep the message brief and non-lecturing. |
| Person already has a Jellyfin account | Detect and offer to grant Seerr access rather than creating a duplicate. |
| Seerr unavailable at invitation time | Create the Jellyfin account and complete the Seerr link when it returns; report the partial state. |
| Household member forgets their password | The operator can issue a reset link. They never see or set the password themselves. |
| Removal with outstanding requests | State what happens to in-flight requests before confirming. |
| Removal with watch history | Ask whether to retain or delete it; deleting is irreversible. |
| Operator invites someone while the stack is stopped | Requires Jellyfin running; say so rather than failing obscurely. |
| Two people share a device | Supported — Jellyfin handles multiple profiles on one client. |
| Invitee on a device that can't scan QR | The URL is always shown alongside. |
| Household member should also be an operator | Out of scope. lemonfiber has a single operator; a second person needs host access. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **D6-R1** | A household member MUST require only one account, serving both watching and requesting. |
| **D6-R2** | The operator MUST NOT set or transmit another person's password. |
| **D6-R3** | Invitations MUST be single-use and MUST expire. |
| **D6-R4** | Invitations MUST be presented as both a URL and a QR code. |
| **D6-R5** | Library access and any age limit MUST be selectable at invitation time in plain language. |
| **D6-R6** | An existing Jellyfin account MUST be detected and reused rather than duplicated. |
| **D6-R7** | Household members MUST be listable with their access, activity and requests in one place. |
| **D6-R8** | Removal MUST revoke access in both Jellyfin and Seerr. |
| **D6-R9** | Removal MUST state the effect on watch history and outstanding requests before confirming. |
| **D6-R10** | The operator MUST be able to issue a password reset without learning the password. |
| **D6-R11** | Invitations MUST state that access is limited to the home network. |
| **D6-R12** | An invitation issued while Seerr is unavailable MUST still create the Jellyfin account and complete the link later, reporting the partial state. |
| **D6-R13** | Expired invitations MUST be re-issuable without redefining the member. |
| **D6-R14** | lemonfiber MUST NOT grant household members any access to lemonfiber itself. |

## Related

- [D4 Household request flow](d4-request-flow.md) — what the account is for
- [D7 Approval & quotas](d7-approval-quotas.md) · [D8 Parental controls](d8-parental-controls.md)
- [D1 Service auto-wiring](d1-seed.md) — the identity connection
- [G6 Client apps](../g-ux/g6-client-apps.md) — getting them watching
- [C6 Web security](../c-trust/c6-web-security.md) — the binding tier they reach
