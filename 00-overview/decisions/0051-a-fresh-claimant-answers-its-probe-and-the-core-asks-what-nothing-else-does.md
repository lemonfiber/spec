# ADR-0051: A fresh claimant answers its probe, and the core asks what nothing else does

**Status:** Accepted
**Date:** 2026-10-20
**Decided:** 2026-10-20, by the maintainer, Wessel Verheij:

- a redirect to HTTPS is, like a refusal, an answer a probe may constrain by its status
  alone, and `proxy.front`'s probe is answered `301` or `308`;
- `lemonfiber plugin record` writes a throwaway self-signed certificate and its key where
  the core writes them for a filler of a capability the core hands a certificate, so a
  stream guard that serves TLS from the start can be recorded from a fresh container;
- a request gate applied no routes answers `403` to every call but its health, rather
  than `503`;
- the core, asking a capability over its contract, is what asks `quality.sync`,
  `archive.extract`, `stream.guard` and `invite.decline`, and no `[[ask]]` row is
  written for it.

**Amended** by [ADR-0052](0052-a-curators-downloads-complete-into-one-folder-and-the-core-tells-each-part-what-it-holds.md): §4. The core asks `dashboard.show` as well: over the contract where its filler speaks it, and where the filler is the assembled Homepage, through an in-process adapter that writes Homepage's own files.

**Amends**:

- [ADR-0032](0032-the-request-service-reaches-the-arrs-through-a-gate.md): §3. A gate
  whose upstream file the core has not written yet refuses every call with `403`, not
  forwarded and not recorded;
- [ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md): §6. A
  capability is asked by something in the bundle or by the core over its contract.

## Context

`F14-R8` puts seven capabilities in the vocabulary, and `ARCH-R119` holds each probe to
what a service holding none of the operator's data answers. `ARCH-R295` takes a
recording from a new container of the pinned image with nothing but its starting files.
Measured on 2026-10-20 against the bundled claimants' pinned images:

- **Caddy answers one thing over plain HTTP.** `ghcr.io/lemonfiber/caddy@sha256:dd64ac74`
  answers every request on its HTTP port, whatever the name and path, with `308`, a
  `Location` at HTTPS, and an empty body with no content type. The vocabulary allowed a
  probe constraining only a status where the answer is a refusal, so no probe Caddy
  could bind would have been a valid one.
- **The door does not start without its certificate.**
  `ghcr.io/lemonfiber/door@sha256:bb78c5b8` serves its TLS port with the certificate and
  key the core writes beside its configuration (`D11-R7`), and stops at start where they
  are absent, so no recording could be taken from its starting files alone. Started, an
  anonymous request for a well-formed item's bytes is put to the media server, which a
  recording has none of; only the refusals the door makes without asking anything answer
  the same on a fresh container.
- **The gate answers `503` before it is applied routes.**
  `ghcr.io/lemonfiber/request-gate@sha256:26f6eed2` answers every call but its health
  with `503` while no upstream file is written, the answer
  [ADR-0032](0032-the-request-service-reaches-the-arrs-through-a-gate.md) gives a file it
  cannot read. A gateway error is what an emptied container's proxy may give too, so it
  is no evidence of a gate.
- **Four capabilities are asked by nothing in the bundle.** Quality sync, archive
  extraction, the stream guard and decline are configured by the core and queried by no
  other service, and `F14-R8` read literally asked for an `[[ask]]` row of each that no
  service makes.

## Decision

1. **A redirect to HTTPS stands with a refusal.** A probe may constrain its answer by
   the status alone where the answer is a refusal or a redirect to HTTPS: neither is
   something a port proxy produces. `proxy.front`'s probe is answered by `301` or `308`.
2. **The recorder writes the certificate the core would.** For a service filling a
   capability the core hands a certificate, `stream.guard` today, `lemonfiber plugin
   record` writes a throwaway self-signed certificate and its key where and as the core
   writes them for that capability's filler, before the container starts, and removes
   them with the throwaway copy. `stream.guard`'s probe is a refusal the guard makes
   without asking anything: a path its declaration refuses, or an item's bytes in a shape
   it cannot ask about, answered `403`.
3. **A gate with no routes refuses.** Until the core writes its upstream file, the gate
   answers every call but its health `403`, not forwarded and not recorded; an upstream
   file that is there and cannot be read stays `503`. `request.gate`'s probe is a call
   presenting no admitted token, refused with `401` or `403`.
4. **The core is an asker.** A capability is asked by something in the bundle or by the
   core over its contract. The core asks `quality.sync`, `archive.extract`,
   `stream.guard` and `invite.decline`, and no `[[ask]]` row stands in for it.

## Consequences

- Each of the seven capabilities has a probe its bundled claimant answers on a fresh
  container of its pin, recorded by `lemonfiber plugin record` as every other claim is.
- A substitute proxy is held to redirecting plain HTTP, a substitute guard to the
  refusals it makes alone, and a substitute gate to refusing before it is configured.
- A recording of the guard is taken with a certificate nobody holds the key to after the
  run, so it pins nothing a client could trust.
- Wiring derives no network for the four capabilities only the core asks; the core
  reaches their fillers as it reaches every filler of a contract it speaks.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **A body constraint on the proxy's redirect, `json_is_absent`** | It satisfies the rule's letter and shows nothing: every empty answer is not JSON. |
| **An HTTP answer with a body in the proxy's starting files** | It changes what the proxy serves on every household name to give a probe something to read. |
| **The door starting without its certificate** | A new image and a TLS port that appears only once the core has written the pair, for the sake of a recording. |
| **A throwaway certificate in the door's starting files** | A published private key the door would serve if the core's write ever failed. |
| **The gate's probe accepting `503`** | A dead upstream behind a port proxy gives a gateway error too, so it shows nothing about the gate. |
| **An empty routes file in the gate's starting files** | A starting file that exists only for the probe, which the core overwrites at its first run. |
| **An `[[ask]]` row for each capability only the core asks** | A row naming a service that makes no such request, and a network derived for a reach nobody has. |

## Revisit when

- A proxy filler answers plain HTTP with something other than a redirect.
- A second capability's filler is handed a certificate by the core.
- A service of the bundle comes to query one of the four capabilities only the core asks.
