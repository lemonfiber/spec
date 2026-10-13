# ADR-0048: A part without a port is proved by running its own program

**Status:** Accepted
**Date:** 2026-10-12
**Decided:** 2026-10-12, by the maintainer, Wessel Verheij:

- a part with no network surface is proved live like every other part, by a `[[proof]]`
  that runs its image's own program: `run = { args = [...] }`, arguments to the image's
  own entrypoint, on `[[proof]]` only, while claim probes stay requests; an `expect`
  checking only `exit` is refused as a status alone is;
- the run is a fresh container from the pinned digest, under the service's posture, user
  and memory limit, with no network and a throwaway copy of its starting files at its
  configuration path, removed afterwards;
- it runs in the plugin's CI, at install and at update, in `plugin prove`, in the
  release gate against recordings, and in the doctor;
- it is bounded: 30 seconds by default and 120 at most, 64 KiB of standard output read
  and 1 KiB recorded, standard error never judged, control characters stripped, an argv
  with no shell, an environment of the entry's constants and `TZ`, `PUID` and `PGID`,
  run as the service's `user_mode`;
- a record mode performing the same bounded run writes the recording;
- the core starts the proof's container through the engine API, as an exception to
  ADR-0008's split.

**Amended** by [ADR-0049](0049-a-moved-pin-is-recorded-again-by-the-core.md): §3. The record mode records
request proofs, claim probes, contributed checks and conformance cases as well as runs.

**Amends** [ADR-0008](0008-hybrid-docker-access.md): a proof's container, which no
Compose project holds, is created, started and removed through the engine API.

## Context

Every proof and claim probe is one HTTP request judged against a recorded response
([plugin-manifest-proof](../../20-architecture/contracts/plugin-manifest-proof.md)). A
first-party plugin's CI runs each image under its posture, healthy and answering its
probes (`REPO-R96`). Quality sync, Recyclarr, has nothing to answer. Measured against
its pinned image, `ghcr.io/recyclarr/recyclarr@sha256:9c6c74d5…`, on 2026-10-12:

- it publishes no port, listens on nothing, provides no capability, and its image
  declares no health check; its manifest's `health` is the container running;
- its entrypoint starts a cron daemon with no arguments, and runs `recyclarr "$@"` with
  any, with no `eval`;
- `--version` with no network prints `v8.7.3 (Branch.master.Sha.237d4dd…)` and exits 0,
  under the `confined` hardening too, and an unknown option exits non-zero;
- every command that reads its configuration fetches the quality guide over git first,
  so nothing deeper is provable without the network;
- run as the operator's uid without a writable configuration directory, even
  `--version` fails, because it creates `/config/state` as it starts.

A proof is evidence that the pinned program starts as the service runs it. "The
container is running" says less: a container whose program fails at its first cron
tick is running.

## Decision

1. **A `[[proof]]` may run the image's own program.** `run = { args = [...] }` in place
   of `request`, judged on `exit` and `stdout_starts_with`. The arguments go to the
   entrypoint the image declares, so the manifest names no program, and lemonfiber
   starts no shell. A capability's probes stay requests, because the vocabulary
   declares them as requests and no capability needs another kind. An exit status alone
   is a status (`ARCH-R105`, `ARCH-R283`).
2. **It runs apart from the service, with less than the service has.** A new container
   from the pinned digest, with no network, as the service's user, under its posture and
   memory limit, with a throwaway copy of its starting files at its configuration path,
   the entry's constants and lemonfiber's `TZ`, `PUID` and `PGID`, and nothing else. No
   setting, secret, URL, mount, device or shape reaches it. It is stopped at its time
   limit, 64 KiB of its output is read, and the container is removed (`ARCH-R284`).
3. **It is recorded by running it.** `lemonfiber plugin record` performs the same
   bounded run and writes the recording. The plugin's CI records again and refuses a
   recording the run does not reproduce, which is how a part without a port is proved
   live (`ARCH-R285`, `REPO-R96`).
4. **It runs wherever a proof runs, and in the doctor on the doctor's own cadence.** The
   doctor runs it when it is run, never on the dashboard's gather, and only where the
   image, the arguments, the posture and user, the starting files or the lemonfiber
   release changed since the verdict it keeps. An image addressed by digest runs the
   same program every time, so a verdict reached once holds until one of those moves
   (`ARCH-R286`, `ARCH-R287`).
5. **The engine API starts it.** ADR-0008 sends writes through Compose because the
   engine API knows nothing of profiles. A proof's container belongs to no profile and
   no project, and `docker compose run` cannot take a service's network away, so the
   core creates, starts, waits on and removes it through the engine API. It carries no
   Compose label, so no reading of the stack lists it.

## Consequences

- Recyclarr gains `recyclarr.runs`, and every part, with a port or without, has
  something its CI proves live.
- A run's output is untrusted text from a program: reports strip its control
  characters, so an escape sequence never reaches the operator's terminal.
- The first doctor run after a pin moves starts a container, and may run past
  `C1-R12`'s thirty seconds once.
- `REPO-R96`'s live step is not yet in the reusable `first-party-plugin.yml` for any
  plugin; adding it is a workflow change every plugin repository's pin follows.

## Alternatives considered

**A full argv naming the program.** More general, and `["/bin/sh", "-c", …]` is a shell
string under another name; refusing interpreters by name is a list that never closes,
the shape ADR-0043 rejected for environment names.

**The container's last scheduled run.** Not provable in CI: it waits for the schedule,
and needs the network and seeded keys.

**A health command.** It runs on every interval in production, and is a health probe
rather than evidence recorded against a pin. The image ships none.

**`docker exec` inside the running service.** The core already has a bounded exec
(ADR-0008). It shares the service's network and its live configuration directory, so
neither bound would hold.

**Running as the image's own user.** The service runs as its `user_mode` writes, and
Recyclarr fails as the operator's uid where it passes as the image's: a proof run as
another user passes where the service does not.

**The doctor running it on every gather.** A container started every few seconds, for a
verdict a pinned digest cannot change.

## Revisit when

- A part's only live question needs the network to ask.
- A capability needs a probe that is not a request.
