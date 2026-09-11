# ADR-0019: A screen paints before it reaches the stack

**Status:** Proposed
**Date:** 2026-09-11

## Context

The companion app's runtime is a persistent PHP process. It boots the framework
once and then handles each interaction as a dispatch through the kernel — closer
to Octane than to a game loop. There is one thread, and it handles one dispatch
at a time.

That single fact collides with the premise
[ADR-0017](0017-the-companion-app-as-a-fourth-surface.md) established.
Reachability is a *reported condition*, not a missing capability, and `N1-R3`
forbids hiding an action because a stack cannot be reached. Which means
unreachable is not the exceptional path — it is an ordinary Tuesday. The stack
is asleep, the phone is on mobile data, the machine is mid-update, someone is
on a train.

So the most common condition the app must handle gracefully is also the one
that occupies its only thread for the length of a network timeout. While it is
occupied, nothing else is processed: taps queue, and the app appears to have
stopped. A design that discovers this on a device is a design that was tested
against a stack on the same desk.

Three capabilities decide what is possible, and all three already exist in the
runtime rather than needing to be built:

1. A screen can publish a frame **before** its setup runs. The router publishes
   a placeholder tree immediately and then performs the slow work, so the first
   paint does not wait on the network.
2. A screen can be woken on an interval, with or without a callback, and more
   than one cadence can run on the same screen.
3. There is no queue worker on the device and no asynchronous HTTP. Work cannot
   be moved off the thread; it can only be *sequenced* around the paint.

## Decision

**A screen paints what it already knows, then reaches the stack.** Never the
other way round.

1. Every screen that reads from a stack publishes its first frame from the
   retained reading, carrying when it was read (`N1-R9`). The reading's age is
   part of the frame, not a detail added later.
2. The read happens after that first paint, in the screen's setup.
3. Where a screen's content changes on its own — a repair running, a verdict
   that may move — it declares a refresh cadence rather than relying on the
   operator to leave and return.
4. Every call the app makes carries a **bounded** timeout, short enough that a
   queued tap is a hesitation rather than a hang. The bound is a property of the
   app, not of the stack: a stack that is slow is indistinguishable from one
   that is asleep, and both must yield the screen back.
5. A spinner is what the app shows when it has **nothing** to show — a stack
   paired moments ago and never yet read. It is not the default state of a
   screen that has been open before.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Read first, then paint** | The straightforward shape, and the reason mobile apps show a blank screen with a spinner for four seconds. It spends the app's only thread before the operator has seen anything, and it spends it on exactly the path that is slowest. |
| **A spinner as the first frame** | Honest but wasteful. The app usually knows the previous verdict, and a spinner discards that to show less. It also trains the operator to wait, which is the habit this decision is trying not to create. |
| **Move the call off the thread** | There is no worker process and no asynchronous HTTP on the device. This is not a trade-off that was weighed and rejected; the mechanism does not exist. |
| **Long timeouts so slow stacks still succeed** | Optimises for the stack at the cost of the operator. A stack that needs thirty seconds is one the app should report on, not wait for. |
| **Cache the reading and never show its age** | Faster to build and dishonest in the one way that matters here: a stale verdict presented as live is how somebody concludes their stack is healthy while it is not. `N1-R9` already forbids it; this decision is what makes obeying it cheap. |

## Consequences

**The fourth screen state earns its place.** A screen is loading, ready,
refused, or **stale** — and stale is not a degraded version of ready, it is the
normal state of a screen that has been open for a minute. Designing for it
first means the app has something truthful to show in every condition.

**Retention becomes a correctness concern, not an optimisation.** What the app
retains between launches decides what it can paint, so the storage decision and
this one are the same decision seen from two sides. Secrets are still never
retained (`N1-R23`).

**A timeout is a product decision.** Bounding it is what keeps the app
responsive, so the bound belongs in the spec rather than in whichever adapter
was written last.

**The first pairing is the honest exception.** There is nothing retained to
paint, so that screen does wait — and it is the one moment the operator has just
typed an address and expects to.

## Related

- [ADR-0017](0017-the-companion-app-as-a-fourth-surface.md) — reachability as a
  reported condition
- [ADR-0018](0018-trusting-a-stack-over-the-local-network.md) — which machine
  the app is willing to talk to
- [N1](../../10-functional/features/n-companion/n1-companion-app.md) — connecting,
  the session, and what a reading carries
- [G4](../../10-functional/features/g-ux/g4-error-model.md) — how a refusal is worded
