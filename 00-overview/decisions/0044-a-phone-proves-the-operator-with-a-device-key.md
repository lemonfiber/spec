# ADR-0044: A phone proves the operator with a device key, so it never holds the password

**Status:** Accepted
**Date:** 2026-10-11
**Decided:** 2026-10-11, by the maintainer, Wessel Verheij: the companion mints integration keys only as claims, proved by a signature from a key pair held in the phone's secure hardware and usable only after face or fingerprint, registered once with the operator password; the link is handed over as a QR code, as copyable text and through the system share sheet.
**Amends:** [ADR-0037](0037-an-integration-key-is-minted-where-the-operator-proves-themself.md), whose rule that a web mint asks for the password again gains a second proof.

## Context

ADR-0037 lets an operator session mint an integration key over the web API, and has the
mint ask for the password again, so a session left open cannot mint a key and a forged
request, which cannot know the password, mints nothing.

On a phone that rule costs the operator their password at every mint, typed on a small
keyboard, or it tempts an app into keeping the password to type it for them. A password
kept on a phone is a master credential in a device that is carried everywhere and lost now
and then. Phones already hold something better: a key pair whose private half never leaves
the secure hardware and is used only after the owner's face or fingerprint.

## Decision

**A device key proves the operator for one mint.** The phone makes a P-256 key pair in the
Secure Enclave or in StrongBox, usable only after face or fingerprint. The operator
registers its public half with the core once, from an operator session, giving the password
in that one request ([C10-R23](../../10-functional/features/c-trust/c10-integration-keys.md)).
From then on:

1. The phone asks the core for a challenge, a fresh value good for one request and one
   minute, bound to that session and that device key (`C10-R24`).
2. The operator shows their face or fingerprint, and the phone signs the challenge together
   with the mint it asks for: the name, the scope, the purpose and that it is a claim
   (`C10-R25`).
3. The core verifies the signature against the public half it holds and accepts it in place
   of the password, for that mint alone (`C10-R28`).

A device key is not a credential. It admits no request; it proves the operator to a session
that is already theirs. Every registration and revoke is journaled and alerted as a key's
mint is, the operator lists and revokes device keys by name, and changing the password
revokes them all (`C10-R26`, `C10-R27`).

**The phone mints claims and nothing else.** A claim carries no secret
([C10-R18](../../10-functional/features/c-trust/c10-integration-keys.md)), so the companion
never receives one, and it never calls the door that collects a key
([N29](../../10-functional/features/n-companion/n29-a-key-for-an-app.md)).

**The link goes where the operator sends it.** The screen shows the link as a QR code, as
text that can be copied, and offers the system share sheet. It is concealed from
screenshots, screen recording and the app switcher, says when the claim lapses, and is
gone once left. A link shared on is worth one collection within ten minutes, which the
operator is alerted to (`C10-R21`).

## Consequences

- C10 gains the device key's rows and amends `C10-R2`; the web API gains the device-key
  routes and a mint body that carries a signature in place of the password
  ([getting in](../../20-architecture/contracts/web-api-getting-in.md#an-integration-key)).
- The companion gains N29, and N28's menu gains *App keys* under **Access**.
- A wrong signature counts against the limit wrong passwords meet, so a stolen registration
  name is no better a guess than the password.

## Alternatives considered

**Keeping the password on the phone, behind face or fingerprint.** No change to the core.
Rejected: the master credential would live on the phone, and a copy of the app's storage
taken from an unlocked phone would carry it.

**Asking for the password at every mint.** ADR-0037 as it stands. Rejected for the phone:
it is the friction that pushes an app toward keeping the password.

**Face or fingerprint checked by the app alone.** Rejected: the core would be trusting the
app's word, which a forged request could give.

## Revisit when

- A browser surface wants the same proof. WebAuthn gives a browser the same kind of key,
  and the registration and challenge here are the shape it would take.
