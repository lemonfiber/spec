# ADR-0022: A recipe declares pairs, not lists

**Status:** Proposed
**Date:** 2026-09-11

## Context

[ADR-0021](0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md) bounded
what a plugin's *container* may reach. This is the other half: what a plugin's
**recipes** may reach, and what they may carry there.

A recipe is an ordered sequence of calls that captures values out of responses,
substitutes them into later calls, branches on what came back, and waits when a
service is not ready
([F3-R15](../../10-functional/features/f-extensibility/f3-stack-manifests.md)).
It is Turing-incomplete by construction, and F3 presents that as the property
that makes *"what can this plugin do?"* answerable by reading it.

It is a real property and it is the wrong one to rely on alone. **Turing
completeness bounds computation; it says nothing about authority.** The recipe
engine runs with lemonfiber's own: the credential store, every service in the
stack on its loopback port, and the open internet. A sequence of twelve calls
with no loop in it can do a great deal of damage without ever computing
anything.

Two specific things follow, and neither is currently refused.

**The declarations do not compose.** `F3-R17` requires every secret a plugin
will hold to be declared. `F5-R8` requires every host its recipes reach to be
declared. Both are satisfied by two flat lists — and a manifest that legally
declares *"I capture the media server's API key"* and *"I reach `plex.tv`"* may
legally send the first to the second. Nothing in F3, F5 or F7 constrains the
**pairs**. Each half was declared; the combination, which is the whole of the
harm, was not.

This is not a hypothetical that a careful author avoids. It is the motivating
example F3 itself names: substituting Plex for Jellyfin means claiming a server
against `plex.tv`, which *is* a flow from a locally-captured credential to an
external host. The design needs the path. It cannot simply forbid it, and a rule
that forbade it would ship a feature unable to do the thing it was built for.

**A declared host says nothing about where it is.** `F5-R8` is satisfied by
declaring `192.168.1.1`. The stack sits inside a home network alongside a router
administration page, a NAS, a printer and whatever else the household owns, none
of which is reachable from outside and all of which is reachable from here. A
recipe engine that will send a declared request to a declared address, on behalf
of a manifest from a stranger, is a request forger positioned inside the
perimeter. The declaration makes it visible in a file nobody reads line by line;
it does not make it refused.

Against that, the promise this product currently makes. What leaves the machine
is a closed list of four destinations, each with a documented purpose (`G8-R3`),
each individually switchable off with the cost of doing so stated (`G8-R5`), and
no telemetry at all. `F5-R9` extends the *account* to a plugin's hosts. It does
not address what those hosts may be sent, or whether any of it can be refused.

## Decision

**A recipe's reach is declared as pairs, checked before it runs, and confined to
names.**

1. **Every capture is labelled by origin** — a service in this stack, the
   credential store, the operator, or the response of an external host.

2. **Every destination is classified** — a service in this stack, or an external
   host. There is no third kind.

3. **A manifest declares the pairs, not two lists.** For every value that may
   travel to a destination, the manifest names *that value going to that
   destination*. A flow with no declared pair behind it is a validation failure.

4. **The check is static, and it is what the sequence shape is for.** Because a
   recipe is finite and its branches are bounded, the set of value-to-destination
   flows it can produce is computable without running any of it. F3 offered
   Turing-incompleteness as an auditability property; this makes it a security
   property, and that is the stronger reason to keep it.

5. **A pair that carries anything out of the machine is approved by the operator
   at rehearsal**, named as itself — *this value, to that host* — before anything
   is written. Declaring it is what makes it possible; the operator agreeing to
   it is what makes it happen.

6. **A recipe names, and never addresses.** An in-stack destination is named by
   its service id and resolved by lemonfiber to the address it already knows. An
   external destination is named by DNS name. A manifest containing an IP
   literal, a CIDR range or a bare host port is refused.

7. **An external name that resolves inside the perimeter is refused at the call.**
   Names-only closes the manifest; it does not close DNS, which can answer with a
   private, loopback or link-local address. The manifest said this destination was
   external; an internal answer contradicts the declaration, and the mismatch is
   the refusal. It is checked per call rather than once, because the answer can
   change between them.

Taken together, the destinations a recipe can reach are exactly **the services in
this stack, plus the external names it declared**. There is no expressible way to
reach anything else on the network the stack happens to sit in.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Two flat lists — hosts, and secrets** | What F3 and F5 say today. Declares both halves of the harm and refuses neither, because the harm is the combination. It also reads as complete, which is worse than reading as partial: an operator comparing the manifest against the account of what leaves the machine would find them consistent. |
| **Forbid a locally-captured value from ever leaving** | Clean, checkable, and it deletes the feature's motivating example — Plex claiming a server against `plex.tv` is exactly this flow. Shipping a substitution mechanism that cannot perform the substitution everybody asked for is not a security win, it is an unused feature with a good property. |
| **Allow it, and rely on review** | The catalogue's reviewer is one person (`F5-R2`), and `F5-R4` deliberately keeps a route with no reviewer at all. A control that exists only on the reviewed path is absent from the path most operators will use the first afternoon. |
| **Check the flows at run time instead of at validation** | A refusal after two calls have already landed leaves a half-configured stack and tells the operator something they could have been told before anything happened. `F6-R1` already requires a rehearsal that states every change before one is written; a flow check that cannot participate in it is in the wrong place. |
| **Permit IP literals against an allow-list** | An allow-list extended on the strength of an untrusted manifest is a deny-list wearing a hat, and this one would be extended with the address of somebody's NAS by the first plugin that wanted it. |
| **Proxy every recipe call through an egress filter** | A second network stack to build, keep correct and cover, and it answers *which host* without answering *carrying what* — so the confused-deputy problem survives it intact. |
| **Declare pairs, but approve them once at install rather than per pair** | A single yes to an install is not consent to a specific disclosure; it is consent to the install. The pairs are the one part of a manifest an operator can meaningfully judge, and collapsing them into one prompt wastes the only moment they are legible. |

## Consequences

**The sequence shape becomes load-bearing rather than merely tidy.** If a recipe
ever gains unbounded iteration, a computed destination or a call built from a
response, the flow set stops being decidable and this check stops working. That
is now a reason `F3-R15` cannot be relaxed later for convenience, and the reason
should be recorded where somebody proposing it will see it.

**Manifests get more verbose, on purpose.** A plugin capturing three values and
reaching two hosts has six possible pairs and will want very few of them. The
ones it does not declare are the ones a reader no longer has to wonder about,
and the verbosity is the readable form of the blast radius `F7-R6` asks to be
stated before installing.

**The rehearsal gains the most important thing in it.** *This plugin will send
your media server's API key to `plex.tv`* is a sentence an operator can judge
without knowing what a recipe is. Everything else a rehearsal says is a change
to their own machine; this is the only part about something leaving it.

**The account of what leaves this machine needs a third category.** It currently
holds lemonfiber's own requests, each with a switch and a stated cost, and the
stack services' requests, which are theirs. A recipe's call is neither: it is a
request lemonfiber makes on a plugin's behalf. Fitting it into `G8-R3` and
`G8-R5` — enumerable, and individually refusable with the consequence stated —
is a separate piece of work that this decision makes unavoidable.

**Some plugins cannot be written honestly, and will be written dishonestly
elsewhere.** A plugin whose business model needs the operator's library contents
cannot declare that pair and expect approval. It can still be published outside
the catalogue, and an operator can still install it from a named source
(`F5-R4`) — having been shown the pair and agreed to it. That is the correct
division: lemonfiber's job is to make the disclosure unavoidable, not to make
the choice.

**Revisit if** a legitimate flow genuinely needs a destination that is not known
until run time — at which point the honest answer is a new declaration form that
is still statically bounded, not an exception that makes the check advisory.

## Related

- [ADR-0021](0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md) — the other half: what a plugin's container may reach
- [F3](../../10-functional/features/f-extensibility/f3-stack-manifests.md) — recipes, their shape, and the declarations this composes
- [F5](../../10-functional/features/f-extensibility/f5-plugin-catalogue.md) — declared hosts, and the reviewed and unreviewed routes
- [F6](../../10-functional/features/f-extensibility/f6-plugin-lifecycle.md) — the rehearsal the approval happens in
- [G8](../../10-functional/features/g-ux/g8-privacy.md) — the account of what leaves this machine, and the switches this will need
- [system-context](../../20-architecture/system-context.md) — the trust zones a recipe must not be able to cross
