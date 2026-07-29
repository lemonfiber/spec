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

The field sets below are the ones the pinned Jellyfin (`10.10.3`) and Seerr
(Jellyseerr `v3.3.0`) expose. As with every contract here, the writer and this
document move together when a pin advances.

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

Jellyfin's `/Startup/*` endpoints are unauthenticated and answer only until setup
completes, which is what makes them safe to drive exactly once.

1. `GET /System/Info/Public` → `{ "StartupWizardCompleted": <bool>, … }`. This is
   the idempotency gate: a completed wizard is left untouched.
2. `POST /Startup/User`, JSON `{ "Name": "admin", "Password": "<minted>" }` —
   creates the administrator.
3. `POST /Startup/Complete` — finalises setup, after which the `/Startup/*`
   endpoints stop answering.

lemonfiber reaches Jellyfin at its published loopback port; the account name and
minted password are what it then hands to Seerr.

## Configuring Seerr against Jellyfin

Seerr (Jellyseerr) is set up in two steps: sign in through Jellyfin, which on a
fresh instance creates the owner and sets the media server, and then a finish
step, which is what actually marks Seerr initialised. The sign-in alone does not
complete setup, so both are the identity wiring.

1. `GET /api/v1/settings/public` → `{ "initialized": <bool>, … }`. The
   idempotency and consent gate: an already-initialised Seerr is **never**
   re-initialised (see below).
2. `POST /api/v1/auth/jellyfin`, JSON:

   ```json
   {
     "username": "admin",
     "password": "<the minted Jellyfin password>",
     "hostname": "http://jellyfin:8096",
     "email": "admin@lemonfiber.local",
     "serverType": 2
   }
   ```

   `hostname` is the address Seerr reaches Jellyfin on across the stack's own
   network — by container name, not the host loopback lemonfiber itself uses.
   `serverType` `2` selects Jellyfin (not Plex or Emby). On the first call this
   creates the Seerr owner from that Jellyfin administrator and points Seerr's
   authentication at Jellyfin.
3. `POST /api/v1/settings/initialize` — finishes setup, the step that flips
   `initialized` to true. The session cookie the sign-in set, carried by the
   transport onto this call, is what authorises it.

Both writes carry `Content-Type: application/json` for their JSON bodies, because
Seerr's framework only parses a body it is told is JSON and silently drops one it
is not.

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

## Related

- [D1 Service auto-wiring](../../10-functional/features/d-content/d1-seed.md) — the feature this serves, and the household-identity requirement
- [download-client.md](download-client.md) · [prowlarr-application.md](prowlarr-application.md) — the other written-down wiring shapes
- [versioning.md](versioning.md) — why a pinned stack makes a written-down field set safe
