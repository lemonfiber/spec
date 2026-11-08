# ADR-0063: The queue heals by strikes, over the curator and the client

**Status:** Accepted
**Date:** 2026-11-08
**Decided:** 2026-11-08, by the maintainer, Wessel Verheij: queue self-healing is the one
way lemonfiber acts on a wedged download, gated by strikes and a grace window, classified
from what the curator and the download client each answer, and read at `GET /api/queue`.

## Context

H5 asks lemonfiber to classify every queued download, act on one only after it has been
flagged on several consecutive checks, and record every run (`H5-R1` to `H5-R15`). C7
already acts on stuck items: with `LEMONFIBER_STUCK_SEARCH_AGAIN` on, the core asks each
curator to drop a stuck download, blocklisting its release, then to search again, once per
release, journalled and undone through `grab` (`C7-R16`). Two loops acting on the same queue
would each be a reason the other's record is wrong.

H5 needs what the client knows of an item: whether it is stalled, resolving metadata or in
error, and when it was added. `download.torrent@1` and `download.usenet@1` answer `transfers`
with a name, progress, speed, an estimate and what is left, and nothing that pairs an item
with the curator's queue entry for it other than its name. The companion's N16 page draws
the classification and every run (`N16-R8`, `N16-R9`, `N16-R11`), and no read serves them.

## Decision

### 1. One healing path

Queue self-healing is the one way lemonfiber acts on a wedged download. The act C7 named
becomes its healing run: `LEMONFIBER_STUCK_SEARCH_AGAIN` is its switch, off by default
(`H5-R15`), and each act is the one `C7-R16` journals: the curator drops the download,
blocklisting its release, and searches again, and putting it back asks `grab`. Off, the
classification still runs and is read.

### 2. Strikes and grace

The guard's pass classifies every queued download each `LEMONFIBER_QUEUE_EVERY_MINUTES`
(10 by default). An item flagged for the same reason on `LEMONFIBER_QUEUE_STRIKES` (3)
consecutive passes, and added longer ago than `LEMONFIBER_QUEUE_GRACE_MINUTES` (30), is
acted on; one healthy pass resets its strikes. A download whose estimate runs past
`LEMONFIBER_QUEUE_SLOW_DAYS` (7) is slow. The strikes are kept beside the configuration so
they survive a restart of the guard.

### 3. The client says what it knows, by its own id

`download.torrent@1` and `download.usenet@1` gain minor 2: `transfers` answers each item's
id in the client, its state (`downloading`, `stalled`, `metadata`, `error`, `queued` or
`paused`) and when it was added. The core pairs a curator's queue entry with a client's item
by the client's id the curator holds for it, never by name. An item in a client under a
curator's category that no curator's queue holds is orphaned. A client speaking an earlier
minor answers none of these, so its items are classified from the curator's view alone, and
the read says so.

### 4. Refusals and fallbacks

Nothing is acted on for a curator whose download client cannot be reached or whose
credential is unverified, or whose client files outside the curator's folders as the seed's
filing check finds it (`H5-R6` to `H5-R8`, `H5-R11`). A curator that answers `unqueue`
`unsupported` is asked to search again alone, and the run records that the download was not
removed (`H5-R9`).

### 5. Every run is kept and read

Every run, rehearsed or not, is kept beside the configuration, the newest first and a bounded
number of them, with each item it acted on, why, and each of its three acts as it came out
(`H5-R12`). `lemonfiber queue --json`, served at `GET /api/queue`, reads the switch, the
strikes and grace in force, every unhealthy item with why, its strikes and what the next run
would do to it, every curator or client it could not reach, the mount mismatch, and the runs
(`H5-R16`).

## Consequences

### Positive

- One record of what lemonfiber did to the queue, and one undo.
- An orphan is found by id, so a renamed release is never torn down as an orphan.

### Negative

- Every download client's adapter answers three more fields from minor 2.

### Neutral

- `C7-R16`'s once-per-release rule becomes the strike gate's: an item healed and grabbed
  again starts from no strikes.

## Alternatives considered

- **Two loops, C7's and H5's.** Rejected: two records of acts on one queue.
- **Classify from the curator alone.** Rejected: stalled, slow and resolving metadata
  collapse into one reason, and orphans cannot be seen.

## Related

- [H5 Queue self-healing](../../10-functional/features/h-glue/h5-queue-selfheal.md)
- [C7 Queue health](../../10-functional/features/c-trust/c7-queue-health.md)
- [N16 What happened while nobody was looking](../../10-functional/features/n-companion/n16-nobody-was-looking.md)
- [Capability contracts](../../20-architecture/contracts/capability-contracts.md)
