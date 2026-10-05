---
id: D11
title: Watching what the house holds
kind: feature
area: D
audience: household
status: accepted
maturity: planned
priority: P2
labels: [household, security, network]
requires: [D6, D8, G5]
relates: [B1, D4, G10, N3]
---

# D11 — Watching what the house holds

**Status:** Accepted · **Audience:** Household · **Area:** D — Content & household

---

## Purpose

What a member needs from the stack to find a film, see what it is and play it,
on their own account and under their own limits.

[N3](../n-companion/n3-household-companion.md) and
[G10](../g-ux/g10-household-web.md) are the two surfaces a member plays on. Both
render what the core answers and decide nothing themselves, so everything they
draw about a title — its artwork, what it is, how far through it a member got,
where it streams from — has to be an answer the core gives. This feature is
those answers, and the grant and the guard that keep each one to the member who
asked ([ADR-0027](../../../00-overview/decisions/0027-a-member-plays-what-the-core-authorised.md)).

## Behaviour

### A grant on the member's own account

A member's paired client asks the media server for a device code, and the core,
as the media server's administrator, authorises that code for the member's own
user. The session that comes back is the member's, so every question asked with
it is answered under the member's age limit and library access
([D8](d8-parental-controls.md)). Nobody learns the member's password
([D6](d6-household-identity.md)). The core ends the grant when it lapses and when
the member is removed from the household.

### The front door guards every byte

The media server answers its byte endpoints — a stream, a segment, a subtitle,
an item's image — without asking who is there. So every one of them is reached
only through a guard the stack keeps in front of the media server, in every form
that serves it ([B1](../b-running/b1-forms.md), [G5](../g-ux/g5-front-door.md)).
Before it passes a request on, the guard asks the media server whether the
session presented may see that item. An item it may not see, a session that is
absent, ended or wrong, and a question that is not answered are all refusals.
The media server's own port is not published to the household beside it.

The guard serves over TLS, and the core states the fingerprint of the
certificate it presents beside every location it gives there. A client pins the
door the way it pins the stack.

### Where each title's pictures and stream are

For each title the core lists for a member, it states where its poster and
backdrop are served at the guarded door, and where the title streams from. Each
location is built from the household address the stack publishes for the media
server, so a client never puts one together. Where the core does not know that
address, it states no location and says why. Only an item's own images are
located: a person's, a genre's or a studio's image is not an item's bytes, and
the guard's question does not reach it.

### What a title is, and how far through it a member got

A title's details — what it is about, how long it runs, its genres, its
certificate, when it came out, and a series' seasons and episodes — are answered
as the member's own session reads them, so a title outside their limits is
answered as absent. What a member was part-way through, and how far, is answered
the same way.

## States

| State | Meaning |
|-------|---------|
| Granted | The member's client holds a session on the member's own account. |
| Lapsed | The grant ran out; the session is refused at the server and at the door. |
| Revoked | The member was removed; every session their devices held is ended. |
| Located | A title carries where its artwork and stream are served. |
| Unlocated | The core does not know the household address, and the title says why. |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| The household address is not known | No location is stated for any title, and each says why. Playback is declined on the surface. |
| A title has no artwork | No artwork location is stated for it. The surface draws its name. |
| A member asks for an item outside their libraries by id | The door refuses it, because the media server says the session cannot see it. |
| A request presents no session | The door refuses it. |
| The media server does not answer the door's question | The door refuses the request rather than passing it through. |
| A member is removed mid-film | Their sessions are ended, and the next byte the door is asked for is refused. |
| The door presents a certificate other than the one the core stated | A client refuses it. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **D11-R1** | A member's paired client MUST be able to obtain a grant to play on the member's own media-server account, authorised by the core without anybody learning the member's password, and the core MUST end it when it lapses and when the member is removed (`D6-R8`). |
| **D11-R2** | Every byte the media server serves for an item, its images included, MUST pass a guard that asks the media server whether the presented session may see that item, and MUST be refused where it may not, where no session is presented, or where the answer does not come. The media server's own port MUST NOT be published to the household beside the guard. |
| **D11-R3** | The core MUST state, for each title it lists for a member, where its poster and backdrop are served at the guarded front door, built from the household address the stack publishes for the media server. It MUST state nothing where it does not know that address, and MUST NOT state the location of an image that is not an item's own. |
| **D11-R4** | The core MUST answer a title's details (overview, runtime, genres, certificate, release date, and seasons and episodes) as the member's own session reads them, and MUST answer a title outside the member's limits as absent (`D8-R9`). |
| **D11-R5** | The core MUST answer what a member was part-way through, with how far through each was, as the member's own session reads it. |
| **D11-R6** | Each title a member may watch MUST carry the location that streams it at the guarded front door where the core knows the household address and the title streams, and MUST carry the reason in its place where it does not. |
| **D11-R7** | The guarded front door MUST serve over TLS, and every location the core states at it (`D11-R3`, `D11-R6`) MUST be answered beside the fingerprint of the certificate the door presents, so that a client pins the door as it pins the stack (`N1-R22`). |

## Related

- [ADR-0027](../../../00-overview/decisions/0027-a-member-plays-what-the-core-authorised.md) — the grant and the guard, and what was proved
- [D6](d6-household-identity.md) — who the member is, and removing them
- [D8](d8-parental-controls.md) — the limits the member's own session carries
- [G5](../g-ux/g5-front-door.md) — the household address the locations are built from
- [D4](d4-request-flow.md) — asking for what is not here yet
- [N3](../n-companion/n3-household-companion.md), [G10](../g-ux/g10-household-web.md) — the surfaces that play it
