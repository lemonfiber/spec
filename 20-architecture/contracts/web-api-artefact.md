# Contract: the web API artefact

**Status:** Accepted

Part of the [web API contract](web-api.md): the machine-readable artefact the core
generates from the types it serialises, what it carries, and how it reaches an SDK.
The requirements it describes are listed with the rest of the contract's, under
[Requirements](web-api.md#requirements).

## Shapes are generated; semantics are not

Two SDKs hand-writing this contract would be two sources of truth for it, and a third would
be a third. So the **shapes** — fields, types, optionality, permitted enum values — are
generated from the server's own `serde` types into one artefact that every SDK consumes
([ADR-0014](../../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md)).

The artefact describes what the server answers with, kind by kind. It does not describe what
a request carries: the body each setup step takes — an answer to one of the wizard's
questions, the choice a recovery takes — and the actions `POST /api/actions/<name>` accepts,
with the arguments each takes and the consent it asks for, are the server's types and no
published shape. A client that sends one copies it from the server's source, and nothing
holds that copy to the server. `ARCH-R133` puts the request bodies in the artefact, and
`ARCH-R134` the actions, so that a client generates both as it generates the kinds.

Nor did it describe where anything is asked for. Every SDK held its own list of the reads,
written by hand and checked against the [`## Reading`](web-api.md#reading) block of the
contract, which is a fourth copy of a table the surface already routes by. `ARCH-R159` puts the reads in the artefact: each path the
surface serves a read at, the query parameters it takes and whether each may be given more
than once, and the kind it answers with, or that it answers with a file. They are generated
from the tables the surface routes and refuses by, so a read the surface gains is a read every
client generates.

Everything in the contract that a schema cannot express stays there, in prose, and every SDK
implements it and tests it: the heartbeat, resumption that does not present pre-gap values as
current, the token's placement, and the refusal on mismatch. **The
[contract](web-api.md) is normative for what the surface means; the artefact is normative for
what it looks like.** Neither restates the other.

### The refusals it lists

A refusal's body is a kind the artefact already describes, `error`, and a problem's `code` is
a string there, because the core raises hundreds of codes and most of them reach a client
only to be shown. The few that a client branches on are the codes a refusal carries, so the
artefact lists those beside the kinds, keyed by code:

```json
"refusals": {
  "ADMIT-4": {
    "name": "NOT_ADMITTED",
    "status": 403,
    "description": "Raised when a request carried no token or session this run admits."
  }
}
```

- `name` is the code's name in the core's registry.
- `status` is the one status the refusal is answered with.
- `description` is the registry's own line about it.

An SDK generates a typed list from this, a value per code, and reads a refusal's code into
it. A code the list does not name reads as none (`ARCH-R138`). No SDK and no client keeps a
hand-written copy of the list: a copy is a second place to update, and the one that was not
updated is the one that reads a new refusal as an old one.

The list is additive in the way the kinds are. A code is added when the core begins to
refuse with it, and it keeps its spelling and its number for good. Adding one leaves
`api_version` alone.

A refusal that says the operator's yes no longer matches what they agreed to is one a client
branches on, whatever route ends with it. A repair, a restore or a replacement takes the offer
its reading answered as its yes, and refuses it when what it would act on has moved since
(`N2-R6`, `A5-R13`). That refusal is how a client knows to read again and offer the new
answer, rather than report a failure, so its code is listed here beside the web API's own. It
ends long-running work rather than a request, so it carries the status the work is answered
with when its name is redeemed, which a client reads beside the code, as it reads any other.

## What else each release publishes

The kinds, reads, actions and refusals are what a client generates code from. Five more
things are published beside them, each generated from what the core already holds, so that
no reader keeps a hand-written copy of something the server knows.

**The event stream.** `GET /api/events` sends events whose payloads are the server's types
like any kind's. The artefact describes each event kind the stream emits with the schema of
its payload, and the interval the heartbeat keeps (`ARCH-R61`), so a client generates the
events it handles as it generates the kinds it reads (`ARCH-R173`).

**Examples.** A schema says what may be sent; an example says what is. The artefact carries
one example for each kind, each read and each action, taken from the core's golden test
fixtures rather than written for the page, and CI validates every example against its schema,
so an example that has stopped being true fails a build rather than a reader (`ARCH-R174`).

**The code registry.** Every code the core raises has a family, a name, a severity, the exit
code the command line ends with, the HTTP status the web API answers with, a summary, what it
means, what to do about it, and the version it appeared in. The core publishes that registry
as `contract/codes.json`, generated from the registry it raises from, and the reference page
`reference/error-codes.md` is generated from that file. The refusals list above is the part
of it a client branches on; the registry is the whole of it, for the reader who is shown a
code and asks what it means (`ARCH-R175`).

**What changed.** Each release attaches `contract-diff.json`: every kind, definition, read,
action, refusal and event that release's artefact added, removed or changed against the
previous release's. An SDK reading the diff knows what taking the release means before it
regenerates, and the documentation shows it per release (`ARCH-R176`).

**OpenAPI.** Tools that read OpenAPI and nothing else are given
`contract/web-api.openapi.json`, generated from the artefact, and CI refuses it when it
differs from what the artefact generates. The artefact stays the source; the OpenAPI
document is a rendering of it (`ARCH-R177`).

## How the artefact reaches an SDK

An SDK does not ask the server for the contract while it builds. It carries a copy. A build
that fetched would depend on a host being reachable, and two builds of the same commit could
produce different types.

So the artefact travels as a **vendored copy pinned to an exact revision**. `lemonfiber`
publishes it with every release; an SDK fetches it once, records the revision it came from
beside the copy, and every build after that reads only what is on disk. Taking a contract
change then becomes a deliberate act that arrives as a diff somebody reads, rather than
something that happens to a build nobody was watching.

The artefact is a directory, `contract/web-api/`, so that no file in it outgrows a reader:

- `index.json` carries `api_version` and names every other file: `kinds` maps each kind to
  its file, and `key_callable`, `reads` and `refusals` each name the file holding that list.
- `kinds/<kind>.json` is the schema of the envelope carrying that kind.
- `defs/<Name>.json` is one definition. Every definition is here, whether one kind carries it
  or nine, so a definition several kinds share is written once.
- `key-callable.json`, `reads.json` and `refusals.json` are the lists the index names.

A `$ref` is a path to a definition's file, resolved against the file it appears in:
`../defs/Remedy.json` from a kind, `Code.json` from another definition. A definition's name is
its file's name, and it describes one shape wherever it is reached. Each release carries the
directory as one archive, `web-api.contract.tar.gz`, with `web-api/` at its root.

The pin is a revision rather than a version number because a revision names exactly one
artefact: the vendored bytes can always be checked against what that revision served, which
is what makes the copy verifiable rather than merely present.

Three guards sit either side of the copy, and a fifth reads every reference in it. Regenerating from it must produce no diff, so a
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

The fourth guard is the same failure one step along: an artefact every reader agrees about, in
which two authorities have chosen one name. A generator writes names of its own beside the ones
the artefact gives it — the object every kind hangs off, the union of every kind the server may
send, the envelope each kind carries, one type per kind. Where it flattens a kind's definitions
into a single scope, those two sets share that scope, and nothing holds them apart.

It reached one SDK once. The `plugins` kind gained a definition named `Kind` — *the kind of
value a key must hold*, five and closed — while the TypeScript generator writes `Kind` for the
union of every kind the server may send. Both were emitted. The compiler reports a duplicate
identifier in a generated file, the union becomes an error type, and every use of it fails
somewhere else: a literal kind is not assignable to `Kind`, a type parameter cannot index
`ByKind`, a payload arrives `unknown`. Six errors across three files, one of them generated and
two of them never touched, and not one of them naming a contract. The PHP SDK never saw it,
because it inlines a kind's definitions into an alias scoped to one class — which is why this
is a rule about the artefact rather than about whichever generator happens to flatten.

So a definition's name is its own, and where a generator has already claimed one, generation
says so at the point it would collide rather than leaving it to whatever the output does next.
The name moves in the artefact: the names a generator writes are an SDK's published surface,
and moving one of those instead would break every caller to spare the producer a rename.

The fifth guard is about a reference that leads nowhere. A generator that cannot resolve a
`$ref` still has a field to describe, and the cheapest description is a type that accepts
anything: it compiles, it analyses clean, and every value of that field reaches a caller
unchecked. So generation refuses a reference it cannot resolve, naming the reference and the
file it appears in, and writes nothing. A copy taken half-read, a definition missing from it,
or a reference in a form the generator does not follow all stop the build where they are,
rather than surfacing later as a field nothing checks (`ARCH-R170`).

## Related

- [web-api](web-api.md) — the contract the artefact describes, and its requirements
- [ADR-0014](../../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md) — one generated contract for every SDK
- [sdk-ts](../../30-repos/sdk-ts.md), [sdk-php](../../30-repos/sdk-php.md), [sdk-python](../../30-repos/sdk-python.md) — the SDKs generated from it
