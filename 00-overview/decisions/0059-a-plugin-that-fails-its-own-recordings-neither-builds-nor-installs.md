# ADR-0059: A plugin that fails its own recordings neither builds into the core nor installs

**Status:** Accepted
**Date:** 2026-11-04
**Decided:** 2026-11-04, by the maintainer, Wessel Verheij:

- the core does not build while a plugin the bundle pins has a case of a contract it
  speaks that fails or has no recording;
- an install or update refuses a plugin with such a case, and names each one.

## Context

`F14-R6` holds every plugin to the contracts it speaks, case by case, proved by the
recordings it ships at `conformance/<capability>@<major>/<case>.json`. One judge reads
them: it walks a contract's cases, reads each case's recording, and replays the recorded
answer through the same client the core asks a running adapter with. Before this
decision the judge lived in `lemonfiber-core`, and only `lemonfiber plugin conform`
called it.

Two places have to reach that judge:

- **The build.** The bundle is compiled into the core by `lemonfiber-bundled`'s build
  script. `lemonfiber-plugin` and `lemonfiber-core` both depend on `lemonfiber-bundled`,
  so its build script cannot depend on either.
- **Install and update.** Both pass through one acceptance step in the core. That step
  checked a plugin's manifest and ran the live unkeyed cases at start, but read no
  recording, so a plugin with a failing or missing recording installed.

Every adapter repository builds against `lemonfiber-contract`, which holds the contracts,
their case lists and the client.

## Decision

### 1. The judge has a crate of its own

`lemonfiber-conformance` holds the recording format, its reader and the judge. It depends
on `lemonfiber-contract` and `lemonfiber-ports` and nothing above them, so
`lemonfiber-bundled`'s build script can depend on it.

The judge takes plain inputs: the contract spoken, the media types the upstream files,
the upstream's `image@digest`, and the plugin's root. It reads no plugin manifest.
Reading the manifest, and the manifest's own refusals, stay with the core.

### 2. A missing recording is its own verdict

A case is `Passed`, `Failed`, `Unrecorded` or `Unproven`:

- `Unrecorded`: no recording is there.
- `Unproven`: a recording is there and could not be judged, for example because it was
  taken against another upstream.

An operation added to a contract after the minor a plugin recorded against is not a case
of that minor, as [ADR-0028](0028-a-supported-major-is-data-proved-by-its-own-recordings.md)
reads a supported major.

### 3. The build refuses

The build script reads each pinned copy's services: what each speaks and fronts, and the
image, digest and media types of what it fronts. It judges every case of every contract
spoken, and refuses the build on any case that is not `Passed`, naming the plugin, the
contract and the case.

The client bounds every answer in time, so the build script, which has no async runtime
of its own, drives the replay to completion on a runtime of one thread with a clock.

### 4. Install and update refuse

The acceptance step every install and update passes through judges the plugin the same
way. It refuses with its own error code, naming each case that failed or has no
recording. The live pass at start still runs after that.

## Alternatives considered

| Alternative | Why not |
|---|---|
| A required test that judges every pinned copy | A red check can be merged past or skipped; the requirement is that the core does not build |
| The judge in `lemonfiber-contract` | Every adapter builds against that crate and would carry the recording format and the judge it never runs |
| The judge kept in the core, with the build script running a built binary | The binary depends on `lemonfiber-bundled`, so it cannot exist while that crate builds |
| Refusing first-party plugins alone at install | `F14-R6` holds every plugin to its contracts; a third party's adapter is the one least likely to have been checked |

## Consequences

- A catalogue pin whose copy fails a case breaks the core's build, and the build says
  which case.
- A plugin installs only with a recording for every case of every contract it speaks.
  The core's own test plugins carry recordings made from each contract's case list.
- `lemonfiber plugin conform`, the build and install all read one judge, so they agree.
- The core's build depends on one more crate.

## Revisit if

- A contract gains a case that cannot be judged from a recording.
- The bundle stops being compiled into the core.

## Related

- [F14](../../10-functional/features/f-extensibility/f14-every-part-is-a-plugin.md) — `F14-R6`
- [ADR-0028](0028-a-supported-major-is-data-proved-by-its-own-recordings.md) — a supported major is proved by its own recordings
- [ADR-0005](0005-embedded-stack-assets.md) — lemonfiber embeds the stack at build time
