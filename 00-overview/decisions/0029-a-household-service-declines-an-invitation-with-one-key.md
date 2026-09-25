# ADR-0029: A household service declines an invitation, holding one media-server key and nothing else

**Status:** Proposed
**Date:** 2026-09-25

## Context

`D6-R15` gives every invitation a decline address, `G5-R14` puts it in the
invitation beside the front door, and `D6-R16` requires three things of a refusal:

- It makes the invitation unclaimable **at once**.
- The stack keeps it until the core reads it.
- The core reports it as `declined`, apart from `expired`, which is what `N9-R7`
  asks the companion to show.

Neither repository implements any of it. The core has no invitation decline, and
the stack has no service to answer the address.

**What an invitation is, on the server.** An invitation is a Jellyfin account with
no password. Signing in with its name and an empty password succeeds, and setting
a password from that session claims it. Both hold on 10.10.3, 10.11.11 and 12.1,
measured on 2026-09-25. The core dates an invitation from Jellyfin's activity log.
It removes an unclaimed account after 48 hours, the next time it issues an
invitation. It keeps nothing of its own.

**What makes an account unclaimable, measured on all three lines:**

| Act | Answer |
|-----|--------|
| `POST /Users/{id}/Policy` with only `IsDisabled` | 400. `AuthenticationProviderId` and `PasswordResetProviderId` are required. |
| The same, with the full policy read back and `IsDisabled=true` | 204 |
| Signing in to the disabled account | 403 |
| A token the account already held | 401 |
| An administrator authorising a Quick Connect code for the disabled account | 200. The session it issues answers 401 on every authorised endpoint. |
| Writing `IsDisabled=false` again | Sign-in succeeds again |
| Disabling an administrator | 403, *"Administrators cannot be disabled."* |
| A member disabling their own account | 403 |

Disabling is an administrator's act. No credential narrower than an administrator
can perform it on any line measured.

**The credentials Jellyfin offers.** An API key from `/Auth/Keys` is full
administration on all three lines. It creates users, writes policies, reads the
server configuration and lists every other key. The key entity has no scope at
`v10.10.3` or at `v12.1`. The only token forms all three lines accept are the
`Authorization: MediaBrowser … Token="…"` header and the `?ApiKey=` query
parameter. 12.1 refuses `X-Emby-Token` and
`?api_key=` by default ([ADR-0028](0028-a-supported-major-is-data-proved-by-its-own-recordings.md)).

The core already mints one key, named `lemonfiber`, and publishes it as
`JELLYFIN_API_KEY` to Homepage's environment. Homepage is bound to the LAN.

**Cross-origin reads.** `CorsHosts` defaults to `["*"]` on all three lines, and a
preflight from any origin is allowed. Two further answers, measured on 10.10.3 and
12.1:

- **An explicit list closes it at once**, with no restart. An unlisted origin gets
  no `Access-Control-Allow-Origin`, and a listed one gets exactly its own.
- **An empty list does not close it.** It is read as `*` on all three lines.

A decline page on its own port is a different origin from Jellyfin.

**The tensions:**

- **`D6-R15` says the page is served "never by a lemonfiber process (`G1-R5`)".**
  The reason given is lifetime: `lemonfiber ui` keeps nothing running, so an
  address it answered would stop answering when the operator closed it. The
  wording also reads as authorship, and would forbid an image lemonfiber builds
  even when the stack runs it under its restart policy.
- **C6 puts full control at `127.0.0.1`.** Its tier table reasons that
  administrative surfaces are only the operator's. This service faces the
  household, and has to hold a credential that is administrative on the media
  server.
- **`C6-R12` refuses a proxy to administrative interfaces**, because *one
  authentication bug would expose all of them*.

## Decision

**A lemonfiber-built decline service, pinned by digest and run by the stack at the
household tier, answers the decline address. It holds one Jellyfin API key minted
for it alone. It disables the invited account the moment the invitee refuses, and
records the refusal for the core. The browser only ever talks to the service's own
origin, so the stack closes Jellyfin's CORS. A declined account is kept, disabled,
until the operator acts.**

### 1. The service

- **Its image.** A lemonfiber-built image with its own repository, build and publish
  pipeline. The stack manifest pins it by digest (`E1-R1`) like any service.
- **Where it runs.** `bind = "lan"`, in the front door's profile, restarted by the
  stack's policy.
- **What it serves.** Its own origin answers exactly three routes:

| Route | Answer |
|-------|--------|
| `GET /decline/{token}` | A page naming what would be declined, or saying the invitation is no longer open (`D6-R15`). |
| `POST /decline/{token}` | The refusal |
| `GET /health` | Whether it is running. The key is proved once after each change to the key file, not on every poll. |

### 2. What a refusal does, in order

1. Hash the token and look it up in the invitation table the core wrote. If it
   is unknown or has lapsed, say the invitation is no longer open and change
   nothing.
2. Read the account with `GET /Users/{id}`. Refuse if it is an administrator, or
   if it has been claimed. It decides that with the `own-writes` strategy
   ([ADR-0028](0028-a-supported-major-is-data-proved-by-its-own-recordings.md)) on
   every line: a `UserPasswordChanged` entry for the account in
   `GET /System/ActivityLog/Entries`, later than the issue time in the table, is a
   claim. The strategy has yet to be proved against a recording.
3. Write the policy back in full with `IsDisabled=true` (`POST /Users/{id}/Policy`).
   From that answer on, the account cannot be signed in to (`D6-R16`).
4. Record the refusal in the service's own state directory: the invitation, the
   account and the time. That record is what *kept by the stack until the core
   reads it* refers to.
5. Answer the page. A second refusal of the same invitation says it is already
   declined, and writes nothing.

The service makes those three calls to Jellyfin and no others. It acts only on
account ids the core's table names, and the only field it ever changes is
`IsDisabled`, from `false` to `true`.

### 3. A declined account is kept, disabled, until the operator acts

Three rules replace the 48-hour removal for a declined account:

- **The expiry sweep skips it.** An account with a refusal record is never removed
  as `expired`.
- **The core reads its standing from the record and the account together:**

| Refusal record | Account | Reported as |
|----------------|---------|-------------|
| Present | Disabled and unclaimed | `declined` (`D6-R16`, `N9-R7`) |
| Absent | Disabled | `suspended`: disabled by the operator, or by the server's own lockout |
| Present | Still enabled, because the write failed | `declined`, not yet enforced. The core disables it on that read, as it holds the administrator's session. |

- **The operator decides what happens next.** They remove it (`D6-R8`), or
  re-issue it (`D6-R13`). Re-issuing re-enables the account and resets it, with a
  new decline token.

### 4. The credential is a dedicated API key, not the administrator's password

The core mints the key with its administrator session, using
`POST /Auth/Keys?App=lemonfiber-decline`, and uses it for nothing else. It is not
narrower than the password: no line offers anything narrower. It wins on
containment:

- **It can be revoked alone.** Revoking it disturbs neither the core, nor Seerr's
  owner sign-in, nor Homepage.
- **It has one consumer.**
- **Jellyfin lists it by name**, so an operator reading Jellyfin's own key list
  can see what holds it.
- **It carries a last-used date.** The service uses it only for a refusal or for
  the one proof after a key change, so the doctor can compare that date with the
  refusal records and name a use neither explains.

The service sends it in `Authorization: MediaBrowser … Token="…"`, the one scheme
every supported line accepts.

### 5. Hand-over and rotation (`A7`)

**Hand-over.** The core writes the key to a file in the service's configuration
directory, owner-only (`A7-R8`), mounted read-only. It is not passed as an
environment variable, because `docker compose config` and `docker inspect` print
the environment, which `A7-R3` refuses. The core writes a second read-only file at
each invitation: the invitation table, holding each token only as a hash, with its
account id, issue time and lapse time. The refusal record is the only thing the
service writes. The key joins the credential inventory: *Jellyfin decline key —
used by the decline service — generated by lemonfiber* (`A7-R1`).

**Rotation** follows `A7-R4` to `A7-R6`:

1. Mint a new key.
2. Write it to the file.
3. The core proves the new key authenticates (`GET /System/Info` with it), and
   the service, which reads the file on each use, reports on its health route that
   it holds the new key.
4. Only then delete the old key with `DELETE /Auth/Keys/{key}`.

If the new key fails, the old one stays. Removing the service revokes its key.

### 6. Containment, and what a compromise yields

**What a stolen key yields.** The key is full Jellyfin administration. With it an
attacker can:

- read every library and account;
- create an administrator;
- reopen CORS;
- install a Jellyfin plugin, which runs as code in the Jellyfin container. That
  container mounts the data root read-write.

A compromise of this service reaches Jellyfin, and through Jellyfin the library.
It does not yield the core's administrator password, another service's
credential, the engine or the host.

**What is contained.** Everything around the key limits what code inside the
decline container can reach. None of it makes the key weaker.

| Measure | What it removes |
|---------|-----------------|
| One network shared only with Jellyfin, plus the network its published port needs. It is not on the network the administrative services share. | Reaching the \*arrs, the download clients or any other service |
| Read-only root filesystem, non-root user, every kernel capability dropped, `no-new-privileges` | Persisting or escalating inside the container |
| No data-root mount, no engine socket, no mount except its configuration directory: key (read-only), invitation table (read-only), refusals (read-write) | Reading the library or controlling the stack directly |
| A memory limit, and a rate limit on `POST` | Using it to exhaust the host, or to guess tokens quickly |
| 128-bit random tokens, held only as hashes | Recovering a live token from the service's files |
| Three fixed server-side calls, on account ids from the core's table only, and no route that forwards | Using it as a general path into Jellyfin, which is `C6-R12`'s concern |

**Egress.** Compose cannot stop a container on a bridge network from reaching the
internet. The service needs no egress, and where the engine can refuse it, it is
refused. Where the engine cannot, the table above is the whole of the
containment, and the doctor says so (`A7-R9`).

### 7. Same origin, and Jellyfin's CORS closed

**The page reaches Jellyfin only through its own origin.** The service is a
same-origin proxy of exactly the three calls above: it makes them server-side, for
the one account a valid token names, and passes nothing else through. The browser
never calls Jellyfin.

**The stack then closes Jellyfin's CORS.** At seed, the core writes `CorsHosts` as
an explicit list, round-tripping the full server configuration the way it
round-trips a policy. It reads the result back, and the doctor checks what
Jellyfin answers to a preflight from an unlisted origin (`C6-R13`).

**The list is never empty**, because an empty list reopens CORS on every line
measured. By default it names Jellyfin's own household origin, the address the
front door publishes. Jellyfin's web client is served from that origin and needs
no CORS, so naming it closes CORS to everything else. An operator whose browser
client is served from elsewhere adds that origin, with the consequence stated
(`G5-R12`).

### 8. Two clarifications this proposes

**`D6-R15`.** Replace *"never by a lemonfiber process (`G1-R5`)"* with:

> never by a process whose lifetime is an operator's session — the CLI, the TUI or
> `lemonfiber ui` (`G1-R5`); a service the stack runs under its restart policy
> answers it, whoever built its image.

The requirement is about lifetime, and the wording should say so.

**C6's tier.** A new requirement, beside `C6-R2`:

> A household-tier service MAY hold a credential that is administrative on another
> service only where one operation must be answerable at household reach at any
> hour. It MUST then hold that credential alone, MUST perform only that operation
> through a fixed set of calls, and MUST be confined as `C6` states: no data
> mount, a read-only root, no kernel capabilities, and no network reach beyond the
> service it acts on and the port it publishes.

### 9. Across majors (ADR-0028)

The service's three calls and its header scheme answered identically on 10.10.3,
10.11.11 and 12.1. Because the core's table gives it each invitation's issue time,
it uses the `own-writes` strategy on every line and needs nothing from a line's
profile. It still reads which line is running, and refuses to act on a line
outside the window. Its recordings join the matrix, and CI runs its calls against
every supported line.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **A static page acting through the unclaimed account's own session.** It signs in with the empty password, writes a marker to `DisplayPreferences`, then sets a throwaway password. No administrator credential is involved. It works on all three lines: the empty-password sign-in, the preferences write and the member's own password write each answer 200 or 204. | It refuses by claiming. During the refusal, and for the whole of its effect, the account is enabled and signed in, holding a password nobody knows. *Unclaimable* then rests on that secret never being learned, not on the server refusing the account. The core would read a set password as `active`, and on 12.x, where the password state is not reported, it could not tell a refusal from an acceptance without reading every member's preferences. The marker sits in a store the member can write. The browser has to reach Jellyfin directly, so CORS stays open. |
| **A page that only records the refusal, and the core acts later** | The account stays claimable until the core next runs. That can be days away (`G1-R5`), and `D6-R16` says *at once*. |
| **Create the account only when the invitee accepts** | It conflicts with what an invitation is. D6 makes the account the invitation, `D6-R5` decides access when inviting, `D6-R10` resets by returning an account to unclaimed, `D6-R12` creates the account while Seerr is down, and lemonfiber#763 confirms what an invitation grants before the account is made. Acceptance would also need a lemonfiber process running at whatever hour the invitee accepts. |
| **Hold the administrator's password instead of a key** | It is the same power, and revoking or rotating it disturbs the core, Seerr's owner and every other consumer at once. |
| **Reuse the existing `lemonfiber` key** | A second consumer of a shared key cannot be revoked without breaking the first, and Jellyfin's key list could no longer say which service used it. |
| **A general reverse proxy to Jellyfin under the page's origin** | It is the single hole `C6-R12` refuses, and a bug in the proxy exposes the whole API with the service's key behind it. |
| **The page as a Jellyfin plugin** | It would be code lemonfiber ships into the media server, running with the server's full rights, rebuilt for each major's runtime. It is more power than this service holds, not less. |

## Consequences

### Positive

- A refusal takes effect the moment it is made, whether or not any lemonfiber
  process is running. Jellyfin enforces it at sign-in and on every held token.
- `declined` is reported apart from `expired` and from the operator's own
  `suspended`, from facts the stack keeps.
- Jellyfin's CORS is closed, which it is not today.
- The key is dedicated, named, dated and revocable alone.

### Negative

- A new image, repository and publish pipeline, and the vulnerabilities that come
  with them.
- An administrator-equivalent credential sits in a service that faces the
  household. A compromise of that service can reach the library through a Jellyfin
  plugin install. The containment narrows the path to Jellyfin and does not narrow
  what Jellyfin allows.
- Egress is refused only where the engine can refuse it.
- A declined account stays on the server until the operator acts, where an
  expired one is removed.
- Closing CORS breaks any browser client served from an origin the list does not
  name.
- The proposed C6 requirement also binds Homepage. Homepage holds the core's own
  `lemonfiber` key, which is administrator-equivalent, at the LAN tier, for a
  dashboard widget rather than one operation. Adopting the requirement means
  Homepage stops holding that key, or the requirement names it as an exception.

### Neutral

- The decline address stays on the household network, like the sign-in address
  beside it (`D6-R11`).

## Revisit if

- Jellyfin offers an API key or role narrower than administration that can disable
  an account.
- A lemonfiber process gains a persistent, household-reachable lifetime, which
  would reopen the question of which process answers the address.
- Remote access (`I1`) makes the decline address reachable off the household
  network.
- A supported line changes how a disabled account's sessions or Quick Connect
  authorisations are refused.

## Related

- [D6 Household identity](../../10-functional/features/d-content/d6-household-identity.md):
  `D6-R15`, `D6-R16` and what an invitation is
- [G5 The front door](../../10-functional/features/g-ux/g5-front-door.md): `G5-R14`
- [N9 Who gets in](../../10-functional/features/n-companion/n9-who-gets-in.md): `N9-R7`
- [C6 Web security](../../10-functional/features/c-trust/c6-web-security.md): the
  tiers, `C6-R12` and `C6-R13`
- [A7 Credential management](../../10-functional/features/a-getting-started/a7-credential-management.md):
  the inventory and rotation
- [G1 Interface tiers](../../10-functional/features/g-ux/g1-interface-tiers.md): `G1-R5`
- [ADR-0028](0028-a-supported-major-is-data-proved-by-its-own-recordings.md): lines,
  profiles and the `claimed` strategy
