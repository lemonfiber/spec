---
id: N4
title: What the app uses of the device
kind: feature
area: N
audience: both
status: draft
maturity: planned
priority: P1
labels: [mobile, security, ux]
requires: [N1, G3]
relates: [A7, B5, C4, G8, N2, N3]
---

# N4 — What the app uses of the device

**Status:** Draft · **Audience:** Both · **Area:** N — Companion

---

## Purpose

A phone offers things a terminal does not — a camera, a secure enclave, a
fingerprint, a notification that arrives when the app is closed — and each one is
a permission somebody grants and a surface somebody can lose.

This feature is the whole of what the app asks of the device, why each is asked
for, and what happens when it is declined. It is separate from
[N1](n1-companion-app.md) because the answer to "what does this app do with my
camera" should be readable in one place by somebody who is not going to read the
rest.

The rule underneath all of it is [G8](../g-ux/g8-privacy.md)'s: nothing leaves
the device that the operator did not ask to send.

## Behaviour

### Every permission is asked for at the moment it is used

Nothing is requested on first launch. The camera is asked for when somebody taps
scan, notifications when they choose to be notified. A permission sheet on
launch, before the person knows what the app is, is a request they cannot
meaningfully answer.

Each one states what it is for in the app's own words before the system asks.

### Every permission is optional, and the app works without it

Declining the camera leaves typed pairing. Declining notifications leaves an app
that is checked rather than one that tells you. Declining biometrics leaves a
passcode. Nothing is a dead end, and nothing is asked for twice after a refusal.

### The session lives in the platform's secure storage

A session token is kept in the Keychain or the Android Keystore, never in
application preferences, never in a file the app writes, and never in a backup
that leaves the device unencrypted.

### The app locks

Anything that can stop a stack or read a household's requests is behind a lock:
biometric where offered, passcode otherwise. It engages on backgrounding rather
than after a timer, because the case it exists for is a phone handed to somebody
for a moment.

Biometric failure falls back to the device passcode. It does not fall back to
nothing.

### Notifications say what happened without saying too much

lemonfiber already decides what is worth telling somebody about
([B5](../b-running/b5-notifications.md)). A notification on a lock screen is
read by whoever is holding the phone, so it carries what happened and never a
credential, a household member's name, or a title somebody requested.

The app does not invent alerts of its own.

### Nothing is sent anywhere else

No analytics, no crash reporting to a third party, no telemetry. A diagnostic the
operator chooses to share is assembled and handed to them
([C4](../c-trust/c4-support-bundle.md)'s rules apply to its contents), and they
send it. The app does not.

### The platform's own accessibility, not a second one

Because the UI is the platform's own components
([ADR-0017](../../../00-overview/decisions/0017-the-companion-app-as-a-fourth-surface.md)),
text scaling, screen readers, contrast and reduced motion are the system's and
are honoured by being used rather than re-implemented.
[G3](../g-ux/g3-accessibility.md)'s bar applies here as it does to every surface.

What the brand does and does not assert on this surface is
[its own mapping](../../../60-brand/surface-mapping.md): the accent, the app icon
and the launch mark, and nothing that would override the reader's own type size
or the system's theme.

## States

| State | Meaning |
|-------|---------|
| Locked | The app is open and showing nothing until unlocked. |
| Unlocked | Normal operation. |
| Permission not asked | The feature needing it has not been used yet. |
| Permission declined | The alternative path is offered; the request is not repeated. |
| No biometric enrolled | Passcode, without presenting biometric as unavailable-and-broken. |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Biometric fails repeatedly | Falls back to the device passcode, never to no lock at all. |
| The device has no secure storage | The app refuses to store a session and says why, rather than writing it somewhere weaker. |
| Notifications are declined after being granted | Honoured immediately; the app does not keep trying. |
| A notification arrives for a stack that has since been removed | Not shown. A notification for a stack the person no longer has is confusing and leaks that it existed. |
| The app is backgrounded mid-repair | The repair is the core's, and continues there. The app locks and reports the outcome when next opened. |
| The OS screenshots the app for its task switcher | The locked screen is what is captured, not the last screen shown. |
| A permission is revoked in system settings while the app runs | Detected at next use and handled as declined, not as an error. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N4-R1** | A permission MUST be requested at the point of first use, and MUST NOT be requested on launch. |
| **N4-R2** | The app MUST state what a permission is for, in its own words, before the system prompt. |
| **N4-R3** | Every permission MUST be optional, and the app MUST offer a working alternative for each declined one. |
| **N4-R4** | A declined permission MUST NOT be requested again automatically. |
| **N4-R5** | A session token MUST be stored in the platform's secure storage, and MUST NOT be written to application preferences, an app-readable file, or an unencrypted backup. |
| **N4-R6** | Where the device offers no secure storage, the app MUST refuse to persist a session and MUST say why. |
| **N4-R7** | The app MUST lock on backgrounding, and MUST require biometric or passcode to resume. |
| **N4-R8** | Biometric failure MUST fall back to the device passcode and MUST NOT fall back to unlocked. |
| **N4-R9** | The task-switcher representation of the app MUST NOT show application content. |
| **N4-R10** | A notification MUST NOT contain a credential, a household member's name, or the title of a requested item. |
| **N4-R11** | The app MUST NOT raise alerts of its own; every notification MUST originate in the core's notification decisions. |
| **N4-R12** | The app MUST NOT send analytics, telemetry or crash reports to any third party. |
| **N4-R13** | A diagnostic report MUST be assembled for the operator to send, and MUST NOT be transmitted by the app. |
| **N4-R14** | The app MUST honour the platform's text scaling, screen reader, contrast and reduced-motion settings, and MUST NOT implement a parallel accessibility layer. |
| **N4-R15** | A notification MUST NOT be shown for a stack no longer configured on the device. |

## Related

- [N1](n1-companion-app.md) — the session this stores and locks
- [G3](../g-ux/g3-accessibility.md) — the accessibility bar every surface is held to
- [G8](../g-ux/g8-privacy.md) — nothing leaves that was not asked to leave
- [B5](../b-running/b5-notifications.md) — where a notification comes from
- [C4](../c-trust/c4-support-bundle.md) — what a diagnostic may contain
