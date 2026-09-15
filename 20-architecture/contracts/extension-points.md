# Contract: `extension-points.json`

**Status:** Draft

The published set of places a plugin may extend lemonfiber itself, so that a
manifest declaring at one lemonfiber does not have is refused by name rather than
by parse failure.

**Satisfies:** [F4-R15](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R16](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R17](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R20](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R21](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F4-R22](../../10-functional/features/f-extensibility/f4-capabilities.md),
[F3-R26](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R27](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R28](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[F3-R30](../../10-functional/features/f-extensibility/f3-stack-manifests.md),
[C1-R15](../../10-functional/features/c-trust/c1-diagnostics.md)

---

## Why this file exists

[`F4-R15`](../../10-functional/features/f-extensibility/f4-capabilities.md)
asks for the same treatment the capability vocabulary gets, pointed at a second
surface: the places a plugin may extend **lemonfiber** rather than the stack must
be published, versioned and owned here, and a manifest declaring at a point this
build does not publish must be refused *by naming that point and listing the ones
that exist*.

The reason is `F4-R14`'s, and it is not tidiness. A declaration skipped because
nothing recognised it leaves a plugin whose stated behaviour is narrower than its
actual one — which is undetected reach rather than a missing feature. A
contribution that quietly disappears from a doctor run is worse than one that
fails, because a stack looks healthy for the wrong reason.

## What a point is

[`F3-R26`](../../10-functional/features/f-extensibility/f3-stack-manifests.md)
fixes the shape and this only publishes it: **a contribution is an entry in a
register some engine already enumerates, never an interpreter of its own.** An
extension point is therefore not a hook and not a callback. It is a register that
already exists, already has bundled rows in it, and already has one evaluator —
and the point names the place a plugin may put another row.

That is what keeps `F3-R6` intact without an argument. Nothing contributed is
executed because there is nothing for contributed code to *be*: the row is data
and the engine that reads it is lemonfiber's, unchanged.

## The artefact

```json
{
  "extension_points_version": 1,
  "points": [
    {
      "name": "doctor.check",
      "summary": "A check the doctor runs, alongside the bundled ones.",
      "register": "the diagnostics register",
      "engine": "the check engine — independent, bounded, four verdicts, a remedy on anything that does not pass",
      "row": {
        "required": ["id", "title", "category", "request", "expect", "why", "fixture"],
        "optional": ["timeout_s", "service"],
        "bounds": { "timeout_s": { "min": 1, "max": 30, "default": 10 } },
        "enums": { "category": ["environment", "storage", "network", "vpn", "credentials", "services", "providers", "queue", "config"] }
      },
      "occupied": ["environment.engine", "storage.space", "vpn.egress-match", "…"]
    },
    {
      "name": "doctor.remedy",
      "summary": "What to do about a contributed check that did not pass.",
      "register": "the remedies a finding carries",
      "engine": "the error renderer — rendered, never executed",
      "row": {
        "required": ["id", "for", "action", "why"],
        "optional": ["detail"]
      },
      "occupied": []
    }
  ]
}
```

| Field | Notes |
|-------|-------|
| `extension_points_version` | Monotonic integer. Advanced by removing a point or narrowing a row; adding a point does not move it. |
| `points[].name` | What a contribution declares `at`. Unique. |
| `points[].register` | The register a row joins, in the operator's words |
| `points[].engine` | What already reads that register, and on what terms |
| `points[].row` | Exactly what a row carries: which fields are required, which are optional, the bounds on each bounded one, and the closed sets |
| `points[].occupied` | The identities the bundled rows already hold. **Generated from the register**, not written here. |

### `occupied` is what makes `F4-R17` a refusal rather than a hope

`F4-R17` forbids a plugin replacing, re-ordering or suppressing a bundled check
or the remedy it carries, and requires a contribution that would to be *refused,
naming what it collided with*. Naming it takes knowing it, so the identities are
published.

Two rules then do the work between them, and they are deliberately belt and
braces:

1. `F4-R16` requires every contributed identity to be namespaced with the
   declaring plugin's id, and a bundled identity never carries a colon. So a
   collision cannot be expressed.
2. A contribution naming an occupied identity anyway — in `id`, or in the `for`
   of a remedy — is refused, naming both.

The second exists because the first is a property of two naming conventions, and
a rule that holds only while two conventions stay disjoint is a rule with an
undefended edge. Standing in for something bundled is a real requirement with a
real home
([F9](../../10-functional/features/f-extensibility/f9-bundled-capabilities.md)),
where it is the operator's recorded choice rather than a manifest's assertion.

Like `declared_by` in the [capability vocabulary](capability-vocabulary.md), this
is read out of the register at generation time rather than restated, so a bundled
check that is renamed moves the artefact rather than leaving a stale name a
contribution could take.

## `doctor.check`

A row in the register [`C1`](../../10-functional/features/c-trust/c1-diagnostics.md)
enumerates. `C1-R15` already has a plugin's declared proof running there,
attributed to the plugin; this generalises that one case rather than opening a
door beside it.

| Field | Notes |
|-------|-------|
| `id` | `<plugin-id>:<name>`. What the verdict is reported against, and what `lemonfiber doctor --only` takes. |
| `title` | The one-line summary of what was checked (`Finding.title`) |
| `category` | Which family it is narrowed to. One of the nine the doctor recognises. |
| `request` | `method` and `path` on the plugin's own service. The same shape a proof takes. |
| `expect` | What the answer must be. The same vocabulary a proof's expectation uses, and the same rule: a status alone is not enough unless it is a refusal. |
| `why` | Why this is worth checking. A check nobody can justify is one nobody will maintain. |
| `fixture` | The recorded response the check is proved against in CI (`F10-R4`) |
| `timeout_s` | Bounded, and bounded here rather than by the plugin's opinion (`C1-R7`) |
| `service` | Which service the finding is about, where it is about one. Defaults to the plugin's own. |

What it inherits from the engine, and may not vary: independence (`C1-R4`), a
bounded timeout reporting `unverified` on expiry (`C1-R7`), the four verdicts with
`unverified` distinct from `pass` (`C1-R3`), an error inside it reported as *this
plugin's check error* rather than as a finding about the stack (`C1-R8`,
`C1-R15`), and attribution wherever it appears (`F3-R27`).

**A contributed check asks the plugin's own service and nothing else.** There is
no field for a host, so a check cannot be pointed at another service, at the
machine, or off it. A plugin wanting to say something about a service it did not
install is asking to speak for somebody else's software, which is what the
attribution rule exists to prevent.

## `doctor.remedy`

`C1-R2` requires every non-passing result to carry a remedy, and
[`G4-R1`](../../10-functional/features/g-ux/g4-error-model.md) fixes its shape.
A remedy is a row of its own rather than a field on the check for the reason
`G4-R12` gives: where several causes are plausible they are listed by likelihood
rather than asserted as certain, and a single field cannot carry a list somebody
ordered.

| Field | Notes |
|-------|-------|
| `id` | `<plugin-id>:<name>` |
| `for` | The `id` of a check **this same plugin declared**. Naming a bundled check is refused, naming both (`F4-R17`). |
| `action` | What to do, in the imperative. The `Remedy.action` the renderer already has. |
| `why` | What the finding means, so the action is not a ritual |
| `detail` | The technical half, which must not lead (`G4-R4`) |

**Rendered, never executed** (`F3-R29`). A remedy is text. A contribution that
would act on the operator's system is refused as a remedy: the ordered calls such
a repair would make are
[F8](../../10-functional/features/f-extensibility/f8-recipes.md)'s, and a second
way to make them here would be the duplicate mechanism `F3-R26` exists to refuse.

Every check a plugin declares must carry at least one remedy, because a finding
with no remedy is a dead end and `C1-R2` does not exempt a contributed one.

## What is not a point, and why each is absent

| Asked for | Answer |
|-----------|--------|
| A dashboard panel | The six sections are fixed (`B3-R2`) and the renderer has no panel vocabulary to declare into, so a declared panel would need something new to read it — and a new interpreter is contributed code wearing a data costume. A plugin's checks become findings, and the summary is computed from findings (`G7-R2`). |
| A command | The command surface is generated from the types the binary parses (`ARCH-R68`), so a declared verb would be a second source for something that has one. A contributed check needs no verb: `lemonfiber doctor --only <id>` reaches it the day it is installed (`C1-R6`). |
| A repair that acts | Not missing an interpreter — it is a recipe, and recipes are declared as recipes. |
| A capability in the core vocabulary | Not this register. A plugin claims a core capability by binding its probes ([capability-vocabulary](capability-vocabulary.md)) and declares its own namespaced ones, which are inert until something asks. |

A point is added by publishing it here, which is a change made once for
everybody, rather than by widening the format for one plugin
([F3](../../10-functional/features/f-extensibility/f3-stack-manifests.md)).

## Withdrawal

`F3-R30` requires a plugin's contributions to go with it, and lemonfiber with no
plugin installed to answer exactly as one that never had any. Rows are held
against the plugin that declared them rather than merged into the bundled
register, so removal is the removal of that plugin's rows and nothing else — and
a doctor run afterwards enumerates exactly what it enumerated before.

## Validation

| Rule | Failure |
|------|---------|
| Every `[[contribution]]` names an `at` this build publishes | Point named, with the ones that exist |
| Every `id` is namespaced with the declaring plugin's id | Identity named, with the namespace required |
| No `id` or `for` names an occupied identity | Both named |
| Every field the point requires is present | Field and point named |
| No field outside the point's set | Field named, with the permitted set |
| Every value in a closed set is one of them | Value named, with the set |
| Every bounded value is within its bounds | Value named, with the bounds |
| Every `doctor.remedy` names a `doctor.check` this manifest declares | Both named |
| Every `doctor.check` carries at least one `doctor.remedy` | Check named |
| Every `doctor.check` names a recorded response that exists | Path named |

## Requirements

| ID | Requirement |
|----|-------------|
| **ARCH-R111** | The extension points MUST be published as one machine-readable artefact generated from the registers they name, MUST carry their own generation, and regenerating them MUST produce no diff, with CI failing if it does. |
| **ARCH-R112** | The identities the bundled rows of each register hold MUST be generated from that register into the published artefact, so a contribution colliding with one can be refused by naming it. |
| **ARCH-R113** | A contribution MUST declare the extension point it is made at, and one naming a point this build does not publish MUST be refused by naming that point and listing those that exist, rather than by parse failure. |
| **ARCH-R114** | A contributed row MUST carry every field its point declares required and none outside its point's set, MUST satisfy that point's closed sets and bounds, and a violation MUST be refused by naming the field and the point. |
| **ARCH-R115** | A contributed check MUST ask only the declaring plugin's own service, and the manifest MUST have no field by which a check could name another host, another service or the machine. |

## Related

- [F4 The capability vocabulary](../../10-functional/features/f-extensibility/f4-capabilities.md) — `F4-R15`, the rule this answers
- [F3 Plugin manifests](../../10-functional/features/f-extensibility/f3-stack-manifests.md) — `F3-R26`–`F3-R30`, what a contribution is and what it may not be
- [C1 Diagnostics](../../10-functional/features/c-trust/c1-diagnostics.md) — the register a contributed check is a row in
- [C3 Auto-remediation](../../10-functional/features/c-trust/c3-auto-remediation.md) — the guided half a contributed remedy joins
- [G4 Error & remedy model](../../10-functional/features/g-ux/g4-error-model.md) — the shape a remedy is written in
- [capability-vocabulary](capability-vocabulary.md) — the other published vocabulary, and the same treatment
- [plugin-manifest](plugin-manifest.md) — where a contribution is declared
