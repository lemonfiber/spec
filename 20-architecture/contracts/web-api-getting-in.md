# Contract: getting in to the web API

**Status:** Accepted

Part of the [web API contract](web-api.md): how a caller is admitted, by the per-run
token, a session or an integration key, and the limit wrong answers meet. The requirements
it describes are listed with the rest of the contract's, under
[Requirements](web-api.md#requirements).

## Getting in

```
POST /api/session
```

The per-run token answers one question — *is this the machine's own operator* — and it
answers it by having been printed on the terminal that started the process. That is the
population loopback already answers for, so while the surface is loopback-bound it is the
whole of what admission needs to be. It is no use at all to somebody holding a phone, and
being reachable from a phone is the entire case for binding beyond loopback
([C6](../../10-functional/features/c-trust/c6-web-security.md)).

So there is a second way in, and exactly one: the operator's own password, exchanged
**once** for a session. The password is not sent again — verifying it is deliberately
expensive, and a credential re-sent on every request is a credential with more chances to
leak.

The request body is `{ "password": … }`. The reply is the envelope, `kind: "admission"`,
carrying the session's own secret and the moment it stops being one. That secret travels in
`X-Lemonfiber-Token`, exactly as the per-run token does, so the surface has **one credential
header** to read and a client has one thing to hold rather than two.

| Refused because | Status |
|---|---|
| The password was wrong, or none is configured | `401` |
| Too many wrong answers lately | `429`, saying how long is left |

**An invitation is claimed at the same door.** The body
`{ "name": …, "password": …, "claim": … }` is a claim
([D6-R25](../../10-functional/features/d-content/d6-household-identity.md)): `claim` is the
token the invitation's join link carries, and `password` is the one the person chose, which
the core sets on their own account at the media server before it opens their session. The
reply is the same `admission` envelope. A claim is counted against the same attempts as a
sign-in. An invitation that is not open, whether its token is unknown, spent, lapsed or
declined, is refused `401` under one code, so a guess learns nothing about which; a password
shorter than the minimum is refused under a code of its own naming it. The token travels in
the body, never in a URL the core receives (`ARCH-R219`).

The `invitation` envelope carries `join`, the link the companion opens, and where it carries
none for a reason other than a rehearsal, `unjoinable`, saying why in words every surface can
show (`ARCH-R218`). No envelope carries a drawn code: a surface draws a QR code from the
address or link it was given, exactly as given (`ARCH-R220`,
[G1-R15](../../10-functional/features/g-ux/g1-interface-tiers.md)).

`401` is the door's alone. A wrong password is answered where it was offered, so a client
reading `401` knows that the password it just sent is the thing to change. Every other
refusal, including a session this run no longer admits, answers `403`, and what tells a
client that signing in again would help is the refusal's code, not its status.

### An integration key

A program that runs beside the stack for months, such as Home Assistant, holds neither the
per-run token nor a session. It holds a key the operator minted for it under a name and
with one scope, `read`, `act` or `member:<account>`
([C10](../../10-functional/features/c-trust/c10-integration-keys.md),
[ADR-0037](../../00-overview/decisions/0037-an-integration-key-is-minted-where-the-operator-proves-themself.md)).

A key travels in `X-Lemonfiber-Token`, so the surface still reads one credential header. It
survives a restart, is refused exactly as a wrong token is once revoked, and is accepted
from another machine only over the TLS its pin verifies. The actions an `act` key may call
are published in the contract, and every other action is refused to a key, naming its
scope.

Minting and revoking are the one credential write the web API takes. Only an operator
session may make them, minting asks for the password in the same request, and the secret
appears once, in the mint reply, beside the stack's address and certificate pin.

```
GET    /api/keys
POST   /api/keys
DELETE /api/keys/{name}
```

`POST /api/keys` takes `{ "name": …, "scope": …, "purpose": …, "password": … }`. The reply
is the envelope under its own kind, carrying the secret, the pin, and the address where the
stack has been served encrypted on the network. It is sent with `Cache-Control: no-store`,
as every reply here is. `GET /api/keys` lists the keys without their secrets, and
`DELETE /api/keys/{name}` revokes one. A key is refused at all three, whatever its scope.

A household member reaches the same three routes for keys of their own. Their mint names
`member:` and themselves as the scope and gives their own password, which the media server
checks as it checks their sign-in, counted against the same limits; it is refused with a
code of its own while the operator has not turned `LEMONFIBER_MEMBER_KEYS` on. Their listing
holds only the keys scoped to them, they revoke only those, and a key that is not theirs is
answered as one that does not exist. Turning the setting off stops members minting, not
revoking.

A key's secret begins with `lfk_`, so the guard can tell a value shaped like a key from a
token or a session without looking it up. That is what it counts: a value shaped like a key
that matches no key counts against [the limit wrong passwords meet](#wrong-answers-are-counted).
A revoked or orphaned key is refused as a wrong token is and not counted. While the limit
holds, a request carrying a value shaped like a key is answered `429` before the value is
checked.

A key presented from another machine over plain HTTP, or over a connection whose origin
cannot be placed, is refused before it is checked, with a code of its own: the remedy is to
connect over the TLS the pin verifies, not to send a different key.

The actions a key may call are published in the artefact as `key_callable`. Each entry
names the action, says whether it disturbs the running system, says whether it takes
`dry_run`, so a client can rehearse it first and offer the real call after, and says whether
calling it again with the same arguments leaves the stack as one call did, so a client can
tell a person whether repeating it is safe (`ARCH-R160`). That is read by where the stack ends
up, not by whether the work is done again: a second restart takes the services down a second
time and leaves them running, as the first did, so a restart is idempotent; an update moves to
whatever is newest by the time it is called, so it is not. Whether it takes
`dry_run` is read from the core's own account of each command rather than written beside the
list. The list starts as:

```
POST /api/actions/restart          POST /api/actions/diagnose
POST /api/actions/update           POST /api/actions/downloads-pause
POST /api/actions/downloads-resume
```

**A rehearsal of one of these answers an offer, and the real call may carry it back.** The
rehearsal of each action that takes `dry_run` answers, beside what it would do, an offer built
from what it read, as the plugin writes' rehearsals do. A call carrying that offer builds it
again from what is there now and is refused where the two differ, naming what moved, with a
problem code the artefact lists among its refusals: a restart rehearsed against one set of
services is not carried out against another, and an update rehearsed against one release is not
carried out against the next. A call carrying no offer acts as it does without one, because
these are calls a program makes on a schedule as well as after asking somebody, and none of them
installs anything a rehearsal would have to be read for. `key_callable` says, entry by entry,
whether an action answers an offer, so a client knows which of its calls can carry one
(`ARCH-R164`).

An `act` key asking for any other action is refused, naming its scope, and a `read` key is
refused every action.

### The session

A session **expires**, on an absolute clock rather than on use: a window left open all week
is not evidence that whoever opened it is still there. It is also void the moment the
password changes — which is what makes changing the password a way to end a session
somebody else is holding, rather than only a way to stop the next one.

Neither is a rule a client may keep its own version of. The server refuses an expired or
voided session exactly as it refuses a wrong one, with the same status, sentence and code.
A client that cached the verdict would be a second opinion about who is admitted. Sessions
live only as long as the process that opened them, so a session from an earlier run is
refused the same way too. A client holding one learns only that what it carries is no
longer admitted, and the remedy is to sign in again. Naming which secret failed would tell
somebody guessing which one to keep guessing at.

### Wrong answers are counted

Failed answers are rate-limited, and the limit is on the surface rather than on the caller's
address: there is one password, and choosing a new source address per attempt is the
ordinary shape of the attack. The refusal says how long is left, so a client waits rather
than retrying into the limit and extending it.
