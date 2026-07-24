# `cli` — command reference

**Status:** Accepted

Every subcommand and its non-interactive contract. This is the surface that makes
`lemonfiber` scriptable — and the guarantee that the TUI is never the only way to
do anything ([F1-R6](../10-functional/features/f-extensibility/f1-customisation.md)).

**Implements:** [G1](../10-functional/features/g-ux/g1-interface-tiers.md),
[F1](../10-functional/features/f-extensibility/f1-customisation.md).

---

## Global flags

| Flag | Effect |
|------|--------|
| `--stack-dir <path>` | Operate an external stack instead of the embedded one (`F1-R3`) |
| `--json` | Machine-readable output with `api_version` (`F1-R12`, `ARCH-R9`) |
| `--dry-run` | Print what would happen; change nothing (`F1-R2`) |
| `--yes` | Assume yes to confirmations — required for unattended runs (`A2-R13`) |
| `--no-color` | Disable colour; `NO_COLOR` honoured equally (`G3-R2`) |
| `--stack-host <ctx>` | Operate a remote Docker context (`B6-R4`) |

## Commands

### Lifecycle

| Command | Does |
|---------|------|
| `lemonfiber up <form…>` | Start a form, or the union of several (`B1-R5`). Health-gated (`B2-R1`). |
| `lemonfiber down [form]` | Stop everything, or one form's exclusive services |
| `lemonfiber restart <svc…>` | Restart services without touching the rest |
| `lemonfiber ps` | Service state — honest status, not "Up" (`B2-R10`) |
| `lemonfiber logs [svc…]` | Stream logs; `--follow`, `--since`, `--severity` |
| `lemonfiber pull [--check]` | Pull updates; `--check` reports without applying (`E1-R2`) |

### Setup & configuration

| Command | Does |
|---------|------|
| `lemonfiber init` | Run setup. Interactive by default; flag-driven for automation |
| `lemonfiber config get/set <key>` | Read or change one setting (`A4-R1`) |
| `lemonfiber config show` | Full configuration, secrets redacted |
| `lemonfiber reconfigure <area>` | Revisit a setup decision (`A4`) |
| `lemonfiber migrate` | Survey and adopt an existing stack (`A5`) |

### Health & wiring

| Command | Does |
|---------|------|
| `lemonfiber doctor [--only <cat>]` | Run checks; `--disruptive` opts into disturbing ones (`C1-R5`) |
| `lemonfiber doctor --fix` | Apply remediations; report-only without it (`C3-R11`) |
| `lemonfiber seed` | Wire services together. Idempotent (`D1-R2`) |
| `lemonfiber support-bundle` | Produce a redacted diagnostic archive (`C4`) |

### Maintenance

| Command | Does |
|---------|------|
| `lemonfiber backup` | Quiesced config backup (`E3-R1`) |
| `lemonfiber restore <archive>` | Restore, whole or per-service (`E3-R6`) |
| `lemonfiber rollback <change>` | Undo one journaled change (`E4-R2`) |
| `lemonfiber history` | Browse the change journal (`E4-R11`) |
| `lemonfiber self-update` | Update the binary, or defer to the package manager (`E2-R1`) |
| `lemonfiber uninstall` | Tiered removal (`A6`) |

### Household

| Command | Does |
|---------|------|
| `lemonfiber invite <name>` | Create an invitation with a link and QR (`D6-R4`) |
| `lemonfiber household` | List and manage members |

### Interface

| Command | Does |
|---------|------|
| `lemonfiber` | TUI at a terminal; help when piped (`G1-R3`) |
| `lemonfiber ui` | Serve the web UI; loopback by default (`G1-R5`, `C6-R1`) |
| `lemonfiber forms [--explain <form>]` | List forms; explain a closure (`B1-R7`) |
| `lemonfiber status` | One-shot health summary (`G7-R1`) |

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
$ echo | lemonfiber init
error: setup requires input and stdin is not interactive
  provide answers via flags, or run in a terminal
  see: lemonfiber init --help
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

- [cli.md](cli.md) · [cli-tui.md](cli-tui.md)
- [G1](../10-functional/features/g-ux/g1-interface-tiers.md) · [F1](../10-functional/features/f-extensibility/f1-customisation.md)
- [versioning](../20-architecture/contracts/versioning.md) — the output contract
