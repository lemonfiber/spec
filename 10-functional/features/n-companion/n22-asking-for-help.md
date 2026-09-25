---
id: N22
title: Asking for help
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P2
labels: [mobile, security, ux]
requires: [N1, C4]
relates: [N2, N4]
---

# N22 — Asking for help

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

[C4](../c-trust/c4-support-bundle.md) lets an operator ask a stranger for help
without handing the stranger their keys. The asking happens on a forum or in a
chat, and for most people that is a phone: the thread is open there, the reply
arrives there, and the machine is in another room.

So the bundle is made from here, read from here, and handed over from here. What
this page owns is that none of the care the stack takes with a bundle is lost on
the way to a small screen — and that the app adds nothing of its own to it.

This is not the app's own diagnostic report. That one is `N4-R13`'s: something
the app assembles about itself. A support bundle is the stack's file, and the app
is carrying it.

## Behaviour

### What goes in is chosen before it is made, and said before it is written

How much of the logs to take, whether media filenames are shown, and which
redacted settings the operator wants shown as they are, are the choices a bundle
has. They are made before it is written, and the stack answers a request that
writes nothing with what the bundle would hold, how large it would be and where it
would go. That answer is what the operator agrees to.

### Revealing a setting is agreed to one setting at a time

A redacted value shown as it is has been published the moment the bundle is
posted. The app asks for it by name, one setting at a time, and never offers a
single switch that reveals everything. What was revealed is carried in the bundle
itself, and the app shows it with the bundle so the operator reads it before they
send it, not after.

### The contents are readable here, before anything is handed over

Every piece of a bundle is already redacted when the stack answers, and the app
shows each one. An operator who cannot read what they are about to post has been
asked to trust the allow-list with their credentials, and `C4-R7` exists so they
do not have to.

### What is missing is part of the bundle

A bundle from a machine whose diagnostics will not run is the one worth having,
and the stack names what it could not collect. That list is shown with the
bundle, because a gap nobody mentions reads as nothing wrong.

### A refused bundle is a refusal, with its source

Where the stack found a credential that redaction missed, it writes nothing and
names where it came from. That is the whole value of the check, and the app shows
it as that — not as a failure to try again.

### Handing it over is the operator's act

The app hands the file to the device's own sharing, and the operator chooses where
it goes. The app sends it nowhere, uploads it nowhere, and adds nothing to it: no
address of the stack, no session, nothing it holds (`N1-R15`).

## States

| State | Meaning |
|-------|---------|
| Described | What the bundle would hold, how large and where it would go. Nothing is written. |
| Written | The bundle exists on the machine, with its contents readable here. |
| Refused | A residual credential was found; nothing was written, and its source is named. |
| Handed over | The operator passed the file to the device's sharing. |
| Unknown | The answer could not be read. Never rendered as written. |

## Edge cases

- **A bundle asked for while diagnostics cannot run.** Written, with what is
  missing named, rather than refused.
- **An operator re-sharing last week's bundle.** When it was taken and from which
  versions are shown on it, so a stale one reads as stale.
- **The device's sharing is declined.** Nothing left the phone, and the bundle is
  still on the machine.
- **The file cannot be fetched after it was written.** The contents already shown
  stand; the handing-over is refused rather than retried silently.

## Requirements

| ID | Requirement |
|----|-------------|
| **N22-R1** | The app MUST offer producing a support bundle, with the log window, whether media filenames are shown and which settings are revealed chosen before it is written (`C4-R9`, `C4-R13`). |
| **N22-R2** | Before a bundle is written, the app MUST show what it would hold, how large it would be and where it would go, as the stack described them, and writing it MUST be agreed to separately from viewing that description (`C4-R10`). |
| **N22-R3** | A redacted setting MUST be revealed only by naming it and agreeing to reveal it on its own, and the app MUST NOT offer revealing several settings, or all of them, by one agreement (`C4-R8`). |
| **N22-R4** | The settings a bundle reveals MUST be shown with the bundle before it can be handed over. |
| **N22-R5** | Every piece of a bundle MUST be readable in the app before the bundle can be handed over (`C4-R7`). |
| **N22-R6** | What the stack could not collect MUST be shown with the bundle, and MUST NOT be left for the reader to discover by its absence (`C4-R11`). |
| **N22-R7** | When a bundle was taken, and the lemonfiber and stack versions it came from, MUST be shown with it (`C4-R12`). |
| **N22-R8** | A bundle the stack refused to write MUST be shown as refused with the source the stack named, and MUST NOT be rendered as an error to retry (`C4-R5`). |
| **N22-R9** | Handing a bundle over MUST be an act of the operator's through the device's own sharing; the app MUST NOT transmit a bundle anywhere itself (`C4-R6`, `N4-R13`). |
| **N22-R10** | The app MUST NOT add to, alter or annotate a bundle, and MUST NOT put a stack address, a session or anything else it holds into one (`N1-R15`). |

## Notes

**What the contract carries.** `bundle` answers the `support` action, which
takes the log window, the filenames flag, the settings to reveal and whether to
write. The destination is settled by the stack rather than asked for.

| Row | Carried | Not carried |
|---|---|---|
| `N22-R1` | The `support` action's arguments | — |
| `N22-R2` | `bytes` and `would_go` on a run that writes nothing; `path` once written | — |
| `N22-R3` | `reveal` names settings one by one | The settings a bundle *could* reveal, as a list to pick from. The app can only name a setting the operator already knows the name of |
| `N22-R4` | `terms.revealed` | — |
| `N22-R5` | `contents.pieces`, each `name` and its already-redacted `body` | — |
| `N22-R6` | `contents.missing` | — |
| `N22-R7` | `contents.taken`: `at`, `lemonfiber`, `stack` | — |
| `N22-R8` | The refusal, as `error`: its code, meaning, remedies, detail and cause | A field of its own naming the source. `C4-R5` asks for the source named, and the app can show it only where the refusal's words carry it |
| `N22-R9` | The file is served at `/api/bundle/{name}` | That read answers with a file rather than an envelope, and `contract/web-api.contract.json` describes envelopes only. Fetching it through the SDK is `N1-R16`'s question, and where the SDK does not offer it `N1-R17` stops the work |
| `N22-R10` | — | Nothing is needed |

`C4-R14` (room to write) and `C4-R15` (plugins, and their withheld configuration)
are the stack's to answer inside the bundle and its refusals. The app shows what
the pieces and the refusal say, and holds no rule of its own about either.

## Related

- [N1](n1-companion-app.md) — parity, and what the app may never put in a report
- [N4](n4-native-integration.md) — the app's own diagnostic, and the device's sharing
- [N2](n2-operator-companion.md) — the findings a bundle is usually asked for about
- [C4](../c-trust/c4-support-bundle.md) — the support bundle
