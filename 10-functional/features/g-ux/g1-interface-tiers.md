---
id: G1
title: Interface tiers
kind: feature
area: G
audience: both
status: accepted
tracks: v1
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

The exceptions are enumerated below rather than left to judgement, because a
requirement that permits exceptions and does not list them permits everything.

### The exceptions, named

An exception to parity is a claim about the *nature* of an action on a surface. It
is not a claim about the state of the code, and the two sentences are easy to say
in the same breath: "a browser cannot do this" and "nobody has built this in the
browser yet" look alike and mean opposite things. Only the first is an exception.
The second is a gap, and gaps are tracked where work is tracked.

So an exception names three things — the action, the surface it is unsuited to,
and the equivalent that surface offers instead. **An action missing from a surface
and missing from this table is unbuilt, not excepted.** That is the whole use of
writing the table down: it takes away the option of leaving something out quietly.

| Action | Unsuited to | Why that is intrinsic | The equivalent that surface offers |
|--------|-------------|-----------------------|-------------------------------------|
| Serving the web UI (`lemonfiber ui`) | Web | A surface cannot start itself. The request can only reach a server that is already serving — where it means nothing — or it means starting a *second* server, which is a different request. And it would make a running server into an endpoint that mints and hands out a per-run token, reachable from any page the operator happens to visit. | The address bar. Being able to ask is proof it is already running. |
| A live-refreshing dashboard | CLI | A command ends, and a view that refreshes does not. A command that never ended would not be a command; a script waiting on one would wait forever. | `lemonfiber ps` — the same reading, taken once. The TUI and the web hold it open. |
| An open event stream | CLI | The same shape one layer down: a stream has no last element, so there is nothing for a command to answer with and exit on. | `lemonfiber logs --follow` streams lines until interrupted; every other reading answers once. |
| Machine-readable output (`--json`) | TUI, Web | `--json` asks how *this run's* answer is written, which only means something where an answer is written to a pipe. A screen is not a pipe. | The web API **is** the machine-readable form — the identical envelope, byte for byte ([web-api](../../../20-architecture/contracts/web-api.md)). A program wanting an answer from a terminal session uses the CLI, which is in the same binary. |

Four rows is the whole list, and that is the point: almost nothing is genuinely
unsuited. The pressure this table is under is the temptation to grow it, because
every unbuilt thing looks like an exception from the side of not having built it.

### Where a surface is poorer, not excepted

Three actions touch a path on the operator's machine — taking a backup, restoring
one, and writing a support bundle. It is tempting to call these web exceptions,
and the argument does not survive being made: the server runs **on the host, as
the operator**, so a path typed into a form is a path the server can read or
write. Nothing about the operation needs a browser to reach the filesystem.

What a browser genuinely cannot do is *browse* to one — show what a directory
already holds, or warn that a name is about to overwrite something — and for a
restore, choosing the wrong archive is not a mistake that can be taken back.

That is a weaker claim than unsuitability and it gets a weaker remedy rather than
an exemption. The browser offers the archives lemonfiber already knows about,
takes a typed path for anything else, and states what it is about to overwrite
before it does. The action is available; only the picker is poorer.

### The terminal interface is not exempt

A dashboard that only reads is a surface missing every action, not a surface whose
nature is to watch. Nothing about a terminal stops a keypress from starting a
form, and the operator the TUI exists for — the one on the far end of an SSH
session, who cannot open a browser — is the one *least* able to reach another
surface to act on what this one has just told them. A screen that says
`sonarr: unhealthy` and offers nothing to do about it is the divergence parity
exists to prevent, arriving one surface earlier than expected.

The counter-argument is that the shell is right there: an operator reading that
line can simply type the restart. It is true, and it proves too much — by the same
reasoning the web UI needs no actions either, since the operator could open a
terminal. Every surface is somebody's only surface, which is why parity is stated
per surface rather than per person.

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
| An action has no sensible form on a surface | State the equivalent explicitly rather than silently omitting it, in [the exceptions table](#the-exceptions-named). Absent from that table means unbuilt. |
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
