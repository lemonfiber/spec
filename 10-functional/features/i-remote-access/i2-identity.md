---
id: I2
title: Household identity & single sign-on
kind: feature
area: I
audience: both
status: accepted
tracks: v2
priority: P1
labels: [security, household, verification]
relates: [I1, C6, D6, A7]
---

# I2 — Household identity & single sign-on

**Status:** Accepted · **Audience:** Both · **Area:** I — Remote access & identity

---

## Purpose

Give the household one account that works across the services, and give remote
access ([I1](i1-remote-access.md)) the authentication gate it requires before
anything is exposed to the outside world. A household member signs in once with
the media login they already have ([D6](../d-content/d6-household-identity.md));
the operator gets a single place to add, disable and rotate people, without
maintaining a separate password in every app.

## Behaviour

### One identity per household member, issued centrally

A self-hosted identity provider issues one identity per household member. That
identity is the authority the services trust, so adding or removing a person is
one change in one place rather than a sweep across six admin panels. The provider
is chosen from open-source, self-hostable options only — no proprietary or hosted
identity plane ever holds the household's accounts.

### Apps that support it authenticate directly

The media apps that speak a standard single-sign-on protocol — Jellyfin and the
request portal — authenticate against the provider directly. A member's browser
is redirected to the provider, they prove who they are, and they are returned to
the app with a session already established.

### Apps that don't are protected at the proxy

The \*arr and administrative apps have no native single-sign-on. They are not left
to their own local logins, and they are not exposed unauthenticated. Instead the
bundled reverse proxy enforces forward-authentication in front of them: a request
for an administrative route is intercepted, checked against the identity provider,
and only forwarded once an authenticated session is present. An app's lack of
protocol support therefore changes *how* it is guarded, never *whether* it is.

### The household sees one account, not the machinery

Single sign-on is an operator concern. A household member experiences exactly one
account — their existing media login ([D6](../d-content/d6-household-identity.md)) —
and never encounters the provider as a separate thing to register with, remember,
or manage. The operator's own administrative identity is distinct from a household
member's, so the surfaces a member can reach and the surfaces an operator can
reach are not the same account.

### Identity is configured as code

Members, groups and which routes require which identity are declared in
configuration, consistent with the project's declarative ethos — not clicked into
each app's database where the next operator cannot find them. Provisioning the
provider, enrolling a member, and issuing or rotating a credential are each
reachable non-interactively so the scripter is never forced through a UI.

### It proves the gate closes and opens

Configuring authentication is not the same as authentication working. The tool
drives a real login round-trip and asserts the redirect-to-provider-then-back flow
completes and a session or token is actually issued. Separately, it asserts that a
protected administrative route **refuses an unauthenticated request and admits an
authenticated one** — proving the gate empirically rather than assuming the proxy
rule took.

## States

| State | Meaning |
|-------|---------|
| `unconfigured` | No identity provider set up; remote exposure of protected surfaces is refused |
| `active` | Provider up; direct-SSO apps and forward-auth routes both authenticating |
| `direct-only` | Provider up and SSO apps working, but a forward-auth route is unverified or misconfigured |
| `provider-down` | Identity provider unreachable; protected routes fail closed |
| `degraded` | Configured but the last login or gate proof failed; names which check failed |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| App has no SSO support | Protect it with forward-authentication at the proxy; it MUST NOT be left reachable without a gate. |
| Identity provider unreachable | Fail closed — protected routes deny access rather than falling open to an unauthenticated pass-through. |
| Household member vs operator identity | Keep them distinct; a member's identity MUST NOT reach an administrative surface, and the member never sees the operator account. |
| Member already has a media login | Reuse it as the single account ([D6](../d-content/d6-household-identity.md)); do not force a second registration. |
| Direct-SSO app supports the protocol but is misconfigured | Do not silently fall through to its local login; surface the misconfiguration and treat the route as unverified. |
| Password or identity rotation | Route it through the same secret-management path as every other credential ([A7](../a-getting-started/a7-credential-management.md)); a rotated credential invalidates prior sessions. |
| Forward-auth rule present but never exercised | Prove it with a live unauthenticated-then-authenticated request pair; a rule that exists but was never tested is not counted as protecting the route. |
| Remote access requested before identity is configured | Refuse to expose the surface until the gate exists ([I1](i1-remote-access.md), [C6](../c-trust/c6-web-security.md)); never warn-and-proceed. |
| Session or token expiry | Re-authenticate through the provider rather than extending indefinitely; expiry is enforced, not cosmetic. |
| Config declares a member the provider does not have | Reconcile toward the declared configuration and report the drift, rather than trusting stale provider state. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **I2-R1** | Household identity MUST be issued by a self-hosted, open-source identity provider, and MUST NOT depend on a proprietary or hosted identity plane. |
| **I2-R2** | The provider MUST issue exactly one identity per household member, usable across the services that trust it. |
| **I2-R3** | Apps that support a standard single-sign-on protocol MUST authenticate against the provider directly. |
| **I2-R4** | Administrative apps with no native single-sign-on MUST be protected by forward-authentication at the bundled reverse proxy, and MUST NOT be exposed unauthenticated. |
| **I2-R5** | A household member MUST experience a single account — their existing media login — and MUST NOT be required to register with or manage the provider separately. |
| **I2-R6** | A household member's identity MUST NOT grant access to any administrative surface; operator and member identities MUST be distinct. |
| **I2-R7** | Members, groups and route-to-identity mappings MUST be file-configured as code, not held only in an app's local store. |
| **I2-R8** | The tool MUST drive a real login round-trip and assert that the redirect-to-provider-then-authenticated-back flow completes and a session or token is issued — a present configuration MUST NOT be reported as working authentication. |
| **I2-R9** | The tool MUST assert that a protected administrative route refuses an unauthenticated request and admits an authenticated one. |
| **I2-R10** | If the identity provider is unreachable, protected routes MUST fail closed and MUST NOT fall through to unauthenticated access. |
| **I2-R11** | Remote exposure of a protected surface MUST be refused until authentication is configured ([I1](i1-remote-access.md), [C6](../c-trust/c6-web-security.md)). |
| **I2-R12** | Credentials and identities MUST be rotatable through the same secret-management path as other secrets ([A7](../a-getting-started/a7-credential-management.md)), and rotation MUST invalidate prior sessions. |
| **I2-R13** | Provider provisioning, member enrolment, and credential issue and rotation MUST each be reachable non-interactively. |
| **I2-R14** | A failed login proof or gate proof MUST be distinguished from success, and each failure MUST carry a remedy ([G4](../g-ux/g4-error-model.md)). |

## Related

- [I1 Remote access for the household](i1-remote-access.md) — the exposure this authentication gates
- [D6 Household identity](../d-content/d6-household-identity.md) — the single account a member actually experiences
- [C6 Web UI security & binding policy](../c-trust/c6-web-security.md) — what may be exposed once a gate exists
- [A7 Credential management](../a-getting-started/a7-credential-management.md) — the rotation path identity secrets share
