---
id: N19
title: Getting underneath it
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P3
labels: [mobile, ux, extensibility, cli]
requires: [N1, F1]
relates: [C9, B2, N2, N14, N18]
---

# N19 — Getting underneath it

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

[F1](../f-extensibility/f1-customisation.md) makes one guarantee the rest of
this product leans on: **lemonfiber is never the thing standing between an
operator and their stack.** The stack is a real Compose project that runs with
no Rust binary anywhere, every command can show its work, files lemonfiber
writes may be edited and are respected, and any area can be declared unmanaged.

A graphical surface is where that guarantee is most easily lost, and an app is
the most graphical surface this product has. It has no shell to fall back to, no
flags to pass, and no obvious place to read what it is about to do. If the
escape hatch is not visible from here, then for anybody whose main surface is
their phone, it does not exist.

The audience `F1` is written for is the one that evaluates this project
publicly, and their objection — *"it hides what's actually happening"* — is
about exactly the shape an app naturally takes.

## Behaviour

### Every offer can show its work

Where the app offers to do something, it can show the command that does it. Not
as a diagnostic buried somewhere, and not only when something has gone wrong:
the same way `--dry-run` prints the invocation without running it, because
nothing is generated that the operator cannot read.

This is the same move [N14](n14-what-version.md) already makes for an update the
app cannot perform itself. There it is a necessity; here it is a promise.

### An escape hatch is not hidden behind a warning

An action an operator can take outside the app is offered plainly. A route
presented with a caution that discourages taking it has been closed politely,
and the audience this guarantee exists for reads that correctly the first time.

### An edited file is respected, and says so

Files lemonfiber writes may be edited directly, and modifications are detected
by content rather than overwritten. Where the operator has edited one, the app
says it is edited and respected — never that it has drifted, and never with an
offer to put it back.

*Drift* and *a decision somebody made* look identical to a surface that only
reads a checksum. They are opposite facts about the same bytes.

### An unmanaged area is shown as unmanaged

An operator can declare a service, or one area of configuration, unmanaged.
lemonfiber reports its state and never writes to it. The app shows that as what
it is — a choice in force — and not as unconfigured, failed, or waiting to be
set up.

A surface that rendered an unmanaged area as incomplete would be asking the
operator to undo a decision it did not know they had made, which is the same
mistake [N18](n18-running-part-of-it.md) refuses about a partial stack.

### Nothing here requires the app

Where the contract carries it, the app can say that the stack runs without
lemonfiber and that every action has a non-interactive equivalent. An operator
wondering what happens if they delete this app should be able to find out from
inside it.

That is not a modest claim to make on a screen, and it is the one that makes
installing the app a low-risk decision — for the same reason `F1` gives about
adopting lemonfiber at all.

## Requirements

| ID | Requirement |
|----|-------------|
| **N19-R1** | Where the app offers an action, it MUST be able to show the command that performs it, without the operator having to reach another surface to find out. |
| **N19-R2** | An action available outside the app MUST be offered plainly, and MUST NOT be presented with a caution that discourages taking it. |
| **N19-R3** | A materialised file the operator has edited MUST be shown as edited and respected, and MUST NOT be rendered as drift. |
| **N19-R4** | The app MUST NOT offer to reassert a value the operator has changed (`C9`). |
| **N19-R5** | An area declared unmanaged MUST be shown as unmanaged, and MUST NOT be rendered as unconfigured, failed, or awaiting setup. |
| **N19-R6** | The app MUST NOT write to an area declared unmanaged, and MUST NOT report drift for one. |
| **N19-R7** | Where the contract carries it, the app MUST be able to state that the stack runs without lemonfiber and that every action has a non-interactive equivalent. |
| **N19-R8** | Where a stack was substituted wholesale, the app MUST show that it is operating the operator's own stack rather than the bundled one. |
| **N19-R9** | Commands, edited files or unmanaged areas that could not be read MUST be told apart from there being none. |
| **N19-R10** | Nothing on this surface MUST offer first-run setup (`N1-R4`). |

## Notes

`N19-R3` and `N19-R5` are the two rows an implementation is most likely to get
wrong while trying to be helpful, and they fail the same way: a surface that
reads only a checksum, or only a count of what is configured, cannot tell a
decision from a defect. Both render as something to fix, and both offers ask the
operator to undo something they chose on purpose.
