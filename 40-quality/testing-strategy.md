# Testing strategy

**Status:** Accepted

What must be tested, how, and why the architecture makes most of it possible
without Docker or a terminal.

**Satisfies:** the verification posture of
[P3](../00-overview/vision.md#p3--the-tool-proves-things-rather-than-assuming-them);
depends on [ARCH-R11](../20-architecture/component-model.md),
[ARCH-R12](../20-architecture/component-model.md),
[ARCH-R35](../20-architecture/platform-matrix.md).

---

## The shape

```mermaid
flowchart TD
    unit["Unit — most logic<br/>no Docker, no terminal, no network"] --> golden
    golden["Golden — command construction<br/>every form × every platform"] --> integ
    integ["Integration — trait-mocked<br/>Docker & service APIs faked"] --> e2e
    e2e["End-to-end — real Docker<br/>gated, needs credentials"]
```

Wide at the bottom, narrow at the top — because the architecture was built to
keep it that way. The core has no UI dependency (`ARCH-R11`), command
construction is pure (`ARCH-R12`), and platform is one fakeable component
(`ARCH-R35`). Each of those is a *testability* decision as much as a design one.

## Unit — the bulk

Most of `lemonfiber-core` is pure or trait-fronted, so most tests need nothing
external:

| Tested | How |
|--------|-----|
| Manifest parse + **every validation rule** | Fixtures: valid, and one-violation-each |
| Form closure + protocol intersection | Pure function over manifest + config |
| Config read/write, comment preservation | In-memory |
| Error → remedy mapping | Assert every variant carries a remedy |
| Drift three-way comparison | Table of (expected, actual, desired) → outcome |
| Platform-conditional behaviour | Faked platform, all four environments |

The manifest validator gets the same run-it-twice treatment as the
[comment gate](code-comments.md#proving-the-gate-fires): a valid manifest passes,
and a fixture-per-rule tree proves each rule catches *its own* violation and no
other. A validator that accepts everything passes its happy-path test and is
useless.

## Golden — command construction

The compose command builder is a pure function (`ARCH-R12`), so its output is
snapshot-tested:

```
tests/golden/
├── up_tv_macos.txt
├── up_tv_linux_native.txt
├── up_full_proxy_windows.txt
└── …  every form × every environment
```

`lemonfiber up tv --dry-run` on macOS must produce exactly the committed vector.
This covers the highest-value, highest-risk surface — *"does lemonfiber generate
the right `docker compose` invocation?"* — with **no daemon**, across platforms a
single CI machine can't otherwise exercise.

Because `--dry-run` and real execution share the path (`ARCH-R13`), the golden
tests cover both.

## Integration — mocked externals

Docker access is behind a trait; service clients are traits. Both are mocked:

| Tested | Mock |
|--------|------|
| Lifecycle orchestration, health-gating | Fake Docker reporting scripted states |
| Seed wiring, idempotency, partial failure | Fake service APIs |
| Doctor checks | Injected conditions |
| **VPN egress comparison logic** | Two fake `exec` results — matching and mismatching |

The VPN leak *logic* is testable without a VPN: feed the comparison two IPs and
assert it reports `verified`, `leaking`, or `killswitch-holding` correctly
(`C2-R1`). The *real* check needs a tunnel and lives in e2e.

## End-to-end — gated

Real Docker, real containers. **Not on every PR** — it needs a Docker daemon and,
for the full path, real provider credentials that cannot live in CI.

| Runs | When |
|------|------|
| Boot each form, assert health | CI with Docker available (no credentials) |
| Hardlink import, real files | CI with Docker |
| VPN leak test end-to-end | Gated job with test VPN credentials |
| Full pipeline (search→import) | Manual, M1 exit criterion |

What can't be automated is stated rather than pretended
([lemonfiber-media-stack CI](../30-repos/lemonfiber-media-stack.md#ci) draws the
same line): a green CI
does not mean the full acquisition path works, because CI has no Usenet account.

## What MUST be covered

A floor **and** a focus. Applicable code is covered 100% ([below](#coverage--100-where-it-applies)),
and on top of that these specific high-consequence paths are called out — because
a bare percentage guarantees lines ran, not that the *right* things were asserted:

| Must be tested | Because |
|----------------|---------|
| Every manifest validation rule, positively and negatively | A hole here ships a broken fork silently |
| VPN state classification | The one failure with off-machine consequences (`C2`) |
| Hardlink detection | Silent degradation otherwise (`C5`) |
| Secret redaction | A miss publishes a credential (`C4`, `A7`) |
| Drift preservation | A miss reverts the operator's work (`C9`) |
| Every error carries a remedy | Structural, but assert it (`G4`) |
| Command construction per platform | The core correctness surface |

## Coverage — 100% where it applies

Coverage **is** a gate — with a scope. Every line of **applicable** code is
covered, 100%, enforced in CI. "Applicable" is the logic the must-cover list lives
in: `lemonfiber-core` and command construction — the code that can actually be
wrong. What is excluded is excluded **explicitly, in the source**, so the number is
honest rather than inflated to hit a target:

| Excluded from the 100% (annotated in code) | Why |
|--------------------------------------------|-----|
| Generated code | Not ours to test |
| Trivial derivations — `Display`, `Debug`, `From`, plain getters | No branch to be wrong |
| Rendering — TUI draw code, web templates | Logic is tested; pixels are reviewed |
| `main.rs` / CLI wiring with no branching | Glue, exercised by the binary itself |
| Unreachable / exhaustiveness arms, platform stubs not on the runner | Cannot execute in the unit environment |
| e2e-only paths (real Docker, real VPN) | Gated separately; not counted in unit coverage |

Enforced by `cargo-llvm-cov` with a 100% threshold over the applicable set, and
surfaced in SonarCloud. A drop below 100% on applicable code **fails the PR**. The
must-cover list says *what* matters and that the right assertions exist; the gate
makes sure none of it silently rots uncovered.

The anti-pattern an earlier draft rightly warned about — coverage theater, tests
that touch trivial getters just to move a number — is avoided not by dropping the
gate but by **scoping** it: trivial code is excluded in the open, so 100% means
100% of the code that can hold a bug. Every exclusion is a reviewed line of source,
not a silent gap.

## What is deliberately not chased

- **A blanket percentage over *all* code.** Chasing a number across generated and
  trivial code rewards theater; the gate is scoped to applicable code (above), and
  the must-cover list is the qualitative bar on top of it.
- **UI pixel/layout tests.** Brittle and low-value; the TUI's *logic* is tested,
  its rendering is reviewed.
- **Testing the services themselves.** Sonarr's correctness is Sonarr's problem;
  our *integration* with it is ours.

## Secret hygiene in tests

Test fixtures use obviously-fake credentials. The [secret-scan](ci-cd.md) runs
over test code too — a real key pasted into a fixture is a leak regardless of
intent.

## Requirements

| ID | Requirement |
|----|-------------|
| **Q-R21** | Every manifest validation rule MUST have a positive and a negative test. |
| **Q-R22** | The validator MUST be tested against a fixture-per-rule tree; each rule MUST catch only its own violation. |
| **Q-R23** | Command construction MUST be golden-tested for every form on every platform. |
| **Q-R24** | Docker and service-API access MUST be trait-fronted and mockable. |
| **Q-R25** | VPN state classification MUST be unit-tested against matching and mismatching egress. |
| **Q-R26** | Secret redaction MUST be tested against known secret patterns. |
| **Q-R27** | End-to-end tests requiring credentials MUST be gated, and their absence from PR CI stated. |
| **Q-R28** | The must-cover paths MUST be tested — a passing coverage gate does not substitute for asserting the right behaviour. |
| **Q-R29** | Secret scanning MUST run over test code as well as production code. |
| **Q-R61** | Applicable code MUST reach 100% coverage, enforced as a merge gate (`cargo-llvm-cov`) and reported to SonarCloud. |
| **Q-R62** | The applicable set MUST be defined by explicit, reviewable in-code exclusions (generated, trivial derivations, rendering, CLI wiring, unreachable arms, e2e-only paths); coverage MUST NOT be inflated by testing trivial code to reach the number. |

## Related

- [code-standards.md](code-standards.md) — the posture this verifies
- [ci-cd.md](ci-cd.md) — where these run
- [component-model](../20-architecture/component-model.md) — the boundaries that make it testable
