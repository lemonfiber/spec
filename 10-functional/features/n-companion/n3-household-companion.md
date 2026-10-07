---
id: N3
title: The household's companion
kind: feature
area: N
audience: household
status: accepted
maturity: building
priority: P2
labels: [mobile, household, ux]
requires: [N1, D4, D6]
relates: [D7, D8, D11, G5, G6, G9]
---

# N3 — The household's companion

**Status:** Accepted · **Audience:** Household · **Area:** N — Companion

---

## Purpose

The other half of the same application, for the people who did not build the
stack and should never have to think about it.

A household member wants three things: to ask for something, to know whether it
is coming, and to find it when it arrives. They do not want a dashboard, and they
must never be shown a control that would let them stop the stack.

This exists in one app with [N2](n2-operator-companion.md) rather than as a
second product because a household is not two populations — the operator is
usually also a member, and asking somebody to install two apps to watch a film
and to fix the machine that serves it is a worse answer than asking who is
signing in.

## Behaviour

### The credential decides the application

A household identity ([D6](../d-content/d6-household-identity.md)) signs in and
gets this. An operator signs in and gets [N2](n2-operator-companion.md) as well.
There is no setting that switches between them, and no build that contains only
one.

A member signs in on the same screen the operator does, with their household
account's name and password. The operator leaves the name empty and types the
machine's own password. The app does not ask which of the two somebody is: the
stack decides from what was offered. A refusal does not say which of the two was
not recognised, because the stack does not say either (`N3-R18`).

### Entitlement is the core's answer, never a hidden button

What a member may do is decided by the core and rendered here. The app does not
implement a permission model of its own, and a control absent from this
application is absent because the core said so.

That distinction matters the day it is wrong: a bug that shows a control must
still be refused by the core, and never merely by the app having drawn it.

### Asking for something

A member searches, finds a title, and asks for it ([D4](../d-content/d4-request-flow.md)).
What happens next is stated honestly at the point of asking: whether it needs
approval, and whether they have allowance left
([D7](../d-content/d7-approval-quotas.md)).

Somebody who has run out is told so before they ask, not after.

### Four tabs, and nothing technical behind any of them

A member's app is Home, Search, Requests and Profile. Home leads with their own
titles: what they were watching, what arrived that they asked for, and what is on
its way. A title's page has one primary action, and its label is the title's
state: Play, Ask, Waiting for approval, On its way, Out on a date. Nothing a member
sees names a service, a size or how the stack stands, and the stack is *the house*
([G2](../g-ux/g2-plain-language.md)); a failure reads as what it means to them, in
the core's words. Where nothing arrives from the house for the core to voice —
the house cannot be reached, its certificate is not the one the phone was paired
with, or it speaks a version this app does not — the app says so in a household
sentence of its own, such as *Can't reach the house right now*, and does not
present it as the house's words. What a title is, its artwork and where it plays
from are the core's answers
([D11](../d-content/d11-watching-what-the-house-holds.md)).

### Knowing whether it is coming

A request they made carries its state in their terms — waiting on somebody,
approved and being fetched, here, or refused with the reason that was given. Not
a pipeline stage, and not a percentage that means nothing to them.

### Finding it when it arrives

The app plays it. A member who asked for something and was told it had arrived
should be able to watch it where they are standing, and an app that hands them to
a second application they must also install is a household product that stops
short of the thing the household wanted.

The stream comes from the media server over the local network, which is what a
media server is built to serve and what the pairing already knows the address of.
Away from home, playback is declined and says so — the same shape as asking for
something new while the stack is unreachable, and an honest refusal beats a
spinner that never resolves.

**What the player may not do is the whole of what it must get right.** It renders
what the core says a member may watch and holds no second copy of it, so an age
limit is never enforced twice and never disagrees with itself. It implements no
part of asking, approving or allowance. A client the household already uses stays
a first-class way to watch ([G6](../g-ux/g6-client-apps.md)); this is a second
way, not a replacement for one.

### What a member is never shown

No lifecycle controls, no logs, no credentials, no other member's requests, no
diagnostics. Where a member's own request failed for a reason that is really a
stack fault, they are told it did not work and that the operator has been told —
never given the operator's error.

### Parental controls are honoured, not re-implemented

What a member may watch or ask for is already decided
([D8](../d-content/d8-parental-controls.md)). The app renders those limits and
does not hold a second copy of them.

## States

| State | Meaning |
|-------|---------|
| Signed in as a member | The household application. |
| Signed in as the operator | Both applications, with the operator's surface reachable. |
| No allowance left | Asking is declined with when it resets, before a search happens rather than after. |
| Request waiting | Somebody has to approve it, and the app says so. |
| Request refused | Refused, carrying the reason that was given. |
| Request fulfilled | Here, and playable where they are standing. |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| The stack is unreachable | Their own requests are shown from the last read, marked with when. Asking for something new is declined rather than queued, because a queued request is a promise the app cannot keep. |
| A member's request failed because the stack is broken | They are told it did not work and that the operator has been told. They are not shown the fault. |
| Nothing arrives from the house: it cannot be reached, its certificate is not the one paired, or it speaks a version this app does not | The app's own household sentence, such as *Can't reach the house right now*, with no technical term, and not presented as the house's words. |
| A member is also the operator | One sign-in, both applications. They are not asked to choose a mode. |
| A title is already held | Said so before they ask for it again. |
| A member is removed from the household while signed in | The next call is refused by the core, and the app returns to signed-out rather than continuing to render what it had. |
| Parental limits hide a title | It is not shown. The app does not display a title it then refuses to request. |
| The media server cannot be reached while away from home | Play is shown and not usable, saying that watching works at home. Nothing buffers and nothing is queued. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N3-R1** | The application a person is given MUST be decided by the identity that signed in, and MUST NOT be a setting or a separate build. |
| **N3-R2** | The app MUST NOT implement its own permission model; what a member may do MUST be the core's answer. |
| **N3-R3** | A control a member is not entitled to MUST be refused by the core if it is ever reached, and MUST NOT rely on the app having omitted it. |
| **N3-R4** | Before a member asks for something, the app MUST state whether it needs approval and whether they have allowance left. |
| **N3-R5** | A member whose allowance is spent MUST be told before asking, with when it resets. |
| **N3-R6** | A member's own requests MUST carry their state in household terms, and MUST NOT expose pipeline internals. |
| **N3-R7** | A refused request MUST carry the reason that was given. |
| **N3-R8** | *Withdrawn.* The app plays media. What this row protected is stated by `N3-R14`, `N3-R15` and `N3-R16`. |
| **N3-R9** | A member MUST NOT be shown lifecycle controls, logs, credentials, diagnostics, or another member's requests. |
| **N3-R10** | Where a member's request failed because of a stack fault, the app MUST tell them it did not work and that the operator has been told, and MUST NOT show them the fault. |
| **N3-R11** | Parental limits MUST be rendered from the core's answer, and the app MUST NOT hold a second copy of them. |
| **N3-R12** | While the stack is unreachable, asking for something new MUST be declined rather than queued. |
| **N3-R13** | An identity removed from the household MUST result in a signed-out app at the next refused call, and MUST NOT continue to render what was already loaded. |
| **N3-R14** | What a member may watch MUST be the core's answer; the player MUST NOT hold a second copy of a library, an age limit or an entitlement. |
| **N3-R15** | Where the media server cannot be reached, playback MUST be declined with the reason, and MUST NOT be queued or shown as buffering. |
| **N3-R16** | The player MUST NOT implement request, approval or allowance logic of its own. |
| **N3-R17** | A refusal whose code says the household could not be asked MUST be reported to the operator as the media server not answering, and to a member as their library not answering right now, in the core's household sentence (`G4-R16`). It MUST NOT sign the member out, and MUST NOT be reported as the account lacking entitlement (`ARCH-R138`). |
| **N3-R18** | A member MUST be able to sign in to a stack from the app with their household account's name and password, on the same screen the operator signs in on, and a refusal MUST NOT say which of the two was not recognised. |
| **N3-R19** | A member's application MUST have a bottom bar of exactly four tabs (Home, Search, Requests and Profile), and MUST have no side menu. Profile MUST hold *Switch house*, App settings, and *Remove this house from the phone*. The tab whose screen is on view, or the tab the screen on view belongs to, MUST be the only one marked current (`G3-R17`). |
| **N3-R20** | Every sentence a member's screen shows about the stack that the core voices MUST be the core's household sentence (`G4-R16`), rendered and not composed (`N3-R2`). Where the core cannot voice an obstacle because nothing from the house arrives — the house cannot be reached, its certificate does not match the one paired (`N1-R20`), or it speaks a version this app does not (`N1-R13`) — the app MUST show its own household sentence, in plain words with no technical term (`G2-R16`), and MUST NOT present it as the house's own words. A sentence about the phone itself (no network, the local network refused, nowhere to keep a stack) MUST be the app's own, in household words (`G2-R16`). The conditions `N1-R10` tells apart MUST each reach a member as a sentence and a remedy of its own. |
| **N3-R21** | A member MUST be able to search for a title and ask for it from the app. A search MUST show only what the core answers under that member's limits (`D8-R8`). Before the member asks, the title MUST say, in the core's words, whether it is already here, already on its way, needs approval, and what it leaves of their allowance (`N3-R4`, `N3-R5`, `D4-R5`, `D4-R10`, `D7-R15`). The ask MUST be the core's action. |
| **N3-R22** | A title's page MUST carry one primary action whose label follows the title's state as the core answers it: *Play* where it is here and playable from where the phone is; *Play*, not usable, with the reason beside it, where it is here and cannot be played from where the phone is (`N3-R15`); *Ask* where it may be asked for; and otherwise the state itself (waiting for approval, on its way, out on a date, or not available), shown as the action and not usable. The action MUST NOT be hidden in any state. |
| **N3-R23** | Home MUST lead with the member's own titles: what they were part-way through, what they asked for that has arrived, and what they asked for that is on its way. Everything else on Home comes after those. A shelf with nothing in it MUST NOT be drawn. |
| **N3-R24** | Every title MUST carry its name as text. Where the core serves no artwork for a title, it MUST be drawn as a poster lettered with its name. |

## Related

- [N1](n1-companion-app.md) — connecting, and what the app may claim
- [D4](../d-content/d4-request-flow.md) — the request flow rendered here
- [D6](../d-content/d6-household-identity.md) — who is signing in
- [D7](../d-content/d7-approval-quotas.md), [D8](../d-content/d8-parental-controls.md) — allowance and limits
- [G6](../g-ux/g6-client-apps.md), [G9](../g-ux/g9-mobile-handoff.md) — the clients this hands off to
