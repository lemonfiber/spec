# What the wire carries that the companion does not read

**Status:** Register · **Measured 25 September 2026**, against the companion at `73bbe5a` and the core at `5e151aa`

The stack **publishes** sixty-two envelopes and **serves** fifty-nine. The
companion app follows twenty-five of them. This is the other thirty-seven, written
down so that what fills them is a decision somebody made rather than whatever the
next person happened to notice.

Three of the sixty-two are published and not served. They are not envelopes
the app has not got to; they are envelopes it cannot reach, and they have a
heading of their own below.

It is a register of **facts**, not of requirements. No row here proposes a
screen. `N1-R17` is the rule that matters: a field wants a requirement before it
wants a surface, and a surface built because the wire happens to carry a field is
a surface nobody asked for. Every row is an invitation to decide, and *no
requirement asks for this* remains a complete answer.

## How it was measured

Reproducible, from the companion's checkout:

```
ls vendor/lemonfiber/sdk-php/src/Generated/*Envelope.php | wc -l   # 62
Tests\Support\WhatTheReadersRead::envelopes()                      # 25
git grep -l '<Name>Envelope' -- app-modules bridge                 # 28 of the 62 names
```

| | |
|---|---|
| Envelopes the SDK ships | **62** |
| Followed by a reader | **25** |
| Not followed | **37** |
| — never referenced anywhere in the app | **34** |
| — referenced but not followed | **3** |

*Referenced* means named under `app-modules` or `bridge`. Four of the
thirty-four, `Credentials`, `Lifecycle`, `Start` and `Wiring`, are named by the
app's root test suite and by nothing it ships.

`Admission`, `Pull` and `Word` are the three referenced without being followed.
The app reads admission through `Admitted` rather than through the envelope, and
names `AdmissionEnvelope` only in the development stand-in that answers for a
stack. `Pull` carries a bare string, and is named in that stand-in's comments.
`Word` is what `/api/explain` answers with when one word is asked for, and is
named only in a test of that stand-in: the app asks for the whole glossary, which
answers with `Glossary`. `Word` has a row below; `Admission` and `Pull` have
none, and these sentences are their entry.

## What the twenty-five answer

Each is followed by a reader in `app-modules/sdk`. The requirements are the
rows in the companion's `.docs/requirements/` that name the envelope, its
reader, or what that reader builds. The last column counts the envelope's rows in
`WhatTheContractCarriesThatNothingReadsTest`: each is a path the app has decided
not to read, with the reason.

| Envelope | Requirements it answers | Where the companion records them | Unread rows |
|---|---|---|---|
| `Alerts` | `N10-R8`, `N10-R11` | `what-leaves-a-machine.md` | 2 |
| `Archives` | `N6-R9`, `N6-R11` | `what-a-machine-keeps.md` | 0 |
| `Bandwidth` | `N10-R4`, `N10-R5`, `N10-R6`, `N10-R7` | `what-leaves-a-machine.md` | 11 |
| `Config` | `F7-R3`, `F7-R4`, `F7-R10`, `F7-R11`, `F7-R12`; `N1-R5` | `what-a-machine-says.md`; `what-the-rules-keep.md` | 5 |
| `Doctor` | `N2-R3`, `G4-R4`, `C1-R15`, `F7-R3` | `what-a-machine-says.md`, `reaching-a-stack.md` | 6 |
| `Error` | `G4-R2` | `what-the-rules-keep.md` | 3 |
| `Forms` | `N2-R7`; `N18-R9` | `the-screens-themselves.md`; `running-part-of-it.md` | 3 |
| `Glossary` | `N15-R3`, `N15-R4`, `N15-R9`, `N15-R10` | `what-the-words-mean.md` | 0 |
| `Held` | none outright; see below | `what-the-rules-keep.md` | 2 |
| `History` | `N11-R1`, `N11-R2`, `N11-R3`, `N11-R5`, `N11-R9`, `N11-R10` | `what-was-done-here.md` | 0 |
| `Hosting` | `N16-R5`, `N16-R6`, `N16-R13`, `N16-R14` | `what-a-machine-says.md` | 5 |
| `Household` | `N2-R11`, `N2-R14`, `D7-R3`, `D7-R4`, `D7-R7`, `N3-R4`, `N3-R5`, `N3-R6`, `N3-R7` | `reaching-a-stack.md`, `what-a-machine-says.md`, `what-the-rules-keep.md` | 12 |
| `Job` | `N1-R41` | `reaching-a-stack.md` | 1 |
| `Log` | `N2-R10`; `G3-R10` | `reaching-a-stack.md`; `what-the-rules-keep.md` | 0 |
| `Outbound` | `N10-R1`, `N10-R2`, `N10-R3`, `N10-R12`, `F7-R9` | `what-leaves-a-machine.md` | 0 |
| `Preview` | `N18-R4`, `N18-R5` | `running-part-of-it.md` | 4 |
| `Provenance` | `N11-R7`, `N11-R8`; `N11-R6` in part | `what-was-done-here.md` | 0 |
| `Repair` | `N2-R4`, `N2-R6` | `reaching-a-stack.md` | 2 |
| `SelfUpdate` | `N14-R1`, `N14-R2`, `N14-R5`, `N14-R6`, `N14-R7`, `N14-R8` | `what-is-running-here.md` | 4 |
| `Space` | `N12-R1`, `N12-R2`, `N12-R3`, `N12-R4`, `N12-R6`, `N12-R9`, `N12-R10` | `how-full-a-machine-is.md` | 8 |
| `Status` | `N2-R7`, `N2-R21`, `B2-R15`; `N18-R1`, `N18-R3`, `N18-R6` | `reaching-a-stack.md`, `what-a-machine-says.md`; `running-part-of-it.md` | 7 |
| `Stored` | `N6-R7`, `N6-R11` | `what-a-machine-keeps.md` | 1 |
| `Stuck` | `N2-R9`, `N16-R10`, `N16-R12` | `reaching-a-stack.md`, `what-a-machine-says.md` | 0 |
| `Trace` | `N8-R4`, `N8-R5`, `N8-R6`, `N8-R8`, `N8-R9` | `where-an-item-got-to.md` | 0 |
| `Update` | `N2-R15`, `N2-R16`, `N2-R19`, `N2-R20`, `N2-R22`, `E5-R6`, `E5-R10`; `N14-R3`, `N14-R4` | `reaching-a-stack.md`, `what-a-machine-says.md`; `what-is-running-here.md` | 21 |

`Held` is the shelf a member sees, drawn by the household module's
`WhatYouCanWatch`. The one row that names it is `N3-R14`, which it does not
answer: that requirement is about a player, and the companion records the player
as not built.

`Error` is read as the kernel's `Problem` — code, severity, state, meaning and
remedies — and a severity outside the four `G4-R2` defines is refused rather
than read. Its `detail`, `cause` and each remedy's `detail` are the three unread
rows.

`Bandwidth`'s eleven are `applied`, which a reading that never writes always
answers the same way; `clients`, a surface of its own; `metered`, which belongs
beside the cap with its exclusions said; `respite` and `respite_says`, the
override's countdown; `rhythm` and `zone`, the household's hours, which are a
setting; and per direction `limit` and `resolved`, which the `says` sentence
already carries.

`Alerts`' two are `changed` and `rehearsed`. Only a call that changes the
setting answers them otherwise, and this app makes none, which is also why
`N10-R9`, a rehearsed alert, is not drawn.

`Hosting`'s five are `caveat`, `changed`, and per command `definition`,
`output` and `runs`.

`History` does not answer `N11-R4`, the reason a change was made: the envelope
carries no such field, because the stack's journal records none, and `because`
is why putting a change back stops short rather than why it was made.

`Provenance` answers `N11-R6` in part. Image, upstream and licence are drawn,
and the version the service is `pinned` at stands where the digest belongs:
the envelope carries no digest, because the stack pins by tag, and `E1-R1`
requires a digest with the tag beside it.

`Config`, `Doctor` and `Outbound` carry the same `origin` on each setting, each
finding and each service: bundled, operator, a named plugin, a named plugin's
override with the value it replaced, a value a removed plugin left, or unknown
with the stack's reason. Its eight paths on each of the three are read, into one
type, and shown. A setting says its origin on every row. A check or a service
says it only where it is not the stack's own, with one line under the list saying
what an unmarked row is, which is how the stack's own terminal draws them. An
origin that cannot be read refuses the reading rather than defaulting to bundled
(`F7-R11`).

## Why nothing caught this

The companion has a machine-checked register for unread fields,
`WhatTheContractCarriesThatNothingReadsTest`, and its rule is that every path
on an envelope the app reads is either followed to a reader or listed with a
reason. Ninety-seven rows, over five hundred and sixty-five paths.

**It cannot see any of the thirty-seven**, and the reason is one line of its own
scaffolding:

```php
foreach (WhatTheReadersRead::envelopes() as $envelope) {
```

It walks the envelopes a reader already reads. An envelope nothing touches
contributes no paths, so it can never be flagged — the blind spot is exactly the
shape of the gap. The rule watches fields arriving on envelopes the app already
knows about; nothing watches whole envelopes the app has never opened.

That is a gap in its own right, and it is not what this register is for.

---

## Connecting it together

The surface that lets an operator wire the stack up. The app draws none of it.
Its kernel holds the types a wiring would be read into, recorded in the
companion's `connecting-the-stack.md`.

| Envelope | What it carries |
|---|---|
| `plugins` **(not served)** | Which plugins are installed, and one being installed now — `install` and `installed`. The whole of what an operator opens a plugin screen to see. |
| `wiring` **(not served)** | Which service asks for which capability, and how each is settled: `outright`, `each`, **`contested`** with its claimants, or **`chosen`** with what it was chosen over, `whose` choice it was — `stack` or **`operator`** — and why. Plus `unfilled`: services asking for something nothing answers. |
| `substitution` **(not served)** | Applying one service in place of another for a capability: who asked for it, what it was `was` and is `now`, the setting that carries it, and `leaves_unfilled` — what the swap breaks. |
| `catalogue` | What the stack could run and does not: each service's `criticality`, what it `describes`, and `without_it` — what the household loses by not having it. Plus `removed`, with the reason and what replaced it. |
| `bundle` | A support export: its `pieces`, what is `missing`, when it was `taken` and against which versions, and `terms` — whether filenames are revealed, what else is, and over what `window`. |
| `beside` | Ports a service asks to be reachable on beside the front door, with a `stance` of unchanged, pending, blocked or applied. |

**Three of these are not served at all.** `wiring`, `substitution` and
`plugins` are published in the contract and generated into the SDK, and no HTTP
route or action produces any of them. Nothing under `lemonfiber-api`'s `src`
names any of them. Its read table, `read/table.rs`, declares every read it
serves, with `catalogue`, `forms` and `alerts` among them and none of these
three. The single action route accepts only the names in `actions/named.rs`'s
`OFFERED` — forty of them, and not one is a plugin, wiring or substitute verb —
so an action outside that list is refused before a command is built. Recorded in
[lemonfiber#731](https://github.com/lemonfiber/lemonfiber/issues/731), which is
open.

**The kind exists because the command line produces it, which is why the
generated surface lists it.** `contract/web-api.surface.json` maps every kind to
its type, including these three, and that file is not evidence of a route.
`Outcome::Plugins` is produced by `Command::Plugins`, which the core and the
command line run; nothing on the HTTP surface asks for it. A register that read
the surface map would call this served, and be wrong.

The plugin lifecycle `plugins` reports on is built at the command line: installing,
rehearsing, updating and removing are plain subcommands (`F6-R13`), and an unmet
capability is refused by name (`F6-R10`). `wiring` and `substitution` each have
a settled report in the core, and `Command::Wiring` produces `Outcome::Wiring`
from the command line. What all three lack is a route.

So they are a different kind of row from everything else here. Every other
envelope in this register is a decision waiting to be made; these three have no
decision about the companion that can reach them while no route serves them.
The companion records the same for `N5`: `N5-R2`, `N5-R4`, `N5-R7`, `N5-R10`,
`N5-R11` and `N5-R13` cannot be answered there until a read exists.

**The `wiring` row names a choice nothing can make.** The core will not resolve
a contested capability — the command line says *nothing wires to it until the
operator chooses, and lemonfiber does not choose by install order*. The contract
models that choice, down to `whose: 'operator'`.

There is nowhere in the companion to make that choice, and nowhere on the wire
to read that it is waiting.

## Guided setup

| Envelope | What it carries |
|---|---|
| `wizard` | Where first run has got to: `at` one of fourteen named stages from `welcome` through `vpn`, `credentials`, `library`, `household` to `review`; whether it `asks`, whether it was `offered`, and the `phase`. |
| `setup` | What setup settled: the `data_root`, which `protocols` are on, the `service_user`, and whether it was `applied`, `abandoned` or was `already-set-up`. |
| `step` | One step of a running job, as a stage — `choosing`, `searching`, `grabbing`, `downloading`, `importing`, `scanning`, `available` — with what was `said` and the detail under it. |
| `walkthrough` | A first acquisition narrated end to end: the `lines` it produced, whether it ran `in_background`, whether the thing was `already_here`, and a `handover` naming what to do next. |
| `word` | One entry of the glossary, alone. |

## Backups and recovery

The companion's `app-modules/backups` holds no code, and its README names `N6`
as the requirement for taking a copy and putting it back. The listing half of
`N6` is read: `archives` and `stored`, above, drawn by
`WhatThisMachineKeepsHere`. These four rows are the acts, and the companion
records `N6-R1` to `N6-R6`, `N6-R8` and `N6-R10` as asked for and not drawn,
because it offers none of them.

| Envelope | What it carries |
|---|---|
| `backup` | A snapshot being taken: its `scope` — whole stack, one service, or an existing project with its trees — the `path`, what was `pruned`, whether it was `rehearsed`, and the `pace` it moved at against a budget. |
| `restore` | A snapshot being put back: what it was restored `from_version`, the `scope`, and whether anything was `relocated` from where it used to live. |
| `undo` | Reversing what was done: what was `reversed` — a removal, a restore, a write — what was `left` and why, and whether it was `rehearsed`. |
| `reset` | Putting configuration back: what was `reverted`, with a diff per path, and which connections went with it. |

## Getting content in

| Envelope | What it carries |
|---|---|
| `adoption` | Taking over an existing setup: what would be `upgrade`d, service by service, with the verdict, the reason, whether it was `refused` and whether it wants a backup first. Plus a `stance` and what to `back_up`. |
| `import` | What an existing setup brings across: what is `carried`, what is `not_carried` and because of what, and what `would_carry`. |
| `migration` | Moving in alongside something already running: what is `carrying` over, the port `beside` moves, and `conflicts` with what holds them. |
| `seed` | What the stack wires up on the operator's behalf, each wiring with a severity that names the breakage and its remediation, and what is `unsupported` and why. |
| `quality` | The quality presets: each with its resolution, what it `means`, size per hour, whether it `needs_transcoding_here`, and whether the operator has `customised` it. |
| `music` | The same for audio: format, scope, size per hour, and what the choice `means`. |
| `watch` | Watching a folder for new material: the `forms` it covers, whether it is `stopped` and the reason, and what it `would` run. |

## A service's life

| Envelope | What it carries |
|---|---|
| `lifecycle` | Starting, stopping and restarting: the `action`, the `command`, the `condition` — inactive, degraded, partial, active — what is `held`, and the `plan` with what it dropped. |
| `start` | A bare string. |
| `removal` | Removing a person's access: what was `revoked` and how widely, how many `requests` they had, and the `findings`. |
| `replacement` | Swapping a service out: what was `stopped`, what `would_stop`, what is `still_running`, and a `stance`. |
| `uninstall` | Taking the stack off: an agreement, the bytes, what is `foreign` and left behind, and a `confidence` naming what could not be read. |
| `upgrade` | Moving media to a new preset: per media type, the preset, size per hour and the outcome. |
| `version` | What is running and what has shipped: the binary, and a `changelog` of releases with what each `delivers`, what it `patches`, whether it is `user_facing` and whether it was `withdrawn`. |
| `stop-seeding` | Stopping a torrent: the download, its `standing` — never imported, seeding at a ratio, or left alone — and what stopping it costs. |

## Household and access

| Envelope | What it carries |
|---|---|
| `invitation` | Inviting somebody in: the address, how many `hours` it stands for, whether it was `linked`, and what was `applied` — which libraries, what filtering, whether unrated material is held back, and whether they may make requests. |
| `credentials` | Every secret the stack holds: its `origin` — operator, service or lemonfiber — its `state` from absent through active, stale, invalid, rotating to superseded, which services `consume` it, its `location` and `fingerprint`. |
| `clients` | Which apps work on which devices: `support` rated good, workable, poor or fallback, with a `caution` and an `instead`, plus what to say when nothing is installed and when it only works at home. |
| `front-door` | How the household reaches the stack: the address, what is `beside` it and what each is `facing`, and whether the address was `derived` or chosen. |
| `dashboard` | The whole front page in one envelope: alerts with severity, meaning, what they affect and their remedies, alongside the door. |
