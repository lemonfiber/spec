# Repo: `sdk-ts`

**Status:** Accepted

The TypeScript client for lemonfiber's web API. Published as
`@lemonfiber/sdk-ts`. TypeScript, Hippocratic 3.0.

**Implements:** the client half of the
[web API contract](../20-architecture/contracts/web-api.md).

---

## What this repo is

A **library with no user interface and no server**. It speaks the
[web API](../20-architecture/contracts/web-api.md) and exposes it as typed calls,
a typed event stream, and a typed error. It is the first thing any consumer of the
API should reach for, and the only thing `lemonfiber-web` uses to talk to the core.

Named for the language rather than the product
([ADR-0013](../00-overview/decisions/0013-an-sdk-owns-the-api-client.md)), so
`sdk-py` and `sdk-rs` need no renaming. Each is a peer implementation of one
specification. **The spec is the reference**; an SDK that disagrees with the
contract is wrong.

## What it owns

| Piece | Obligation |
|---|---|
| `envelope` | The `{ api_version, kind, data }` shape, and refusing a version it cannot speak (`ARCH-R46`, `ARCH-R55`) |
| `client` | One method per endpoint, mirroring the commands (`ARCH-R47`) |
| `actions` | `POST /api/actions/<name>`, and following a job to completion (`ARCH-R48`) |
| `events` | The stream: heartbeat detection (`ARCH-R50`), resumption, and marking pre-gap values stale (`ARCH-R51`) |
| `problem` | The error model, in the language [G2](../10-functional/features/g-ux/g2-plain-language.md) requires |

Also the token: supplied by the caller, sent as a header, never placed in a URL
(`ARCH-R52`).

## What it must not own

- **Rendering.** No DOM, no components, no framework dependency. A consumer that
  is not a browser must be able to use it.
- **Policy.** It reports what the core said. Deciding what to do about a stuck
  download is the core's job, and displaying it is the surface's.
- **State beyond the stream.** It does not cache, reconcile or invent. A figure it
  has not been given is one it does not have.

## Versioning

Two numbers doing different jobs, and conflating them is the mistake to avoid:

- **The package** carries semver. Ordinary software, ordinary breaking changes.
- **`api_version`** is a monotonic integer describing the wire
  ([ARCH-R2](../20-architecture/contracts/versioning.md)).

The package declares which `api_version` it speaks. Many package versions may speak
one wire version. That declaration is what `ARCH-R54` validates against the binary
at build time, surfaced through the application that embeds it.

## Quality bar

The same standards as [`lemonfiber-web`](lemonfiber-web.md): 100% coverage across
lines, statements, branches and functions; `strict` TypeScript with
`noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`; `typescript-eslint`
`strictTypeChecked` with no warnings tolerated; no escape hatches.

Two obligations are specific to a published library: **no runtime dependencies**
without a recorded reason, since a client library's dependency tree becomes every
consumer's problem; and **a changelog**, since people pin it.

## Related

- [ADR-0013](../00-overview/decisions/0013-an-sdk-owns-the-api-client.md) — why it exists and why it is separate
- [web-api.md](../20-architecture/contracts/web-api.md) — the contract it implements
- [lemonfiber-web.md](lemonfiber-web.md) — its first consumer
