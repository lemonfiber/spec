---
id: G11
title: The operator's web console
kind: feature
area: G
audience: operator
status: accepted
maturity: building
priority: P2
labels: [web, ux, extensibility, security]
requires: [G1, F14]
relates: [G10, F6, A7, N25, N9, E3, N6, N4, N2, A2, A4, A6, B8, B9, D2, D9, F1, H5, K2, F5, F7, F8, C10, E1]
---

# G11 — The operator's web console

**Status:** Accepted · **Audience:** Operator · **Area:** G — Cross-cutting UX

---

## Purpose

The operator's side of the web surface, in a browser, held to what it shows and
asks for where the core's requirements leave that to the surface.

[G1](g1-interface-tiers.md) says every action is available from every surface and
that no surface implements behaviour of its own. The core's rows say what an act
takes and what a read carries; they do not say how a console draws a consent or
what it tells the operator afterwards. [G10](g10-household-web.md) says that for
the household's side of the same surface, and the companion says it for itself in
N. This page says it for the operator at a browser.

It holds a third-party plugin's grants: a credential of another service that
crosses to a plugin for a capability it fills
([F14](../f-extensibility/f14-every-part-is-a-plugin.md)). It holds how a running
backup or restore is drawn ([E3](../e-maintenance/e3-backup-restore.md)), and what
the alerts panel says when the alerts sent again after a break in the stream may not
be all of them.

It holds what the console names before an act that stops downloads, how it shows
the way it is served itself, how the stack runs without lemonfiber, what setup
settled and the choices setup made, the readings of the machine's health, and
choosing a quality.

## Behaviour

### Approving a grant

An install or update of a third-party plugin is read before it is agreed to, and
the reading names each credential of another service that would cross to it: the
setting it is held under, the service whose credential it is, and the capability
of the plugin's own it is for. No value is shown, because the reading carries
none.

Each grant has a switch of its own beside it, off until the operator turns it on.
Agreeing to the reading agrees to the plugin and to nothing that would cross to
it, as with a value a recipe would carry elsewhere and a privileged shape a
service would take. The yes carries each grant switched on, written exactly as
the reading names it. An update asks for every grant again, so one the plugin
already holds is switched off like any other until the operator turns it on.

### The grants a plugin holds

Each installed plugin lists the grants it holds, each by its setting, its
service, the capability it fills and when it was approved. The credentials panel
lists every grant again beside the credential it crosses, with the plugin it is
granted to, so either place answers *who holds this*.

### Ending a grant

A grant can be revoked. The revoke is read first, labelled as nothing ended yet:
the grant it would end and the plugin's services that would restart once the
credential is withdrawn. The yes carries the name that reading gave itself, and
the core refuses it where the grant has moved since.

Afterwards the console says whether the grant ended, which services restarted,
and the core's reason where they did not. It says that the plugin stays installed
with the capability the credential was for left unfilled, and that a value
already handed to the plugin is taken back only by rotating the credential.

### A backup or restore that is running

The disk screen, where the backups are kept, shows a backup or restore while it
runs: whether it is a backup or a restore, how much it has written of how much it
will, as a bar and in words, and the part it is writing now, named as the stack
names it. It says in plain words whether the copy is working, slowed on purpose to
the limit the operator set, or stalled, with when it last wrote (`E3-R17`).

What it shows is what the stack says, read from `GET /api/copying` on the way into
the screen and from each `copying` event the stream carries after that, every
5 seconds while a copy runs. The screen works out no progress, stall or end of its
own: a page that heard nothing for a while has learned something about its
connection, not about the copy, and the panel's stamp says how old what it shows
is. Where no copy runs, the screen says nothing of one.

The figures change every 5 seconds and are not read out each time. A screen reader
is told when the copy's state or its part changes, and reads the figures when it
reaches the bar.

### Alerts that may be missing

When the stream breaks and opens again, the stack sends again the alerts raised
meanwhile and says first whether that is every one of them (`ARCH-R281`). Where it
says `partial`, the overview's alerts panel shows a quiet note: *Some alerts raised
while this page was away may be missing.* The note sits above the alerts and adds,
removes or reorders none of them. It is shown where the overview is open when the
stream says it, or the next time the operator opens the overview, and it is gone
once the operator leaves the overview, as the companion's line is gone once its
health screen has been opened (`N4-R28`). A replay that says `whole` adds nothing.

### Before a stop

A stop, an update, an uninstall, a configuration change, a restart and a switch
each stop services, and a download still coming down inside one is interrupted.
Before the operator agrees to one, the console reads `GET /api/in-flight` for what
that act would stop: the forms or services it names, or the whole stack where it
names none. It names each download the stack lists, with how far along it is and
the kind of client holding it, above the yes.

A stop, an update, an uninstall and a configuration change take `wait`, so the
console offers letting the downloads finish first beside going ahead now, and going
ahead says they will be interrupted. A restart and a switch take no `wait`: the
console names what they would interrupt and offers no choice to let it finish.

Where the stack names nothing, the console adds nothing. Where it cannot be asked,
the console says it could not find out and still offers the act. The companion does
the same before the acts it offers (`N2-R42`).

### How this machine stands

The settings show four readings, each read on the way in and none changing
anything.

- **This console**, from `GET /api/served`: the port, whether it is encrypted and
  offered to the network, the name a request has to carry, and the certificate it
  presents, with its fingerprint in full for the operator to compare with what the
  browser shows. A console served without encryption to the network says so in the
  panel, and an alarm banner says it on every visit to the settings until it is
  served encrypted.
- **Running without lemonfiber**, from `GET /api/stack`: which stack runs and where,
  the project directory and its `.env`, the exact `docker compose` words, how an
  action runs without questions, and each part those words alone do not bring up.
- **What setup settled**, from `GET /api/settled`: where the library is kept, which
  ways of downloading are set up, the user and group the services run as, and
  whether the stack is set up.
- **The choices setup made**, from the `config` read the configuration panel
  already takes: every decision with what changing it affects and costs, and never
  its value; and every area the operator declared unmanaged, with what it covers
  now. A decision is changed through the configuration change the console already
  reviews.

### The machine's health

The checks screen shows starting with the machine (`GET /api/boot`), what watches
the stack from outside (`GET /api/watcher`) and the self-healing of stuck downloads
(`GET /api/queue`), each item of which opens its trace. The settings show where
alerts go (`GET /api/notify`): each back-end, how far it is proven and what it last
delivered, and never a credential. Each is shown as the stack says it: a watcher
that does not answer is not an all-clear, and a check after an earlier start is not
the check after the latest.

### Choosing a quality

The quality panel offers a preset for everything or for one kind of media, or a
format for music, from what the `quality` reading offers and nothing else. A choice
is rehearsed first and shows what it means, its size and what playback costs, with
the stack's sentence that it shapes future downloads only. Where this machine would
have to transcode it in software, the rehearsal holds it, the warning is shown, and
the yes says it is chosen anyway.

Putting the recorded preset back over a hand-edited configuration is rehearsed
first too: the console shows each file it would replace, with the lines that go and
the lines that land, before the yes.

### Plugins, complete

Under each installed plugin the console offers proving it again and running one of
its recipes. Each is rehearsed first and done on a yes carrying the offer the
rehearsal made; a recipe's approvals are asked as an install's are. Every input a
recipe asks the operator for is asked inside the install, update or run reading
before the yes, and a secret input is typed hidden and never shown back. The
Plugins panel also lists what the verified catalogue offers, with what is installed
of each; installing one goes through the install reading the console already has.

### Keys and phones

Minting a key can hand it to a program as a claim: the console shows the claim link
once, as text and as a scannable code, with when it lapses, and never the key's
secret, which the program collects itself. The console lists each phone's hardware
key and each phone that can be woken, and revokes or removes one on a yes naming
it. A wake address is shown by its host and a short fingerprint, the only two
things the stack answers about it, because the whole address lets anyone holding
it wake the phone.

### One service at a time

An update can move one service alone, reading first what stopping it would
interrupt; a backup can take one service alone; and a service that runs and exits
can be run now, rehearsed first. Work that ended before it finished says whether
its name was released or the work was let go, told apart from work that finished
or failed, and putting away the record of work still running forgets its name
without ending it: the console stops following it, and the work runs on and stays
in the journal.

### What this credential can do

The console reads what the stack and the credential it holds can do once per
session. A panel the credential cannot use is drawn silenced, with one sentence
saying why; a single control it cannot use is not drawn. No version number decides
it.

### The operator alone

Grants, and revoking them, a running copy, the note, what a stop would interrupt,
how this machine stands, its health and its quality, plugins, keys and phones, one
service's controls and what the credential can do are drawn for the operator. A
member signed in to the same surface is shown none of it
([G10](g10-household-web.md)).

## Requirements

| ID | Requirement |
|----|-------------|
| **G11-R1** | Where an install or update of a third-party plugin names a credential of another service that would cross to it, the console's reading MUST show each one with the setting it is held under, the service whose credential it is and the capability of the plugin's own it is for, and never its value. The operator MUST approve each one apart from the offer, on a switch of its own that is off until turned on; agreeing to the offer MUST approve none of them, and the yes MUST carry each approved one exactly as the reading names it (`ARCH-R323`, `F14-R20`). Every update MUST ask again, and a grant the plugin already holds MUST NOT be taken as approved. Where the stack refuses the act for a grant left off, the refusal MUST be drawn in the stack's words. |
| **G11-R2** | The console MUST list, for each installed plugin, the grants it holds, each with the setting the credential is held under, the service whose credential it is, the capability it fills and when it was approved, and never a value (`ARCH-R323`). |
| **G11-R3** | The console MUST offer revoking each grant a plugin holds. The revoke MUST be read first, labelled as nothing ended yet, showing the grant it ends and the plugin's services it would restart; the yes MUST carry back the offer the stack named (`ARCH-R324`). Afterwards the console MUST show whether the grant was ended, the services that restarted and, where they did not, the stack's reason, and MUST say that the plugin stays installed and that rotating the credential is what takes back a value already handed (`ARCH-R324`). |
| **G11-R4** | A plugin's grants, and revoking them, MUST be shown to the operator alone and MUST NOT appear anywhere a member is shown (`G10-R9`). |
| **G11-R5** | The console's credentials panel MUST list every grant beside the credential it crosses, with the plugin it is granted to, the capability it is for and when it was approved, and never a value (`ARCH-R325`, `F14-R20`). |
| **G11-R6** | While a backup or restore runs, the console's disk screen MUST show it in a panel of its own: whether it is a backup or a restore, the bytes written of the bytes it will write as a progress bar whose text equivalent says both figures, the same figures in words, and the part being written now as the stack names it (`E3-R17`). It MUST be drawn from the `copying` read on the way into the screen and from each `copying` event the stream carries after that, without the screen being opened again (`ARCH-R456`, `ARCH-R457`), and MUST NOT show a progress, a stall or an end the stack has not said. Where no copy runs, the screen MUST show no such panel. |
| **G11-R7** | The panel MUST say in plain words whether the copy is working, slowed on purpose to the operator's limit, given per second, or stalled, with when it last wrote, telling the slowed and the stalled apart as the stack says them (`E3-R18`, `E3-R19`). Its live region MUST be polite and MUST be changed only by a change of state or of part, never by an update of the figures alone. |
| **G11-R8** | After the stream resumes with a `replay` event saying `partial` (`ARCH-R281`), the overview's alerts panel MUST show a note that some alerts raised while the page was away may be missing, drawn calm, and MUST NOT add, remove or reorder an alert for it. The note MUST be shown on the overview open when the event arrives, or else the next time the operator opens it, and MUST be gone once the operator leaves the overview (`N4-R28`). A `replay` saying `whole` MUST add nothing. |
| **G11-R9** | The running copy and the note MUST be shown to the operator alone and MUST NOT appear anywhere a member is shown (`G10-R9`). |
| **G11-R10** | Before the operator agrees to a stop, an update, an uninstall or a configuration change, the console MUST read `GET /api/in-flight` for what that act would stop, the forms or services it names or the whole stack where it names none, and MUST name each download the stack lists, with how far along it is and the kind of client holding it (`ARCH-R447`). It MUST offer letting the downloads finish first, sent as `wait`, beside going ahead now, and going ahead MUST say that they will be interrupted (`A6-R11`). Where the stack names nothing, the console MUST add nothing. Where the read is refused or the stack cannot be asked, the console MUST say it could not find out and MUST still offer the act with both choices. |
| **G11-R11** | Before the operator agrees to a restart or a switch, the console MUST read `GET /api/in-flight` for the forms or services it would stop and MUST name each download the stack lists as `G11-R10` does, saying that they will be interrupted, and MUST NOT offer letting them finish first, which neither act takes. Where the stack names nothing, the console MUST add nothing. Where the stack cannot be asked, the console MUST say it could not find out and MUST still offer the act. |
| **G11-R12** | The console's settings MUST show how the console itself is served, read from `GET /api/served` (`ARCH-R448`): its port, whether it is encrypted, whether it is offered to the network, the name a request has to carry where one is given, and the reason the stack gives where it could not record where the console is served. Where it is encrypted, they MUST show the certificate's fingerprint in full beside a sentence asking the operator to compare it with what the browser shows (`N1-R18`), who it is made out to and who signed it, whether it is self-signed, the names it covers with how many are left out, and when it is valid from and until. A subject, an issuer and a name MUST be drawn as plain text, and one cut MUST be marked as shortened. |
| **G11-R13** | Where the console is served without encryption to the network, the panel MUST say so, and an alarm banner saying so MUST be shown on every visit to the console's settings until it is served encrypted. A console served without encryption to this machine alone MUST NOT raise the banner. |
| **G11-R14** | The console's settings MUST show how the stack runs without lemonfiber, read from `GET /api/stack` (`F1-R15`): whether it runs the stack lemonfiber ships or the operator's own and where that is, the project directory and the `.env` beside it, the exact `docker compose` words as one command the operator can copy, how any action is run without questions, and each part those words alone do not bring up with why. A refusal MUST be drawn in the stack's words and MUST NOT be drawn as the stack lemonfiber ships. |
| **G11-R15** | The console's settings MUST show what setup settled, read from `GET /api/settled` (`A2-R16`): where the library is kept or that no place is set, whether downloading over Usenet and over torrents is each set up, the user and group the services run as and where each came from, and whether the stack is set up, part-way through setup or not set up. |
| **G11-R16** | The console's configuration panel MUST list every decision the `config` read carries (`ARCH-R449`), each by its setting, what changing it affects, whether a change takes a restart or is said and confirmed first, whether it is held and whether its value is withheld as a credential, and MUST NOT show a value; changing one MUST go through the configuration change the console already reviews. The panel MUST list every area declared unmanaged (`ARCH-R453`) with its reason, each drawn as plain text and marked where cut, and each thing it covers now by its kind and name, with how many areas and covered things are left out; where none is declared it MUST show no such list. |
| **G11-R17** | The console's checks screen MUST show starting with the machine, read from `GET /api/boot` (`B8-R16`): when the machine last started or that it does not say, the check kept against that start with what it came to, each service that did not come back, whether the tunnel came back and the forwarded port, why a run after the start started nothing where one did, and since when and for how many starts the stack has not come back. Where no check ran after the latest start, the newest check MUST be shown as against the start it names and MUST NOT be shown as against the latest. |
| **G11-R18** | The console's checks screen MUST show what watches the stack from outside, read from `GET /api/watcher` (`K2-R16`): the plugin that watches or that none does, every monitor with how it checks, what it sees and since when, its last reading, its heartbeat and whether it is active, what it watches instead where it does not watch what it should, and every critical service and entry point no active monitor covers. A watcher that does not answer MUST be shown with why and as nothing seen, and MUST NOT be shown as all clear. |
| **G11-R19** | The console's checks screen MUST show the self-healing of stuck downloads, read from `GET /api/queue` (`H5-R16`): whether healing acts, the strikes and grace in force, every unhealthy item with the service holding it, its title or release, why, its strikes, until when it is left alone and what the next run would do to it, each curator or download client that could not be reached, the mismatch where there is one, whether the list may be short, and the newest runs with whether each was rehearsed and what it did. Each item MUST open its trace (`D9-R11`). |
| **G11-R20** | The console's settings MUST show where alerts go, read from `GET /api/notify` (`ARCH-R400`): where delivery as a whole stands, each back-end with what it speaks, where it reaches, who chose it, how far it is proven, its newest delivery, every failure since its last confirmed one and a delivery still to be tried again, and each back-end whose record could not be read with why. It MUST NOT show a credential. |
| **G11-R21** | The console's quality panel MUST offer choosing a preset for everything or for one kind of media, or a format for music, from what the `quality` reading offers and from nothing else (`D2-R13`). The choice MUST be rehearsed first, showing what it means, roughly how much disk an hour of it takes and what playback costs, and the stack's sentence that it shapes future downloads only (`D2-R2`, `D2-R14`). Where the rehearsal holds the choice because this machine would have to transcode it in software, the console MUST show the warning and its yes MUST say that it is chosen anyway (`D2-R4`). |
| **G11-R22** | Putting the recorded preset back over a hand-edited configuration MUST be rehearsed first, showing each file it would replace with the lines that go and the lines that land in their place, or that nothing edited would be replaced, and MUST be done only on a yes given after that reading (`D2-R8`). |
| **G11-R23** | What `G11-R10` to `G11-R22` show MUST be shown to the operator alone and MUST NOT appear anywhere a member is shown (`G10-R9`). |
| **G11-R24** | Under each installed plugin the console MUST offer proving it again (`plugin-prove`, `ARCH-R286`), rehearsed first and run only on a yes carrying the offer the rehearsal made (`ARCH-R146`), and MUST show what each proof came to in the stack's words, a pass saying the recorded failure is cleared; where the offer has moved, it MUST show the stack's refusal and MUST NOT run it. |
| **G11-R25** | Under each installed plugin the console MUST offer running one of its recipes by name (`plugin-run`), rehearsed first, showing what it would do and each approval it asks, approved one by one as an install's are (`G11-R1`), and run only on a yes carrying the offer and those approvals (`ARCH-R146`). |
| **G11-R26** | The install, update and run readings MUST ask each input the plugin reading lists for the recipe (`F8-R19`) by its question before the yes, and MUST send them as `inputs`; an input marked secret MUST be typed hidden and MUST NOT be shown back, put in an address or kept by the page once sent. |
| **G11-R27** | The Plugins panel MUST list what `GET /api/plugins/catalogue` returns (`ARCH-R153`), each entry by name, description, version, what is installed of it and what the stack does without it, and installing one MUST go through the install reading of `G11-R1` and `G11-R26`. Where reaching the catalogue is switched off it MUST say so with the setting that switches it on; where the read is `failed` it MUST show the stack's sentence and no entry (`ARCH-R452`). |
| **G11-R28** | Minting a key MUST offer handing it to a program as a claim (`C10-R20`): the console MUST show the claim link once, as text and as a scannable code, with when it lapses, and MUST NOT show the key's secret. |
| **G11-R29** | The console MUST list each phone's hardware key from `GET /api/device-keys` (`ARCH-R259`) by name, app, fingerprint, backing, when it was registered and when it was last used, and MUST revoke one with `DELETE /api/device-keys/{name}` only on a yes naming the phone. |
| **G11-R30** | The console MUST list each phone that can be woken from `GET /api/push-endpoints` (`ARCH-R282`) by name, the `host` and `fingerprint` the listing carries for its address and when it was registered, and MUST remove one with `DELETE /api/push-endpoints/{name}` only on a yes naming it. It MUST NOT show the whole address. |
| **G11-R31** | The update reading MUST offer moving one service alone (`update` with `service`, `E1-R13`), read before the yes as the whole update is, with what stopping that service would interrupt as `G11-R10` reads it for `services` naming it. |
| **G11-R32** | The backups panel MUST offer backing up one service alone (`backup` with `service`, `G1-R1`). |
| **G11-R33** | Beside each service that runs and exits, the console MUST offer running it now (`run`, `ARCH-R438`), rehearsed first, showing whether a run was due and what held it back, and run only on a yes. |
| **G11-R34** | A record whose work ended before it finished MUST say whether its name was released or the work was let go, told apart from work that finished, failed or is still running (`ARCH-R132`). Putting away the record of work still running MUST forget its name with `POST /api/jobs/{job}/forget` (`ARCH-R464`), never release it, and the record MUST say that the work runs on. |
| **G11-R35** | The console MUST read `GET /api/capabilities` once per session (`ARCH-R78`). A panel whose read the credential cannot use MUST be drawn silenced with one sentence saying why, and a single control it cannot use MUST NOT be drawn. The console MUST NOT decide either from a version number. |
| **G11-R36** | What `G11-R24` to `G11-R35` show MUST be shown to the operator alone and MUST NOT appear anywhere a member is shown (`G10-R9`). |

## Notes

**The same promises as the companion's.** G11-R1 to G11-R4 say for the web
console what `N25-R21` to `N25-R24` say for the app, and G11-R5 what `N9-R12`
says for its credentials screen, so an operator meets one consent wherever they
are. G11-R6 and G11-R7 say for the web console what `N6-R4` says for the app's
running copy, and G11-R8 what `N4-R28` says for its health screen. G11-R10 says for the web console what `N2-R42`
says for the app, and G11-R11 extends it to the restart and the switch, which the console offers and which take no
`wait`.

| Row | What the web API carries | Not carried |
|---|---|---|
| `G11-R1` | `install.would.granted[]`: `credential`, `of`, `for`; the same under `update.install`; `PLUGIN-46` where a crossing secret names no capability | The line the yes approves for each grant: a pair and a privileged shape carry their `approval`, and a grant carries none |
| `G11-R2` | `installed[].granted[]`: `credential`, `of`, `for`, `at` | — |
| `G11-R3` | `credentials-revoke` with `plugin` and `credential`; `revoked`: `agreement`, `ended`, `grant`, `restarts`, `unrestarted`; `PLUGIN-47` where no such grant is held | — |
| `G11-R5` | `grants[]`: `plugin`, `credential`, `of`, `for`, `at` | — |
| `G11-R6` | `copying.running`: `what`, `written`, `whole`, `part`; the `copying` event | — |
| `G11-R7` | `copying.running.state`: `working`, `paced` with `limit`, `stalled` with `wrote` | — |
| `G11-R8` | the `replay` event: `alerts`, `whole` or `partial` | — |
| `G11-R10` | `in-flight.downloads[]`: `name`, `progress`, `protocol`; `wait` on `down`, `update`, `uninstall` and `config-set` | — |
| `G11-R11` | `in-flight` as for `G11-R10` | `wait` on `restart` and `switch` |
| `G11-R12` | `served`: `port`, `encrypted`, `network`, `named`, `unrecorded`; `certificate`: `fingerprint`, `subject`, `subject_cut`, `issuer`, `issuer_cut`, `self_signed`, `names`, `names_more`, `valid_from`, `valid_until` | — |
| `G11-R13` | `served.encrypted`, `served.network` | — |
| `G11-R14` | `stack`: `source`, `project`, `env`, `plain_up`, `non_interactive`, `exceptions[]` | — |
| `G11-R15` | `settled`: `data_root`, `protocols`, `service_user` with `from`, `setup` | — |
| `G11-R16` | `config.decisions[]`: `key`, `cost`, `affects`, `held`, `credential`, `setting`; `config.unmanaged[]`: `area`, `area_cut`, `why`, `why_cut`, `covers[]`, `covers_more`; `unmanaged_more` | — |
| `G11-R17` | `boot`: `booted_at`, `verified`, `last_verified`, `declined`, `failing_since`, `failed_boots` | — |
| `G11-R18` | `watcher`: `watcher`, `reachable`, `unreachable_because`, `read_at`, `monitors[]`, `uncovered[]` | — |
| `G11-R19` | `queue`: `healing`, `strikes_needed`, `grace_s`, `items[]`, `unreachable[]`, `mismatch`, `incomplete`, `classified_at`, `runs[]` | — |
| `G11-R20` | `notify`: `state`, `backends[]`, `unread[]` | — |
| `G11-R21` | `quality.offered`: `presets`, `formats`, `media_types`; `quality-set` with `preset`, `media_type`, `confirm` and `dry_run`; `disposition` `held` | — |
| `G11-R22` | `quality-reapply` with `dry_run`; `quality.overwritten`: `path`, `diff` | — |
| `G11-R24` | `plugin-prove` with `plugin`, `dry_run` and `offer` | — |
| `G11-R25` | `plugin-run` with `plugin`, `recipe`, `inputs`, `dry_run`, `offer` and `approved` | — |
| `G11-R26` | `inputs` on `plugin-install`, `plugin-update` and `plugin-run` | — |
| `G11-R27` | `plugin-catalogue`: `state` (`listed`, `off`, `failed`), `entries[]`: `id`, `name`, `description`, `version`, `installed`, `without_it`; `setting`, `failure` | — |
| `G11-R28` | `POST /api/keys` with `claim`; `key-claim`: `name`, `scope`, `purpose`, `link`, `lapses` | — |
| `G11-R29` | `device-keys.keys[]`: `name`, `app`, `fingerprint`, `backing`, `registered`, `used`, `revoked` | — |
| `G11-R30` | `push-endpoints.endpoints[]`: `name`, `host`, `fingerprint`, `registered` | the whole address |
| `G11-R31` | `update` with `service` | — |
| `G11-R32` | `backup` with `service` | — |
| `G11-R33` | `run` with `service` and `dry_run`; `ran`: `service`, `due`, `held`, `ran`, `skipped` | — |
| `G11-R34` | `ended`: `job`, `action`, `ended` (`released`, `let-go`, `quiet`); `POST /api/jobs/{job}/forget` | — |
| `G11-R35` | `capabilities`: each path with `available`, `unconfigured` or `unpermitted`; `scope` | — |

## Related

- [G1](g1-interface-tiers.md) — every action from every surface
- [G10](g10-household-web.md) — the household's side of the same surface
- [F14](../f-extensibility/f14-every-part-is-a-plugin.md) — a third-party plugin's grant
- [A7](../a-getting-started/a7-credential-management.md) — the credentials the stack holds
- [N25](../n-companion/n25-a-plugin-after-it-lands.md) and [N9](../n-companion/n9-who-gets-in.md) — the same grants on the companion
- [E3](../e-maintenance/e3-backup-restore.md) — a backup or restore and the reading of one running
- [N6](../n-companion/n6-taking-a-copy.md) and [N4](../n-companion/n4-native-integration.md) — a running copy and alerts that may be missing, on the companion
- [N2](../n-companion/n2-operator-companion.md) — what a stop would interrupt, on the companion
- [A6](../a-getting-started/a6-uninstall.md) — downloads in flight, with an option to wait
- [F1](../f-extensibility/f1-customisation.md), [A2](../a-getting-started/a2-setup-wizard.md) and [A4](../a-getting-started/a4-reconfiguration.md) — running without lemonfiber, what setup settled, the choices it made
- [B8](../b-running/b8-autostart.md), [K2](../k-observability/k2-uptime.md), [H5](../h-glue/h5-queue-selfheal.md), [D9](../d-content/d9-pipeline-trace.md) and [B9](../b-running/b9-notification-backends.md) — the machine's health
- [D2](../d-content/d2-quality-presets.md) — quality presets
- [F5](../f-extensibility/f5-plugin-catalogue.md), [F7](../f-extensibility/f7-plugin-provenance.md) and [F8](../f-extensibility/f8-recipes.md) — the catalogue, proving a plugin and its recipes
- [C10](../c-trust/c10-integration-keys.md) — keys, their claims and phones' hardware keys
- [E1](../e-maintenance/e1-stack-updates.md) — updating one service
