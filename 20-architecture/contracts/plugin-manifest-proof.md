# Contract: `plugin.toml` — `[[proof]]`

**Status:** Accepted

Part of the [`plugin.toml` contract](plugin-manifest.md): the checks a plugin declares,
which must hold before lemonfiber installs it. The requirements this page describes are
listed with the rest of the contract's, under
[Requirements](plugin-manifest.md#requirements).

## `[[proof]]` — what must hold before it is installed

```toml
[[proof]]
id      = "plex.serves"
title   = "Plex answers on its declared health path"
request = { method = "GET", path = "/identity" }
expect  = { status = 200, json_has_keys = ["MediaContainer"] }
fixture = "fixtures/identity.json"
why     = "The path the health probe asks for is one this image serves."
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | Unique within the plugin. What a verdict is reported against. |
| `title` | string | ✔ | What it establishes, in one line |
| `request` | table | ✔ | `method` and `path`. The same shape a `health` probe takes. |
| `expect` | table | ✔ | What the answer must be. A status alone is not sufficient — see below. |
| `fixture` | string | | A recorded response to run against where no instance exists (`F10-R4`) |
| `service` | string | ✔ where the plugin declares more than one service | Which of this plugin's services is asked. Default: the only one. |
| `why` | string | ✔ | Why this is worth asserting. A proof nobody can justify is one nobody will maintain. |
| `expected` | array of tables | | Recordings this proof fails on, each with the constraint it fails and the reason — see [What an assertion is declared to fail on](#what-an-assertion-is-declared-to-fail-on) |

`F3-R1` names a plugin's proofs among what its manifest declares, `F3-R3` runs
them in the existing verification engine, and `[[proof]]` is where they are
declared — so `F3-R4`, *a plugin whose proofs do not pass is not installed*, has
something to evaluate.

**`expect` must constrain the body.** A status is a claim about the network
path, not about the service: Docker publishes a port by putting a proxy in front
of it, and that proxy accepts a connection before knowing whether anything
inside is listening. A manifest whose every proof asserts only a status MUST be
refused, naming the proofs, because it has declared nothing a replaced container
would fail (`ARCH-R105`). The core holds a `[[claim.probe]]` to its probe's body
constraints and holds a `[[proof]]` to nothing of the kind: a proof whose `expect`
is a status alone is installed and run as written. `0.18.0` locks `ARCH-R105`.

### What an expectation may say

One vocabulary, read in three places — a `[[proof]]`, a `[[claim.probe]]` and a
contributed check — because all three ask a service a question and judge the
answer, and three vocabularies for one job would be three things to keep in step.

| Key | Type | What it asserts |
|-----|------|-----------------|
| `status` | integer | The response status. Not sufficient alone, except for a refusal — see above. |
| `json` | table | Places the body must carry, each with the exact value it must hold. A value is a boolean, a whole number or a string; nothing nested, because a shape deeper than that is asking about a document rather than about a claim — and where the thing worth asserting is deeper *in* the answer, the key reaches it rather than the value growing to match. |
| `json_has_keys` | array | Places the body must carry, whatever they hold |
| `json_types` | table | Places the body must carry, each with the kind of value it must be: `bool`, `int`, `str`, `list` or `dict` |
| `json_at_least` | table | Places the body must carry, each with a number it must not be below. *At least one series*, rather than *a catalogue exists*. |
| `json_array_min` | integer | The body read as a JSON **array**, with at least this many entries. A catalogue is very often a list rather than an object, and none of the key-wise constraints can say anything about one. |
| `json_is_absent` | boolean | **The body did not parse as JSON at all.** How a proof says *this answered with an application shell, not an object* — which is what a client-routed service answers for every path it does not implement, and the reason a status proves nothing against one. |
| `content_type` | string | A substring of the content type the answer was served as |
| `body_starts_with` | string | What the body must begin with, where it is not JSON |

The set is closed. A key outside it is refused by name rather than ignored, for
`ARCH-R91`'s reason pointed at an expectation: an assertion nothing evaluates is
a proof that silently checks less than it says, which is worse than one that
fails.

`json_is_absent` is the one worth reading twice, because its name invites the
other reading — *these keys are absent* — and the two are not close. It says
nothing about keys. It says the answer was not JSON.

#### Where an expectation looks

The four key-wise constraints above take a **place** rather than a name. The
other five are about the answer as a whole and take none.

A key that does not begin with `/` is the name of a top-level member, which is
what every key written before this generation is and is why none of them changed
meaning. A key that does begin with `/` is a
[JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901), with one extension this
contract defines.

| Key | Reaches |
|-----|---------|
| `content` | the top-level member `content` |
| `/MediaContainer/machineIdentifier` | `machineIdentifier` inside `MediaContainer` |
| `/MediaContainer/Setting/[id=PublishServerOnPlexOnlineKey]/value` | the entry of the `Setting` list whose `id` holds that word, then its `value` |
| `/MediaContainer/Directory/[type=movie]/Location/[path=~1data~1media~1movies]/path` | the film library's location under the stack's data root |
| `/a~1b` | the top-level member literally called `a/b` (RFC 6901's escapes: `~1` is `/`, `~0` is `~`) |

**Standard, and ours.** Everything but the third row is RFC 6901 unchanged. The
third is the extension, and it is one step and one comparison: a reference token
written `[field=value]` means *the entry of this list whose `field` holds
`value`*, exactly one entry must, and there are no operators, no wildcards, no
nesting and no indices.

An index would be the trap the selector exists to avoid. Plex answers a hundred
and fifty-one settings at `/:/prefs` and the order of them is not a promise
anybody made, so *the ninety-first* is the wrong answer one release later, in a
way that keeps passing.

**A selector's value is escaped like any other reference token**, which the fourth
row is there to show and which the common case needs: a filesystem path is full
of slashes, and a slash in a token is written `~1`. Unescaped,
`[path=/data/media/movies]` is four steps rather than one, and is refused by
name rather than resolved somewhere nobody meant.

Its cost is stated rather than hidden. `[` and `]` belong to the selector, so a
reference token carrying either is refused rather than read as a member name — a
member actually called `[a=b]` is unreachable through a pointer. That is the
price of the extension; it also closes the mistake anybody would actually make,
which is writing `…/Setting[id=X]/value` and being told nothing while it looks
for a member with brackets in its name.

**Why a name was not enough.** A flat name says everything there is to say about
a flat answer, and the two plugins published before this one both have flat
answers. A service that nests its payload — Plex puts every response one level
down under `MediaContainer` — could only be asserted about at the envelope, so
`json_has_keys = ["MediaContainer"]` was the strongest claim available and it
says that the service replied. A probe that passes by observing that something
replied is worse than one that fails, because a port proxy replies.

A key naming no place is **refused when the manifest is read**, naming the key
and what is wrong with it. It is not evaluated as a missing member: an assertion
nothing can evaluate is one that silently checks less than it says, which is
`ARCH-R91` pointed at an expectation.

`[[recipe.step]].capture.from` reads an answer with these same keys, so one
dialect says where a value is, whether a proof is asserting about it or a recipe
is taking it.

Three verdicts, never two (`F3-R5`, `F4-R7`): passed, failed, and could not be
run. The third is reported as unproven and is never counted as the first.
Against a recording a proof or a check declares it fails on, a fourth is
reported in place of the second: failing as declared.

### What an assertion is declared to fail on

A `[[proof]]` and a `doctor.check` row may carry `expected`: the recordings it
fails on, which of its constraints fails there, and why. It is for an assertion
whose passing state nobody can record, such as a check that a server has an
owner where claiming one needs an account the plugin's CI does not hold
(`F10-R12`).

```toml
[[contribution]]
at        = "doctor.check"
id        = "plex:claimed"
request   = { method = "GET", path = "/identity", accept = "application/json" }
expect    = { status = 200, json = { "/MediaContainer/claimed" = true } }
fixture   = "fixtures/identity-anonymous.json"
expected  = [
    { fixture = "fixtures/identity-anonymous.json", verdict = "fails", constraint = "json", place = "/MediaContainer/claimed", reason = "Recorded from a server nobody has claimed; claiming one needs a plex.tv account." },
]
# … title, category, timeout_s and why as for any check
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `fixture` | string | ✔ | The recording the assertion fails on. It may be the assertion's own `fixture`. |
| `verdict` | string | ✔ | `fails`, and nothing else. Passing is what `expect` already declares, and unproven is never excused. |
| `constraint` | string | ✔ | The key of this assertion's `expect` that fails on the recording: one of the [vocabulary's](#what-an-expectation-may-say) keys, and one `expect` carries. |
| `place` | string | ✔ where `constraint` is key-wise | The place within that constraint that fails, written exactly as `expect` writes it. Absent for a constraint about the answer as a whole. |
| `reason` | string | ✔ | Why this recording is one the assertion fails on. Reported with the verdict every time. |

An entry names one constraint, and it has to be one the assertion makes. An
entry naming a key `expect` does not carry, or a place that key does not
constrain, is refused by name, with the constraints the assertion does make
(`ARCH-R130`).

What each entry changes is the report about **that recording** and nothing else.
Every constraint of `expect` is judged, so the report can say which failed:

| The assertion, against the recording an entry names | Reported as |
|-----|-----|
| Ran; the named constraint was judged false and every other constraint held | Failing as declared, naming the declared constraint, what the answer held there, and the reason (`F10-R13`) |
| Ran; the named constraint held | Failed: the declaration is stale, naming it (`F10-R14`) |
| Ran; a constraint the entry does not name was judged false | Failed, naming the declared constraint and every constraint that failed, whether or not the declared one did (`F10-R14`) |
| Could not be run | Unproven, naming the recording (`ARCH-R122`, `F10-R16`) |

Against any other recording, and against the live service, the assertion is held
to `expect` exactly as if `expected` were absent (`F10-R15`). A `[[claim.probe]]`
has no `expected`: a claim is what other services are wired on, and one whose
probe fails is not wired to (`F4-R6`).

### What a recording is

A `fixture` names a file beside the manifest holding **one response somebody
recorded from the image this manifest pins**. It is what lets a claim be shown
where no instance exists — an author's laptop, the catalogue's CI, a reviewer's
checkout — and it is ordinary reviewable data rather than a cassette a tool
wrote and only that tool reads (`F10-R4`, `F10-R5`).

```json
{
  "recorded_from": "ghcr.io/example/thing@sha256:6c2a967…",
  "note": "An unauthenticated read of the catalogue. A refusal is the pass: a library server on the household network that answered this would be publishing somebody's collection to every device on it.",
  "request":  { "method": "GET", "path": "/api/v1/series" },
  "response": {
    "status": 401,
    "headers": { "content-type": "application/json" },
    "json": { "status": 401, "error": "Unauthorized" }
  }
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `recorded_from` | string | ✔ | The image this answer came out of, as `image@sha256:…` |
| `note` | string | ✔ | Why this is the answer worth recording — the half a diff cannot show |
| `request.method` | string | ✔ | What was asked |
| `request.path` | string | ✔ | Where it was asked |
| `request.accept` | string | | What representation it asked for, where it asked for one |
| `response.status` | integer | ✔ | |
| `response.headers` | table | | The headers an expectation may constrain; `content-type` is the one in use |
| `response.json` | any | | The body as it parsed, or `null` where it did not parse as JSON |
| `response.body_starts_with` | string | | The beginning of a body that is not JSON |

**It names the image by digest, and that digest is the manifest's own pin.** A
recording taken from some other build is a claim about software nobody is
installing, and the drift is silent: it passes, and the service it describes is
not the service that will run. Moving the pin means re-recording in the same
change, and a recording naming a different image is refused rather than trusted.

**What was asked for is part of which call a recording is of.** A service that
negotiates answers two different things at one path, so a recording that did not
say which it asked for would be evidence for whichever question somebody later
pointed at it. A recording taken plainly is not evidence for a request that
names an `accept`, and one that named an `accept` is not evidence for a request
that does not.

**A recording that is absent, unreadable, or records a request the assertion
does not ask is unproven** — never a pass and never a failure. Nothing about the
service has been established either way, and reporting it as a failure would say
the service is broken when the recording is. It is the third verdict's plainest
case, and the one an author meets most often.

## Related

- [plugin-manifest](plugin-manifest.md) — the rest of the contract, its validation and its requirements
- [plugin-manifest-recipe](plugin-manifest-recipe.md) — the ordered calls a plugin may declare
