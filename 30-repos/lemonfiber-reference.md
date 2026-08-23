# `lemonfiber` — command reference

**Status:** Accepted

What the command line promises, whatever it grows next. This is the surface that makes
`lemonfiber` scriptable — and the guarantee that the TUI is never the only way to
do anything ([F1-R6](../10-functional/features/f-extensibility/f1-customisation.md)).

**Implements:** [G1](../10-functional/features/g-ux/g1-interface-tiers.md),
[F1](../10-functional/features/f-extensibility/f1-customisation.md).

---

## The commands are generated, not listed here

Every subcommand and flag is declared once, in the types the binary parses arguments
with. Repeating them here would be a second description of the same command line, and
two descriptions do not stay level — which is how a document comes to name commands
that were renamed away and miss ones that were added.

So the inventory lives where it cannot drift: `reference/commands.md` in the
[`lemonfiber`](https://github.com/lemonfiber/lemonfiber) repository, generated from
those declarations and checked against them by CI (`ARCH-R68`). Every command, its
flags and its help text are there, at the revision that produced them.

This document keeps the half that generation cannot produce: what an exit code means,
what happens when a command needs input and none is coming, what `--json` promises, and
the obligations below that any version of the command line has to satisfy.

## Exit codes

Meaningful and documented (`G1-R8`), because scripts depend on them:

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General failure |
| `2` | Usage error — bad flags or arguments |
| `3` | Preflight failed — Docker absent/unreachable, unsupported version |
| `4` | Health-gate timeout — started, but a service never became healthy |
| `5` | Validation failed — manifest, config, or credential |
| `6` | Would block on input in a non-interactive context (`G1-R13`) |
| `7` | Remote/context error |

Distinct codes so a script can branch on *why*, not just success versus failure.

## Non-interactive contract

Everything the TUI does has a flag equivalent (`F1-R6`). In a non-interactive
context (piped, CI, `--yes` absent where input is needed), commands **fail
naming the required flag** rather than blocking on stdin (`G1-R13`), exit `6`.

```
$ echo | lemonfiber setup
error: setup requires input and stdin is not interactive
  provide answers via flags, or run in a terminal
  see: lemonfiber setup --help
exit: 6
```

## `--json` output

```json
{
  "api_version": 1,
  "kind": "status",
  "data": {
    "health": "healthy",
    "services": [ … ],
    "vpn": { "state": "verified", "port": 51413 }
  }
}
```

Every payload carries `api_version` (`ARCH-R9`); additive changes don't bump it,
so a script pinning `== 1` keeps working across feature additions.

## Requirements

| ID | Requirement |
|----|-------------|
| **REPO-R10** | Every TUI action MUST have a non-interactive command equivalent. |
| **REPO-R11** | Exit codes MUST be documented and distinguish failure classes. |
| **REPO-R12** | Non-interactive invocation needing input MUST fail naming the flag, exit `6`, and MUST NOT block on stdin. |
| **REPO-R13** | `--dry-run` MUST be available on every state-changing command. |
| **REPO-R14** | `--json` output MUST carry `api_version` and be stable within a major version. |
| **REPO-R15** | `--stack-dir` and `--stack-host` MUST be accepted globally. |

## Related

- [lemonfiber.md](lemonfiber.md) · [lemonfiber-tui.md](lemonfiber-tui.md)
- [G1](../10-functional/features/g-ux/g1-interface-tiers.md) · [F1](../10-functional/features/f-extensibility/f1-customisation.md)
- [versioning](../20-architecture/contracts/versioning.md) — the output contract
- [component-model](../20-architecture/component-model.md) — why the inventory is generated
