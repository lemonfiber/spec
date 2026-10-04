# ADR-0031: Installing a plugin and choosing a filler are web API writes; replacing a credential is not

**Status:** Accepted
**Date:** 2026-09-28
**Decided:** 2026-09-28, by the maintainer, Wessel Verheij: with the yes to each of these writes being the offer its rehearsal answered, rather than a bare confirm.
**Amended:** 2026-10-04 by [ADR-0036](0036-a-plugin-may-come-from-any-source-the-command-takes.md), which lets the actions take every source the command takes.

## Context

`G1-R1` requires every action to be available from every surface, except where
it is intrinsically unsuited, and requires each exception to be documented.
`ARCH-R48` bounds the web API from the other side: it exposes nothing the
command line cannot do.

The web API already documents one exception. `/api/credentials` lists every
credential the stack holds and no value, and the two things that can be asked
of a line of it, printing the value and replacing it, are not offered over that
door ([the web API contract](../../20-architecture/contracts/web-api.md)). Two
reasons are given. A value printed over HTTP passes through a browser's cache,
any proxy between and the log each keeps. Replacing one is a write a request
could be forged into making against the credential the stack is working on.
Both acts stay at the terminal, in front of the person who typed the
confirmation.

Installing, updating and removing a plugin, and choosing which service fills a
capability, are consequential in the same way. An install adds a stranger's
service to a working stack, and a choice decides what every consumer of a
capability reaches. In the core all four are command-line only, and `F6-R15`
and `F4-R27` require them on the web API. The companion reaches a stack only
over the web API (`N1-R16`), so without them its plugin screen and its
contested-capability question (N5, N25) have nothing to act through. A contest
is refused until the operator chooses (`F4-R8`), and an operator who can read it
on the companion cannot answer it there.

So the question is whether these writes are exceptions in the sense the
credential writes are.

## Decision

**They are not.** Installing, updating and removing a plugin (`F6-R15`), and
choosing which service fills a capability with an optional reason (`F4-R27`,
`F4-R29`), are actions of the web API. Each takes what the command takes and
answers as the command answers. Each can be rehearsed over the API, writing
nothing (`F6-R16`, `F4-R28`). Printing and replacing a credential stay at the
terminal.

The line between them is what the request carries and what a forged one could
do.

1. **No secret travels.** An install names a source by its path on the stack's
   machine, an update names a new version's path, a removal names a plugin id,
   and a choice names a capability, a service and a reason. None of it is a
   secret, so nothing sensitive reaches a cache, a proxy or a log. A
   credential's replacement carries the secret itself.
2. **A forged write can only choose among what is already there.** An install
   reads a source already on the machine at the path named, and the manifest
   decides everything the install writes. The command takes no flag by which a
   request could ask for terms the manifest did not declare, and lemonfiber
   writes the container ([ADR-0021](0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md)).
   A choice is refused unless the service is one of this stack's and claims the
   capability. A credential's replacement installs a value that came from
   outside the machine, chosen by whoever sent it.
3. **Each is recorded and can be put back.** Every change an install makes is
   journalled (`F6-R2`), removal reverses it (`F6-R7`), and a choice is one
   journalled setting that `undo` puts back (`F4-R10`). The rehearsal states
   what each would do before it is agreed to (`F6-R1`, `F4-R11`).
4. **They sit behind the guards every other write does.** The per-run token or
   session in a header (`ARCH-R52`, `ARCH-R76`), `Origin` and `Host` checked
   against the bound address (`ARCH-R53`), protection against cross-site
   request forgery (`C6-R10`), and the core's refusal of anything a credential
   is not entitled to (`G10-R3`): a household member is granted a short list of
   reads and refused every other command, so none of these writes reaches one.
   `uninstall`, `restore` and `reset` are already web API writes on those
   terms. The capability read that would show a client that answer
   (`ARCH-R80`) is not served yet; it reports the refusal and does not enforce
   it.
5. **The yes is the offer that was read.** Each of these is two requests with a
   decision between them: a rehearsal states what the write would do, and the
   write does it. Between the two, what was read can move. A manifest at the
   named path can be replaced, a newer version can land, another plugin can
   come to claim the capability, and a choice made meanwhile can settle the
   contest another way. So each rehearsal answers an offer, a name built from
   what it read. The write takes that offer as its yes, builds the name again
   from what is there now, and refuses where the two differ, naming what moved.
   A bare `confirm` is not a yes to any of the four over the API. This is how
   `repair`, `restore`, `stop-seeding` and `uninstall` already take theirs.
   The command takes the same offer (`ARCH-R48`) (`F6-R17`, `F4-R30`).

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Terminal only, like a credential's replacement** | Leaves N5 and N25 unanswerable, and leaves a contest the companion can show with nowhere to answer it. Neither of the reasons the credential exception rests on applies: no secret travels, and a forged request can only choose among what is already on the machine. |
| **Read over the API, act at the terminal** | Serves the question and not its answer. An operator told on their phone that a capability is contested and refused has been told about a broken link they cannot mend from there, which is the state `F4-R8` exists to keep short. |
| **A bare `confirm`, with the journal as the safety net** | The journal puts a change back after it lands; it does not stop a yes from agreeing to something other than what was shown. A manifest replaced between the rehearsal and the yes would install terms nobody read, and a contest settled meanwhile would be overridden by a choice made against a wiring that no longer stands. Undoing afterwards is repair, not consent. Every other write that shows the operator something and then acts on the answer already takes the offer. |
| **Install from a URL or a git source over the API** | The command takes a path, and `ARCH-R48` forbids the API taking more. A source fetched on a request's say-so reaches the network on behalf of whoever sent the request, which is a different risk from reading a path already on the machine. |

## Consequences

### Positive

- The companion can install, update and remove a plugin, and answer a contest,
  from wherever the operator is. `G1-R1` holds for all four with no exception to
  document.
- A choice carries the operator's reason on both surfaces, so a choice read
  later says what it was for (`F4-R29`, `N5`).
- A yes agrees to what the operator read and nothing else. A manifest, a
  version or a wiring that moved after the rehearsal is refused by name, not
  applied.

### Negative

- A request that passes the guards can install a plugin whose source is already
  on the machine. The guards are the same ones every other write relies on, so
  a weakness in them is a weakness for all of them.
- Installing from a remote source is offered on neither surface, because the
  command takes only a path.

- Each of the four becomes two requests with a name carried between them, so
  a client that sent a bare `confirm` is refused and has to rehearse first.

### Neutral

- The credential exception is unchanged, and this ADR states why it differs
  rather than moving it.

## Revisit if

- The install command takes a source other than a path on the machine, such as
  a git URL (`F5-R4`). The web action would then fetch on a request's say-so,
  and the second reason above no longer holds as written.
- A plugin act or a choice gains an effect outside the machine, or one the
  journal cannot put back.
- A household credential becomes able to reach any of these writes.

## Related

- [F6](../../10-functional/features/f-extensibility/f6-plugin-lifecycle.md) — the plugin lifecycle, and `F6-R14` to `F6-R17`
- [F4](../../10-functional/features/f-extensibility/f4-capabilities.md) — the capability vocabulary, and `F4-R26` to `F4-R30`
- [N5](../../10-functional/features/n-companion/n5-connecting-the-stack.md) — what connects to what, on the companion
- [N25](../../10-functional/features/n-companion/n25-a-plugin-after-it-lands.md) — a plugin after it lands
- [The web API contract](../../20-architecture/contracts/web-api.md) — the credential exception, and the guards
- [ADR-0021](0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md) — a plugin is data, and lemonfiber writes its container
