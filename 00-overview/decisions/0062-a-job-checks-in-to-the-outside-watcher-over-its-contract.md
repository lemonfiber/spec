# ADR-0062: A job checks in to the outside watcher over its contract

**Status:** Accepted
**Date:** 2026-11-08
**Decided:** 2026-11-08, by the maintainer, Wessel Verheij: a job checks in through
`check_in`, a fifth operation of `status.watch@1`; a job is a command the service manager
hosts that acts on a beat; and a critical service is one whose criticality is `critical` or
`core`.

Amends [ADR-0061](0061-the-outside-watcher-is-a-capability-the-core-provisions.md).

## Context

ADR-0061 has the core provision a heartbeat for every job the stack runs on a schedule
(`K2-R4`, `K2-R15`), and declares four operations of `status.watch@1`: `reachable`,
`monitors`, `provision` and `retire`. None of them lets a job check in, so a heartbeat
the core provisions could never be fed, and every one would read as missed. Nothing in
the stack is declared as a job either: the core runs no scheduler and no manifest names
one. And "critical service" is used without a definition, while the manifest grades every
service on its own scale.

## Decision

### 1. A job checks in through `check_in`

`status.watch@1` gains a fifth operation, `check_in`: it records a check-in of the
heartbeat holding a tag, and is refused where no heartbeat holds the tag. The adapter makes
the push its monitor takes, so the core never reaches the monitor outside its contract
([ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md)). `check_in` is
held to the rules `provision` and `retire` are: it touches no monitor holding no tag or a
tag outside `lemonfiber:`, and an adapter whose monitor cannot be configured answers it
`unsupported` (`ARCH-R390`).

### 2. A job is a hosted command that acts on a beat

The jobs are the commands the machine's service manager hosts that act on a beat, each
checking in at every beat it acts on:

- the guard on the data location, which passes the forwarded port on each minute, checks
  in each minute under `lemonfiber:job:guard`;
- the clock that closes requests nobody ruled on, which wakes each hour, checks in at each
  wake under `lemonfiber:job:expiring`.

A job's heartbeat is provisioned only where the service manager hosts its command, since a
command nobody hosts is not expected to run.

### 3. A critical service is `critical` or `core`

A critical service is one whose manifest names its criticality `critical` (its failure has
consequences outside the machine) or `core` (its form does not work without it).

## Consequences

### Positive

- Every heartbeat the core provisions is one a job feeds, so a missed check-in means a job
  that stopped.
- What counts as critical is read from the manifest, which every part already declares.

### Negative

- An adapter for `status.watch` implements five operations rather than four.

### Neutral

- A media server graded `important` is watched as the household's way in rather than as a
  critical service.

## Alternatives considered

- **`provision` answers a check-in address, and the core calls it directly.** Rejected: the
  core would then reach a part outside its contract.
- **No job today.** Rejected: `K2-R4` would go unmet in the version it is a goal of.
- **Critical alone.** Rejected: almost nothing in the bundle is graded `critical`, so the
  watcher would watch next to nothing.

## Related

- [ADR-0061](0061-the-outside-watcher-is-a-capability-the-core-provisions.md)
- [K2 Uptime monitoring](../../10-functional/features/k-observability/k2-uptime.md)
- [Capability contracts](../../20-architecture/contracts/capability-contracts.md)
