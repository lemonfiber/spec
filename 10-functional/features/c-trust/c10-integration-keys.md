---
id: C10
title: Integration keys
kind: feature
area: C
audience: operator
status: accepted
maturity: planned
labels: [security, web]
relates: [C6, F12, F13, G1, B5]
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
The core keeps a digest only.

### Minting over the web asks for the password again

From the web console or the companion, only an operator session may mint or revoke, and
minting asks for the password in the same request. A key never mints, lists or revokes keys.

### A member may mint their own, once the operator allows it

A setting, off until the operator turns it on, lets a household member mint and revoke a
`member:` key for themselves from the companion or the household web. Such a key is scoped
to that member alone, shown once like any other, and the operator sees it in the listing
and can revoke it. This is how a member connects an assistant through
[F13](../f-extensibility/f13-mcp.md): turning the setting on is what lets a member's data
reach a program they chose.

### A key says what it is for

Each key carries a purpose given when it is minted: `home-assistant`, `mcp` or `other`. The
listing shows it so the operator can tell keys apart. It is a label the minter chose, not
something the core can verify, and the listing says so.

### Revoking is immediate, and every change is heard

Keys are listed by name, scope, minting time and last use, and revoked by name. A revoked
key is refused at its next request. Every mint and revoke is journaled and raises an
operator alert naming the key and its scope.

### What a key may call is published

Each action declares whether a key may call it, and the contract lists those that may. The
list starts as restarting a service, running the doctor, applying a stack update, and
pausing or resuming downloads.

## States

| State | Meaning |
|---|---|
| `active` | Admitted within its scope |
| `revoked` | Refused as a wrong token is; kept in the listing with when it was revoked |
| `orphaned` | A `member:` key whose account has left the household; refused, and listed so the operator can revoke it |

## Edge cases

| Situation | Behaviour |
|---|---|
| A key is presented over plain HTTP from another machine | Refused. A key is accepted off loopback only over the TLS the pin verifies. |
| A key's member account is removed from the household | Refused from then on, listed as orphaned. |
| Two keys are minted under one name | Refused, naming the existing key. A name identifies one key. |
| A key asks for an action not on the list | Refused, naming the key's scope and that the action is not callable by a key. |
| Many wrong keys in a short time | Counted against the same surface-wide limit as wrong passwords. |
| The password changes | Sessions end (C6). Keys stay, since they were minted deliberately and are revoked deliberately. |
| A member tries to mint a key while the setting is off | Refused, saying the operator has not allowed members to mint keys. |
| A member tries to mint a key for another account | Refused. A member mints only `member:` keys for themselves. |
| The operator turns the setting off | Members can no longer mint. Keys they already minted stay until revoked, and the listing marks them as member-minted. |
| A key is presented while the web surface is loopback-bound | Admitted from this machine. A client elsewhere cannot reach it, which is C6's binding, not the key's refusal. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **C10-R1** | An operator MUST be able to mint a named key with exactly one scope, `read`, `act` or `member:<account>`, at the command line and over the web API. |
| **C10-R2** | Over the web API, only an operator session MUST be able to mint or revoke a key, except as `C10-R15` allows a member, and minting MUST require the operator password in the same request. A key MUST NOT be able to mint, list or revoke keys, whatever its scope. |
| **C10-R3** | A key's secret MUST appear only in the reply that minted it, sent with `Cache-Control: no-store`, and MUST be stored only as a digest. No read, listing, log, support bundle, alert or journal entry MUST carry it. |
| **C10-R4** | The mint reply MUST carry the stack's address and its certificate pin beside the secret. |
| **C10-R5** | A key MUST survive a restart and MUST travel in `X-Lemonfiber-Token`. A revoked, orphaned or unknown key MUST be refused exactly as a wrong token is, with the same status, sentence and code, from its next request. |
| **C10-R6** | Keys MUST be listed by name, scope, state, minting time and last use, without their secrets, and MUST be revocable by name, at the command line and over the web API. |
| **C10-R7** | A `read` key MUST be admitted to every served read and the event stream and to no action. |
| **C10-R8** | An `act` key MUST be admitted to what `read` admits and to exactly the actions the contract publishes as callable by a key. Any other action MUST be refused, naming the key's scope. |
| **C10-R9** | The actions callable by a key MUST be published in the contract. Uninstalling, any action on a credential, a key or the password, installing, updating or removing a plugin, a reset and a restore MUST NOT be callable by a key. |
| **C10-R10** | A `member:<account>` key MUST be admitted to exactly what that account's own session admits, and MUST be refused once the account leaves the household. |
| **C10-R11** | A key MUST NOT be accepted from another machine except over the TLS its pin verifies. |
| **C10-R12** | Every mint and revoke MUST be journaled and MUST raise an operator alert naming the key and its scope. |
| **C10-R13** | Wrong keys MUST count against the same surface-wide limit as wrong passwords. |
| **C10-R14** | Minting a key under a name another key holds MUST be refused, naming that key. |
| **C10-R15** | A setting, off by default and changeable only by the operator, MUST decide whether household members may mint keys. While it is on, a member session MUST be able to mint and revoke a `member:` key scoped to that member alone, and MUST NOT be able to mint any other scope or a key for another account. |
| **C10-R16** | A member-minted key MUST be listed to the operator, marked as member-minted, and MUST be revocable by the operator as well as by the member. Its mint and revoke MUST be journaled and MUST alert the operator (`C10-R12`). |
| **C10-R17** | Every key MUST carry a purpose chosen when it is minted, `home-assistant`, `mcp` or `other`, shown in the listing as the minter's declaration rather than as anything the core verified. |

## Related

- [C6 Web UI security & binding policy](c6-web-security.md) — who can reach the surface at all
- [F12 Home Assistant](../f-extensibility/f12-home-assistant.md) — the first program that holds a key
- [ADR-0037](../../../00-overview/decisions/0037-an-integration-key-is-minted-where-the-operator-proves-themself.md) · [ADR-0031](../../../00-overview/decisions/0031-a-plugin-and-a-choice-are-web-writes-a-credential-is-not.md) · [ADR-0025](../../../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md)
