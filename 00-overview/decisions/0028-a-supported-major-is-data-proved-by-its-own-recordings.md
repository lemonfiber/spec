# ADR-0028: A supported major is data the stack declares, proved by its own recordings

**Status:** Proposed
**Date:** 2026-09-25

## Context

The stack runs one version of the media server, and the core is written against
that one. `lemonfiber-media-stack` pins `jellyfin/jellyfin` at tag `10.10.3`, in
`stack.toml` and in `compose/media.yml`, with no digest. `E1-R1` and the
[stack manifest](../../20-architecture/contracts/stack-manifest.md) require a
digest, and the pin does not carry one yet. The
[identity contract](../../20-architecture/contracts/jellyfin-seerr-identity.md)
states the posture plainly: *the writer and this document move together when a
pin advances.* One version at a time, and the code follows the pin.

Upstream has moved twice since that pin. The release list shows:

| Line | Releases | Standing upstream |
|------|----------|-------------------|
| 10.10 | 10.10.3 (2024-11-19) to 10.10.7 (2025-04-05) | Ended |
| 10.11 | 10.11.0 (2025-10-20) to 10.11.11 (2026-06-06) | Ended |
| 12 | 12.0 (2026-09-08), 12.1 (2026-09-15) | Current stable |

**"v12" is Jellyfin 12.** At 12.0 upstream dropped the leading `10.`. The release
after 10.11 is 12.0: the first number is now the major and the second the minor.
`GET /System/Info/Public` on the 12.1 image answers `"Version": "12.1.0"`.
Before 12, upstream treated `10.x` as the major. 10.10 to 10.11 is a one-way database
migration, so J7 labelling `10.10.3 → 10.11.0` a *minor* reads the number and misses
the jump.

**What differs, measured.** On 2026-09-25 the three images were run side by side:
`10.10.3` (`sha256:17c3a8d9…bc221`), `10.11.11` (`sha256:aefb67e6…35db`) and `12.1`
(`sha256:78d3ea12…dd7e`), as pulled. The calls the core makes, and the ones the
household work depends on, were each issued against all three:

| Behaviour | 10.10.3 | 10.11.11 | 12.1 |
|-----------|---------|----------|------|
| Sign-in with the core's `X-Emby-Authorization` header | 200 | 200 | **400** |
| A token in `X-Emby-Token`, `X-MediaBrowser-Token` or `?api_key=` | accepted | accepted | **401** |
| A token in `Authorization: MediaBrowser … Token="…"`, or `?ApiKey=` | accepted | accepted | accepted |
| `HasPassword` on an account with no password | `false` | `false` | **`true`** |
| Rating value of `TV-PG` in `/Localization/ParentalRatings` | 13 | **10** | 10 |
| A second rating dimension (`MaxParentalSubRating`, `RatingScore.subScore`) | absent | present | present |
| Fields a new account's policy returns, nulls omitted | 42 | the same 42 | the same 42 |
| A partial policy body | 400 | 400 | 400 |
| `IsDisabled=true`: sign-in, then an existing token | 403, 401 | 403, 401 | 403, 401 |
| An administrator authorises a Quick Connect code for another user, and the session issued is that user's | 200, yes | 200, yes | 200, yes |
| `GET /Items` with no token | 401 | 401 | 401 |
| `GET /Videos/{id}/stream?static=true` with no token | **200, the file** | **200, the file** | **200, the file** |
| `GET /Items/{id}/Download` and the HLS playlist with no token | 401 | 401 | 401 |
| `CorsHosts` default, and an empty list | `["*"]`, reads as `*` | same | same |
| An API key's reach | full administration | same | same |

Three rows decide the shape of this ADR. The core as it stands cannot sign in to
12.1 at all. On 12.x an account's password state is no longer reported: upstream
marks `HasPassword` *"no longer provided"* and `HasConfiguredPassword` *"always
true"* in `UserDto.cs` at `v12.1`. That is the field D6's *unclaimed* state is read
from today. And 10.11 changed what the integer the core writes to
`MaxParentalRating` means: the same number admits different ratings on the two
lines.

**Moving between lines is one-way.** Upstream requires 10.10.7 before the 10.11 or 12
migration and supports no other starting point. From 10.10.5, the server refuses to
start on a migrated database. The 12.0 notes say rolling back needs a full restore.
10.10.3, the current pin, cannot migrate directly.

**The version that runs is not always the one pinned.** In native mode
([ADR-0007](0007-dual-mode-jellyfin.md)) the operator installs the media server,
and lemonfiber neither pulls it nor chooses its version (`B2-R15`).

Two precedents already exist. `api.version` on a `servarr` service makes the API
generation *"data the manifest carries rather than a guess the client makes"*. The
manifest format supports *"the current `schema_version` and exactly one
predecessor"* (`ARCH-R7`).

## Decision

**A bundled service may declare more than one supported major. Each is a line in
the stack manifest, with its own digest, an API profile the core's client reads,
and recordings from that digest that prove every claim and every call the core
makes. The core detects which line is running and uses that line's profile. No
code compares version numbers.** Jellyfin is the first service to have two lines.

### 1. A line is declared, and pinned by digest

```toml
[[service]]
id           = "jellyfin"
image        = "jellyfin/jellyfin"
api          = { kind = "jellyfin", key_source = "generated" }
default_line = "12"

[[service.line]]
line     = "10.10"
tag      = "10.10.7"
digest   = "sha256:…"
profile  = "profiles/jellyfin/10.10.toml"
standing = "leaving"

[[service.line]]
line     = "12"
tag      = "12.1"
digest   = "sha256:…"
profile  = "profiles/jellyfin/12.toml"
standing = "supported"
from     = ["10.10.7", "10.11"]
```

Each line carries its own digest and tag (`E1-R1`). `from` names the versions
upstream supports a direct upgrade from. A service declaring one line has the shape
every service has today.

### 2. A profile is what the client reads, and it is data

A profile lives in `lemonfiber-media-stack` beside the pin and reviews as a diff. It
may declare:

| Field | What it says | Example, line 12 |
|-------|--------------|------------------|
| `reports` | The pattern `Version` in `GET /System/Info/Public` must match | `^12\.` |
| `auth` | Which scheme, from the set the client implements, carries a token | `mediabrowser-authorization` |
| `operations` | For each operation the core performs: method, path and the strategy that performs it | `disable = { method = "POST", path = "/Users/{id}/Policy", strategy = "policy-round-trip" }` |
| `claimed` | Which strategy tells a claimed account from an unclaimed one | `own-writes` |
| `ratings` | Where a rating's value is read in `/Localization/ParentalRatings`, and which policy fields a limit is written to | `RatingScore.score`, `RatingScore.subScore`; `MaxParentalRating`, `MaxParentalSubRating` |
| `bytes` | The recorded answer to an anonymous byte request | `open` |

Ratings are read from the running server rather than tabulated, because the table
is the server's own and changed between lines.

### 3. What "without code changes" covers, and what it cannot

**Covered, as data:**

- A new tag and digest within a line.
- A new line whose differences are paths, field names, where a value is read, or
  which *existing* strategy an operation uses.
- The version pattern, the default line, and a line's standing, including its
  retirement.

**Not covered: a behaviour that differs in kind.** Where a new line removes the
thing an existing strategy relies on, no data can select a strategy that does not
exist. The measured cases:

- **12 refuses the legacy headers the core sends.** The modern header was
  accepted by all three lines measured, so it replaces the legacy one for every
  line. It is a one-time change and needs no variant.
- **12 stops reporting whether an account has a password.** D6's unclaimed
  state needs a second `claimed` strategy. The proposal, which is inferred and
  has not been proved against a recording yet: `own-writes`. The core records
  when it made or reset an account, taking the time from Jellyfin's own activity
  entry for that write. A later `UserPasswordChanged` entry for that account is
  then a claim. A reset and a claim both write `UserPasswordChanged`, as measured
  on 10.10.3 and 12.1, so only the ordering tells them apart.

**How such a change is contained.** A new behaviour is a *named strategy* in that
service's client, and a profile selects it:

- A strategy is written once and proved by the recordings of every line that
  names it.
- The core never compares a version, so a strategy is never an
  `if version >= 12`.
- A new strategy is a core release, and the profile that selects it is data.
- A pinned line whose profile names a strategy this binary lacks is refused by
  naming the strategy, the way a manifest's unmet requirement names the
  capability (`F3-R21`).

### 4. The running line is detected, never assumed

The core reads `GET /System/Info/Public` and matches its `Version` against each
line's `reports`. On every line measured, this read needs no credential. The match
has three outcomes:

- **The running version matches a line.** The core uses that line's profile.
- **It matches a line other than the one pinned.** This happens in native mode or
  with an image pulled by hand. The core uses the running line's profile, and the
  doctor reports the difference.
- **It matches no line.** Every call to the media server is refused, naming the
  running version and the lines supported. Nothing is guessed.

A detection is a reading and carries its age like any other.

### 5. Every line proves every claim, and CI runs the whole matrix

A bundled service binds its capability probes the way a plugin does (`ARCH-R109`),
once per line:

- The capabilities are `media.serve` and `identity.source`, and every probe
  they declare is bound on each line.
- Each probe's recording names that line's digest as `recorded_from`.
- Each operation in a line's profile has a recorded exchange from that digest.
- The recordings are readable data (`F10-R5`) and are reported as proofs against
  recordings (`F10-R6`).

The recordings live beside the profiles in `lemonfiber-media-stack`, and the core
embeds them with the stack. The core's CI runs its client, every claim and every
operation against the recordings of every line the manifest declares. A version does not ship while any line's
claim or operation is refused. That is `F9-R2`, applied per line. Moving a line's
pin means re-recording that line in the same change.

### 6. The contract says which line is running, and behaviour arrives as capabilities

The services envelope (`GET /api/services` and the `--json` it mirrors) carries
four fields per service:

- `line`
- `running_version`, as read
- `tag` and `digest`, as pinned
- `line_standing`: `supported`, `leaving`, `outside` or `unread`

The companion reads these to show them. It does not derive behaviour from them. A
feature the running line cannot perform arrives as absent or `unconfigured` in
`/api/capabilities` (`ARCH-R78`), so no client carries a table of which line does
what.

### 7. The operator chooses a line, and moving is optional

- **Choosing a line.** A new installation takes `default_line`. An existing one
  stays on its line, and staying is never nagged about (`E1-R14`).
- **Moving is an update across a major** (`E1-R10`):
  - It states that the move is irreversible (`E1-R3`).
  - It backs up first (`E1-R4`).
  - It takes the path the target line's `from` declares. From 10.10.3 that means
    through the 10.10 line's pin, 10.10.7, first.
- **Going back is restoring the backup taken before the move** (`E1-R8`,
  `E4-R5`). No line is ever downgraded in place, because upstream refuses to
  start on a migrated database.

### 8. The window: at most two lines, chosen by upgrade path

A service supports an explicit list of lines, never more than two at once:

- the newest stable major upstream ships, and
- one predecessor that upstream supports a direct upgrade from.

That is N-1 by upgrade path rather than by number. For Jellyfin today the two
lines are:

- **10.10, pinned at 10.10.7.** 10.10.7 is the one 10.10 release upstream
  supports migrating from.
- **12, pinned at 12.1.**

10.11 is not a line. 10.10.7 migrates directly to 12, so 10.11 would add a
recording set without adding an option.

- **When a line leaves.** A line is marked `leaving` for at least one lemonfiber
  release before it is removed. The doctor and the services envelope say so.
- **Known advisories.** A leaving line states the published advisories that its
  pin carries and the next line fixes.

### 9. Bytes are open on every line, and the guard does not read the line

On all three lines an anonymous `GET /Videos/{id}/stream?static=true` returns
the file, while the catalogue, the download route and the HLS playlist refuse. The
source matches:

- `VideosController` and `AudioController` carry no `[Authorize]` on these
  actions at any tag from `v10.10.3` to `v12.1`.
- No fallback policy is registered.
- Upstream issue #13984, *"Video streams unauthenticated"*, is open.

So the media server enforces discovery and not bytes. The playback grant proposed
in spec#537 rests on the Quick Connect row above, which holds on all three lines,
and on this: a member's session limits what the member can find, not what bytes
an item id fetches. `media.serve`'s `guarded`
probe asks for the catalogue, and it passes on every line even though bytes are
open.

The front-door guard the maintainer has decided for byte requests is therefore
needed on every line, and it is never relaxed per line:

- **`bytes` is a recorded fact in each profile**, proved by that line's recording
  of the anonymous request.
- **A doctor check asserts that the guard refuses that same request.** It is proved
  by firing on a recording taken with no guard in front (`F10-R11`), so it tests
  the guard rather than the media server.
- **A future line whose recording shows a refusal changes that line's fact, and
  the guard stays in place.** Dropping a guard because a version number says it is
  unnecessary is the version branching this decision forbids.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **One line at a time; the code follows the pin (today)** | Every major becomes a flag day for every operator at once. Because upstream's upgrades are one-way, an operator can neither hold back nor try the new line and return. That is the migration optionality the decision exists to keep. |
| **Branch on the version number in code** | The client carries a table of which release does what, which is the second copy of a changelog that `ARCH-R78` refuses for the contract. Native mode running an unlisted version then passes silently through whichever branch its number falls into. |
| **Probe behaviour at run time instead of declaring it** | Finding out which header, field or strategy works by trying it means writes and sign-ins against a live server. A failed sign-in increments the account's `InvalidLoginAttemptCount` and disables it at `LoginAttemptsBeforeLockout` (`UserManager.cs`, at `v10.10.3` and `v12.1`), and testing whether an account is claimed by signing in as it records a failed attempt against a member who has a password. Nothing discovered at run time can be proved in CI. |
| **Each major as a separate plugin claiming `media.serve`** | Two claimants of one capability collide (`F4-R8`). The client that differs is the core's own code, and a plugin cannot carry code (`F3-R6`). |
| **Support every line upstream has shipped** | The recording matrix grows without bound, and lines upstream has stopped patching accumulate advisories nobody fixes. |
| **Follow upstream's newest line only** | It removes the option this decision exists to give. With one-way upgrades, the newest line without a supported predecessor is the flag day above. |

## Consequences

### Positive

- An operator can stay on 10.10 while 12 is proved, and move when they choose,
  with a backup and a stated way back.
- A new pin within a line, or a line that only reshuffles known strategies, is a
  data change reviewed as a diff.
- Every supported line is proved in CI against recordings from its own digest,
  and a line the core cannot serve is refused by name rather than half-served.
- Native mode gets a checked answer to *which version is this* rather than an
  assumption.

### Negative

- Two recording sets to keep, re-recorded whenever either pin moves.
- Before 12 works at all, the core needs a one-time change: the modern
  `Authorization` header, and an `own-writes` strategy for claimed accounts, which
  has yet to be proved.
- The stack manifest gains `[[service.line]]` and `default_line`. Before the first
  release candidate this changes the schema in place (`ARCH-R43`), and afterwards
  it increments it.
- The pin has to move from 10.10.3 to 10.10.7 and gain digests on both lines
  before either line meets `E1-R1`.
- The 10.10 line carries published advisories that only a later line fixes.
  Keeping it keeps them, stated rather than hidden.
- A native-mode server on a version between lines, 10.11 today, is refused until
  it moves to a line.

### Neutral

- A service with one line behaves exactly as today.
- The rule that no code compares a version number applies to every service, and
  Jellyfin is only the first with two lines.

## Revisit if

- Upstream makes the byte endpoints require a token on a line in the window.
- Upstream reports an account's password state again, making `own-writes`
  unnecessary.
- A second bundled service needs two lines and the profile fields above do not fit
  it.
- Keeping two lines' recordings current costs more than the migration option is
  worth to operators.

## Related

- [E1 Stack updates](../../10-functional/features/e-maintenance/e1-stack-updates.md):
  pins, majors and irreversibility
- [E4 Rollback](../../10-functional/features/e-maintenance/e4-rollback.md): where a
  migration means restore
- [F9 Capabilities of the bundled services](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md)
  and [F10 Authoring](../../10-functional/features/f-extensibility/f10-authoring.md):
  claims, recordings and `fires_on`
- [D6 Household identity](../../10-functional/features/d-content/d6-household-identity.md)
  and [D8 Parental controls](../../10-functional/features/d-content/d8-parental-controls.md):
  what the per-line differences touch
- [Stack manifest](../../20-architecture/contracts/stack-manifest.md) ·
  [Capability vocabulary](../../20-architecture/contracts/capability-vocabulary.md) ·
  [Versioning](../../20-architecture/contracts/versioning.md) ·
  [Web API](../../20-architecture/contracts/web-api.md)
- [ADR-0007](0007-dual-mode-jellyfin.md): native mode, where lemonfiber does not
  choose the version
- [ADR-0023](0023-a-pin-is-a-digest.md): a pin is a digest
