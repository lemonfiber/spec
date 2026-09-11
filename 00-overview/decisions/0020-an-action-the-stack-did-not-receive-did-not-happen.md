# ADR-0020: An action the stack did not receive did not happen

**Status:** Proposed
**Date:** 2026-09-11

## Context

[ADR-0019](0019-a-screen-paints-before-it-reaches-the-stack.md) settled how the
app *reads* from a stack it may not be able to reach. It said nothing about
writing, and writing is where being unreachable stops being a display problem.

The companion offers real actions: repair a finding, apply an update, take a
snapshot, undo one. `N1-R3` requires those actions to stay offered when a stack
cannot be reached — the app reports the condition rather than hiding the
button. So an operator will press one while the stack is asleep. That is not an
edge case; it follows directly from a requirement.

The obvious kindness is to hold the action and send it when the stack comes
back. It is worth being precise about what that would mean, because it sounds
smaller than it is: a durable queue that survives the app being killed, an
ordering guarantee between held actions, a way to show what is pending and
cancel it, and an answer to the question of what to do when the stack returns
in a different state than the one the operator was looking at when they pressed.

That last one is the problem. A repair is a judgement about a machine at a
moment. Twenty minutes later the finding may be gone, or fixed by something
else, or replaced by a worse one. Replaying the operator's intent against a
machine that has moved on is not the same as doing what they asked, and the
gap between the two is invisible to them.

## Decision

**The app does not hold an action it could not deliver.** An action the stack
did not receive did not happen, and the operator is told so.

1. Where a stack cannot be reached, an action is refused rather than retained,
   and the refusal says which stack and that nothing was changed.
2. The action itself stays offered (`N1-R3`); it is the attempt that failed, not
   the capability that is missing.
3. Idempotency keys (`N1` mutations) remain necessary and are unaffected. They
   exist for the retry *within* one attempt — a mobile network that drops an
   acknowledgement rather than a request — not for replay across a reconnect.
4. Nothing about an attempted-and-refused action is written to storage, so
   there is no pending state to reconcile, display, cancel, or migrate.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Queue and replay on reconnect** | Replays an operator's judgement against a machine that may have changed since they made it, and does so invisibly. It also brings a durable queue, replay ordering, a pending-and-cancel surface, and keys that must survive a restart — a subsystem, to make an uncommon case feel smoother. |
| **Queue only "safe" actions** | Requires a reliable notion of which actions are safe to replay. Whether a repair is still the right repair depends on the stack's state, not on the action's type, so the category cannot be drawn correctly. |
| **Ask at reconnect whether to still apply** | Better than replaying silently, and it asks the operator to re-make a judgement about a moment they can no longer see. In practice people accept the prompt. |
| **Retry briefly before refusing** | Already covered: `N1-R26` bounds the timeout. Extending it past that bound is waiting, dressed as resilience. |

## Consequences

**Nothing pending means nothing to reconcile.** No queue to migrate when the
stored shape changes (`N1-R32`), no pending indicator to design, no cancel path,
and no question about what a held action means after the app is reinstalled.

**The refusal has to be good.** It is now the whole of the experience for this
case, so it names the stack, says plainly that nothing changed, and leaves the
action where it was. `G4` governs the wording.

**An operator away from their network cannot act.** That is the accepted cost,
and it is the honest one for a tool whose actions change a machine. The app
tells them what it cannot do rather than promising something it will do later on
their behalf.

**Revisit if** operators report routinely acting while off the network, or if a
long-running action needs to survive an app restart for its own reasons — at
which point durable state exists anyway and the calculation changes.

## Related

- [ADR-0019](0019-a-screen-paints-before-it-reaches-the-stack.md) — reading
  from a stack that may not answer
- [G4](../../10-functional/features/g-ux/g4-error-model.md) — how a refusal is worded
- [N1](../../10-functional/features/n-companion/n1-companion-app.md) — actions,
  sessions, and reachability
