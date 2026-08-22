# ADR-0013: The API gets an SDK, and the SDK gets its own repo

**Status:** Proposed
**Date:** 2026-08-23

## Context

[ADR-0011](0011-web-surface-as-a-fifth-repo.md) made the boundary between the core and the
web surface a **published contract**, and named the outcome that would prove the decision
right: *"A second consumer of the API appears. That would strengthen the boundary rather than
weaken it."*

That consumer has arrived earlier than expected, and it is worth being precise about what it
is. The web surface is not one consumer with one client — it is the **first** consumer, and
whatever it writes to talk to the core is the thing every later consumer will either reuse or
reinvent.

Three parts of the [web API contract](../../20-architecture/contracts/web-api.md) are much
harder than they look, and all three are the kind of thing that is got wrong quietly:

- **`ARCH-R50`** — a silent event stream and a dead one are indistinguishable without a
  heartbeat. A client that omits it appears to work perfectly until the moment it matters.
- **`ARCH-R51`** — on reconnect, a client holds values gathered *before* the gap. They are
  stale by definition. Presenting them as current is the exact failure `Reading<T>` exists to
  prevent one layer down, reintroduced at the transport.
- **`ARCH-R55`** — a version mismatch must refuse plainly rather than render a page whose
  fields have quietly changed meaning.

Written once, these are a careful afternoon. Written per consumer, they are three chances to
reintroduce the bug the core was built to avoid.

## Decision

**A separate repo, `sdk-ts`, publishing `@lemonfiber/sdk-ts` to npm. It owns transport,
types and the stream. `lemonfiber-web` consumes it and renders.**

```
sdk-ts/
├── envelope.ts    Envelope<T>, read(), the api_version this client speaks
├── client.ts      one method per endpoint, mirroring the commands
├── actions.ts     POST /api/actions/<name>, and job progress
├── events.ts      SSE: heartbeat detection, resume, staleness on reconnect
└── problem.ts     the error model, in the plain language G2 requires
```

**The name carries the language, not the product.** `sdk-ts` leaves `sdk-py` and `sdk-rs`
free without renaming anything. Each is a peer implementation of one specification; none is
the reference, because **the spec is the reference** — an SDK that disagrees with the
contract is wrong, not authoritative.

**It is published from the start.** ADR-0011 already recorded that the API is a public
surface the moment it exists. Publishing formalises a commitment that has already been made,
and it forces versioning discipline while the surface is still small enough to change
cheaply.

**Two version numbers, doing different jobs.** The package carries semver, because it is
ordinary software with ordinary breaking changes. `api_version` stays a monotonic integer
([ARCH-R2](../../20-architecture/contracts/versioning.md)) describing the *wire*. The SDK may
release many versions against one `api_version`, and must state which one it speaks — that
declaration is what `ARCH-R54` validates at build time, surfaced through the app that embeds
it.

## Alternatives considered

**No SDK; every consumer uses `fetch` directly.** Nothing to publish, nothing to version, no
support commitment. Rejected because it makes `ARCH-R50` and `ARCH-R51` the responsibility of
each consumer, and those are precisely the requirements a consumer will not know it has got
wrong. It would also mean the web app carries transport logic it should not own.

**A package inside `lemonfiber-web`.** No extra repo, and the only consumer that exists today
gets it for free. Genuinely tempting, and the honest reason to reject it is small: a
third-party reaching for the client would take a dependency on a *web application*, and the
first non-web consumer would force the extraction anyway — at which point it has history,
dependents and a name to change.

**Generate the SDK from an OpenAPI schema.** The types could not drift, which is the whole
problem stated as a solution. Rejected because the contract is not shaped like a REST
resource model — it is one envelope, endpoints that mirror commands, and a stream with
semantics no schema language captures. A generator would produce correct types and none of
the behaviour that is actually difficult. Worth revisiting for *types only* if hand-written
types ever drift from the core's serialisation.

**Put it in the `lemonfiber` repo alongside the server.** Server and client change together,
which is real. Rejected for the same reason ADR-0011 kept the web surface out: a Node
toolchain inside a Rust workspace whose gates all assume Rust.

## Consequences

- **A third repo in the release train**, and a published package with the obligations that
  brings — a changelog, deprecations rather than removals, and a version people can pin.
- **`lemonfiber-web` gains a dependency it does not control**, pinned like every other.
- **The difficult requirements are implemented and tested once**, and a bug in resumption is
  fixed once for every consumer rather than per client.
- **A future `sdk-py` must reimplement them**, not translate them. The spec is what both
  conform to; neither SDK is the source of truth for the other.
- **The API can no longer be changed quietly.** This is the point, and it is also the cost.

## Revisit if

- No second consumer materialises and the SDK is only ever used by `lemonfiber-web` — the
  honest signal that the package boundary is ceremony rather than structure.
- Hand-written types drift from the core's serialisation more than once. That is the argument
  for generating the types (though not the behaviour) from the server's own definitions.
- The stream's semantics stabilise enough that a generated client would be complete, which
  would make the hand-written parts maintenance rather than value.
