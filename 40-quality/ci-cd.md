# CI/CD

**Status:** Accepted

The pipeline, the release process, and the checks that gate a merge.

**Satisfies:** [roadmap M6](../00-overview/roadmap.md#m6--release-engineering),
[E2](../10-functional/features/e-maintenance/e2-self-update.md),
[GOV-R](../50-governance/cross-repo-ci.md) enforcement.

---

## PR pipeline — `lemonfiber`

```mermaid
flowchart LR
    pr[PR] --> spec[spec-check]
    spec --> fmt[rustfmt]
    fmt --> lint[clippy strict]
    lint --> arch[arch tests]
    arch --> unit[unit + golden]
    unit --> integ[integration mocked]
    integ --> sec[secret scan + cargo-deny]
    sec --> e2e{Docker available?}
    e2e -->|yes| boot[boot forms]
    e2e -->|no| done[pass]
    boot --> done
```

Ordered cheapest-first so a formatting failure doesn't wait on a compile. Every
stage blocks merge.

| Stage | Gate |
|-------|------|
| `spec-check` | Citation present, resolves, spec merged first ([GOV-R](../50-governance/cross-repo-ci.md)) |
| `rustfmt` | Formatting (`Q-R19`) |
| `clippy` | The full strict set; warnings are errors (`Q-R12`) |
| arch tests | Boundaries, no `#[allow]` in `src/`, comment policy (`Q-R13`, `Q-R7`) |
| unit + golden | Logic and command construction (`Q-R23`) |
| integration | Mocked Docker and service APIs |
| secret scan | No credential in any tracked file |
| `cargo-deny` | Licences, advisories, banned/duplicate deps |
| e2e (conditional) | Boot forms where Docker is present |

## The comment gate in CI

The [comment policy](code-comments.md) runs as an arch test, and — critically —
against its **fixture tree** (`Q-R7`): it must find each planted violation and
pass the compliant control. A comment gate that only runs over production source
passes vacuously on a young repo. Running it over deliberate violations is what
proves it still works.

## `cargo-deny`

Supply chain is a real threat ([security](security.md)), enforced not exhorted:

| Check | Fails on |
|-------|----------|
| `advisories` | A dependency with a known RUSTSEC advisory |
| `licenses` | A dependency licence outside the allow-list |
| `bans` | A banned crate, or a **telemetry-carrying** one (`G8-R11`) |
| `sources` | A dependency from an unapproved registry |

`G8-R11` — dependencies must not introduce telemetry — is checked here rather than
hoped for.

## Secret scanning

Runs over **all** tracked files including tests (`Q-R29`). A real key in a fixture
is a leak whatever the intent. This is defence-in-depth behind the allow-list
redaction ([C4](../10-functional/features/c-trust/c4-support-bundle.md)) — the
redaction protects the operator's secrets; this protects the project's.

## Release — `cargo-dist`

A tagged release on `lemonfiber` triggers the three-platform build:

```mermaid
flowchart TD
    tag["tag v0.4.0"] --> build[cargo-dist build matrix]
    build --> mac["macOS<br/>aarch64 + x86_64"]
    build --> lin["Linux<br/>gnu + musl"]
    build --> win["Windows<br/>x86_64"]
    mac & lin & win --> art[Signed artifacts + checksums]
    art --> gh[GitHub Release]
    art --> tap[Regenerate homebrew-tap formula]
    art --> inst[Shell + PowerShell installers]
```

| Output | For |
|--------|-----|
| Per-platform archives + checksums | Direct download, and every installer |
| `homebrew-tap` formula | `brew` ([homebrew-tap](../30-repos/homebrew-tap.md)) |
| `install.sh` / `install.ps1` | `curl \| sh`, `irm \| iex` |
| Signed release | Integrity |

The `web-ui` build runs here, at release time — the only non-Rust toolchain, and
an end user never sees it (`ARCH-R19`).

## Real cross-platform testing

Not "it compiles" — actually run. The release matrix builds all targets; a
smoke-test job **runs** the binary on macOS, Linux and Windows (`roadmap M6`
exit). A binary that builds for Windows and panics on first launch has been
tested for the wrong thing.

## `media-stack` and `homebrew-tap` pipelines

- **`media-stack`** — `spec-check`, then the structural checks in its
  [repo spec](../30-repos/media-stack.md#ci). No stack boot in CI (no
  credentials).
- **`homebrew-tap`** — `spec-check` and `brew audit` (configured to accept the
  non-SPDX licence). Mostly receives generated commits.

## Branch protection

All four repos: required checks must pass, `spec-check` among them, before merge
(`roadmap M0.5`). The [override](../50-governance/overrides.md) bypasses
`spec-check` **only**, never the build, tests, or review (`GOV-R19`).

## Requirements

| ID | Requirement |
|----|-------------|
| **Q-R30** | PR CI MUST run spec-check, format, strict clippy, arch tests, unit, golden, integration, secret scan and `cargo-deny`, all blocking. |
| **Q-R31** | The comment and boundary arch tests MUST run against their fixture trees, not only production source. |
| **Q-R32** | `cargo-deny` MUST fail on advisories, disallowed licences, banned crates, and telemetry-carrying dependencies. |
| **Q-R33** | Secret scanning MUST cover all tracked files. |
| **Q-R34** | Releases MUST build macOS (arm64 + x86_64), Linux (gnu + musl) and Windows, with checksums. |
| **Q-R35** | The release MUST regenerate the Homebrew formula and produce shell and PowerShell installers. |
| **Q-R36** | A release smoke test MUST run the binary on all three platforms, not merely build it. |
| **Q-R37** | All four repos MUST require passing checks before merge; the override MUST bypass only spec-check. |

## Related

- [testing-strategy.md](testing-strategy.md) — what the test stages run
- [security.md](security.md) — why `cargo-deny` and secret scanning matter
- [50-governance/cross-repo-ci.md](../50-governance/cross-repo-ci.md) — spec-check
- [roadmap M6](../00-overview/roadmap.md#m6--release-engineering)
