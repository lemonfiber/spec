# ADR-0030: An assertion declared to fail on a recording is reported as failing as declared

**Status:** Proposed
**Date:** 2026-09-26

## Context

A plugin's proofs and contributed checks are proved against recordings of the
image it pins, so that neither its author nor any CI needs a live instance
(`F10-R4`). A recording names the image it was taken from by digest, and that
digest is the one the manifest pins (`ARCH-R121`).

`plugin-plex` declares the doctor check `plex:claimed`, which expects
`/MediaContainer/claimed` to be `true` on `GET /identity`. An unclaimed Plex
server hands ownership to whoever reaches it first, so the check is right to
exist. Claiming a server needs a plex.tv account, and the plugin's CI holds
none. The one recording of `/identity` is of an unclaimed server, and the check
fails on it. The recording is honest, and so is the failure.

`plugin-plex`'s `proofs` job reports every assertion that is not passed as a
failure, so the job is red on every run. A permanently red job teaches its
readers to ignore it, and it hides the day something else in it fails.

`F10-R11` answered part of this with `fires_on`: a check names a recording it
must fail on, failing there is reported as **passed**, and passing there is
reported as refuted. It covers checks and not proofs, carries no reason, and
reports a failure as a pass. It is in `lemonfiber`'s `main` and in no release.

## Decision

A declared proof and a contributed check may each declare, per recording, the
verdict it is expected to reach there, with a reason. The only verdict it may
declare is failing (`F10-R12`, `ARCH-R130`).

- Failing there is reported as **failing as declared**, apart from passed and
  from failed, with the reason and what the assertion failed on (`F10-R13`).
- Passing there is reported as failed, naming the declaration as stale, and fails
  the run (`F10-R14`). The declaration is removed in the change that made the
  recording pass.
- The declaration applies to the recording it names and nothing else. The live
  service, and every other recording, hold the assertion to its own expectation
  (`F10-R15`).
- An assertion that could not be run on the named recording is unproven, as any
  other is. A declaration never stands in for a run (`F10-R16`).
- The catalogue's CI (`F5-R13`) and the release train's plugin gate (`OPS-R72`)
  each name a proof failing as declared, do not refuse on it, and do not count it
  as passed.

`F10-R11` is superseded by `F10-R12` to `F10-R16`, `F5-R2` by `F5-R13`, and
`OPS-R69` by `OPS-R72`.
`fires_on` is replaced by `expected`.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| Report failing where declared as passed (`F10-R11` as written) | A pass says the assertion holds. Here it does not, and a reader of the report would learn the opposite of what the recording shows. |
| Skip the assertion against that recording | A skipped assertion reads as one that ran. Nothing would notice the recording starting to pass, and nothing would say why the assertion was not run. |
| Record a claimed server in CI | Needs a plex.tv account held for CI, which is ruled out. |
| Hand-write a recording of a claimed server | It would carry the pinned digest and an answer that image never gave: a claim about the software rather than a recording of it. |
| Drop the check, or its fixture | The check is the finding the plugin exists to make about an unclaimed server. Without a recording it is not proved at all. |
| Make the `proofs` job advisory | Every other assertion in it stops being enforced with the one that is expected to fail. |
| Allow a declaration of unproven, or of any verdict | Unproven is the verdict that says nothing ran. Excusing it is the hiding this decision exists to prevent. |

## Consequences

### Positive

- A plugin whose honest recordings include the state a check exists to find has
  a green proving run that still says so, every run, with the reason.
- A declaration cannot outlive the fact it records: the day the recording passes,
  the run fails and names it.
- Proofs get the same treatment as checks. A proof's passing state is sometimes
  as unrecordable as a check's.

### Negative

- The report has a fourth outcome, and every reader of it changes: `lemonfiber`'s
  verdicts, the plugin template's reader, the catalogue's CI, and the release
  train's plugin gate.
- `fires_on` is removed before any release carried it, so `lemonfiber`'s
  unreleased implementation of `F10-R11` is reworked rather than shipped.

### Neutral

- A probe carries no declaration. A claim is what other services are wired on,
  and a claim whose probe fails is not wired to (`F4-R6`).

### Affected repositories

- **lemonfiber** — the manifest types and generated schema (`expected` replacing
  `fires_on`), the verdict `lemonfiber plugin claims` reports, and the published
  contract artefacts.
- **sdk-ts, sdk-php** — regenerated from the contract that carries the field.
- **plugin-template** — `.github/reader/reader.py` reports the new outcome apart
  from passed and failed, writes it to `proofs.json`, and fails only on the rest.
  `plugin-komga`, `plugin-uptime-kuma` and `plugin-plex` carry the same file.
- **plugin-plex** — `plex:claimed` declares that it fails on
  `fixtures/identity-anonymous.json`, with the reason, once `targets.toml` names
  a release that reads `expected`.
- **lemonfiber-plugins** — its CI reads the new outcome under `F5-R13`.
- **spec** — `scripts/check_plugins.py` and the two workflows that run it
  implement `OPS-R72`.

## Revisit if

- A plugin needs to declare a verdict other than failing against a recording.
- Recordings of a service's passing state become obtainable without an account,
  so declarations of this kind stop being needed.
