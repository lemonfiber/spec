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

| Major | Releases | Standing upstream |
|-------|----------|-------------------|
| 10 | 10.10.3 (2024-11-19) to 10.10.7 (2025-04-05), then 10.11.0 (2025-10-20) to 10.11.11 (2026-06-06) | Ended; 10.11.11 is the last 10.x |
| 12 | 12.0 (2026-09-08), 12.1 (2026-09-15) | Current stable |

**"v12" is Jellyfin 12.** At 12.0 upstream dropped the leading `10.`. The release
after 10.11 is 12.0: the first number is now the major and the second the minor.
`GET /System/Info/Public` on the 12.1 image answers `"Version": "12.1.0"`.
There is no Jellyfin 11. Before 12, upstream shipped its large changes as `10.x`
releases, and 10.10 to 10.11 in particular carries a one-way database migration.

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
`MaxParentalRating` means: the same number admits different ratings on 10.10 and
10.11.

**Some moves are one-way, including one inside major 10.** Upstream's 10.11 and 12
migrations start only from 10.10.7 (or, for 12, from 10.11.x). The 10.11.0
announcement says upgrading from any other version *"is NOT supported and WILL
fail"*. From 10.10.5, a 10.10 server
refuses to start on a database 10.11 has migrated. The 12.0 notes say rolling back
needs a full restore. 10.10.3, the current pin, cannot migrate directly.

**The version that runs is not always the one pinned.** In native mode
([ADR-0007](0007-dual-mode-jellyfin.md)) the operator installs the media server,
and lemonfiber neither pulls it nor chooses its version (`B2-R15`).

Two precedents already exist. `api.version` on a `servarr` service makes the API
generation *"data the manifest carries rather than a guess the client makes"*. The
manifest format supports *"the current `schema_version` and exactly one
predecessor"* (`ARCH-R7`).

## Decision

**A bundled service may declare more than one supported major. Each major is a
line in the stack manifest, with its own digest, an API profile the core's client
reads, and recordings from that digest that prove every claim and every call the
core makes. A line is split only on a major version, and its pin always follows the
newest release of that major. The core detects which line is running and uses that
line's profile. No code compares version numbers.** Jellyfin is the first service to
have two lines: 10 and 12.

### 1. A line is declared, and pinned by digest

```toml
[[service]]
id           = "jellyfin"
image        = "jellyfin/jellyfin"
api          = { kind = "jellyfin", key_source = "generated" }
default_line = "12"

[[service.line]]
major    = 10
tag      = "10.11.11"
digest   = "sha256:…"
profile  = "profiles/jellyfin/10.toml"
standing = "supported"
via      = ["10.10.7"]

[[service.line]]
major    = 12
tag      = "12.1"
digest   = "sha256:…"
profile  = "profiles/jellyfin/12.toml"
standing = "supported"
via      = ["10.10.7"]
```

Each line carries its own digest and tag (`E1-R1`). `via` names the releases an
update must pass through, because upstream supports a migration only from them:
a 10.10.3 server reaches 10.11.11 or 12.1 through 10.10.7. A service declaring one
line has the shape every service has today.

### 1a. A line's pin follows its major's newest release, and a bump proves itself

A major carries no breaking change by definition, and the newest release of a major
is the one upstream still fixes. So each line's pin always moves to the newest
release of its major, and never across a major. Moving it is automatic:

1. **A scheduled workflow in `lemonfiber-media-stack`** reads the registry's tags
   for each line, keeps those whose version is in the line's major and is not a
   pre-release, and resolves the newest to the digest of its multi-architecture
   index. It is a workflow of the stack's own rather than a Dependabot update:
   Dependabot does not edit `stack.toml`, and it rebuilds its own branches, which
   would discard the re-recorded files.
2. **It re-records every recording of that line from the new digest**: it runs the
   image in CI, drives the same requests, and writes each recording with the new
   `recorded_from`. Each recording's `note` is carried over, and a changed answer
   reviews as a diff.
3. **It opens one pull request per line** moving `tag`, `digest`, the compose
   image and the recordings together.
4. **CI proves every claim and every operation** of that line against the new
   recordings (section 5). A green bump merges on its own.
5. **A bump that breaks a claim is refused and reported, never silently held
   back.** Its pull request stays open and red, naming the claim or operation it
   broke and showing the recording that broke it. Until it is resolved the line's
   standing is `held`, carrying the release it could not take, in the services
   envelope and the doctor. The fix is a profile change (data) or a new strategy
   (code, section 3) in the same pull request, and the bump then merges.

A pin moving changes what an update offers. It updates no operator's running
server: applying it is an E1 update the operator chooses.

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
is the server's own: it changed between 10.10 and 10.11, inside one major.

### 3. What "without code changes" covers, and what it cannot

**Covered, as data:**

- A new release within a major, which the bump in section 1a takes.
- A new major whose differences are paths, field names, where a value is read, or
  which *existing* strategy an operation uses.
- The version pattern, the default line, the `via` releases, and a line's
  standing, including its retirement.

**Not covered: a behaviour that differs in kind.** Where a new line removes the
thing an existing strategy relies on, no data can select a strategy that does not
exist. The measured cases:

- **12 refuses the legacy headers the core sends.** The modern header was
  accepted by all three releases measured, so it replaces the legacy one for every
  line. It is a one-time change and needs no variant.
- **12 stops reporting whether an account has a password.** D6's unclaimed
  state needs a second `claimed` strategy. The proposal, which is inferred and
  has not been proved against a recording yet, is `own-writes`. It is proved
  against the recordings of both lines before any core work relies on it. The
  core records when it made or reset an account, taking the time from Jellyfin's
  own activity entry for that write. A later `UserPasswordChanged` entry for that account is
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
- **It matches a line, at a release older than that line's pin.** This happens
  before an operator applies an update, in native mode, or with an image pulled
  by hand. The core uses the line's profile, reports the server as `older`, and
  says that the line's recordings were taken from a newer release. The doctor
  offers the update, naming any `via` release it passes through.
- **It matches a line other than the one pinned.** The core uses the running
  line's profile, and the doctor reports the difference.
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
five fields per service:

- `line`: the major that is running
- `running_version`, as read
- `tag` and `digest`, as pinned
- `running`: `at-pin`, `older`, `outside` (no line matches) or `unread`
- `line_standing`: `supported`, `leaving`, or `held` (the newest release of the
  major was refused, section 1a)

The companion reads these to show them. It does not derive behaviour from them. A
feature the running line cannot perform arrives as absent or `unconfigured` in
`/api/capabilities` (`ARCH-R78`), so no client carries a table of which line does
what.

### 7. The operator chooses a line, and moving is optional

- **Choosing a line.** A new installation takes `default_line`. An existing one
  stays on its line, and staying is never nagged about (`E1-R14`).
- **Moving to another line is an update across a major** (`E1-R10`):
  - It states that the move is irreversible (`E1-R3`).
  - It backs up first (`E1-R4`).
  - It passes through the target line's `via` releases where the running release
    predates them.
- **Updating within a line is an ordinary update, and may still migrate.**
  10.10.x to 10.11.11 is a move within major 10. It is also one-way: 10.11
  migrates the database, and a 10.10.5 or later server refuses to start on it
  afterwards. So the update says so and backs up first (`E1-R3`, `E1-R4`), and
  from 10.10.3 it passes through 10.10.7. That is a consequence for the operator,
  stated at the update, and not a reason for a line of its own.
- **Going back is restoring the backup taken before the move** (`E1-R8`,
  `E4-R5`), across a line or within one. Nothing is downgraded in place across a
  migration, because upstream refuses to start on a migrated database.

### 8. The window: two majors, each at its newest release

A service supports an explicit list of majors, never more than two at once: the
newest stable major upstream ships, and the major before it. That is N-1 by major.
For Jellyfin today the two lines are:

- **10, pinned at 10.11.11**, the newest 10.x release.
- **12, pinned at 12.1.**

A line is never split below a major. 10.10 and 10.11 are both major 10, so they
are one line, and its pin is the newest 10.x. What 10.11 changed inside that major,
the migration and the rating scale, is stated to the operator at the update
(section 7) and read from the server (section 2), not carried as a second line.

- **When a line leaves.** A line is marked `leaving` for at least one lemonfiber
  release before it is removed. The doctor and the services envelope say so.
- **Security.** Tracking the newest release of each major is also how a line
  takes upstream's fixes. A major upstream has stopped releasing keeps the
  advisories its last release carries, and a line on such a major states them.
  Major 10 is in that position: its last release is 10.11.11.

### 9. Bytes are open on every line, and the guard does not read the line

On all three releases measured, an anonymous `GET /Videos/{id}/stream?static=true` returns
the file, while the catalogue, the download route and the HLS playlist refuse. The
source matches:

- `VideosController` and `AudioController` carry no `[Authorize]` on these
  actions at any tag from `v10.10.3` to `v12.1`.
- No fallback policy is registered.
- Upstream issue #13984, *"Video streams unauthenticated"*, is open.

So the media server enforces discovery and not bytes. The playback grant proposed
in spec#537 rests on the Quick Connect row above, which holds on all three releases,
and on this: a member's session limits what the member can find, not what bytes
an item id fetches. `media.serve`'s `guarded`
probe asks for the catalogue, and it passes on every release even though bytes are
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
| **A line per upstream minor (10.10 and 10.11 apart)** | Splitting below a major multiplies recording sets for releases upstream has stopped fixing, and holds operators on superseded patches. A minor's migration is a consequence stated at the update, which E1 already requires. |
| **Hold a line's pin until someone moves it** | The pin falls behind upstream's fixes while nothing says so. Following the newest release automatically, with a refused bump reported as `held`, keeps the lag visible and short. |
| **Support every major upstream has shipped** | The recording matrix grows without bound, and majors upstream has stopped patching accumulate advisories nobody fixes. |
| **Follow upstream's newest line only** | It removes the option this decision exists to give. With one-way upgrades, the newest line without a supported predecessor is the flag day above. |

## Consequences

### Positive

- An operator can stay on 10 while 12 is proved, and move when they choose,
  with a backup and a stated way back.
- A new release within a major reaches the pin without anyone moving it, proved
  before it merges. A new major that only reshuffles known strategies is a data
  change reviewed as a diff.
- Every supported line is proved in CI against recordings from its own digest,
  and a line the core cannot serve is refused by name rather than half-served.
- Native mode gets a checked answer to *which version is this* rather than an
  assumption.

### Negative

- Two recording sets, re-recorded on every release of either major, and a
  workflow in the stack's repository that runs each image in CI to do it.
- Before 12 works at all, the core needs a one-time change: the modern
  `Authorization` header, and an `own-writes` strategy for claimed accounts, which
  has yet to be proved.
- The stack manifest gains `[[service.line]]` and `default_line`. Before the first
  release candidate this changes the schema in place (`ARCH-R43`), and afterwards
  it increments it.
- The pin has to move from 10.10.3 to 10.11.11 and gain digests on both lines
  before either line meets `E1-R1`. For an existing installation that update
  migrates the database, through 10.10.7.
- Major 10 has ended upstream, so its line carries whatever advisories 10.11.11
  carries. Keeping it keeps them, stated rather than hidden.
- A server on an older release of a line runs on recordings taken from a newer
  one, and is reported as `older` until it is updated.

### Neutral

- A service with one line behaves exactly as today.
- The rule that no code compares a version number applies to every service, and
  Jellyfin is only the first with two lines.

## Revisit if

- Upstream makes the byte endpoints require a token on a line in the window.
- Upstream breaks a claim within a major, so that following the newest release
  stops being safe to automate.
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
