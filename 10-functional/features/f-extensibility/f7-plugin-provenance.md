---
id: F7
title: Plugin provenance
kind: feature
area: F
audience: operator
status: draft
maturity: planned
priority: P1
labels: [extensibility, ux, verification]
requires: [F3, F6, E4]
relates: [F4, F5, C9, G2]
---

# F7 — Plugin provenance

**Status:** Draft · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Keep *"why did my stack do that?"* answerable once plugins can change things.

A plugin may add a service, take over a capability, rewrite wiring and override bundled
behaviour. Every one of those makes the stack less obviously the product of the bundled
defaults and the operator's own choices. Without something deliberate, the cost lands six
months later on somebody reading a setting they do not remember choosing, in a stack they
no longer fully recognise, with no thread back to the plugin that set it.

Four mechanisms carry that thread, and they are deliberately redundant, because they fail
in different ways. A record answers *what happened*. Attribution at the point of reading
answers *where did this value come from* without requiring anybody to have thought to ask.
A single read answers *what have I installed and what did each one do*. And a declaration
answers all three **before** installing rather than after.

## Behaviour

### What a plugin changed is on the record

Every change a plugin makes is journalled exactly as an apply or a reconfigure is: what
changed, from what to what, when, and which operation made it — the operation being the
plugin, named. It follows that a plugin's changes appear in the history, are classified by
the rollback layer as whole, partial or irreversible, and can be put back.

No second mechanism is built for this. A plugin change is a change.

### Every value says where it came from

Wherever a setting, a wiring or a check is shown, it says whether it came from the bundle,
from the operator, or from a named plugin. Not in a separate view an operator has to think
to open — beside the value, so that reading it and reading its origin are the same act.

This is the mechanism that helps the person who did not know to ask. The other three
require somebody to already suspect a plugin is involved.

### One read says what each plugin is doing

`lemonfiber plugins` lists what is installed and, for each: where it came from, whether it
was reviewed, what capabilities it claims and fills, what it added, what it substituted,
what it overrides, which hosts it reaches, which secrets it holds, and when it was
installed. One place to look when something is surprising.

### The blast radius is declared before it happens

A plugin declares its overrides in its manifest, so the rehearsal can state the full extent
of what it will change before anything is written — and touching anything undeclared is a
validation failure rather than a discovery. The other three mechanisms explain a stack that
has already changed; this one is the only one that can stop a change the operator would not
have agreed to.

### Nothing a plugin holds is exempt from the ordinary account

A plugin's secrets appear on the credentials surface with everything else — what each is,
what uses it, where it lives, attributed to the plugin, and never its value. A plugin's
hosts appear in the account of what leaves this machine, attributed the same way. Plugins
do not get their own parallel surfaces; they get their own column in the existing ones.

## States

| State | Meaning |
|-------|---------|
| `bundled` | The value is lemonfiber's own default |
| `operator` | The value was set by the operator |
| `plugin` | The value was set by a named plugin |
| `overridden` | A bundled value that a named plugin has replaced; both the current and the bundled value are readable |
| `orphaned` | A value a plugin set that is still in force after the plugin was removed, reported rather than hidden |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| An operator edits a value a plugin set | The value becomes the operator's; the plugin's original is kept as what a removal would restore, and the removal refuses it as drift. |
| Two plugins would override the same value | Refused at install; there is no last-writer state to attribute. |
| A plugin is removed but a value it set survives | Report it as orphaned, naming the plugin that set it. A value with no owner is worse than one with a dead owner named. |
| A plugin is uninstalled and reinstalled | The new installation's changes are its own; the history keeps both, because they are two runs. |
| A value's origin cannot be determined | Say unknown rather than guessing bundled. A wrong attribution is worse than an absent one. |
| A plugin holds a secret | It appears on the credentials surface attributed to the plugin, never with its value. |
| A plugin reaches a host | It appears in the account of what leaves this machine, attributed to the plugin. |
| The plugins read is asked for on a machine with none | Answer with an empty list and say so, rather than with nothing. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F7-R1** | Every change a plugin makes MUST be journalled in the same record as any other change, with the plugin named as the operation. |
| **F7-R2** | A plugin's changes MUST appear in the change history and MUST be classified by the rollback layer like any other change. |
| **F7-R3** | Wherever a setting, wiring or check is shown, its origin — bundled, operator, or a named plugin — MUST be shown beside it. |
| **F7-R4** | A value a plugin has overridden MUST expose both the value in force and the bundled value it replaced. |
| **F7-R5** | A single read MUST list every installed plugin with its origin, whether it was reviewed, what it claims and fills, what it added, substituted and overrides, the hosts it reaches, the secrets it holds, and when it was installed. |
| **F7-R6** | A plugin MUST declare every bundled thing it will override, and the rehearsal MUST state the full extent before anything is written. |
| **F7-R7** | Changing anything a plugin did not declare MUST fail validation. |
| **F7-R8** | A plugin's secrets MUST appear on the credentials surface attributed to the plugin, and MUST NOT expose their values. |
| **F7-R9** | A plugin's declared hosts MUST appear in the account of what leaves this machine, attributed to the plugin. |
| **F7-R10** | A value left in force by a removed plugin MUST be reported as orphaned, naming the plugin that set it. |
| **F7-R11** | An origin that cannot be determined MUST be reported as unknown and MUST NOT be reported as bundled. |
| **F7-R12** | Plugins MUST NOT have parallel surfaces of their own for secrets, outbound traffic or settings; they MUST appear on the existing ones. |

## Related

- [E4 Rollback](../e-maintenance/e4-rollback.md) — the record a plugin's changes are written into
- [F6 Plugin lifecycle](f6-plugin-lifecycle.md) — when the declaration is stated and checked
- [F5 The plugin catalogue](f5-plugin-catalogue.md) — where origin and reviewed-ness come from
- [C9 Drift detection](../c-trust/c9-drift.md) — how an operator's own edit is told apart from a plugin's
