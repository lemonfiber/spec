# Contract: Jellyfin as Seerr's identity source

**Status:** Accepted

How lemonfiber makes Jellyfin the identity source for Seerr during
[seed](../../10-functional/features/d-content/d1-seed.md), so a household member
signs in to Seerr with their Jellyfin account rather than a second one. Jellyfin
and Seerr read these calls; lemonfiber writes them.

**Satisfies:**
[D1-R7](../../10-functional/features/d-content/d1-seed.md),
[D1-R16](../../10-functional/features/d-content/d1-seed.md),
[D1-R4](../../10-functional/features/d-content/d1-seed.md)

---

## Why this is written down

Connecting Seerr's authentication to Jellyfin is the difference between a
household member having one account or two, and the spec makes it unconditional.
But it is not a single field written to a config file the way a Servarr key is:
it is two services' own setup APIs, driven in order, and — unlike every other
service — Jellyfin has no key on disk for lemonfiber to read. So the shape of
those calls, and the one credential lemonfiber must **mint** to make them, are
recorded here for the same reason the download-client and Prowlarr-application
shapes are: a pinned-version upgrade that moves a field becomes a reviewed change
rather than a runtime surprise.

The field sets below are the ones the pinned Jellyfin (`jellyfin/jellyfin`
`10.11.11`) and Seerr (`ghcr.io/seerr-team/seerr` `v3.5.0`, from `seerr-team/seerr`)
expose. As with every contract here, the writer and this document move together
when a pin advances.

## The one credential lemonfiber mints, not reads

Jellyfin generates no API key to disk and asks its operator to create the first
account through a setup wizard. That is the same shape as qBittorrent's temporary
password ([D1-R16](../../10-functional/features/d-content/d1-seed.md)): there is
nothing durable to read, so lemonfiber **mints** the administrator password,
sets it by driving Jellyfin's own first-run setup, and records it where a later
run — and the Seerr wiring below — can read it back. The generated password is
recorded under `JELLYFIN_ADMIN_PASSWORD`, beside the account name `admin`. As
with qBittorrent, no randomness means no account is created and nothing is
recorded, never a guessable fallback.

If Jellyfin's setup is **already complete** when seed runs — the household set it
up themselves — lemonfiber holds no credential for it and does not have one to
mint. It does not guess or reset one; the Seerr wiring is skipped for that run
with a note that Jellyfin was set up outside lemonfiber.

## Driving Jellyfin's first-run setup

Jellyfin's `/Startup/*` endpoints answer without a credential only until setup
completes; afterwards they answer an administrator alone. That is what makes them
safe to drive exactly once.

1. `GET /System/Info/Public` → `{ "StartupWizardCompleted": <bool>, … }`. This is
   the idempotency gate: a completed wizard is left untouched.
2. `GET /Startup/User` → `{ "Name": "<default name>" }`. On a server nobody has set
   up, this read is what creates the first account.
3. `POST /Startup/User`, JSON `{ "Name": "admin", "Password": "<minted>" }` →
   `204`. It renames the first account to `admin` and sets its password; it does
   not create an account, and answers `404` where none exists yet, which is why step
   2 comes first. An empty `Password` is refused with `400`.
4. `POST /Startup/Complete` → `204`. Setup is finished, and `/Startup/*` stops
   answering without an administrator's credential.

lemonfiber reaches Jellyfin at its published loopback port; the account name and
minted password are what it then hands to Seerr.

## Configuring Seerr against Jellyfin

Seerr is set up in two steps: sign in through Jellyfin, which on a fresh instance
creates the owner and sets the media server, and then a finish step, which is what
actually marks Seerr initialised. The sign-in alone does not complete setup, so
both are the identity wiring.

1. `GET /api/v1/settings/public` → `{ "initialized": <bool>, … }`. It needs no
   session. The idempotency and consent gate: an already-initialised Seerr is
   **never** re-initialised (see below).
2. `POST /api/v1/auth/jellyfin`, JSON:

   ```json
   {
     "username": "admin",
     "password": "<the minted Jellyfin password>",
     "hostname": "jellyfin",
     "port": 8096,
     "useSsl": false,
     "urlBase": "",
     "email": "admin@lemonfiber.local",
     "serverType": 2
   }
   ```

   | Field | What Seerr does with it |
   |-------|-------------------------|
   | `username`, `password` | Forwarded to Jellyfin's `POST /Users/AuthenticateByName` as `Username` and `Pw`. A missing `username` is refused with `500`. |
   | `hostname` | The host alone, with no scheme, port or path. Seerr builds the address as `{http\|https}://{hostname}:{port}{urlBase}`, so a whole URL here yields an address nobody wrote. It is the name Seerr reaches Jellyfin by across the stack's own network — the container name, not the host loopback lemonfiber itself uses. |
   | `port` | Jellyfin's port inside the stack. Stored as `8096` where absent, but the address of this very call is built from the body as sent, so it is always given. |
   | `useSsl` | `https` where true. Stored as `false` where absent. |
   | `urlBase` | A path Jellyfin is served under, empty at the root. Stored as `""` where absent. |
   | `email` | Optional. The owner's address in Seerr; where absent, Seerr files the owner under the Jellyfin account's name. |
   | `serverType` | `2` selects Jellyfin (`1` is Plex, `3` Emby). Read only on the call that sets the media server; any value but `2` or `3` there is refused with `500` (`NO_ADMIN_USER`). |

   On the first call this signs in to Jellyfin as that administrator and:

   - creates the Seerr owner from it, answering `403` (`NOT_ADMIN`) for an account
     that is not a Jellyfin administrator;
   - points Seerr's authentication at Jellyfin;
   - mints a Jellyfin API key named `Seerr` with that session
     (`POST /Auth/Keys?App=Seerr`, then `GET /Auth/Keys`), and writes it with the
     address fields to `settings.json` as `jellyfin.apiKey`, `jellyfin.ip`,
     `jellyfin.port`, `jellyfin.useSsl` and `jellyfin.urlBase`.

3. `POST /api/v1/settings/initialize` — finishes setup, the step that flips
   `initialized` to true, and answers `200` with the public settings. It answers
   only an administrator: the session cookie the sign-in set, carried by the
   transport onto this call, is what authorises it.

Every JSON body is sent with `Content-Type: application/json`, because Seerr's
framework only parses a body it is told is JSON and silently drops one it is not.

### Every later sign-in

The owner's session is what lemonfiber reads and writes Seerr with on later runs,
and a session is opened by the same `POST /api/v1/auth/jellyfin` with
`{ "username": "admin", "password": "<the minted Jellyfin password>" }` and
nothing else. Once Seerr holds a Jellyfin address, it refuses
any sign-in that names one with `500` (`Jellyfin hostname already configured`),
whatever `initialized` says, and signs in against the address it holds.

## Read back, and never override

After writing, `GET /api/v1/settings/public` is read again and its `initialized`
must now be true; only then is the connection called wired
([D1-R4](../../10-functional/features/d-content/d1-seed.md)). A refusal carries
the service's own words rather than a paraphrase.

An **already-initialised** Seerr is left exactly as it is and never
re-initialised — whether it was this that initialised it on an earlier run
(idempotent, so a second run changes nothing) or the household set it up
themselves with local accounts. Switching a running Seerr's identity source would
affect the accounts already on it, so it is treated as the household's own to
change, reported rather than reverted. This is the drift-aware rule the rest of
seed follows, applied to the one connection where overriding would cost a
household its existing sign-ins.

## What ADR-0032 changes

[ADR-0032](../../00-overview/decisions/0032-the-request-service-reaches-the-arrs-through-a-gate.md)
puts a request gate between Seerr and Jellyfin
([D1-R19](../../10-functional/features/d-content/d1-seed.md),
[D1-R20](../../10-functional/features/d-content/d1-seed.md)). Where the gate runs,
the address in step 2 is the gate's Jellyfin route, the gate answers the key mint
itself so Seerr holds no Jellyfin key, and lemonfiber's later calls carry Seerr's
own API key in place of the owner's sign-in. The calls above are the ones the core
on `lemonfiber` main makes.

## Related

- [D1 Service auto-wiring](../../10-functional/features/d-content/d1-seed.md) — the feature this serves, and the household-identity requirement
- [ADR-0032](../../00-overview/decisions/0032-the-request-service-reaches-the-arrs-through-a-gate.md) — the request gate, and what Seerr holds once it runs
- [download-client.md](download-client.md) · [prowlarr-application.md](prowlarr-application.md) — the other written-down wiring shapes
- [versioning.md](versioning.md) — why a pinned stack makes a written-down field set safe
