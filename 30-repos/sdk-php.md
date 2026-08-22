# Repo: `sdk-php`

**Status:** Accepted

The PHP client for lemonfiber's web API. PHP, Hippocratic 3.0.

**Implements:** the client half of the
[web API contract](../20-architecture/contracts/web-api.md), as a peer of
[`sdk-ts`](sdk-ts.md).

---

## What this repo is

A **library with no user interface and no server**, built on
[Saloon](https://docs.saloon.dev) for its HTTP layer. It speaks the
[web API](../20-architecture/contracts/web-api.md) and exposes it as typed calls,
a typed event stream, and typed errors.

It is a **peer** of `sdk-ts`, not a translation of it
([ADR-0013](../00-overview/decisions/0013-an-sdk-owns-the-api-client.md)). Both
conform to the same specification; neither is the reference for the other. An SDK
that disagrees with the contract is wrong.

## What is generated and what is written

The split is the same in every SDK
([ADR-0014](../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md)):

| | |
|---|---|
| **Generated** into `src/Generated/`, never edited by hand | Response shapes, endpoint paths and parameters, action names, event names, the wire version |
| **Written**, once, in PHP | The stream's behaviour, the token's placement, the error model's wording |

Everything generated comes from `web-api.contract.json`, which `lemonfiber`
produces from the types that actually serialise the reply (`ARCH-R56`). A
hand-written response shape here would be a second source of truth for the
contract, which `ARCH-R58` forbids.

## What it owns

The parts a schema cannot express, and which each SDK must therefore implement
and test for itself:

- **The stream** — heartbeat detection (`ARCH-R50`), resumption, and marking
  values held across a reconnect gap as stale rather than current (`ARCH-R51`).
- **The token** — supplied by the caller, sent as a header, never placed in a
  URL (`ARCH-R52`).
- **Loopback only** — a non-loopback host is refused, matching
  [C6-R1](../10-functional/features/c-trust/c6-web-security.md).
- **The refusal on mismatch** — a wire version it cannot speak names both
  versions and returns nothing (`ARCH-R55`).

## What it must not own

- **Rendering or presentation.** It is consumed by scripts and applications, and
  must assume neither.
- **Policy.** It reports what the core said. What to do about a stuck download is
  the core's decision.
- **State beyond the stream.** No caching, no reconciliation. A figure it has not
  been given is one it does not have.

## Quality bar

The same standard as the Rust workspace, in its PHP equivalents: static analysis
at maximum with no baseline and no suppressions, 100% coverage enforced as a
gate, **mutation testing with a minimum score** — coverage that kills no mutants
proves only that lines ran — automated refactoring checks, architecture tests,
and a strict formatter. Dependencies beyond the HTTP layer are avoided: a client
library's dependency tree becomes every consumer's.

Two obligations are specific to a published library: a **changelog**, since
people pin it, and a **backward-compatibility check**, so a breaking change fails
the build rather than surprising a consumer.

## Publishing

Not yet published. Nothing consumes it, so it stays unreleased until there is a
stable major worth pinning; registration on Packagist happens then rather than
now.

## Related

- [ADR-0013](../00-overview/decisions/0013-an-sdk-owns-the-api-client.md) — why the SDK exists and is separate
- [ADR-0014](../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md) — why its types are generated
- [web-api.md](../20-architecture/contracts/web-api.md) — the contract it implements
- [sdk-ts.md](sdk-ts.md) — its peer
