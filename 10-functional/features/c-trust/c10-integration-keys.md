---
id: C10
title: Integration keys
kind: feature
area: C
audience: operator
status: accepted
maturity: built
labels: [security, web]
relates: [C6, D10, F12, F13, G1, B5]
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

### Minting over the web asks for the password again

From the web console or the companion, only an operator session may mint or revoke, except
as a member may for themselves (below), and minting asks for the password in the same
request. A key never mints, lists or revokes keys.

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
| The password changes | Sessions end (C6). Keys stay, since they were minted deliberately and are revoked deliberately. |
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
| **C10-R2** | Over the web API, only an operator session MUST be able to mint or revoke a key, except as `C10-R15` allows a member, and minting MUST require the operator password in the same request. A key MUST NOT be able to mint, list or revoke keys, whatever its scope. |
| **C10-R3** | A key's secret MUST appear only in the reply that minted it, sent with `Cache-Control: no-store`, and MUST be stored only as a digest. No read, listing, log, support bundle, alert or journal entry MUST carry it. |
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

## Related

- [C6 Web UI security & binding policy](c6-web-security.md) — who can reach the surface at all
- [F12 Home Assistant](../f-extensibility/f12-home-assistant.md) — the first program that holds a key
- [ADR-0037](../../../00-overview/decisions/0037-an-integration-key-is-minted-where-the-operator-proves-themself.md) · [ADR-0031](../../../00-overview/decisions/0031-a-plugin-and-a-choice-are-web-writes-a-credential-is-not.md) · [ADR-0025](../../../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md)
