# J9 — Getting the household watching

**Status:** Accepted · **Audience:** Both

**Exercises:** [D6](../features/d-content/d6-household-identity.md) ·
[D4](../features/d-content/d4-request-flow.md) ·
[G5](../features/g-ux/g5-front-door.md) ·
[G6](../features/g-ux/g6-client-apps.md)

---

## Why this journey is as important as J1

[J1](j1-first-run.md) is the operator getting to a working stack. **J9 is
everyone else getting value from it** — and for most households that's the point
of the exercise.

It's also where the product is judged by people who never chose it. A partner who
finds it confusing doesn't file an issue; they go back to a streaming
subscription, and the operator quietly stops maintaining the stack.

## The operator's half

```
$ lemonfiber invite ana

  What should Ana be able to see?
    ● Everything
    ○ Films and TV only
    ○ Age-limited  →  [12 ▾]

  ✓ invitation created

  Send this link — expires in 48 hours:
  http://mediabox.local:5055/invite/7f3a…

  ▄▄▄▄▄▄▄  ▄ ▄▄  ▄▄▄▄▄▄▄
  █ ▄▄▄ █ ▀█▄▀▄  █ ▄▄▄ █     [QR code]
  █ ███ █ █ ▄▀▄  █ ███ █
  ▀▀▀▀▀▀▀ ▀ ▀ ▀  ▀▀▀▀▀▀▀
```

Two things the operator never does: **choose someone else's password**, and
decide which of four URLs to send.

## Ana's half

She opens the link, sets her own password, and lands at **Jellyseerr**.

That's the front door (`G5-R2`), and choosing it over Jellyfin is the
non-obvious call. Jellyfin is where she *watches* — but it's where she
*finishes*, not where she *starts*. Send someone to Jellyfin and they can watch
what already exists and have no way to ask for anything; their next move is to
ask the operator in person, which is precisely the interruption the stack was
installed to remove.

Jellyseerr is where a request begins, shows its status, and links onward to
playback. One door, and it's the one that closes the loop.

## One account, not two

Ana's Jellyfin account authenticates her to Jellyseerr as well (`D6-R1`,
`D1-R7`). She has one credential for asking and watching.

This is one API call at seed time, and it's the difference between a household
member having one login or two.

## The loop closing

```
Ana requests "Dune Part Two"          she sees: request received
        ↓
Auto-approved (within quota)          she sees: approved
        ↓
Radarr searches, grabs, imports       she sees: processing
        ↓
Jellyfin scans                        she sees: ready to watch ↗
```

The failure mode to avoid is silence. A request disappearing into nothing is read
as being ignored, and produces the in-person follow-up the system exists to
prevent (`D4-R2`, `D4-R3`).

Jellyseerr sends these; lemonfiber's job is ensuring it's configured to.

## Getting onto a television

The last step is outside lemonfiber's control and is where a successful setup can
still end in "it doesn't work" — usually attempted by the least technical person
in the house, on a TV remote.

| Device | Guidance |
|--------|----------|
| Phone, tablet | Official Jellyfin app |
| Android TV, Fire TV | Official app — the common living-room case |
| Apple TV | Official app available |
| Older smart TV | Weakest area — suggest a streaming stick or casting |
| **Any browser** | **Always works, nothing to install** (`G6-R2`) |

The browser fallback means nobody is ever fully blocked, whatever their TV runs.

The QR code matters here too: the recipient is usually holding the phone they'll
watch on, and typing a LAN address and password with a TV remote is exactly the
friction that makes people give up.

## What Ana never sees

She has no lemonfiber account and no lemonfiber URL (`D4-R9`). She cannot reach
Sonarr, qBittorrent, or anything administrative — those bind to loopback
(`C6-R1`), so they're unreachable from her device by construction rather than by
her not knowing the address.

## Where it goes wrong

| Situation | Behaviour |
|-----------|-----------|
| Invitation expires unused | Re-issuable without redefining the member (`D6-R13`) |
| Ana already has a Jellyfin account | Detected; Jellyseerr access granted rather than a duplicate created (`D6-R6`) |
| Client can't find the server | Distinguishes wrong address, wrong network, and server down — three different fixes (`G6-R9`) |
| Ana's device is on guest Wi-Fi | Named as a likely cause — guest networks isolate clients (`G6-R10`) |
| Playback buffers | Likely transcoding; points at the quality preset and platform capability (`G6-R6`) |
| Library appears empty | Distinguishes an unscanned library from parental restrictions (`G6-R11`) |
| Ana tries to watch away from home | **Not supported in 1.0.** Stated in the invitation rather than discovered at a friend's house (`D6-R11`) |
| Ana forgets her password | Operator issues a reset link, never learning the password (`D6-R10`) |

## Related

- [J1 First run](j1-first-run.md) — the operator's half
- [D4](../features/d-content/d4-request-flow.md) · [D6](../features/d-content/d6-household-identity.md) · [D7](../features/d-content/d7-approval-quotas.md) · [D8](../features/d-content/d8-parental-controls.md)
- [G5 The front door](../features/g-ux/g5-front-door.md) · [G6 Client apps](../features/g-ux/g6-client-apps.md)
