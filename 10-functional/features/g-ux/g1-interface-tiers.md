---
id: G1
title: Interface tiers
kind: feature
area: G
audience: both
status: accepted
tracks: v1
milestone: M5
labels: [cli, tui, web, ux]
relates: [B6, C6, G3, G4]
---

# G1 — Interface tiers

**Status:** Accepted · **Audience:** Both · **Area:** G — Cross-cutting UX

---

## Purpose

Serve three different people through one program: someone scripting, someone at a
terminal, and someone who would rather not be at a terminal at all.

The stated goal is that *everyone* can use this. A terminal UI alone excludes the
audience most in need of help — the non-technical operator who can follow
instructions but for whom a shell is itself a barrier. A web UI alone loses the
operator working over SSH and anyone automating.

## Behaviour

### Three surfaces, one core

| Surface | Invocation | For |
|---------|-----------|-----|
| **CLI** | `lemonfiber up tv` | Scripting, automation, remote shells |
| **TUI** | `lemonfiber` | Interactive use at a terminal |
| **Web** | `lemonfiber ui` | Anyone who'd rather use a browser |

All three drive the same logic. A surface is a rendering, never a capability.

### Feature parity is a requirement, not an aspiration

**Every action is available from every surface**, with a stated exception for
things intrinsically unsuited to one — a live-refreshing dashboard has no
meaningful CLI form, so the CLI offers a point-in-time equivalent.

Parity is what stops the surfaces diverging into a "real" interface and a
crippled one — the usual fate of a GUI bolted onto a CLI.

### The default surface fits the situation

Bare `lemonfiber` opens the TUI when attached to a terminal, and prints help when
piped. It never blocks waiting for input that cannot arrive.

### The web UI is where the wizard shines

Setup is where the web UI earns its place. Form validation, inline explanation,
links to provider documentation, and a QR code for household invitations are all
substantially better in HTML than in a terminal — and setup is precisely where the
least technical operator is.

### Web UI is served on demand, not always

It runs when asked, bound to loopback by default, under
[C6](../c-trust/c6-web-security.md)'s policy. lemonfiber is not a daemon that
happens to have a CLI.

### CLI output is designed for both readers

Human-readable by default; machine-readable on request, as a stable versioned
interface ([F1](../f-extensibility/f1-customisation.md)). Exit codes are
meaningful and documented.

### The TUI degrades rather than demands

It works in a plain terminal without a true-colour palette, without a Nerd Font,
and at modest dimensions. Requiring a specific terminal setup would exclude
exactly the users this exists for.

## States

| State | Meaning |
|-------|---------|
| `cli` | Non-interactive invocation |
| `tui` | Interactive terminal session |
| `web-loopback` | Web UI on `127.0.0.1` |
| `web-lan` | Web UI on the LAN with authentication |
| `piped` | stdout not a terminal; machine-oriented behaviour |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Bare invocation with stdout piped | Print help; never open the TUI or block on input. |
| Terminal doesn't support required features | Degrade — ASCII borders, no colour — rather than refuse. |
| `NO_COLOR` set | Honour it ([G3](g3-accessibility.md)). |
| Web UI requested, port in use | Report the conflict and offer another port. |
| Web UI open while a CLI command runs | Both act on the same state; reflect changes live. Serialise lifecycle operations. |
| Browser cannot be opened automatically | Print the URL. Never fail because a browser couldn't be launched. |
| An action has no sensible form on a surface | State the equivalent explicitly rather than silently omitting it. |
| Very small terminal | Reduce by priority; state that the view is abbreviated. |
| Screen reader in use | Prefer the web UI, which has real accessibility semantics; the TUI cannot match it ([G3](g3-accessibility.md)). |
| Session ends mid-operation | Server-side work continues; on return the outcome is visible. |
| Non-interactive invocation missing required input | Fail naming the flags needed. Never prompt. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **G1-R1** | Every action MUST be available from every surface, except where intrinsically unsuited, and such exceptions MUST be documented. |
| **G1-R2** | All surfaces MUST drive the same underlying logic; no surface MAY implement behaviour independently. |
| **G1-R3** | Bare invocation MUST open the TUI when attached to a terminal, and MUST print help when not. |
| **G1-R4** | lemonfiber MUST NOT block on input when stdin is not interactive. |
| **G1-R5** | The web UI MUST be started explicitly and MUST NOT run persistently by default. |
| **G1-R6** | The web UI MUST bind to loopback by default under the security policy. |
| **G1-R7** | CLI output MUST offer a machine-readable form as a stable, versioned interface. |
| **G1-R8** | Exit codes MUST be meaningful and documented. |
| **G1-R9** | The TUI MUST function without true-colour support, without special fonts, and at modest terminal sizes. |
| **G1-R10** | `NO_COLOR` MUST be honoured. |
| **G1-R11** | Failure to launch a browser MUST NOT fail the command; the URL MUST be printed. |
| **G1-R12** | Concurrent surfaces MUST reflect the same state, and lifecycle operations MUST be serialised across them. |
| **G1-R13** | Non-interactive invocation lacking required input MUST fail naming the required flags. |
| **G1-R14** | Setup MUST be completable from all three surfaces. |

## Related

- [C6 Web UI security](../c-trust/c6-web-security.md) — binding and authentication
- [B6 Remote stack control](../b-running/b6-remote-stack.md) — LAN access
- [G3 Accessibility](g3-accessibility.md) · [G4 Error model](g4-error-model.md)
- [ADR-0003 Rust + Ratatui](../../../00-overview/decisions/0003-rust-ratatui-for-cli.md)
