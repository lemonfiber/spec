# ADR-0026: A screen may hold the stream, and holding it is its one read

**Status:** Proposed
**Date:** 2026-09-25

## Context

The health summary is the product's most repeated statement, and `G7-R8`
requires it to be identical on every surface, from one computation. The core
computes it once, into the dashboard snapshot, and publishes that snapshot in
one place: the event stream, `GET /api/events`
([web API](../../20-architecture/contracts/web-api.md)). No endpoint that answers
and closes carries it. So the companion either reads the stream or computes a
summary of its own from a report, and the second is the divergence `G7-R8`
forbids.

The companion's rules were written for requests that answer and close, and a
held stream collides with four of them as they stand:

- `N1-R26` bounds every call with a timeout short enough to hand the screen
  back. A stream that is working never finishes, so any bound on the whole of it
  ends a healthy subscription.
- `N1-R65` allows one read per published frame. A stream delivers a new value
  every time the core gathers, and each one is a new frame.
- `N1-R66` allows a screen to reach a stack only on a stated cadence or an act of
  the operator's. Values arriving on the stream are neither.
- `N1-R25` and [ADR-0019](0019-a-screen-paints-before-it-reaches-the-stack.md)
  require the first frame before the read, on a runtime with one thread and no
  asynchronous HTTP.

Each rule exists to protect something a stream does not threaten when it is held
correctly, which is what makes this a decision rather than an exception:

- The timeout protects the operator's screen from a stack that does not answer.
  Opening a stream is a call and can be bounded like any other. Once it is open,
  what can hang is reading from it, and that is bounded by reading only what has
  already arrived.
- The one-read rule protects the stack from a screen that asks per value it
  renders. A subscription is asked for once. What arrives on it was sent by the
  core on the core's own cadence, to every listener at once, from the gather
  that already runs (`G1-R12`). A phone holding the stream costs the stack one
  connection and nothing per value.
- The cadence rule protects the stack from a screen that reaches it unprompted.
  Taking what has already arrived on an open connection does not reach the
  stack: no request goes out.

What a stream can do that a request cannot is go quiet without failing. The
contract answers that already: the server sends a heartbeat at least every 15
seconds, and a client treats twice that in silence as a broken stream
(`ARCH-R61`). A screen that shows a held value after that point is showing a
reading it can no longer vouch for.

A stream can also outlive the operator's attention. A phone in a pocket holding
a connection open wakes its radio on every beat, all night, for a screen nobody
is looking at.

## Decision

**A screen may hold a subscription to the event stream in place of a read, and
holding it is that screen's one read.**

1. **It paints first.** The first frame is built from what the app holds, before
   the subscription is opened (`N1-R25`), and says the reading is not live yet.
2. **Opening is a call and is bounded.** The connect carries the same bounded
   timeout as every other call (`N1-R26`). A connect that does not complete
   within it is a refused reach, reported the way `N1-R10` reports one.
3. **Reading what arrived does not wait on the stack.** On its stated cadence
   the screen takes what the subscription has already delivered and renders it.
   It does not block for a value that has not arrived. The wait for the next
   value is the stream's, and it is spent between frames rather than inside one.
4. **Silence has a bound, and the bound is the contract's.** A subscription that
   has delivered nothing, neither a value nor a heartbeat, for twice the
   heartbeat interval (`ARCH-R61`) is broken. What it last delivered is shown as
   stale with when it was read (`N1-R9`), and a summary is never shown as
   healthy on the strength of one.
5. **A broken subscription is reopened on a stated cadence**, not in a loop. The
   first value after reopening replaces what was held. Nothing held from before
   the break is presented as current.
6. **It is held only while it is watched.** A subscription is open only while a
   screen showing what it carries is in front of the operator. Leaving that
   screen closes it, and the app leaving the foreground closes it at the
   screen's next wake. Nothing is opened or read in the background.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Compute the summary in the app from the doctor report** | A report's overall verdict has four words where the summary has eight, it cannot know that a stack was stopped on purpose or that only optional services failed, and it is a second computation of the one statement `G7-R8` requires to come from one. |
| **A request/response endpoint for the summary** | The contract's position is that the stream is fed by the gather that already serves the dashboard, and that two gathers are two chances to disagree. A second route for one field of that snapshot is a change to the core for the benefit of one client, and still leaves the other half of the snapshot unreachable. |
| **Open the stream per frame, read one value, close** | It meets every rule by the letter and is the worst for the stack: a connection, an admission and a gather nudge for every value shown, with the heartbeat, the resumption id and the backlog all thrown away. It is polling with a longer request. |
| **Hold the stream on a background thread** | The runtime's background lane runs a task to completion and hands back one result. A subscription never completes. Carrying its values across would need a side channel the framework does not offer, and a task on that lane cannot be stopped once started, so the connection could not be closed when the operator stops looking. |
| **Hold the stream in native code and forward events** | It is a second HTTP client, which `N1-R16` refuses, and it would have to enforce the certificate pin (`N1-R19`) a second time, in two languages. |
| **Keep the stream open in the background for faster return** | Buys a second or two on return at the cost of the battery and the radio for as long as the phone is in a pocket. iOS suspends a backgrounded app's sockets regardless, so on that platform it would not even deliver what it costs. |

## Consequences

### Positive

- The companion says what the terminal and the browser say, from the same
  computation, including `stopped`, `advisory` and `unknown`, which it could not
  derive.
- A value arrives when the core has it, and the stack answers one connection
  instead of one request per refresh.
- The stale state `ADR-0019` introduced gets a mechanical trigger: silence past
  the contract's bound.

### Negative

- A screen holding a subscription wakes on a cadence even when nothing arrives,
  to take what has arrived and to notice silence. The cadence must be stated,
  and it costs a render per wake.
- On the first open after a return to the foreground there is a moment with
  nothing live to show. The retained value, marked with its age, fills it.

### Neutral

- `N1-R65` and `N1-R66` are unchanged for everything that reads. This adds a
  second way to satisfy them, and says what that way owes.

## Revisit if

- The runtime gains a background lane that can deliver more than one result and
  be stopped from the screen that started it.
- The contract carries the health summary on an endpoint that answers and
  closes, from the same gather.
- The platforms begin delivering background socket traffic to a suspended app,
  so that holding a connection while backgrounded would cost less than
  reopening it.

## Related

- [ADR-0019](0019-a-screen-paints-before-it-reaches-the-stack.md): the first
  frame before the read, on one thread
- [ADR-0017](0017-the-companion-app-as-a-fourth-surface.md): reachability as a
  reported condition
- [N1](../../10-functional/features/n-companion/n1-companion-app.md): holding a
  subscription
- [G7](../../10-functional/features/g-ux/g7-health-summary.md): one summary,
  from one computation
- [Web API](../../20-architecture/contracts/web-api.md): the stream, its
  heartbeat and resumption
