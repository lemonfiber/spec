---
id: N29
title: A key for an app
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P2
labels: [mobile, security]
requires: [N1, C10]
relates: [N2, N4, N28, F12, F13, C6]
---

# N29 — A key for an app

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Connecting Home Assistant or an assistant to the stack takes a key
([C10](../c-trust/c10-integration-keys.md)). The operator often holds the stack in their
hand rather than at a terminal, and the program that wants the key often runs on a device
with a camera. This page lets the operator make that key from the phone: as a claim the
program collects once, handed over as a code it can scan, proved by the operator's face or
fingerprint rather than by a password the phone would have to keep
([ADR-0044](../../../00-overview/decisions/0044-a-phone-proves-the-operator-with-a-device-key.md)).

## Behaviour

### App keys

*App keys*, in the menu's **Access** group ([N28](n28-finding-your-way.md)), lists the
stack's keys as the core answers them: each by name, what it admits, what it is for, how it
stands, when it was made and last used, and whether a member made it. A key waiting to be
collected says so. Each key can be revoked, with the core's own sentence for what that does.

### Making a key

The operator names the key, chooses what it admits (*read*, *act*, or one member of the
household) and what it is for (*Home Assistant*, *an assistant*, *something else*). The
phone always makes it as a claim: the core answers with a link that collects the key once,
within ten minutes, and never with the key's secret. The phone never collects a key itself.

### Face or fingerprint, not the password

The first time the operator makes a key from this phone for a stack, the phone makes a key
pair in its hardware, usable only after face or fingerprint, and registers its public half
with the stack, with the platform's attestation of where it lives. The phone uses StrongBox
or the Secure Enclave where it has one, and its trusted environment otherwise; the stack
records which and shows it. That one registration asks for the operator password; it is
sent once and not kept.

From then on, making a key asks for face or fingerprint. The phone asks the stack for a
challenge, signs it together with the key it is asking for, and sends the signature in place
of the password. A phone that can hold the key only in software, or has no face or
fingerprint set up, cannot make a key, and the screen says so and that a key can be made at
the stack's terminal.

*Phone keys*, beside the list, shows the device keys registered with the stack, each with
where it lives, this phone's marked, and lets the operator revoke any of them. Removing a stack from the phone deletes the
phone's own key pair for it.

### Handing the link over

The link is shown as a code to scan, as text that can be copied, and through the phone's own
share sheet, with when the claim lapses. The screen cannot be captured in a screenshot or a
recording and is blank in the app switcher. Once the operator leaves it, the link is gone:
the phone keeps no copy, and a second look means making another key.

## States

| State | Meaning |
|---|---|
| No phone key yet | Making a key first registers one, asking for the password once. |
| Phone key registered | Making a key asks for face or fingerprint. |
| Link shown | The code, the text and the share sheet, with when the claim lapses; concealed. |
| Claim lapsed | The screen says the link no longer collects anything and offers making another. |
| No hardware for the key, or no face or fingerprint | Making a key is not offered; the screen says why and where it can be done. |
| Member | Nothing of this page is offered (`N3-R19`). |

## Edge cases

| Situation | Behaviour |
|---|---|
| The stack is not served so another machine can reach it | The core refuses the claim; the screen says how to serve the stack, as the core says (`C10-R18`). |
| Face or fingerprint fails or is cancelled | Nothing is sent; the form stays as it was. |
| The operator enrols a new face or fingerprint | The phone's key pair stops working; the next mint registers a new one, asking for the password once. |
| The phone's device key was revoked, or the password changed | The stack refuses it; the phone deletes its key pair and registers a new one at the next mint (`C10-R27`). |
| The stack refuses the mint | Shown in the stack's own words (`N1-R77`). |
| The app locks while a link is shown | The link is gone; unlocking does not show it again (`N4-R24`). |

## Requirements

| ID | Requirement |
|----|-------------|
| **N29-R1** | The operator MUST be able to list a stack's integration keys by name, scope, purpose, state, minting time and last use, as the core answers them, with a key waiting to be collected and a member-minted key each marked (`C10-R6`, `C10-R16`, `C10-R18`). |
| **N29-R2** | The operator MUST be able to mint a key only as a claim (`C10-R18`), naming it and choosing its scope, `read`, `act` or `member:<account>` from the household's members, and its purpose (`C10-R17`). The app MUST NOT mint a key whose secret it would receive, and MUST NOT call the door that collects a key (`C10-R20`). |
| **N29-R3** | Minting MUST be proved by a signature from a key pair the app makes in the phone's hardware, usable only after face or fingerprint, over a challenge the core issued for that mint (`C10-R24`, `C10-R25`). The first mint from a phone for a stack MUST register the key pair's public half (`C10-R23`), asking for the operator password for that one request; the app MUST send the password once and MUST NOT keep, log or prefill it. |
| **N29-R4** | The key link MUST be shown as the core gave it, as a QR code drawn from it, as text the operator can copy and through the platform's share sheet, with when the claim lapses. The app MUST NOT construct, alter or keep the link, and MUST NOT show it again once the screen is left or the app locks (`C10-R22`, `N4-R24`). |
| **N29-R5** | The screen showing a key link MUST be concealed from screenshots, screen recording and the app switcher. |
| **N29-R6** | The operator MUST be able to revoke a key by name, shown with the core's sentence for what revoking does, after which the listing MUST show it as the core answers it (`C10-R6`). |
| **N29-R7** | The operator MUST be able to list the stack's device keys, each with its backing as the core answers it, this phone's marked, and revoke any of them (`C10-R26`). Removing a stack from the phone MUST delete the phone's key pair for it, and a key pair the stack refuses as unregistered MUST be deleted and registered again at the next mint. |
| **N29-R8** | The app MUST make the key pair in StrongBox or the Secure Enclave where the phone has one, and in its trusted environment otherwise, and MUST register it with the platform's attestation of where it lives (`C10-R23`). Where the phone can hold the key pair only in software or has no face or fingerprint enrolled, minting MUST NOT be offered, and the screen MUST say why and that a key can be minted at the stack's terminal. |
| **N29-R9** | A refused mint, registration or revoke MUST be shown in the core's words; where the stack is not served so another machine can reach it, the screen MUST say how to serve it, as the core says (`C10-R18`). |
| **N29-R10** | Nothing of this page MUST be offered to a member (`N3-R19`). |

## Notes

**Claims only, by decision.** A key minted with its secret would put that secret on the
phone, in its memory and its share sheet. A claim puts there a link worth one collection
within ten minutes, which the operator is alerted to.

## Related

- [C10](../c-trust/c10-integration-keys.md) — keys, claims and device keys
- [N28](n28-finding-your-way.md) — where *App keys* sits in the menu
- [N4](n4-native-integration.md) — the lock, concealment and the phone's hardware keys
- [F12](../f-extensibility/f12-home-assistant.md) and [F13](../f-extensibility/f13-mcp.md) — the programs that collect a key
- [ADR-0044](../../../00-overview/decisions/0044-a-phone-proves-the-operator-with-a-device-key.md) — why the phone proves the operator with a device key
