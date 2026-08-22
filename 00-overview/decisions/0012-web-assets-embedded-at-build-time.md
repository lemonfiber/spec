# ADR-0012: The web surface ships inside the binary, as a pinned submodule of built assets

**Status:** Proposed
**Date:** 2026-08-23

## Context

[ADR-0011](0011-web-surface-as-a-fifth-repo.md) put the web surface in its own repo behind
the JSON contract, and deliberately left one question open: **how the built app reaches an
operator's machine.** It has to be answered before either side is built, because it decides
what a release is.

Three facts constrain it.

**The install story is one binary.** M10 ships via cargo-dist and a Homebrew tap. `v0.8.0`'s
artefacts are 3.0–3.5 MB compressed per platform, and what an operator downloads is a single
file that then works.

**There is already a precedent for exactly this shape.**
[ADR-0005](0005-embedded-stack-assets.md) makes the media stack a git submodule pinned to a
tag, embedded with `include_dir!`, with `build.rs` validating `schema_version` **at compile
time**. It costs 396 KB today and has caused no trouble.

**Size is not the deciding factor, and it would be dishonest to pretend otherwise.** A built
app with its embedded typefaces lands near 200–250 KB, so embedding grows a 3.1 MB download
by roughly 3–5%. That is small enough that it does not decide anything on its own — and it
stays small across framework choices, since even the heaviest runtime is tens of kilobytes
against a multi-megabyte binary.

What actually decides it is **what a version means**. If the binary and the app ship
separately, then "lemonfiber 0.9.0" names two things that can be installed in combination,
and the `api_version` mismatch that [ADR-0011] designed for stops being a rare accident and
becomes an ordinary Tuesday.

The one real objection to embedding is toolchain contamination: if building `lemonfiber`
required Node, every Rust contributor would pay for a surface they may never touch.

## Decision

**`lemonfiber-web` publishes built assets at a tag. `lemonfiber` carries them as a pinned
submodule and embeds them with `include_dir!`, exactly as it already does for the stack.**

```
lemonfiber/
├── assets/media-stack/     # submodule, pinned      (ADR-0005)
├── assets/web/             # submodule, pinned      (this ADR)
├── build.rs                # validates schema_version AND api_version, at COMPILE TIME
└── src/web/embedded.rs     # include_dir!("assets/web")
```

Three consequences follow, and each one answers an objection:

**No Node in the Rust build.** The submodule contains *output*, not source — the app is
compiled in its own repo's CI and the result is what gets tagged. `cargo build` sees files.
A contributor fixing a Rust bug never installs npm.

**Drift becomes a compile error.** `build.rs` already refuses to build when the stack's
`schema_version` disagrees with the binary. The app declares the `api_version` it speaks, and
the same check applies. A mismatched pair cannot be released, rather than being detected by a
user seeing a wrong page.

**Development does not go through the submodule.** `lemonfiber web --dev` serves from a
running Vite dev server instead of the embedded copy, so the inner loop stays hot reload.
The embedded path is what ships, not what is worked in.

## Alternatives considered

**Ship the app as a second artefact.** A small binary, and the UI updates without a
`lemonfiber` release — genuinely attractive while the surface is changing fast. Rejected
because it makes a mismatched pair an ordinary state rather than an error: two things to
install, two things to version, two things a support request has to establish. It also gives
up the offline and air-gapped install, which a self-hosted tool should keep, and it means
new packaging work in the Homebrew tap and cargo-dist for a saving of ~200 KB.

**Vendor the built assets directly into the `lemonfiber` repo** — no submodule, just
committed files. Simpler to clone, and no submodule footguns. Rejected because it puts
generated output under review in the consuming repo and makes every UI change a diff of
minified bundles in `lemonfiber`'s history. The submodule keeps the pin without keeping the
bytes.

**Fetch the app at runtime on first run.** Keeps the binary smallest and allows the UI to
update independently. Rejected outright: it makes first run require the network, introduces a
download the operator did not ask for, and adds a supply-chain surface to a tool whose entire
proposition is that it verifies rather than trusts.

**Build the app from source during `cargo build`.** One repo state, always consistent.
Rejected because it is the toolchain contamination named above — Node becomes a build
dependency of the Rust project for everyone.

## Consequences

- **A UI change requires a `lemonfiber` release to reach operators.** This is the real cost,
  and it is deliberate: it is the same cost the stack already pays, and it buys a version
  number that means one thing.
- **Two submodules to bump**, with the same tag-pinning discipline as the stack.
- **`lemonfiber-web` CI must produce a reproducible build artefact**, since the tag is what
  gets embedded — its output is a release artefact, not a preview.
- **The version manifest gains a third pin** alongside `schema_version` and the stack
  ([OPS-R35](../../70-operations/staging.md)).
- **Binary grows by roughly 200–250 KB**, about 3–5% of the current download.

## Revisit if

- The web surface starts changing far faster than the binary, so that lockstep releases
  become the thing slowing the project down — that is the honest signal that separate
  artefacts were right.
- A second consumer needs the built assets without the binary.
- The embedded size stops being negligible against the binary, which would mean the app has
  grown into something this decision did not anticipate.
