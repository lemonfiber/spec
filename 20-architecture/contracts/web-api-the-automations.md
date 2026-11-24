# Contract: the web API's automations

**Status:** Accepted

Part of the [web API contract](web-api.md): the automations a stack runs beside its services
(cross-seeding, announce-driven grabbing, quality-profile sync, library cleanup, playback
statistics and the metrics pipeline), the one answer each gives to whether it works, and what a
member is answered of their own viewing. The requirements it describes are listed with the rest
of the contract's, under [Requirements](web-api.md#requirements).

## One answer to whether it works

Each of these proves its wiring against real data rather than trusting it
([H1](../../10-functional/features/h-glue/h1-cross-seed.md),
[H2](../../10-functional/features/h-glue/h2-autobrr.md),
[H3](../../10-functional/features/h-glue/h3-quality-sync.md),
[H6](../../10-functional/features/h-glue/h6-library-cleanup.md),
[H8](../../10-functional/features/h-glue/h8-stats.md),
[K1](../../10-functional/features/k-observability/k1-metrics.md)). What each proves differs;
the answer it gives does not. Every read of an automation carries `proof` in one shape, the
same type in the artefact for all six, so a client words it once and an automation added later
is worded the same way:

```json
{ "state": "unproven", "checked": 1795563600, "against": "the sonarr instance",
  "why": "the scores written were not read back" }
```

`state` is `working` where the proof held against real data, `unproven` where it has not held
yet, and `unknown` where it could not be told. `checked` is the instant the proof last ran, and
is absent where it never has. `against` names what it ran against: the local item, the announce
line, the instance, the session or the target. `why` says, in the operator's words, why one is
not `working`, and is absent where it is (`ARCH-R458`).

A proof that has not run is `unproven`, not `unknown`: nothing has shown it works, and that is
something the stack can tell. `unknown` is the stack being unable to tell at all, a proof that
could not be run or read, and is never shown as working.

## What the automation is doing

```
GET /api/automations
```

The `automations` envelope `lemonfiber automations --json` prints: each automation this stack
runs, by what it runs, with `kind` (`cross-seed`, `announce`, `quality-sync`, `cleanup`,
`playback-stats` or `metrics`), its `name`, and its `proof`. An automation the stack does not
run is not listed, not even as off: a list of everything that could be is a list mostly of
things the operator never chose. It is the operator's: an operator session and a key whose
scope reaches reads are answered, and a member session and a key scoped to a member are
refused (`ARCH-R459`).

## What a member watched

```
GET /api/watched        POST /api/actions/watched-hide
```

`/api/watched` answers a member session, and a key scoped to a member, with that member's own
viewing history and nobody else's: each title, when it was watched and how far through, in the
household's words. It is refused to an operator session and to a `read` or `act` key, because
the operator is answered whether the statistics work, on `/api/automations`, and never what
anybody watched (`H8-R15`). Where the operator has turned members' history off with
`LEMONFIBER_MEMBER_HISTORY`, nothing is kept per member while it is off, and it answers that
it is off and lists nothing, what was kept before included (`H8-R16`).

`watched-hide` takes `hidden`, `true` or `false`, and is taken from a member session alone. While
a member's history is hidden, `/api/watched` answers them that it is hidden and lists nothing,
until they show it again (`H8-R17`, `ARCH-R460`).

## Related

- [The web API](web-api.md) — the contract this page is part of
- [N26](../../10-functional/features/n-companion/n26-what-the-glue-is-doing.md) — the companion's screens for these
