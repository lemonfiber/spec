# ADR-0058: A Plex member signs in by Plex's own code, and what they may watch is said in Plex's terms

**Status:** Accepted
**Date:** 2026-11-04
**Decided:** 2026-11-04, by the maintainer, Wessel Verheij:

- a member of a Plex household signs in to lemonfiber by a code plex.tv shows them, and
  no member's password passes through lemonfiber;
- the certificates an age limit is said in are those Plex's libraries hold, aged by a
  table the plugin keeps for the owner's plex.tv country;
- a suspended account is kept, open to no library;
- an account's sessions are those the server lists as playing.

**Amends** [ADR-0057](0057-plex-serves-the-household-without-handing-out-its-owners-token.md):
§7. A member of the household it reads signs in to lemonfiber by a plex.tv code, and what
each may watch is written as below.

## Context

`identity.source@1` was written against a media server that keeps its own accounts. It
signs a member in with the name and password the server holds (`whoever`), sets an
invited account's first password (`claim`), and reads a rating table the server keeps
with an age for each certificate.

Plex holds none of these. Its accounts are plex.tv's:

- A shared member is an account of their own at plex.tv.
- A Home account belongs to the Home of the account that claimed the server.
- Nobody's password is the server's to check.
- plex.tv signs a device in by a PIN the member approves at `plex.tv/link`. This works
  whether or not the account asks for a second factor.

Plex keeps no ages:

- An item carries the certificate its agent read, prefixed with the country for most
  countries.
- A share is limited by a filter of those certificates.
- A Home account is limited by a restriction profile.
- No account can be switched off.
- The server lists the sessions playing, not the devices signed in.

[ADR-0057](0057-plex-serves-the-household-without-handing-out-its-owners-token.md) §7 reads
the household and makes, takes back and withdraws invitations (`ARCH-R371`). It does not
say how a member of that household signs in to lemonfiber, or how what they may watch is
written.

## Decision

### 1. A member signs in by a code

`identity.source@1` gains two operations at minor `1` (`ARCH-R375`):

- `sign_in_by_code` makes a code at the outside service for a device, and answers where
  to approve it and when it lapses.
- `signed_by_code` answers the member the approved code proved, checked against the
  household (`ARCH-R377`).

Over Plex the code is a plex.tv PIN. The adapter:

1. makes the PIN;
2. reads the account it was approved for;
3. answers it only where that account is a Home account or a share of this server, and is
   not the request service's own.

`whoever` and `claim` answer `unsupported`. `standing` asks plex.tv with the token the code
granted, then reads the account in the household again. No member's password passes
through lemonfiber or the adapter.

The core's sign-in surface for a code is the core's to build, and comes with its own rows.

### 2. Certificates in Plex's own terms

`ratings` answers the certificates Plex's libraries hold, each at the age the plugin's
table holds it at for the country of the plex.tv account that claimed the server, which
`country` answers. The table is the plugin's: Plex keeps none, and the core holds only a
fallback ladder. Where the table does not hold that country, `ratings` answers none. The
core then names its own mapping and says in the answer that it is lemonfiber's (`ARCH-R378`).

How `allow` and `claimable` write a limit:

| Account | Libraries | Age limit |
|---|---|---|
| A share | Its libraries | A content-rating filter. With unrated content held back, it admits only the certificates at or under the limit. With unrated content let through, it refuses those above the limit |
| A Home account | Its libraries | The restriction profile nearest at or under the limit |

### 3. Suspending keeps the account

`suspend` keeps the share or Home account and opens it to no library. A later `allow`
opens its libraries again.

### 4. Sessions are what is playing

`sessions` answers the account's sessions that the server lists as playing.

### What follows without a choice

| Operation | Over Plex |
|---|---|
| `startup_completed` | Whether the server is claimed |
| `create_admin`, `replace_admin_password` | `unsupported`: setup is `owner.claim`'s, and the owner's password is plex.tv's |
| `claimable` | The same narrowing as `allow`; plex.tv bounds the guesses at a member's password |
| `signs_devices_in` | True |

## Alternatives considered

| Alternative | Why not |
|---|---|
| `whoever` signing in at plex.tv with the member's name and password | Every member's plex.tv password would pass through lemonfiber, and an account with a second factor could not sign in |
| No sign-in for a Plex member until later | A household it reads could not reach lemonfiber's own surfaces |
| No age limits over Plex, libraries only | Parental controls would fall away on a Plex stack |
| Refusing `suspend` | Plex can keep an account and open it to nothing, which is what switching it off is for |
| Refusing `sessions` | What is playing is what the server can say, and the operator asks for it |

## Consequences

- No member's password crosses lemonfiber on a Plex stack.
- The plugin keeps a table of certificates and ages by country, and keeps it true as
  rating boards change.
- A country missing from it falls back to the core's ladder, and the answer says so.
- `identity.source@1` gains its first minor. Sources recorded before it pass the two new
  cases as `unsupported`.

## Related

- [ADR-0057](0057-plex-serves-the-household-without-handing-out-its-owners-token.md) — the Plex household this signs in
- [capability-contracts.md](../../20-architecture/contracts/capability-contracts.md) — `ARCH-R371`, `ARCH-R375`, `ARCH-R377`, `ARCH-R378`
- [D6](../../10-functional/features/d-content/d6-household-identity.md) — the household's accounts
