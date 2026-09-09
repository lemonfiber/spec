---
id: F6
title: Plugin lifecycle
kind: feature
area: F
audience: operator
status: draft
maturity: planned
priority: P1
labels: [extensibility, verification, updates]
requires: [F3, F4, E4]
relates: [F5, F7, E3, C9]
---

# F6 — Plugin lifecycle

**Status:** Draft · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Say what actually happens when a plugin is added, and what happens when it is taken away —
including when either goes wrong halfway.

Installing a plugin is the most consequential thing an operator can ask lemonfiber to do
to a working stack. It can add a service, take over a capability another service was
filling, rewrite wiring and change settings the household depends on. A design that got
everything else right and left this as "we write the changes and hope" would be worse than
having no plugins at all, because the failure lands on a stack that was working.

So the lifecycle is built on the machinery that already exists for exactly this problem.
Every change a plugin makes is journalled. Verification runs over what it changed, not
just over what it claimed. A failure anywhere reverses what was done. And removal is not a
second, parallel implementation of undoing — it is a rollback with a name on it.

## Behaviour

### Rehearse first: shown, not guessed

Before anything is written, an install can be **rehearsed**. The rehearsal states exactly
what would change: which services would start, which capability would change hands, which
settings would be rewritten and from what to what, which secrets would be captured, which
hosts would be reached, and which of the plugin's proofs would run.

A rehearsal touches nothing. It is the answer to "what is this about to do to my stack",
given before the stack finds out, and it is the same account the install will follow.

### Then its proofs, then the stack's own verification

An install is not done when the writes succeed. Two things must hold, in order:

1. **The plugin's declared proofs pass** — it works.
2. **The stack's own verification passes over what the plugin changed** — everything else
   still works.

The second is what a plugin cannot check for itself. A plugin can substitute a media
server, pass every one of its own proofs, and leave the request service unable to sign
anybody in. Its proofs were never going to catch that; the stack's own checks are.

### Either failure reverses the install

If the proofs fail, or the stack's verification fails, the install is **put back** through
the journal — the same rollback machinery that reverses an apply, with the same honesty
about what it cannot reverse. An operator is not left with a half-installed plugin and a
broken sign-in.

Where the reversal itself cannot complete — a service unreachable, a value changed by hand
in the meantime — the exact resulting state is reported. Never "something went wrong":
which changes went back, which did not, and what each of those leaves.

### Removal is a rollback with a name on it

Removing a plugin replays its journalled changes in reverse. It inherits every refusal the
rollback layer already makes: a setting edited by hand since is drift and is not silently
overwritten; a change a later change depends on is refused until that one goes back; a
move that re-points a location says plainly that data does not follow it.

There is no separate "disable". A plugin is installed or it is not, because a third state
in which a plugin is present but inert is a state nothing else in this product has and one
an operator would have to keep in their head.

### Updating is removal and installation, judged as one

A plugin update is the old one going back and the new one going in, rehearsed as a single
account and reversed as a single unit if either half fails. An update that left a stack
between two versions of a plugin would be the worst of both.

### Capability negotiation, not version pinning

A plugin says what it needs of lemonfiber. If something is missing, the refusal names the
missing capability — not a version number. A plugin keeps working across upgrades for
exactly as long as what it actually uses still exists, and when it stops working the
message says which thing went.

## States

| State | Meaning |
|-------|---------|
| `rehearsed` | What the install would do has been stated; nothing written |
| `installing` | Changes are being written and journalled |
| `proving` | The plugin's own declared proofs are running |
| `verifying` | The stack's verification is running over what the plugin changed |
| `installed` | Both passed; the plugin is in force |
| `reversed` | Something failed and the install was put back in full |
| `partially-reversed` | The reversal could not complete; the exact resulting state is reported |
| `unmet-requirement` | The plugin needs a capability this lemonfiber does not provide, named |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| The plugin's proofs fail | Reverse the install through the journal. Report which proof failed and what it answered. |
| The plugin's proofs pass but the stack's verification fails | Reverse the install. Name what broke — this is the case a plugin cannot check for itself. |
| The reversal itself fails partway | Report the exact resulting state: what went back, what did not, and what each leaves. Never leave it ambiguous. |
| A service is running when a change needs it stopped | Say what will be interrupted before doing it, then stop, change and restart. |
| A setting the plugin wrote was edited by hand since | Treat it as drift on removal: refuse rather than overwrite, and say what the file holds. |
| A later change depends on something the plugin set | Refuse the removal until that change goes back, naming it. |
| An update's new version fails its proofs | Put the whole update back — the old plugin returns. Never leave the stack between two versions. |
| A plugin needs a capability this lemonfiber lacks | Refuse, naming the capability rather than a version. |
| Removing a plugin would leave a capability unfilled | Say so in the rehearsal for the removal, before it happens. |
| The operator removes a plugin whose service holds data | Re-point what re-points, and say plainly that data is not moved back. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F6-R1** | An install MUST be rehearsable, stating every change it would make and every proof it would run, without writing anything. |
| **F6-R2** | Every change an install makes MUST be journalled as it is made. |
| **F6-R3** | An install MUST NOT be reported as complete until the plugin's declared proofs have passed. |
| **F6-R4** | An install MUST NOT be reported as complete until the stack's own verification has passed over what the plugin changed. |
| **F6-R5** | A failure of either MUST reverse the install through the journal. |
| **F6-R6** | A reversal that cannot complete MUST report the exact resulting state — what went back, what did not, and what each leaves. |
| **F6-R7** | Removing a plugin MUST reverse its journalled changes, and MUST inherit the rollback layer's refusals for drift and for dependent later changes. |
| **F6-R8** | Where a change requires a running service to stop, what will be interrupted MUST be stated before it is. |
| **F6-R9** | Updating a plugin MUST be rehearsed as one account and reversed as one unit, and MUST NOT leave the stack between two versions. |
| **F6-R10** | A plugin MUST declare the capabilities it requires of lemonfiber, and an unmet requirement MUST be refused by naming the capability rather than a version. |
| **F6-R11** | A removal that would leave a capability unfilled MUST state so before it happens. |
| **F6-R12** | Reversing a change that re-points a data location MUST state that the data itself does not move back. |
| **F6-R13** | Installing, rehearsing, updating and removing MUST each be reachable non-interactively with a meaningful exit status. |

## Related

- [E4 Rollback](../e-maintenance/e4-rollback.md) — the journal and the reversal machinery this is built on
- [F3 Plugin manifests and recipes](f3-stack-manifests.md) — what is being installed
- [F4 Capabilities & substitution](f4-capabilities.md) — what changes hands during an install
- [F7 Plugin provenance](f7-plugin-provenance.md) — what is readable afterwards
- [E3 Backup & restore](../e-maintenance/e3-backup-restore.md) — the heavier recovery path when a reversal cannot finish
