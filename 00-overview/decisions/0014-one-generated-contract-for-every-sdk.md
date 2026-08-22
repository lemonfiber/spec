# ADR-0014: Every SDK generates its types from one artefact the server emits

**Status:** Proposed
**Date:** 2026-08-23

## Context

[ADR-0013](0013-an-sdk-owns-the-api-client.md) put the API client in `sdk-ts` and left room
for `sdk-py` and `sdk-rs`. A PHP client now exists too, and that turns a hypothetical into a
present problem: **two clients hand-writing types against a prose contract are two sources of
truth**, and a third would be a third.

ADR-0013 named this exact risk as its revisit condition — *"Hand-written types drift from the
core's serialisation more than once. That is the argument for generating the types (though
not the behaviour) from the server's own definitions."* The condition has been met before the
drift, which is the cheap moment to act.

The distinction that decision drew is the one to build on. **Shapes and semantics are
different kinds of thing**, and only one of them can be generated:

- **Shapes** — what fields exist, their types, which are optional, what an enum permits. A
  machine can check these, and a human writing them twice will eventually write them
  differently.
- **Semantics** — that a silent stream is not a healthy one, that values held across a
  reconnect gap are stale, that a version mismatch refuses rather than renders. No schema
  language expresses these. They are the prose contract's job, and each SDK implements them.

There is also a subtler point about *which* definition is canonical. A hand-written schema
would be a third artefact that can disagree with the server — the same problem in a new
place. The only definition that cannot lie about what the server sends is **the server's own
serialisation**.

## Decision

**`lemonfiber` generates a contract artefact from its `serde` types. Every SDK generates its
types from that artefact and hand-writes only behaviour.**

The artefact is one JSON document, `web-api.contract.json`:

```jsonc
{
  "api_version": 1,
  "kinds":     { "status": { /* JSON Schema for data */ }, "services": { … } },
  "endpoints": { "/api/status": { "method": "GET", "kind": "status", "params": { … } } },
  "actions":   { "retry-import": { "params": { … }, "kind": "job" } },
  "events":    ["status", "transfers", "storage"]
}
```

**Generated from `serde`, via `schemars`.** The types that serialise the response are the
types the schema describes, so the artefact cannot describe something the server does not
send.

**Checked, not trusted.** Regenerating in CI must produce no diff, exactly as `just board`
already guards the spec's generated board. A change to a serialised type that forgets to
regenerate fails the build rather than reaching an SDK.

**Not OpenAPI.** This API is not resource-oriented — it is one envelope, endpoints that mirror
commands, and a stream. An OpenAPI document would describe it as a REST model it is not, and
buy generator tooling for the half of the problem (types) that JSON Schema already covers,
while describing none of the half that is actually hard. The `kinds` map is a truer
description of a surface whose organising idea is `kind`.

**Versioned with the wire, not with the package.** The artefact carries `api_version`. SDKs
pin the artefact by `lemonfiber` release tag and regenerate deliberately, the same discipline
as every other pin in the project.

## Alternatives considered

**Each SDK hand-writes its types against the prose contract.** No generator, no build step,
and each SDK reads idiomatically. Rejected because it is the thing being fixed: N SDKs is N
opportunities to disagree with the server, and the disagreements surface as a user seeing a
missing field rather than as a failing build.

**A hand-written OpenAPI or JSON Schema document as the canonical definition.** Mature
tooling, and the definition reads as a document rather than as an output. Rejected because
it can disagree with the server. A schema that is *written* is a claim about the server; a
schema that is *generated* is a description of it.

**Generate the whole SDK, not just the types.** Least code to maintain. Rejected for the
reason ADR-0013 gave: the difficult parts are the stream's semantics, and a generator would
produce a client that compiles, talks, and quietly presents stale values as current.

**Publish the artefact from `spec` rather than `lemonfiber`.** It would make the spec
literally canonical, which is appealing given "the spec is the reference". Rejected because
the spec cannot generate it — only the code that serialises can — and a copy in `spec` would
be a second place for it to be stale. The prose contract in `spec` stays normative for
semantics; the generated artefact is normative for shapes; neither restates the other.

## Consequences

- **A new build step in `lemonfiber`** (`schemars`, a generator, and a CI check that
  regeneration is a no-op).
- **A generator per SDK**, written once each. This is the cost of not having one language's
  tooling dictate the others'.
- **Generated code is not reviewed line by line.** It is checked by the no-diff gate and by
  the SDK's own tests, and it must live in a directory that is obviously generated and never
  edited by hand.
- **An SDK cannot quietly disagree with the server about shapes.** It can still disagree
  about behaviour, which is what each SDK's tests against the prose contract are for.
- **Adding a field becomes a deliberate act across repos** — generate, regenerate, release.
  That is friction, and it is the friction that keeps `api_version` honest.

## Revisit if

- The artefact's bespoke envelope grows until it is an OpenAPI document with a different
  name. At that point the tooling argument wins and it should simply become one.
- A generator has to be hand-patched to produce idiomatic output more than occasionally,
  which would mean the shapes are not as language-neutral as this assumes.
- Only one SDK ever exists, making the artefact ceremony between a repo and itself.
