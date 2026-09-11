# ADR-0023: A pin is a digest, and a signature is a different question

**Status:** Proposed
**Date:** 2026-09-11

## Context

`F3-R8` asks that a plugin's referenced images be *"signed and pinned"*, and that
an unpinned or unsigned one be *"flagged rather than silently accepted"*. It
treats those as one obligation with one remedy. They are two obligations with
different failure modes, and the conflation hides a problem in each.

**The pinning half is stricter than the project currently practises.** Every one
of the nineteen bundled images is pinned to a tag — `lscr.io/linuxserver/sonarr:4.0.15`,
`qmcgaw/gluetun:v3.40.0` — and not one is pinned to a digest. `E1-R1` asks for
*"explicit versions"* and no *"floating tag"*, and a tag satisfies that reading:
`4.0.15` is explicit and does not float in the sense `latest` does.

It floats in the sense that matters. A tag is a name its publisher can repoint at
any time, so the image a maintainer reviewed when they moved the pin and the
image an operator pulls six months later can differ with nothing in the
repository having changed. That is precisely the reasoning
[ADR-0009](0009-action-pinning.md) applied to workflow actions — *"a mutable ref
is a real supply-chain surface"*, and every `uses:` in the estate is pinned to a
SHA because of it. The project holds its CI to a standard it does not hold the
software that runs on its users' machines to, and plugins make the gap
untenable: `F3-R8` as written would hold a stranger's image to a bar the bundled
stack does not meet.

**The signing half has nothing underneath it.** There is no artefact-signing
mechanism anywhere in the estate — no cosign, no minisign, no GPG. Release
artefacts carry checksums and build attestations, which are useful and are not
signatures. Signing is owed by `L1-R2`, and L1 ships at `1.0.0`.

`F5-R3` — *"Catalogue releases MUST be signed, and a signature that does not
verify MUST be refused"* — is scheduled before that. So a requirement due in the
plugin versions depends on a capability not owed until after them, and nothing
detects it: F5's frontmatter declares `requires: [F3]`, the ordering check reads
that frontmatter, and L1 is not in it.

There is also a distinction the single word "signed" obscures. A **catalogue
release** is signed by this project, and its signature answers *did the thing I
fetched come from the review I am relying on*. An **image** is signed, if at all,
by a publisher this project has no relationship with, and its signature answers a
question about them. Requiring both under one word would make the second a
condition of installing anything, which would exclude most of the container
ecosystem, including images the bundled stack itself depends on.

## Decision

**A pin is a digest. A signature is a separate obligation with a separate
remedy. And pinning applies to the bundled stack on the same terms it applies to
a plugin.**

1. **An image is named by an immutable digest.** The human-readable tag is
   recorded alongside it and shown wherever a version is shown, because a digest
   is not something an operator can read and `E1-R2` requires an update to state
   what the jump is. The tag is a label; the digest is what runs.

2. **The digest is of the multi-architecture index**, not of one platform's
   image. The stack is required to run on `linux/amd64` and `linux/arm64`, and
   pinning a single platform's digest would produce a stack that resolves on one
   machine and fails on another with an error about a manifest rather than about
   an architecture.

3. **This binds the bundled stack.** `E1-R1` is amended to require it. We do not
   hold a stranger's contribution to a bar the nineteen services we chose
   ourselves do not meet, and the honest correction is to raise ours rather than
   lower theirs.

4. **An absent digest is a refusal; an absent signature is an unproven.** A
   digest can always be obtained — it is a property of the image, available from
   any registry that serves it — so its absence is a fault in the manifest and is
   refused before anything runs. A signature may simply not exist, because its
   publisher never made one, so its absence is reported as unproven and is never
   reported as verified. `F3-R8` is split accordingly.

5. **A signature that is claimed and does not verify is refused**, for both
   kinds. That is worse than no signature and is treated as worse, exactly as
   `F5`'s `signature-unverified` state already says.

6. **Artefact signing is one capability with two consumers**, and the earlier
   consumer sets its date. The catalogue needs it before the release pipeline
   does; the mechanism is chosen once and serves both, rather than the catalogue
   inventing a second one because the first has not arrived.

7. **A digest that is later found to be bad is replaced, not revoked.** There is
   no revocation list and no callback: a pinned digest is inert data on the
   operator's machine, and the answer to a bad one is an update that names a
   different one. What lemonfiber owes is that the update path works and says
   what changed — not a mechanism by which a stranger can cause an already-
   installed plugin to stop working.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Keep tag pinning, for the bundled stack and plugins alike** | The status quo, and it means the reviewed artefact and the running artefact can differ silently. It is also the position the project has already rejected for CI in ADR-0009, and holding a lower standard for the software that touches the operator's library than for the software that builds it is not defensible when it is written down side by side. |
| **Digest-pin plugins, leave the bundled stack on tags** | What `F3-R8` says today. Holds a stranger to a bar we do not meet, which is both unfair and unpersuasive: the first contributor to notice will ask, and the answer would have to be "we have not got round to it". |
| **Require a verified image signature before installing anything** | Excludes most of the container ecosystem, including several images the bundled stack depends on. A requirement that the bundled stack itself would fail is not a standard, it is a wish. |
| **Treat an unsigned image as equivalent to an unverified one** | Collapses "nobody made a claim" into "a claim did not check out". They are different facts and an operator deciding whether to proceed needs to be able to tell them apart — the same distinction `C1` already draws between a check that failed and one that could not be run. |
| **Pin a single platform's digest** | Produces a stack that resolves on the maintainer's machine and fails on an operator's, with a diagnostic about a manifest rather than about an architecture. |
| **Build a revocation list the operator's machine consults** | A callback to a project-run service, on a product whose account of what leaves the machine is a closed list and whose whole proposition is that it does not phone home. The cure is worse than the disease, and the disease is already treated by an update. |
| **Defer `F5-R3` until `L1` delivers signing** | Leaves the catalogue serving unsigned releases in the versions where it is introduced — which is exactly when its review claim is doing the most work, since nobody yet has a reason to trust it. |

## Consequences

**Every image reference in the estate changes shape**, and the tooling that
advances them changes with it. Nineteen bundled services gain digests beside
their tags, the manifest gains a field, and the update flow has to move both
together — a pin bump that advanced the tag and left the digest would be worse
than either alone, because it would read as reviewed.

**Reviewing a pin bump gets harder in a way that is honest.** A digest is
unreadable, so a reviewer cannot see from the diff what moved. What they can see
is that exactly one thing moved and it names a version; the check that the digest
belongs to the tag is mechanical and belongs in CI rather than in a person's
head.

**`F5-R3` now has something to stand on, and it arrives earlier than L1
planned.** Artefact signing stops being a release-engineering detail owed at
`1.0.0` and becomes a prerequisite of the version that introduces the catalogue.
The version manifests have to reflect that, and the ordering check cannot see it
because it reads `requires:` frontmatter that does not mention L1.

**The bundled stack's own supply chain is stated rather than assumed.** Whether
each of the nineteen publishers signs their images becomes a fact the catalogue
records, and an honest answer to "is this stack signed end to end" is *mostly
not, and here is which*. That is a worse-sounding answer than silence and a much
better one than an implication.

**Revisit if** the container ecosystem's signing practice becomes near-universal,
at which point requiring a verified signature stops excluding most of it and the
unproven state can become a refusal.

## Related

- [ADR-0009](0009-action-pinning.md) — the same reasoning about mutable refs, applied to CI
- [ADR-0021](0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md) — the generated entry a digest is written into
- [F3](../../10-functional/features/f-extensibility/f3-stack-manifests.md) — `F3-R8` and `F3-R25`, the two halves this separates
- [F5](../../10-functional/features/f-extensibility/f5-plugin-catalogue.md) — catalogue signing, and what a signature vouches for
- [E1](../../10-functional/features/e-maintenance/e1-stack-updates.md) — `E1-R1`, the bundled stack's pinning rule this raises
- [L1](../../10-functional/features/l-release/l1-release-engineering.md) — `L1-R2`, the signing capability whose date this moves
- [plugin-manifest](../../20-architecture/contracts/plugin-manifest.md) — where a plugin's digest and tag are declared
