---
id: B4
title: Log viewing
kind: feature
area: B
audience: operator
status: accepted
tracks: v1
---

# B4 — Log viewing

**Status:** Accepted · **Audience:** Operator · **Area:** B — Running it

---

## Purpose

See what a service is actually saying, without leaving lemonfiber and without
knowing Docker's log syntax.

Logs are where every non-obvious failure explains itself. But the default
experience — `docker logs -f` one container at a time, in a separate terminal,
with no filtering — makes correlating a failure across services genuinely hard.
The failures that matter here are usually *cross-service*: Sonarr says import
failed, and the reason is in SABnzbd's log, or in Gluetun's.

## Behaviour

### Multiple services in one stream

Logs from several services can be viewed together, interleaved chronologically
and tagged by source. This is the feature's central value: an import failure
becomes explicable when Sonarr's and SABnzbd's lines sit side by side.

### Filtering is immediate

By service, by severity, and by free-text match, applied live to both the
existing scrollback and incoming lines.

### Following without losing your place

The default follows new output. Scrolling up detaches automatically and shows
that new lines are arriving; returning to the bottom re-attaches. Nothing is more
frustrating than a viewer that yanks you away from what you're reading.

### Relevant logs surface automatically at failures

When a service fails to start or a check fails, its recent log lines are shown
**inline at the point of failure** — not left for the operator to go and find.
The most likely explanation should already be on screen.

### Severity is normalised across services

Each service formats logs differently. lemonfiber parses what it reliably can
into a common severity so that "show me errors" works across all of them, and
leaves the message body untouched.

Where a format can't be parsed confidently, lines are passed through unclassified
rather than guessed at — a misclassified error is worse than an unclassified one.

### Export for sharing

A filtered view can be exported for a forum post or issue, passing through
[support bundle redaction](../c-trust/c4-support-bundle.md) so API keys and
credentials never leave the machine.

## States

| State | Meaning |
|-------|---------|
| `following` | Attached to the tail, auto-scrolling |
| `detached` | Scrolled back; new lines buffered and counted |
| `filtered` | A filter is active; the match count is shown |
| `truncated` | Buffer limit reached; oldest lines dropped, and this is stated |
| `source-lost` | A service's stream ended (stopped or removed) |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Service produces output faster than it can be rendered | Sample and state that sampling is active. Never block the UI, never silently drop. |
| Very long single line | Wrap or truncate with a marker; never corrupt the layout. |
| Service restarts mid-view | Note the restart in the stream and continue. Don't end the view. |
| Service stopped or removed | Mark `source-lost` and keep existing scrollback readable. |
| Binary or ANSI-laden output | Strip or render control sequences safely. Never let a log line reconfigure the terminal. |
| Log contains a credential | Redact on export. Warn on screen where a known secret pattern is detected. |
| Buffer limit reached | Drop oldest, state that truncation occurred, and offer the full log via the underlying tool. |
| Clock skew between containers | Sort by the container's own timestamp; annotate where skew is detected. |
| No logs at all | Say "no output", distinguishing it from "not reading logs". |
| Multi-line stack traces | Keep grouped when the format permits; never interleave one trace's lines with another service's. |
| Filter matches nothing | Say so, with the number of lines scanned — silence looks like a hang. |
| Very large historical log | Load lazily from the tail backwards; don't read gigabytes to show the last screen. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **B4-R1** | Logs from multiple services MUST be viewable in one chronologically interleaved stream, tagged by source. |
| **B4-R2** | Filtering by service, severity and free text MUST apply to both scrollback and incoming lines. |
| **B4-R3** | Scrolling back MUST detach from following, and returning to the tail MUST re-attach. |
| **B4-R4** | While detached, the count of new lines MUST be shown. |
| **B4-R5** | When a service fails to start or a check fails, its recent log lines MUST be surfaced inline at the failure. |
| **B4-R6** | Severity MUST be normalised across services where the format permits, and lines MUST pass through unclassified rather than be guessed. |
| **B4-R7** | Control sequences in log output MUST NOT alter terminal state. |
| **B4-R8** | Buffer truncation MUST be stated explicitly. |
| **B4-R9** | High-rate output MUST NOT block input; sampling MUST be stated when active. |
| **B4-R10** | Exported logs MUST pass through the same redaction rules as the support bundle. |
| **B4-R11** | A service restarting mid-view MUST be noted in the stream without ending the view. |
| **B4-R12** | An empty result MUST be stated, with the number of lines scanned. |
| **B4-R13** | Historical logs MUST be read from the tail backwards, not by loading the whole file. |

## Related

- [B3 Dashboard](b3-dashboard.md) — where log viewing is entered from
- [C1 Diagnostics](../c-trust/c1-diagnostics.md) — checks that surface logs on failure
- [C4 Support bundle](../c-trust/c4-support-bundle.md) — redaction rules
- [G4 Error model](../g-ux/g4-error-model.md)
