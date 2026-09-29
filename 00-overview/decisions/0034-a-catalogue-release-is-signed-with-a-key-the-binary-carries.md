# ADR-0034: A catalogue release is signed with a key pair, and lemonfiber carries the public half

**Status:** Accepted
**Date:** 2026-09-29
**Decided:** 2026-09-29, by the maintainer, Wessel Verheij: a cosign P-256 key pair, chosen over Sigstore keyless signing and minisign.

## Context

[ADR-0023](0023-a-pin-is-a-digest.md) decides that artefact signing is one capability
with two consumers — the plugin catalogue and the release pipeline — and that the
earlier consumer sets its date (§6). It does not choose the mechanism. `F5-R3` asks
that catalogue releases be signed and that a signature which does not verify be
refused, and it is locked in the version that introduces the catalogue, so the choice
cannot wait for `L1-R2`.

Three facts constrain it.

**Verification happens on the operator's machine, with nothing else running.** The
account of what leaves that machine is a closed list ([G8](../../10-functional/features/g-ux/g8-privacy.md)),
and every entry on it is a request lemonfiber has a reason to make. A verifier that
consults a transparency log or a certificate authority adds a request whose only reason
is the verifier.

**lemonfiber already verifies one kind of signature.** An image's publisher may sign it
with cosign, and `plugin provenance` checks a P-256 ECDSA signature over the image's
digest against a key the operator supplies. A second algorithm would be a second
verifier to keep correct.

**The catalogue has one maintainer and no infrastructure.** It is a repository, a CI
workflow and a release page ([`30-repos/lemonfiber-plugins.md`](../../30-repos/lemonfiber-plugins.md)),
and the key has to live somewhere that set-up already has.

## Decision

1. **A catalogue release is a tag in `lemonfiber-plugins` whose release carries two
   assets:** `index.json`, which maps each plugin id to its origin, the revision the
   catalogue reviewed and the digest of the manifest at that revision, and
   `index.json.sig`, a cosign signature over exactly those bytes. The index is what was
   reviewed, so it is what is signed (`REPO-R57`).

2. **The signature is a cosign P-256 key-pair signature.** The private key is held only
   as the `lemonfiber-plugins` Actions secret `CATALOGUE_SIGNING_KEY`, with its password
   as `CATALOGUE_SIGNING_PASSWORD`. The release workflow signs, and nothing else reads
   either secret.

3. **lemonfiber carries the public key and verifies offline.** The key is a constant
   compiled into the binary. Installing by name fetches the index and its signature from
   the release, verifies one against the other with the key the binary carries, and only
   then resolves the name. Nothing else is asked of anybody: no log, no certificate
   authority, no key server.

4. **A signature that does not verify is refused**, and so is an index with none, for an
   install by name. An index is the catalogue's claim to have reviewed something; an
   unverifiable claim is worse than none (ADR-0023 §5). Installing from a named source
   needs no index and is untouched (`F5-R4`, `F5-R10`).

5. **A key is replaced by a lemonfiber release that carries the new one.** There is no
   revocation list and no callback (ADR-0023 §7). A binary verifies against the key it
   was built with; an operator on an older binary installs by name from releases that
   key signed, and from anywhere by naming the source.

6. **The release pipeline uses the same mechanism with its own key.** One mechanism, two
   keys: a compromise of the catalogue's signing key must not let anybody sign a
   lemonfiber binary, and the reverse. `L1-R2` records its key when it delivers.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Sigstore keyless signing** (an OIDC identity, a short-lived certificate, a transparency-log entry) | No key to hold, which is its real advantage. Verifying it on the operator's machine means either asking the transparency log — a request on the closed list whose only reason is the verifier — or carrying a trust root and an identity policy that lemonfiber would have to keep current. The catalogue gains nothing it needs from either. |
| **minisign / Ed25519** | A sound, small scheme, and a second algorithm beside the P-256 verification lemonfiber already has for images. Two verifiers for one capability is the drift ADR-0023 §6 set out to avoid. |
| **SSH signatures** (`ssh-keygen -Y`) | Familiar from signed commits, and a third format with no verifier here and no signing tool the release workflow already uses. |
| **Signed git tags only** | Signs a commit of the catalogue repository rather than the index an operator resolves through, so what is verified is not what is used — and verifying it needs the repository's history on the operator's machine. |

## Consequences

**The catalogue has a release workflow and two secrets.** The maintainer generates the
key pair and sets both secrets; nobody else can, and the workflow fails rather than
publishing an unsigned index when they are absent.

**The public key is a constant in lemonfiber's source.** A binary built before the key
exists carries a placeholder that verifies nothing, so every install by name from it is
refused as unverifiable rather than accepted.

**Installing by name is two new requests on the closed list**, both made only when an
operator installs by name: the index and its signature, from the catalogue's release. A
named git source is a third, made only when an operator names one (`G8-R3`).

## Related

- [ADR-0023](0023-a-pin-is-a-digest.md) — one signing capability with two consumers; this chooses it
- [F5](../../10-functional/features/f-extensibility/f5-plugin-catalogue.md) — `F5-R3`, `F5-R14`: signed releases, and resolving a name only through a verified index
- [L1](../../10-functional/features/l-release/l1-release-engineering.md) — `L1-R2`, the second consumer
- [G8](../../10-functional/features/g-ux/g8-privacy.md) — the closed list the new requests join
- [`30-repos/lemonfiber-plugins.md`](../../30-repos/lemonfiber-plugins.md) — `REPO-R57`, what the signature covers
