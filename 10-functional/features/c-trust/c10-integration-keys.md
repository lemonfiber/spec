---
id: C10
title: Integration keys
kind: feature
area: C
audience: operator
status: accepted
maturity: building
labels: [security, web]
relates: [C6, D10, F12, F13, G1, B5, N29]
---

# C10 — Integration keys

**Status:** Accepted · **Audience:** Operator · **Area:** C — Trust & correctness

---

## Purpose

Let another program read the stack, and do a short list of things to it, without holding
the operator's password ([ADR-0037](../../../00-overview/decisions/0037-an-integration-key-is-minted-where-the-operator-proves-themself.md)).

The per-run token and the password session suit a person at a screen. A program that runs
for months beside the stack, such as Home Assistant ([F12](../f-extensibility/f12-home-assistant.md)),
needs a credential that outlives a restart and can do less than the operator.

## Behaviour

### A key has a name and one scope

The operator mints a key under a name, at the command line or from the web console or the
companion, and gives it one scope:

| Scope | Admits |
|---|---|
| `read` | Every served read and the event stream |
| `act` | `read`, and the actions the contract publishes as callable by a key |
| `member:<account>` | What that household member's own session admits, and no more |

### The secret is shown once

The reply that minted a key is the only place its secret ever appears. It also carries the
stack's address and certificate pin, which is everything a client on another machine needs
to connect ([ADR-0025](../../../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md)).
The core keeps a digest only. Every secret begins with the same short prefix, so a value
shaped like a key can be told from a token or a session without being looked up.

Where the stack has never been served encrypted on the network, there is no address yet for
a client elsewhere to reach. The key is minted all the same: the reply carries the pin, no
address, and a caution saying how to serve the stack so another machine can connect.

### Minting over the web asks for the password again, or a device's signature

From the web console or the companion, only an operator session may mint or revoke, except
as a member may for themselves (below), and minting asks for the operator's proof in the
same request: the password, or a signature from a device key the operator registered
(below). A key never mints, lists or revokes keys.

### A phone proves the operator with a key it cannot give away

A phone can hold a key pair whose private half lives in its hardware, the Secure Enclave,
StrongBox or the processor's trusted environment, and can be used only after the
operator's face or fingerprint
([ADR-0044](../../../00-overview/decisions/0044-a-phone-proves-the-operator-with-a-device-key.md)).
The operator registers its public half with the core once, from an operator session, giving
the password in that one request, with the platform's attestation of where the key lives:
on Android the key's attestation chain, on iOS an App Attest attestation whose client data
is the SHA-256 of the public half. The core verifies the attestation and records the key's
backing, `strongbox`, `enclave` or `tee`. Android's attestation vouches for the key's
hardware. App Attest vouches for the app instance and the client data it signed, not for the
key: on iOS, `enclave` means the genuine app placed the key in the Secure Enclave, not that
the hardware proved it.

**Only an app the core trusts may register one.** The attestation names the app that made
the key, by its package and the digest of its signing certificate on Android, and by its
Team ID and bundle ID on iOS. The build ships the official NightWorksIO companion's
identities; an operator running a build of their own adds its identity as a setting, at the
command line or over the web API. An attestation from any other app is refused.

**Verifying needs nothing from outside.** The core checks an attestation against the
platform roots shipped in the build, and sends no request to do it. It does not fetch
Google's revocation list for attestation keys, so a phone whose attestation key Google has
since revoked is not caught by that list ([ADR-0044](../../../00-overview/decisions/0044-a-phone-proves-the-operator-with-a-device-key.md)). StrongBox and the Secure Enclave are preferred, and a key in the
trusted environment alone is accepted and shown as such; a key held in software, or one
whose attestation is missing or does not verify, is refused. The core keeps the public half
and its backing under a name, journals the registration and alerts the operator, as it does
for a key.

To mint, the phone asks the core for a challenge: a fresh value, good for one request, for
one minute, from that session and for that device key alone. The phone signs the challenge
with the mint it asks for, after the operator's face or fingerprint, and sends the
signature in place of the password. The core checks the signature against the public half
it holds and accepts it as the operator's proof for that mint and nothing else. The
password is never kept on the phone, and a device key admits nothing on its own: it proves
the operator to a session that is already theirs.

The operator lists device keys by name, backing, when each was registered and last used,
and revokes one by name. Changing the operator password revokes every device key, so a phone that is
lost is cut off by the same act that ends its sessions.

### A member may mint their own, once the operator allows it

A setting, `LEMONFIBER_MEMBER_KEYS`, off until the operator turns it on, lets a household
member mint a `member:` key for themselves from the companion or the household web. Minting
asks for the member's own password in the same request, checked by the media server as
their sign-in is and counted against the same limits, for the reason the operator's mint
asks for theirs. Such a key is scoped to that member alone, shown once like any other, and
the operator sees it in the listing and can revoke it. A member's own listing shows only
their keys, and they revoke only those: another member's key is, to them, no key at all.
Turning the setting off stops new mints; a member can still revoke the keys they already
hold, since a revoke only takes access away. This is how a member connects an assistant through
[F13](../f-extensibility/f13-mcp.md): turning the setting on is what lets a member's data
reach a program they chose.

### A key says what it is for

Each key carries a purpose given when it is minted: `home-assistant`, `mcp` or `other`. The
listing shows it so the operator can tell keys apart. It is a label the minter chose, not
something the core can verify, and the listing says so.

### Revoking is immediate, and every change is heard

Keys are listed by name, scope, minting time and last use, and revoked by name. A revoked
key is refused at its next request. Every mint and revoke is journaled and raises an
operator alert naming the key and its scope. A mint is journaled as reversible, and undoing
it revokes the key. A revoke is journaled as not reversible, because a revoked key is never
made good again: the remedy is to mint a new one.

### What a key may call is published

Each action declares whether a key may call it, and the contract lists those that may. The
list starts as restarting a service, running the doctor with the checks that disturb the
system, applying a stack update, and pausing or resuming downloads
([D10](../d-content/d10-bandwidth.md)). Each entry says whether the action disturbs the
running system and whether it can be rehearsed, so a client can rehearse an action first
and offer the real call after.

## States

| State | Meaning |
|---|---|
| `active` | Admitted within its scope |
| `revoked` | Refused as a wrong token is; kept in the listing with when it was revoked |
| `orphaned` | A `member:` key whose account has left the household; refused, and listed so the operator can revoke it |

## Edge cases

| Situation | Behaviour |
|---|---|
| A key is presented over plain HTTP from another machine | Refused before the key is checked, with a refusal code of its own. A key is accepted off loopback only over the TLS the pin verifies. |
| A request arrives over a connection whose origin cannot be placed | Treated as coming from another machine over plain HTTP, and refused the same way. |
| A key's member account is removed from the household | Refused from then on, listed as orphaned. |
| Two keys are minted under one name | Refused, naming the existing key. A name identifies one key. |
| A key asks for an action not on the list | Refused, naming the key's scope and that the action is not callable by a key. |
| Many wrong keys in a short time | A value shaped like a key that matches no key counts against the same surface-wide limit as wrong passwords. |
| A revoked or orphaned key keeps being presented | Refused as a wrong token is, and not counted: it is a key the stack knows, not a guess, and counting it would let a forgotten integration lock the operator out. |
| A key is presented while the limit holds | Refused with the wait before the key is checked, a right key included. A right key does not reset the count. |
| A key is minted before the stack has been served encrypted on the network | Minted. The reply carries the pin and no address, and says how to serve the stack so another machine can connect. |
| The password changes | Sessions end (C6). Keys stay, since they were minted deliberately and are revoked deliberately. Every device key is revoked, journaled and alerted. |
| A mint carries a signature from a device key that is not registered, or revoked | Refused with a code of its own, before the challenge is looked at. |
| A mint carries a challenge that was never issued, was spent, lapsed, or was issued to another session or device key | Refused with one code for all of these, so a guess learns nothing about which. |
| A signature does not verify | Refused with a code of its own, and counted against the same surface-wide limit as wrong passwords. |
| A device key is registered under a name another holds, or with a public half another holds | Refused, naming the existing device key. |
| A public half that is not a P-256 key | Refused with a code of its own, naming the curve the core accepts. |
| A device key registered with no attestation | Refused with a code of its own: a key nothing vouches for is treated as one held in software. |
| An attestation that does not verify, or does not cover the public half given | Refused with a code of its own. |
| An attestation that places the key in software | Refused with a code of its own, saying a device key has to live in the phone's hardware. |
| A key in the trusted environment alone | Registered, with its backing recorded as `tee` and shown in the listing. |
| An attestation names an app the core does not trust | Refused with a code of its own, naming the app's identity and that the operator can add it as a setting. |
| The operator removes an app identity they added | Every device key registered from that app is revoked, journaled and alerted. |
| A device key is presented as a credential | It is none: a request carrying only a device key's signature, with no operator session, is refused as a request with no credential is. |
| A member tries to mint a key while the setting is off | Refused with a code of its own, saying the operator has not allowed members to mint keys, before their password is checked. |
| A member tries to mint a key for another account | Refused. A member mints only `member:` keys for themselves. |
| A member gives a wrong password when minting | Refused as a wrong password is, and counted against the same limits as a sign-in. |
| A member names a key that is not theirs | Listed, revoked and refused as a key that does not exist. |
| The operator turns the setting off | Members can no longer mint. Keys they already minted stay until revoked, members can still revoke their own, and the listing marks them as member-minted. |
| A key is presented while the web surface is loopback-bound | Admitted from this machine. A client elsewhere cannot reach it, which is C6's binding, not the key's refusal. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **C10-R1** | An operator MUST be able to mint a named key with exactly one scope, `read`, `act` or `member:<account>`, at the command line and over the web API. |
| **C10-R2** | Over the web API, only an operator session MUST be able to mint or revoke a key, except as `C10-R15` allows a member, and minting MUST require the operator's proof in the same request: the operator password, or a signature from a registered device key over a challenge the core issued for that request (`C10-R24`, `C10-R25`). A key MUST NOT be able to mint, list or revoke keys, whatever its scope. |
| **C10-R3** | A key's secret MUST appear only in the reply that minted it or, for a key minted as a claim, only in the reply that collected it (`C10-R20`), sent with `Cache-Control: no-store`, and MUST be stored only as a digest. No read, listing, log, support bundle, alert or journal entry MUST carry it. |
| **C10-R4** | The mint reply MUST carry the stack's certificate pin beside the secret, and the stack's address where it has been served encrypted on the network. Where it has not, the reply MUST carry no address and MUST say how to serve the stack so another machine can connect. |
| **C10-R5** | A key MUST survive a restart and MUST travel in `X-Lemonfiber-Token`. A revoked, orphaned or unknown key MUST be refused exactly as a wrong token is, with the same status, sentence and code, from its next request. |
| **C10-R6** | Keys MUST be listed by name, scope, state, minting time and last use, without their secrets, and MUST be revocable by name, at the command line and over the web API. |
| **C10-R7** | A `read` key MUST be admitted to every served read and the event stream and to no action. |
| **C10-R8** | An `act` key MUST be admitted to what `read` admits and to exactly the actions the contract publishes as callable by a key. Any other action MUST be refused, naming the key's scope. |
| **C10-R9** | The actions callable by a key MUST be published in the contract, each saying whether it disturbs the running system and whether it can be rehearsed. Uninstalling, any action on a credential, a key or the password, installing, updating or removing a plugin, a reset and a restore MUST NOT be callable by a key. |
| **C10-R10** | A `member:<account>` key MUST be admitted to exactly what that account's own session admits, and MUST be refused once the account leaves the household. |
| **C10-R11** | A key MUST NOT be accepted from another machine except over the TLS its pin verifies. A key presented from another machine without it, or over a connection whose origin cannot be placed, MUST be refused before it is checked, with a refusal code of its own. |
| **C10-R12** | Every mint and revoke MUST be journaled and MUST raise an operator alert naming the key and its scope. A mint MUST be journaled as reversible, its undo revoking the key, and a revoke MUST be journaled as not reversible. |
| **C10-R13** | A presented value shaped like a key that matches no key MUST count against the same surface-wide limit as wrong passwords, and a revoked or orphaned key MUST NOT. While that limit holds, a request carrying a value shaped like a key MUST be refused with the wait before the value is checked, and a right key MUST NOT reset the count. |
| **C10-R14** | Minting a key under a name another key holds MUST be refused, naming that key. |
| **C10-R15** | A setting, `LEMONFIBER_MEMBER_KEYS`, off by default and changeable only by the operator, MUST decide whether household members may mint keys. While it is on, a member session MUST be able to mint a `member:` key scoped to that member alone, giving their own password again in the same request, checked by the media server and counted against the same limits as their sign-in, and MUST NOT be able to mint any other scope or a key for another account. While it is off, a member's mint MUST be refused with a refusal code of its own, and a member MUST still be able to revoke the keys scoped to them. |
| **C10-R16** | A member-minted key MUST be listed to the operator, marked as member-minted, and MUST be revocable by the operator as well as by the member. Its mint and revoke MUST be journaled and MUST alert the operator (`C10-R12`). A member's listing MUST show only the keys scoped to them, and a key that is not theirs MUST be answered to them as a key that does not exist. |
| **C10-R17** | Every key MUST carry a purpose chosen when it is minted, `home-assistant`, `mcp` or `other`, shown in the listing as the minter's declaration rather than as anything the core verified. |
| **C10-R18** | A key MUST be able to be minted as a claim, at the command line and over the web API. Its reply MUST carry no secret but a key link, `lemonfiber://key?` followed by these parameters, percent-encoded and no others: `address`, `fingerprint`, `stack`, `expires` and `claim`. The listing MUST show the key as waiting to be collected until it is. Where the reply could carry no address (`C10-R4`), a claim MUST NOT be minted, and the refusal MUST say how to serve the stack so another machine can connect. |
| **C10-R19** | The core MUST keep a claim only as a hash on the key it was minted for. A claim MUST collect its key once, and only within ten minutes of the mint; collecting, lapsing or the key's revocation MUST end it. |
| **C10-R20** | A key MUST be collected by a request carrying its claim alone, in the body, over the TLS the link's fingerprint verifies (`C10-R11`). The reply MUST carry the key's secret, name, scope and the stack's pin, sent with `Cache-Control: no-store`. An unknown, spent or lapsed claim MUST be refused with one status, sentence and code, and MUST count against the same surface-wide limit as wrong passwords (`C10-R13`). |
| **C10-R21** | Collecting a key MUST be journaled and MUST raise an operator alert naming the key, its purpose and the address it was collected from. A key whose claim lapses uncollected MUST be revoked, journaled as not reversible, and alerted. |
| **C10-R22** | Every surface that shows a key link MUST also draw it as a QR code from the link, and MUST NOT show the link or the code again once that screen is left. |
| **C10-R23** | An operator session MUST be able to register a device key over the web API: a name, the public half of a P-256 key pair and the platform's attestation of where the key lives (an Android key attestation chain, or an iOS App Attest attestation whose client data is the SHA-256 of the public half), with the operator password in the same request. The core MUST verify the attestation and record the key's backing as `strongbox`, `enclave` or `tee`, `enclave` meaning on iOS that App Attest vouched for the genuine app that placed the key there, not that the hardware proved it, and MUST refuse, each with a code of its own, a registration with no attestation, an attestation that does not verify or does not cover the public half, and an attestation placing the key in software. The core MUST keep only the public half and its backing under that name, MUST refuse a name or a public half another device key holds, naming it, and MUST refuse a public half that is not a P-256 key with a code of its own. A member session and a key MUST NOT be able to register, list or revoke device keys. Every registration MUST be journaled and MUST raise an operator alert naming the device key. |
| **C10-R24** | An operator session MUST be able to ask for a challenge for a registered device key. The core MUST issue a fresh random value of at least 32 bytes, keep it only in memory, bound to that session and that device key, and accept it for one request within one minute; using it, its lapsing, the session ending and the device key's revocation MUST end it. |
| **C10-R25** | A mint carrying a device key's name, a challenge and a signature in place of the password MUST be admitted only where the device key is registered, the challenge stands for that session and that device key, and the signature verifies against the device key's public half over the challenge and the mint's name, scope, purpose and whether it is a claim, in the form the contract publishes. An unregistered or revoked device key MUST be refused with a code of its own; a challenge that does not stand, for any reason, with one code; and a signature that does not verify with a code of its own, counted against the same surface-wide limit as wrong passwords (`C10-R13`). |
| **C10-R26** | Device keys MUST be listed by name, the fingerprint of their public half, their backing, registration time and last use, and MUST be revocable by name, over the web API, with effect at the next challenge. Every revoke MUST be journaled as not reversible and MUST raise an operator alert naming the device key. |
| **C10-R27** | Changing the operator password MUST revoke every device key, journaled and alerted as `C10-R26` says. |
| **C10-R28** | A device key's signature MUST prove the operator for the one mint it was made for and nothing else: it MUST NOT admit a request, stand in for a session or the password anywhere else, or be accepted without an operator session. |
| **C10-R29** | The core MUST register a device key only where its attestation names an app identity the core trusts: the package and the SHA-256 digest of its signing certificate on Android, the Team ID and bundle ID on iOS. The build MUST ship the official NightWorksIO companion's identities, and an attestation naming any other app MUST be refused with a code of its own, naming the identity. |
| **C10-R30** | The operator MUST be able to add and remove the identities of their own builds as a setting, at the command line and over the web API (`ARCH-R262`); each change MUST be journaled and MUST raise an operator alert naming the identity, the official identities MUST NOT be removable, and removing an identity MUST revoke every device key registered from it. |
| **C10-R31** | The core MUST verify an attestation against the platform roots shipped in its build and MUST NOT send any request to verify one, a revocation list included. |

## Related

- [C6 Web UI security & binding policy](c6-web-security.md) — who can reach the surface at all
- [F12 Home Assistant](../f-extensibility/f12-home-assistant.md) — the first program that holds a key
- [N29 A key for an app](../n-companion/n29-a-key-for-an-app.md) — minting a claim from the phone, proved by a device key
- [ADR-0037](../../../00-overview/decisions/0037-an-integration-key-is-minted-where-the-operator-proves-themself.md) · [ADR-0044](../../../00-overview/decisions/0044-a-phone-proves-the-operator-with-a-device-key.md) · [ADR-0031](../../../00-overview/decisions/0031-a-plugin-and-a-choice-are-web-writes-a-credential-is-not.md) · [ADR-0025](../../../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md)
