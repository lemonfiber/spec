# ADR-0027: A member plays what the core authorised, on the member's own account

**Status:** Proposed
**Date:** 2026-09-25

## Context

`N3` has the companion play what the household holds, and `N3-R14` requires what
a member may watch to be the core's answer, with no second copy of a library, an
age limit or an entitlement in the player. The contract cannot serve that today:

- `Held { id, medium, title, year? }`, the entry `/api/held` lists, carries no
  location. Its `id` is described as "what asking to play one of them names", but
  no action or read accepts it, and no route plays or streams anything.
- The core signs in to the media server only as the stack's administrator, with
  the password the stack recorded when it set the server up. A stream opened on
  that session is the administrator's. It carries none of the member's age limit
  or library access, so a player using it would have to enforce those itself,
  which is the second copy `N3-R14` forbids.
- `D6-R2` means the operator never sets or learns a member's password. The core
  cannot sign in as the member the ordinary way.

So the core has to give a member a stream authorised for that member, without
anybody but the member knowing the member's credential, and without the player
deciding what the member may see.

Four constraints bound every answer:

- **Reachability.** A stream is only playable where the media server can be
  reached (`N3-R15`), and a location the core states has to be one it knows the
  server is reachable at. The companion must not compose an address.
- **The front door.** The household reaches the stack through the front door
  (`G5`), which publishes the media server's household address. That address is
  the one the stack already knows is reachable from the household network.
- **`G1-R5`.** The web surface is started explicitly and does not run
  persistently, so nothing the household relies on at any hour may depend on a
  lemonfiber process being up.
- **The media server enforces its own policy.** A user-scoped request to the
  media server is answered under that user's parental limits and library access.
  That is the one enforcement point the core already relies on (`D8`).

## Decision

**The core mints a playback grant on the member's own media-server account, and
each held entry says where it is streamed from. The media server enforces what
the member may watch, because the stream is the member's.**

1. **A per-holding location.** Each `Held` entry gains `stream_from`: the address
   the media server streams that item from, built by the core from the household
   address the front door publishes and the server's own item path. It is present
   only where the core knows that address. Where it does not, the field is absent,
   and the entry says why rather than carrying a guess.
2. **A member grant with an expiry.** A new action, taken by a member's paired
   client, asks the core for a grant to play. The core obtains a session on that
   member's own media-server account and hands back the session token and when it
   lapses. The member's password is never involved and nobody learns it.
3. **How the session is obtained.** The core uses the media server's own
   device-authorisation flow: the client asks the server for a short code, and the
   core, as administrator, authorises that code for the member's user id. The
   session the server then issues belongs to the member, so every request made
   with it is answered under the member's policy. This has to be proved against
   the pinned image before it is relied on, the way every other media-server call
   is proved against a recording.
4. **Expiry is the core's.** The media server's own sessions do not lapse on a
   schedule, so the grant's expiry is enforced by the core revoking that device's
   session when it lapses, and when the member is removed from the household
   (`D6-R8`). A revoked session fails at the server, so playback ends there rather
   than in the player.
5. **Nothing is proxied.** The stream goes from the media server to the client
   directly. No lemonfiber process carries media, so `G1-R5` holds and playback
   does not depend on the web surface being up.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| The core proxies the stream, at a core-signed address, under the administrator's session, and filters by the member's policy before it serves anything. | It puts every byte of video through a lemonfiber process, so playback depends on the web surface running, which `G1-R5` says it need not. It also makes the core enforce the member's limits a second time, beside the media server, and two enforcement points can disagree. |
| The member signs in to the media server in the companion with their own password. | The member's credential then lives on the phone beside the operator's pairing, and a member who never set a password (an unclaimed invitation) cannot play at all. It also reaches the media server without the core, so the core cannot revoke or expire it when the member leaves. |
| An administrator API key for the companion. | An API key is the administrator's. Streams on it carry no member policy, so the player would hold the second copy `N3-R14` forbids. |
| The core composes the stream address from the pairing address. | The pairing address is how the companion reaches the core, not the media server. Composing one address from another is exactly the inference the companion must not make, and it is wrong wherever the two live on different hosts or ports. |

## Consequences

### Positive

- The member's limits are enforced once, by the media server, on the member's
  own session. The player holds no copy of them.
- Removing a member ends their playback at the server, through the same
  revocation `D6-R8` already performs.
- Playback does not depend on any lemonfiber process running.

### Negative

- It depends on the media server's device-authorisation flow accepting an
  administrator's authorisation on a member's behalf. If the pinned image does
  not offer that, this decision fails and has to be revisited.
- A grant is a live credential on the phone until it lapses or is revoked. Its
  lifetime has to be short enough to bound that, and long enough not to interrupt
  a film.
- `stream_from` is absent wherever the front door cannot state the media server's
  household address, and playback is declined there.

### Neutral

- Away from home, the household address does not answer and playback is declined
  (`N3-R15`), which is what `N3` already says.

## Revisit if

- The pinned media server stops accepting an administrator's authorisation of a
  device on a member's behalf.
- Remote access ships, and the address a member can stream from depends on where
  they are.
- A second media server is supported whose session model differs.

## Related

- [N3](../../10-functional/features/n-companion/n3-household-companion.md) — what a member sees, and `N3-R14`–`N3-R16`
- [D6](../../10-functional/features/d-content/d6-household-identity.md) — `D6-R2` and `D6-R8`
- [D8](../../10-functional/features/d-content/d8-parental-controls.md) — where the limits are decided
- [G1](../../10-functional/features/g-ux/g1-interface-tiers.md) — `G1-R5`
- [G5](../../10-functional/features/g-ux/g5-front-door.md) — the front door
