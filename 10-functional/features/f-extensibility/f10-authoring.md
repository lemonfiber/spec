---
id: F10
title: Writing a plugin
kind: feature
area: F
audience: operator
status: draft
maturity: planned
priority: P2
labels: [extensibility, cli, verification]
requires: [F3]
relates: [F5, F6, F8, G4]
---

# F10 — Writing a plugin

**Status:** Draft · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Say what somebody actually does, from an empty directory to something an operator can
install — and say what they are given to do it with.

Everything else in this area describes a plugin from lemonfiber's side: what it is, what
it may reach, what installing one does, what stays readable afterwards. None of it says
what the author's afternoon looks like, and an extensibility design that nobody can
comfortably write against is an extensibility design in name only.

The instinct here is to reach for an SDK, because that is what the API got
([ADR-0013](../../../00-overview/decisions/0013-an-sdk-owns-the-api-client.md)). It is
the wrong instrument, and the reason is worth stating rather than leaving as an omission
somebody later reads as an oversight.

## Behaviour

### The schema is published, and it is generated

The manifest format is published as a schema with every release, generated from the types
lemonfiber deserialises rather than written beside them
([`ARCH-R92`](../../../20-architecture/contracts/plugin-manifest.md)).

That single artefact is the authoring experience. A published JSON Schema gives an author
completion, inline validation and hover documentation **in any editor that speaks it, in
any language, with nothing installed and nothing to keep in step**. It is a better
instrument than a library for the same job, and there is exactly one of it.

### There is no plugin SDK, and that is a decision rather than a gap

[ADR-0013](../../../00-overview/decisions/0013-an-sdk-owns-the-api-client.md) gives an SDK
a precise job: the web API is a **runtime protocol** with semantics no schema expresses —
a heartbeat, so a silent stream is distinguishable from a dead one; values held across a
reconnect being stale by definition; a version mismatch refusing rather than rendering a
partial view. An SDK exists so that every consumer does not reimplement those three bugs.

**A plugin has none of them.** It is not a client. It opens no connection, holds no
session, handles no stream, and authenticates to nothing. It is an artefact the core
*reads*. There is no transport to own, so there is nothing for a library to hold.

Building one anyway would do active harm, for the reason
[ADR-0014](../../../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md)
already gives: *a schema that is written is a claim about the server; a schema that is
generated is a description of it.* A plugin SDK would be a second, hand-maintained
description of the manifest, and the day it disagreed with the parser the symptom would be
a plugin that validates in its author's editor and is refused on an operator's machine.

### The binary is the toolchain

Fetching, validating, rehearsing, proving, installing and removing are already required to
be plain subcommands with meaningful exit statuses (`F3-R13`, `F6-R13`). That is the
authoring tool, and the author already has it: it is the same binary the operator runs.

Every one of them works against a local path. Nothing about writing a plugin requires the
catalogue, a network, or anybody's permission.

### A plugin is testable without the service it configures

This is the part that decides whether authoring is pleasant or miserable, and it is the
one piece that has to be built rather than reused.

A plugin's proofs — and, once [F8](f8-recipes.md) lands, its recipes — talk to a service.
Requiring the real thing would mean *"to write a plugin for Plex, own a Plex server"*, and
it would mean the catalogue's CI cannot run declared proofs at all, which `F5-R2` requires
it to. So an author records a service's responses once, and proves against the recording.

The recordings are data and are reviewed like the manifest: a fixture nobody can read is
a place for something to hide.

### A template that already passes

An author starts from a repository containing one manifest, its fixtures, and a workflow
that runs the same commands the catalogue's CI runs. Beginning from something that
validates and proves is the difference between an afternoon and a weekend, and it means
the first thing an author sees is the bar they will be held to.

### Shipping one needs nothing but a git repository

A plugin is published by pushing it somewhere an operator can fetch from. The catalogue
is a convenience and a review mechanism, not a dependency (`F5-R10`) — an author who
never opens a pull request against it has still shipped, and an operator can install what
they wrote (`F5-R4`).

## States

Per plugin, while it is being written:

| State | Meaning |
|-------|---------|
| `drafting` | A manifest exists; the schema is being satisfied |
| `schema-valid` | It conforms and may be considered |
| `rehearsed` | What installing it would do has been stated against a real stack; nothing written |
| `proven-against-fixtures` | Its declared proofs pass against recorded responses |
| `proven-against-service` | Its proofs pass against the real service |
| `published` | Fetchable from a source an operator can name |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| An author's editor knows nothing about the schema | The same commands validate from the terminal with the same messages. The schema is a convenience, not the mechanism. |
| A manifest validates in the editor and is refused by lemonfiber | A defect in the generated schema, not in the manifest. The generator and the parser come from one set of types precisely so this cannot be an ordinary occurrence (`ARCH-R93`). |
| An author has no instance of the service to test against | Record fixtures, or take somebody else's. Proving against a recording is a first-class outcome, not a degraded one. |
| Fixtures drift from what the service now does | The proof passes against the recording and fails against the service. Both results are reported as what they are; a fixture is evidence about a moment. |
| An author wants a helper library in their own language | Nothing stops them writing one. What is not published is an official second description of the format. |
| A plugin is written against a newer lemonfiber than the operator has | Refused by naming the capability the manifest asked for, never by naming a version (`F3-R21`). |
| An author asks what adapters or capabilities they may name | Answerable non-interactively from the binary; the sets are published rather than discovered (`F3-R20`). |
| A validation failure is unclear | It names the location in the manifest and what was expected, and reports every violation in one pass (`F3-R22`). Authoring is where `G4`'s error model earns its keep. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F10-R1** | The published manifest schema MUST be fetchable with every release, and MUST be sufficient to validate a manifest without running lemonfiber. |
| **F10-R2** | Authoring MUST NOT require a language-specific library, and the generated schema MUST be the only description of the manifest format published to authors; a second, hand-maintained description MUST NOT be published beside it. |
| **F10-R3** | Validating, rehearsing and proving MUST each work against a local path, with no catalogue and no network involved. |
| **F10-R4** | A plugin's declared proofs MUST be runnable against recorded responses, so that neither authoring nor the catalogue's CI requires a live instance of the service. |
| **F10-R5** | Recorded responses MUST be readable data, reviewable in the same way the manifest is. |
| **F10-R6** | A proof run against recordings MUST be reported as such, and MUST NOT be presented as a proof against the service. |
| **F10-R7** | A template plugin MUST exist that validates and proves unmodified, and its CI MUST run the same commands the catalogue's CI runs. |
| **F10-R8** | The sets an author may name — adapters, core capabilities, and what a manifest may require of lemonfiber — MUST each be readable non-interactively. |
| **F10-R9** | Publishing a plugin MUST require no infrastructure beyond a git repository. |
| **F10-R10** | An authoring failure MUST name its location in the manifest and what was expected, and MUST report every violation in one pass. |

## Related

- [F3 Plugin manifests](f3-stack-manifests.md) — the format this is the experience of writing
- [F5 The plugin catalogue](f5-plugin-catalogue.md) — where one goes afterwards, and why it is optional
- [F8 Recipes and named adapters](f8-recipes.md) — the part fixtures matter most for
- [plugin-manifest contract](../../../20-architecture/contracts/plugin-manifest.md) — `ARCH-R92`, the generated schema this is built on
- [ADR-0013](../../../00-overview/decisions/0013-an-sdk-owns-the-api-client.md) · [ADR-0014](../../../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md) — why the API gets an SDK and a plugin does not
- [G4 Error & remedy model](../g-ux/g4-error-model.md) — the standard a validation message is held to
