# ADR-0049: A moved pin is recorded again by the core

**Status:** Accepted
**Date:** 2026-10-13
**Decided:** 2026-10-13, by the maintainer, Wessel Verheij:

- `lemonfiber plugin record` records every recording a manifest names, requests as well
  as runs: a fresh container of the pinned digest under the service's posture, its first
  run done through the adapter lemonfiber already has for it, an operator's probe asked
  with the key that first run left lemonfiber holding, and every recording written with
  `recorded_from` set to the image that ran;
- a first-party plugin's upstream image pins move every week, to the newest release of
  each pin's major, one rolling pull request per image, through a reusable workflow of
  `spec`'s that records them again with that command in the same change;
- the media stack's own `pins` workflow stops in the change that turns those callers on.

**Amends** [ADR-0048](0048-a-part-without-a-port-is-proved-by-running-its-own-program.md):
§3, the record mode, which records request proofs, claim probes, contributed checks and
conformance cases as well as runs.

## Context

A recording names the digest it was taken from, and one naming any digest but the
manifest's pin is refused (`ARCH-R121`, `ARCH-R217`). Moving a pin therefore means
recording again in the same change.

The media stack moves every upstream pin each Monday: `scripts/pins.py` takes the newest
tag in the pinned tag's spelling and major, and `scripts/record.py` records each claim
again from a fresh container ([ADR-0028](0028-a-supported-major-is-data-proved-by-its-own-recordings.md)
§1a). The recorder holds a first-run recipe of its own for each service it records:
about 460 lines of Python that read a key from a file, finish a setup wizard or sign in
as an image's documented administrator.

[ADR-0045](0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md)
moves each part into a plugin repository and freezes the media stack at the source
switch. Measured against those repositories on 2026-10-13:

- Each of the seventeen part repositories that pins an upstream's image and has no
  adapter carries one or two recordings naming that image's digest, and `plugin-jellyfin` carries `fixtures/` and
  the conformance recordings of the two contracts its adapter speaks, which only its own
  `.github/record.py` writes.
- Nothing in a plugin repository moves an upstream pin. Once the media stack is frozen,
  no upstream image would move again.
- `lemonfiber plugin record` records run proofs only (`ARCH-R285`), and no build ships it
  yet.
- A first-party plugin carries no Python of its own: the reader is `first-party-plugin`'s.
- The plugin check already goes red where an upstream publishes a tag again under a new
  digest, because the reader's `image` step holds the tag to the pinned digest.

The core already knows each part's first run. An assembled part's in-process adapter,
named by `api`, reads its key through `api.key_source`; an installed part's adapter
performs its first run over its contract (`F14-R26`, `F14-R28`).

## Decision

1. **`plugin record` records every recording a manifest names.** Each run proof's, as
   `ARCH-R285` already holds; each request proof's, each claim probe's and each
   contributed check's; and, for a service an adapter of the plugin `fronts`, every case
   of each contract that adapter speaks. It takes no option: the manifest is the list,
   as it is for run proofs.
2. **One fresh container per service.** It is started from the pinned digest under the
   service's posture, user and memory limit, with a throwaway copy of its starting files
   and a throwaway data directory, the entry's constants and `TZ`, `PUID` and `PGID`. Its
   network is one of its own that no other container joins, with the adapter that
   fronts it as the one exception, and its `listens` port is published on loopback alone.
   It is waited on until its `health` passes within its own `timeout_s`, and every one of
   its recordings is asked of that one container.
3. **The first run is the core's own.** For an assembled part it is the first run the
   in-process adapter `api` names performs. For an installed part it is the adapter
   started from its own pinned digest beside the service, given the key and
   `upstream.json` lemonfiber writes at install, and the first run install performs over
   its contract. A service with neither has no first run.
4. **An operator's probe is asked with the key that first run left lemonfiber holding.**
   A probe whose vocabulary entry says `credential = "operator"` presents it as the
   adapter presents it; every other request presents nothing beyond what the manifest
   writes (`ARCH-R123`). A recording never holds the key.
5. **What is written is what came back, scrubbed.** `recorded_from` is the image that
   ran, and for a conformance case the image of the service the adapter fronts. The
   request is the one the manifest declares; the response is its status, its
   `content-type`, and its body as parsed JSON or as its first 1 KiB, cut at a character
   boundary, as a run's output is recorded. Every credential the run made or read, in
   every encoding an answer could echo it in, and the container's id, hostname and
   addresses are replaced with `<redacted>`; a recording still holding one is not
   written. The `note` already at that path is kept.
6. **A service is recorded whole or not at all.** Where its container, its health, its
   first run or any of its requests fails, none of its recordings is written, the ones
   already there stay as they were, and the run goes on to the next service. The run
   fails naming the service, the step and why, with the last 50 lines of the
   container's log scrubbed and stripped of control characters. Every container and
   network it started is removed through the engine API, as ADR-0048 §5 starts a run
   proof's.
7. **A first-party plugin's upstream pins move every week.** `spec`'s `upstream-pins`
   workflow, on the plugin repository's schedule, moves each image not under
   `ghcr.io/lemonfiber/` to the newest tag in its pinned tag's spelling and major whose
   index publishes `linux/amd64` and `linux/arm64`, and takes a digest that moved under an
   unchanged tag. Each image moves on its own rolling branch, recorded again by `plugin
   record` at the lemonfiber its `targets.toml` names, with `proofs.json` written from
   the new recordings. The image runs and lemonfiber is built in a job that holds no
   secret. The job holding the App's token runs none of it: it works the move out again
   from main's manifest and the registry, and commits only plain files, never read
   through a link: main's manifest with exactly that move, `proofs.json`, and
   recordings the manifest names taken from exactly that pin. A bump that leaves no
   recording naming the old image is armed to merge and the required checks judge it;
   one that does is opened disarmed, naming each (`OPS-R87`).
8. **One mover holds each upstream's pin.** The callers are turned on in the same change
   that stops the media stack's `pins`, at the source switch (ADR-0045 §11), so the
   stack and the plugin repositories never move the same pin apart.

## Consequences

- No part's first run is written twice: the recording uses the code the stack runs.
- The media stack's per-service recipes are not carried anywhere; the adapters replace
  them.
- `plugin-jellyfin`'s `.github/record.py` is replaced by `plugin record` once the core
  records conformance cases.
- An adapterless part's recordings change only through the core, so a part the core
  cannot first-run is a part whose pin cannot move clean.
- The callers wait on a core build that records requests; until then a bump opens
  disarmed and says the recordings were not taken.
- `F2-R14`'s release date stays the bundle's: the catalogue's reviewed pin pull request
  moves it beside the plugin's revision.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Port the media stack's recorder into `spec`** | Eighteen first-run recipes in a repository that holds no part's code, written a second time beside the adapters that already perform each first run. |
| **The recorder in plugin-template's reader** | The same recipes, copied into every plugin's CI. |
| **Move the pin and list the stale recordings** | Every bump stays red until someone records by hand, and the bot's next rebuild of the branch discards what they pushed. |
| **Rewrite `recorded_from` without running anything** | A recording would name an image it never came out of, which is the drift `ARCH-R121` exists to refuse. |
| **Dependabot's docker manager** | It does not edit `plugin.toml`, records nothing, and rebuilds its own branches. |
| **A container per recording** | Every first run repeated for each probe of the same service, for nothing a second container would show. |
| **No network route out** | Some upstreams finish their first run only once they reach the internet, and Docker publishes no port from a network without one. |

## Revisit if

- A part's first run cannot be performed by its adapter without an operator.
- An upstream's answers differ from one fresh container to the next in a way scrubbing
  cannot name.
