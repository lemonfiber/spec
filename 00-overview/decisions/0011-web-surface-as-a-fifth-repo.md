# ADR-0011: The web surface is a fifth repo behind the JSON contract

**Status:** Proposed
**Date:** 2026-08-22

## Context

M7 adds a third surface. Two v1 guarantees decide most of its shape before anyone
argues about frameworks.

**No surface may implement behaviour independently** ([G1-R2]) and **every action
must be available from every surface** ([G1-R1]). Together these say the web surface
is a *rendering* of the core, not a second product with its own opinions. The failure
mode they exist to prevent is the ordinary one: a web UI that grows a shortcut the
CLI does not have, and then two answers to the same question.

**The web UI is started explicitly and binds to loopback** ([G1-R5], [G1-R6]). It is
not a daemon. An operator runs `lemonfiber web`, a browser opens, and the process
ends when they are done.

Against that, [ADR-0004](0004-four-repo-split.md) fixed a four-repo split and named
`lemonfiber` as "Rust CLI/TUI". A web surface has to live somewhere, and none of the
four existing repos is obviously it.

The contested part is not *whether* to build it. It is where the boundary goes — and
whether the boundary is a **contract** or a **compiler**.

One thing that is not contested, and is worth writing down because it was nearly
decided by omission: the surface **writes**. [G1-R14] requires setup to be completable
from all three surfaces, and M7's exit criteria as first written said "read-only".
Both could not be true. Widening the milestone is the decision recorded here, and it
is what makes the security question below real rather than theoretical.

## Decision

**A fifth repo, `lemonfiber-web`, holding a static single-page application that
speaks to a local HTTP API served by the `lemonfiber` binary.**

| Piece | Where | Why there |
|-------|-------|-----------|
| The API | `lemonfiber` | It is the core's own answer, in the envelope `--json` already emits |
| The SPA | `lemonfiber-web` | Its own CI, its own component review, its own release cadence |
| The contract | `Envelope { api_version, kind, data }` | Already shipped, already versioned ([G1-R7]) |

**The boundary is the JSON contract**, which is the same one a script already
consumes. [G1-R2] then holds *by construction* rather than by discipline: the SPA
cannot implement behaviour, because it has no way to do anything except ask the core
and draw the answer.

**Live state arrives by server-sent events over the same gather the dashboard uses.**
Not a second gather — the same one. [G1-R12] requires concurrent surfaces to agree,
and two independent gathers are two chances to disagree. SSE is one-way and textual,
which fits a read-mostly view and keeps the action path plain HTTP.

**Writes are guarded before they exist.** A writable loopback API is reachable from
any page the operator visits: a page cannot *read* a cross-origin response, but it
can send a request the server acts on, and DNS rebinding defeats a naive origin
check. The CLI has no equivalent exposure — nothing a web page does reaches `argv`.
So the CSRF-relevant parts of [C6] move forward into `0.9.0` alongside the surface
they guard, by [OPS-R31] review. Accounts and LAN binding stay in `0.10.0`, because
those are what *widening* the surface needs; a strict origin check and a per-run
token printed by the CLI are what *having* it needs.

**The SPA is TypeScript, built with Vite, with Storybook for components.** The
framework is deliberately *not* decided here — it is chosen once the page sketches
show whether these pages mostly render state or are genuinely interactive, and that
is a smaller decision made better with evidence.

## Alternatives considered

**A crate in the existing workspace.** Assets embedded at build time, one repo, one
CI, one release, and the compiler catching drift instead of a versioned contract.
Rejected because it puts a Node toolchain inside a Rust workspace whose gates,
lints and coverage rules all assume Rust — and because component review and
Storybook want a cadence of their own. The contract we would be avoiding is one we
already ship and version for scripts.

**A submodule, as `media-stack` already is under [ADR-0005](0005-embedded-stack-assets.md).**
Independent design, one shipped artefact, no runtime contract. Genuinely close, and
the pattern is proven here. Rejected because the stack is *data* — it has no
runtime relationship with the binary — whereas the SPA and the API talk to each
other while running, and pretending otherwise hides the versioning question rather
than answering it.

**Server-rendered HTML from Rust.** No JS build, no second repo, no API surface.
Simplest to ship and impossible to drift. Rejected because Storybook and
component-driven design do not apply to it, and live state becomes hand-written
polling — but it is the alternative to revisit first if the contract proves more
expensive than the drift it prevents.

**A page reading JSON files the CLI writes, with no server.** Avoids binding a port
entirely. Rejected because it cannot show live state, which is exactly what the
milestone's exit criteria require.

## Consequences

- **A second CI to keep green**, and a versioned contract that can drift. `api_version`
  exists for this; the SPA must state which it speaks and fail visibly on a mismatch
  rather than rendering a wrong page.
- **`0.9.0`'s locked goals change**, which [OPS-R31] permits with review and an
  announcement. This is that record.
- **M7's exit criteria change** from "read-only" to a surface that can complete setup.
- **The API is a public surface** the moment it exists. It is the same envelope
  scripts already consume, so this mostly formalises what is already promised.
- **Two repos must be released together** when the contract changes. The version
  manifest already records embedded pins ([OPS-R35]); this adds one more.

## Revisit if

- The contract costs more than the drift it prevents — the honest signal is a change
  that has to be made twice in lockstep more than occasionally.
- The surface stops being read-mostly. SSE and plain HTTP suit a view; a genuinely
  interactive control panel would argue for a duplex channel.
- A second consumer of the API appears. That would strengthen the boundary rather
  than weaken it, and is the outcome that would make this decision obviously right.

[G1-R1]: ../../10-functional/features/g-ux/g1-interface-tiers.md
[G1-R2]: ../../10-functional/features/g-ux/g1-interface-tiers.md
[G1-R5]: ../../10-functional/features/g-ux/g1-interface-tiers.md
[G1-R6]: ../../10-functional/features/g-ux/g1-interface-tiers.md
[G1-R7]: ../../10-functional/features/g-ux/g1-interface-tiers.md
[G1-R12]: ../../10-functional/features/g-ux/g1-interface-tiers.md
[G1-R14]: ../../10-functional/features/g-ux/g1-interface-tiers.md
[C6]: ../../10-functional/features/c-trust/c6-web-security.md
[OPS-R31]: ../../70-operations/staging.md
[OPS-R35]: ../../70-operations/staging.md
