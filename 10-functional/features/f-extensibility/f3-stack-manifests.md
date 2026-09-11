---
id: F3
title: Plugin manifests and recipes
kind: feature
area: F
audience: operator
status: accepted
maturity: planned
priority: P1
labels: [extensibility, verification, wiring]
requires: [F1, F2]
relates: [F4, F5, F6, F7, C9, E4]
---

# F3 — Plugin manifests and recipes

**Status:** Accepted · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Say what a plugin **is**, so that everything else about plugins — how they wire, where
they come from, what installing one does — has a single thing to talk about.

A plugin is declarative data. It describes a service, what that service can do, how it
connects to the rest of the stack, the secrets it will hold, what it intends to override,
and the proofs by which it can be judged.

It contributes **no code to lemonfiber's own process**, and no opt-in changes that. What
it does contribute is a container to the stack and a script of calls to the recipe
engine, and both of those execute. The precision matters, because an image is arbitrary
code running as a daemon with network access and a mount of the operator's library, and
nobody reads one line by line. So the property this buys is not that nothing runs. It is
that **what runs, and what it may reach, is stated in advance and is checkable without
running it** — by a person reading a diff, and by lemonfiber refusing a manifest that
asks for more than the format can express. That is what lets a stranger's contribution be
judged before it is trusted, and it is why a plugin catalogue can exist at all.

The hard case this must survive is the one an operator will actually ask for: **run Plex
instead of Jellyfin**. Jellyfin is not a container in this stack — it is the identity
source the request service signs in through, whose admin password lemonfiber mints by
driving Jellyfin's own first-run setup. A plugin that only described a container would
substitute nothing. So the manifest carries **recipes**: ordered sequences of HTTP calls
that capture values, feed them into later calls, branch on what came back and wait when
something is not ready yet. Recipes are how first-run flows become data.

Where even that is not enough, a plugin **names** one of a fixed set of adapters
lemonfiber implements. It never supplies one. The bespoke stays first-party, and a plugin
reuses it by name.

## Behaviour

### A plugin is data, and every part of it is declared

A manifest declares:

- **The service** — which image runs, at which digest, on which port, and whether that
  port is an admin surface or a household one. Not how the container is assembled: that
  is written rather than supplied.
- **The capabilities it claims** — what it can do, in the vocabulary [F4](f4-capabilities.md)
  owns.
- **The wiring** — what it connects to, expressed as capabilities asked for rather than
  services named.
- **The recipes** — the ordered calls that configure it and the services around it.
- **The secrets it will hold** — each named in advance.
- **The overrides it intends** — each bundled thing it will change, named in advance.
- **The proofs** — the checks by which lemonfiber decides whether it actually worked.

Nothing a plugin does may fall outside what it declared. A recipe that captures a secret
the manifest did not name, or changes something the manifest did not list as an override,
is a validation failure rather than a surprise found later. The declaration is not
paperwork: it is what lets an operator read the blast radius before installing, and it is
what makes over-reach detectable rather than merely discouraged.

### The container is written, not supplied

A plugin says which image runs and how it should be reached. It does not say how the
container is assembled. lemonfiber writes that from the declaration
([ADR-0021](../../../00-overview/decisions/0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md)),
against the same template every bundled service is built from.

The consequence is the one an operator cares about: **installing a plugin cannot give it
more of the machine than a bundled service has.** Not a second mount, not a path outside
its own configuration directory, not a device, not a kernel capability, not another
container's network, not the container runtime's own socket. None of these is refused by
a rule somebody has to remember and apply — there is no field in which to ask, so a
manifest that tries is refused by name and told what it may declare instead.

It follows that some services cannot be plugins, and that is the intended answer rather
than an awkward one. The tunnel that keeps torrent traffic off the home address needs a
device and a kernel capability; it is the one service whose failure has consequences
outside the machine, and it is not one a stranger installs on an operator's behalf. For
anything genuinely in that position the route is [F1](f1-customisation.md)'s — fork the
stack and operate it, with the operator's own name on the decision.

### A recipe is a sequence, not a program

A recipe is an ordered list of calls. Each may:

- **capture** values out of a response and name them,
- **substitute** values captured earlier into a later call,
- **branch** on a status code or a captured value,
- **wait and retry** a bounded number of times when a service is not ready yet.

There is no arbitrary computation, no loop that does not terminate, no way to reach
anything the manifest did not declare. A recipe is powerful enough to create an account,
claim a server and read back a token — which is what a first-run flow is — and no more
powerful than that. It is Turing-incomplete by construction rather than by convention, so
"what can this plugin do?" is answerable by reading it.

### Where data will not reach, a plugin names an adapter

Some flows cannot be honestly expressed as calls and captures. For those a plugin names
one of a fixed set of **adapters** that lemonfiber implements and ships — the
Servarr-shaped registration flow, and others as they earn their place. The plugin supplies
the parameters; lemonfiber supplies the behaviour.

This keeps the awkward cases in code that is reviewed, tested and covered like the rest of
the product, while still letting a plugin reach them. A plugin naming an adapter that does
not exist is a validation failure, and the set of adapters is published rather than
discovered.

### No code, and no route to code

No contributed code is loaded into lemonfiber's own process, and there is no opt-in,
grant or sandbox that changes that. The earlier draft of this feature reserved a
sandboxed escape hatch; recipes and named adapters replace it, and reserving a code path
"for the rare case" is how the rare case becomes the common one. Native plugins are not a
supported mechanism and never become one.

The container a plugin names is a separate question, answered separately. It runs, and
what it may reach is fixed by the shape lemonfiber writes rather than by anything the
plugin asked for. Whether it deserves to run is a question about where the image came
from — pinned by digest, so the thing reviewed and the thing running are the same one —
rather than a question anybody answers by reading it.

### It validates before anything happens

Every manifest is checked against the published schema before lemonfiber acts on it, and a
manifest that does not conform is refused outright — never partly applied, never applied on
the strength of the parts that did parse. All violations are reported in one pass, each
named with its location, so a contributor fixes a manifest once rather than discovering the
next fault after correcting the last.

### Every step is reachable without a person

Fetching a manifest, validating it, rehearsing it and running its proofs are each plain
subcommands with meaningful exit statuses. Adding a plugin never requires the wizard.

## States

| State | Meaning |
|-------|---------|
| `schema-valid` | The manifest conforms to the published schema and may be considered |
| `schema-rejected` | The manifest fails validation; refused outright, nothing applied |
| `undeclared-reach` | A recipe reaches a secret or an override the manifest did not declare; refused |
| `adapter-unknown` | The manifest names an adapter this lemonfiber does not implement |
| `proofs-passing` | The declared proofs ran and passed |
| `proofs-failing` | The declared proofs ran and did not pass; the plugin is not installed |
| `proofs-unrunnable` | A declared proof could not be run; reported as unproven, never as passed |
| `image-unpinned` | A referenced image is named by tag rather than digest; refused, because a digest can always be obtained |
| `image-unproven` | A referenced image is pinned, and its registry offers no signature; installed and reported as unproven, never as verified |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| A manifest is malformed or malicious | Refuse at schema validation. Nothing in a manifest is executed, whatever it claims about itself. |
| A recipe captures a secret the manifest did not declare | Refuse the plugin. An undeclared capture is a validation failure, not a warning. |
| A recipe changes something the manifest did not list as an override | Refuse the plugin, naming what it reached for. |
| A declared proof fails | Do not install. A declared-and-failing proof is a rejection, not an advisory. |
| A declared proof cannot be run at all | Report it as unproven. An unrunnable check is not a satisfied one. |
| A recipe's call never succeeds | Bound the retries, then fail the recipe naming the call and what it last answered. |
| A recipe branches on a value that was never captured | Refuse at validation rather than at run time; the reference is checkable without running anything. |
| The manifest names an adapter that does not exist | Refuse, naming the adapter and listing what is available. |
| A referenced image is unsigned | Report it as unproven and say so. A publisher who never signed anything has made no claim, which is a different fact from a claim that did not check out, and an operator deciding whether to proceed needs to tell them apart. |
| A referenced image claims a signature that does not verify | Refuse. A claimed-and-invalid signature is worse than none and is treated as worse. |
| A manifest asks for a mount, a device, a kernel capability or a network of its own | Refuse, naming the field and listing what may be declared. There is no field for it, so this is a malformed manifest rather than a permission being withheld. |
| A manifest names an image by tag alone | Refuse. A tag is a name its publisher can repoint, so the reviewed version and the running version can differ with nothing in the manifest changing. A digest can always be obtained, so its absence is a fault in the manifest rather than a limitation of the registry — which is why this is refused where a missing signature is only unproven. |
| A service genuinely needs more than a plugin can describe | Say so plainly and name the fork route. The shape is not widened for one plugin; widening it is a change made once, for everybody. |
| The schema has moved on since the manifest was written | Answer with the capability the manifest asked for that this lemonfiber does not provide, by name, rather than with a version number. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F3-R1** | A plugin MUST be expressed as declarative data — the service, its capabilities, its wiring, its recipes, its declared secrets and overrides, and its proofs — never as executable code. |
| **F3-R2** | Every manifest MUST be validated against a published schema before lemonfiber acts on it, and a non-conforming manifest MUST be rejected outright. |
| **F3-R3** | A plugin's declared proofs MUST be runnable by the existing verification engine, the same way the bundled proofs are run. |
| **F3-R4** | A plugin whose declared proofs do not pass MUST NOT be installed. |
| **F3-R5** | A declared proof that cannot be run MUST be reported as unproven and MUST NOT be treated as passed. |
| **F3-R6** | Contributed code MUST NOT be executed, and no opt-in, sandbox or capability grant may make it executable. |
| **F3-R7** | Arbitrary native plugins MUST NOT be a supported extension mechanism. |
| **F3-R8** | A referenced image MUST be named by an immutable digest, and one named by tag alone MUST be refused. |
| **F3-R25** | Where a registry offers a signature for a referenced image it MUST be verified, and one that does not verify MUST be refused. Where none is offered the image MUST be reported as unproven, and an unproven image MUST NOT be reported as verified. |
| **F3-R9** | The manifest schema MUST be validated in the catalogue's CI so malformed contributions are caught before merge. |
| **F3-R10** | A manifest MUST review as a readable diff, with no opaque or obfuscated content required to understand what it does. |
| **F3-R11** | A plugin MUST NOT reach beyond what its manifest declares, and one that over-reaches MUST be rejected rather than confined. |
| **F3-R12** | A plugin's provenance MUST be verifiable rather than taken on trust. |
| **F3-R13** | Fetching, validating, rehearsing and proving a plugin MUST each be reachable non-interactively with a meaningful exit status. |
| **F3-R14** | A plugin that conflicts with the bundled topology MUST surface the conflict at validation rather than silently overriding it. |
| **F3-R15** | A recipe MUST be an ordered sequence of calls supporting capture, substitution of earlier captures, branching on status or captured value, and bounded wait-and-retry — and MUST NOT support unbounded computation. |
| **F3-R16** | A recipe MUST NOT reach any host, service or value the manifest has not declared. |
| **F3-R17** | Every secret a plugin will hold MUST be declared in its manifest, and capturing an undeclared value MUST fail validation. |
| **F3-R18** | Every bundled thing a plugin will override MUST be declared in its manifest, and changing an undeclared one MUST fail validation. |
| **F3-R19** | A plugin MAY name one of a published, fixed set of lemonfiber-implemented adapters for flows recipes cannot express, and MUST NOT supply an adapter of its own. |
| **F3-R20** | Naming an adapter this lemonfiber does not implement MUST be refused, naming the adapter and the set that is available. |
| **F3-R21** | A manifest MUST declare the capabilities it requires of lemonfiber, and an unmet requirement MUST be refused by naming the capability rather than a version. |
| **F3-R22** | Manifest validation MUST report every violation in one pass, each named with its location. |
| **F3-R23** | A plugin MUST NOT supply a container definition, and lemonfiber MUST generate one from what the plugin declares. |
| **F3-R24** | What a plugin's service may reach of the machine MUST be fixed by lemonfiber rather than chosen by the plugin — no mount beyond the data root and its own configuration directory, no device, no kernel capability, no network mode, no privileged container and no user override — and a manifest asking for any of them MUST be refused by name. |

## Related

- [ADR-0021](../../../00-overview/decisions/0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md) — why a plugin is data, and why its container is written rather than supplied
- [plugin-manifest contract](../../../20-architecture/contracts/plugin-manifest.md) — the fields a plugin declares in, and the entry lemonfiber writes from them
- [F1 Customisation & escape hatches](f1-customisation.md) — the escape-hatch posture this narrows to declarative data
- [F2 Service catalogue](f2-service-catalogue.md) — the bundled catalogue whose entries a plugin extends
- [F4 Capabilities & substitution](f4-capabilities.md) — the vocabulary a manifest claims and asks in
- [F5 The plugin catalogue](f5-plugin-catalogue.md) — where a manifest comes from and what vouches for it
- [F6 Plugin lifecycle](f6-plugin-lifecycle.md) — what rehearsing, installing and removing one does
- [F7 Plugin provenance](f7-plugin-provenance.md) — how what a plugin changed stays answerable
