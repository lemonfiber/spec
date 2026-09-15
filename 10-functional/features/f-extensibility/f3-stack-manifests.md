---
id: F3
title: Plugin manifests
kind: feature
area: F
audience: operator
status: accepted
maturity: planned
priority: P1
labels: [extensibility, verification, wiring]
requires: [F1, F2, C1, G4]
relates: [F4, F5, F6, F7, F8, B3, C3, C9, E4]
---

# F3 — Plugin manifests

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
substitute nothing.

So a manifest carries more than a container, and the rest of it is
[F8](f8-recipes.md): the ordered calls that turn a first-run flow into data, and the
named adapters for the flows even those cannot express. This feature says what a manifest
*is* and what may be written in it; F8 says what the calls in it may do.

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
- **The recipes** — the ordered calls that configure it and the services around it,
  which [F8](f8-recipes.md) governs.
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

### Recipes and adapters are their own feature

A manifest that only describes a service can add one; it cannot *substitute* one, because
the case this design exists for needs an account created and a token read back. Those
flows are recipes, and recipes are [F8](f8-recipes.md).

They are separated because they are different in kind. What this feature describes is a
container whose reach lemonfiber fixes. A recipe runs with lemonfiber's own authority, on
behalf of a manifest a stranger wrote, and it is where the risk in the design actually
lives. Keeping them apart lets the simplest useful plugin — one that adds a service — be
operated before the most consequential mechanism arrives.

### Extending lemonfiber itself, in terms lemonfiber already runs in

A plugin adds a service beside lemonfiber. It may also add to what lemonfiber *says* — a
check the doctor runs, and the remedy that check carries when it does not pass.

That is not a second mechanism. `F3-R3` already has a plugin's declared proofs running in
the existing verification engine, and [`C1-R15`](../c-trust/c1-diagnostics.md) already has
one of them appearing as a check like any other, attributed to the plugin. What follows
generalises that one case rather than opening a door beside it.

The rule it generalises is the load-bearing part: **a contribution is an entry in a
register some engine already enumerates, never an interpreter of its own.** The doctor
already runs checks independently, bounds each one, keeps `unverified` distinct from
`pass`, and carries a remedy in the error model's four parts. A plugin's check is another
row in that register. Nothing new evaluates it — which is why no contributed code runs
here: there is nothing for contributed code to be.

Two things an operator might reasonably ask for are absent, and the same test refuses both.

| Asked for | Answer |
|-----------|--------|
| A dashboard panel of its own | No. The six sections are fixed (`B3-R2`) and the renderer has no panel vocabulary to declare into, so a declared panel would need something new to read it — and a new interpreter is contributed code wearing a data costume. A plugin reaches the dashboard the way everything else does: its checks become findings, and the summary is computed from findings (`G7-R2`). |
| A command of its own | No. The command surface is generated from the types the binary parses (`ARCH-R68`), so a declared verb would be a second source for something that has one, and CI already fails when those two disagree. A contributed check needs no verb: the doctor already runs a single named check (`C1-R6`), so the plugin's check is reachable by name the day it is installed. |

A repair that *acts* is the third of these and is absent for a different reason. It is not
missing an interpreter; it is a recipe. The ordered calls such a repair would make are
exactly [F8](f8-recipes.md)'s four operations, bounded by its declared pairs, and a second
way to make them here would be the duplicate mechanism this section exists to refuse. So
what a plugin may contribute to remediation is the **guided** half
[`C3-R3`](../c-trust/c3-auto-remediation.md) already distinguishes — the explanation and
the next action, rendered rather than performed — and the automatic half arrives with
recipes or not at all.

### Adding is not overriding

A contribution is namespaced to the plugin that made it and cannot take the identity of a
bundled one. A plugin may not replace, re-order or suppress a check lemonfiber ships, or
the remedy that check carries.

This is not tidiness. What lemonfiber says about itself is the one account an operator has
that is not a claim by the thing being described, and a plugin able to edit it could make
a stack look healthy by removing whatever noticed it was not. Standing in for something
bundled is a real requirement with a real home: [F9](f9-bundled-capabilities.md), where
substitution is already the subject and is already recorded as an operator's choice rather
than a manifest's assertion.

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
| `contribution-declared` | The manifest declares a check or a remedy at a published extension point |
| `contribution-unrun` | A declared contribution could not be run or rendered; reported as unrun, never as passed and never omitted |
| `contribution-shadowing` | A contribution would take the identity of a bundled check or remedy; refused |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| A manifest is malformed or malicious | Refuse at schema validation. Nothing in a manifest is executed, whatever it claims about itself. |
| A recipe captures a secret the manifest did not declare | Refuse the plugin. An undeclared capture is a validation failure, not a warning. |
| A recipe changes something the manifest did not list as an override | Refuse the plugin, naming what it reached for. |
| A declared proof fails | Do not install. A declared-and-failing proof is a rejection, not an advisory. |
| A declared proof cannot be run at all | Report it as unproven. An unrunnable check is not a satisfied one. |
| The manifest names an adapter that does not exist | Refuse, naming the adapter and listing what is available. |
| A referenced image is unsigned | Report it as unproven and say so. A publisher who never signed anything has made no claim, which is a different fact from a claim that did not check out, and an operator deciding whether to proceed needs to tell them apart. |
| A referenced image claims a signature that does not verify | Refuse. A claimed-and-invalid signature is worse than none and is treated as worse. |
| A manifest asks for a mount, a device, a kernel capability or a network of its own | Refuse, naming the field and listing what may be declared. There is no field for it, so this is a malformed manifest rather than a permission being withheld. |
| A manifest names an image by tag alone | Refuse. A tag is a name its publisher can repoint, so the reviewed version and the running version can differ with nothing in the manifest changing. A digest can always be obtained, so its absence is a fault in the manifest rather than a limitation of the registry — which is why this is refused where a missing signature is only unproven. |
| A service genuinely needs more than a plugin can describe | Say so plainly and name the fork route. The shape is not widened for one plugin; widening it is a change made once, for everybody. |
| The schema has moved on since the manifest was written | Answer with the capability the manifest asked for that this lemonfiber does not provide, by name, rather than with a version number. |
| A manifest declares a dashboard panel or a command of its own | Refuse, naming the field and saying what may be contributed instead. There is no point to declare either at, so this is a malformed manifest rather than a permission withheld. |
| A declared check cannot be run | Report it as unrun, naming the check and the plugin. An unrunnable check is not a passing one, and one that quietly disappears from the run is worse than one that fails. |
| A contributed remedy would act on the machine rather than be read | Refuse it as a remedy. A remedy is rendered; a thing that acts is a recipe, and a recipe is declared as one. |
| A contribution names a bundled check or remedy | Refuse, naming both. Adding is not overriding, and overriding something bundled is F9's subject rather than a manifest's. |
| A plugin is removed | Its contributions go with it. A stack with no plugin installed answers exactly as one that never had any. |

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
| **F3-R15** | *Withdrawn — carried to [F8-R1](f8-recipes.md) when recipes became their own feature. The number is not reused.* |
| **F3-R16** | *Withdrawn — carried to [F8-R10](f8-recipes.md) when recipes became their own feature. The number is not reused.* |
| **F3-R17** | Every secret a plugin will hold MUST be declared in its manifest, and capturing an undeclared value MUST fail validation. |
| **F3-R18** | Every bundled thing a plugin will override MUST be declared in its manifest, and changing an undeclared one MUST fail validation. |
| **F3-R19** | *Withdrawn — carried to [F8-R11](f8-recipes.md) when recipes became their own feature. The number is not reused.* |
| **F3-R20** | *Withdrawn — carried to [F8-R12](f8-recipes.md) when recipes became their own feature. The number is not reused.* |
| **F3-R21** | A manifest MUST declare the capabilities it requires of lemonfiber, and an unmet requirement MUST be refused by naming the capability rather than a version. |
| **F3-R22** | Manifest validation MUST report every violation in one pass, each named with its location. |
| **F3-R23** | A plugin MUST NOT supply a container definition, and lemonfiber MUST generate one from what the plugin declares. |
| **F3-R24** | What a plugin's service may reach of the machine MUST be fixed by lemonfiber rather than chosen by the plugin — no mount beyond the data root and its own configuration directory, no device, no kernel capability, no network mode, no privileged container and no user override — and a manifest asking for any of them MUST be refused by name. |
| **F3-R26** | A plugin MAY declare contributions to lemonfiber's own behaviour, and every contribution MUST be data an engine lemonfiber already runs interprets, in that engine's existing vocabulary. A contribution that would require an interpreter lemonfiber does not already have MUST NOT be declarable. |
| **F3-R27** | A declared contribution MUST be run or rendered by that engine exactly as its bundled entries are — the same evaluation, the same verdicts, the same bounds — and MUST be attributed to the plugin that declared it wherever it appears. |
| **F3-R28** | A declared contribution that cannot be run or rendered MUST be reported as unrun, naming it and the plugin, and MUST NOT be reported as passed, as satisfied, or by being omitted. |
| **F3-R29** | A contributed remedy MUST be text in the error model's shape, rendered and never executed; a contribution that would act on the operator's system MUST be refused as a remedy and MUST be declared as a recipe or not at all. |
| **F3-R30** | A plugin's contributions MUST be withdrawn when the plugin is removed, and lemonfiber with no plugin installed MUST answer exactly as it does with none ever declared. |

## Related

- [ADR-0021](../../../00-overview/decisions/0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md) — why a plugin is data, and why its container is written rather than supplied
- [plugin-manifest contract](../../../20-architecture/contracts/plugin-manifest.md) — the fields a plugin declares in, and the entry lemonfiber writes from them
- [F1 Customisation & escape hatches](f1-customisation.md) — the escape-hatch posture this narrows to declarative data
- [F2 Service catalogue](f2-service-catalogue.md) — the bundled catalogue whose entries a plugin extends
- [F4 The capability vocabulary](f4-capabilities.md) — the vocabulary a manifest claims and asks in
- [F5 The plugin catalogue](f5-plugin-catalogue.md) — where a manifest comes from and what vouches for it
- [F6 Plugin lifecycle](f6-plugin-lifecycle.md) — what rehearsing, installing and removing one does
- [F7 Plugin provenance](f7-plugin-provenance.md) — how what a plugin changed stays answerable
- [F9 Capabilities of the bundled services](f9-bundled-capabilities.md) — where standing in for something bundled lives, which a contribution here may not do
- [F11 Executing contributed code](f11-executing-contributed-code.md) — the question `F3-R6` closes, opened on its own rather than riding along with this
- [C1 Diagnostics](../c-trust/c1-diagnostics.md) — the engine a contributed check is a row in
- [C3 Auto-remediation](../c-trust/c3-auto-remediation.md) — the guided half a contributed remedy joins, and the automatic half it may not
