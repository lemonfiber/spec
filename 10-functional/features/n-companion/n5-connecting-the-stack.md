---
id: N5
title: What connects to what
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P2
labels: [mobile, extensibility, ux]
requires: [N1, F4, F5]
relates: [F2, F6, F7, F9, N2]
---

# N5 — What connects to what

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

The stack decides what each service *can* do. The operator decides what actually
answers what. That second decision has never had a surface here.

It is not a decision the core is willing to make on the operator's behalf, and
it says so: a capability more than one installed service claims is
[`contested`](../f-extensibility/f4-capabilities.md) — *refused pending the
operator's choice* — and standing in for a bundled service
MUST remain an operator's recorded choice rather than a manifest's assertion
(`F4-R17`). The core computes the question, the contract carries it down to
`whose: 'operator'` with the claimants and the reason, and there has been
nowhere to answer it.

So this is not a new capability. It is the missing half of one the product
already has, and `N1-R2` already required: every action available from another
surface is offered here.

This feature owns **what answers what, and what is installed**. What is wrong
and what would fix it is [N2](n2-operator-companion.md); connecting to the stack
at all is [N1](n1-companion-app.md).

## Behaviour

### A contested capability is a question, asked here

More than one service claiming one capability is not a fault and is not
resolved by install order. It is a question with named claimants, and the app
asks it: which of these answers when something asks for this.

The question carries what the choice costs. Choosing is not picking a name off a
list — the service that loses stops being what the stack reaches for, and the
operator is owed that before they answer rather than after.

### A choice is the operator's, and it is recorded as theirs

The contract distinguishes a choice the stack made from one the operator made.
The app never makes the first look like the second, and never presents its own
default as either. Where the stack settled something outright there is nothing
to ask; where it did not, the app asks and records the answer as the operator's,
with their reason if they gave one.

### What a substitution leaves unfilled is said before it is agreed to

Putting one service in place of another for a capability can leave a third thing
asking for something nothing now answers. The contract carries that as
`leaves_unfilled`, and it is the part worth reading — a substitution that
silently breaks a service the operator was not thinking about is the failure
this surface exists to prevent.

It is stated before the change, not reported after it.

### Unfilled is a state, not an error

A service asking for a capability nothing fills is a fact about the stack, and
the app shows it as one: what is asking, and what would answer it. It is not a
fault to be repaired and it is not hidden because nothing is broken.

### A by-name wiring says that it is one

An operator may wire a service to another by name rather than by capability, and
a plugin may not (`F4-R12`). Where a wiring is by-name the app says so and
carries the reason it was made, because a by-name link is the exception the
operator chose and reads otherwise as the stack's own arrangement.

### The catalogue says what the household loses

What the stack could run and does not is not a list of software. Each entry
carries what it is for and what the household is without it, and the app leads
with that rather than with the name of the project.

A service that was removed names what replaced it, so an operator looking for
something they remember is answered rather than told it does not exist.

### A plugin is installed with what vouches for it, or not at all

What is installed, and what is being installed now, is the whole of what this
screen is for. An install is a decision, and it carries its provenance
([F7](../f-extensibility/f7-plugin-provenance.md)) at the moment it is made
rather than somewhere a curious operator could go and look.

### Nothing here decides what the core has not decided

The app holds no second copy of the capability vocabulary, no rule about which
service ought to win, and no opinion about what a good stack looks like. Every
name, state and consequence on this surface is the core's answer rendered
(`N1-R1`).

## States

| State | Meaning |
|-------|---------|
| Settled | Every capability something asks for is answered, and nothing is waiting on the operator. |
| Contested | One or more capabilities have more than one claimant and are refused until the operator chooses. |
| Unfilled | Something asks for a capability nothing installed answers. Shown, not repaired. |
| Installing | A plugin install is in progress; the screen does not claim it is installed until the core says so. |
| Unknown | The wiring could not be read. Never rendered as settled. |

## Edge cases

- **A capability contested between a bundled service and a plugin.** The bundled
  one is not the default, and the app does not present it as one. `F4-R17` makes
  standing in for a bundled service the operator's recorded choice, which is the
  same choice as any other and is asked the same way.
- **A choice that is no longer possible.** A claimant the operator chose is later
  uninstalled. The capability returns to contested or unfilled, and the app says
  the earlier choice is gone rather than silently re-deciding.
- **A substitution that would leave nothing unfilled and still breaks something.**
  The app states what the contract carries and does not guess beyond it
  (`N2-R14`); what it cannot say, it does not.
- **An install refused by provenance.** The refusal is the answer and is shown
  with its reason, rather than the plugin being absent from the catalogue.

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N5-R1** | A contested capability MUST be presented as a choice naming every claimant, and the app MUST NOT settle it — by default, by install order, or by any ordering of its own. |
| **N5-R2** | Before the choice is made, the app MUST state what the stack reaches for now and what it would reach for after. |
| **N5-R3** | A choice MUST be recorded as the operator's, and a settlement the stack made MUST NOT be presented as one the operator made. |
| **N5-R4** | A substitution MUST state what it would leave unfilled before it is agreed to, naming each service and the capability it would lose. |
| **N5-R5** | A capability nothing fills MUST be shown as a state with what is asking for it, and MUST NOT be presented as a fault or omitted because nothing is broken. |
| **N5-R6** | A by-name wiring MUST be shown as by-name and MUST carry the reason it was made. |
| **N5-R7** | The app MUST NOT offer to create a wiring a plugin is forbidden to create (`F4-R12`). |
| **N5-R8** | A catalogue entry MUST carry what the household is without it, and MUST NOT be presented as a name and a description alone. |
| **N5-R9** | A service removed from the catalogue MUST name what replaced it where the contract carries one. |
| **N5-R10** | A plugin install MUST carry its provenance at the moment it is offered, and an install the core refuses MUST be shown with the refusal rather than omitted. |
| **N5-R11** | An install in progress MUST NOT be rendered as installed until the core reports it. |
| **N5-R12** | The app MUST hold no copy of the capability vocabulary, and MUST render the names, states and consequences the core answers with. |
| **N5-R13** | Where the wiring cannot be read, the app MUST say so and MUST NOT render the stack as settled. |

## Related

- [N1](n1-companion-app.md) — connecting, parity, and what the app may claim
- [N2](n2-operator-companion.md) — what is wrong and what would fix it
- [F4](../f-extensibility/f4-capabilities.md) — the capability vocabulary and what `contested` means
- [F5](../f-extensibility/f5-plugin-catalogue.md) — the catalogue and what vouches for a plugin
- [F6](../f-extensibility/f6-plugin-lifecycle.md) — installing, updating and removing one
- [F7](../f-extensibility/f7-plugin-provenance.md) — what an install carries with it
- [F9](../f-extensibility/f9-bundled-capabilities.md) — what the bundled services already answer
