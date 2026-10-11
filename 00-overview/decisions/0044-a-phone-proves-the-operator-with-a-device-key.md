# ADR-0044: A phone proves the operator with a device key, so it never holds the password

**Status:** Accepted
**Date:** 2026-10-11
**Decided:** 2026-10-11, by the maintainer, Wessel Verheij: the companion mints integration keys only as claims, proved by a signature from a key pair held in the phone's hardware and usable only after face or fingerprint, registered once with the operator password and the platform's attestation; StrongBox and the Secure Enclave are preferred, a key in the trusted environment alone is accepted and shown as such, and a key in software is refused; on iOS, `enclave` records that the genuine app placed the key in the Secure Enclave, App Attest vouching for the app rather than the key; only the official NightWorksIO companion's identities and builds the operator adds as a setting may register a device key; attestations are verified against roots shipped in the build, with no request leaving the machine and no revocation list fetched; a password change revokes every device key; the link is handed over as a QR code, as copyable text and through the system share sheet.
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

**A device key proves the operator for one mint.** The phone makes a P-256 key pair in its
hardware, usable only after face or fingerprint: StrongBox or the Secure Enclave where it
has one, its trusted environment otherwise. The operator registers its public half with the
core once, from an operator session, giving the password in that one request with the
platform's attestation of where the key lives
([C10-R23](../../10-functional/features/c-trust/c10-integration-keys.md)). The core verifies
the attestation, records the backing, `strongbox`, `enclave` or `tee`, and shows it in the
listing; a key the attestation places in software, or one with no attestation that
verifies, is refused.

What the attestation proves differs by platform, and the record says no more than it
proves. Android's key attestation vouches for the key itself and the hardware holding it.
Apple's App Attest vouches for a genuine instance of the app and for a hash of client data it
signed, not for any key the app made: the phone sends SHA-256 of the device key's public half
as that client data, so on iOS `enclave` means the genuine app placed the key in the Secure
Enclave, not that the hardware proved it.

**Only an app the core trusts may register a device key.** Every attestation names the app:
its package and the digest of its signing certificate on Android, its Team ID and bundle ID
on iOS. The build ships the official NightWorksIO companion's identities. An operator who
builds the companion themselves adds their build's identity as a setting, at the command
line or over the web API, journaled and alerted (`C10-R29`, `C10-R30`). An attestation from
any other app is refused with a code of its own, so a program that is not the companion
cannot plant a key it controls.

**Verifying an attestation sends nothing out.** The core checks it against the platform
roots shipped in its build and makes no request to do so (`C10-R31`). It does not fetch
Google's revocation list for attestation keys. That is the accepted trade-off: a phone whose
attestation key Google has revoked since the build was made is not caught by that list. The
alternative is a call to Google at every registration, which would tell a third party when
and from where the operator registers a phone, and would make registering depend on a large
company's service being up. The registration still needs the operator password, and the
operator sees every registration in an alert.

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

**Fetching Google's attestation revocation list.** It would catch a phone whose attestation
key has leaked. Rejected: it sends a request to Google for every registration and ties
registering to Google's service, against keeping the operator's business on their own
machine; the password and the alert stand behind every registration instead.

**Any app's attestation.** Simpler, and any program on the phone able to pass attestation
could register a key it controls. Rejected for that reason.

**StrongBox or the Secure Enclave only.** Rejected: many Android phones in use hold keys in
the trusted environment and have no StrongBox, and they would be left with the password.
A key there is still outside the operating system's reach, and the listing says where each
key lives so the operator can judge it.

## Revisit when

- A browser surface wants the same proof. WebAuthn gives a browser the same kind of key,
  and the registration and challenge here are the shape it would take.
