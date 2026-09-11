# Repo: `lemonfiber-companion`

**Status:** Draft

The mobile companion app. PHP on NativePHP, Hippocratic 3.0.

**Implements:** area [M](../10-functional/features/README.md) — the fourth
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
which ([M3-R1](../10-functional/features/m-companion/m3-household-companion.md)).

## What it does not contain

**No API client.** It consumes [`sdk-php`](sdk-php.md), which owns that job
([ADR-0013](../00-overview/decisions/0013-an-sdk-owns-the-api-client.md)). A
second client here would be a second source of truth for the contract, which
`ARCH-R58` forbids.

**No business logic.** It renders the core's answers. A decision made here that
the core does not also make is the drift `G1-R2` exists to prevent.

**No second permission model.** What a household member may do is the core's
answer, rendered ([M3-R2](../10-functional/features/m-companion/m3-household-companion.md)).

**No generated contract of its own.** The envelope shapes arrive through the
SDK, already generated from `web-api.contract.json`
([ADR-0014](../00-overview/decisions/0014-one-generated-contract-for-every-sdk.md)).

## What it owns

| | |
|---|---|
| Pairing, session exchange, and multi-stack handling | [M1](../10-functional/features/m-companion/m1-companion-app.md) |
| The operator's screens | [M2](../10-functional/features/m-companion/m2-operator-companion.md) |
| The household's screens | [M3](../10-functional/features/m-companion/m3-household-companion.md) |
| Device permissions, secure storage, app lock, notifications | [M4](../10-functional/features/m-companion/m4-native-integration.md) |

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
- **Captainhook** for the same pre-commit guards.
- A **DCO** sign-off on every commit and a `Spec:` citation naming a requirement,
  enforced by the shared governance workflow every repository in this project
  calls ([`spec-check`](../50-governance/cross-repo-ci.md)).

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
