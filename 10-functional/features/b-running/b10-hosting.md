---
id: B10
title: Hosting long-running commands
kind: feature
area: B
audience: operator
status: accepted
tracks: v1
labels: [cli, storage, household]
requires: [C5, D7, G4]
relates: [B2, B5, B8, G1]
---

# B10 — Hosting long-running commands

**Status:** Accepted · **Audience:** Operator · **Area:** B — Running it

---

## Purpose

Two of lemonfiber's guarantees are made by a command that has to keep running,
and both of them currently end when a terminal window closes.

The data-location guard ([C5](../c-trust/c5-storage.md)) stops the stack if the
volume it writes to disappears. The request clock ([D7](../d-content/d7-approval-quotas.md))
closes requests nobody ruled on after the period the household agreed to, and
tells the requester why. Neither is a command somebody sits and watches: the
first is worth having precisely on the day nobody is at the machine, and the
second is measured in days. Both are started in a shell, and both die with it —
along with a laptop lid, an SSH session, or a terminal closed by somebody
tidying up.

The failure is not that they stop. It is that stopping is invisible. An operator
who started a guard believes the guard is there; a household told its requests
close after thirty days believes something is closing them. Nothing says
otherwise until the day it mattered.

**This is not [B8](b8-autostart.md).** B8 brings the *stack* back after a
reboot — Docker Desktop at login, container restart policies, the VPN tunnel and
its forwarded port. Every one of its requirements is about containers somebody
else runs. It hosts nothing of lemonfiber's own, so building all of it would
leave both of these commands exactly as they are. The two features share a
standard — what is installed must be verifiable and must come back out cleanly —
and share no mechanism, no subject and no failure mode.

## Behaviour

### A long-running command can be handed to the machine

The operator asks for it once, by name, and the operating system's own service
manager runs it from then on: after the terminal is closed, and after the
machine is restarted. What is installed is lemonfiber running the same command
the operator would have typed.

### The platform's own mechanism, or an honest refusal

| Platform | What lemonfiber does |
|----------|----------------------|
| **macOS** | Installs a launch agent in the operator's own login session |
| **Linux** | Installs a user service in the operator's own session |
| **Anything else** | Says it cannot configure this platform, and says what to do instead |

Both of the supported forms belong to the operator's account. Neither needs
administrative rights, and neither installs anything another user of the machine
inherits. A media stack on a home machine that demanded root to keep a clock
running would be a worse product than the terminal it replaces.

Where the platform is one lemonfiber does not configure, it says so and gives
instructions. It never reports an installation it did not make.

### Installing is an act of its own

It is asked for, never arrived at. Running the long command does not offer to
install it, and no other command installs it as a side effect. An operator who
asked to guard a volume this afternoon has not thereby asked for something on
their machine that starts at every login.

### What it does at install time, it says

Installing also starts the command, because an installation that took effect at
the next login would be an installation the operator could not tell from a
failure. That it started is reported, along with where the command's words are
being written, since a command with no terminal has nowhere to say them.

### Installed is not running

The state that matters is whether the service manager is actually running the
command — not whether a file was written. Where the platform will not say,
lemonfiber says it does not know rather than treating a written file as a
running command.

### It ends where it means to, and stays ended

Both hosted commands end for reasons the operator has to hear about. The guard
returns the moment the data location is lost — that is its whole contract. The
clock stops when the arrangement it was closing requests under is withdrawn or
replaced. A service manager told to restart them would restart them past the
reason, forever, against a volume that is still missing or an arrangement
nobody agreed to. So neither is restarted automatically, and what ended is
readable afterwards.

### Removal leaves nothing

Removing takes back everything the installation made: the service definition,
its registration with the manager, and its entry in the operator's login items.
The standard is [B8-R11](b8-autostart.md)'s and it is the right one here — a
thing that is hard to remove is a thing an operator will not risk installing.

### What depends on it says whether it is hosted

The reminder that names an expiry period today says, in the same sentence, that
nothing runs the clock for the operator. Once something does, it says that
instead. A guarantee that reads as continuous while nothing is running it is the
whole failure this feature exists to remove, and it would survive the feature
being built if the words did not move with it.

## States

Per hosted command:

| State | Meaning |
|-------|---------|
| `not-hosted` | Nothing is installed; the command runs only while a terminal holds it |
| `hosted` | Installed, and the platform confirms it is running |
| `installed-unverified` | Installed, and the platform would not say whether it is running |
| `stopped` | Installed, and the platform says it is not running |
| `orphaned` | Installed, and the program it names is no longer there |
| `unsupported` | This platform has no service manager lemonfiber configures |

`installed-unverified` is the important one, for the same reason
[B8-R4](b8-autostart.md)'s is: it is the state where the operator believes a
guarantee is being kept and it is not.

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Platform lemonfiber cannot configure | Report it, and instruct. Never report an install. |
| The service manager refuses the definition | Report the manager's own words, and remove the definition that was written. A failed install leaves nothing behind either. |
| The same command is installed twice | Replace what is there. Never two services closing the same requests. |
| Removing something that was never installed | Say so and succeed. Removal is asked for by somebody who wants it gone, and it is gone. |
| Removing while it is running | Stop it first, and say that it was stopped. |
| lemonfiber updated itself and moved | The service names a program that is no longer there. Report it as orphaned rather than leaving a service that fails at every login. |
| A Linux session that does not survive logout | A user service runs while the operator is logged in. Surviving a logout is a setting on the account, and lemonfiber says so rather than enabling it silently or claiming what it has not got. |
| The hosted command ends on its own | Leave it ended, and make the ending readable. |
| The arrangement a hosted clock runs under is withdrawn | The clock stops itself, as it does in a terminal. The service stays installed and reads as stopped. |
| The data location is lost while the guard is hosted | The guard stops the forms and returns, as it does in a terminal. It is not restarted against a volume that is still missing. |
| Two forms of the same command wanted | One service per command. Installing again replaces what the last install asked for rather than adding to it. |
| This machine will not say where it keeps its own files | Refuse by name. A service installed into a guessed directory is one nothing can find to remove. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **B10-R1** | A long-running lemonfiber command MUST be installable as a service the operating system runs, and MUST continue after the terminal that installed it is closed. |
| **B10-R2** | Every long-running command MUST be installable this way; the mechanism MUST NOT be particular to one of them. |
| **B10-R3** | lemonfiber MUST use the service manager belonging to the platform it is running on. |
| **B10-R4** | Where the platform has no service manager lemonfiber configures, it MUST say so and MUST instruct, and MUST NOT report an installation it did not make. |
| **B10-R5** | Installing MUST NOT require administrative rights, and MUST NOT install anything outside the operator's own account. |
| **B10-R6** | Installing MUST be an act of its own, and MUST NOT be a side effect of running the command or of any other command. |
| **B10-R7** | Installing MUST state whether the command is now running, and MUST NOT start anything without saying so. |
| **B10-R8** | An installation whose running state cannot be confirmed MUST be reported as `installed-unverified`, and MUST NOT be reported as running. |
| **B10-R9** | What is hosted MUST be readable — which commands are installed, what each runs, and whether the platform is running it now. |
| **B10-R10** | Removing MUST take back everything the installation made, leaving no orphaned service definition, registration or login item. |
| **B10-R11** | Removing what is not installed MUST report that and MUST NOT fail. |
| **B10-R12** | Installing a command that is already hosted MUST NOT leave two services for it. |
| **B10-R13** | A hosted command's words MUST be written where the operator can read them, and installing MUST say where. |
| **B10-R14** | A hosted command that ends MUST NOT be restarted automatically, and its ending MUST be readable. |
| **B10-R15** | A hosted service whose program is no longer present MUST be reported, and MUST NOT be reported as hosting anything. |
| **B10-R16** | Where a guarantee depends on a long-running command, what the operator and the household are told MUST say whether that command is hosted, and MUST NOT describe as continuous what nothing is running. |

## Related

- [B8 Autostart & boot persistence](b8-autostart.md) — the stack coming back, which this is not
- [B2 Lifecycle control](b2-lifecycle.md) — what a hosted guard stops
- [C5 Storage & hardlink management](../c-trust/c5-storage.md) — the guard on the data location
- [D7 Request approval & quotas](../d-content/d7-approval-quotas.md) — the clock that closes long-pending requests
- [G1 Interface tiers](../g-ux/g1-interface-tiers.md) — which surfaces this reaches
- [G4 Error & remedy model](../g-ux/g4-error-model.md) — how a refusal is worded
