# ADR-0046: The stores are filled once, at the cutover, and a secret never enters the journal

**Status:** Accepted
**Date:** 2026-10-12
**Decided:** 2026-10-12, by the maintainer, Wessel Verheij:

- the stack's settings stay in its environment file, behind one closed table naming each
  by its setting, until the release that stops reading the stack's static Compose files,
  while a plugin's settings and secrets go to the stores at once;
- the first run of that release reads the environment file once and files every value
  the assembled parts and the settings the core publishes read from it under their
  settings or secrets, journalling each, and lemonfiber never reads the file for them
  again; a part's later move in place migrates nothing, since its names are kept;
- an assembled part keeps its plugin manifest's `[[secret]]`, each held in the service
  id's namespace;
- the journal records a secret's fingerprint and never its value, not even sealed; the
  secret store keeps one previous value, which undo restores only while the fingerprints
  match, and otherwise undo says the secret must be replaced at the terminal;
- a core setting is one of a closed list lemonfiber publishes, beginning with
  `LEMONFIBER_DEVICE_KEY_APPS`; `lemonfiber config` keeps every other `LEMONFIBER_*` key,
  and each command refuses the other's names, naming the right one;
- the `settings` event goes to the operator alone, never to a member's stream or a key's;
- a credential that crosses to a plugin is read from its holder whenever an entry is
  written and never copied into the secret store, so replacing it regenerates what reads
  it.

**Supersedes in part** [ADR-0043](0043-the-core-writes-every-compose-entry-from-one-typed-service-model.md):
the last sentence of §7, when the stack's environment file is read: once, at the first run
of the release that stops reading the static Compose files, rather than at each part's move
in place.
**Amends** [ADR-0045](0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md):
§2, an assembled part keeps its plugin's `[[secret]]` as well as the stack's setting and
credential names.

## Context

[ADR-0043](0043-the-core-writes-every-compose-entry-from-one-typed-service-model.md) §7
gives settings and secrets one home each, and has the move in place that brings a part's
first-party plugin read the stack's environment file once.
[ADR-0045](0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md)
separated the two events that sentence joined. A part moves in place when its adapter
ships, part by part, some of them after 0.18.0. The stack stops reading its static
Compose files at the compose cutover, which ships in 0.18.0. Read as written, the
environment file would stay a source of values for every part still assembled: two
places for one value, the alternative ADR-0043 rejected.

Measured against the core at `34a79f1d` and this specification at `e16d8d9`, five more
gaps stood between the decision and the stores:

- **An assembled part had nowhere to declare a secret.** It is a stack service, and a
  stack service named no `[[secret]]`, so the WireGuard key the egress guard reads had no
  declaration once the static Compose files go.
- **The journal kept credential values, sealed.** A change whose name looks like a
  credential is journalled with its value encrypted under a key kept beside the journal.
  A secret store whose journal holds its values keeps a second copy of every secret.
- **"Core setting" named no set.** `ARCH-R262` makes `LEMONFIBER_DEVICE_KEY_APPS` one,
  while `lemonfiber config` already reads and writes the core's `LEMONFIBER_*` keys. Two
  commands writing one name are two answers to who holds it.
- **The operator's stream reaches keys.** A member is given a stream of their own
  (`ARCH-R157`), and a `read` or an `act` key is given the operator's, so the `settings`
  event would reach the keys `ARCH-R254` refuses the read.
- **A crossing credential had no rule.** Copied into the secret store, it would be a copy
  that a replacement leaves stale.

## Decision

1. **The environment file is filed at the cutover.** Until the release that stops
   reading the static Compose files, those files substitute the stack's values from the
   environment file, so the stack's settings stay there, behind one closed table naming
   each by its setting, and the settings surfaces read and write them there, saying where
   each is held. The first run of that release reads the file once, files every value
   the assembled parts and the published settings read from it under their setting or
   secret, journals each, and never reads the file for them again. A part's plugin keeps
   the names the stack gave it (`ARCH-R273`), so its later move in place migrates
   nothing. A plugin's own settings and secrets have no reader in the static files, and
   go to the stores at once (`ARCH-R249`).
2. **An assembled part keeps its secrets.** Its plugin's `[[secret]]` declarations come
   with its one service, each held as `<service id>:<secret id>`, the name an installed
   plugin's would have, and written to the service's own secrets file. A `--stack-dir`
   stack's service still declares none (`ARCH-R275`).
3. **The journal holds a secret's fingerprint, never its value.** A secret's change is
   journalled by the fingerprint of the value before and after it, and never by the
   value, sealed or otherwise. The secret store keeps each secret's one previous value.
   Undo restores it only while the values held match the fingerprints journalled;
   otherwise it says the secret must be replaced at the terminal (`ARCH-R276`).
4. **A core setting is on a closed list.** The list is written in the web API contract's
   settings section, and holds `LEMONFIBER_DEVICE_KEY_APPS`. `lemonfiber settings` takes
   a core setting and no other `LEMONFIBER_*` key; `lemonfiber config` takes every other
   one. Each refuses the other's names, naming the command that takes it (`ARCH-R278`).
5. **The settings ride the operator's stream alone.** The `settings` event goes to the
   per-run token and an operator session, and to no member and no key of any scope
   (`ARCH-R257`).
6. **A crossing credential is read, never copied.** A credential `F14-R18` or `F14-R20`
   lets cross is read from the store that holds it whenever an entry naming it is
   written, so replacing it regenerates every entry that reads it (`ARCH-R277`).

## Consequences

- `ARCH-R248` holds for a plugin's values from the stores' first release, and for the
  stack's from the cutover. Both are 0.18.0's goals, and no release of 0.18.0, a
  pre-release included, is published before every goal is met.
- The undo of a secret's change works while nothing has replaced the secret since. After
  a second change, undoing the first says the secret must be replaced at the terminal.
- Only an operator who saw the secret's value can put it back after the store has moved
  on. A secret a recipe captured is captured again by running the recipe.
- `LEMONFIBER_DEVICE_KEY_APPS` is written by `lemonfiber settings` and refused by
  `lemonfiber config`, naming `lemonfiber settings`.

## Alternatives considered

**Filing each part at its move in place.** ADR-0043 as written. The environment file
stays a source of values until the last adapter ships, beside a settings store that
holds the rest.

**Filing the stack's values into the stores now and mirroring them into the environment
file.** The static Compose files would keep reading them until the cutover. Two copies of
each value, kept equal by a sync that can drift, for the window before a cutover that
removes the need.

**Journalling a secret sealed.** Undo would restore any secret at any time. The journal
would hold every secret beside the key that opens it, and a leaked secret could not be
removed from the machine without rewriting the journal.

**No undo for a secret.** The simplest rule, and a mistyped replacement could not be put
back a minute later.

**Every `LEMONFIBER_*` key under `lemonfiber settings`.** One command for everything, and
the operator's screens would show the core's tuning beside what a service reads. A short
list the operator's screens show, and the rest kept where they are, was preferred.

**The `settings` event to every stream that is not a member's.** A key refused the read
would be told every setting on the stream.

## Revisit when

- A service reads a value from the environment file that no setting or secret names at
  the cutover.
- The core needs a second setting of its own that the operator's screens should show.
