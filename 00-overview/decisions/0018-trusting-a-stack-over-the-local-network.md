# ADR-0018: Trusting a stack over the local network

**Status:** Proposed
**Date:** 2026-09-11
**Amended by:** [ADR-0025](0025-nothing-leaves-this-machine-unpinned.md) — the fingerprint's written form, how a client enforces it, and the address it permits.

## Context

[ADR-0017](0017-the-companion-app-as-a-fourth-surface.md) settled that the
companion app reaches the stack over the network rather than running on it. That
leaves a question the three existing surfaces never had to answer: **how does the
app know it is talking to the right machine?**

The CLI and TUI are the same process as the core. The web surface talks to it
over loopback, and [C6](../../10-functional/features/c-trust/c6-web-security.md)
binds it to `127.0.0.1` precisely so that the network is not in the trust path.
A phone on the same Wi-Fi has no such luxury. Every byte crosses a network the
operator does not control end to end, shared with whatever else is on it — a
guest laptop, a television, a thermostat.

Three facts decide the shape of the answer.

**A self-hosted stack will present a self-signed certificate.** Nobody is going
to obtain a publicly trusted certificate for `192.168.1.42`, and the names a
stack is reachable under are exactly the names a public CA will not sign. Any
design that assumes the platform trust store will validate the connection is a
design that does not work on the first day.

**The failure mode of not deciding is known and specific.** It is
`'verify' => false`. It appears in a branch called something like "make it work
on my LAN", it removes every guarantee TLS provides, and it does not look like a
security change in review — it looks like a configuration line. Once present it
is invisible, because nothing fails.

**The moment of pairing is the only moment authentication is possible.** After
pairing, the app has no independent way to tell a stack from anything that can
answer on its address. Whatever trust exists later has to be established then,
and carried forward.

## Decision

**The pairing payload carries the stack's expected certificate fingerprint, the
app pins it, and a change to it stops the connection until a human re-pairs.**

Concretely:

1. Pairing material produced by the stack includes the fingerprint of the
   certificate the stack will present. It is not fetched from the network; it
   comes from the same payload as the address, over the same out-of-band channel.
   [ADR-0025](0025-nothing-leaves-this-machine-unpinned.md) fixes its written
   form — SHA-256 over the DER encoding, lower-case hex — because "a
   fingerprint" also names the public-key digest, and confusing the two survives
   review.
2. The app pins that fingerprint against that stack and validates every
   subsequent connection against it, regardless of the platform trust store.
3. A connection presenting a different certificate is **refused**, not warned
   about. The app explains what happened in the operator's language — that this
   machine is not the one it was introduced to — and offers re-pairing as the
   only way forward.
4. Certificate rotation on the stack is therefore a deliberate act that requires
   re-pairing, and the stack is responsible for saying so before it rotates.
   That responsibility is `C6-R19` rather than only this sentence, and it covers
   the case where the stack does not control renewal at all.
5. Verification is never disabled, for any build, under any flag. There is no
   development shortcut, because a development shortcut is the thing being
   guarded against.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Disable verification** | Makes every connection interceptable by anything on the network, and fails silently — the worst combination available. It also does not look like a security change in review; it looks like a configuration line. |
| **Trust on first use, unverified** | Better than nothing and worse than it sounds. An attacker present at the moment of pairing is trusted permanently, and pairing is the one moment an attacker can provoke, by making the real stack briefly unreachable. |
| **A fingerprint read by a human** | Cryptographically sound and genuinely used in practice, but it asks a person to compare sixty-four hex characters across two screens. People check the first four and the last four, or they press accept. |
| **Rely on the platform trust store** | No public CA will sign `192.168.1.42`, and the names a stack is reachable under are exactly the ones they refuse. A design resting on this does not work on the first day. |
| **Ship a CA with the app** | Puts a signing key in something distributed publicly, so every install shares the secret that would let any of them impersonate any stack. |

## Consequences

**The first connection is authenticated, not merely remembered.** This is the
property trust-on-first-use lacks and the reason to prefer this over it: an
attacker present during pairing does not get trusted, because the fingerprint
they would have to match came from the stack's own screen.

**No human compares hex.** The comparison happens in software, which is the only
way it happens reliably. The operator's job is the one people are good at —
confirming that the code on their machine's screen is the one their phone is
reading.

**Rotation costs something.** An operator who replaces the stack's certificate
must re-pair every device. This is a real cost and it is accepted deliberately:
the alternative is an app that accepts a new certificate quietly, which is the
same as an app that accepts any certificate.

A public-key pin would have avoided that cost, and
[ADR-0025](0025-nothing-leaves-this-machine-unpinned.md) considered it and
declined — it accepts a re-issue nobody has to act on, which is the event this
decision exists to make loud. What that ADR changes instead is the other side:
`C6-R19` requires the stack to announce the rotation first, so the alarm does
not fire for a reason the operator was never told about.

**The stack owes the app a fingerprint.** This is a requirement on the stack and
on the SDK contract, not only on the app. Where the SDK does not yet expose it,
`N1-R17` applies: the gap is raised and the dependent work stops rather than
being approximated.

**A stack reachable at several addresses is still one identity.** Pinning is to
the stack, not to the address, so moving between Wi-Fi and a VPN does not
re-open the question.

## Related

- [ADR-0025](0025-nothing-leaves-this-machine-unpinned.md) — the pinned value's
  form, the handshake check that enforces it, and the address it unlocks
- [ADR-0017](0017-the-companion-app-as-a-fourth-surface.md) — the companion as a
  fourth surface, and why reachability is a reported condition
- [C6](../../10-functional/features/c-trust/c6-web-security.md) — why the admin
  surface is loopback by default
- [N1](../../10-functional/features/n-companion/n1-companion-app.md) — connecting,
  the session, and holding more than one stack
