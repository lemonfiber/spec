# ADR-0054: A media server credential crosses the stack only over TLS the core pins

**Status:** Accepted
**Date:** 2026-10-27
**Decided:** 2026-10-27, by the maintainer, Wessel Verheij:

- the filler of `identity.source` serves an internal TLS port with a certificate the core
  makes for its service name, as it makes the guarded door's;
- every service the core hands a media server credential reaches the media server only at
  that port, and accepts only a certificate whose SHA-256 the core handed it with the
  credential: the decline service through `invite.decline`'s `hold`, amended in place at
  `@1`, and the request gate through its media server route;
- the core replaces that certificate with the old and the new SHA-256 both held, and
  withdraws the old only once each holder has reached the media server with the new.

**Amends**:

- [ADR-0029](0029-a-household-service-declines-an-invitation-with-one-key.md): §6. The
  decline service's key reaches Jellyfin over TLS it pins, not in cleartext on the
  network the two share;
- [ADR-0050](0050-a-contract-hands-its-filler-all-it-enforces-and-reads-back-no-secret.md):
  §3 and §7. `hold` and the media server's gate route carry the SHA-256 of each
  certificate the media server may present.

## Context

[ADR-0029](0029-a-household-service-declines-an-invitation-with-one-key.md) gives the
decline service one Jellyfin API key, which administers the whole server: no narrower
credential can switch an account off (§4). `D6-R16` has a refusal make the invitation
unclaimable at once, and `D6-R21` has a lapse taken back without a lemonfiber process
running, so the service has to reach Jellyfin with that key itself. §6 contains the
service by its networks, its posture and its fixed calls, and sends the key in cleartext
to `http://jellyfin:8096`, the only way Jellyfin is served on the network the two share.

Code scanning in `lemonfiber-decline` reports that as `rust/cleartext-transmission`:
alert #1 at the call that switches an account off, and alert #2 at the call that removes
one when its invitation lapses, both in `src/jellyfin.rs`. The maintainer chose to fix both in
code rather than dismiss them. The request gate holds the same kind of credential: its
media server route presents a Jellyfin key to the server
([ADR-0032](0032-the-request-service-reaches-the-arrs-through-a-gate.md),
`ARCH-R305`).

The guarded door already serves over TLS with a certificate the core makes for it, and
the core states its fingerprint beside every location it gives there, so a client pins
the door as it pins the stack (`D11-R7`).

## Decision

1. **The media server serves an internal TLS port.** The filler of `identity.source`
   serves a TLS port on the stack's internal networks, named in its `media.serve`
   declaration beside its other ports, with a certificate the core makes for its service
   name. No authority outside the house signs it. The port the household and the proxy
   reach stays as it is.
2. **A credential holder pins that port.** Every service the core hands a media server
   credential reaches the media server only at the internal TLS port, and accepts only a
   certificate whose SHA-256 the core handed it with the credential. The decline service
   gets it with the key in `hold`. `invite.decline@1` is amended in place, because no
   release has carried it. The request gate gets it on its media server route.
3. **Replacing the certificate keeps every holder reaching it.** The core hands each
   holder the new certificate's SHA-256 beside the old, then serves the new certificate,
   restarting the media server where it reads its certificate only at start. It
   withdraws the old SHA-256 only once each holder has reached the media server with the
   new, as a gate token's rotation keeps the old hash until the new token is proved.

## Consequences

- **The key never crosses a network in cleartext.** A service on a network the decline
  service or the gate shares with the media server sees TLS, and a service that answers
  in the media server's place without its certificate is refused.
- **The core makes one more certificate**, by the code that makes the door's, and
  replaces it on the same schedule. `lemonfiber plugin record` writes a throwaway one for
  the media server, as it does for the door
  ([ADR-0051](0051-a-fresh-claimant-answers-its-probe-and-the-core-asks-what-nothing-else-does.md)
  §2).
- **The media server plugin serves the port.** `plugin-jellyfin` serves Jellyfin's HTTPS
  port inside the stack with the certificate the core writes.
- **The decline service and the request gate verify the pin.** Each reaches the media
  server over TLS whose certificate's SHA-256 is one the core handed it, and no other.
- **A server that cannot serve TLS cannot fill `identity.source`** for a stack that runs
  the decline service or the request gate.

## Alternatives considered

| Alternative | Why not |
|---|---|
| **The alerts dismissed, as ADR-0029 §6 reasoned** | The maintainer chose to fix them. The network a service shares with Jellyfin is containment, not secrecy. |
| **The core switches accounts off, and the decline service holds no key** | A refusal would leave the invitation claimable until a lemonfiber process runs, against `D6-R16`'s "at once" and `D6-R21`. |
| **The decline service inside Jellyfin's network namespace (`network.via`)** | It ties the service's lifetime and exposure to Jellyfin's, `network.via` is the egress guard's alone, and its household port would be published on Jellyfin's entry. |
| **The decline service asks the media server's adapter over `identity.source`** | It is still a bearer credential in cleartext inside the stack, and it hands the decline service the adapter's plugin key. |
| **A certificate from a public authority** | It asks an authority outside the house about a name that answers only inside it. |

## Revisit when

- a supported media server line cannot serve TLS with a certificate it is handed;
- the stack's internal networks gain encryption of their own, which would make the
  internal port redundant.
