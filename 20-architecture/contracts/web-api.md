# Contract: the web API

**Status:** Accepted

The interface between `lemonfiber`, which serves it, and
[`lemonfiber-web`](../../30-repos/lemonfiber-web.md), which draws it.

**Satisfies:** [G1-R1](../../10-functional/features/g-ux/g1-interface-tiers.md),
[G1-R2](../../10-functional/features/g-ux/g1-interface-tiers.md),
[G1-R7](../../10-functional/features/g-ux/g1-interface-tiers.md),
[G1-R12](../../10-functional/features/g-ux/g1-interface-tiers.md),
[C6-R10](../../10-functional/features/c-trust/c6-web-security.md),
[C6-R12](../../10-functional/features/c-trust/c6-web-security.md)

---

## Why this is a contract

[ADR-0011](../../00-overview/decisions/0011-web-surface-as-a-fifth-repo.md) put the web
surface in its own repo, which means the boundary between it and the core is a **published
shape** rather than a compiler check. That is the whole point: `G1-R2` says no surface may
implement behaviour independently, and a client that can only ask and draw cannot break it
by construction.

The risk a contract carries is drift, so this one is built to make drift structurally hard
rather than merely discouraged.

## It is the envelope that already exists

Machine-readable output is already a stable interface (`ARCH-R9`, [versioning](versioning.md)):

```json
{ "api_version": 1, "kind": "status", "data": { … } }
```

**The web API does not introduce a second shape.** Every endpoint answers with the identical
envelope the equivalent command emits under `--json`, byte for byte. A script piping
`lemonfiber status --json` and the web app fetching `/api/status` receive the same document.

This is the load-bearing decision in the contract, and it is worth being explicit about why.
A separate "web shape" would be a second serialisation of the same domain — two places to
change when a field is added, two sets of tests, and eventually two answers to the same
question, which is exactly what `G1-R2` exists to prevent. One shape means the surface adds
**no vocabulary of its own**.

## Reading

Each command that supports `--json` has one endpoint, named for the command, returning that
command's envelope:

```
GET /api/forms         GET /api/status         GET /api/services
GET /api/checks        GET /api/storage        GET /api/logs?…
GET /api/requests      GET /api/trace?…        GET /api/stuck
GET /api/version       GET /api/config?…       GET /api/quality
GET /api/explain?…     GET /api/backups        GET /api/bundle/{name}
```

Query parameters mirror what the command takes, flag or argument. A command that gains one
gains a parameter; one that gains an endpoint gained a command first.

`/api/bundle/{name}` is the one read that does not answer with an envelope. It answers with
the bundle itself, because a browser has no path on the host to be told and handing the file
over is the only form `--out` can take on a screen. The name is resolved beneath the bundles
directory rather than followed, so one carrying a path, or climbing out of that directory, is
refused by name.

### When a read is refused

The body of a refusal is the error envelope, the same one `--json` renders, so the status is
the only thing that tells one refusal from another — and they are worth telling apart:

| Refused because | Status |
|---|---|
| What the request named, this product does not have | `404` |
| The request could not be answered as it was asked | `400` |
| Nothing about the request was wrong; the machine could not answer it | `500` |

The line between the first two is what the request was *for*. A word this product does not
explain is absent — the word is the whole of what `/api/explain` was asked for, and there is
no entry — while a parameter left out, given twice, or given a value the surface does not
offer is a request that could never have been answered as it stands. It is the same line the
write surface already draws between an action name nothing answers to and an argument it
cannot take, and the same reading `ARCH-R72` makes of a job name this run never issued.

`500` is reserved rather than incidental. A client told the machine failed will retry, and a
client told that about a word with no entry retries forever; worse, one that cannot tell the
two apart has to word a single message that is true of both, which is how "no entry" and "no
answer" reach an operator as the same sentence.

## Live state

```
GET /api/events        text/event-stream
```

The SSE event name is the envelope's `kind`, and the payload is the envelope. Three
properties are required rather than incidental:

**It is the same gather.** `G1-R12` requires concurrent surfaces to agree, and two
independent gathers are two chances to disagree — so the stream is fed by the gather that
already serves the dashboard, not a second one built for the web.

**A silent stream is distinguishable from a broken one.** Without a heartbeat, "nothing has
changed" and "the connection died twenty minutes ago" look identical to a client, which is
the same confusion `Reading::Stale` exists to prevent one layer down.

**A resumed stream does not lie about what it missed.** On reconnect a client may hold values
gathered before the gap. Those are `Stale` by definition, and must be presented as such
rather than as current.

## Writing

```
POST /api/actions/<name>
```

Arguments mirror the command's. `G1-R1` requires every action to be available from every
surface, and this contract adds the converse: **the web API exposes nothing the CLI cannot
do.** An action that exists only here would be a behaviour implemented by a surface.

Long-running actions return a job identifier and report progress on the event stream, so a
browser tab that closes mid-repair does not orphan the work. The identifier is **redeemable**
— see [a job's outcome](#a-jobs-outcome) — because a name that cannot be turned back into an
outcome makes the reply an acknowledgement rather than an answer.

## What guards it

A writable API on loopback is reachable from any page the operator happens to visit — a page
cannot *read* a cross-origin response, but it can *send* a request the server acts on, and
DNS rebinding defeats a naive origin check. The CLI never had this exposure; nothing a web
page does reaches `argv`.

| Guard | Requirement |
|---|---|
| Bound to loopback, never all interfaces | [C6-R1, C6-R3](../../10-functional/features/c-trust/c6-web-security.md) |
| A per-run token, printed by the CLI at start, on every request | `ARCH-R52` |
| `Origin` and `Host` checked against the bound address | `ARCH-R53` |
| No proxying to an admin service | [C6-R12](../../10-functional/features/c-trust/c6-web-security.md) |
| Says plainly that it is unencrypted HTTP | [C6-R6](../../10-functional/features/c-trust/c6-web-security.md) |

The token travels in a header. Never a query parameter: URLs reach logs, history and
referrers, and a credential that leaks into any of those has leaked.

## Version skew

The client declares the `api_version` it speaks. Because the built app is embedded from a
pinned submodule ([ADR-0012](../../00-overview/decisions/0012-web-assets-embedded-at-build-time.md)),
`build.rs` validates that declaration against the binary **at compile time** — the same
protection `ARCH-R6` already gives the embedded stack's `schema_version`. A mismatched pair
cannot be released.

The runtime check remains, because a browser may hold a cached older app. A mismatch there
refuses plainly and says which versions are involved, rather than rendering a page whose
fields have quietly changed meaning.

## The details two clients must agree on

A requirement that states an obligation without stating its mechanism gets two
implementations that both satisfy it and cannot talk to the same server. These are
the particulars, fixed so that no client has to invent them.

### The token

The header is **`X-Lemonfiber-Token`**. The binary prints the token when it starts
serving, and a client is given it by its caller — there is no discovery, no file to
read, and no default.

### The address

There is **no default port**. The binary chooses a free one unless told otherwise and
prints the whole address; a client is configured with that address rather than
assembling one.

A host name is accepted only if it resolves to a loopback address. Refusing the word
`localhost` outright is the wrong trade: it is what an operator types and what a
printed address may contain. Refusing a name that resolves *off* loopback is the
protection that matters, and resolving before connecting is what provides it.

### The heartbeat

The server emits a comment line at least every **15 seconds** when nothing else has
been sent. A client treats the stream as broken once **twice** that has passed in
silence, which tolerates one missed beat without pretending a dead connection is a
quiet one.

### Resumption

Every event carries an `id`. A client resuming sends the last one it saw as
`Last-Event-ID`, and the server replays from after it where it can, or restarts the
stream where it cannot. Either way everything the client still holds from before the
gap is stale until replaced — the resumption mechanism does not change what is
current, only what is retransmitted.

### A job's outcome

```
GET /api/jobs/<job>
```

The other end of the accepting reply. It is not named for a command, because it answers no
request the command line has: being answered with a name instead of an outcome is the web's
own arrangement, and this is the half that makes it an answer.

The standing is carried by the **status**, and the body is a document the client already
parses either way:

| Standing | Status | Body |
|---|---|---|
| Still in flight | `202` | the identical envelope the accepting reply carried |
| Finished | `200` | the equivalent command's machine-readable output |
| Stopped | `500` | the error envelope the failure renders |
| Not a name this run issued | `404` | a refusal, not the name repeated back |

Status rather than a field, because the alternative is a shape only this endpoint has — and a
second serialisation of an outcome the contract already describes is the drift `ARCH-R47`
exists to prevent.

The stream is not the mechanism. A client that reconnects sends the last id it saw, and a
client connecting for the first time has none to send, so an event announcing the end reaches
only a client that was already listening when it happened — which is not the client the
accepting reply exists to serve. A tab closed mid-repair and reopened holds a name and nothing
else, and this is what it does with it.

Names do not outlive the run that issued them. Work in flight does not survive the process
doing it, so a record that outlived the run would describe jobs nothing is running; a name from
an earlier run is therefore one this run never issued.

### The payload's type

`data` differs by `kind`, so a client exposes it **typed by its kind** rather than as
an untyped value. Generated types make this ordinary rather than laborious: the kind
is the discriminator, and an untyped payload on the public surface means the
generation has not been used.

## Requirements

| ID | Requirement |
|----|-------------|
| **ARCH-R46** | The web API MUST carry the same `api_version` envelope as machine-readable command output. |
| **ARCH-R47** | A web API response MUST be identical to the equivalent command's machine-readable output. |
| **ARCH-R48** | The web API MUST NOT expose an action that is unavailable from the command line. |
| **ARCH-R49** | Live state MUST be served from the same gather that serves the other surfaces. |
| **ARCH-R50** | The event stream MUST emit a heartbeat, so a silent stream is distinguishable from a broken one. |
| **ARCH-R51** | A resumed event stream MUST NOT present values gathered before the gap as current. |
| **ARCH-R52** | Every request MUST carry a per-run token, delivered in a header and never in a URL; a request without it MUST be refused. |
| **ARCH-R53** | `Origin` and `Host` MUST be checked against the bound address, and a mismatch MUST be refused. |
| **ARCH-R54** | The client's declared `api_version` MUST be validated against the binary at build time. |
| **ARCH-R55** | An `api_version` mismatch at run time MUST be refused plainly, naming both versions, rather than rendering a partial view. |
| **ARCH-R56** | The contract artefact MUST be generated from the types the server serialises, never hand-written. |
| **ARCH-R57** | Regenerating the contract artefact MUST produce no diff, and CI MUST fail if it does. |
| **ARCH-R58** | An SDK's contract types MUST be generated from the artefact; hand-written response shapes MUST NOT be used. |
| **ARCH-R59** | The per-run token MUST be sent in the `X-Lemonfiber-Token` header. |
| **ARCH-R60** | A client MUST refuse a base address that does not resolve to a loopback address, and MUST NOT refuse a loopback address for being named rather than numeric. |
| **ARCH-R61** | The event stream MUST emit a heartbeat at least every 15 seconds, and a client MUST treat twice that in silence as a broken stream. |
| **ARCH-R62** | Every event MUST carry an `id`, and a resuming client MUST send the last one it saw as `Last-Event-ID`. |
| **ARCH-R63** | A client MUST expose a payload typed by its `kind`, never as an untyped value. |
| **ARCH-R64** | The contract artefact MUST be published with every release, and an SDK MUST vendor it from an exact revision recorded beside the copy. |
| **ARCH-R65** | Generating an SDK's contract types MUST read the vendored artefact, and MUST NOT reach the network. |
| **ARCH-R66** | Regenerating an SDK's contract types MUST produce no diff, and CI MUST fail if it does. |
| **ARCH-R67** | Generation MUST refuse an artefact whose `api_version` the SDK does not implement, naming both versions, and MUST write nothing when it refuses. |
| **ARCH-R70** | A job identifier returned by a long-running action MUST be redeemable: a client MUST be able to learn from the server that the work ended and how it went, without having held a connection open since it started. |
| **ARCH-R71** | Redeeming a job identifier MUST answer finished work with the equivalent command's machine-readable output and work still in flight with the identical document the accepting reply carried; the two MUST be distinguished by status, never by a shape only this endpoint has. |
| **ARCH-R72** | A job identifier the run did not issue MUST be refused as absent, and MUST NOT be reported as still in flight. |
| **ARCH-R73** | The contract artefact MUST NOT describe a schema in a form whose meaning depends on which JSON Schema draft the reader applies, and SDK generation MUST refuse such an artefact, naming where it occurs, rather than generate from the half of it that it reads. |
| **ARCH-R74** | A refused read MUST carry a status that distinguishes what the request named and this product does not have, from a request that could not be answered as it was asked, from a failure of the machine; the body MUST be the error envelope in every case, and the status of a failure of the machine MUST NOT be given to either of the others. |

## Shapes are generated; semantics are not

Two SDKs hand-writing this contract would be two sources of truth for it, and a third would
be a third. So the **shapes** — fields, types, optionality, permitted enum values — are
generated from the server's own `serde` types into one artefact that every SDK consumes
([ADR-0014](../../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md)).

Everything above that a schema cannot express stays here, in prose, and every SDK implements
it and tests it: the heartbeat, resumption that does not present pre-gap values as current,
the token's placement, and the refusal on mismatch. **This document is normative for what the
surface means; the artefact is normative for what it looks like.** Neither restates the other.

## How the artefact reaches an SDK

An SDK does not ask the server for the contract while it builds. It carries a copy. A build
that fetched would depend on a host being reachable, and two builds of the same commit could
produce different types.

So the artefact travels as a **vendored file pinned to an exact revision**. `lemonfiber`
publishes it with every release; an SDK fetches it once, records the revision it came from
beside the copy, and every build after that reads only what is on disk. Taking a contract
change then becomes a deliberate act that arrives as a diff somebody reads, rather than
something that happens to a build nobody was watching.

The pin is a revision rather than a version number because a revision names exactly one
artefact: the vendored bytes can always be checked against what that revision served, which
is what makes the copy verifiable rather than merely present.

Three guards sit either side of the copy. Regenerating from it must produce no diff, so a
stale generated tree fails CI rather than shipping. Generation refuses an artefact whose
`api_version` it does not implement, naming both versions and writing nothing — types that
compile and lie are worse than a build that stops, and a refusal that does not say which two
versions disagreed sends somebody looking for what it already knew.

The third guard is about the artefact's own legibility, and it is the one nothing suggested
until it was needed. An artefact can be valid, generated, pinned, regenerated without a diff,
and still not be read the same way twice — which is worse than being unreadable, because
nothing stops. A `$ref` beside a constraint is that shape: a draft-07 reader discards what
accompanies a reference, a 2020-12 reader applies both, and the draft a schema declares says
nothing about which of the two a generator happens to be.

It reached both SDKs once. A verdict carrying a diagnosis was described as a reference to the
diagnosis sitting beside the property naming the verdict. The TypeScript generator kept the
property and dropped the reference, so both such verdicts became a type holding the verdict's
name and none of the diagnosis — no summary, no meaning, no remedies. The PHP generator kept
the reference and dropped the property, so both became the diagnosis with nothing to say which
verdict it belonged to: two verdicts collapsed into one shape, and five arrived as four. Each
discarded exactly what the other kept, and both produced output that compiled and analysed
clean, which is why neither side said so.

So the artefact is held to one reading, and a generator meeting a shape that has two refuses it
rather than choosing. An annotation is not a constraint — a described reference means one thing
to every reader, and stays ordinary company.

## Related

- [sdk-ts](../../30-repos/sdk-ts.md) — the TypeScript client implementing this contract
- [versioning.md](versioning.md) — `api_version` and the envelope it belongs to
- [design-tokens.md](design-tokens.md) — the other contract `lemonfiber-web` consumes
- [ADR-0011](../../00-overview/decisions/0011-web-surface-as-a-fifth-repo.md) — why the boundary is a contract
- [ADR-0012](../../00-overview/decisions/0012-web-assets-embedded-at-build-time.md) — how the built client reaches a machine
- [C6](../../10-functional/features/c-trust/c6-web-security.md) — the security policy this sits inside
