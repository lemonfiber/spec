---
id: N28
title: Finding your way
kind: feature
area: N
audience: operator
status: accepted
maturity: building
priority: P2
labels: [mobile, ux]
requires: [N1, N2, N27]
relates: [N3, N4, N25, G2, G3]
---

# N28 — Finding your way

**Status:** Accepted · **Audience:** Operator · **Area:** N — Companion

---

## Purpose

The app has more screens than a bottom bar can hold. Four of them — health, what
runs, updates and repairs — are the readings an operator returns to, and they are
the bar. Everything else was a list of rows at the foot of the health screen, each
named by a sentence, which made health a menu and made the menu hard to read.

This page is how an operator finds their way: a bar for the four readings, a menu
for everything else, the stack's name at the top to switch between stacks, and
labels short enough to read at a glance by somebody who does not run servers for a
living.

## Behaviour

### The top bar

Every screen about a stack has a top bar with a menu button and the stack's name.
Tapping the name opens the list of stacks as a sheet: each with a glyph and a word
or two for how it stands, the current one marked, and *Add a stack* at the end.
Choosing one opens it on the tab the operator last used there (`N27-R16`).

Signing in to a stack shows the name, which opens the same sheet, and the menu, so the
stack's settings and App settings stay in reach while the stack will not let the
operator in. It shows no tabs until the stack has let the operator in.

### The bottom bar

Four tabs: **Health**, **Services**, **Updates**, **Repairs**. A tab holding
something new carries a mark (`N27-R21`). The tab for the screen on view is shown as
current, and so is the tab a screen belongs to: what one service is doing and what it
has been saying belong to **Services**, and mark it. A screen reached from the menu
shows none as current.

### The menu

The menu opens from the side. At its top is the stack, with *Switch stack*, and
**What's new** with how many items are new (`N27-R20`). Under it, every other screen
about the stack, in five groups:

| Group | Items |
|-------|-------|
| **Household** | Requests · Allowance · Stuck downloads · Follow a download · View as member |
| **Access** | Invite someone · Front door · Watch apps · Passwords · Pair a phone |
| **Machine** | Storage · Backups · After a restart · Already installed · Other programs · About · Uninstall |
| **Settings** | General · Quality · Connections · Plugins · Bandwidth · Outgoing traffic · Alerts · History · Sources |
| **Help** | Get help · Glossary · Services explained |

At its foot, the stack's own settings and **App settings** (`N27-R14` to `N27-R18`).
Every item carries an icon beside its label, never in place of it.

*Allowance* is the operator's reading of what each member of the household may ask
for and how much of it is left, on a screen of its own with the menu like every
other.

*View as member* opens the member's application as a member with the household's
default access and allowance would see it, marked as a preview (`N2-R25`). It is
not an operator screen, and it is in the menu all the same: the member's app has no
menu of its own, so it opens over the operator's screens and the platform's way back
returns to them (`N28-R13`). The preview's mark carries a way back as well, because a
member's screens offer nothing else that leads to the operator's (`N28-R14`).

A screen that is one step of something begun elsewhere is reached from where it
begins, not from the menu: taking a copy, putting the configuration back, and
guarding where the data is kept while the operator watches.

A screen that details one thing another screen shows is reached from that screen:
*Versions*, which is what *About* says is running, told release by release. Put in
the menu beside *About* it would be a second item for one question.

Until the app has *What's new* and the settings screens (`N27-R14` to `N27-R20`),
their items are in the menu all the same, and opening one says it is not in this
version of the app yet.

### Health is about health

The health screen shows how the stack stands and what is wrong — and nothing that
belongs in the menu. The first thing on it, where anything is new, is *What's new*.

### Short words

A tab, a menu item, a button and a section heading name what they open or do, in a
word or a few. A sentence is for explaining, beside a label, and never is one. The
words are the plain ones (`G2-R3`, `G2-R15`): *Problems* rather than *findings*,
*Passwords* rather than *credentials*, *Storage* rather than *disk*.

## States

| State | Meaning |
|-------|---------|
| No stack | First run: no top bar, no menu, no tabs (`N1-R35`). |
| Locked | Nothing of the menu, the bar or the stack list is drawn (`N4-R24`). |
| One stack | The stack's name still opens the sheet, which offers *Add a stack*. |
| Something new | A mark on the tab that holds it, and a count on *What's new*. |

## Edge cases

- **A screen the stack is too old to offer.** Its menu item stays, and opening it
  says what would provide it (`N1-R30`); it is not taken out of the menu.
- **A stack that cannot be reached.** The menu and the bar work as ever, and every
  screen shows what it last knew and when (`N27-R7`).
- **A long stack name.** Shortened in the top bar with its whole name read to a
  screen reader; shown whole in the sheet.
- **Text scaled up by the phone.** Labels wrap rather than being cut off, and the
  menu scrolls (`N4-R14`).

## Requirements

| ID | Requirement |
|----|-------------|
| **N28-R1** | Every operator screen about a stack MUST have a top bar holding a control that opens the menu and the stack's name. |
| **N28-R2** | The stack's name in the top bar MUST open the list of stacks, each with its glyph and a short word for how it stands and the current one marked, and the list MUST offer adding a stack. |
| **N28-R3** | Choosing a stack from that list MUST open it on the tab the operator last used for it (`N27-R16`). |
| **N28-R4** | The bottom bar MUST hold exactly four tabs — Health, Services, Updates and Repairs — and MUST mark as current only the tab whose screen is on view, or the tab the screen on view belongs to; what one service is doing and its log belong to Services. |
| **N28-R5** | Every operator screen about a stack that is not one of the four tabs, a screen belonging to one of them (`N28-R4`), one step of something begun on another screen, or a screen detailing one thing another screen shows MUST be reachable from the menu in the groups this page names, and MUST NOT be reached only from another screen's body. The menu's **Household** group MUST also hold *View as member*, which opens the member's application as `N2-R25` describes. |
| **N28-R6** | The menu MUST begin with the current stack and *What's new* with its count, and MUST end with the stack's settings and App settings. Where the phone holds no session for the current stack, *What's new* MUST NOT be offered: there is nothing on the stack it can read. |
| **N28-R7** | Every menu item MUST carry an icon and a label, and the icon MUST NOT stand in for the label (`N4-R21`). |
| **N28-R8** | The health screen MUST show how the stack stands and what is wrong, MUST offer *What's new* first where anything is new, and MUST NOT list the menu's items. |
| **N28-R9** | A tab, a menu item, a button and a section heading MUST name what it opens or does in at most three words, and MUST NOT be a sentence; a sentence MAY explain beside it (`G2-R15`). |
| **N28-R10** | A screen the connected stack does not offer MUST keep its menu item, and opening it MUST say what would provide it (`N1-R30`); a screen this version of the app does not have yet MUST keep its menu item too, and opening it MUST say so. |
| **N28-R11** | With no stack paired there MUST be no menu, top-bar switcher or bottom bar (`N1-R35`), and while the app is locked none of them MUST be drawn (`N4-R24`). Signing in to a stack MUST show the switcher and the menu, and MUST NOT show the bottom bar. |
| **N28-R12** | Labels MUST wrap rather than be cut off at the phone's text size, and a shortened stack name MUST be read whole to a screen reader (`N4-R14`). |
| **N28-R13** | A screen opened over another MUST offer the platform's own way back: its back control and, on iOS, the edge swipe. A screen with nothing beneath it MUST NOT offer one. |
| **N28-R14** | Every screen of the member's application opened as a preview (`N2-R25`) MUST carry, in the mark that says it is a preview, a control that returns to the operator's screen it was opened from, as well as the platform's own way back (`N28-R13`). |

## Notes

**The labels are the ones in the table above**, approved with the navigation
wireframe on 2026-09-29. Changing one is a change to this page. The screens they open
keep their titles for now; bringing every title, heading and button into line with
`N28-R9` is the plain-language pass that follows.

**The household's surface is not this page.** A member finds their way by four
tabs and no menu ([N3](n3-household-companion.md), `N3-R19`).

## Related

- [N27](n27-what-the-phone-keeps.md) — where the app reopens, What's new, the settings screens
- [N1](n1-companion-app.md) — first run, capabilities, multiple stacks
- [N2](n2-operator-companion.md) — the operator's screens the menu reaches
- [N4](n4-native-integration.md) — the lock, text size and screen readers
- [G2](../g-ux/g2-plain-language.md) — one word for one thing
- [G3](../g-ux/g3-accessibility.md) — accessibility
