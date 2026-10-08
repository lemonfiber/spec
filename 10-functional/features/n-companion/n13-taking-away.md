---
id: N13
title: Taking something away
kind: feature
area: N
audience: operator
status: accepted
maturity: built
priority: P3
labels: [mobile, household, storage, ux]
requires: [N1, A6]
relates: [D6, D7, A5, N3, N6, N7, N12]
---

# N13 — Taking something away

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Two removals, and what they have in common is that a half-done one reads exactly
like a finished one.

Taking a person out of the household and taking lemonfiber off the machine are
different operations with the same failure mode: the operator is told it is done,
and it is done in one place and not another. The stack is careful about this — it
says how far a revocation reached, what it could not read, and what it could not
take — and none of that care survives to a surface away from the machine unless
the surface carries it.

[N3](n3-household-companion.md) already covers what happens to a **member's** app
when their identity is removed (`N3-R13`). This is the operator's side of the same
act, and of the larger one beside it.

Two neighbouring acts are not this page's. **Replacement** is A5's replace mode:
it stops the containers of a project that is already on the machine and deletes
none of them, and [N7](n7-moving-in.md) owns it with the rest of moving in
(`N7-R18`). **Substitution**, one service in place of another for a capability, is
[N5](n5-connecting-the-stack.md)'s (`N5-R4`) and [N25](n25-a-plugin-after-it-lands.md)'s.

## Behaviour

### A revocation reaches everywhere, or only the media server, or nowhere

The contract distinguishes these, and the distinction is the whole point.
*Removed* that turns out to mean *removed from Jellyfin and still holding an
account on the request service* is a false statement the operator will act on —
they will believe the person is gone.

So the app says which of the three happened, in those terms, and never renders
*media-server-only* as done. *Nothing* is what an unconfirmed reading says: what
removing them would cost, with nobody removed.

### What removing a person costs is said before they are removed

Somebody with pending requests is not the same as somebody with none, and whether
they ask through the request service at all changes what removing them does. Their
requests are destroyed rather than handed to anybody, and their watch history goes
with the account. All of it is shown before the decision, not discovered
afterwards.

The removal's findings — what could not be done, and what the stack thinks the
operator should know — are shown in the stack's words, before and after. A finding
is how the stack says the request service would not answer, or that an account is
still left there for the next run to take.

### An uninstall says what it could not read

The stack reports whether its account of what it would remove is **complete**,
and names what it could not read. That is the most important sentence on the
screen: an operator uninstalling to reclaim a disk, or because they are handing
the machine on, is entitled to know the list is partial.

An incomplete account is never presented as a complete one. That is about the
reading, before anything goes. Whether the removal itself finished is a second
question with its own answer, below.

### What is not lemonfiber's is named as not lemonfiber's

An uninstall finds things at the locations it manages that it did not put there.
The contract carries them separately, with how much and how many, and the app
keeps them separate — an operator deciding whether to delete a directory needs to
know some of what is in it is theirs.

### What is kept is kept for a reason, and said

An image another project stands on, or a path the stack could not confirm, stays
on the list with the reason it is being kept. It is not counted in what the
removal frees, and it is not hidden: a list that dropped it would read as a
machine with less on it than it has.

### The library tier is its own decision

Removing the library and the downloads is never offered beside another tier, and
its agreement names how much data goes. Where the data location is on a network
share or a drive that unplugs, that is said before anything is agreed, because a
removal across a mount somebody forgot was a mount is otherwise found out
afterwards.

### Downloads still coming down are named, and waiting is offered

Stopping interrupts what is still arriving. The stack names each one with how far
along it is, and the app offers waiting for them to land beside going ahead now.
Neither is chosen for the operator.

### Removing configuration says what it destroys, and what it takes first

The tier that removes configuration destroys credentials, and the app says which,
by name and never by value (`N6-R7`). Before it is agreed to, the app shows what
the stack says about the backup it takes first. Afterwards, the credentials the
removal destroyed are listed.

That tier also removes what admits this app. The web interface's password is
among lemonfiber's own state, and without it the stack stops offering the surface
the app reaches. So the app says before the agreement that its own session ends
when this runs, and afterwards that reaching a stack on that machine again means
setting one up and pairing again. The pairing itself stays until the operator
takes it away: a session ending is not a machine changing (`N1-R45`).

### What lemonfiber cannot take is named, with how to take it by hand

Docker itself, a natively installed media server, a tunnel client such as
Tailscale, the lemonfiber binary: things the stack did not install, or cannot take
out from under itself, and will not remove. Each is listed with why it is not
lemonfiber's and how to remove it on this platform, including where the survey
did not find it, because a survey that could not look is not a machine without
it. After a removal that could not take everything, each thing left is named with
what the machine said about it and how to finish by hand.

### Nothing is removed without agreement, and the agreement names the scope

Each operation carries an agreement of its own. The app does not accept one
agreement for a different operation than the one described, and does not carry an
agreement forward from a previous screen: it asks every time, because it retains
none (`N1-R41`).

### A refusal is shown, with the reason

Where the stack refuses either of these, the refusal and its reason are what the
operator needs. It is not an error to be retried.

### A rehearsed removal removed nothing

As everywhere (`N6-R1`), and here it decides whether somebody still has access.

## States

Neither operation carries a `stance`. *Unchanged* and *pending* are the stance of
a proposed change read against what is in force — `unchanged` is a change that
already holds what was asked for, `pending` is one staged and not yet agreed to —
and they are replacement's words, rendered in [N7](n7-moving-in.md), not these.

**Removing a person**, from `confirmed` and `revoked`:

| State | Meaning |
|-------|---------|
| Unconfirmed | Read and not agreed to. What removing them costs is shown; `revoked` is *nothing*. |
| Everywhere | Gone from the media server and the request service. |
| Media server only | They can neither watch nor ask, and an account is still held on the request service. Never rendered as done. |

**Taking lemonfiber off**, from `removal.state`:

| State | Meaning |
|-------|---------|
| Surveyed | Everything the tier reaches is listed with its size. Nothing has been removed. |
| Rehearsed | The tier and the reading were agreed to and nothing was touched. Labelled as a rehearsal (`N6-R1`). |
| Complete | Everything the reading named as going is gone, with the credentials it destroyed. |
| Partial | Some of it could not be removed, and each thing left is named with how to finish it by hand. Never rendered as complete. |

`confidence` is about the reading, and is read before anything is removed;
*partial* is about the removal, and is read after. A complete reading can end in a
partial removal and an incomplete one can end complete, so the two are shown
apart.

**Either**:

| State | Meaning |
|-------|---------|
| Refused | The stack turned it away, with its reason. Nothing was removed. |
| Unknown | The operation could not be read. Never rendered as not having run. |

## Edge cases

- **A person removed from the media server while the request service is down.**
  The reach of the revocation is what is shown, *media-server-only*, with the
  finding that says why — not the intent of the operation.
- **The request service would not say what it holds for them.** Their account
  there is not counted and not removed, and the finding says so. The revocation
  reads *media-server-only*, because removal is not complete until the stack
  knows there is nothing left.
- **An uninstall on a machine where another tool shares the data root.** The
  foreign items are named and are not counted as lemonfiber's, and the data
  location is not removed as one tree.
- **The container engine does not answer.** The reading is incomplete and names
  the engine among what it could not read. It is not shown as a machine with no
  containers on it.
- **An agreement given, then the stack restarted before it was acted on.** The
  stack names an uninstall's agreement after the reading itself, so where nothing
  changed the same agreement would still stand. The app asks again anyway: it
  retains no agreement past the screen it was given on (`N13-R7`, `N1-R41`).
- **Removing configuration from the app itself.** The app shows the answer the
  stack gave for the removal, and then that reaching that machine again needs a
  stack set up and paired again, and why (`N13-R20`).

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N13-R1** | How far a revocation reached MUST be shown as one of *everywhere*, *media-server-only* or *nothing*, and MUST NOT be flattened into *removed*. |
| **N13-R2** | A revocation that reached only the media server MUST NOT be rendered as complete. |
| **N13-R3** | Before a person is removed, the app MUST show what they have outstanding and whether they ask through the request service. |
| **N13-R4** | An uninstall MUST state whether its account of what would be removed is complete, and MUST name what could not be read. |
| **N13-R5** | An incomplete account MUST NOT be presented as a complete one. |
| **N13-R6** | Items found at managed locations that lemonfiber did not put there MUST be shown separately, with their extent. |
| **N13-R7** | Each of these operations MUST carry its own agreement, naming its scope, and an agreement MUST NOT be carried forward from another screen or another operation. |
| **N13-R8** | *Withdrawn — carried to [N7-R18](n7-moving-in.md), because replacement is A5's replace mode and N7 owns moving in. The number is not reused.* |
| **N13-R9** | A refusal MUST be shown with the stack's reason, and MUST NOT be rendered as an error to retry. |
| **N13-R10** | A rehearsed removal MUST be labelled as a rehearsal (`N6-R1`). |
| **N13-R11** | An operation that could not be read MUST be told apart from one that has not run. |
| **N13-R12** | Removing the library and the downloads MUST be offered only on its own, never beside another tier, and its agreement MUST state the amount of data that goes before it is given (`A6-R1`, `A6-R4`). |
| **N13-R13** | Where the stack says the data location is on a network share or a drive that unplugs, the app MUST show that before the removal is agreed to, and MUST ask for it to be acknowledged apart from the agreement itself. |
| **N13-R14** | Where downloads are still coming down, the app MUST name each with how far along it is before the removal is agreed to, and MUST offer waiting for them to land beside going ahead; going ahead MUST say that they will be interrupted (`A6-R11`). |
| **N13-R15** | Before a tier that removes configuration is agreed to, the app MUST show what the stack says about the backup it takes first, and MUST NOT say a backup will be taken where the stack says none (`A6-R12`). |
| **N13-R16** | Before configuration is removed, each item that holds a credential MUST be marked as holding one, and its value MUST NOT be shown (`N6-R7`). Once it is removed, the credentials the removal destroyed MUST be listed by name, on a complete and a partial removal alike (`A6-R5`). |
| **N13-R17** | An item the stack keeps rather than removes MUST be shown as kept, with the reason, apart from what goes, and MUST NOT be counted in what the removal frees (`A6-R10`). |
| **N13-R18** | What lemonfiber cannot remove MUST be listed with why it is not lemonfiber's and how to remove it by hand, and one the survey did not find MUST be told apart from one it found (`A6-R6`). After a removal that could not take everything, each thing left MUST be named with what the machine said about it and how to finish it by hand (`A6-R8`). |
| **N13-R19** | Before a person is removed, the app MUST state what removing them does to their watch history and to their requests — that the requests are destroyed, not handed to anybody — as the stack states it (`D6-R9`), and MUST show every one of the removal's findings in the stack's words, before it is agreed to and after it runs. |
| **N13-R20** | Before the tier that removes configuration is agreed to from the app, the app MUST say that it removes what admits this app to the stack, so that the app's session ends when it runs and the stack stops offering the surface the pairing reaches. After it has run, the app MUST say that reaching that machine again needs a stack set up and paired again, and why (`N1-R34`); it MUST NOT report the ended session as a refused credential (`N1-R46`), and MUST NOT discard the pairing unless the operator asks it to (`N1-R45`). |

## Notes

**What the contract carries for the rows above.** Checked against the core's
`contract/web-api/` — the `removal` and `uninstall` kinds — and the
actions its HTTP route accepts: `remove` for a person, `uninstall` for a tier.

| Row | Carried | Not carried |
|---|---|---|
| `N13-R1`, `N13-R2` | `removal.revoked`: `everywhere`, `media-server-only`, `nothing` | — |
| `N13-R3` | `removal.requests`, `removal.asks-through-the-request-service` | — |
| `N13-R4`, `N13-R5` | `uninstall.manifest.confidence`: `complete`, and `unread` in the words of whatever refused | — |
| `N13-R6` | `manifest.foreign`: `at`, `bytes`, `files` | — |
| `N13-R7` | `manifest.agreement`, the name of the reading, answered through the action's `offer`. The core checks an agreement given for any tier against the reading standing now, and requires one for `media` | **A person's removal carries no agreement.** The `remove` action takes a bare `confirm`, so nothing on the wire can name what was agreed to or tell one agreement from another |
| `N13-R9` | The error envelope, with the stack's own reason — an agreement missing for `media`, or naming a reading that no longer stands | — |
| `N13-R10` | `removal.state: confirmed`, the state an uninstall rehearsal ends in | **No rehearsal can be asked for.** No action argument on the HTTP route asks for one, so none arrives. A person's removal carries no marker of a rehearsal at all: `confirmed: false` is an unconfirmed reading and a rehearsed one alike |
| `N13-R11` | — | — |
| `N13-R12` | `manifest.tier`, `manifest.bytes`, `manifest.removes`, `manifest.items` | — |
| `N13-R13` | `manifest.volume` | — |
| `N13-R14` | `manifest.coming`: `name`, `progress`; the action's `wait` | — |
| `N13-R15` | `manifest.backup` | — |
| `N13-R16` | `items[].secret`; `removal.credentials` on `complete` and `partial` | — |
| `N13-R17` | `items[].kept`; `manifest.bytes` counts only what goes | — |
| `N13-R18` | `manifest.outside`: `what`, `why`, `by_hand`, `found`; `removal.left`: `name`, `why`, `by_hand` | — |
| `N13-R19` | `removal.findings`, `removal.requests` | **The effect on watch history.** `findings` carries what could not be done — a request service that would not answer, an account left behind — and nothing on the wire says that the watch history goes with the account |
| `N13-R20` | `manifest.tier: configuration`, and the web interface's password among `items` | — |

The three gaps in bold are the contract's to close, and until they are the rows
stand as written: `N1-R17` and `N2-R14` apply, and the app substitutes nothing of
its own for what the stack does not say. A requirement is not withdrawn for being
unanswerable from the wire.

## Related

- [N1](n1-companion-app.md) — connecting, parity, pairing, and what the app may claim
- [N3](n3-household-companion.md) — what a removed member's own app does
- [N6](n6-taking-a-copy.md) — a copy before a destructive act, and rehearsals
- [N7](n7-moving-in.md) — replacement, with the rest of moving in
- [N12](n12-making-room.md) — removing media, which is a different act
- [A6](../a-getting-started/a6-uninstall.md) — leaving, and what is left behind
- [A5](../a-getting-started/a5-migration.md) — the replace mode
- [D6](../d-content/d6-household-identity.md) — who is in the household
- [D7](../d-content/d7-approval-quotas.md) — what they had outstanding
