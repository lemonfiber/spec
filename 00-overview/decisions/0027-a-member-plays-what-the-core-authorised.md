# ADR-0027: A member plays what the core authorised, on the member's own account

**Status:** Accepted
**Date:** 2026-09-25
**Decided:** 2026-09-25, by the maintainer, Wessel Verheij, on the proof recorded below: the device-authorisation flow holds, and the media server's byte endpoints do not enforce the member's policy, so the front door does.

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
- **The media server holds the policy.** A user-scoped request to the media server
  is answered under that user's parental limits and library access (`D8`). Whether
  it applies that policy to every request is a question the proof below answers.

## Decision

**Two layers. The media server's own policy decides what a member can find, on a
session that is the member's; a reverse proxy the stack keeps in front of the media
server decides whether any byte of an item leaves, by asking the media server
whether the presented session may see that item. Neither layer is a lemonfiber
process.**

### What was proved, and what was not

The device-authorisation flow was proved against the pinned media server, in a
throwaway instance holding two libraries and a member given only one of them. The
recordings are real responses with every password, token, secret and code
withheld:

| Recording | What the server did |
|-----------|---------------------|
| `quickconnect-enabled` | Device authorisation is available, asked with nothing presented. |
| `quickconnect-initiate` | A device asks for a code, presenting nothing but itself. |
| `quickconnect-authorize-for-member` | The administrator authorises that code for the member's user id. |
| `quickconnect-session` | The device exchanges its secret for a session, and the session is the member's. |
| `session-is-the-member` | That session is the member's, not an administrator's, with the member's policy. |
| `session-sees-only-the-library-it-was-given` | It lists only the library the member was given. |
| `session-cannot-administer` | It is refused an administrator's write (403). |
| `administrator-ends-the-device` | The administrator ends every session the device holds (204). |
| `revoked-session-is-refused` | The member's session, asked again afterwards, is refused at the server (401). |
| `member-streams-a-film-they-may-watch` | The member's session streams a film in their library. |
| `member-streams-a-film-in-a-library-they-were-not-given` | **The same session streams a film in a library the member was not given.** |
| `anybody-streams-a-film-presenting-nothing` | **A caller presenting no token at all streams the same film.** |

So the session is the member's, and the server enforces the member's policy on
**discovery**: listing, an item's metadata and its playback information answer
404 for an item outside the member's libraries. It does not enforce it on the
**bytes**. The server's byte endpoints answer without authorization: a video or
audio stream by item id, an HLS segment, a subtitle, an attachment, an item's
image, a live-TV recording or stream. That was observed on the pinned 10.10 image
and on 10.11.11, and is so in the source of 12.1, where the same endpoints carry no
authorization requirement. Anybody who can reach the media server's port and holds
an item id can stream it, which is a fact about every household this stack serves
today, independent of the companion.

### The decision

1. **A member grant, on the member's own account.** A member's paired client asks
   the core for a grant to play. The client asks the media server for a device
   code, and the core, as administrator, authorises that code for the member's user
   id. The session the server issues belongs to the member, so every discovery
   request made with it is answered under the member's policy. The member's
   password is never involved and nobody learns it.
2. **Expiry and revocation are the core's.** The media server's sessions do not
   lapse on a schedule, so the core ends the device's sessions when the grant lapses
   and when the member is removed from the household (`D6-R8`). An ended session is
   refused at the server and at the proxy alike.
3. **A reverse proxy guards the bytes.** Every byte endpoint of the media server is
   reached only through a reverse proxy the stack runs under its restart policy,
   in every form that serves the media server rather than only in the optional
   `proxy` form. Before it passes a byte request on, it
   asks the media server, with the token the request presented, for that item as
   the session's own user sees it. An item the session cannot see, a token that is
   absent, ended or wrong, and an answer that does not come are all refusals, so
   the bytes of an item follow the same policy as its discovery. What the question
   is called in the media server's API is the supported release's, declared where
   the stack declares how each supported release is spoken to, and this decision
   holds for every release that serves bytes without authorization.
4. **The media server's port is not published beside the proxy.** The guard is
   only a guard if nothing reaches the server another way. The stack publishes the
   media server's port on the household network today, on every interface where
   nothing narrows it, so the proxy is what the household reaches by default and the
   media server's own port is published on this machine only. The proxy is also
   where sign-in attempts can be counted and slowed, which the media server does not
   do for a member account unless it is told to, and where the media server's
   cross-origin allowance can be narrowed to the household's own origins.
5. **A per-holding location.** Each `Held` entry gains `stream_from`: the address
   at the proxy that streams that item, built from the household address the stack
   publishes for the media server and the media server's item path. It is present only where
   the core knows that address and the item is one that streams. Where it is not,
   the field is absent and the entry says why rather than carrying a guess.
6. **Nothing is added to lemonfiber's own run.** The grant is asked for through the
   core; the stream goes from the media server through the proxy to the client.
   No lemonfiber process carries media or decides a byte request, so `G1-R5` holds
   and playback does not depend on the web surface being up.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| The core proxies the stream, at a core-signed address, under the administrator's session, and filters by the member's policy before it serves anything. | It puts every byte of video through a lemonfiber process, so playback depends on the web surface running, which `G1-R5` says it need not. It also makes the core a second judge of the member's limits, beside the media server, and two judges can disagree. The front door asks the media server instead of judging for itself. |
| The media server is trusted to guard its own bytes, and nothing stands in front of it. | Observed false: its byte endpoints answer without authorization on every release examined, so a member's limits and a household's whole library are open to anybody on the network who holds an item id. |
| A newer media server release is pinned in place of the guard. | No release examined enforces authorization on its byte endpoints, so a re-pin changes nothing this decision is about. The guard holds for every supported release. |
| The member signs in to the media server in the companion with their own password. | The member's credential then lives on the phone beside the operator's pairing, and a member who never set a password (an unclaimed invitation) cannot play at all. It also reaches the media server without the core, so the core cannot revoke or expire it when the member leaves. |
| An administrator API key for the companion. | An API key is the administrator's. Streams on it carry no member policy, so the player would hold the second copy `N3-R14` forbids. |
| The core composes the stream address from the pairing address. | The pairing address is how the companion reaches the core, not the media server. Composing one address from another is exactly the inference the companion must not make, and it is wrong wherever the two live on different hosts or ports. |

## Consequences

### Positive

- The member's limits are decided once, by the media server, on the member's own
  session, and the front door applies that decision to the bytes. The player holds
  no copy of them.
- The proxy closes the anonymous byte endpoints for the whole household, not only
  for the companion.
- Removing a member ends their playback at the server, through the same
  revocation `D6-R8` already performs.
- Playback does not depend on any lemonfiber process running.

### Negative

- It depends on the media server's device-authorisation flow accepting an
  administrator's authorisation on a member's behalf, which holds on the pinned
  release by the recordings above and has to hold on every supported release.
- Every byte request costs the proxy one question to the media server.
- The reverse proxy stops being optional wherever the media server runs, which is
  a change to the forms (`B1`) and to what the household address points at (`G5`).
- A client that reached the media server's port directly on the household network
  now reaches it through the proxy, and one that was pointed at the port has to be
  pointed at the proxy.
- Images named by a person, a genre or a studio rather than by an item are not an
  item's bytes and are not guarded by the item question.
- A grant is a live credential on the phone until it lapses or is revoked. Its
  lifetime has to be short enough to bound that, and long enough not to interrupt
  a film.
- `stream_from` is absent wherever the front door cannot state the media server's
  household address, and playback is declined there.

### Neutral

- Away from home, the household address does not answer and playback is declined
  (`N3-R15`), which is what `N3` already says.

## Revisit if

- A supported media server release stops accepting an administrator's
  authorisation of a device on a member's behalf.
- Every supported release enforces authorization on its byte endpoints, which
  would make the guard's question redundant rather than wrong.
- Remote access ships, and the address a member can stream from depends on where
  they are.
- A second media server is supported whose session model differs.

## Related

- [N3](../../10-functional/features/n-companion/n3-household-companion.md) — what a member sees, and `N3-R14`–`N3-R16`
- [D6](../../10-functional/features/d-content/d6-household-identity.md) — `D6-R2` and `D6-R8`
- [D8](../../10-functional/features/d-content/d8-parental-controls.md) — where the limits are decided
- [G1](../../10-functional/features/g-ux/g1-interface-tiers.md) — `G1-R5`
- [G5](../../10-functional/features/g-ux/g5-front-door.md) — the front door
