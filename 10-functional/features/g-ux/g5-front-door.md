# G5 — The front door

**Status:** Accepted · **Audience:** Both · **Area:** G — Cross-cutting UX

---

## Purpose

Answer, with exactly one answer, the question *"what link do I send my partner?"*

The stack presents at least four plausible entry points: Homepage (a dashboard of
everything), Seerr (where you ask for things), Jellyfin (where you watch),
and lemonfiber's own web UI (where you administer). Without a decision, the
operator improvises — usually by sending several links with an explanation, which
is precisely the complexity this product exists to remove.

Nothing else in the catalogue picks one. This feature does.

## Behaviour

### Two doors, one per audience

| Audience | Front door | Why |
|----------|-----------|-----|
| **Household** | **Seerr** | Where you ask for things *and* the link onward to watching. Requires an account they already have. |
| **Operator** | **lemonfiber** (TUI or web UI) | Everything operational, one place |

Seerr rather than Jellyfin for the household is the non-obvious call.
Jellyfin is where they watch, but Seerr is where they *start* — it's the
place a request begins, it links to Jellyfin for playback, and it shows the status
of what they asked for. Sending someone to Jellyfin leaves them with no way to
ask for anything.

### Homepage is the operator's index, not a front door

Homepage links every service and shows live status — genuinely useful to the
operator, and meaningless to a household member, who should never see qBittorrent
exists.

It's an operator convenience, not an entry point, and is never given to the
household.

### The invitation carries the right link

[Invitations](../d-content/d6-household-identity.md) contain the household front
door and nothing else — the address, a QR code, and what to do on arrival. The
operator doesn't have to decide what to send, because lemonfiber decides.

### The address is stable and shown

The household front door is a LAN address, and lemonfiber shows it prominently —
after setup, on the dashboard, and in invitations. Where mDNS makes a friendly
name available, that's preferred over a raw IP, since IPs change and a broken
bookmark is a support request.

### Configuration reflected honestly

If Seerr isn't running, there is no household front door, and lemonfiber says
so rather than pointing at something absent. In a library-only configuration
Jellyfin becomes the household door — there's nothing to request.

### The operator's door never leads to the household's

lemonfiber's UI links out to services for convenience; household surfaces never
link back to administration. A household member following links should never
arrive somewhere they can change the stack's behaviour.

## States

| State | Meaning |
|-------|---------|
| `established` | Household front door running and reachable |
| `library-only` | Jellyfin is the household door; no request surface |
| `none` | No household-facing services; operator-only configuration |
| `unreachable` | Front door configured but not currently responding |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Seerr not in the active form | No household front door. Say so; don't point at Jellyfin as a substitute without explaining the difference. |
| Library-only configuration | Jellyfin is the door; invitations reflect that. |
| Host IP changes | Prefer an mDNS name where available; detect the change and update what's shown. |
| mDNS unavailable on the network | Fall back to the IP, and note that it may change. |
| Household member bookmarks Jellyfin directly | Fine. The front door is a starting point, not a gate. |
| Operator wants a different front door | Configurable, with the consequence stated. |
| Caddy overlay active | The front door becomes the friendly hostname; invitations use it. |
| Front door unreachable from a device | Distinguish "service down" from "device can't reach the network". |
| Household member finds an admin service | Loopback binding ([C6](../c-trust/c6-web-security.md)) means they can't. If they can, that's a policy violation and MUST be reported. |
| Multiple households or address ranges | Out of scope; a single LAN is assumed. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **G5-R1** | Exactly one household front door MUST be defined at any time. |
| **G5-R2** | Seerr MUST be the household front door where a request surface exists. |
| **G5-R3** | In a library-only configuration, Jellyfin MUST be the household front door. |
| **G5-R4** | Where no household-facing service is running, lemonfiber MUST state that there is no front door rather than substituting one silently. |
| **G5-R5** | Homepage MUST NOT be presented as a household front door. |
| **G5-R6** | Invitations MUST contain the household front door address and nothing else. |
| **G5-R7** | The front door address MUST be shown after setup, on the dashboard, and in invitations. |
| **G5-R8** | A friendly mDNS name MUST be preferred over a raw IP where available. |
| **G5-R9** | Where only an IP is available, lemonfiber MUST note that it may change. |
| **G5-R10** | Household-facing surfaces MUST NOT link to administrative surfaces. |
| **G5-R11** | A change of host address MUST be detected and reflected. |
| **G5-R12** | The front door MUST be configurable, with consequences stated. |
| **G5-R13** | "Service unreachable" MUST be distinguished from "network unreachable". |

## Related

- [D4 Household request flow](../d-content/d4-request-flow.md) — what's behind the door
- [D6 Household identity](../d-content/d6-household-identity.md) — invitations
- [G6 Client apps](g6-client-apps.md) — where they go next
- [C6 Web security](../c-trust/c6-web-security.md) — the binding tiers underneath
