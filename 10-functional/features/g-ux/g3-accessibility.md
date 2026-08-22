---
id: G3
title: Accessibility
kind: feature
area: G
audience: both
status: accepted
tracks: v1
labels: [ux]
relates: [B3, B4, G1, G4]
---

# G3 — Accessibility

**Status:** Accepted · **Audience:** Both · **Area:** G — Cross-cutting UX

---

## Purpose

Make the product usable by people whose vision, motor control, or environment
differs from the developer's.

Terminal applications are habitually poor here: colour used as the sole carrier
of meaning, layouts that assume a wide window, spinners that emit thousands of
lines when redirected, and interaction that assumes a mouse or precise timing.

The commitment that *everyone* can use this is empty if it means everyone with
typical vision, a modern terminal, and a steady hand.

## Behaviour

### Colour is never the only signal

Every state distinguished by colour is also distinguished by symbol or text. A
red dot and a green dot are identical to a substantial minority of operators.

```
  ✓ prowlarr      healthy
  ! sabnzbd       degraded — no capacity
  ✗ gluetun       failed
```

Readable with no colour at all.

### `NO_COLOR` is honoured

The [`NO_COLOR` convention](https://no-color.org/) is respected, as are terminals
reporting no colour support. Output must remain fully comprehensible.

### The web UI carries the real accessibility story

A TUI cannot provide what a screen reader needs — semantic structure, landmarks,
labelled controls, focus management. The web UI can, and therefore **must**: it
is the accessible surface, and that's a reason for its existence beyond
friendliness to newcomers.

It should meet WCAG 2.2 AA for contrast, keyboard operability, focus visibility,
and text alternatives.

### Everything is keyboard-operable

The TUI necessarily; the web UI equally, with visible focus and no
keyboard traps. No action may require a pointing device.

### Motion is restrained and respectful

Spinners and progress indicators are informative rather than decorative.
`prefers-reduced-motion` is honoured in the web UI. Nothing flashes.

### Output is not corrupted when redirected

Piped or redirected output emits no control sequences, no cursor movement, and no
repeated progress lines — a 4,000-line progress bar in a log file is a
frequent and avoidable failure.

### Text from elsewhere cannot take over the terminal

Most of what this product shows, it did not write. A release name comes from an
indexer, a failure message from a \*arr, a container name from an image somebody
else built. A terminal is not a text box: a control sequence in the middle of one
of those is an instruction to the emulator rather than something said. `\x1b[2J`
clears the screen, `\x1b[H` moves the cursor home, and a carriage return writes
over the line just printed.

Nothing executes, which is exactly what makes it easy to leave alone. What is lost
is the screen agreeing with the product — and a diagnosis an operator cannot trust
to say what happened is a diagnosis that was not worth printing.

It holds on every surface, not only in the log viewer where it was first written
down, because the text arrives by more roads than one: a service's own words reach
a failure message as readily as a container's reach a log line. Redaction is not
this rule — a credential scrubber looks for secrets, and has no opinion about an
escape.

### Layout adapts rather than assumes

Content reflows for narrow terminals and small viewports. No horizontal scrolling
in the web UI. Text size is respected rather than fixed.

### Time limits are avoidable

Prompts that expire and confirmations that time out disadvantage anyone who reads
or types slowly. Where a timeout exists it is generous, stated, and extendable.

## States

| State | Meaning |
|-------|---------|
| `full` | All affordances available |
| `no-colour` | Colour unavailable or disabled; symbols carry state |
| `reduced-motion` | Animation suppressed |
| `plain-output` | Non-interactive; no control sequences |
| `narrow` | Reduced layout, content prioritised |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Terminal reports colour but renders poorly | `NO_COLOR` and an explicit flag both available. |
| Screen reader on the TUI | Best-effort; direct to the web UI, which is the supported path. |
| Very narrow terminal | Reduce by priority. Never truncate a value so it misleads. |
| Output redirected to a file | Plain text, no control sequences, single-line progress summaries. |
| Operator needs larger text | Web UI respects browser text sizing; layout must not break. |
| Symbols render as boxes | Fall back to ASCII markers. Never depend on Unicode symbols alone. |
| Long-running operation with no output | Emit periodic textual progress; silence is indistinguishable from a hang for anyone not watching a spinner. |
| Confirmation prompt with a timeout | Generous, stated, extendable — or absent. |
| High-contrast mode | Honour system preference in the web UI. |
| Colour-coded severity in logs | Severity always also present as text. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **G3-R1** | No state MAY be conveyed by colour alone; a symbol or text MUST also carry it. |
| **G3-R2** | `NO_COLOR` MUST be honoured, and output MUST remain fully comprehensible without colour. |
| **G3-R3** | The web UI MUST meet WCAG 2.2 AA for contrast, keyboard operability, focus visibility and text alternatives. |
| **G3-R4** | All functionality MUST be operable by keyboard alone, with visible focus and no keyboard traps. |
| **G3-R5** | `prefers-reduced-motion` MUST be honoured in the web UI. |
| **G3-R6** | Nothing MAY flash or blink. |
| **G3-R7** | Redirected or piped output MUST contain no control sequences and no repeated progress lines. |
| **G3-R8** | Layout MUST adapt to narrow terminals and small viewports without horizontal scrolling. |
| **G3-R9** | Unicode symbols MUST fall back to ASCII where unsupported. |
| **G3-R10** | Values MUST NOT be truncated in a way that changes their meaning. |
| **G3-R11** | Long-running operations MUST emit periodic textual progress. |
| **G3-R12** | Timeouts on prompts MUST be generous, stated, and extendable, or absent. |
| **G3-R13** | The web UI MUST respect browser text sizing and system high-contrast preferences. |
| **G3-R14** | Severity in log output MUST be present as text, not only as colour. |
| **G3-R15** | Text the product did not author MUST NOT be able to alter terminal state, on any surface that shows it. |

## Related

- [G1 Interface tiers](g1-interface-tiers.md) — the web UI as the accessible surface
- [G4 Error model](g4-error-model.md) — error presentation
- [B3 Dashboard](../b-running/b3-dashboard.md) · [B4 Log viewing](../b-running/b4-logs.md)
