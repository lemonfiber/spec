# ADR-0057: Plex serves the household without handing out its owner's token, unless the operator opts in

**Status:** Accepted
**Date:** 2026-10-31
**Decided:** 2026-10-31, by the maintainer, Wessel Verheij:

- a media server is given a library for each media type the stack files by a
  `media.serve` operation the core asks on every seed, which Plex answers by adding the
  library and never by changing one the operator arranged;
- the request service is linked to Plex in one of three modes the operator chooses:
  `managed`, the default, `owner`, an opt-in that names its cost, and `fronted`;
- the request service's Plex traffic passes through the request gate in every mode;
- household members ask through lemonfiber's own surfaces in every mode, and sign in to
  the request service's own page with Plex where the mode allows it;
- a Plex household is the owner's Home accounts and the plex.tv accounts the server is
  shared with.

**Amends**:

- [ADR-0032](0032-the-request-service-reaches-the-arrs-through-a-gate.md): §1 gains a
  route for Plex, §2 what the request service holds on it, and §3 the calls it answers;
  in `fronted` mode the gate also answers the request service's plex.tv calls and has
  egress to plex.tv for one of them.

## Context

Plex is the media server of a lemonfiber stack once the Plex plugin is installed. The
adapter claims Plex with the code plex.tv shows the operator, and reads the token Plex
keeps for that account from Plex's own `Preferences.xml` on every call, never holding it
beyond the call (`ARCH-R364`). The plugin's old first-run recipe also made Plex's
libraries and handed that token to the request service. Neither can be done that way.
A claimed Plex refuses the recipe's unauthenticated reads, and the token is the
account's own.

**What the request service does with Plex.** Seerr `v3.5.0`, the pinned request service
(`server/routes/auth.ts`, `server/api/plextv.ts`, `server/api/plexapi.ts`,
`server/lib/refreshToken.ts`):

- Its first sign-in with a Plex token creates its owner. It reads that token's account
  from plex.tv (`/users/account.json`), keeps the token as the owner's, and makes Plex its
  media server.
- It reads Plex's libraries, contents and items with the owner's token (`/`,
  `/library/sections`, `/library/sections/{id}/all`, `/library/metadata/{key}`,
  `/library/metadata/{key}/children`).
- It checks the owner's token at plex.tv every day (`/api/v2/ping`).
- It lets anyone but the owner sign in with Plex only if plex.tv lists them on the
  owner's `/api/users` with this server's identifier. So a member's Plex sign-in needs
  the owner's token, or something answering for plex.tv in its place.
- Its plex.tv address is fixed in its code.

**What Plex offers in its place.**

- **No narrower token.** A transient token (`/security/token?type=delegation&scope=all`)
  has "the same access level as the caller's token" for up to 48 hours (Plex's own API
  document). Plex's JWTs are the account's, and their scopes restrict nothing (Plex's
  developer forum).
- **A managed Home account.** It needs no Plex Pass, is no administrator, sees only the
  libraries shared with it, and is removed by the Home's owner. A Home holds 15 members
  at most (Plex support, *What is Plex Home?*).
- **Libraries are added** with `POST /library/sections` (name, type, agent, scanner,
  language, location), checked on the pinned Plex for films, series and music.

[C6-R20](../../10-functional/features/c-trust/c6-web-security.md) keeps every credential
that is administrative on another service out of a household-tier service, and the
request service is one. The owner's Plex token is administrative on Plex and on the
owner's whole plex.tv account.

## Decision

### 1. A media server is given its libraries

`media.serve@1` declares `furnish` (`ARCH-R369`). The core hands it each media type the
stack files, with the folder the media server reads it at, beneath the data root's
`media/<type>`. The filler adds a library for each type whose folder exists and that no
library reads, and answers for each type whether a library now reads it. It never renames,
re-points or removes a library, so what the operator arranged stays theirs. A type the media
server does not take is answered not held, never refused. The core asks it at install's
first run and on every seed, once `owner.claim` answers `Ours`. Plex answers it with
`POST /library/sections`; the other media servers answer it as they come to.

### 2. The request service has a Plex account of its own

In every mode, lemonfiber mints the request service a managed account in the Plex Home of
the account that claimed Plex, and shares every library with it (`ARCH-R370`). It is
`media.serve`'s key for an app, minted, listed, dated and revoked over that contract. It
takes one of the Home's fifteen places. Its token is what Plex is read with on the request
service's behalf.

### 3. Three modes, the operator's choice

The mode is kept in the stack's environment file as `PLEX_LINK_MODE`, `managed` where it
is absent. Changing it is one setting change, rehearsed before it is applied (`F13-R4`) and
journalled (`E4-R1`) (`C6-R26`).

| | `managed` (default) | `owner` (opt-in) | `fronted` |
|---|---|---|---|
| The request service's owner | Its own Plex account (§2) | The operator's own Plex account | Its own Plex account (§2) |
| The token it holds as its owner's | That account's token, carried to it once by the core | One plex.tv issued to it when the operator signed in through Plex's own sign-in on its page; the core never carries it | A token lemonfiber mints for the gate |
| Its plex.tv calls | To plex.tv, as its own account | To plex.tv, as the operator | To the gate, which answers them (§5) |
| Members sign in to its page with Plex | Not offered: its owner shares nothing, so plex.tv lists nobody | Offered | Offered |
| Consent | None beyond install | The rehearsal states the cost and the operator confirms it (below) | The rehearsal states that the request service will resolve plex.tv to the gate and trust a certificate authority lemonfiber makes for it alone |
| Revocation | Revoking the key removes the account, and the gate stops admitting its token | The operator signs the request service's device out at plex.tv, which the rehearsal names | The gate token is revoked at the gate, as ADR-0032's are |

**`owner`'s cost**, stated in the rehearsal before the operator confirms: the request
service, a household-tier service, would hold a token of the operator's own Plex account.
Anything that took the request service over could act as that account at plex.tv: claim
and share servers, and read the account. The confirmation is the opt-in C6-R20 allows
(`C6-R26`).

**When a mode can change.** The request service cannot change which Plex account its
owner is once it is set up, and lemonfiber never sets it up again (the
jellyfin-seerr-identity contract's *Read back, and never override*). So:

- `owner` is chosen before the request service is first set up. Entering it, or
  leaving it, for a request service already set up is refused, naming that the request
  service would have to be set up again.
- `managed` and `fronted` share an owner, so switching between them is a re-sign-in of
  that owner with the other token.

### 4. The request service's Plex traffic passes through the gate

ADR-0032's gate gains a Plex route. The request service is told the gate's Plex route as
Plex's address, and has no other path to Plex (`C6-R22`). The route answers the five reads
above and nothing else, and builds each upstream request with the request service's Plex
account token (§2), whatever the request service presented (`C6-R27`). What it admits
depends on the mode:

- `managed`: the hash of that account's token;
- `owner`: a token plex.tv answers as the account that claimed Plex, asked of plex.tv once
  per token and kept as its hash;
- `fronted`: the gate token.

So Plex is read as the request service's own account in every mode, and the operator's
token, where it is held, is never what Plex is read with.

### 5. In `fronted` mode the gate answers for plex.tv

The request service resolves `plex.tv` and `discover.provider.plex.tv` to the gate, and
trusts a certificate authority the core makes for the gate alone, whose certificate names
only those hosts (`C6-R28`). The gate answers:

- `/users/account.json` and `/api/v2/ping` presenting the gate token: as the request
  service's own account, from what the core applies to it;
- `/api/users` presenting the gate token: the household's Plex accounts with access to
  this server, read through `identity.source` (§7), each with this server's identifier;
- `/api/resources` presenting the gate token: this server alone;
- `/users/account.json` presenting any other token, as a member's own from Plex's
  sign-in: forwarded to plex.tv unchanged, its answer handed back. It is the gate's only
  egress.

Everything else is refused unforwarded. The request service's Plex watchlist sync, which
reads each member's watchlist from plex.tv, is therefore not offered in `fronted` mode.

### 6. Members ask through lemonfiber

On a Plex stack, as on every other, a member asks through lemonfiber's own surfaces, which
ask the request service on their behalf over `request.intake`. The request service's own
page signs members in with Plex only in `owner` and `fronted`. The doctor reports, every
run:

- the mode;
- whose Plex account the request service's owner is;
- whether members can sign in to its page with Plex;
- in `owner`, the cost above as a standing notice (`D1-R27`).

### 7. A Plex household

`identity.source` over Plex reads the household as the owner's Home accounts and the
plex.tv accounts the server's libraries are shared with (`ARCH-R371`). An invitation shares
the libraries with the plex.tv account it names. Taking one back, or withdrawing a member,
removes that share, or the Home account where the member is one. The request service's own
account (§2) is never a member.

## Consequences

- Plex's owner token never leaves the adapter in `managed` and `fronted`. In `owner` it
  reaches the request service only through the operator's own sign-in, after a confirmed
  rehearsal that names the cost.
- The gate's reach grows by Plex in every mode and by one plex.tv path in `fronted`. Its
  confinement is otherwise unchanged.
- One Home place is the request service's.
- `fronted` makes lemonfiber answer for plex.tv inside the request service's container,
  with a certificate authority nothing else trusts.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Only `managed` | The household could not sign in to the request service's page with Plex at all; the maintainer chose to offer it where a mode allows it. |
| The owner's token by default | It puts a token of the operator's whole plex.tv account in a household-tier service, against C6-R20. Kept only as a named opt-in. |
| A transient or JWT token in place of the owner's | Neither is narrower: a transient token has the caller's access, and JWT scopes restrict nothing. |
| The Plex adapter making libraries at claim, as Komga's does | It ties a media type's folder to each adapter's constants, and nothing keeps it true as the stack's media types change. `furnish` is asked with the stack's own. |
| The request service talking to Plex directly in `managed` | Its token there is no administrator's, but a fixed call list at the gate is narrower still, and one path for every mode keeps the doctor's account of it simple. |

## Related

- [ADR-0032](0032-the-request-service-reaches-the-arrs-through-a-gate.md) — the request gate this extends
- [ADR-0050](0050-a-contract-hands-its-filler-all-it-enforces-and-reads-back-no-secret.md) — no secret read back
- [C6](../../10-functional/features/c-trust/c6-web-security.md) — `C6-R20`, `C6-R22`, `C6-R24`, `C6-R26`–`C6-R28`
- [D1](../../10-functional/features/d-content/d1-seed.md) — `D1-R27`, `D1-R28`
- [capability-contracts.md](../../20-architecture/contracts/capability-contracts.md) — `ARCH-R369`–`ARCH-R371`
- [jellyfin-seerr-identity.md](../../20-architecture/contracts/jellyfin-seerr-identity.md) — the Jellyfin counterpart
