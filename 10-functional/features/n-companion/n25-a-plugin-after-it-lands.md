---
id: N25
title: A plugin after it lands
kind: feature
area: N
audience: operator
status: accepted
maturity: built
priority: P3
labels: [mobile, extensibility, ux]
requires: [N1, N5, F5, F6]
relates: [N6, N11, N20, F14]
---

# N25 — A plugin after it lands

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

[N5](n5-connecting-the-stack.md) makes installing a plugin a companion act: the
catalogue, what vouches for a plugin, an install in progress, a refused one.
[N20](n20-what-a-plugin-may-send.md) keeps what a plugin would send off the
machine apart from the install that wants it. Neither says what happens next.

[F6](../f-extensibility/f6-plugin-lifecycle.md) does: an install is rehearsed
before it is written, verified after, and reversed if either fails; an update is
one account and one reversal; a removal is a rollback with a name on it.
[F5](../f-extensibility/f5-plugin-catalogue.md) adds that where a plugin came
from, and whether anybody read it, stays with it for as long as it is installed.
This page is those acts, and that record, from here.

## Behaviour

### A rehearsal says everything the install would do, and asks nothing

Before anything is written, the stack says every change the install makes, in
order and in full paths; every proof it would ask; every bundled setting it
declares it will change; and every capability it would leave contested. The app
shows all four. A rehearsal that showed less than the real run would be a preview
of a different install.

A rehearsal asked no proof, and a proof nobody asked is not a proof that passed.
The app never shows the first as the second.

### A privileged shape is approved on its own

A plugin that fronts an egress guard takes a privileged shape: a service of it is
granted network administration and given the tunnel device, which no other
plugin's service may have (`F14-R12`). A media server takes another, the host's
render device for hardware transcoding (`ARCH-R237`). Where an install or update
would give a service either, the rehearsal names each service that takes a shape,
with the capabilities it is granted and the devices it is given. The operator
approves each one apart from the offer, and agreeing to the offer approves none of
them (`F14-R21`). A service
left unapproved leaves the install refused, and the app says which service it
was and why it needs the shape.

An adapter whose upstream is configured only through its own files is handed that
service's whole configuration directory, and writes those files (`ARCH-R339`). It
asks no approval of its own, but it is a write into another service's
configuration, so the rehearsal of an install or update names each adapter that
does, the service whose files it writes, and where that service's directory lands
inside it.

### A plugin's settings are the operator's to change

A plugin's services can read values the operator sets: the countries an egress
guard may exit from, the domain the proxy answers on. The app lists them on the
plugin, each with the services that read it, its default, and the operator's
value where there is one, read from the stack's settings (`ARCH-R254`). Changing
one is rehearsed first and says which services restart for it; agreeing sends the
offer that rehearsal answered (`ARCH-R255`). Putting a setting back to its
default is the same act.

Secrets are listed beside the settings and never shown: each says whether a value
is held and where it came from, and nothing more. The app offers no way to change
one, and says that a secret is changed at the stack's terminal (`ARCH-R256`).
These screens are the operator's alone; a member never sees them.

A setting or a secret that no installed plugin's services read is the stack's
own: the core's, or a namespace's that no plugin brought. The app lists those on
a screen of the stack's, beside what the stack is set to, grouped as the core's
or by the namespace that owns each, and offers changing them and putting them
back exactly as it does on a plugin. Without it, a value the stack itself reads
could be changed from the command line and the web API but not from the
app (`ARCH-R248`).

A setting whose services accept only some values lists them as its choices, and
a value can be a choice only while other settings hold what it needs: a region
a VPN provider serves, a type a provider offers (`ARCH-R348`). Such a setting is
changed by choosing. Every value is shown, a value that is not a choice now with
what it needs, and nothing outside the choices is sent; the stack would refuse
it (`ARCH-R350`). Which values go together is the stack's to say, and the app
holds no rule of its own about it.

Settings that depend on each other are changed together. One change can move
several settings, and its rehearsal shows each one with what it holds, what it
will hold and what moving it costs, and the services the change restarts, starts
and leaves waiting. A change the stack refuses because it would leave another
setting outside its choices offers that setting in the same change, so the
operator is never left with two changes each refused for want of the other.

A service the stack holds back until the operator gives it something is waiting,
not broken (`ARCH-R351`). Services shows it apart from those that run, stopped or
failed, with everything it waits for: a setting with its choices, a secret by
name, the service it runs through. A setting it waits for is changed from there,
and the rehearsal says which services the change would start; a secret it waits
for is entered at the stack's terminal, as every secret is. The rehearsal of an
install or an update names each service it would leave waiting before the yes.
None of this names a value, and none of it is shown to a member.

Where a plugin brings the egress guard, the core asks the guard to take up the
control credential its adapter was handed once the plugin is installed or
updated (`ARCH-R357`). What that came to, where it was more than held at once,
is part of the account after the yes: the guard restarted to take it up, or why
it did not.

| Where | English | Dutch |
|-------|---------|-------|
| The section on a plugin | Settings | Instellingen |
| A setting left as it came | Default | Standaard |
| A setting the operator changed | Set by you | Door jou ingesteld |
| Putting it back | Back to default | Terug naar standaard |
| Before a change is agreed | Changing this restarts {services}. | Dit wijzigen herstart {services}. |
| A secret that is held | Saved, never shown | Opgeslagen, nooit getoond |
| A secret with no value | Not set yet | Nog niet ingesteld |
| Why a secret cannot be changed here | Secrets are changed at the stack's terminal. | Geheimen wijzig je in de terminal van de stack. |
| The group of services held back | Waiting for you | Wacht op jou |
| A value that is not a choice now | Needs {setting}: {values} | Vraagt {setting}: {values} |

### Installed means proven and verified, and a failure says what went back

An install is finished when its proofs held and the stack's own checks found
nothing it made worse. Where either failed, the stack puts it back and says what
went back and what did not, with the reason each is still standing. The app
shows that account as it came. *Could not tell* is not *broke*, and a check the
stack could conclude nothing about is shown as that rather than as a failure.

### An update is one thing, with one answer

Moving a plugin from one version to another is rehearsed as one account and put
back as one unit. The app shows both versions, every service that stops for it —
named before any of them does — and, where the new version did not hold, what
putting the old one back came to. The stack is never shown between the two.

### A removal says what it stops and what it leaves unfilled, before it happens

Taking a plugin out stops its services and can leave something asking for a
capability nothing then fills. Both are said before the removal is agreed to.
Afterwards, what was put back and what was not are shown, because a removal that
got as far as the files and no further is a different machine from one that
finished.

### A recipe the plugin offers on demand is run from the plugin

A plugin can declare recipes that run only when asked for by name. Each installed
plugin lists its demand recipes with the title and the reason the manifest gives, and
offers running each one. Running is rehearsed first and labelled a rehearsal: every step
in the order the recipe gives, each adapter named as lemonfiber's, and each pair it would
carry, with the value's name, where it comes from and the destination by the name the
manifest gave ([N20](n20-what-a-plugin-may-send.md)). A pair that leaves the machine, or
releases a value a service answered with, is agreed to as itself, apart from the run and
with none agreed for the operator; an approval given at install covers no run, and each
run asks again.

Agreed, the app sends the run with the offer its rehearsal named and the pairs approved,
follows the job, and shows what ran step by step, a step the stack held with its reason.
An offer that moved since the rehearsal is rehearsed and shown again, and nothing runs
until the operator agrees to the new one.

A recipe that asks the operator for a value is not run from the app. It is listed with
what it asks for, and the app says it is run at the web console or the terminal: a value
a recipe asks for may be a secret, and the app takes no such value for an install, an
update or a run.

### Where it came from, and whether anybody read it, stays on it

Every installed plugin carries the source the operator named, its version, and
whether anybody reviewed it. *Unreviewed* is not a banner at install time; it is
part of the plugin for as long as the plugin is here, and the app shows it on
every appearance.

## States

| State | Meaning |
|-------|---------|
| Rehearsed | What an install, update, removal or recipe run would do. Nothing written, no proof asked. |
| Installed | Proofs held and the stack's checks found nothing made worse. |
| Put back | Something failed; what went back and what did not are shown. |
| Updating | Between asking and the answer. Never shown as either version. |
| Removed | The record no longer holds it, and its changes went back. |
| Partly removed | Files put back and the record not written. |
| Unknown | The plugin record could not be read. Never shown as none installed. |

## Edge cases

- **A plugin installed from a source that has since gone.** It keeps working
  (`F5-R11`), and is shown with the source it was installed from.
- **An install that would contest a capability the bundled stack fills.** The
  contest is shown in the rehearsal, and answering it is `N5`'s.
- **A plugin whose shape the operator does not approve.** The install is refused,
  not run without the shape, and the service is named.
- **A setting changed on another surface while the app shows it.** The `settings`
  event brings the new value, and a change agreed to against the old one is
  refused as an offer that moved.
- **A change that would strand another setting.** Refused by the stack naming that
  setting; the app offers it in the same change rather than a second one.
- **A service waiting on a service that waits.** Both are shown waiting, the first
  naming the second, and giving the second what it needs starts both.
- **A demand recipe that asks for a value.** Listed with what it asks for and where it
  is run; not offered here.
- **A run whose offer moved.** Rehearsed and shown again; nothing runs on the old one.
- **A reversal that could not finish.** What is still standing is named with its
  reason; the install is not shown as undone.
- **A plugin whose configuration directory still holds what its service wrote
  after an update went back.** Named as still standing.

## Requirements

| ID | Requirement |
|----|-------------|
| **N25-R1** | The app MUST offer rehearsing a plugin install, and the rehearsal MUST show every change in order with its full path, every proof, every bundled setting the plugin declares it will change, and every capability it would leave contested (`F6-R1`). |
| **N25-R2** | A proof that was not asked MUST NOT be shown as passed, and a check the stack could conclude nothing about MUST NOT be shown as failed. |
| **N25-R3** | An install MUST NOT be shown as installed until its proofs held and the stack's own checks found nothing it made worse (`F6-R3`, `F6-R4`, `N5-R11`). |
| **N25-R4** | Where an install was put back, the app MUST show what went back and what did not, with the reason each is still standing, and MUST NOT present a partial reversal as complete (`F6-R5`, `F6-R6`, `N6-R6`). |
| **N25-R5** | The app MUST offer updating a plugin, and MUST show the version it moves from and to and every service that stops for it before it is agreed to; where the update did not hold, it MUST show what putting the previous version back came to (`F6-R8`, `F6-R9`). |
| **N25-R6** | The app MUST offer removing a plugin, and MUST show every service it stops and every capability it would leave unfilled before the removal is agreed to (`F6-R8`, `F6-R11`). |
| **N25-R7** | A removal that put the files back without writing the record MUST be shown as partial, and MUST NOT be shown as removed (`F6-R7`). |
| **N25-R8** | Every installed plugin MUST be shown with the source it was installed from, its version and whether it was reviewed, and an unreviewed plugin MUST be shown as unreviewed wherever it appears (`F5-R5`, `F5-R7`). |
| **N25-R9** | A rehearsed install, update or removal MUST be labelled as a rehearsal (`N6-R1`). |
| **N25-R10** | A plugin record that could not be read MUST be told apart from there being no plugins installed. |
| **N25-R11** | Where an install or update states `taking[]`, the rehearsal MUST show each service that takes a privileged shape, the egress guard's or `render`, with the capabilities it is granted and the devices it is given; the operator MUST approve each one apart from the offer, agreeing to the offer MUST approve none of them, and the agreement MUST send `<shape>@<service>` in `approved` for exactly the services approved. A service not approved MUST leave the install refused, and the app MUST say which service was not approved and why it needs the shape (`F14-R12`, `F14-R21`, `ARCH-R238`). |
| **N25-R12** | The app MUST list, on each installed plugin, every setting its services read, with the services that read it, its default and the operator's value where one is recorded, and MUST offer changing it and putting it back to its default, each rehearsed with the services it restarts and agreed to by the offer that rehearsal answered (`ARCH-R254`, `ARCH-R255`). |
| **N25-R13** | The app MUST list each secret a plugin's services read with whether a value is held and where it came from, MUST NOT show or offer to change a secret's value, and MUST say a secret is changed at the stack's terminal (`ARCH-R256`). |
| **N25-R14** | A plugin's settings and secrets MUST be shown to the operator alone and MUST NOT appear anywhere a member is shown. |
| **N25-R15** | Where the stack holds answers a plugin gave outside its contract, the app MUST offer proving the plugin again, and before asking MUST show what the proof would ask and which capability a pass would clear. The yes MUST carry back the offer the stack named (`N2-R27`). A proof that fails MUST leave that capability shown as unfilled with the stack's reason, and MUST NOT be presented as passed (`N25-R2`). |
| **N25-R16** | Each installed plugin MUST list its demand recipes with the title and reason the manifest gives, and MUST offer running each one that asks the operator for no value (`N1-R2`). |
| **N25-R17** | Running a demand recipe MUST be rehearsed first and the rehearsal labelled a rehearsal (`N6-R1`), showing every step in the order the recipe gives, each adapter as lemonfiber's, and each pair it would carry with the value's name, where it comes from and the destination by the manifest's name (`N20-R3`, `N20-R5`, `N20-R6`). |
| **N25-R18** | A pair a run would carry out of the machine, or that releases a value a service answered with, MUST be agreed to as itself, apart from the run and with none agreed for the operator, and an approval given at install MUST NOT be taken as an approval of a run (`N20-R1`, `N20-R2`); the run MUST send the offer its rehearsal named and exactly the pairs approved, and an offer that moved MUST be rehearsed and shown again with nothing run. |
| **N25-R19** | A run MUST be followed to its end and MUST show what ran, step by step, with each step the stack held and the stack's reason, and MUST NOT be shown as having run where a step was held. |
| **N25-R20** | A demand recipe that asks the operator for a value MUST NOT be run from the app; it MUST be listed with what it asks for, and the app MUST say it is run at the web console or the terminal. This is the exception to `N1-R2` for runs: the value may be a secret, and the app takes no value a recipe asks for. |
| **N25-R21** | Where an install or update of a third-party plugin names a credential of another service that would cross to it, the rehearsal MUST show each one with the setting it is held under, the service whose credential it is and the capability of the plugin's own it is for, and never its value. The operator MUST approve each one apart from the offer, on a switch of its own that is off until turned on; agreeing to the offer MUST approve none of them, and the yes MUST carry each approved one exactly as the reading names it (`ARCH-R323`, `F14-R20`). Every update MUST ask again, and a grant the plugin already holds MUST NOT be taken as approved. Where the stack refuses the act for a grant left off, the refusal MUST be drawn in the stack's words. |
| **N25-R22** | Each installed plugin MUST list the grants it holds, each with the setting the credential is held under, the service whose credential it is, the capability it fills and when it was approved, and never a value (`ARCH-R323`). |
| **N25-R23** | The app MUST offer revoking each grant a plugin holds. The revoke MUST be read first, labelled as nothing ended yet (`N6-R1`), showing the grant it ends and the plugin's services it would restart; the yes MUST carry back the offer the stack named (`N2-R27`). Afterwards the app MUST show whether the grant was ended, the services that restarted and, where they did not, the stack's reason, and MUST say that the plugin stays installed and that rotating the credential is what takes back a value already handed (`ARCH-R324`). |
| **N25-R24** | A plugin's grants, and revoking them, MUST be shown to the operator alone and MUST NOT appear anywhere a member is shown. |
| **N25-R25** | The app MUST list, on a screen of the stack's own, every setting and secret in the stack's stores that no installed plugin's services read, grouped as the core's or by the namespace that owns it. It MUST show and offer changing each setting as `N25-R12` says, list each secret as `N25-R13` says, and show all of it to the operator alone as `N25-R14` says (`ARCH-R248`). |
| **N25-R26** | Where an install or update states `sharing`, the rehearsal MUST name each adapter that writes the files of the service it fronts, that service, and where that service's configuration directory lands inside the adapter (`ARCH-R339`). |
| **N25-R27** | A setting the stack lists with choices MUST be changed by choosing one of them. The app MUST show every value, each value that is not a choice now with the settings and values it needs, and MUST NOT send a value outside the choices (`ARCH-R348`, `ARCH-R350`, `ARCH-R352`). |
| **N25-R28** | A change MUST be able to move several settings in one act. Its rehearsal MUST show each setting moved with what it holds, what it will hold and what moving it costs, and the services it restarts, starts and leaves waiting. A refusal naming another setting MUST offer that setting in the same change (`ARCH-R350`). |
| **N25-R29** | Each service the stack holds back MUST be shown with every setting and secret it waits for, and the service it runs through, never by value. A setting MUST be shown with its choices where it has them. Such a service MUST NOT be shown as stopped, failed or missing (`ARCH-R351`, `ARCH-R352`). |
| **N25-R30** | A setting a held-back service waits for MUST be offered as a change from where the service is shown. A secret it waits for MUST be said to be entered at the stack's terminal (`N25-R13`). |
| **N25-R31** | The rehearsal of an install or an update MUST name each service it would leave held back, with what it waits for (`ARCH-R351`). |
| **N25-R32** | The account of an install or an update after the yes MUST say what asking its egress guard to take up its control credential came to, in the stack's words, wherever the stack says (`ARCH-R357`). |

## Notes

**None of this can be answered while nothing serves it.** The `plugins`
envelope is published and generated into the SDK, and no HTTP route produces it:
the action route accepts no plugin verb, and the read table serves no plugin read
([the register](../../../90-appendix/what-the-companion-does-not-read.md) records
this). `N5-R10` and `N5-R11` wait on the same read. The rows stand as written,
because the envelope already describes what they need.

The core's side is required and scheduled. `F6-R14` requires what is installed
to be a read of the web API, `F6-R15` requires installing, updating and removing
to be actions of it, and `F6-R16` requires each to be rehearsable there; `0.18.0`
locks all three. `F6-R14` also requires a record that cannot be read to be refused
rather than answered with an empty list, which is the distinction `N25-R10` asks
for and the envelope alone does not carry.

| Row | What `plugins` carries | Not carried |
|---|---|---|
| `N25-R1` | `install.changes` (`path`, `puts`), `install.proofs`, `install.overrides`, `install.contests` | — |
| `N25-R2` | `proofs[].came_to`, absent where nothing was asked; `verified.broke` and `verified.unsettled` apart | — |
| `N25-R3` | `install.recorded`, `install.proofs[].came_to`, `install.verified` | — |
| `N25-R4` | `install.reversed`: `reversed`, `left` with `because`, `noted` | — |
| `N25-R5` | `update`: `from`, `to`, `interrupts`, `install`, `stopped`, `restored`, `went_back` | — |
| `N25-R6` | `removal`: `interrupts`, `leaves` | — |
| `N25-R7` | `removal.removed` and `removal.went_back`, apart | — |
| `N25-R8` | `installed[]`: `from`, `version`, `declared.reviewed`, `declared.upstream` | The revision the source was at and what signed it (`F5-R7`). Whether an origin can still be fetched (`F5-R11`) |
| `N25-R9` | `install.recorded`, `removal.removed`, and `proofs[].came_to` absent on a rehearsal | A single flag saying a run was a rehearsal |
| `N25-R10` | — | Whether the record was read: `installed` is a list, and an empty one is the only answer the envelope gives |
| `N25-R11` | `install.taking[]`: `service`, `shape`, `grants`, `devices`, `approval`; the same under `update.install`; `PLUGIN-26` where an approval is missing | — |
| `N25-R21` | `install.would.granted[]`: `credential`, `of`, `for`; the same under `update.install`; `PLUGIN-46` where a crossing secret names no capability | The line the yes approves for each grant: a pair and a privileged shape carry their `approval`, and a grant carries none |
| `N25-R22` | `installed[].granted[]`: `credential`, `of`, `for`, `at` | — |
| `N25-R23` | `credentials-revoke` with `plugin` and `credential`; `revoked`: `agreement`, `ended`, `grant`, `restarts`, `unrestarted`; `PLUGIN-47` where no such grant is held | — |
| `N25-R31` | `install.waiting[]`: `service`, `wants` (a `setting` with its `choices`, a `secret`, a `service`); the same under `update.install` | — |
| `N25-R32` | `install.secured`, absent where the guard held the credential at once, where no service is a guard and on every rehearsal; the same under `update.install` | — |

## Related

- [N1](n1-companion-app.md) — parity, and what the app may claim
- [N5](n5-connecting-the-stack.md) — the catalogue, and installing
- [N20](n20-what-a-plugin-may-send.md) — what a plugin may send, and may never run
- [N6](n6-taking-a-copy.md) — what a reversal owes, and a rehearsal's label
- [N11](n11-the-record.md) — the record every change is journalled in
- [F5](../f-extensibility/f5-plugin-catalogue.md) — the catalogue and what vouches for a plugin
- [F6](../f-extensibility/f6-plugin-lifecycle.md) — the plugin lifecycle
- [F14](../f-extensibility/f14-every-part-is-a-plugin.md) — the one privileged shape, and approving it
