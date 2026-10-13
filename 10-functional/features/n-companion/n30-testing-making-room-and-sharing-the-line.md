---
id: N30
title: Testing, making room and sharing the line
kind: feature
area: N
audience: operator
status: accepted
maturity: building
priority: P2
labels: [mobile, verification, storage, network]
requires: [N1, N2, C1, D5, D10]
relates: [N10, N12, N6, C2, B2]
---

# N30 — Testing, making room and sharing the line

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Three things the operator can do at the machine the phone only reads: run a check that
disturbs something to find out whether it works, give back the room the stack says costs
nothing, and change how the stack shares the line. Each has a screen in the app already —
Health, Storage and Bandwidth — that ends with *done at the machine*. This page puts the
doing on those screens, on the terms the core already sets for each (`N1-R2`).

## Behaviour

### A check that disturbs is run from the finding that needs it

A check the stack leaves unverified because running it disturbs something — the VPN
killswitch test takes the tunnel down, a live release search spends an indexer's daily
query — is a finding on Health, saying so. That finding carries the way to run it: the
check or group to run, what it disturbs and for how long the stack bounds it, all as the
stack reported them (`ARCH-R288`). The app reads them; it never estimates a duration
(`N2-R8`).

Pressed, it asks first: what will be disturbed, for up to how long, and, where the stack
reports transfers moving, that those are interrupted. Agreed, the app sends `diagnose`
narrowed to that check, follows the job, and draws the finding again with the verdict the
run came to and when it ran. A run is never rehearsed: the check *is* the disturbance, and
the core refuses a rehearsal of one.

### Room the stack says costs nothing is given back by category

Storage already lists what is using the disk and what could come back. Beside it, the app
reads the stack's offer: the categories of what costs nothing to remove — downloads never
imported, archive parts already unpacked — each with its size, under the name the stack
gave the offer. Each category is its own control, nothing is selected for the operator, and
nothing else is offered: media, anything seeding and anything left alone stay where they
are (`N12-R4`, `N12-R5`, `D5-R5`).

Agreeing to a category sends `space` with the offer's name and that category alone
(`ARCH-R289`), follows the job, and says what came back. An offer that moved since it was
read is read again and shown again, and nothing is removed until the operator agrees to the
new one (`ARCH-R142`). Stopping a download seeding stays its own action (`N12-R7`).

### The line is shared from the Bandwidth screen

Every limit the command line declares can be changed here: download and upload, each as a
share of the measured line or as a figure; the active window; the line's own capacity; the
monthly cap and what reaching it does; and a temporary lift. A share is set with its
measured capacity beside it and the rate it comes to (`D10-R2`); upload is set apart from
download and starts from the more careful default (`D10-R4`).

A change is rehearsed before it is applied. The rehearsal shows what each download client
would be asked, and where a limit affects seeding, what it costs the ratio (`D10-R5`);
labelled a rehearsal, never as limits in force (`N6-R1`). Applied, the screen shows what each
client then said it is doing, and an overshoot the stack reports (`D10-R13`). A temporary
lift is chosen as 15 minutes, an hour or four hours, or a number of minutes up to 240, and
the screen says when it ends.

A refusal is drawn as itself with the stack's remedy: a share of a line nobody measured, a
window with no time zone, a value the stack cannot read, or no download client to limit.

## States

| State | Meaning |
|---|---|
| Unverified, can be run | A finding that disturbs to check, with what it disturbs and its bound, and the way to run it. |
| Asking | What a run, a reclaim or a change will do, before it is sent. |
| Running | A job the stack accepted, followed until it ends. |
| Rehearsed | A change to the line as the stack says it would go, labelled a rehearsal. |
| Done | What the run found, what came back, or what each client is doing. |
| Offer moved | The room offered changed since it was read; shown again, nothing removed. |
| Refused | The stack's refusal and remedy, drawn as a refusal. |
| Member | None of this is offered (`N3-R19`). |

## Edge cases

| Situation | Behaviour |
|---|---|
| The stack reports no bound for a disruptive check | The confirmation says the stack gave no bound, and the app adds none (`N2-R8`, `B2-R16`). |
| Nothing costs nothing to remove | Storage says so; no reclaim control is drawn. |
| A temporary lift is running | The screen says until when, and offers ending it now. |
| The phone loses the stack mid-job | The job is the core's; the screen asks after it again when it can (`N1-R24`). |

## Requirements

| ID | Requirement |
|---|---|
| **N30-R1** | A finding the stack leaves unverified because checking it disturbs something MUST offer running that check, narrowed to the check or group the stack names for it (`ARCH-R288`). |
| **N30-R2** | Before a disruptive check is sent, the app MUST state what it disturbs and the bound the stack reported, or that it reported none, and where the stack reports transfers in progress, that they are interrupted; it MUST NOT estimate a duration (`N2-R8`, `C1-R5`). |
| **N30-R3** | A disruptive check MUST be followed to its end and its finding drawn again with the verdict the run came to and when it ran, and MUST NOT be offered as a rehearsal. |
| **N30-R4** | Storage MUST show the stack's offer of what costs nothing to remove, by category with each one's size, MUST make each category its own agreement with none selected, and MUST NOT offer media, anything seeding or anything left alone (`N12-R4`, `N12-R5`, `D5-R5`). |
| **N30-R5** | Agreeing to a category MUST send `space` with the offer's name and that category alone (`ARCH-R289`), and MUST say what came back; an offer that moved MUST be read and shown again with nothing removed (`ARCH-R142`). |
| **N30-R6** | The Bandwidth screen MUST offer every limit the `bandwidth` action takes: download and upload as a share or a figure, the active window, the line's capacity, the monthly cap with what reaching it does, and a temporary lift of up to 240 minutes (`D10-R1`, `D10-R3`, `D10-R9`, `D10-R11`). |
| **N30-R7** | A share MUST be set with the measured capacity beside it and the rate it comes to, and upload MUST be set apart from download, starting from the more careful default (`D10-R2`, `D10-R4`). |
| **N30-R8** | A change to the line MUST be rehearsed before it is applied, showing what each download client would be asked and the ratio cost of a limit that affects seeding, labelled a rehearsal (`D10-R5`, `N6-R1`); applied, the screen MUST show what each client then said it is doing and any overshoot (`D10-R13`). |
| **N30-R9** | A refusal of any of the three MUST be drawn as a refusal with the stack's remedy, never as an empty or unchanged screen (`G4-R16`). |

## Notes

The three share a page because they share a shape: a screen that reads becomes one that
also acts, each act asked for on the core's own terms, which differ. A disruptive check has
no rehearsal and no offer; room comes back only against the stack's named offer; the line
is changed with no offer but always rehearsed first.

## Related

- [N2](n2-operator-companion.md) — disruptive actions say what they disturb first
- [N12](n12-making-room.md) — making room, by category and never as one act
- [N10](n10-nobody-watching.md) — what the line screen reads
- [C1](../c-trust/c1-diagnostics.md) — opt-in disruptive checks
- [D5](../d-content/d5-disk-space.md) — what is reclaimable
- [D10](../d-content/d10-bandwidth.md) — limits, schedules, caps and lifts
