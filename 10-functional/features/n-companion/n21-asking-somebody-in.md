---
id: N21
title: Asking somebody in
kind: feature
area: N
audience: operator
status: draft
maturity: planned
priority: P2
labels: [mobile, household, ux]
requires: [N1, D6]
relates: [N3, N9, N13, N4]
---

# N21 — Asking somebody in

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

[D6](../d-content/d6-household-identity.md) exists so an operator never learns
the media server's user administration. The moment it is for is a person on the
sofa asking how they get on — and the thing the operator has in their hand at
that moment is a phone.

[N9](n9-who-gets-in.md) already says what an invitation must state before it is
sent: what it grants, when it lapses, and whether it works away from home.
[N13](n13-taking-away.md) says what taking somebody out must say. This page is
the acts between them: **inviting, handing the invitation over, letting somebody
set a new password, and asking again** — each of which the stack performs over
the same route the other surfaces use.

## Behaviour

### Inviting is offered here, in the stack's terms

A person is named, and given libraries, an age limit and a choice about material
the media server has no rating for. Those are the whole decision, in the words
the stack uses for them, and nothing about how the media server stores any of it
is asked for or shown.

### The invitation is the stack's address, handed over by the operator

What the person needs is one address and how long it stands. The stack builds the
address from what the machine is called on the network, and the app hands that
address over as it came — as text, and as a code another phone can scan from this
one's screen. It builds no address of its own, and it sends nothing itself: the
operator hands it over through the device's own sharing, to whomever they choose.

An address that is a number can stop working when a router hands the number to
something else, and the stack says so with the invitation. That caution goes
wherever the address goes.

### What was found is an answer, and four answers are not one

Offering somebody an account twice is ordinary. The stack says what it found: a
new account made, an invitation already standing, a person who has already joined,
or a password taken off an account that was already theirs. Each means a different
thing to say to the person, and none of them is a failure. *Already joined* shown
as *invited* sends somebody a link to an account they have been using for a year.

### Watching and asking can arrive separately

The account a person watches with and the one they ask with live on two services,
and the second can be down while the first is not. Where the stack made the first
and could not yet tell the second, the person can watch and cannot yet ask, and
the app says exactly that. It is neither done nor failed: the next run finishes it
without anybody having to remember.

### A new password is theirs to choose

Where somebody has lost the way into their account, the stack takes the password
off and hands back an invitation to send, and the person chooses the next one at
the media server. The app offers that act. It never shows, sets or carries a
password, because the operator is not supposed to know one (`D6-R2`).

### An account that runs the media server is not a household member's

The stack refuses to take the password off the account it signs in with, and
the app shows that refusal with its reason rather than hiding the person from the
list.

### A rehearsed invitation made nothing

As everywhere (`N6-R1`). Here it decides whether somebody has an account.

## States

| State | Meaning |
|-------|---------|
| Made | An account was made; the address is ready to hand over. |
| Waiting | An invitation already stood for this person; it is the one to send. |
| Joined | They are already in the household. Nothing is sent. |
| Reset | Their password was taken off; the address is ready to hand over. |
| Not yet asking | They can watch, and the request service has not been told yet. |
| Refused | The stack refused, with its reason. |
| Unknown | The answer could not be read. Never rendered as sent. |

## Edge cases

- **An invitation asked for twice in an evening.** *Waiting* is shown, with the
  same address, and not a second invitation.
- **Invited while the request service is down.** *Made* and *not yet asking*
  together, shown as both.
- **A person the stack cannot find by that name.** The refusal names the name
  that was asked for.
- **Handing over declined by the platform's sharing.** Nothing was sent, and the
  address is still on screen to hand over another way.

## Requirements

| ID | Requirement |
|----|-------------|
| **N21-R1** | The app MUST offer inviting a person, with libraries, an age limit and what happens to unrated material chosen in the stack's terms, and MUST NOT ask for or show anything in the media server's own terms (`D6-R5`). |
| **N21-R2** | An invitation MUST be handed over as the address the stack gave, both as text and as a code another device can scan, and the app MUST NOT construct, shorten or alter an address of its own (`D6-R4`). |
| **N21-R3** | Handing an invitation over MUST be an act of the operator's through the device's own sharing, and the app MUST NOT send an invitation to anybody itself. |
| **N21-R4** | Where the stack carries a caution about the address, it MUST be shown with the address and MUST travel with it when it is handed over. |
| **N21-R5** | What the stack found MUST be shown as the standing it gave — *made*, *waiting*, *joined* or *reset* — and *joined* and *reset* MUST NOT be presented as a new invitation (`D6-R6`). |
| **N21-R6** | Where an account was made and the request service has not been told, the app MUST say that the person can watch and cannot yet ask, and MUST NOT present the invitation as complete or as failed (`D6-R12`). |
| **N21-R7** | The app MUST offer taking a member's password off so they can choose a new one, and MUST NOT show, set, accept or transmit a password (`D6-R2`, `D6-R10`). |
| **N21-R8** | A refusal about a person MUST be shown with the stack's reason and the name that was asked for, and MUST NOT be rendered as an error to retry. |
| **N21-R9** | A rehearsed invitation MUST be labelled as a rehearsal (`N6-R1`), and MUST NOT be presented as an account that exists. |
| **N21-R10** | Invitations the stack withdrew on the way past MUST be shown with the answer they arrived on, and MUST NOT be dropped. |

## Notes

**What the contract carries.** `invitation` answers the `invite` and `reissue`
actions; `invite` takes a name, libraries, an age limit and a word about unrated
material, and `reissue` takes a name.

| Row | Carried | Not carried |
|---|---|---|
| `N21-R1` | The `invite` action's `libraries`, `age_limit` and `unrated`; `applied` on the answer says what was written | The libraries there are to choose from, as a list to pick in. `household` names each member's libraries, not the set a new member could be given |
| `N21-R2` | `address`, built from the machine's name on the network | — |
| `N21-R3` | — | Nothing is needed: handing over is the device's act, not the stack's |
| `N21-R4` | `caution` | — |
| `N21-R5` | `standing`: `made`, `waiting`, `joined`, `reset` | `declined` (`D6-R16`), which `N9-R7` also waits on |
| `N21-R6` | `linked`: `made`, `not-yet`, `not-tried` | — |
| `N21-R7` | `reissue`, answered with an `invitation` whose standing is `reset` | — |
| `N21-R8` | The refusal, as `error` | — |
| `N21-R9` | `rehearsed` | — |
| `N21-R10` | `withdrawn` | — |

**`D6-R13` is not a row here.** An invitation nobody claimed is withdrawn, and
withdrawal removes the account, so there is no member left to re-issue to without
naming their access again. `reissue` makes an *existing* account claimable. Asking
again after a lapse is `invite`, which takes the access afresh — and nothing on the
wire keeps what the lapsed invitation granted to offer back.

**The decline address is not carried.** `D6-R15` puts one on every invitation;
`invitation` has no field for it, so the app hands over the one address it has.

## Related

- [N1](n1-companion-app.md) — parity, and what the app may claim
- [N9](n9-who-gets-in.md) — what an invitation states before it is sent
- [N13](n13-taking-away.md) — taking somebody out
- [N3](n3-household-companion.md) — what the person sees once they are in
- [N4](n4-native-integration.md) — the device's own sharing, and what a notification may say
- [D6](../d-content/d6-household-identity.md) — household identity and invitations
