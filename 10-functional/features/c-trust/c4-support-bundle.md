---
id: C4
title: Support bundle
kind: feature
area: C
audience: operator
status: accepted
tracks: v1
labels: [verification, security]
depends: [A7, B4, C1, G8]
---

# C4 — Support bundle

**Status:** Accepted · **Audience:** Operator · **Area:** C — Trust & correctness

---

## Purpose

Let an operator ask for help without leaking their credentials.

When something is wrong beyond their ability to diagnose, they post on a forum or
open an issue. What they need to share is genuinely sensitive: configuration
containing API keys, logs containing indexer URLs with keys embedded, VPN
settings. What they actually do is screenshot a terminal, or paste a config file
having removed the parts they *recognised* as secret.

That last part is the problem. Nobody reliably spots every secret in a
40-line config, and the ones people miss — an API key inside a query string in a
log line — are the ones that matter.

## Behaviour

### One command produces one shareable file

Diagnostics results, service versions, platform details, sanitised
configuration, recent logs, and remediation history — collected, redacted, and
written to a single archive.

### Redaction is allow-list, not deny-list

The critical design decision. A deny-list redacts patterns known to be secret and
leaks anything unanticipated. An **allow-list** emits only fields known to be
safe and redacts everything else by default.

New secrets appear constantly — a service adds a field, an indexer uses an
unusual parameter name. Under a deny-list every one of those leaks until someone
notices. Under an allow-list they're redacted automatically, and the cost of
being wrong is a missing diagnostic field rather than a published credential.

### Redaction is consistent, not destructive

A redacted value is replaced by a stable placeholder derived from it, so the same
key reads identically everywhere in the bundle. Someone helping can see that two
services reference the same key without ever seeing the key.

```
indexer_api_key: <redacted:a3f1>
...
GET /api?apikey=<redacted:a3f1>&t=search
```

That preserves the diagnostic signal — *are these the same key?* — which naive
redaction destroys.

### The operator can inspect before sharing

The bundle is written locally and never transmitted anywhere. Its contents are
listable and readable. Nothing leaves the machine unless the operator sends it.

### Redaction is verified

Before writing, the bundle is scanned for anything resembling a known credential.
Any hit is a hard failure, not a warning: the bundle isn't written.

This is a belt-and-braces check on the allow-list — the one place where a bug
costs the operator a published secret.

### Bounded and predictable

Logs are truncated to a useful recent window rather than shipping gigabytes. The
size is stated before writing.

## States

| State | Meaning |
|-------|---------|
| `collecting` | Gathering |
| `redacting` | Applying the allow-list |
| `verifying` | Scanning for residual secrets |
| `ready` | Written locally; contents listable |
| `blocked` | Verification found a residual secret; nothing written |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Verification finds a residual secret | **Do not write the bundle.** Report which source produced it. Failing closed is the only acceptable behaviour. |
| A service log embeds a key in a URL | Redact query parameters wholesale unless allow-listed. |
| Config file in an unrecognised format | Include it only if entirely allow-listed; otherwise note its presence and exclude its contents. |
| Operator wants a field that's redacted | Permitted with explicit per-field consent, and the bundle marks that it contains a revealed secret. |
| Bundle would be very large | State the size and offer to reduce the log window. |
| Diagnostics cannot run | Collect what's available; note what's missing. A bundle from a broken system is exactly when it's needed. |
| Docker unreachable | Collect filesystem and configuration only; state the limitation. |
| Media filenames are sensitive | Offer to redact filenames. Some operators consider their library contents private. |
| Bundle contains a hostname or LAN IP | Allow-listed as safe by default; offer to redact for the cautious. |
| Operator shares an old bundle | Bundles are timestamped and carry the lemonfiber and stack versions. |
| Insufficient disk to write | Report before collecting rather than failing partway. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **C4-R1** | A support bundle MUST be produced by a single command into a single local file. |
| **C4-R2** | Redaction MUST use an allow-list; any field not explicitly allowed MUST be redacted. |
| **C4-R3** | Redacted values MUST be replaced by a stable placeholder derived from the value, so identical secrets are identifiable as identical. |
| **C4-R4** | The bundle MUST be scanned for residual credentials before writing. |
| **C4-R5** | If verification finds a residual credential, the bundle MUST NOT be written, and the source MUST be named. |
| **C4-R6** | The bundle MUST NOT be transmitted anywhere automatically. |
| **C4-R7** | Bundle contents MUST be listable and readable by the operator before sharing. |
| **C4-R8** | Revealing a redacted field MUST require explicit per-field consent and MUST be marked in the bundle. |
| **C4-R9** | Log inclusion MUST be bounded to a stated recent window. |
| **C4-R10** | Bundle size MUST be reported before writing. |
| **C4-R11** | The bundle MUST be producible when diagnostics cannot fully run, noting what is missing. |
| **C4-R12** | The bundle MUST record lemonfiber version, stack version and creation time. |
| **C4-R13** | Media filename redaction MUST be offered. |
| **C4-R14** | Insufficient disk space MUST be detected before collection begins. |

## Related

- [A7 Credential management](../a-getting-started/a7-credential-management.md) — what must never appear
- [C1 Diagnostics](c1-diagnostics.md) — the primary content
- [B4 Log viewing](../b-running/b4-logs.md) — shares the redaction rules
- [G8 Privacy stance](../g-ux/g8-privacy.md)
