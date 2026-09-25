---
id: D6
title: Household identity & invitations
kind: feature
area: D
audience: both
status: accepted
maturity: shipped
shipped: 0.11.0
labels: [household, security]
relates: [C6, D1, D4, D7, D8, G6]
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
  ✓ ana can sign in — unclaimed until she sets a password, and expires in 48 hours

  Send this:
  http://192.168.1.20:8096

  [QR code]

  Tell her to sign in as `ana`. She will be asked to set a password.
  If she would rather not, she can decline it here:
  http://192.168.1.20:8097/decline/7f3c9a
```

**Both addresses are answered by the stack, never by a process that lives only as
long as an operator's session.** `lemonfiber ui` keeps nothing running once the
operator closes it (`G1-R5`), so an invitation that only worked while it did would
stop working the moment the operator went to bed. What matters is how long the
process lives, not who built it: the decline page is served by a lemonfiber-built
image that the stack runs under its restart policy
([ADR-0029](../../../00-overview/decisions/0029-a-household-service-declines-an-invitation-with-one-key.md)). Accepting is a state Jellyfin holds: the account is there,
unclaimed, until somebody sets its password. Declining is a page, and the stack
serves it from a service it keeps running under its restart policy, beside the
household front door and at the same binding tier ([C6](../c-trust/c6-web-security.md)),
which is where the invitee already is. The front door itself is Seerr or Jellyfin,
and lemonfiber adds no route to either.

**A refusal is the invitation's standing.** The page declines the one invitation
its address names and nothing else. The service answering it disables the account
at once, so it can no longer be signed in to or claimed, and keeps the refusal
until the core next reads the household, which reports the invitation as
`declined` rather than `expired`. A declined account is kept, disabled, until the
operator removes it or re-issues the invitation: it is not swept when 48 hours
pass, because a refusal is something the operator should see before it goes.

**The sign-in address is Jellyfin's, which is not always the front door.** Setting a first
password happens in Jellyfin, and Seerr authenticates against Jellyfin rather
than holding credentials of its own — so an account with no password yet cannot
be claimed through Seerr, whichever service `G5` picks as the door. What `G5-R14`
is for still holds, and is what the operator experiences: one address, chosen by
lemonfiber, rather than four to choose between. After the account is claimed, the
household member uses the front door like everyone else.

What `invite` does is create the account (`D6-R12` says so plainly — an
invitation issued while Seerr is down still creates it), leave it without a
password, and record that it is unclaimed. The address is the same one the
household is given for everything else.

That is also what makes it single-use and expiring in the way `D6-R3` asks
(`D6-R4` covers the QR). It is claimed once, because setting a password is
something that happens once and cannot be undone by a second arrival; and it
expires because an account nobody claimed within 48 hours is removed rather than
left standing as a way in that nobody is watching.

The operator never chooses or transmits someone else's password.

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

### On the companion

*Access is decided at invitation, in plain terms* becomes several requirements,
because an invitation sent from a phone is the one most likely to be sent without
its terms being read ([N9](../n-companion/n9-who-gets-in.md)). `N9-R5` requires
an invitation to state what it grants — libraries, filtering, unrated material,
and whether requests may be made — **before** it is sent, and `N9-R6` requires it
to state when it lapses.

Afterwards, `N9-R7` requires two outcomes kept apart: lapsed unaccepted, and
declined by the invitee (`D6-R16`). From the operator's end they look identical —
nobody arrived — and each has a different next move, which is the argument
[D9](d9-pipeline-trace.md) makes about content that never appeared, applied to
people.

*LAN-only, and said plainly* becomes `N9-R9`: where something works only on the
household network, the app says so. That matters more here than anywhere else,
because the app is the thing most likely to be held at a friend's house.

*Removal is complete and honest* is where rounding does the most damage. `N13-R1`
requires how far a revocation reached shown as *everywhere*, *media-server-only*
or *nothing*, and `N13-R2` forbids rendering the middle one as complete
([N13](../n-companion/n13-taking-away.md)). That middle state is precisely the
one this feature refuses to leave behind — and flattening it into *removed* is
how it gets left behind anyway.

## States

Per household member:

| State | Meaning |
|-------|---------|
| `invited` | Invitation issued, not yet accepted |
| `expired` | Invitation lapsed unused |
| `declined` | The invitee refused the invitation at its decline address |
| `active` | Account created and usable |
| `restricted` | Active with content or library limits |
| `suspended` | Access temporarily withdrawn; account retained |
| `removed` | Access revoked everywhere |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Invitation link intercepted on the LAN | Single-use and short-lived. State that it grants account creation to whoever opens it. Whoever holds the decline address can refuse the invitation, which costs a re-issue and grants nothing. |
| Invitation expires unused | Re-issuable without recreating the account definition. |
| Invitee declines | The account is disabled at once and can no longer be claimed. The core reports the invitation as `declined` rather than `expired`, and the account stays, disabled, until the operator removes it or re-issues the invitation. |
| Decline address opened after the invitation was claimed or lapsed | Says the invitation is no longer open, and changes nothing. |
| The stack is stopped when the invitee opens the decline address | Nothing answers, as with the sign-in address. The invitation stays `invited` until it lapses. |
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
| **D6-R15** | An invitation MUST carry a decline address whose page offers the invitee a refusal of that invitation only, served by a service the stack keeps running under its restart policy beside the household front door, at the household binding tier, and never by a process whose lifetime is an operator's session — the CLI, the TUI or `lemonfiber ui` (`G1-R5`); who built the serving image does not matter. |
| **D6-R16** | A refusal MUST make the invitation unclaimable at once, MUST be kept by the stack until the core reads it, and the core MUST report it as the invitation's standing, `declined`, told apart from one that lapsed (`expired`). |

## Related

- [D4 Household request flow](d4-request-flow.md) — what the account is for
- [D7 Approval & quotas](d7-approval-quotas.md) · [D8 Parental controls](d8-parental-controls.md)
- [D1 Service auto-wiring](d1-seed.md) — the identity connection
- [G6 Client apps](../g-ux/g6-client-apps.md) — getting them watching
- [C6 Web security](../c-trust/c6-web-security.md) — the binding tier they reach
