# ADR-0042: The bundle is first-party plugins, pinned and embedded

**Status:** Accepted
**Date:** 2026-10-10
**Decided:** 2026-10-10, by the maintainer, Wessel Verheij: an existing install moves
to each first-party plugin in place, on update.

**Supersedes** [ADR-0004](0004-four-repo-split.md) where it splits the stack into
`lemonfiber-media-stack`, and [ADR-0001](0001-docker-compose-as-engine.md) where it
keeps that stack usable without lemonfiber.
**Amends** [ADR-0005](0005-embedded-stack-assets.md): what is embedded is the bundle.

## Context

[ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md) makes every
bundled part a first-party plugin and the media stack "the bundle". It does not say
what the bundle is, where it lives, how the binary carries it, or how an install
running today's bundled services comes to run the plugins instead. Without that, no
part can leave the core: deleting a service module needs the default stack to install
its plugin in the module's place.

## Decision

1. **The bundle is a manifest in `lemonfiber-plugins`.** It names the forms, which
   capabilities each form asks for, and the first-party plugin that fills each by
   default, each pinned by release: its version and the digest of its manifest.
2. **The binary embeds it.** `lemonfiber-plugins` enters the core as a submodule at a
   pinned commit, as the media stack did. The bundle and every pinned plugin's manifest
   are compiled in. The set the core trusts as first-party is generated from the
   pins, by plugin and manifest digest, so a plugin is first-party only at the exact
   manifest the bundle names.
3. **A stack is installed through the plugin path.** Bringing up a form installs its
   first-party plugins the way an outsider's is installed, offline from the embedded
   manifests, and settles each as its capability's default filler. Nothing about a
   first-party plugin bypasses validation, conformance or the trust gate.
4. **An install moves in place, on update.** When an update brings a part's
   first-party plugin, the bundled service it replaces becomes that plugin's upstream
   under the same container name, the same configuration directory and the same data.
   The move is rehearsed and shown before it is made, keeps accounts, progress and
   keys, and is undone as any substitution is.
5. **Parts move one at a time.** Until a part's plugin is in the bundle, the core keeps
   its bundled adapter; the release that adds the plugin deletes the adapter. A stack
   running some parts as plugins and some as bundled services is supported for as long
   as the moves take, and no longer.
6. **The media stack retires.** `lemonfiber-media-stack` is archived once nothing reads
   it. Each part's description, configuration and recordings move to its plugin's
   repository. The stack is no longer a Compose file someone runs without lemonfiber;
   each plugin's repository is what stands on its own.
7. **The bundle rides the release train.** A first-party plugin's release moves the
   bundle's pin, and a lemonfiber release embeds the bundle at that pin
   ([ADR-0033](0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md)).

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Operator opts in to each move** | Two code paths would live until every install had switched, and a stack that never switched would keep a core module ADR-0041 deletes. |
| **Fresh installs only** | The longest-lived dual path: every bundled adapter would stay in the core until a later major. |
| **Keep the media stack, fill it from plugin manifests** | A second description of each part beside its plugin's, which drifts. |

## Consequences

- The core loses the media-stack submodule and gains `lemonfiber-plugins`.
- `first_party::EMBEDDED` stops being hand-written: it is what the bundle pins.
- Every update that moves a part carries a rehearsed, journalled substitution, and the
  doctor reports a stack mid-move.
- A fork of the stack is a fork of `lemonfiber-plugins` and of the plugins it pins.

## Revisit if

- An update cannot move a part in place without losing data the part holds.
