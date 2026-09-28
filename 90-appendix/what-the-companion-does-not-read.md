# What the wire carries that the companion does not read

**Status:** Register · **Measured 28 September 2026**, against the companion at `dab906bd` and the core at `950df25b`

The stack **publishes** sixty-two envelopes and **serves** fifty-seven. The
companion app follows thirty-nine of them. This is the other twenty-three,
written down so that what fills them is a decision somebody made rather than
whatever the next person happened to notice.

Five of the sixty-two are published and not served. They are not envelopes the
app has not got to; they are envelopes it cannot reach. Three have a heading of
their own below, `setup` is marked so under *Guided setup*, and the fifth,
`pull`, is a line of the command line's own, said in the next section.

It is a register of **facts**, not of requirements. No row here proposes a
screen. `N1-R17` is the rule that matters: a field wants a requirement before it
wants a surface, and a surface built because the wire happens to carry a field is
a surface nobody asked for. Every row is an invitation to decide, and *no
requirement asks for this* remains a complete answer.

## How it was measured

Reproducible, from the companion's checkout:

```
ls vendor/lemonfiber/sdk-php/src/Generated/*Envelope.php | wc -l                 # 62
Tests\Support\WhatTheReadersRead::envelopes()                                    # 39
git grep -lw '<Name>Envelope' -- app-modules bridge/src ':!*/tests/*'            # 40 of the 62 names
```

| | |
|---|---|
| Envelopes the SDK ships | **62** |
| Followed by a reader | **39** |
| Not followed | **23** |
| — never named by the app's code, tests aside | **21** |
| — named but not followed | **2** |

The companion measures the same thing and states it. Its
`tests/Feature/EveryActionTheStackOffersTest.php` puts every kind the SDK ships
in one of three lists: `OFFERED`, held to exactly the envelopes
`WhatTheReadersRead::envelopes()` answers with, which is thirty-nine;
`ELSEWHERE`, `Setup` and `Wizard`, each excused by `N1-R4`; and `NOT_YET`, the
other twenty-one. Its `.docs/requirements/what-a-screen-owes.md` says 62, 39, 21
and 2, and that test holds the page to what the lists come to. This register
counts the same way and agrees with it: *named* means named in a file under
`app-modules` or `bridge/src` outside a `tests` directory.

The grep answers forty names rather than forty-one, because `Log` is followed
without being named: a log window arrives through the SDK's `LogWindow`, held in
its envelopes, and `WhatTheReadersRead` seats the reads on it all the same.
Three of the twenty-one are named by tests and by nothing the app ships: `Start`
and `Wiring` by the app's root test suite, and `Word` by a test of the
development stand-in, under `app-modules/dx/tests`.

`Admission` and `Pull` are the two named without being followed. The app reads
admission through `Admitted` rather than through the envelope, and its code
names `AdmissionEnvelope` only in the development stand-in that answers for a
stack. `Pull` carries a bare string, and is named in that stand-in's comments.
`Word` is what `/api/explain` answers with when one word is asked for: the app
asks for the whole glossary, which answers with `Glossary`. `Word` has a row
below; `Admission` and `Pull` have none, and these sentences are their entry.

From the core's checkout, `contract/web-api.contract.json` publishes sixty-two
kinds. Fifty-three are the variants of `Outcome`, in
`crates/lemonfiber-core/src/app/outcome.rs`, each written by the command that
produces it; the other nine are written with `Envelope::new` where they arise. A
kind is served when `crates/lemonfiber-api` answers with it: through a command
its reads (`read/table.rs`), its actions (`actions/named.rs`) or setup's
endpoints (`setup.rs`) build, or an envelope it writes itself — `admission`,
`error`, `job` and `log`, and on the event stream `dashboard`, `start` and
`step`.

| | |
|---|---|
| Kinds the contract publishes | **62** |
| Served over HTTP | **57** |
| Published and not served | **5** |

`plugins`, `wiring` and `substitution` are not served because no read, action or
endpoint builds `Command::Plugins` or `Command::Wiring`. `pull` and `setup` are
written only by the command line, in `crates/lemonfiber/src/engine.rs` and
`crates/lemonfiber/src/setup.rs`; the HTTP crate names both only to describe them
in the contract, and setup's endpoints answer with `wizard`.

**`pull` is the command line's alone.** Its bare strings are the lines
`docker compose pull` prints, which the command line writes under that kind as
they arrive. No read, action or event produces it over HTTP: the `pull` action
answers with a job whose outcome is `lifecycle`, and nothing is said on the event
stream while it runs. `N2-R24` asks the app to offer the fetch, and `N2` records
the progress that does not reach it.

## What the thirty-nine answer

Each is followed by a reader in `app-modules/sdk`. The requirements are the
rows in the companion's `.docs/requirements/` that name the envelope, its
reader, or what that reader builds. The last column counts the envelope's rows in
`WhatTheContractCarriesThatNothingReadsTest`: each is a path the app has decided
not to read, with the reason.

| Envelope | Requirements it answers | Where the companion records them | Unread rows |
|---|---|---|---|
| `Alerts` | `N10-R8`, `N10-R11` | `what-leaves-a-machine.md` | 2 |
| `Archives` | `N6-R9`, `N6-R11` | `what-a-machine-keeps.md` | 0 |
| `Backup` | `N6-R1`, `N6-R2`, `N6-R3`, `N6-R4` | `what-a-machine-keeps.md` | 2 |
| `Bandwidth` | `N10-R4`, `N10-R5`, `N10-R6`, `N10-R7` | `what-leaves-a-machine.md` | 11 |
| `Bundle` | `N22-R3`, `N22-R4`, `N22-R5`, `N22-R6`, `N22-R7`, `N22-R9` | `asking-for-help.md` | 0 |
| `Clients` | `N9-R8`, `N9-R9`, `N9-R11` | `who-gets-in.md` | 0 |
| `Config` | `F7-R3`, `F7-R4`, `F7-R10`, `F7-R11`, `F7-R12`; `N1-R5` | `what-a-machine-says.md`; `what-the-rules-keep.md` | 5 |
| `Credentials` | `N9-R1`, `N9-R2`, `N9-R3`, `N9-R4`, `N9-R11` | `who-gets-in.md` | 6 |
| `Dashboard` | `G7-R5`, `G7-R8`, `G7-R9`, `G7-R10`, `N1-R67`, `N1-R69`, `N2-R1`; `N23-R6`, `N23-R7`, `N23-R8` | `the-one-line.md`; `what-a-machine-says.md` | 9 |
| `Doctor` | `N2-R3`, `G4-R4`, `C1-R15`, `F7-R3` | `what-a-machine-says.md`, `reaching-a-stack.md` | 6 |
| `Error` | `G4-R2` | `what-the-rules-keep.md` | 3 |
| `Forms` | `N2-R7`; `N18-R9` | `the-screens-themselves.md`; `running-part-of-it.md` | 3 |
| `FrontDoor` | `N9-R9`, `N9-R10`, `N9-R11` | `who-gets-in.md` | 0 |
| `Glossary` | `N15-R3`, `N15-R4`, `N15-R9`, `N15-R10` | `what-the-words-mean.md` | 0 |
| `Held` | none outright; see below | `what-the-rules-keep.md` | 2 |
| `History` | `N11-R1`, `N11-R2`, `N11-R3`, `N11-R5`, `N11-R9`, `N11-R10` | `what-was-done-here.md` | 0 |
| `Hosting` | `N10-R10`, `N23-R1`, `N23-R2`, `N23-R3`, `N23-R4`, `N23-R5` | `what-a-machine-says.md` | 3 |
| `Household` | `N2-R11`, `N2-R14`, `D7-R3`, `D7-R4`, `D7-R7`, `N3-R4`, `N3-R5`, `N3-R6`, `N3-R7` | `reaching-a-stack.md`, `what-a-machine-says.md`, `what-the-rules-keep.md` | 12 |
| `Invitation` | `N9-R5`, `N9-R6`; `N21-R2`, `N21-R5`, `N21-R6`, `N21-R9`, `N21-R10` | `who-gets-in.md`; `asking-somebody-in.md` | 0 |
| `Job` | `N1-R41` | `reaching-a-stack.md` | 1 |
| `Lifecycle` | `N2-R7`, `N16-R6`, `N6-R1`, `N18-R3`, `N7-R5` | `what-a-machine-says.md`, `the-screens-themselves.md` | 19 |
| `Log` | `N2-R10`; `G3-R10` | `reaching-a-stack.md`; `what-the-rules-keep.md` | 0 |
| `Migration` | `N7-R5`, `N7-R6`, `N7-R11`, `N7-R12`, `N7-R13`, `N7-R14` | `moving-in.md` | 5 |
| `Music` | `N8-R3`, `N24-R2`, `N24-R10` | `choosing-how-good.md` | 0 |
| `Outbound` | `N10-R1`, `N10-R2`, `N10-R3`, `N10-R12`, `F7-R9` | `what-leaves-a-machine.md` | 0 |
| `Preview` | `N18-R4`, `N18-R5` | `running-part-of-it.md` | 4 |
| `Provenance` | `N11-R6`, `N11-R7`, `N11-R8` | `what-was-done-here.md` | 0 |
| `Quality` | `N8-R2`, `N8-R3`, `N24-R2`, `N24-R3`, `N24-R5`, `N24-R10` | `choosing-how-good.md` | 1 |
| `Repair` | `N2-R4`, `N2-R6` | `reaching-a-stack.md` | 2 |
| `Restore` | `N6-R1`, `N6-R2`, `N6-R5`, `N6-R10` | `what-a-machine-keeps.md` | 6 |
| `SelfUpdate` | `N14-R1`, `N14-R2`, `N14-R5`, `N14-R6`, `N14-R7`, `N14-R8` | `what-is-running-here.md` | 4 |
| `Space` | `N12-R1`, `N12-R2`, `N12-R3`, `N12-R4`, `N12-R6`, `N12-R9`, `N12-R10` | `how-full-a-machine-is.md` | 8 |
| `Status` | `N2-R7`, `N2-R21`, `B2-R15`; `N18-R1`, `N18-R3`, `N18-R6` | `reaching-a-stack.md`, `what-a-machine-says.md`; `running-part-of-it.md` | 7 |
| `Stored` | `N6-R7`, `N6-R11` | `what-a-machine-keeps.md` | 1 |
| `Stuck` | `N2-R9`, `N16-R10`, `N16-R12`, `N16-R13`, `N23-R9` | `reaching-a-stack.md`, `what-a-machine-says.md` | 0 |
| `Trace` | `N8-R4`, `N8-R5`, `N8-R6`, `N8-R8`, `N8-R9` | `where-an-item-got-to.md` | 0 |
| `Update` | `N2-R15`, `N2-R16`, `N2-R19`, `N2-R20`, `N2-R22`, `E5-R6`, `E5-R10`; `N14-R3`, `N14-R4` | `reaching-a-stack.md`, `what-a-machine-says.md`; `what-is-running-here.md` | 21 |
| `Upgrade` | `N24-R4` | `choosing-how-good.md` | 0 |
| `Walkthrough` | `N15-R6`, `N15-R7`, `N15-R8`, `N15-R9` | `watching-one-thing-arrive.md` | 0 |

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

`Hosting`'s three are `caveat`, and per command `definition` and `runs`.

`History` does not answer `N11-R4`, the reason a change was made: the envelope
carries no such field, because the stack's journal records none, and `because`
is why putting a change back stops short rather than why it was made.

`Config`, `Doctor` and `Outbound` carry the same `origin` on each setting, each
finding and each service: bundled, operator, a named plugin, a named plugin's
override with the value it replaced, a value a removed plugin left, or unknown
with the stack's reason. Its eight paths on each of the three are read, into one
type, and shown. A setting says its origin on every row. A check or a service
says it only where it is not the stack's own, with one line under the list saying
what an unmarked row is, which is how the stack's own terminal draws them. An
origin that cannot be read refuses the reading rather than defaulting to bundled
(`F7-R11`).

## What watches the envelopes

The companion has a machine-checked register for unread fields,
`WhatTheContractCarriesThatNothingReadsTest`, and its rule is that every path
on an envelope the app reads is either followed to a reader or listed with a
reason. A hundred and forty-three rows, over the one thousand and twenty-seven
paths the contract declares on the thirty-nine envelopes the app reads.

**It cannot see any of the twenty-three**, and the reason is one line of its own
scaffolding:

```php
foreach (WhatTheReadersRead::envelopes() as $envelope) {
```

It walks the envelopes a reader already reads. An envelope nothing touches
contributes no paths, so it can never be flagged — the blind spot is exactly the
shape of the gap. The rule watches fields arriving on envelopes the app already
knows about.

Whole envelopes are held by `EveryActionTheStackOffersTest`, which names every
kind in one of its three lists, so a kind the stack adds fails there as
unclassified. `NOT_YET` claims only that somebody looked: it carries no reason
and no account of what the envelope holds. This register is that account.

---

## Connecting it together

The surface that lets an operator wire the stack up. The app draws none of it.
Its kernel holds the types a wiring would be read into, recorded in the
companion's `connecting-the-stack.md`.

| Envelope | What it carries |
|---|---|
| `plugins` **(not served)** | Which plugins are `installed`, and what installing, updating or removing one came to — `install`, `update` and `removal` — and every capability the operator chose one of a plugin's services to fill, `substituted`. The whole of what an operator opens a plugin screen to see. |
| `wiring` **(not served)** | Which service asks for which capability, and how each is settled: `outright`, `each`, **`contested`** with its claimants, **`chosen`** with what it was chosen over, `whose` choice it was — `stack` or **`operator`** — and why, or `unfilled`. Plus `unfilled`: services asking for something nothing answers. |
| `substitution` **(not served)** | Applying one service in place of another for a capability: who asked for it, what it was `was` and is `now`, the setting that carries it, and `leaves_unfilled` — what the swap breaks. |
| `catalogue` | What each service is for — every service the stack's manifest holds, not only the ones a form would start: its `criticality`, what it `describes`, and `without_it` — what the household loses by not having it. Plus `removed`, with the reason and what replaced it. |

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

**Serving them is required, and scheduled.** `F6-R14` requires what is installed
to be a read of the web API, `F6-R15` requires installing, updating and removing a
plugin to be actions of it, and `F6-R16` requires each of those to be rehearsable
there. `F4-R26` requires the wiring to be a read, `F4-R27` requires choosing which
service fills a capability to be an action, and `F4-R28` requires that choice to be
rehearsable. `0.18.0`, which is planned, locks all six as goals, with `F4-R29`,
which gives the choice an optional reason on both surfaces.

So they are a different kind of row from everything else here. Every other
envelope in this register is a decision waiting to be made, or, for `setup` and
`wizard`, one `N1-R4` has made; these three have no decision about the companion
that can reach them while no route serves them. The companion records the same
for `N5`: `N5-R2`, `N5-R4`, `N5-R7`, `N5-R10`, `N5-R11` and `N5-R13` cannot be
answered there until a read exists.

**The `wiring` row names a choice nothing can make.** The core will not resolve
a contested capability — the command line says *nothing wires to it until the
operator chooses, and lemonfiber does not choose by install order*. The contract
models that choice, down to `whose: 'operator'`.

There is nowhere in the companion to make that choice, and nowhere on the wire
to read that it is waiting. `F4-R26` requires the read that says it is waiting,
and `F4-R27` the action that makes it: for a contested capability too, recorded
and journalled as the command records it, and read back as the operator's, with
their reason where they gave one (`F4-R29`).

## Guided setup

The companion excuses `setup` and `wizard` under `N1-R4`: setup is performed at
the machine, and the app says so rather than offering it.

| Envelope | What it carries |
|---|---|
| `wizard` | Where first run has got to: `at` one of fourteen named stages from `welcome` through `vpn`, `credentials`, `library`, `household` to `review`; whether it `asks`, whether it was `offered`, and the `phase`. |
| `setup` **(not served)** | What setup settled: the `data_root`, which `protocols` are on, the `service_user`, and whether it was `applied`, `abandoned` or was `already-set-up`. Written by the command line's own setup; the setup endpoints answer with `wizard`. |
| `step` | One step of a walkthrough while it runs, on the event stream: its stage — `choosing`, `searching`, `grabbing`, `downloading`, `importing`, `scanning`, `available` — with what was `said` and the `detail` under it. The app follows a running walkthrough by asking after its job, and reads its lines from the record it finishes with. |
| `word` | One entry of the glossary, alone: `word`, `short`, `deep`, `also_called` and `forms`, from `GET /api/explain?word=`. `N15-R11` asks for it where the glossary the app holds has no entry. |

## Putting things back

Copies are read: `archives`, `backup` and `restore`, above. These two put the
stack back without one.

| Envelope | What it carries |
|---|---|
| `undo` | Putting back one run of changes — the last repair, or a run named by the stamp its entry in the history carries: what was `reversed`, each with what it `does` — remove, restore, delete, withdraw, repin or reconfigure — what was `left` and `noted` and why, and whether it was `rehearsed`. |
| `reset` | Putting configuration back to lemonfiber's own: what was `reverted`, with a diff per path, and which connections went with it. |

## Moving in

The survey of what is already on the machine, `migration`, is read, drawn by
`WhatIsAlreadyOnThisMachine`. These are the acts, and the companion records
`N7-R1` to `N7-R4`, carrying out a mode, and `N7-R7` to `N7-R10` and `N7-R15` to
`N7-R17`, the `seed` action, as asked for and not drawn.

| Envelope | What it carries |
|---|---|
| `adoption` | Taking over an existing setup: what would be `upgrade`d, service by service, with the verdict, the reason, whether it was `refused` and whether it wants a backup first. Plus a `stance` and what to `back_up`. |
| `beside` | Standing lemonfiber beside a setup already on the machine — A5's beside mode: where each service would listen instead, as `ports` with the `service`, the port it moves `from` and the one it moves `to`; where the Compose file that says so was `written`; the `refusal` where nothing was; and a `stance` of unchanged, pending, blocked or applied. |
| `replacement` | Standing in place of a setup already on the machine — A5's replace mode, which stops that project's containers and deletes none: what `would_stop`, what was `stopped`, what is `still_running`, the `refusal` where nothing was, and a `stance`. `N7-R18` asks for it. |
| `import` | What an existing setup brings across: what is `carried`, what is `not_carried` and because of what, and what `would_carry`. |
| `seed` | What the stack wires up on the operator's behalf, each wiring with a severity that names the breakage and its remediation, and what is `unsupported` and why. |

## A service's life

| Envelope | What it carries |
|---|---|
| `start` | A bare string: one line of what a start is waiting for, on the event stream, the newest replacing the one before. `N2-R23` asks for it. |
| `uninstall` | Taking the stack off: an agreement, the bytes, what is `foreign` and left behind, and a `confidence` naming what could not be read. `N13` asks for it. |
| `watch` | The data-root guard, once the data location it was guarding was lost: the `forms` it stopped, whether stopping them succeeded (`stopped`) and the `reason`, and on a rehearsal what it `would` keep — the `root`, how often it looks (`every`) and the `command` it would run. Over HTTP it is a job that lives only while somebody asks about it. `N23-R11`, `N23-R12` and `N23-R13` ask for it, and `N8-R7` for the reason it stopped. |
| `version` | What is running and what has shipped: the binary, and a `changelog` of releases with what each `delivers`, what it `patches`, whether it is `user_facing` and whether it was `withdrawn`. |
| `stop-seeding` | Stopping a torrent: the download, its `standing` — never imported, seeding at a ratio, or left alone — and what stopping it costs. |

## Household and access

| Envelope | What it carries |
|---|---|
| `removal` | Removing a person's access: how widely it was `revoked` — everywhere, the media server only, or nothing — how many `requests` they had, whether they ask through the request service, and the `findings`. `N13-R1`, `N13-R3` and `N13-R19` ask for it. |
