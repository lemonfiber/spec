# Repo: `sdk-rust`

**Status:** Accepted

The Rust client for lemonfiber's web API, as the crate `lemonfiber-sdk`: an asynchronous
client over one generated contract and a transport the caller may replace. Rust,
Hippocratic 3.0.

**Implements:** the client half of the
[web API contract](../20-architecture/contracts/web-api.md), as a peer of
[`sdk-ts`](sdk-ts.md), [`sdk-php`](sdk-php.md) and [`sdk-python`](sdk-python.md).

---

## What this repo is

A **library with no user interface and no server**. It speaks the
[web API](../20-architecture/contracts/web-api.md) and exposes it as typed calls, a typed
event stream, and typed errors. Its first consumer is `lemonfiber` itself: the proof that
each capability is filled by a substitute
([F14-R14](../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md)) drives
a running stack through it, as any other program would.

It is a **peer** of the other SDKs, not a translation of any of them
([ADR-0013](../00-overview/decisions/0013-an-sdk-owns-the-api-client.md)). An SDK that
disagrees with the contract is wrong.

## One client, a transport behind it

| Piece | What it is |
|---|---|
| The client | Asynchronous. Every read, action, job, key, device key and setup step the surface serves is a method on it |
| The transport | A trait the client sends every request through. The default is `reqwest` over `rustls` with the `ring` provider, the stack the core's own pinned client uses |

A caller may hand the client its own transport for a stack on this machine. A stack anywhere
else is reached only through the default, which checks its pin, so no argument reaches one
through a transport that does not (`ARCH-R99`). Whatever the transport, the address, the
credential header and the reading of the answer are the client's.

## What is generated and what is written

The split is the same in every SDK
([ADR-0014](../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md)):

| | |
|---|---|
| **Generated** into `crates/lemonfiber-sdk/src/contract/`, never edited by hand | Response shapes, request bodies, every action and its arguments, the reads and their parameters, the refusal codes, the actions a key may call, the wire version |
| **Written**, once, in Rust | The stream's behaviour, the token's placement, the address and its pin, the error model's wording |

Everything generated comes from the `contract/web-api/` directory, vendored at the
revision `contract/VERSION` names. The generator is a crate in the same workspace, reads
only the vendored copy, and a run that changes anything committed fails CI.

## What it owns

- **The stream**: heartbeat detection (`ARCH-R50`, `ARCH-R61`), resumption from the last
  event id (`ARCH-R62`), and marking values held across a reconnect gap as stale rather
  than current (`ARCH-R51`).
- **The token**: a per-run token, a session or an integration key
  ([C10](../10-functional/features/c-trust/c10-integration-keys.md)), supplied by the
  caller, sent in `X-Lemonfiber-Token`, never placed in a URL (`ARCH-R52`, `ARCH-R59`).
- **Loopback, or an address a pin vouches for**: a non-loopback host is refused unless the
  caller gave that stack's certificate pin, and the pin is checked against the peer's
  certificate during the handshake, before any request is written (`ARCH-R60`,
  `ARCH-R99`, [ADR-0025](../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md)).
  A named host given without a pin is resolved once, accepted only where every address it
  resolves to is loopback, and reached at those addresses. The pin is given with the
  address, and no argument or setting weakens verification.
- **The refusal on mismatch**: a wire version it cannot speak names both versions and
  returns nothing (`ARCH-R55`).
- **Errors as values**: every call returns a `Result`, and a refusal is read from its code
  where the contract lists it and from its status where it does not (`ARCH-R138`).

## What it must not own

- **Rendering or presentation.** A command line prints, a proof asserts. Neither is this
  library's business.
- **Policy.** It reports what the core said.
- **State beyond the stream.** No caching, no reconciliation.

## Quality bar

The same standard as the Rust workspace in `lemonfiber`:

- `unsafe_code` forbidden, `missing_docs` denied, clippy's pedantic set as warnings, and
  `unwrap`, `expect`, `panic` and indexing denied; CI fails on any warning.
- 100% line coverage, enforced as a gate.
- Mutation testing of the written client, every mutant told apart, run in CI.
- A backward-compatibility check against the commit the core pins, and a changelog.
- `cargo deny` over the dependency tree, with the core's policy on licences, sources and
  duplicate versions.
- The organisation's shared workflows: spec-check, DCO, commitlint, hygiene, security,
  workflow pins, Sonar and CodeQL.

Its dependencies are held to the versions the core's lockfile resolves, so the core takes
the crate without a second copy of anything.

## Publishing

Not published to a package registry. Consumers take it as a git dependency pinned to a
commit.

## Related

- [`sdk-ts`](sdk-ts.md) · [`sdk-php`](sdk-php.md) · [`sdk-python`](sdk-python.md): the peers
- [`lemonfiber`](lemonfiber.md): the first consumer
- [ADR-0013](../00-overview/decisions/0013-an-sdk-owns-the-api-client.md) · [ADR-0014](../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md) · [ADR-0025](../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md)
