# Repo: `lemonfiber-companion`

**Status:** Draft

The mobile companion app. PHP on NativePHP, Hippocratic 3.0.

**Implements:** area [N](../10-functional/features/README.md) — the fourth
surface, against the
[web API contract](../20-architecture/contracts/web-api.md), by way of
[`sdk-php`](sdk-php.md).

---

## What this repo is

A **native mobile application** for iOS and Android, built with
[NativePHP](https://nativephp.com) in **SuperNative** mode: Blade compiled to a
binary representation that SwiftUI and Jetpack Compose render directly. There is
no web view, no DOM and no JavaScript bridge
([ADR-0017](../00-overview/decisions/0017-the-companion-app-as-a-fourth-surface.md)).

It is **a fourth surface under [G1](../10-functional/features/g-ux/g1-interface-tiers.md)**,
not a companion in the weaker sense of a viewer. The parity rule applies: an
action reachable from a terminal is reachable here, subject to the two
qualifications ADR-0017 records — reachability is a reported condition, and
first-run setup does not cross the device boundary.

One application serves both audiences. The credential that signs in decides
which ([N3-R1](../10-functional/features/n-companion/n3-household-companion.md)).

## What it does not contain

**No API client.** It consumes [`sdk-php`](sdk-php.md), which owns that job
([ADR-0013](../00-overview/decisions/0013-an-sdk-owns-the-api-client.md)). A
second client here would be a second source of truth for the contract, which
`ARCH-R58` forbids.

**No way around the SDK.** Not "prefers the SDK" — the app issues no HTTP request
of its own at all
([N1-R16](../10-functional/features/n-companion/n1-companion-app.md)). Where the
SDK does not yet expose something a screen needs, **the work stops and the gap is
raised** against the SDK and the contract
([N1-R17](../10-functional/features/n-companion/n1-companion-app.md)). It is not
worked around, not fetched directly "just this once", and not approximated from a
neighbouring endpoint.

That rule is load-bearing for anyone — person or agent — building here
unsupervised. A blocked screen is a smaller problem than a fourth consumer the
contract does not know it has, and being blocked is a finding worth reporting
rather than a problem to solve locally.

**No business logic.** It renders the core's answers. A decision made here that
the core does not also make is the drift `G1-R2` exists to prevent.

**No second permission model.** What a household member may do is the core's
answer, rendered ([N3-R2](../10-functional/features/n-companion/n3-household-companion.md)).

**No generated contract of its own.** The envelope shapes arrive through the
SDK, already generated from `web-api.contract.json`
([ADR-0014](../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md)).

## What it owns

| | |
|---|---|
| Pairing, session exchange, and multi-stack handling | [N1](../10-functional/features/n-companion/n1-companion-app.md) |
| The operator's screens | [N2](../10-functional/features/n-companion/n2-operator-companion.md) |
| The household's screens | [N3](../10-functional/features/n-companion/n3-household-companion.md) |
| Device permissions, secure storage, app lock, notifications | [N4](../10-functional/features/n-companion/n4-native-integration.md) |

## Standards

Held to the same bar as [`sdk-php`](sdk-php.md), because it is the same language
and the same project:

- **PHP 8.5**, strict types throughout.
- **PHPStan** at the level `sdk-php` runs, with the same strict, deprecation and
  ergebnis rule sets.
- **Pest**, including its architecture plugin — the boundary rules above are
  tests, not conventions.
- **Pint** for formatting, **Rector** for upgrades, **composer-dependency-analyser**
  for unused and shadow dependencies.
- **Git hooks** under `.githooks`, installed by composer setting `core.hooksPath`.
  They run only the fast checks — a hook that takes a minute is one people turn
  off, and one that is off enforces nothing (`OPS-R51`).
- A **DCO** sign-off on every commit and a `Spec:` citation naming a requirement,
  enforced by the shared governance workflow every repository in this project
  calls ([`spec-check`](../50-governance/cross-repo-ci.md)).

## How it is laid out

The application is modular: a composition root holding nothing but bindings, and
modules under `app-modules/` that each declare what **kind** they are —
`kernel`, `capability`, `design`, `surface` or `adapter`. That declaration
generates the module's dependency rules, so a module added later is governed the
moment it exists rather than when somebody remembers to write its test.

Each module is a composer package with its own manifest, which is what makes the
SDK rule structural rather than advisory: `modules/sdk` is the only manifest
requiring `lemonfiber/sdk-php`, so a screen that names the SDK is a shadow
dependency and fails resolution. `N1-R16` stops being a rule a reviewer applies.

The architecture document in that repository lists every rule beside the
mechanism enforcing it, and a test reads that column and fails when the two
disagree — in either direction. A rule table that can quietly go out of date is
worse than none, because people stop reading it once they trust it.

## The decisions that shape it

| | |
|---|---|
| It is a fourth surface, reached over the network, rendering natively | [ADR-0017](../00-overview/decisions/0017-the-companion-app-as-a-fourth-surface.md) |
| A paired fingerprint decides which machine it will talk to | [ADR-0018](../00-overview/decisions/0018-trusting-a-stack-over-the-local-network.md) |
| A screen paints what it knows before it reaches the stack | [ADR-0019](../00-overview/decisions/0019-a-screen-paints-before-it-reaches-the-stack.md) |
| An action the stack did not receive did not happen | [ADR-0020](../00-overview/decisions/0020-an-action-the-stack-did-not-receive-did-not-happen.md) |

## It follows the main repos rather than gating them

**This repo carries no version of its own yet, and locks no goal on the release
train.** Area N is specified in full because the specification leads everywhere
in this project; the app is built against what the main repositories have already
shipped rather than the other way round.

So it tracks `main` and takes no releases while it catches up. When it has, it is
pinned with the rest of the repositories the way every other one is
([pins](../70-operations/releasing.md)), and from that point it moves on the
train like everything else.

What this deliberately avoids: a version manifest locking `N1`–`N4` would make
`1.0.0` — "everything specced is built" — wait on an application that is
following the core rather than leading it. The specification is not the thing
holding anything up here, and a manifest would make it look like it was.

## Distribution

Builds and signing run in **Bifrost**, NativePHP's cloud build service, rather
than on a machine holding distribution certificates.

That is a supply-chain surface this project did not previously have, and it is
named here rather than left in a workflow file: a signing identity that lives in
somebody else's cloud is a thing an operator of this project's own standards is
entitled to know about. `L1`'s attestation requirements reach it.

## Why PHP for a mobile app

The honest answer is that it is the same language as an SDK this project already
maintains to a high standard, so the app is written against a client that is
already tested rather than against a second one in a language nobody here is
holding to that bar.

The less honest answer would be that PHP is the natural choice for mobile. It is
not, and the decision is recorded with its trade-offs in
[ADR-0017](../00-overview/decisions/0017-the-companion-app-as-a-fourth-surface.md)
rather than presented as obvious.

## Related

- [`sdk-php`](sdk-php.md) — the client this consumes
- [`lemonfiber-web`](lemonfiber-web.md) — the other surface behind the same contract
- [`lemonfiber`](lemonfiber.md) — the core, and the API it serves
