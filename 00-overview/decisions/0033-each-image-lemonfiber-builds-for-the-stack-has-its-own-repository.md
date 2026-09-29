# ADR-0033: Each image lemonfiber builds for the stack has its own repository, named for the service it runs

**Status:** Accepted
**Date:** 2026-09-29
**Decided:** 2026-09-29, by the maintainer, Wessel Verheij: accepted as proposed, with the names `lemonfiber-decline` and `lemonfiber-request-gate`.

## Context

[ADR-0029](0029-a-household-service-declines-an-invitation-with-one-key.md) and
[ADR-0032](0032-the-request-service-reaches-the-arrs-through-a-gate.md) each add a
service the stack runs from an image lemonfiber builds. Until now the stack has run
only images other projects publish:

- **The decline service** is published to the household network. It holds one
  Jellyfin API key, minted for it alone.
- **The request gate** publishes no port. It holds the Sonarr and Radarr keys and a
  Jellyfin key, and answers only Seerr.

ADR-0029 gives the decline service "its own repository, build and publish pipeline",
and ADR-0032 builds the gate "the way the decline service's is". Neither says how the
two relate to each other, to the repositories that already exist, or to the release
that ships them. Several facts shape the answer.

**The two services are two trust boundaries.** ADR-0032 already refuses to fold the
gate into the decline service at runtime: the decline service faces the household,
and adding the \*arr keys to it would put them behind a published port. They hold
different credentials, sit on different networks, and answer different callers. A
compromise of either is bounded by what that one holds (ADR-0029 §6, ADR-0032's
containment table).

**They share almost no code.**
- The decline service makes three fixed Jellyfin calls.
- The gate builds a fixed list of \*arr and Jellyfin calls from Seerr's requests.
- The core has no Jellyfin or \*arr client to reuse: its calls live inside
  `lemonfiber-core`, not in a library crate.
- What the two would share is scaffolding: reading a key file on each use, a health
  route, hashed-token comparison, a rate limit, structured logs. That is a few hundred
  lines.

**They change for different reasons.**
- A Seerr release that changes its \*arr calls changes the gate and nothing else.
- A Jellyfin line that changes how a policy is written changes the decline service.
- A vulnerability in one is patched, released and re-pinned without touching the
  other.

**The organisation already names its parts one way.**
- Governed product repositories are `lemonfiber-<role>`: `lemonfiber-web`,
  `lemonfiber-companion`, `lemonfiber-media-stack`, `lemonfiber-plugins`.
- Clients are `sdk-<language>`. Plugins, which are data a stranger could have
  written, are `plugin-<name>`.
- A bare name such as `request-gate` would read, in the organisation's listing, as
  a third-party project.

**How an image reaches an operator today.** The stack manifest pins every image by
the digest of its multi-architecture index, with the tag beside it
([ADR-0023](0023-a-pin-is-a-digest.md), `E1-R1`). `lemonfiber-media-stack` enters the
core as a submodule embedded at build time
([ADR-0005](0005-embedded-stack-assets.md)). So a lemonfiber-built image reaches an
operator when its digest is in the stack manifest at the commit the core's release
embeds. Nothing in the organisation publishes a container image yet.

## Decision

**Each image lemonfiber builds for the stack has its own repository, named
`lemonfiber-` followed by the service's id in the stack manifest. The image carries
the service id as its name. A repository builds exactly one image, publishes it by
digest, and proposes that digest to the stack. Nothing is shared between two such
repositories but the organisation's shared workflows, gates and hooks.**

### 1. Names

| Service id in `stack.toml` | Repository | Image |
|---|---|---|
| `decline` | `lemonfiber-decline` | `ghcr.io/lemonfiber/decline` |
| `request-gate` | `lemonfiber-request-gate` | `ghcr.io/lemonfiber/request-gate` |

One name, three places. An operator who reads `decline` in `lemonfiber status`, in
`docker ps` or in the stack manifest finds the repository by prefixing it, and the
reverse holds for a contributor. A future lemonfiber-built service follows the same
rule, and its id is chosen with that in mind.

### 2. What such a repository holds

- **One Rust binary crate.** The core's toolchain, lints, `cargo-deny` policy and
  coverage floor apply, through the same shared workflows (`Q-R` rows apply as they
  do to `lemonfiber`).
- **One Dockerfile.** A multi-stage build ends on a distroless static base as a
  non-root user, with no shell and no package manager.
- **Its recordings.** The upstream calls it makes are proved against every
  supported line by recordings, as [ADR-0028](0028-a-supported-major-is-data-proved-by-its-own-recordings.md)
  requires. CI runs them against the pinned upstream images, as ADR-0029 §9 and
  ADR-0032 ask.
- **What it needs from the stack, stated and not written.** The repository's
  documentation names the networks, mounts, capabilities and limits its ADR
  requires. The compose entry lives in `lemonfiber-media-stack`, which is the one
  place the stack is declared (ADR-0004), and that repository's CI holds the entry to
  what the service's ADR states.

### 3. Publishing

A signed tag `vX.Y.Z` on `main` is the only thing that publishes.

1. CI builds `linux/amd64` and `linux/arm64` and pushes both under one
   multi-architecture index.
2. The build attaches a software bill of materials and a build-provenance
   attestation.
3. The index is signed with the organisation's artefact-signing mechanism once it
   exists (ADR-0023 §6). Until then the image is published unsigned, and everything
   that reads it reports the signature as unproven, never as verified (ADR-0023 §4).
4. Nothing is published from a branch, and a tag is never moved.

### 4. Reaching the stack

Publishing opens a pull request on `lemonfiber-media-stack` that sets the service's
`tag` and `digest`. It is the same fan-out the contract uses to reach the SDKs.
That repository's CI checks that the digest resolves on both platforms, and that the
compose entry still carries the containment the service's ADR requires. The core
takes the stack through its submodule as it does for every other service. The
release that embeds it states the jump, as for any service (`E1-R2`).

### 5. No shared library, for now

The two repositories do not share a crate. The scaffolding they have in common is
small, and a shared library would put both trust boundaries' release and review on
one dependency: a change made for the gate would ship in the decline service's next
build, whether or not that service needed it. A third lemonfiber-built service
reopens this.

### 6. Governance

Each repository, like every other the specification governs:

- is listed in `30-repos/repos.toml` and has a page under `30-repos/`;
- adopts the shared hooks and gates through `shared/adoption.toml`;
- carries the organisation's rulesets and required checks;
- takes updates through Dependabot (ADR-0016), with every action pinned to a SHA
  (ADR-0009).

Its version is its own semver. The stack records which version of each it pins.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **One repository, two images** (`lemonfiber-stack-services`, a Cargo workspace building both) | It shares CI and tooling, which the shared workflows already give. What it adds is coupling: a workspace-wide dependency bump rebuilds and re-releases both, a review of the gate's call list sits beside the household-facing page, and "the only code that ever holds the \*arr keys" is no longer one repository an auditor can read end to end. The two are separated at runtime for their credentials, and separating their source keeps that boundary where it can be seen. |
| **Two crates in `lemonfiber`** (`crates/lemonfiber-decline`, `crates/lemonfiber-gate`) | The core is the operator's tool, a binary on the release train. These are long-running services in the household's stack. Building their images in the core puts container publishing and two more trust boundaries in its CI, and ties a gate fix for a Seerr change to the core's release. It also contradicts ADR-0029 §1 as written. |
| **Source in `lemonfiber-media-stack`** | That repository declares the stack and runs standalone. It is reviewed as YAML and TOML (ADR-0004), and has no Rust toolchain. Code in it would make a compose change and an image build one review, and the digest it pins would be of an image built from itself. |
| **A shared "service kit" crate from the start** | It serves two consumers with a few hundred lines. It becomes a third repository and a coupling point before anything has shown what is genuinely shared. |
| **Bare names** (`decline-service`, `request-gate`) | In the organisation's listing, they read as third-party projects beside `plugin-*`, and they drop the link to the service id that makes an image traceable to its source. |
| **Longer names** (`lemonfiber-invitation-decline`, `lemonfiber-seerr-gate`) | Each breaks the one-name rule, since the service id would differ, or names the current upstream (Seerr) in something meant to outlive it. |

## Consequences

### Positive

- Each credential's code lives in one repository, and a review, an audit or a CVE
  response reads exactly that.
- A change for one upstream releases one image.
- An operator traces a running container to its source by name alone.
- The pattern is fixed for any later lemonfiber-built service.

### Negative

- Two more repositories to govern: rulesets, adoption rows, pages, Dependabot.
- The small scaffolding is written twice.
- Until the signing mechanism lands, both images are published unsigned and reported
  as unproven.

### Neutral

- Release cadence is per image. What the operator runs is still decided in one
  place, the stack manifest the core embeds.

## Revisit if

- A third lemonfiber-built service appears, which reopens the shared library.
- The organisation adopts a registry other than GHCR.
- The signing mechanism of ADR-0023 §6 changes what a publish must attach.

## Related

- [ADR-0004](0004-four-repo-split.md), [ADR-0005](0005-embedded-stack-assets.md): the
  repository split and the embedded stack
- [ADR-0023](0023-a-pin-is-a-digest.md): the digest pin and the separate signature
- [ADR-0028](0028-a-supported-major-is-data-proved-by-its-own-recordings.md): the
  recordings each service's calls are proved by
- [ADR-0029](0029-a-household-service-declines-an-invitation-with-one-key.md),
  [ADR-0032](0032-the-request-service-reaches-the-arrs-through-a-gate.md): the two
  services
