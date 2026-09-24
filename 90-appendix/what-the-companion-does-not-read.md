# What the wire carries that the companion does not read

**Status:** Register · **Measured 22 September 2026** · **Re-checked 23 September 2026**, when `hosting` became the first envelope this register lost to a reader

The stack **publishes** sixty-two envelopes and **serves** fifty-nine. The
companion app follows fifteen of them. This is the other forty-seven, written down
so that what fills them is a decision somebody made rather than whatever the
next person happened to notice.

The gap between sixty-two and fifty-nine is the correction this register most
needed. An earlier version said the stack served all sixty-two, which put three
envelopes in here under the wrong heading: they are not envelopes the app has
not got to, they are envelopes it cannot reach.

It is a register of **facts**, not of requirements. No row here proposes a
screen. `N1-R17` is the rule that matters: a field wants a requirement before it
wants a surface, and a surface built because the wire happens to carry a field is
a surface nobody asked for. Every row is an invitation to decide, and *no
requirement asks for this* remains a complete answer.

## How it was measured

Reproducible, from the companion's checkout:

```
ls vendor/lemonfiber/sdk-php/src/Generated/*Envelope.php | wc -l   # 62
Tests\Support\WhatTheReadersRead::envelopes()                      # 15
```

| | |
|---|---|
| Envelopes the SDK ships | **62** |
| Followed by a reader | **15** |
| Not followed | **47** |
| — never referenced anywhere in the app | **45** |
| — referenced but not followed | **2** |

The fifteen that are read: `Config`, `Doctor`, `Error`, `Held`, `History`,
`Hosting`, `Household`, `Job`, `Log`, `Outbound`, `Provenance`, `Repair`,
`Status`, `Stuck`, `Update`.

`Outbound` is the newest. It answers `N10-R1`, `N10-R2`, `N10-R3` and
`N10-R12` — lemonfiber's own requests and the services' in two lists that are
never merged, each of lemonfiber's with its purpose, destination, switch and
the cost of turning it off, and a list that could not be read told apart from
an empty one. A service the stack has no record of is drawn as unknown, never
as reaching nothing. Every one of its paths is read.

`Provenance` came before it. It answers `N11-R7` and `N11-R8` — a licence on
every service, and the pin and licence shown whatever becomes of the upstream,
because nothing is looked up — and `N11-R6` in part: image, upstream and
licence are drawn, and the version it is `pinned` at stands where the digest
belongs, because the stack pins by tag (`E1-R1`). Every one of its paths is
read.

`History` came just before. It answers `N11-R1`, `N11-R2`, `N11-R3`, `N11-R9` and
`N11-R10` — the record's horizon said where the list ends, how far each change
could be put back and why it stops short, how many changes came with it, an
empty record told apart from one that could not be read, and changes made at
one moment drawn together. Every one of its paths is read. `N11-R4`, the
reason a change was made, is not: the envelope carries no such field, because
the stack's journal records none, and `because` is why putting a change back
stops short rather than why it was made.

`Hosting` was the first this register lost to a reader. It
answers `N16-R5`, `N16-R6` and `N16-R13` — whether the stack comes back after a
restart, what did not come back, and the difference between a platform this
product cannot configure and a machine with nothing running. Five of its paths
are still unread and are recorded as such in the companion's own register:
`caveat`, `changed`, and per command `definition`, `output` and `runs`.

`Admission` and `Pull` are the two referenced without being followed — the app
reads admission through `Admitted` rather than through the envelope, and `Pull`
carries a bare string.

## Why nothing caught this

The companion already has a machine-checked register for unread fields,
`WhatTheContractCarriesThatNothingReadsTest`, and it is a good rule: every path
on an envelope the app reads is either followed to a reader or listed with a
reason. Sixty-one rows, three hundred and twenty-four paths.

**It cannot see any of the forty-seven**, and the reason is one line of its own
scaffolding:

```php
foreach (WhatTheReadersRead::envelopes() as $envelope) {
```

It walks the envelopes a reader already reads. An envelope nothing touches
contributes no paths, so it can never be flagged — the blind spot is exactly the
shape of the gap. The rule watches fields arriving on envelopes the app already
knows about; nothing watches whole envelopes the app has never opened.

That is worth fixing on its own, and it is not what this register is for.

---

## Connecting it together

The surface that lets an operator wire the stack up. None of it exists in the
app today.

| Envelope | What it carries |
|---|---|
| `plugins` **(not served)** | Which plugins are installed, and one being installed now — `install` and `installed`. The whole of what an operator opens a plugin screen to see. |
| `wiring` **(not served)** | Which service asks for which capability, and how each is settled: `outright`, `each`, **`contested`** with its claimants, or **`chosen`** with what it was chosen over, `whose` choice it was — `stack` or **`operator`** — and why. Plus `unfilled`: services asking for something nothing answers. |
| `substitution` **(not served)** | Applying one service in place of another for a capability: who asked for it, what it was `was` and is `now`, the setting that carries it, and `leaves_unfilled` — what the swap breaks. |
| `catalogue` | What the stack could run and does not: each service's `criticality`, what it `describes`, and `without_it` — what the household loses by not having it. Plus `removed`, with the reason and what replaced it. |
| `bundle` | A support export: its `pieces`, what is `missing`, when it was `taken` and against which versions, and `terms` — whether filenames are revealed, what else is, and over what `window`. |
| `beside` | Ports a service asks to be reachable on beside the front door, with a `stance` of unchanged, pending, blocked or applied. |
| `preview` | What a change would come to before it is made: the services, profiles and forms it would leave, and what it `dropped` and why. |

**Three of these are not served at all.** `wiring`, `substitution` and
`plugins` are published in the contract and generated into the SDK, and no HTTP
route or action produces any of them. Checked against the core's routes, its
dispatched reads and the list of action names it will accept, with `catalogue`,
`forms` and `alerts` as controls that pass the same test. Raised as
[lemonfiber#731](https://github.com/lemonfiber/lemonfiber/issues/731).

**Re-checked 23 September, against the core at `688865f`, and all three still
hold.** `lemonfiber-api` names none of them: there is no handler, and no
`wiring`, `substitution` or `plugins` module among the per-read modules beside
`catalogue`, `provenance`, `stack`, `outbound` and `history`. The single action
route accepts only the names in `actions/named.rs`'s `OFFERED` — forty-one of
them, and not one is a plugin, wiring or substitute verb, so an action outside
that list is refused before a command is built.

**The kind exists because the command line produces it, which is why the
generated surface lists it.** `contract/web-api.surface.json` maps every kind to
its type, including these three, and that file is not evidence of a route. The
plugin work landing in 0.16.0 added `Outcome::Plugins` and grew the envelope for
the core and the CLI; nothing on the HTTP surface asks for it. A register that
read the surface map would have called this fixed and been wrong.

**They are waiting on a release rather than on a route being forgotten**, and
that is the correction this paragraph most needed. Serving them now would
publish a surface over the plugin install and removal lifecycle while that is
still being built, and the two slices left in it — the capability set and the
command surface (`F6-R10`, `F6-R13`) — are the ones that decide what a plugin
action's arguments are. A `plugins` read and a plugin action belong on top of a
finished lifecycle. `wiring` and `substitution` are in the same position for a
different reason: both have a settled report in the core and want only a route.

So they are a different kind of row from everything else here. Every other
envelope in this register is a decision waiting to be made; these three are
waiting on a version, and no decision about the companion can reach them until
it lands. They are the candidate for the first slice after 0.16.0, which is
where `N5` would stop being unanswerable.

**The `wiring` row is the one with a hole under it, and the hole is deeper than
it first looked.** The core will not resolve a contested capability — its own
reader says *nothing wires to it until the operator chooses, and lemonfiber does
not choose by install order*. The contract already models that choice, down to
`whose: 'operator'`. The core can answer the question: `Command::Wiring`
produces `Outcome::Wiring`, reachable from the command line.

There is nowhere in the companion to make that choice, and nowhere on the wire
to read that it is waiting.

## Guided setup

| Envelope | What it carries |
|---|---|
| `wizard` | Where first run has got to: `at` one of fourteen named stages from `welcome` through `vpn`, `credentials`, `library`, `household` to `review`; whether it `asks`, whether it was `offered`, and the `phase`. |
| `setup` | What setup settled: the `data_root`, which `protocols` are on, the `service_user`, and whether it was `applied`, `abandoned` or was `already-set-up`. |
| `step` | One step of a running job, as a stage — `choosing`, `searching`, `grabbing`, `downloading`, `importing`, `scanning`, `available` — with what was `said` and the detail under it. |
| `walkthrough` | A first acquisition narrated end to end: the `lines` it produced, whether it ran `in_background`, whether the thing was `already_here`, and a `handover` naming what to do next. |
| `forms` | The forms a service can be asked for, each with a description and whether it is `composable`. |
| `glossary` | The vocabulary itself: each `word`, a `short` gloss, a `deep` one, and what it is `also_called`. |
| `word` | One entry of that glossary, alone. |

## Backups and recovery

The companion's own `app-modules/backups` is deliberately empty, and its README
says why: nothing in `N1`–`N4` asks the app to do anything with a snapshot, and
the module is a held name rather than abandoned work. These six rows are what a
requirement would be written against.

| Envelope | What it carries |
|---|---|
| `backup` | A snapshot being taken: its `scope` — whole stack, one service, or an existing project with its trees — the `path`, what was `pruned`, whether it was `rehearsed`, and the `pace` it moved at against a budget. |
| `restore` | A snapshot being put back: what it was restored `from_version`, the `scope`, and whether anything was `relocated` from where it used to live. |
| `archives` | The snapshots that exist. |
| `stored` | What the stack keeps and where: each item's location, whether it is `secret`, why it is kept, what sits `beside` it, and the state of any `removal`. |
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
| `trace` | Where one wanted thing has got to, with `confidence`, and `coverage` season by season — what is outstanding and the stage each episode reached. |

## A service's life

| Envelope | What it carries |
|---|---|
| `lifecycle` | Starting, stopping and restarting: the `action`, the `command`, the `condition` — inactive, degraded, partial, active — what is `held`, and the `plan` with what it dropped. |
| `start` | A bare string. |
| `removal` | Removing a person's access: what was `revoked` and how widely, how many `requests` they had, and the `findings`. |
| `replacement` | Swapping a service out: what was `stopped`, what `would_stop`, what is `still_running`, and a `stance`. |
| `uninstall` | Taking the stack off: an agreement, the bytes, what is `foreign` and left behind, and a `confidence` naming what could not be read. |
| `upgrade` | Moving media to a new preset: per media type, the preset, size per hour and the outcome. |
| `self-update` | The companion updating itself: how it was `installed` — homebrew, scoop, winget, cargo, distribution, installer or elsewhere — what it `carries`, and what happens `afterwards`. |
| `version` | What is running and what has shipped: the binary, and a `changelog` of releases with what each `delivers`, what it `patches`, whether it is `user_facing` and whether it was `withdrawn`. |
| `stop-seeding` | Stopping a torrent: the download, its `standing` — never imported, seeding at a ratio, or left alone — and what stopping it costs. |
| `space` | What is taking room and what could go: each candidate's bytes, its `standing`, and the `consequence` of removing it. |

## Household and access

| Envelope | What it carries |
|---|---|
| `invitation` | Inviting somebody in: the address, how many `hours` it stands for, whether it was `linked`, and what was `applied` — which libraries, what filtering, whether unrated material is held back, and whether they may make requests. |
| `credentials` | Every secret the stack holds: its `origin` — operator, service or lemonfiber — its `state` from absent through active, stale, invalid, rotating to superseded, which services `consume` it, its `location` and `fingerprint`. |
| `clients` | Which apps work on which devices: `support` rated good, workable, poor or fallback, with a `caution` and an `instead`, plus what to say when nothing is installed and when it only works at home. |
| `front-door` | How the household reaches the stack: the address, what is `beside` it and what each is `facing`, and whether the address was `derived` or chosen. |
| `dashboard` | The whole front page in one envelope: alerts with severity, meaning, what they affect and their remedies, alongside the door. |

## Resources and evidence

| Envelope | What it carries |
|---|---|
| `bandwidth` | What the line can carry and what is using it: `capacity` up and down, whether it was `declared` or `observed`, whether it runs through the tunnel, a monthly `cap` and what happens when it is exceeded. |
| `alerts` | What the stack will tell somebody about: the `preset`, what it `means`, the `exceptions`, and whether it has been `rehearsed`. |
