---
id: N27
title: What the phone keeps
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P2
labels: [mobile, storage, security, ux]
requires: [N1, N4]
relates: [N2, N3, N13, G3]
---

# N27 — What the phone keeps

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

The app forgets everything a stack told it when it closes. Opening it again is a
spinner, a stack that is out of reach says only that it is out of reach, and a choice
the operator makes — how soon to ask for the passcode again, which stack comes first —
has nowhere to stay.

This page is what the phone keeps between launches, and the rules for keeping it:
the last reading of each kind per stack, shown for what it is; the operator's own
settings; and a note of what they have already seen, so that the app can say what is
new. How it is kept, and why that way, is
[ADR-0035](../../../00-overview/decisions/0035-what-the-phone-keeps-and-how.md).

## Behaviour

### Opening shows what the phone last knew

A screen that has a kept reading draws it at once, with when it was read, and then
asks the stack (`N1-R24`, `N1-R25`, `N1-R9`). The kept reading is replaced when the
fresh one arrives. Until then, nothing that acts on the stack can be used: a restart,
taking an update or agreeing to anything is shown, disabled, with the reading's age
beside it. A stack that cannot be reached shows what it last said and when, beside
the reason it cannot be reached now.

Four kinds of reading are kept per stack: health, what runs, updates and household.
A repair offer is not kept: it is something the operator agrees to, and an agreement
is only ever given against a fresh offer (`N13-R7`).

### What is kept stays on the phone, sealed

Everything kept is encrypted with a key the phone's secure storage holds, and can be
read only while the phone is unlocked. Nothing kept is ever a password, a sign-in or
pairing material (`N1-R23`), an action the stack did not receive (`N1-R41`) or the
confirmation of one (`N1-R24`). A phone with no secure storage keeps nothing and says
so; a phone whose key has gone — restored onto another device, its keychain reset —
clears what it had kept, keeps its pairings and says once that it did.

### How long, and clearing it

The operator chooses how long readings are kept: any whole number of days from 1 to
365, or until the stack is removed from the phone. It is 30 days until they choose.
Readings older than that are deleted when the app opens and when the setting changes.
Removing a stack from the phone removes everything kept about it. *Clear saved data*
removes every reading, setting and marker the phone keeps, and leaves every stack
paired and signed in.

### Settings the phone remembers

**App settings**, for the whole phone: when to ask for the passcode again (`N4-R19`),
how long readings are kept, the order of the stacks, and clearing saved data. It is
also where a phone with no secure storage says that it keeps nothing.

**A stack's settings**, one per stack: which of the kinds of notification that stack
raises may reach the phone, within the phone's own notification settings, and which
kinds are marked as new. The kinds of notification are the core's (`N4-R11`): a kind
the stack adds appears here without a change to the app.

The app also remembers where the operator was — which stack and which tab — and opens
there, after the lock.

### What is new

For each stack, the phone notes the newest update, request and problem the operator has
seen. Anything newer, of a kind the operator wants marked, is new. An update is newer by
its place in the stack's record, a request by its number, and a problem by when it began
(`C1-R17`), which are the orders the stack itself vouches for (`ARCH-R140`). The tab it
belongs to carries a mark, and *What's new* lists every new item across the stacks,
filtered by kind and by stack. Opening an item marks it as seen; *Mark all seen* clears
the list. A mark is announced to a screen reader and never shown by colour alone.

## States

| State | Meaning |
|-------|---------|
| Kept | A reading from an earlier session, shown with when it was read. Its actions wait. |
| Fresh | Read in this session. Replaces what was kept. |
| Nothing kept | No reading of this kind yet, or none kept for this stack. The only place a spinner may show (`N1-R28`). |
| Not keeping | The phone has no secure storage. Nothing survives a launch, and the app says why. |
| Cleared | The key could not be read. Saved data was removed; pairings stayed. Said once. |
| New | An item newer than the last one seen, of a kind the operator wants marked. |

## Edge cases

- **The first reading of a stack.** Nothing has been seen yet, so nothing is new: the
  first reading records what it holds as seen, and only what arrives after it is marked.
- **A kind switched off in a stack's settings.** Its marks disappear at once; switched
  on again, it starts from what is current, not from everything since it was off.
- **The stack last used has been removed.** The app opens on the first stack in the
  operator's order, or on first run if none is left (`N1-R35`).
- **A reading kept by an older version of the app.** Its shape is not this build's, so
  it is discarded and read again; a setting from an older version is carried over
  (`N1-R32`, `N1-R33`).
- **The lifetime shortened below the age of what is kept.** Everything older is deleted
  at once, not at the next launch.
- **A stack re-paired after moving address.** It is the same stack (`N1-R22`), and what
  was kept for it stays.

## Requirements

| ID | Requirement |
|----|-------------|
| **N27-R1** | The app MUST keep between launches only readings of a stack's health, what it runs, its updates and its household; the operator's settings on this page; and, per stack and kind, an identifier of the newest item seen. It MUST NOT keep anything else a stack sends. |
| **N27-R2** | The app MUST NOT keep a repair offer, an agreement (`N13-R7`), an action the stack did not receive (`N1-R41`) or the confirmation of an action (`N1-R24`), and MUST NOT keep a credential, a session token or pairing material outside the storage `N4-R5` defines (`N1-R23`). |
| **N27-R3** | Everything kept MUST be encrypted with a key held in the platform's secure storage and readable only while the device is unlocked, and MUST NOT be encrypted with a key kept in the application's own files. |
| **N27-R4** | A kept row MUST identify its stack only by a keyed hash, and MUST NOT store the stack's identity, name or address in the clear. |
| **N27-R5** | Where the device offers no secure storage, the app MUST keep nothing between launches and MUST say so on App settings (`N4-R6`). |
| **N27-R6** | Where the key cannot be read, the app MUST delete what it kept, create a new key, keep every pairing and its fingerprint (`N1-R34`), and MUST say once that saved data was cleared. |
| **N27-R7** | A kept reading MUST be shown on opening with when it was read (`N1-R9`), and MUST be replaced by a fresh reading when one arrives. |
| **N27-R8** | While a kept reading is shown and no fresh reading has arrived, every control that acts on the stack MUST be shown and MUST NOT be usable, with the reading's age beside it; such a control MUST NOT be hidden (`N1-R3`). |
| **N27-R9** | The operator MUST be able to set how long readings are kept, as a whole number of days from 1 to 365 or until the stack is removed from the phone, and it MUST be 30 days until they set it. |
| **N27-R10** | Readings older than the kept period MUST be deleted when the app opens and when the period changes. |
| **N27-R11** | Removing a stack from the phone MUST remove every reading, setting and marker kept for it, in the same act. |
| **N27-R12** | *Clear saved data* MUST remove every reading, setting and marker the phone keeps, and MUST NOT remove a pairing or a session. |
| **N27-R13** | A kept reading written in a shape this version does not read MUST be discarded; a kept setting MUST be migrated to the current shape (`N1-R32`, `N1-R33`). |
| **N27-R14** | App settings MUST offer when to ask for the passcode again (`N4-R19`): immediately, which MUST be the choice until the operator sets one, or after 1, 5 or 15 minutes, or 1 hour. |
| **N27-R15** | App settings MUST offer the order of the stacks, and every list of stacks MUST follow it. |
| **N27-R16** | The app MUST open, after the lock, on the stack and tab the operator last used, and on the first stack in their order where that stack is gone. |
| **N27-R17** | Each stack's settings MUST offer, for each kind of notification that stack raises, whether it may reach the phone, and a kind switched off MUST NOT be notified; the kinds offered MUST be the ones the stack declares, and the app MUST NOT add a kind of its own (`N4-R11`). |
| **N27-R18** | Each stack's settings MUST offer which of updates, requests and problems are marked as new. |
| **N27-R19** | An update, request or problem newer than the newest of its kind the operator has seen for that stack MUST be marked as new, where that kind is switched on; the first reading of a stack MUST record what it holds as seen. |
| **N27-R20** | *What's new* MUST list every item marked as new across the stacks, filterable by kind and by stack; opening an item MUST mark it as seen, and the list MUST offer marking everything seen. |
| **N27-R21** | A tab holding an item marked as new MUST carry a mark that a screen reader announces, and the mark MUST NOT rely on colour alone (`N4-R21`). |
| **N27-R22** | Nothing kept MUST be drawn while the app is locked (`N4-R24`). |

## Notes

**Where each thing is kept is a decision about the app, not about behaviour.** Which
module keeps what, the sealing port and the rules that test it are in
[ADR-0035](../../../00-overview/decisions/0035-what-the-phone-keeps-and-how.md); the
companion's architecture document carries each rule beside its test.

**Where these screens sit in the app** — the menu that reaches *What's new*, App
settings and a stack's settings — is the navigation page, not this one.

## Related

- [ADR-0035](../../../00-overview/decisions/0035-what-the-phone-keeps-and-how.md) — how it is kept
- [N1](n1-companion-app.md) — retained readings, shapes and pairings
- [N4](n4-native-integration.md) — secure storage, notifications and the lock
- [N13](n13-taking-away.md) — why an agreement is never kept
- [N2](n2-operator-companion.md), [N3](n3-household-companion.md) — the screens whose readings are kept
- [G3](../g-ux/g3-accessibility.md) — marks a screen reader can hear
