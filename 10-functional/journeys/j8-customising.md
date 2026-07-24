# J8 — Customising the stack

**Status:** Accepted · **Audience:** Operator

**Exercises:** [F1](../features/f-extensibility/f1-customisation.md) ·
[C9](../features/c-trust/c9-drift.md)

---

## The journey

```
$ git clone https://github.com/lemonfiber/media-stack ~/dev/media-stack
$ vim ~/dev/media-stack/compose.yml        # add a service
$ vim ~/dev/media-stack/stack.toml         # declare it
$ lemonfiber up tv --stack-dir ~/dev/media-stack

  ✓ manifest valid    schema_version 1 · 20 services · 10 forms
  ✓ 8 services healthy
```

lemonfiber validates the fork's manifest contract and operates it. It has no
opinion about the contents beyond the contract.

## Who this is for, and why they matter disproportionately

The experienced operator evaluates the project publicly, answers questions in
forums, and is the person newcomers ask for advice. Their objection — *"it hides
what's actually happening"* — kills adoption among exactly the audience the
product is built for.

They're also right to be suspicious. A tool that wraps a system opaquely, then
breaks or is abandoned, leaves its users with something they can't operate.

## The guarantee underneath everything

```
$ cd ~/dev/media-stack
$ docker compose --profile search --profile usenet --profile tv up -d
```

**The stack runs with no lemonfiber binary anywhere** (`F1-R1`).

This is the load-bearing property. Everything else in this journey is
convenience; this is what makes adopting lemonfiber a *reversible* decision, and
therefore a low-risk one.

## Showing its work

```
$ lemonfiber up tv --dry-run

  docker compose \
    --project-name lemonfiber \
    --profile search --profile usenet --profile torrent \
    --profile tv --profile subs \
    up -d
```

Nothing is generated that the operator can't read (`F1-R2`). Debugging is
tractable because the command can be pasted into a shell.

## Adding a service requires no Rust

Three edits, all data:

1. A service entry in `compose.yml` with **exactly one** profile.
2. A manifest entry — ports, health endpoint, description.
3. Inclusion in whichever forms should carry it.

No lemonfiber change, no release (`F1-R5`). This is the direct payoff of
[ADR-0002](../../00-overview/decisions/0002-profiles-and-forms.md) keeping forms
as data rather than code.

For a service lemonfiber doesn't know, lifecycle and status work generically;
features needing specific knowledge — seeding, queue health — report as
unsupported for it rather than failing (`F1-R10`, `F1-R11`).

## Editing in place instead of forking

Files lemonfiber materialises can be edited directly. Modifications are detected
by content and **never silently overwritten** on upgrade — a diff is shown and
the operator chooses (`F1-R4`).

Similarly, hand-tuning a service's settings is preserved rather than reverted by
the next seed (`C9-R4`). Tuning worth keeping can be adopted into the baseline so
it survives rebuilds too (`C9-R6`).

## Opting out entirely

A service or configuration area can be marked **unmanaged**: lemonfiber reports
its state but never writes to it, and stops reporting drift for it (`F1-R7`,
`F1-R8`).

Taken to its limit, this is a stack lemonfiber only observes.

## Where it goes wrong

| Situation | Behaviour |
|-----------|-----------|
| Manifest invalid | Refused, naming the specific violation and location — **all violations in one pass**, not one per run (`F1-R9`) |
| Unsupported schema version | Refused, naming both versions |
| Fork breaks the single-mount rule | Consequence reported; **not refused**. It's their system (`F1-R13`) |
| Operator removes a service lemonfiber uses | Reports which features become unavailable; doesn't refuse |
| Scripting against output | Machine-readable output is a stable, versioned interface (`F1-R12`) |

## Related

- [F1 Customisation](../features/f-extensibility/f1-customisation.md)
- [C9 Drift detection](../features/c-trust/c9-drift.md)
- [ADR-0001](../../00-overview/decisions/0001-docker-compose-as-engine.md) · [ADR-0002](../../00-overview/decisions/0002-profiles-and-forms.md) · [ADR-0005](../../00-overview/decisions/0005-embedded-stack-assets.md)
