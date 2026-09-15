# Contract: `capability-vocabulary.json`

**Status:** Draft

The published set of things a service can do, so that wiring can ask for one
rather than name a service, and a plugin can claim one rather than invent a name
for it.

**Satisfies:** [F4-R1](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R2](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R3](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R4](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R18](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R19](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R23](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R24](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F9-R1](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md),
[F9-R3](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md),
[F10-R8](../../10-functional/features/f-extensibility/f10-authoring.md)

---

## Why this file exists

[F4](../../10-functional/features/f-extensibility/f4-capabilities.md) has been
able to describe a capability since it was written, and has had nothing to point
at. The consequence was not theoretical. Every capability the two published
plugins claim is namespaced with the plugin's own id — `komga:opds`,
`uptime-kuma:status-page` — because `F4-R4` forbids a plugin inventing a
core-looking name, and there was no core name to use instead. A namespaced
capability is inert until something asks for it, and nothing asks.

So both plugins install a container, pass their proofs, and **wire nothing**.
They can be read and they cannot be useful, and the reason is one missing
artefact rather than anything either author did.

This is that artefact. It is a single file, generated from the types lemonfiber
reads it with, attached to every release, and readable from the binary with no
network and no running stack.

## What a capability is, and what it is not

A capability is **a named, contracted thing a service can do**, carrying probes
that demonstrate the contract holds. Three things in this system are called
capabilities and only one of them is this:

| Thing | Where it is read | What it means |
|-------|------------------|---------------|
| **This** | `provides` on a service, and the wiring that asks | What a *service* can do |
| lemonfiber's own | `[requires].capabilities` in a manifest, `GET /api/capabilities` (`ARCH-R78`) | What *lemonfiber* offers the thing reading it |
| Kernel | `grants` in `stack.toml` | What the *kernel* lets a container do |

The third was renamed out of collision when `F4-R13` was written. The first two
still share a word, and the field a name is read in is what tells them apart —
which is enough for a reader and not enough for a gate. So the two sets are
published as separate artefacts and **no name may appear in both** (`F4-R23`).
A name that did would be one whose meaning depended on which field it was
sitting in, which is exactly the failure `F4-R13` refused for the kernel set.

## Names

| Kind | Shape | Example | Who may declare it |
|------|-------|---------|--------------------|
| Core | `area.verb` — lowercase, exactly one dot | `media.serve` | lemonfiber, here |
| A plugin's own | `<plugin-id>:<name>` — exactly one colon | `komga:kobo-sync` | the plugin whose id prefixes it |

The two shapes are disjoint, so which kind a name is can be decided by reading
the name. That is what lets `F4-R4` be a rule a gate can hold rather than a
convention a reviewer has to remember: a plugin declaring `media.serve` in
`provides` without binding its probes is refused, and a plugin declaring
`plex:direct-play` is accepted and treated as inert.

A core name is never reused and never quietly removed. Removing one advances the
generation and the removed name is carried in `removed`, so a manifest naming it
is told *it was removed in generation N* rather than *no such capability* — the
same distinction `F3-R21` draws between a version that is older and a thing that
has gone.

## The artefact

```json
{
  "vocabulary": "service-capabilities",
  "vocabulary_version": 1,
  "capabilities": [
    {
      "name": "media.serve",
      "summary": "Serves the filed library to a player, with its own catalogue of what it holds.",
      "contract": "A service claiming this holds a catalogue of what is in the library …",
      "declared_by": ["jellyfin", "audiobookshelf", "calibre-web-automated", "navidrome"],
      "probes": [
        {
          "id": "guarded",
          "title": "An anonymous caller is refused the catalogue",
          "asks": "a read of the catalogue of what it holds, presenting nothing",
          "why": "A refusal is the one answer no port proxy can produce …",
          "credential": "none",
          "requires": { "status": [401, 403], "body": [] }
        },
        {
          "id": "catalogue",
          "title": "It answers with the catalogue of what it holds",
          "asks": "the same read, with the credential the operator holds",
          "why": "…",
          "credential": "operator",
          "requires": { "status": [200], "body": ["json", "json_has_keys", "json_types"] }
        }
      ]
    }
  ],
  "removed": []
}
```

| Field | Notes |
|-------|-------|
| `vocabulary` | Which of the three sets above this is. Present so a file read out of context cannot be mistaken for another one. |
| `vocabulary_version` | Monotonic integer. Advanced by a removal or by a contract narrowing; adding a capability does not move it. |
| `capabilities[].name` | The core name. Unique, and never reused. |
| `capabilities[].summary` | One line, in the terms `F2-R1` asks of a bundled service |
| `capabilities[].contract` | What a service claiming it undertakes to do. The prose a plugin author is held to. |
| `capabilities[].declared_by` | Every bundled service declaring it. **Generated from the stack manifest**, not written here — see below. |
| `capabilities[].probes` | What must be demonstrated. At least one. |
| `removed` | Names a published generation carried and this one does not, each with the generation it went in. |

### `declared_by` is generated, and it is what enforces `F9-R3`

`F9-R3` refuses a capability into the vocabulary that no bundled service
declares, because *an untested contract is worse than an absent one — a plugin
author will trust it.* That rule needs somebody to hold it, and a hand-written
list of claimants would be a second statement of a fact the stack manifest
already makes.

So `declared_by` is read out of the pinned stack manifest at generation time, and
a capability nothing declares **fails generation**. The rule is enforced by the
artefact refusing to be built rather than by a reviewer noticing.

It follows that moving the stack pin can move this file, which is the intended
behaviour: a bundled service that stops declaring a capability changes what
lemonfiber publishes, and a change nobody meant shows up as a diff in a generated
artefact rather than as a plugin that stopped wiring six months later.

### Two bundled services declare nothing, and that is the right answer

Recyclarr keeps quality profiles in step; Unpackerr unpacks a completed download.
Both act on the filesystem and on other services' configuration, and **neither is
asked for through an interface**. Nothing can substitute for them by asking,
because there is no asking — so there is no capability for them to fill, and
inventing one would put a contract in the vocabulary that no probe could
demonstrate.

A capability earns its place by something needing to ask for it. These two are
the honest demonstration that the rule bites.

## Probes

`F4-R3` requires every core capability to carry probes that demonstrate its
contract. The difficulty is that a capability is one contract and its claimants
are many services, each answering at a path of its own: Jellyfin's catalogue is
not Komga's and neither is Audiobookshelf's.

So the two halves are split where they belong. **The vocabulary declares what
must be shown. The claimant declares where to ask.**

| Declared here | Declared by the claimant |
|---------------|--------------------------|
| What question the probe asks, in prose | The method and path that asks it on this service |
| Which statuses are an acceptable answer | Which of them this service gives |
| Which kinds of body constraint the answer must carry | The constraint itself |
| Whether a credential is needed to ask | The recorded response it was answered with |

A claim that does not bind every probe its capability declares is refused, naming
the probe (`ARCH-R109`). A binding whose expectation is weaker than the probe
requires — a status outside the set, or no constraint where one is required — is
refused, naming the probe and what it requires. Neither is a parse failure.

### A probe carries who it is asked as

| `credential` | Meaning | Against a live service with nothing held |
|--------------|---------|------------------------------------------|
| `none` | Anyone may ask | Runs |
| `operator` | The credential the operator holds for this service | **Unproven** — never failed |

The second is not a weakening. It is `F3-R5` and `F4-R7` applied honestly: a
manifest cannot hold a credential until recipes arrive
([F8](../../10-functional/features/f-extensibility/f8-recipes.md)), so a
credentialed probe run against a live service with nothing to present has
established nothing — and reporting that as a failure would say the service is
broken when the runner is. Against a recording it runs like any other, and is
reported as a proof against recordings and never as one against the service
(`F10-R6`).

### A refusal is evidence; a status alone usually is not

`ARCH-R105` refuses a manifest whose every proof constrains only a status,
because Docker publishes a port by putting a proxy in front of it and that proxy
accepts a connection before knowing whether anything inside is listening.

A `guarded` probe is the exception the rule leaves room for, and the reason is
worth stating rather than looking like an inconsistency. **A `401` is not
something a port proxy can produce.** An emptied container answers a refused
connection or a gateway error; only an application that has a protected surface
answers that it is protected. So `"body": []` on a `guarded` probe is not a
weaker expectation — it is the one case where the status *is* the body's job.

It is also the one probe every claimant can bind, which is why it is required
almost everywhere: measured across the bundled stack, the anonymous read of the
thing a capability is about is refused by Sonarr, Radarr, Lidarr, Bindery,
Prowlarr, SABnzbd, Bazarr, Jellyfin, Audiobookshelf, Calibre-Web and Seerr, and
answered by none of them. A media server that stopped refusing it would be
publishing somebody's library to the household network, and this is the probe
that notices.

## What is published, where

| Artefact | Asset on every release | Read from the binary |
|----------|------------------------|----------------------|
| This | `capability-vocabulary.json` | `lemonfiber plugin capabilities --json` |
| [The extension points](extension-points.md) | `extension-points.json` | `lemonfiber plugin extension-points --json` |
| [The manifest schema](plugin-manifest.md#the-published-schema) | `plugin-manifest.schema.json` | `lemonfiber plugin schema` |

All three are generated, committed, and regenerated by CI with a diff failing the
build (`ARCH-R106`, `ARCH-R111`, `ARCH-R93`). None is hand-written, for
[ADR-0014](../../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md)'s
reason: *a schema that is written is a claim about the server; a schema that is
generated is a description of it.*

Every read works with no network, no catalogue and no running stack, and states
the generation it is reporting. An author asking what they may claim gets an
answer from the binary they already have (`F10-R8`).

## Validation

| Rule | Failure |
|------|---------|
| Every `provides` entry is a core name or is namespaced with the plugin's id | Name given, with the two shapes |
| Every core name in `provides` names a capability this generation carries | Name given, with the ones that exist |
| A name this generation removed | Name given, with the generation it went in |
| Every core name in `provides` has exactly one `[[claim]]` | Name given |
| Every `[[claim]]` names a capability in `provides` | Both given |
| Every probe the capability declares is bound | Probe and capability given |
| No binding names a probe the capability does not declare | Probe given, with the ones it declares |
| A binding's status is one the probe permits | Status given, with the set |
| A binding carries one of the body constraints the probe requires | Probe given, with the kinds |
| Every binding names a recorded response that exists | Path given |

## Requirements

| ID | Requirement |
|----|-------------|
| **ARCH-R106** | The core capability vocabulary MUST be published as one machine-readable artefact generated from the types lemonfiber reads it with, MUST carry its own generation, and regenerating it MUST produce no diff, with CI failing if it does. |
| **ARCH-R107** | The set of bundled services declaring each capability MUST be generated from the stack manifest rather than restated, and generating a vocabulary carrying a capability no bundled service declares MUST fail. |
| **ARCH-R108** | The capability vocabulary, the extension points and the generated manifest schema MUST each be attached to every release under a stable name, and MUST each be readable from the binary with no network, no catalogue and no running stack, stating the generation reported. |
| **ARCH-R109** | A service claiming a core capability MUST bind every probe that capability declares to a request on itself, an expectation the probe permits and a recorded response; a claim leaving one unbound, naming one the capability does not declare, or carrying an expectation weaker than the probe requires MUST be refused by naming the probe rather than by parse failure. |
| **ARCH-R110** | A bundled service MUST declare the capabilities it provides in the stack manifest, in this vocabulary, and a name the vocabulary does not carry MUST be refused by name. |

## Related

- [F4 The capability vocabulary](../../10-functional/features/f-extensibility/f4-capabilities.md) — the model this publishes
- [F9 Capabilities of the bundled services](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md) — the twenty that implement it, and the wiring converted to ask in it
- [extension-points](extension-points.md) — the second vocabulary, and the same treatment
- [plugin-manifest](plugin-manifest.md) — where a claim is declared and its probes bound
- [stack-manifest](stack-manifest.md) — where a bundled service declares what it provides
- [web-api](web-api.md) — `ARCH-R78`, lemonfiber's own capability set, which this is not
