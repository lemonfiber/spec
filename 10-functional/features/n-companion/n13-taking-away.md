---
id: N13
title: Taking something away
kind: feature
area: N
audience: operator
status: draft
maturity: planned
priority: P3
labels: [mobile, household, storage, ux]
requires: [N1, A6]
relates: [D6, D7, A5, N3, N6, N12]
---

# N13 — Taking something away

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Three removals, and what they have in common is that a half-done one reads
exactly like a finished one.

Taking a person out of the household, swapping a service for another, and taking
lemonfiber off the machine entirely are different operations with the same
failure mode: the operator is told it is done, and it is done in one place and
not another. The stack is careful about this — it says how far a revocation
reached, what it could not read, and what is still running — and none of that
care survives to a surface away from the machine, because there is no surface.

[N3](n3-household-companion.md) already covers what happens to a **member's**
app when their identity is removed (`N3-R13`). This is the operator's side of
the same act, and of the two larger ones beside it.

## Behaviour

### A revocation reaches everywhere, or only the media server, or nowhere

The contract distinguishes these, and the distinction is the whole point.
*Removed* that turns out to mean *removed from Jellyfin and still able to make
requests* is a false statement the operator will act on — they will believe the
person is gone.

So the app says which of the three happened, in those terms, and never renders
*media-server-only* as done.

### What the person had outstanding is said before they are removed

Somebody with pending requests is not the same as somebody with none, and
whether they ask through the request service at all changes what removing them
does. Both are carried and both are shown before the decision, not discovered
afterwards by requests that no longer have an owner.

### An uninstall says what it could not read

The stack reports whether its account of what it would remove is **complete**,
and names what it could not read. That is the most important sentence on the
screen: an operator uninstalling to reclaim a disk, or because they are handing
the machine on, is entitled to know the list is partial.

An incomplete account is never presented as a complete one.

### What is not lemonfiber's is named as not lemonfiber's

An uninstall finds things at the locations it manages that it did not put there.
The contract carries them separately, with how much and how many, and the app
keeps them separate — an operator deciding whether to delete a directory needs to
know some of what is in it is theirs.

### Nothing is removed without agreement, and the agreement names the scope

Each of these carries an agreement. The app does not accept one agreement for a
different operation than the one described, and does not carry an agreement
forward from a previous screen.

### A replacement says what stopped, what would stop, and what is still running

Swapping one service for another is three lists, and an operator reads all
three. *Still running* is the one that matters most and is the one a success
message would omit: a replacement that left the old service running has not
replaced anything, it has doubled it.

### A refusal is shown, with the reason

Where the stack refuses any of these, the refusal and its reason are what the
operator needs. It is not an error to be retried.

### A rehearsed removal removed nothing

As everywhere (`N6-R1`), and here it decides whether somebody still has access.

## States

| State | Meaning |
|-------|---------|
| Unchanged | Nothing has been taken away. What would be is shown. |
| Pending | Agreed and not finished. Never rendered as done. |
| Blocked | Refused, with the reason. |
| Applied, complete | Finished, and the stack could account for all of it. |
| Applied, partial | Finished, and the account is incomplete, naming what could not be read. |
| Unknown | The operation could not be read. Never rendered as unchanged. |

## Edge cases

- **A person removed from the media server while the request service is down.**
  The reach of the revocation is what is shown, not the intent of the operation.
- **An uninstall on a machine where another tool shares the data root.** The
  foreign items are named and are not counted as lemonfiber's.
- **A replacement where the old service refuses to stop.** It appears under
  *still running*, and the operation is not reported as applied.
- **An agreement given, then the stack restarted before it was acted on.** The
  agreement is asked for again rather than assumed to stand.

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
| **N13-R8** | A replacement MUST show what stopped, what would stop and what is still running, and MUST NOT be reported as applied while anything it replaces is still running. |
| **N13-R9** | A refusal MUST be shown with the stack's reason, and MUST NOT be rendered as an error to retry. |
| **N13-R10** | A rehearsed removal MUST be labelled as a rehearsal (`N6-R1`). |
| **N13-R11** | An operation that could not be read MUST be told apart from one that has not run. |

## Related

- [N1](n1-companion-app.md) — connecting, parity, and what the app may claim
- [N3](n3-household-companion.md) — what a removed member's own app does
- [N6](n6-taking-a-copy.md) — a copy before a destructive act, and rehearsals
- [N12](n12-making-room.md) — removing media, which is a different act
- [A6](../a-getting-started/a6-uninstall.md) — leaving, and what is left behind
- [D6](../d-content/d6-household-identity.md) — who is in the household
- [D7](../d-content/d7-approval-quotas.md) — what they had outstanding
