---
id: G11
title: The operator's web console
kind: feature
area: G
audience: operator
status: accepted
maturity: building
priority: P2
labels: [web, ux, extensibility, security]
requires: [G1, F14]
relates: [G10, F6, A7, N25, N9]
---

# G11 — The operator's web console

**Status:** Accepted · **Audience:** Operator · **Area:** G — Cross-cutting UX

---

## Purpose

The operator's side of the web surface, in a browser, held to what it shows and
asks for where the core's requirements leave that to the surface.

[G1](g1-interface-tiers.md) says every action is available from every surface and
that no surface implements behaviour of its own. The core's rows say what an act
takes and what a read carries; they do not say how a console draws a consent or
what it tells the operator afterwards. [G10](g10-household-web.md) says that for
the household's side of the same surface, and the companion says it for itself in
N. This page says it for the operator at a browser.

It holds a third-party plugin's grants: a credential of another service that
crosses to a plugin for a capability it fills
([F14](../f-extensibility/f14-every-part-is-a-plugin.md)).

## Behaviour

### Approving a grant

An install or update of a third-party plugin is read before it is agreed to, and
the reading names each credential of another service that would cross to it: the
setting it is held under, the service whose credential it is, and the capability
of the plugin's own it is for. No value is shown, because the reading carries
none.

Each grant has a switch of its own beside it, off until the operator turns it on.
Agreeing to the reading agrees to the plugin and to nothing that would cross to
it, as with a value a recipe would carry elsewhere and a privileged shape a
service would take. The yes carries each grant switched on, written exactly as
the reading names it. An update asks for every grant again, so one the plugin
already holds is switched off like any other until the operator turns it on.

### The grants a plugin holds

Each installed plugin lists the grants it holds, each by its setting, its
service, the capability it fills and when it was approved. The credentials panel
lists every grant again beside the credential it crosses, with the plugin it is
granted to, so either place answers *who holds this*.

### Ending a grant

A grant can be revoked. The revoke is read first, labelled as nothing ended yet:
the grant it would end and the plugin's services that would restart once the
credential is withdrawn. The yes carries the name that reading gave itself, and
the core refuses it where the grant has moved since.

Afterwards the console says whether the grant ended, which services restarted,
and the core's reason where they did not. It says that the plugin stays installed
with the capability the credential was for left unfilled, and that a value
already handed to the plugin is taken back only by rotating the credential.

### The operator alone

Grants, and revoking them, are drawn for the operator. A member signed in to the
same surface is shown none of it ([G10](g10-household-web.md)).

## Requirements

| ID | Requirement |
|----|-------------|
| **G11-R1** | Where an install or update of a third-party plugin names a credential of another service that would cross to it, the console's reading MUST show each one with the setting it is held under, the service whose credential it is and the capability of the plugin's own it is for, and never its value. The operator MUST approve each one apart from the offer, on a switch of its own that is off until turned on; agreeing to the offer MUST approve none of them, and the yes MUST carry each approved one exactly as the reading names it (`ARCH-R323`, `F14-R20`). Every update MUST ask again, and a grant the plugin already holds MUST NOT be taken as approved. Where the stack refuses the act for a grant left off, the refusal MUST be drawn in the stack's words. |
| **G11-R2** | The console MUST list, for each installed plugin, the grants it holds, each with the setting the credential is held under, the service whose credential it is, the capability it fills and when it was approved, and never a value (`ARCH-R323`). |
| **G11-R3** | The console MUST offer revoking each grant a plugin holds. The revoke MUST be read first, labelled as nothing ended yet, showing the grant it ends and the plugin's services it would restart; the yes MUST carry back the offer the stack named (`ARCH-R324`). Afterwards the console MUST show whether the grant was ended, the services that restarted and, where they did not, the stack's reason, and MUST say that the plugin stays installed and that rotating the credential is what takes back a value already handed (`ARCH-R324`). |
| **G11-R4** | A plugin's grants, and revoking them, MUST be shown to the operator alone and MUST NOT appear anywhere a member is shown (`G10-R9`). |
| **G11-R5** | The console's credentials panel MUST list every grant beside the credential it crosses, with the plugin it is granted to, the capability it is for and when it was approved, and never a value (`ARCH-R325`, `F14-R20`). |

## Notes

**The same promises as the companion's.** G11-R1 to G11-R4 say for the web
console what `N25-R21` to `N25-R24` say for the app, and G11-R5 what `N9-R12`
says for its credentials screen, so an operator meets one consent wherever they
are.

| Row | What the web API carries | Not carried |
|---|---|---|
| `G11-R1` | `install.would.granted[]`: `credential`, `of`, `for`; the same under `update.install`; `PLUGIN-46` where a crossing secret names no capability | The line the yes approves for each grant: a pair and a privileged shape carry their `approval`, and a grant carries none |
| `G11-R2` | `installed[].granted[]`: `credential`, `of`, `for`, `at` | — |
| `G11-R3` | `credentials-revoke` with `plugin` and `credential`; `revoked`: `agreement`, `ended`, `grant`, `restarts`, `unrestarted`; `PLUGIN-47` where no such grant is held | — |
| `G11-R5` | `grants[]`: `plugin`, `credential`, `of`, `for`, `at` | — |

## Related

- [G1](g1-interface-tiers.md) — every action from every surface
- [G10](g10-household-web.md) — the household's side of the same surface
- [F14](../f-extensibility/f14-every-part-is-a-plugin.md) — a third-party plugin's grant
- [A7](../a-getting-started/a7-credential-management.md) — the credentials the stack holds
- [N25](../n-companion/n25-a-plugin-after-it-lands.md) and [N9](../n-companion/n9-who-gets-in.md) — the same grants on the companion
