---
id: N9
title: Who gets in, and what the stack holds for them
kind: feature
area: N
audience: operator
status: accepted
maturity: built
priority: P3
labels: [mobile, household, security, ux]
requires: [N1, D6]
relates: [A7, G5, G6, N2, N3]
---

# N9 — Who gets in, and what the stack holds for them

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Inviting somebody into the household, and knowing what the stack is holding to
let them in, are operator jobs done away from the machine more often than at it.
Somebody asks to be added while the operator is on the sofa; a provider password
expires and nothing says which services just stopped working.

`N2` already draws the line on the second one: **the app does not set or change a
credential's value** (`N2-R12`), and it is right — a provider password typed into
a phone over a LAN is not what this product is for. But a prohibition is not a
surface. Nothing today says which credentials exist, what state they are in, or
what stops working when one goes stale.

This is that surface, and it keeps the prohibition.

## Behaviour

### A credential's state is six things, and four of them are trouble

Absent, active, stale, invalid, rotating, superseded. Only *active* is quiet.
*Stale* and *invalid* are different failures with different remedies, and
*rotating* is mid-change rather than broken — an app that rendered them all as a
warning triangle would be throwing away what the core worked out.

### What breaks is named, not implied

Every credential names the services that consume it. **That is the answer to the
question an operator actually has** — not *this key is stale* but *this key is
stale and your indexer and your subtitle fetcher are using it*.

### Where it came from decides who fixes it

A credential set by the operator, one a service issued, and one lemonfiber
generated are three different things to be told about a failing one. The origin
is carried and is shown, on the same argument `F7-R3` already makes for settings.

### Nothing here sets a value

`N2-R12` stands. The app reports state, names consumers, and offers whatever
reconciliation the core has. It does not offer a text field.

Replacing the media server's internal certificate is one of those
reconciliations: the core makes the new certificate and its key on the machine,
and the key never leaves it (`ARCH-R354`). The phone sends the agreement and
reads back public facts — a certificate's SHA-256, the services that hold it,
and what the replacement came to.

### The internal certificate is replaced from its card

The media server's internal certificate is listed like any credential, with the
services that hold its SHA-256 and the SHA-256 of the one in force, short enough
to compare at a glance. Before and after a replacement, that short form is how
the operator sees it landed.

Replacing it is read first. The rehearsal says, in the stack's words, which
services are handed the new SHA-256 and whether the media server restarts, and
the app adds who is watching on it now (`N2-R28`), because a restart stops their
stream. The yes carries back what the rehearsal answered; where that has moved,
the app reads it again rather than calling it a failure.

The replacement is followed to its end. *Replaced* is said only where the stack
says it, and every other outcome in its own words, with each holder and whether
it reached the media server with the new certificate. An outcome short of
replaced offers starting again.

This is not the certificate the phone pinned when it was paired (`N1-R19`). The
screen says so: replacing it does not touch the pairing, and cannot make the app
accept a different machine.

### An invitation says what it grants before it is sent

An invite carries which libraries it opens, what filtering applies, whether
unrated material is let through, and whether the person may make requests. Those
are the whole of what the operator is deciding, and they are shown before the
invitation exists rather than discovered afterwards by what the person can see.

### An invitation expires, and the app says when

An invite stands for a number of hours. An operator who sends one and does not
say so has sent a link that will quietly stop working, and the person on the
other end will think the household is broken rather than that they were slow.

### A client app is rated for the device it would run on

Which app to use is not one answer. It depends on the device, and the contract
rates each pairing — good, workable, poor, fallback — and carries what to use
instead where it is poor. A recommendation without the *instead* is a dead end
on a television somebody already owns.

### Reaching it from away is a different answer from reaching it at home

The contract says where a thing only works on the household network. That is
said plainly, because an operator who sets somebody up on the sofa and sends
them home has not finished.

### The front door says whether its address was chosen or derived

How the household reaches the stack, and what sits beside it, is not a single
URL. Each has what it faces and why, and whether the address was the operator's
choice or worked out. A derived address presented as a decision is a decision
nobody made.

## States

| State | Meaning |
|-------|---------|
| Active | The credential works. Nothing is asked. |
| Stale | It will stop working, with what depends on it. |
| Invalid | It has stopped working, with what depends on it. |
| Rotating | Mid-change. Not rendered as broken. |
| Superseded | Replaced, kept for reference. |
| Pending | An invitation is out and unaccepted, with when it lapses. |
| Unknown | Credentials or the door could not be read. Never rendered as healthy. |

## Edge cases

- **A credential with no consumers.** Shown, and said to have none — that is a
  reason to remove it rather than a reason to hide it.
- **An invitation that lapsed unaccepted.** Distinguished from one the invitee
  declined. Whether the operator ever passed the link on is not something the
  stack can know, so nothing is claimed about it.
- **A device with no good client at all.** The *fallback* rating is an answer and
  is shown as one, with what it costs.
- **A front door reachable only at home, presented to somebody who is not.** The
  app says which it is rather than offering an address that will not answer.

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N9-R1** | A credential MUST be shown with the state the contract gives, and *stale*, *invalid* and *rotating* MUST NOT be flattened into a single warning. |
| **N9-R2** | A credential MUST name the services that consume it. |
| **N9-R3** | A credential's origin MUST be shown beside it. |
| **N9-R4** | The app MUST NOT offer to set or change a credential's value (`N2-R12`), and MUST NOT render its value where the contract carries one. |
| **N9-R5** | An invitation MUST state what it grants — libraries, filtering, unrated material and whether requests may be made — before it is sent. |
| **N9-R6** | An invitation MUST state when it lapses. |
| **N9-R7** | An invitation that lapsed unaccepted MUST be told apart from one the invitee declined. |
| **N9-R8** | A client recommendation MUST be for a named device, MUST carry its rating, and where the rating is poor MUST carry what to use instead. |
| **N9-R9** | Where something only works on the household network, the app MUST say so. |
| **N9-R10** | The front door MUST show what each address faces and why, and MUST say whether it was chosen or derived. |
| **N9-R11** | Credentials or a door that could not be read MUST be told apart from there being none. |
| **N9-R12** | The credentials screen MUST list every grant beside the credential it crosses, with the plugin it is granted to, the capability it is for and when it was approved, and never a value (`ARCH-R325`, `F14-R20`). |
| **N9-R13** | The credentials screen MUST list the media server's internal certificate with its state and every service that holds its SHA-256, MUST show the SHA-256 of the certificate in force in the comparable form of `N1-R51`, and MUST NOT ask for, carry or show its key (`ARCH-R354`). |
| **N9-R14** | The app MUST offer replacing the media server's internal certificate. The replacement MUST be read first and labelled as nothing replaced yet (`N6-R1`), MUST show in the stack's words every service handed the new SHA-256 and whether the media server restarts, and MUST name who is watching on the media server now (`N2-R28`). The yes MUST carry back the offer the stack answered with, and an answer refused because that offer moved MUST be read again rather than reported as a failure (`N2-R27`, `ARCH-R354`). |
| **N9-R15** | After the yes, the app MUST follow the replacement to its end and MUST show it as replaced only where the stack says it was, with the new certificate's SHA-256 in the comparable form of `N1-R51`. Every other outcome MUST be shown in its own words with each holder and whether it reached the media server with the new certificate, and an outcome short of replaced MUST offer starting again. |
| **N9-R16** | Replacing the internal certificate MUST NOT change the certificate the app pins for the stack (`N1-R19`), and the screen offering it MUST say that the phone's pairing is unaffected. |
| **N9-R17** | The internal certificate and replacing it MUST be shown to the operator alone and MUST NOT appear anywhere a member is shown. |

## Notes

| Row | What `credentials` carries | Not carried |
|---|---|---|
| `N9-R13` | `held[]` where `setting` is `internal-certificate`: `fingerprint`, `state`, `consumers` | — |
| `N9-R14` | `internal-certificate-replace` with `dry_run`; `rotated.offer`; `rotated.settled` `rehearsed` with its `detail`; `CRED-4` where the offer moved | Who is watching, which `N2-R28` reads from `playing` |
| `N9-R15` | `internal-certificate-replace` with `offer`; `rotated.settled` in each arm; `rotated.consumers[]`: `consumer`, `reach` with its `detail` | — |

## Related

- [N1](n1-companion-app.md) — connecting, parity, and what the app may claim
- [N2](n2-operator-companion.md) — the verdict, and why nothing here sets a value
- [N3](n3-household-companion.md) — what the person being invited then sees
- [D6](../d-content/d6-household-identity.md) — who is in the household
- [A7](../a-getting-started/a7-credential-management.md) — what is held, and rotating it
- [G5](../g-ux/g5-front-door.md) — how the household reaches the stack
- [G6](../g-ux/g6-client-apps.md) — which app on which device
