# Contract: the web API on the wire

**Status:** Accepted

Part of the [web API contract](web-api.md): the particulars two clients must agree on to
talk to the same server — the token's header, the address, the heartbeat, resuming the
stream, a job's outcome, an action sent again, the payload's type and how an instant is
written. The requirements it describes are listed with the rest of the contract's, under
[Requirements](web-api.md#requirements).

## The details two clients must agree on

A requirement that states an obligation without stating its mechanism gets two
implementations that both satisfy it and cannot talk to the same server. These are
the particulars, fixed so that no client has to invent them.

### The token

The header is **`X-Lemonfiber-Token`**. The binary prints the token when it starts
serving, and a client is given it by its caller — there is no discovery, no file to
read, and no default.

### The address

There is **no default port**. The binary chooses a free one unless told otherwise and
prints the whole address; a client is configured with that address rather than
assembling one.

A host name is accepted only if it resolves to a loopback address. Refusing the word
`localhost` outright is the wrong trade: it is what an operator types and what a
printed address may contain. Refusing a name that resolves *off* loopback is the
protection that matters, and resolving before connecting is what provides it.

That protection is against a browser: a page the operator visits cannot read a
cross-origin response, but it can send a request the server acts on, and DNS
rebinding defeats a naive origin check. A page has no pin to offer and never
will, so for `sdk-ts` the rule stands unchanged.

A client that *can* be given a pin is in a different position. The companion is
deliberately not on this machine ([ADR-0017](../../00-overview/decisions/0017-the-companion-app-as-a-fourth-surface.md)),
and the identity question a loopback address answered by construction is answered
for it by the pinned certificate instead
([ADR-0025](../../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md)).
So the address rule is a condition rather than a prohibition: loopback needs no
pin, anything else needs one, and there is no third case. `ARCH-R99` is written so
that the unsafe combination has no spelling — a non-loopback address is not a
setting that can be turned on and a pin forgotten, because the pin is what
produces the address.

### The heartbeat

The server emits a comment line at least every **15 seconds** when nothing else has
been sent. A client treats the stream as broken once **twice** that has passed in
silence, which tolerates one missed beat without pretending a dead connection is a
quiet one.

### Resumption

Every event carries an `id`. A client resuming sends the last one it saw as
`Last-Event-ID`, and the server replays from after it where it can, or restarts the
stream where it cannot. Either way everything the client still holds from before the
gap is stale until replaced — the resumption mechanism does not change what is
current, only what is retransmitted.

### A job's outcome

```
GET    /api/jobs/<job>
DELETE /api/jobs/<job>
```

The other end of the accepting reply. It is not named for a command, because it answers no
request the command line has: being answered with a name instead of an outcome is the web's
own arrangement, and this is the half that makes it an answer.

`DELETE` releases the name. For work with no ending of its own — a guard that holds until the
data location is lost — a browser has no interruption to send, so letting the name go is its
Ctrl-C, and what the container engine was already asked to do goes on exactly as it does when
a terminal is closed.

The standing is carried by the **status**, and the body is a document the client already
parses either way:

| Standing | Status | Body |
|---|---|---|
| Still in flight | `202` | the identical envelope the accepting reply carried |
| Finished | `200` | the equivalent command's machine-readable output |
| Stopped on a failure | the status the failure warrants — `404` for something named that the stack does not have, `400` for a request asked wrongly, `409` for work that found other work holding the stack, `500` otherwise | the error envelope the failure renders |
| Ended before it finished | `200` | the `job` envelope, saying whether the name was released or let go |
| Not a name this run issued | `404` | a refusal, not the name repeated back |

Status rather than a field, because the alternative is a shape only this endpoint has — and a
second serialisation of an outcome the contract already describes is the drift `ARCH-R47`
exists to prevent.

Work that found other work holding the stack is none of the refusals above. Nothing it named
was missing, nothing about it was asked wrongly, and the machine did not fail: the stack does
one lifecycle operation at a time (`B6-R8`), and this one waited its turn and did not get it.
It is the one stopped job whose right answer is the same request sent again once the other
work is done, so it has a status of its own, `409`. Told `500`, a client words a failure of
the machine about a stack that was working and busy, and cannot do what `B6` asks of it —
show that another operation is in progress (`ARCH-R135`).

Work ended before it finished has no outcome to give, and it ended one of two ways. A
client released its name, or nothing asked about work with no ending of its own for long
enough and it was let go. The two are different news to whoever comes back to the name:
the first is somebody's decision, and the second is a guard that stopped guarding because
the screen watching it went away. So the answer says which, and neither is told as work
that finished or work still going (`ARCH-R132`).

The stream is not the mechanism. A client that reconnects sends the last id it saw, and a
client connecting for the first time has none to send, so an event announcing the end reaches
only a client that was already listening when it happened — which is not the client the
accepting reply exists to serve. A tab closed mid-repair and reopened holds a name and nothing
else, and this is what it does with it.

Names do not outlive the run that issued them. Work in flight does not survive the process
doing it, so a record that outlived the run would describe jobs nothing is running; a name from
an earlier run is therefore one this run never issued.

### An action sent again

```
POST /api/actions/<name>
Idempotency-Key: <key>
```

A client that sent an action and heard nothing back cannot tell a request that never
arrived from an answer that never reached it. The safe thing for it to do is send the same
action again, and a stack that could not recognise the second send would restart twice or
pause twice. So an action request may carry an `Idempotency-Key` naming the attempt it is,
and a request without one is an attempt of its own (`ARCH-R165`). It serves the retry inside
one attempt and nothing longer (`N1-R42`, [ADR-0020](../../00-overview/decisions/0020-an-action-the-stack-did-not-receive-did-not-happen.md)).

The same key sent again by the same caller while its attempt is remembered is answered
with what the first send was answered with: the same job name for work that runs on, and
the same status and envelope for an action answered on the spot, a failure included. The
action runs once. A second send that arrives while the first is still being carried out
waits for the first one's answer rather than starting the action beside it (`ARCH-R166`).
The caller is whoever the guard admitted: the terminal's token, the operator, a household
member, or a key by its name.

A request refused before its action is reached — a body it cannot read, an action it does
not name, an argument refused, a caller not permitted — is not an attempt. Nothing ran, so
nothing is kept, and the same request sent again is ruled on again.

Work that ends without an answer — stopped, or fallen over — is answered `500` with a
code of its own, to the first send and to every send waiting on it, and its attempt is
forgotten: it reached no answer to give again, so the same key sent afterwards runs the
action again. A send never waits on an attempt that will not answer (`ARCH-R166`).

**A key names one attempt, so it names one action and its arguments.** The same key sent
with another action or other arguments is refused with its own code at `400`, and nothing
runs under it (`ARCH-R167`). Answering it with the first send's outcome would hand a client
an answer to a request it did not make, and running it would run two attempts under one
name.

What is remembered is held in memory and nowhere else, and does not outlive the run, as
the work it names does not. Each caller has their own, and how long and how many are the
operator's two settings, read again at every send so a change holds from the next one:

| Setting | Holds | Default | May be |
|---|---|---|---|
| `LEMONFIBER_IDEMPOTENCY_MINUTES` | how long an attempt is remembered from its first send | `30` | a whole number from 1 to 1440 |
| `LEMONFIBER_IDEMPOTENCY_KEYS` | how many attempts one caller has remembered at once | `256` | a whole number from 1 to 4096 |

Half an hour is the lease a job's name is kept for, so a second send answered with a name
is answered while that name can still be redeemed. Past the count, a caller's next attempt
lets go of that caller's oldest answered one, so one caller sending many keys never pushes
out another's. An attempt still being carried out is never let go, by age or for room:
letting it go would let its second send run the action beside it (`ARCH-R168`). Each
setting is changed as any setting is, and shown with where it came from (`A4-R13`).

A key is one to 255 visible ASCII characters, `!` to `~`, given once. Anything else — an
empty value, a longer one, a space, a character outside ASCII, the header given twice — is
refused with its own code at `400` before anything runs, because a key that cannot be read
the same way twice is one a second send could not be recognised by (`ARCH-R169`). The
header means nothing outside `/api/actions/<name>`.

### The payload's type

`data` differs by `kind`, so a client exposes it **typed by its kind** rather than as
an untyped value. Generated types make this ordinary rather than laborious: the kind
is the discriminator, and an untyped payload on the public surface means the
generation has not been used.

### An instant

Every instant the web API carries is an integer: whole seconds since the Unix epoch,
`1970-01-01T00:00:00Z`, as a JSON number in a request, a response or an event, and as
its decimal digits in a link the core builds, such as the join link's `expires`
(`D6-R22`) and the key link's (`C10-R18`). There is no string form, no fraction and no
zone to read, so two clients compare two instants as numbers and agree. A command's
`--json` writes instants alike, since the web API answers with the command's own
envelope (`ARCH-R46`). A stamp a service wrote and lemonfiber passes on verbatim, such
as the one a container put on a log line, is that service's text rather than an instant
of lemonfiber's, and is labelled as such (`ARCH-R274`).

## Related

- [web-api](web-api.md) — the rest of the contract, and its requirements
- [web-api-getting-in](web-api-getting-in.md) — how a caller is admitted
