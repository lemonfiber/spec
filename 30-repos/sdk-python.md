# Repo: `sdk-python`

**Status:** Accepted

The Python client for lemonfiber's web API, with an asynchronous and a synchronous client
over one generated contract. Python, Hippocratic 3.0.

**Implements:** the client half of the
[web API contract](../20-architecture/contracts/web-api.md), as a peer of
[`sdk-ts`](sdk-ts.md) and [`sdk-php`](sdk-php.md).

---

## What this repo is

A **library with no user interface and no server**. It speaks the
[web API](../20-architecture/contracts/web-api.md) and exposes it as typed calls, a typed
event stream, and typed errors. Its first consumer is
[`integration-home-assistant`](integration-home-assistant.md), and it is written so that a
script can use it too.

It is a **peer** of the other SDKs, not a translation of either
([ADR-0013](../00-overview/decisions/0013-an-sdk-owns-the-api-client.md)). An SDK that
disagrees with the contract is wrong.

## Two clients, one contract

| Client | Transport | Why |
|---|---|---|
| Asynchronous | `aiohttp`, with a session the caller may supply | Home Assistant is asynchronous throughout and gives an integration its own session |
| Synchronous | `urllib3` | A script should not need an event loop to read a disk figure |

Both are built from the same generated shapes and the same written behaviour, and both are
held to the same tests: each behaviour the async client has is asserted of the sync client
too.

## What is generated and what is written

The split is the same in every SDK
([ADR-0014](../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md)):

| | |
|---|---|
| **Generated** into `src/lemonfiber/_generated/`, never edited by hand | Response shapes, endpoint paths and parameters, action names, event names, the wire version |
| **Written**, once, in Python | The stream's behaviour, the token's placement, the pin, the error model's wording |

Everything generated comes from `web-api.contract.json`. A generator run that changes
anything committed fails CI.

## What it owns

- **The stream**: heartbeat detection (`ARCH-R50`), resumption, and marking values held
  across a reconnect gap as stale rather than current (`ARCH-R51`).
- **The token**: a per-run token, a session or an integration key
  ([C10](../10-functional/features/c-trust/c10-integration-keys.md)), supplied by the
  caller, sent in `X-Lemonfiber-Token`, never placed in a URL (`ARCH-R52`).
- **Loopback, or an address a pin vouches for**: a non-loopback host is refused unless the
  caller gave that stack's certificate pin, and the pin is checked against the peer's
  certificate after the handshake and before any request is written (`ARCH-R60`,
  `ARCH-R99`, [ADR-0025](../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md)).
  The async client uses `aiohttp.Fingerprint` and the sync client `urllib3`'s
  `assert_fingerprint`. The pin is given when a client is built, and no argument or setting
  weakens verification.
- **The refusal on mismatch**: a wire version it cannot speak names both versions and
  returns nothing (`ARCH-R55`).

## What it must not own

- **Rendering or presentation.** Home Assistant draws entities, a script prints. Neither is
  this library's business.
- **Policy.** It reports what the core said.
- **State beyond the stream.** No caching, no reconciliation.

## Quality bar

The same standard as the other SDKs, in Python's equivalents:

- `pyright` in strict mode with no suppressions, and `ruff` with its full rule set and the
  formatter enforced.
- `pytest` at 100% line and branch coverage, enforced as a gate.
- Mutation testing with a minimum score, run in CI.
- Architecture tests that keep generated code generated and transports behind the client.
- A backward-compatibility check against the last commit a consumer pins, and a changelog.
- The organisation's shared workflows: spec-check, DCO, commitlint, hygiene, security,
  attribution, workflow pins, Sonar and CodeQL.

Runtime dependencies are `aiohttp` and `urllib3` and nothing else without a recorded reason.
The supported Python versions start at the oldest one Home Assistant's current release
supports.

## Publishing

Not published to a package registry. Consumers take it by commit:
`integration-home-assistant` vendors the generated client at a pinned commit, with a drift
check that fails when the pin is behind what the core serves.

## Related

- [`sdk-ts`](sdk-ts.md) · [`sdk-php`](sdk-php.md): the peers
- [`integration-home-assistant`](integration-home-assistant.md): the first consumer
- [ADR-0013](../00-overview/decisions/0013-an-sdk-owns-the-api-client.md) · [ADR-0014](../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md) · [ADR-0025](../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md)
