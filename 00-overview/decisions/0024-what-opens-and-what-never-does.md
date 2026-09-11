# ADR-0024: Data about this installation opens; behaviour lemonfiber implements does not

**Status:** Proposed
**Date:** 2026-09-12

## Context

Almost every guarantee this product makes is enforced by an enumeration that is
closed at compile time. That is not incidental — it is the method. What leaves
this machine is a seven-variant `Reach`; what the doctor checks is a six-variant
`Category`; which credentials exist is a `const CATALOGUE`; which API shapes a
service may name is an eight-variant `ApiKind`; which kernel capabilities a
container may hold is `ALLOWED_GRANTS`, one entry long. Each is provable by
reading it, and several are held in place by tests that do exactly that.

A plugin system's whole purpose is to open some of them. Two Accepted
requirements already say so:

- `F4-R14` — *"Extending the set of things a service may declare MUST NOT
  require a closed enumeration in first-party source to be edited, and an
  unrecognised declaration MUST be refused by name rather than by parse
  failure."*
- `G8-R15` and `G8-R16` — the account of what leaves this machine must carry a
  third kind of request, attributed to the plugin that declared it and refusable
  on its own. `Reach` cannot express that. Its members are written in Rust.

So the specification requires enumerations to open, in two places, and **no
decision says which ones**. That gap is not a tidy-up. It is the condition under
which each enumeration gets argued separately, at the moment somebody wants one
opened, with the reasoning invented on the spot — and the one that gets argued
under the most pressure is `ALLOWED_GRANTS`, because it is one entry long and
the entry is what keeps torrent traffic inside the VPN tunnel.

The other half is equally unstated. `F3-R19` requires that a plugin *"MAY name
one of a published, **fixed** set of lemonfiber-implemented adapters … and MUST
NOT supply an adapter of its own."* Fixed is the point of it, and nothing
records why that one is fixed while `Reach` is not.

## Decision

**An enumeration opens when its members are facts about a particular
installation. It stays closed when its members are behaviours lemonfiber
implements. Security policy never opens, whichever of the two it resembles.**

1. **The line.** A *fact* varies from machine to machine — what this one
   reaches, what checks this stack runs, what its services can do, which
   credentials it holds. A plugin adding to that set is describing its own
   installation, which is the thing a manifest is for. A *behaviour* is
   something lemonfiber can be asked to do; the set is fixed by the code that
   implements it, and a registry of behaviours would be a registry of code paths
   that may not exist.

2. **These open**, because their members are facts:

   | Enumeration | Why it is a fact |
   |-------------|------------------|
   | `Reach` — what leaves this machine | A plugin's declared host is a destination *this* installation has, and `G8-R15` requires it attributed and `G8-R16` refusable on its own |
   | The doctor's `Category` | A plugin's declared proof is a check *this* stack runs (`C1-R15`) |
   | The capability vocabulary | What a service can do, which `F4-R4` already lets a plugin extend under its own namespace |
   | The credential catalogue | A plugin's secret is a credential *this* stack holds (`F7-R8`), and rotation must reach it (`A7-R15`) |

3. **These never open**, because their members are behaviours or policy:

   | Enumeration | Why it stays closed |
   |-------------|---------------------|
   | `ApiKind` — the adapters | Each variant *is* a client lemonfiber implements. `F3-R19` fixes the set deliberately: a plugin names one, never supplies one |
   | `KeySource` | Each variant is a reader lemonfiber implements — a file format it parses, or a flow it drives |
   | `ALLOWED_GRANTS` | Security policy. It is not data about an installation and never becomes it |

4. **Opening is not adding variants.** A closed enumeration grown by one variant
   is still closed, and is now a wire-breaking change every time it grows —
   [versioning](../../20-architecture/contracts/versioning.md) says adding a
   permitted value increments, because a stricter parser rejecting an unknown
   one is correct behaviour. Opening means replacing the variant with an
   **identified record**: a stable id, and the fields the surfaces already
   render beside it. Growth then stops being a schema event, which is the whole
   gain.

5. **Refusal stays by name.** An unrecognised *instruction* is refused, naming
   what was not recognised and what is available (`F4-R14`, `ARCH-R91`). Opening
   the set of things that may be named does not make an unknown name tolerable;
   it makes the known set data instead of source.

6. **The closed ones stay closed by test.** `ApiKind`'s closedness is currently
   enforced by an architecture test that reads `schema.rs`, extracts the enum
   body and asserts every variant is acted on somewhere. That test is possible
   only because there is source to scrape — the same property that makes the
   enumeration closed. An enumeration that opens loses that test and owes a
   different one.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Open all of them, uniformly** | Simple, and it opens `ALLOWED_GRANTS` — a plugin able to extend the kernel-capability allow-list is a plugin able to grant itself `NET_ADMIN`. Uniformity is not a virtue when one member of the set is the control that keeps a home IP address off a torrent swarm. |
| **Close all of them, and grow the first party** | What happens today. Every plugin's destination, check, capability and credential would need a lemonfiber release, which contradicts `F1-R5` and is precisely the coupling the extensibility area exists to remove. |
| **Decide per enumeration, when each one comes up** | No stated rule means the argument gets made four times and the four answers will not agree. It is also the mechanism by which `ALLOWED_GRANTS` eventually opens: under pressure, for one plugin somebody wants, by whoever is on the change. |
| **Open by adding a variant whenever one is needed** | Every addition breaks the wire under this project's own versioning rule, and the additions come from manifests nobody has read yet — so they cannot be enumerated at build time at all. It is not a slower version of opening; it does not work. |
| **A capability grant that lets a trusted plugin extend a closed set** | The escape hatch `F3` already refused once for code: *"reserving a code path 'for the rare case' is how the rare case becomes the common one."* A grant that extends `ApiKind` is a plugin supplying an adapter with extra steps. |
| **Keep `Reach` closed and exempt plugin hosts from the account** | Narrows `G8-R3` and `G8-R5` the moment plugins exist, which is the promise being abandoned rather than kept. `#293` already decided against it. |

## Consequences

**Opening `Reach` is wire-breaking, and this is the last cheap moment to do it.**
It derives `JsonSchema` and crosses the web API inside the `outbound` kind, so it
reaches `lemonfiber-web` and both SDKs through the generated contract. Before
`1.0.0` that is a regeneration; after it, a migration with an `api_version`
attached. `G8-R15`–`G8-R17` already commit to the behaviour, so the only question
left is when the type moves.

**The closed sets acquire a published list, and owe one.** `F3-R19` and `F3-R20`
already require the adapters to be published rather than discovered, and to be
refused by name with the available set alongside. `KeySource` and
`ALLOWED_GRANTS` now owe the same, because a fixed set nobody can read is
indistinguishable from an arbitrary one.

**Every surface stops assuming a fixed set.** Four of them render these —
CLI, TUI, web and companion — and each currently knows the variants. `ARCH-R81`
already tells a client to tolerate a capability name it does not recognise; that
tolerance now extends to reaches, categories and credentials.

**Some tests change shape rather than surviving.** The scrape-the-source test
dies with the enumeration it reads. What replaces it is not a weaker test but a
different one: that every registered member is rendered, attributed and
switchable, which is what the enumeration was standing in for.

**Revisit if** an enumeration turns out to be genuinely both — a behaviour
lemonfiber implements whose members a plugin legitimately adds to. The honest
answer there is two enumerations, a closed one of implementations and an open one
of instances, rather than one that is half-open and has to be explained.

## Related

- [F4](../../10-functional/features/f-extensibility/f4-capabilities.md) — `F4-R14`, the requirement this decides the shape of
- [G8](../../10-functional/features/g-ux/g8-privacy.md) — `G8-R15`–`G8-R17`, which commit to opening `Reach`
- [F3](../../10-functional/features/f-extensibility/f3-stack-manifests.md) — `F3-R19`, the fixed adapter set this keeps fixed
- [versioning](../../20-architecture/contracts/versioning.md) — why adding a permitted value is a breaking change
- [web-api](../../20-architecture/contracts/web-api.md) — `ARCH-R81`, tolerating a name a client does not know
- [ADR-0021](0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md) — the same instinct applied to the container: what a plugin may ask for is fixed, what it may say is data
