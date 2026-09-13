# ADR-0025: Nothing leaves this machine unpinned

**Status:** Proposed
**Date:** 2026-09-13

## Context

[ADR-0018](0018-trusting-a-stack-over-the-local-network.md) decided that the
companion pins the stack's certificate from pairing material and refuses a
connection presenting a different one. It settled *what is trusted*. It left
three questions that turn out to be one question: **what the pinned value is,
how a client enforces it, and what a client may address once it holds one.**

Two issues found the gaps from opposite ends, and neither can be closed alone.

**The address is refused before a pin could matter.** `ARCH-R60` requires every
client to refuse a base address that does not resolve to loopback, and
`sdk-php`'s `BaseUrl` implements it exactly. So the companion — the one consumer
that is deliberately *not* on the machine — cannot reach a stack at all, and a
pinning seam added above that check would never be reached.

`sdk-php`'s own repo document cites `C6-R1` for the rule. That citation is
wrong: `C6-R1` says admin services bind to loopback *by default*, which is a
statement about where a server listens, not about what a client may dial. The
rule genuinely traces to `ARCH-R60`, whose reason is written down beside it and
is narrower than it looks — a writable API on loopback is reachable from any
page the operator visits, and DNS rebinding defeats a naive origin check.
**That is a browser's threat.** It is why `sdk-ts` should keep the rule
unchanged, and why restating it as an absolute prohibition on every client was a
generalisation nothing asked for.

**"A fingerprint" names two different values, and the wrong one type-checks.**
`ADR-0018` and `N1-R18` say "the fingerprint of the certificate". The option a
developer reaches for, `CURLOPT_PINNEDPUBLICKEY`, pins the
SubjectPublicKeyInfo instead. Both are a SHA-256 and both are 32 bytes, so
confusing them survives review and fails at run time by refusing every
connection to a stack that is entirely correct — which reads to an operator as
the stack being broken and to a developer as pinning being unreliable.

The two values differ, and they differ in the way that decides this. Against one
self-signed certificate and a re-issue of it that keeps the same key:

```
$ openssl x509 -in cert.pem  -outform DER | openssl dgst -sha256
86b25c676b761e9a398081373fec783c2bec970baa255370838aebb5c687841e
$ openssl x509 -in cert2.pem -outform DER | openssl dgst -sha256
a10ead53dd9ded9fc1e6a9086dcd0868f500d5604a11a749a1b0a9188787a364

$ openssl x509 -in cert.pem  -pubkey -noout | openssl pkey -pubin -outform DER \
    | openssl dgst -sha256 -binary | openssl base64
l3ehbj5GiKLuq2UcJ7emYqINC4e/QvB6cHaSh/UDPQQ=
$ openssl x509 -in cert2.pem -pubkey -noout | openssl pkey -pubin -outform DER \
    | openssl dgst -sha256 -binary | openssl base64
l3ehbj5GiKLuq2UcJ7emYqINC4e/QvB6cHaSh/UDPQQ=
```

So a public-key pin survives a re-issue and a certificate pin does not. That is
usually the argument *for* pinning the key, and here it is the argument against:
it is precisely the event `ADR-0018` exists to make loud.

**Both are enforceable during the handshake; only one is on a supported path.**
The reason to prefer a public-key pin would be that it is the only thing a
client can check before it sends anything — an after-the-fact read of the peer
certificate has already handed a session token to an impostor. That turns out
not to be true. Measured through Guzzle against a local TLS server presenting a
self-signed certificate, with a server that records whether any request bytes
ever arrived:

| client | pin | outcome | server saw |
|---|---|---|---|
| stream handler, `ssl.peer_fingerprint` | the certificate's own digest | connected | the request |
| stream handler, `ssl.peer_fingerprint` | a different digest | **refused** | handshake, then nothing |
| cURL handler, `CURLOPT_PINNEDPUBLICKEY` | the certificate's own SPKI | connected | the request |
| cURL handler, `CURLOPT_PINNEDPUBLICKEY` | a different SPKI | **refused** | handshake, then nothing |

Both refuse before a request is written, and both do so with `verify` off, which
is what `N1-R19` requires — the pin holds whether or not the trust store would
have accepted the certificate.

What separates them is which one the HTTP layer intends to keep.
`ssl.peer_fingerprint` is on Guzzle's allow-list of supported stream-context
options. `CURLOPT_PINNEDPUBLICKEY` is on neither its supported nor its
conflicting list, so passing it emits:

```
Since guzzlehttp/guzzle 7.12: Passing CURLOPT_PINNEDPUBLICKEY (10230) in the
"curl" request option is deprecated; guzzlehttp/guzzle 8.0 will reject raw cURL
options outside the built-in cURL option allow-list.
```

The primitive that matches `ADR-0018` is the one the transport supports. The
primitive that would have overturned it is the one scheduled for removal.

## Decision

**A pin is the certificate's digest, it is what permits an address off this
machine, and there is no way to have the second without the first.**

1. **The pinned value stays the certificate**, as `ADR-0018` decided.
   `SubjectPublicKeyInfo` pinning is not adopted: it buys a re-issue that
   nobody has to act on, and a re-issue nobody has to act on is the one thing
   `ADR-0018` is for.

2. **The value has one written form**: SHA-256 over the certificate's DER
   encoding, lower-case hex, sixty-four characters. `N1-R18` says so, so that
   an implementation cannot pick a different digest or a different encoding and
   still claim to satisfy it. This is the half of the confusion that a type
   cannot catch.

3. **A client MUST refuse a base address that is not loopback unless a pin was
   supplied**, and MUST NOT require one for loopback. `ARCH-R60` is narrowed to
   say that rather than to prohibit outright, and `ARCH-R99` states the
   coupling. Loopback keeps needing no pin, because nothing leaves the machine.
   Anything else needs one, because everything does.

   The coupling is the point, and it is deliberately one-directional. Pinning
   is not an option beside a LAN address; it is the thing that produces one.
   There is no configuration in which a client addresses a LAN stack unpinned,
   because there is no order of arguments that reaches it.

4. **The enforcement is the certificate-digest check at handshake time**, and
   in `sdk-php` that is `ssl.peer_fingerprint` on Guzzle's stream handler. A
   check performed after the response arrives is not an implementation of this
   and does not satisfy `N1-R19`.

5. **The seam is constructor-time and closed.** A pin is given to the client
   when it is built, and the client turns it into handler selection and
   transport configuration itself. The SDK does not expose "here are some HTTP
   options": a seam a caller can reach to strengthen verification is a seam
   they can reach to weaken it, and `'verify' => false` is the specific failure
   `ADR-0018` names.

6. **A certificate change stays a deliberate, announced act.** `C6-R19` puts
   that on the stack rather than leaving it as prose in an ADR. An alarm that
   fires for a reason the operator was not warned about is one they learn to
   click through, and that is the whole value of the alarm gone. The answer is
   that the stack says so first — not that the client stops noticing.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Pin the SubjectPublicKeyInfo instead** | Identical security against an impostor, and it survives a re-issue that keeps the key — which sounds like a pure gain and is the decision `ADR-0018` deliberately made the other way. It also reaches the wire only through `CURLOPT_PINNEDPUBLICKEY`, which Guzzle has deprecated and will reject at 8.0, so the version that reads better is the one with a removal date on it. |
| **Read the peer certificate after the handshake** (`CURLOPT_CERTINFO`) | Pins the value `ADR-0018` names, and checks it after the request has been sent. For a request carrying a session token, discovering the impostor in the response is discovering it too late. |
| **Expose the transport's options to the caller** | The smallest change, and it hands every consumer the same seam in both directions. `'verify' => false` does not look like a security change in review; it looks like a configuration line, which is exactly why `ADR-0018` names it. |
| **Leave `ARCH-R60` absolute and give the companion its own client** | Contradicts `N1-R16`, which says every call goes through the SDK and there is no second client. It would also duplicate the envelope, the stream and the error model in the one consumer with the least ability to keep them in step. |
| **Permit a non-loopback address unpinned, and pin separately** | Two independent settings, one of which is easy to forget, and the failure of forgetting it is silent. Making the address depend on the pin means the unsafe combination has no spelling. |
| **Keep loopback-only and wait for remote access** ([I1](../../10-functional/features/i-remote-access/i1-remote-access.md)) | Defers the companion indefinitely behind a feature planned for `0.21.0`, and answers the wrong question: an overlay changes which route the traffic takes, not whether the app may name a machine that is not this one. |

## Consequences

**A pinned connection is HTTP/1.1.** `ssl.peer_fingerprint` is honoured by
Guzzle's stream handler and by nothing else, so choosing the pin chooses the
handler, and that gives up HTTP/2 and connection reuse. Against a stack on a
LAN this is a small cost and it is a real one; it is named here rather than
discovered as a performance regression later. Unpinned loopback callers —
`lemonfiber-web`, every script — are unaffected and keep the default handler.

**The SDK grows a platform requirement it did not have.** `sdk-php` requires
neither `ext-curl` nor `ext-openssl` today. Pinning needs the latter, and a
client asked to pin on a build without it must refuse rather than connect
unpinned.

**`sdk-php` and `sdk-ts` stop having the same rule, for a stated reason.** A
browser cannot resolve a name, has no pin to be given, and is the party
`ARCH-R60`'s DNS-rebinding reasoning is actually about. `sdk-ts` keeps refusing
every non-loopback address and needs no change. The two SDKs are peers of one
contract, not copies, and this is the first place that distinction does work.

**Re-pairing is now something the stack owes a warning about.** `C6-R19` makes
it a requirement on the stack that a certificate change be announced before it
happens. Where the stack does not control renewal — the Caddy overlay obtaining
real certificates — it cannot promise that, and `C6-R19` requires it to say so
at pairing rather than let every device discover it at the next renewal. This is
the honest version of the cost `ADR-0018` accepted, and it is worse-sounding
than silence and better than a surprise.

**The companion is unblocked, and only in the shape this describes.** The guard
`lemonfiber-companion` added — refusing any file that names the SDK's transport
— can be lifted only once the SDK carries the pin, which is the order this was
meant to happen in.

**Revisit if** the transport stops supporting a certificate-digest pin, or the
stack gains a certificate lifecycle it genuinely controls end to end. The first
would force the mechanism question open again; the second would make a
public-key pin cost nothing, at which point the alternatives table's first row
deserves re-reading rather than re-quoting.

## Related

- [ADR-0018](0018-trusting-a-stack-over-the-local-network.md) — the decision this carries to the wire
- [ADR-0013](0013-an-sdk-owns-the-api-client.md) — why there is one client and it is the SDK
- [ADR-0017](0017-the-companion-app-as-a-fourth-surface.md) — the surface that is not on the machine
- [N1](../../10-functional/features/n-companion/n1-companion-app.md) — `N1-R16`, `N1-R18`, `N1-R19`, and what the app does with a pin
- [C6](../../10-functional/features/c-trust/c6-web-security.md) — `C6-R1`, `C6-R19`, and what the stack owes before it rotates
- [web-api](../../20-architecture/contracts/web-api.md) — `ARCH-R60` and `ARCH-R99`, the address rule and its condition
- [sdk-php](../../30-repos/sdk-php.md) — the client that grows the seam
- [sdk-ts](../../30-repos/sdk-ts.md) — the peer that keeps the rule it has
