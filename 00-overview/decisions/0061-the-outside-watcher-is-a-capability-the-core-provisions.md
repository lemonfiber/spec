# ADR-0061: The outside watcher is a capability the core provisions and reads

**Status:** Accepted
**Date:** 2026-11-08
**Decided:** 2026-11-08, by the maintainer, Wessel Verheij: the outside watcher is
`status.watch@1`, provisioned by the core under its own tags and read at
`GET /api/watcher`.

## Context

K2 asks for a second opinion on whether the stack is up: an open-source, self-hosted
monitor that watches every critical service and every entry point the household uses,
watches scheduled work by heartbeat, and is independent of lemonfiber's own health path
(`K2-R1`, `K2-R2`). The companion's N16 page draws what that monitor sees beside what the
stack says of itself (`N16-R1` to `N16-R4`).

`plugin-uptime-kuma` puts Uptime Kuma in the stack. Its one contribution is a `doctor`
check of its own health. No core capability names a watcher, nothing provisions a
monitor, and nothing reads one, so no surface can say which of the stack's services a
monitor covers, whether it is actively checking, or that the monitor itself cannot be
reached.

A monitor could be paired with what it covers by its name or its target. Both are a
guess: an operator renames a monitor, two services share a host, and an entry point is
watched at an address that is not the household's. Pairing by a guess is the comfortable
falsehood `K2-R8` forbids in another form.

## Decision

### 1. `status.watch` is a core capability

`status.watch@1` is the outside watcher's contract. A plugin fills it with an adapter in
front of its monitor, as every part fills a capability
([ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md)). The core asks
it four operations:

| Operation | Answers or does |
|---|---|
| `reachable` | Whether the monitor itself answers, and why not where it does not |
| `monitors` | Every monitor it holds: its id, the tag lemonfiber gave it where it made it, its name, its kind (`http`, `keyword`, `port`, `ping`, `dns`, `docker` or `heartbeat`), its target, whether it is active or paused, a heartbeat's expected interval and grace, its state (`up`, `down`, `pending` or `paused`) and since when, and its last reading |
| `provision` | Makes or updates the one monitor holding a tag, of a kind, at a target, at an interval, a heartbeat's grace and a count of failed checks before it alarms; answers its id and what it watches where it could not watch what it was asked to |
| `retire` | Removes the monitor holding a tag; nothing where none holds it |

A tag is lemonfiber's own: `lemonfiber:service:<id>`, `lemonfiber:entry:<id>` or
`lemonfiber:job:<id>`. `provision` is idempotent by it: provisioning a tag twice leaves
one monitor. A monitor the operator made holds no tag and is never provisioned over or
retired.

### 2. The core provisions what it covers

Where a plugin fills `status.watch`, the core provisions a monitor for every critical
service, every household-facing entry point over the path the household uses (the front
door's household address, never an internal one), and every job the stack runs on a
schedule as a heartbeat. It retires every tagged monitor whose service, entry point or
job is gone. Each monitor alarms only after the failed checks the contract names
(`K2-R9`). Provisioning runs at every act that writes the project and leaves the stack
running, and on its own, without a terminal (`K2-R14`).

The core keeps the id `provision` answered for each tag. That record is how a monitor is
paired with what it covers. Nothing is paired by its name or its target.

### 3. The core reads it as `lemonfiber watcher`

`lemonfiber watcher --json`, served at `GET /api/watcher`, answers which plugin fills
`status.watch`, whether the monitor answers, when the core asked, and each monitor with
what it covers where the core made it. Two of its states are the core's own:

- `expected-down`, where what it covers is stopped on purpose (`K2-R10`), from the
  lifecycle's record of a deliberate stop;
- `not-reporting`, where it holds no reading newer than its interval and grace.

A monitor the core could not make watch what it should is answered with what it was
asked to watch, what it watches instead, and why (`K2-R7`, `K2-R12`). Every critical
service and entry point with no active monitor is listed as uncovered (`K2-R3`, `K2-R5`).
A monitor that cannot be reached is answered as blind, never as all clear (`K2-R8`).

## Consequences

### Positive

- A monitor is paired with what it covers by a record the core made, so the companion
  never shows a service as watched on the strength of a name.
- The operator's own monitors stand beside lemonfiber's, untouched.
- Any monitor with a supported configuration surface can fill the capability; Uptime
  Kuma is the first.

### Negative

- The core writes to the monitor. A monitor whose adapter cannot provision answers
  `unsupported`, and every service it would cover is listed uncovered until it can.
- Seven K2 rows move from 0.23.0 to 0.19.0, which brings the adapter for Uptime Kuma
  forward with them.

### Neutral

- The detection proof (`K2-R6`) and alert routing (`K2-R11`, `K2-R13`) stay in 0.23.0.

## Alternatives considered

- **Read-only now, `covers` absent until provisioning.** Rejected: every service would
  read as uncovered, and the page would mostly say "unknown".
- **Pair by name or target.** Rejected: a rename or a shared host pairs the wrong
  monitor, which is reporting coverage that is not there.
- **Leave the watcher to 0.23.0.** Rejected by the maintainer: N16's order puts it second.

## Related

- [K2 Uptime monitoring](../../10-functional/features/k-observability/k2-uptime.md)
- [N16 What happened while nobody was looking](../../10-functional/features/n-companion/n16-nobody-was-looking.md)
- [Capability contracts](../../20-architecture/contracts/capability-contracts.md)
- [ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md)
