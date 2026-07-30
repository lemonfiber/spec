---
id: B8
title: Autostart & boot persistence
kind: feature
area: B
audience: operator
status: accepted
tracks: v1
---

# B8 — Autostart & boot persistence

**Status:** Accepted · **Audience:** Operator · **Area:** B — Running it

---

## Purpose

The stack must come back after the machine restarts.

This is the hole that swallows non-technical operators. Docker's `restart:`
policies bring *containers* back — but only once the Docker **daemon** is
running, and on macOS and Windows Docker Desktop does not start at login by
default. So the machine reboots after an OS update, and everything is simply
gone. No error, no notification, nothing in any log the operator would think to
check. It just stopped working.

They then conclude the software is unreliable, which is a fair conclusion from
the evidence available to them.

## Behaviour

### Autostart is offered during setup, with the consequence stated

The wizard asks whether the stack should start automatically, and says what
happens if it doesn't. It is not buried in a configuration file the operator
would have to know exists.

### The platform difference is handled, not documented

"Start on boot" means three genuinely different things:

| Platform | What must happen |
|----------|------------------|
| **macOS** | Docker Desktop set to open at login; containers restart via their policy |
| **Windows** | Docker Desktop set to start at login; WSL2 backend must come up first |
| **Linux (native Docker)** | The Docker service is already enabled at boot; only container restart policies matter |

lemonfiber detects the platform and configures or instructs accordingly. Where a
setting belongs to Docker Desktop rather than to us, lemonfiber **verifies** it
and reports its state rather than silently assuming it.

### Restart policy is deliberate, not incidental

Services carry a restart policy so they survive daemon restarts and individual
crashes — but a container in a crash loop must be surfaced
([B2](b2-lifecycle.md)) rather than restarted invisibly forever.

Which form starts on boot is remembered: the last form the operator ran, unless
they pin a specific one.

### Post-boot verification

After a restart, the first thing lemonfiber does is confirm the stack actually
came back — including that the VPN re-established and its forwarded port was
re-acquired, since a dynamically assigned port does **not** survive a reconnect
and must be re-pushed into the download client.

This is exactly the class of silent post-reboot degradation the feature exists to
prevent: everything appears to be running, but torrents get no incoming
connections.

### Boot failure is reported, not silent

If the stack did not come back, the operator is told the next time they interact
with lemonfiber, with the reason. Optionally via a notification
([B5](b5-notifications.md)), because the whole failure mode is *not noticing*.

### Autostart is reversible

It can be turned off, and turning it off removes what was configured rather than
leaving orphaned login items or services behind.

## States

| State | Meaning |
|-------|---------|
| `disabled` | Nothing starts automatically |
| `enabled` | Configured; prerequisites verified present |
| `enabled-unverified` | Configured on our side, but a platform prerequisite (e.g. Docker Desktop at login) is not confirmed |
| `degraded` | Started at boot but with failures |
| `failed-boot` | Should have started and did not; reason recorded |

`enabled-unverified` is the important one: it is the state where the operator
*believes* they have autostart and does not.

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Docker Desktop not set to open at login | Detect, report, and offer instructions. This is the single most common cause of the whole failure. |
| Operator enables autostart but Docker Desktop remains off at login | Report `enabled-unverified`. Never claim autostart works when it can't. |
| Machine wakes from sleep rather than booting | Containers generally survive; the VPN may not. Re-verify the tunnel and forwarded port. |
| Laptop on battery | Do not auto-start on battery unless the operator opted in; a media stack will drain it. |
| Data root on an external or network volume not yet mounted | Services must not start against a missing data root — that risks writing into an empty mount point. Wait, then report if it never appears. |
| VPN reconnects with a different forwarded port | Detect and re-push it to the download client. |
| A service fails at boot | Start the rest, record the failure, report on next interaction. |
| Stack was deliberately stopped before shutdown | Respect that. Don't resurrect something the operator intentionally stopped. |
| Multiple boots with the same failure | Don't re-notify every boot; report a recurring condition once. |
| OS upgrade removes or resets the login item | Detect at next run and offer to restore. |
| Operator changes the pinned autostart form | Take effect from the next boot, and say so. |
| Boot before network is available | Retry rather than failing permanently — common on wired hosts that boot fast. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **B8-R1** | Setup MUST ask whether the stack should start automatically, and MUST state the consequence of declining. |
| **B8-R2** | lemonfiber MUST detect the platform and configure or instruct the correct autostart mechanism for it. |
| **B8-R3** | Where a prerequisite belongs to Docker Desktop, lemonfiber MUST verify its state and MUST NOT assume it. |
| **B8-R4** | An unverifiable prerequisite MUST produce `enabled-unverified`, and MUST NOT be reported as working autostart. |
| **B8-R5** | The form started at boot MUST be the last-run form unless a specific form is pinned. |
| **B8-R6** | After a boot, lemonfiber MUST verify the stack came back, including VPN tunnel and forwarded port. |
| **B8-R7** | A forwarded port that changed across a reconnect MUST be re-pushed to the download client. |
| **B8-R8** | A failed boot start MUST be reported at the operator's next interaction, with the reason. |
| **B8-R9** | Services MUST NOT start when the data root is not present, and MUST report rather than write into an empty mount point. |
| **B8-R10** | A deliberately stopped stack MUST NOT be auto-started at the next boot. |
| **B8-R11** | Disabling autostart MUST remove everything it configured, leaving no orphaned login items or services. |
| **B8-R12** | On battery power, autostart MUST NOT occur unless explicitly opted in. |
| **B8-R13** | A recurring boot failure MUST be reported as one ongoing condition, not once per boot. |
| **B8-R14** | Boot before network availability MUST retry rather than fail permanently. |

## Related

- [B2 Lifecycle control](b2-lifecycle.md) — restart policies and crash-loop detection
- [B5 Notifications](b5-notifications.md) — reporting a failed boot
- [C2 VPN verification](../c-trust/c2-vpn-verification.md) — post-reconnect port re-acquisition
- [C5 Storage management](../c-trust/c5-storage.md) — data root availability
