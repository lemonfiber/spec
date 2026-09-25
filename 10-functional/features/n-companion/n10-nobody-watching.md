---
id: N10
title: What the stack does when nobody is watching
kind: feature
area: N
audience: operator
status: accepted
maturity: planned
priority: P3
labels: [mobile, network, notifications, ux]
requires: [N1, G8]
relates: [B5, B10, D10, N2, N4]
---

# N10 — What the stack does when nobody is watching

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

A media stack is mostly unattended. It reaches out to other people's servers, it
uses a line somebody else in the house is also using, it decides what is worth
waking a person for, and it runs things that must outlive a terminal.

All four are decisions with consequences, all four are the operator's to make,
and none of them has a surface away from the machine.

[N4](n4-native-integration.md) owns notifications **arriving** — what a push may
contain, and that the app raises none of its own (`N4-R11`). This owns choosing
what the stack tells anybody about in the first place, which is a different
decision made at a different time.

## Behaviour

### What lemonfiber sends is not what the services send

The contract keeps these apart: connections the product makes on the operator's
behalf, and connections the installed services make on their own. **That
distinction is the whole of the privacy answer**, and an app that merged them
into one list would be taking responsibility for other people's software or
disclaiming its own.

Each is shown as what it is.

### Every outbound connection carries what turns it off

The contract names a switch for each connection lemonfiber makes. A privacy
screen that lists what leaves the machine without saying how to stop it is a
disclosure, not a control.

Where a connection has a cost to turning it off, that cost is stated with it.

### Capacity that was measured is not capacity that was claimed

The line's capacity is either what somebody declared or what the stack observed,
and the contract says which. An operator deciding a cap on a declared figure is
deciding on a guess, and has a right to know that is what they are doing.

### Whether it goes through the tunnel is part of the answer

Traffic through the VPN and traffic beside it are different facts about the
household, and the contract distinguishes them. So does this.

### A cap does one of three things, and the app says which

Reaching a monthly cap pauses, throttles, or continues. These produce completely
different evenings, and *you have reached your cap* without which one is not an
answer.

### An alert preset is a decision about being woken

What the stack tells somebody about is a preset with a meaning and a set of
exceptions the operator has made. Both are shown: a preset name alone does not
say what will happen at three in the morning, and the exceptions are what the
operator has already decided they do not want.

### A rehearsed alert is not an alert

Alerts can be rehearsed, and a rehearsal is labelled on the same terms as
everywhere else (`N6-R1`). Somebody who believes they received a real alert
because the app did not say otherwise has been misled about their own stack.

### A long-running command says what it guarantees and what is missing

Some guarantees are made by something that has to keep running, and both the
guarantee and what is absent are carried. An operator away from the machine
checking whether the thing that stops the stack writing to a vanished disk is
actually running is asking a reasonable question, and it is answerable.

## States

| State | Meaning |
|-------|---------|
| Open | A connection is allowed. Its purpose, destination and switch are shown. |
| Closed | Turned off, with what that costs. |
| Within cap | Under the monthly figure, with how much is taken. |
| At cap | Reached, and what the stack does about it — pause, throttle or continue. |
| Rehearsed | An alert run that told nobody, labelled as such. |
| Unknown | The connections, the line or the alerts could not be read. Never rendered as none. |

## Edge cases

- **A service making a connection lemonfiber did not ask for.** Shown under
  *theirs*, and not presented as the product's doing.
- **An observed capacity that has only been observed once.** The source is said;
  the app does not present it as established.
- **A cap with no monthly figure set.** Distinguished from a cap of zero.
- **A long-running command that is defined but not running.** That is the state
  the operator most needs and is shown as its own answer, not as absent.

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **N10-R1** | Connections lemonfiber makes MUST be shown apart from connections the installed services make, and the two MUST NOT be merged into one list. |
| **N10-R2** | Each connection lemonfiber makes MUST be shown with its purpose, its destination and the switch that turns it off. |
| **N10-R3** | Where turning a connection off has a cost, that cost MUST be shown with it. |
| **N10-R4** | The line's capacity MUST say whether it was declared or observed. |
| **N10-R5** | Whether traffic passes through the tunnel MUST be shown where the contract carries it. |
| **N10-R6** | Reaching a cap MUST say which of pause, throttle or continue the stack does. |
| **N10-R7** | A cap with no figure set MUST be told apart from a cap of zero. |
| **N10-R8** | An alert preset MUST be shown with what it means and with the exceptions the operator has made. |
| **N10-R9** | A rehearsed alert MUST be labelled as a rehearsal (`N6-R1`), and MUST NOT be presented as an alert that was sent. |
| **N10-R10** | A long-running command MUST be shown with what it guarantees and what is missing, and one that is defined but not running MUST be shown as that rather than as absent. |
| **N10-R11** | The app MUST NOT raise alerts of its own here; what is configured is the core's (`N4-R11`). |
| **N10-R12** | Connections, capacity or alerts that could not be read MUST be told apart from there being none. |

## Related

- [N1](n1-companion-app.md) — connecting, parity, and what the app may claim
- [N4](n4-native-integration.md) — notifications arriving on the device
- [N6](n6-taking-a-copy.md) — what a rehearsal may not look like
- [G8](../g-ux/g8-privacy.md) — the privacy stance this renders
- [B5](../b-running/b5-notifications.md) — what the stack tells somebody about
- [B10](../b-running/b10-hosting.md) — guarantees made by something that keeps running
- [D10](../d-content/d10-bandwidth.md) — the line, and what uses it
