# J1 — First run on a clean machine

**Status:** Accepted · **Audience:** Operator

**Exercises:** [A1](../features/a-getting-started/a1-prerequisites.md) ·
[A2](../features/a-getting-started/a2-setup-wizard.md) ·
[A3](../features/a-getting-started/a3-credential-validation.md) ·
[C5](../features/c-trust/c5-storage.md) ·
[B8](../features/b-running/b8-autostart.md) ·
[D1](../features/d-content/d1-seed.md) ·
[D3](../features/d-content/d3-first-content.md)

**Target:** a working stack in under 15 minutes, with no service web UI opened to
wire anything together.

---

## The journey

```
$ lemonfiber

  ┌─ lemonfiber ──────────────────────────────────────────┐
  │                                                        │
  │   No configuration found.                              │
  │   Run first-time setup?                       [Y/n]    │
  │                                                        │
  └────────────────────────────────────────────────────────┘
```

| Step | What happens | Why it's here |
|------|--------------|---------------|
| 1. Welcome | States what's about to happen and roughly how long | Image pulls take minutes; silence reads as a hang |
| 2. Preflight | Detects OS; verifies Docker daemon reachable and Compose new enough | Every later failure is confusing if this is wrong |
| 3. Prerequisites | The account checklist — what's needed, in what order, roughly what it costs | The real wall for a newcomer (`A1-R1`) |
| 4. Protocols | Usenet, torrents, both, or neither | "Neither" is valid — see below |
| 5. Data location | Proposes a default, then **creates a hardlink and inspects it** | Empirical, not assumed (`C5-R1`) |
| 6. Credentials | Each one tested against the live service as it's entered | A wrong key must fail here, not in a week (`A3-R1`) |
| 7. Quality | Plain language — "looks right on a TV", not custom formats | |
| 8. Library | Whether to run Jellyfin; if so, Docker or native | Native only offered where it helps |
| 9. Household | Whether others will use it | Drives invitations later |
| 10. Autostart | Whether to start on boot | Closes the reboot hole (`B8-R1`) |
| 11. **Review** | Complete summary. **Nothing has touched disk yet.** | (`A2-R2`) |
| 12. Apply | Writes config, creates the directory tree, materialises stack files | |
| 13. Start | Pulls images with per-image progress, then waits for health | |
| 14. Wire | Registers download clients, root folders, indexer sync, identity | The half-hour of clicking (`D1-R1`) |
| 15. Finish | Prints URLs; offers the first-content walkthrough | Ends in success, not an empty dashboard |

## The zero-cost path

Declining both protocols is a **supported end state**, not a degraded one
(`A1-R3`). Someone with an existing folder of media reaches a working Jellyfin
with no third-party accounts and no spend.

Steps 3, 6 and much of 14 are skipped entirely. This is the gentlest possible
on-ramp, and nothing else in the ecosystem presents it as a first-class option.

## Where it goes wrong

| Situation | Behaviour |
|-----------|-----------|
| Docker not installed | Platform-specific install instructions, then exit. Never a stack trace. |
| Docker installed, daemon stopped | **Distinct message** — the remedy differs entirely (`A2-R9`) |
| Data location can't hardlink | Consequences stated concretely; offer another location or copy mode (`C5-R3`) |
| Port already bound | Names the conflicting process where the OS allows; offers a remap |
| VPN key rejected | Names the NAT-PMP-at-generation cause first — it's the likeliest and isn't guessable (`A3-R8`) |
| Operator quits mid-wizard | Answers preserved; resumes at the same step (`A2-R4`) |
| Interrupted during apply | Detected next run; offers resume, roll back, or start over (`A2-R10`) |
| A service fails health check | Reports which, shows its logs inline, offers to continue where the form permits |

## What "success" means

1. A working stack.
2. **No YAML edited**, no API key copied, no service web UI opened for wiring.
3. The operator has a rough mental model of what's running — built by watching
   step 15 narrate an actual download.

## Related

- [J2](j2-search-only.md) / [J3](j3-download-only.md) — narrower starting points
- [J9](j9-household.md) — the natural next journey
- [A5 Migration](../features/a-getting-started/a5-migration.md) — when a stack already exists
