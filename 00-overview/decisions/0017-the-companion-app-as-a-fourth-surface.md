# ADR-0017: The companion app is a fourth surface, reached over the network

**Status:** Proposed
**Date:** 2026-09-11

## Context

[G1](../../10-functional/features/g-ux/g1-interface-tiers.md) fixed three
surfaces — CLI, TUI and web — and two guarantees that decide most of a fourth
one's shape before anyone argues about frameworks. **No surface may implement
behaviour independently** (`G1-R2`) and **every action must be available from
every surface** (`G1-R1`). A surface is a rendering, never a capability.

All three of those surfaces run **on the machine the stack runs on**. The CLI and
TUI are the same process as the core. The web UI is a separate program
([ADR-0011](0011-web-surface-as-a-fifth-repo.md)) that talks to the core over
loopback, and [C6](../../10-functional/features/c-trust/c6-web-security.md) binds
it to `127.0.0.1` by default.

A phone is a fourth place somebody would operate from, and it is the first one
that is not on that machine. That single fact is what this decision is about.
Everything else — which framework, which language — follows from it or is
already settled by
[ADR-0013](0013-an-sdk-owns-the-api-client.md) and
[ADR-0014](0014-one-generated-contract-for-every-sdk.md).

Three things are true at once and have to be reconciled rather than chosen
between:

1. **The admin surface is loopback by default, and widening it is refused
   without authentication** (`C6-R1`, `C6-R6`). That is not an obstacle to work
   around; it is the policy, and a companion app that argued with it would be
   arguing for the failure C6 exists to prevent.
2. **Remote access does not exist yet.**
   [I1](../../10-functional/features/i-remote-access/i1-remote-access.md) is
   scheduled for `0.20.0` and is built on a self-hosted overlay. Waiting for it
   would leave the LAN case — which already works — unserved for five minors.
3. **Parity is a requirement, not an aspiration** (`G1-R1`). A fourth surface
   that quietly did less would re-introduce exactly the drift G1 forbids.

## Decision

**A sixth repo, `lemonfiber-companion`: a native mobile application that is a
fourth surface under G1, speaking the same web API contract every other client
speaks.**

| Piece | Where | Why there |
|-------|-------|-----------|
| The API | `lemonfiber` | Already the core's own answer, already versioned |
| The app | `lemonfiber-companion` | Its own CI, its own store releases, its own cadence |
| The client | `lemonfiber/sdk-php` | ADR-0013 — an SDK owns the API client, and a second one here would be a second source of truth |
| The boundary | `Envelope { api_version, kind, data }` | The same contract the SPA and both SDKs are held to |

### It is a surface, so parity binds it

`G1-R1` and `G1-R2` apply. The companion renders the core's answers; it does not
decide anything the core does not already decide. An action reachable from
`lemonfiber` on a terminal is reachable from the app.

### Parity is about what it offers, not about whether it is connected

This is the part that a device boundary changes, and it is written down because
it would otherwise be settled by omission.

On the host, a surface can always reach the core — the core is the same process,
or one loopback hop away. On a phone it cannot: reaching the stack at all
requires the operator to have opted into a LAN binding with authentication
configured, which is their decision and not the app's.

So the rule the companion is held to is that **every action is offered, and an
unreachable stack is rendered honestly as a state rather than hidden as a missing
feature**. "Cannot reach your stack" is a screen, with what to check. It is not a
button that is absent on Tuesdays.

### First-run setup is the one action that cannot cross the boundary

`G1-R14` requires setup to be completable from every surface. It cannot be
completed from a phone against a machine that has not been set up, and the reason
is not effort: the thing that lets a phone reach the machine — a bound, authenticated
admin surface — is **created during setup**. A phone cannot perform the act that
makes the phone able to perform acts.

So the companion offers *re*configuration
([A4](../../10-functional/features/a-getting-started/a4-reconfiguration.md)) in
full, and first-run setup not at all, and says which it is. This is recorded as
an exception to `G1-R14` with its reason rather than left as a gap somebody finds
later and reads as an oversight.

### The transport is LAN first and the session outlives it

The app exchanges a password **once** at `/api/session` for a session, and
carries it in `X-Lemonfiber-Token` thereafter — the mechanism the API already has
for exactly this caller, described in its own source as being for "somebody
holding a phone".

What changes when I1 lands is the route the bytes take, not the credential, not
the contract, and not a line of the app. That is the reason for choosing this
transport now rather than waiting: it is not a stopgap to be replaced, it is the
same conversation over a different path.

### It is native, not a web view

The app is built with **NativePHP SuperNative**: Blade compiled to a binary
representation that SwiftUI and Jetpack Compose render directly, with no web
view, no DOM and no JavaScript bridge.

The reason is not performance. It is that a web view inside a native shell is a
fourth rendering of the web surface, and this project already has one of those.
A surface whose components are the platform's own gets the platform's
accessibility tree, its text scaling and its dark mode for free —
[G3](../../10-functional/features/g-ux/g3-accessibility.md) asks for all three,
and a web view would mean meeting them twice, differently.

Where a screen genuinely needs HTML, the web view remains available as an
explicit component rather than as the default everything sits inside.

### Both audiences, decided by who signs in

lemonfiber already distinguishes an operator from a household member
([D6](../../10-functional/features/d-content/d6-household-identity.md)). The app
carries both: the credential that signs in decides which application the person
gets. A household member browses and requests; they are never shown a control
they are not entitled to, and the entitlement is decided by the core rather than
by hiding buttons.

## Consequences

**G1 gains a fourth tier**, and its table is no longer "three surfaces, one
core". The parity requirement it already carries now reaches further than the
machine, which is a larger promise than it was written to make — hence the two
qualifications above, both stated as requirements rather than as prose.

**A second reason to keep the contract honest.** A missing field in
`web-api.contract.json` already breaks two SDKs and the SPA. It now also breaks
an application in two app stores, where a fix takes review time rather than a
deploy.

**Store distribution is a new kind of release.** Builds and signing run through
NativePHP's Bifrost cloud rather than on a machine holding distribution
certificates. That is a supply-chain surface this project did not have, and
`L1`'s attestation standard has to reach it.

**The LAN case is honest HTTP.** C6 is deliberate that plain HTTP on a trusted
local network beats training operators to click through certificate warnings. A
phone on the same LAN inherits that, and the app says so rather than implying a
protection it does not provide.

## Alternatives considered

**Wait for I1.** One connection story, no migration. Rejected because the LAN
case works today and the session mechanism is already built for this caller;
waiting would have served nobody for five minors to avoid a change that this
decision shows is not needed.

**A web view wrapping `lemonfiber-web`.** Fastest to something installable, and
it is the shape this project is most likely to be asked why it did not take. It
is a fourth rendering of a surface that already exists, it meets G3 twice, and
every native affordance — biometrics, the camera, notifications — becomes a
bridge call rather than a component.

**A second API client written in the app.** Rejected by ADR-0013 before it was
asked here. `sdk-php` is the client.

**Two apps, operator and household.** Two store listings, two review queues, and
a household member who is also the operator installing twice. The core already
knows the difference between them; the app can ask.
