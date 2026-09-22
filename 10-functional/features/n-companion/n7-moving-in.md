---
id: N7
title: Moving in beside what is already there
kind: feature
area: N
audience: operator
status: draft
maturity: planned
priority: P3
labels: [mobile, storage, wiring, ux]
requires: [N1, A5]
relates: [D1, A6, E3, N2]
---

# N7 — Moving in beside what is already there

**Status:** Draft · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

Most people who install lemonfiber already have something running. Taking that
over is the most consequential thing the product does to a machine it did not
set up, and it is a long operation an operator will not sit and watch.

So it is exactly the thing they will pick a phone up to check on — *did it take
my Sonarr settings, is it safe to turn the old one off, what did it decide it
could not bring across*. The stack already answers all three. Nothing renders
them away from the machine.

[A5](../a-getting-started/a5-migration.md) owns what moving in is and what it
covers. This owns what it looks like from somewhere else while it happens, and
afterwards.

## Behaviour

### What did not come across is the part worth reading

An import carries some things and not others, and the contract names each thing
it could not carry and why. **That list is the finding**, not a footnote to a
success message: an operator who believes their quality profiles came over, and
discovers in three weeks that they did not, was told something true and useless.

The app leads with what was left behind.

### A stance is four things, and only one of them is done

Moving in is *unchanged*, *pending*, *blocked* or *applied*. The app renders
which, and never renders the first three as the last. A blocked move carries its
refusal, and the refusal is shown rather than a generic failure.

### A refusal is an answer

Where the stack refuses to take something over — because it would overwrite, or
because it cannot read it — that refusal is what the operator needs and is shown
with its reason. It is not an error state and not a retry prompt.

### What wants a copy first says so before it is agreed to

Some things the stack takes over are taken over destructively, and it says which
of those it would want a backup of first. That is stated with the decision rather
than after it, and it is the same discipline `N6` applies to a copy's scope.

### A conflict names what already holds the thing

Running beside an existing setup means ports that are taken. The contract carries
what is conflicting and what holds it, and the app names the holder — *something
else is on 8989* is not actionable, and *your existing Sonarr is on 8989* is.

### A port that moved is remembered, not just reported

Where the stack put a service on a different port to avoid a collision, that is
not a transient detail of the install. It is how the operator will reach the
thing for as long as it runs, and the app keeps it available rather than showing
it once.

### Unassessable is not the same as fine

When the stack wires services together it may be unable to assess whether a
connection is sound. That is a third answer beside *sound* and *broken*, and it
stays a third answer here: an app that rendered it as fine would be inventing
confidence the core declined to express (`N2-R14`).

### A wiring that would break something says what and how to mend it

Where a connection carries a severity, it carries what would break and what would
put it right. Both are shown; a severity alone is a colour, not information.

## States

| State | Meaning |
|-------|---------|
| Unchanged | Nothing has been taken over. What would be is shown. |
| Pending | A move is agreed and not finished. Never rendered as done. |
| Blocked | The stack refused, and the refusal is shown with its reason. |
| Applied | It finished. What was not carried is shown alongside what was. |
| Unassessable | A wiring could not be judged. Shown as its own answer, not as sound. |
| Unknown | The move could not be read. Never rendered as unchanged. |

## Edge cases

- **An import that carried nothing.** Distinguished from an import that has not
  run. Both are quiet screens and they mean opposite things.
- **A conflict on a port the operator cannot change.** The holder is named, and
  what the stack did instead is shown, rather than the move simply failing.
- **A move applied while the app was closed.** The app renders the finished state
  and what was not carried, rather than treating it as new.
- **A refusal the operator can do nothing about.** Still shown. An operator who
  cannot see why a thing did not happen will try it again.

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N7-R1** | What an import could not carry MUST be shown with the reason for each, and MUST NOT be subordinated to a success message. |
| **N7-R2** | The stance of a move MUST be rendered as given, and *unchanged*, *pending* or *blocked* MUST NOT be presented as *applied*. |
| **N7-R3** | A refusal MUST be shown with the reason the stack gave, and MUST NOT be rendered as a generic failure or a retry prompt. |
| **N7-R4** | Where the stack would take something over destructively and wants a copy first, the app MUST say so before the decision is agreed to. |
| **N7-R5** | A conflict MUST name what already holds the thing it conflicts over. |
| **N7-R6** | Where a service was placed on a different port to avoid a conflict, the app MUST keep that reachable afterwards and MUST NOT show it only at the moment it happened. |
| **N7-R7** | A wiring the stack could not assess MUST be shown as its own answer, and MUST NOT be rendered as sound. |
| **N7-R8** | Where a wiring carries a severity, what would break and what would put it right MUST both be shown. |
| **N7-R9** | An import that carried nothing MUST be told apart from an import that has not run. |
| **N7-R10** | A rehearsed wiring run MUST be labelled as a rehearsal, on the same terms as `N6-R1`. |

## Related

- [N1](n1-companion-app.md) — connecting, parity, and what the app may claim
- [N2](n2-operator-companion.md) — the verdict, and why a value is never substituted
- [N6](n6-taking-a-copy.md) — copies, and what a rehearsal may not look like
- [A5](../a-getting-started/a5-migration.md) — what moving in is and what it covers
- [D1](../d-content/d1-seed.md) — wiring the services to each other
- [A6](../a-getting-started/a6-uninstall.md) — leaving, and what is left behind
