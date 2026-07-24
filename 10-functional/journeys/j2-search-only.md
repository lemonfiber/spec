# J2 — "I just want to search for an NZB"

**Status:** Accepted · **Audience:** Operator

**Exercises:** [B1](../features/b-running/b1-forms.md) ·
[B2](../features/b-running/b2-lifecycle.md)

---

## The journey

```
$ lemonfiber up search

  ✓ prowlarr       healthy    http://localhost:9696
  ✓ flaresolverr   healthy
  ✓ nzbhydra2      healthy    http://localhost:5076

  3 services · 1 profile · ~180 MB
```

Three containers. No Sonarr, no Jellyfin, no download client, no VPN.

## Why this journey exists

It is the clearest demonstration of
[P2](../../00-overview/vision.md#p2--partial-stacks-are-first-class-not-degraded).
Every other stack in this space is a single compose file: wanting to look up one
NZB means booting a media server, a request portal, a subtitle daemon and four
automation services.

That isn't primarily about memory — it's that the tooling has no vocabulary for
*"I only need part of this."* Forms supply it.

## What makes it work

**Profile closure is computed, not hardcoded** (`B1-R3`). The `search` form
expands to exactly one profile, which contains exactly three services.

**No service hard-depends on anything outside its profile** (`B1-R14`). This is
what makes an arbitrary subset bootable — the reason partial stacks are reliable
rather than best-effort. Prowlarr doesn't need a download client to run; it just
can't push indexers anywhere until one exists.

**Startup is health-gated** (`B2-R1`). "Healthy" means Prowlarr's API is
answering, not that a process exists.

## Where it goes wrong

| Situation | Behaviour |
|-----------|-----------|
| No indexers configured yet | Services start fine. Prowlarr is where indexers get added — that's the point of running this form. |
| FlareSolverr not needed | Runs anyway; it costs little and which indexers need it isn't knowable in advance. |
| Port 9696 occupied | Named, with the conflicting process where the OS allows. |
| Operator later wants to download | `lemonfiber up hunt` adds the download clients, leaving the running search services untouched (`B1-R10`). |

## Growing out of it

The natural progression, each step leaving what's already running in place:

```
search  →  hunt  →  tv
   3         6        8   services
```

Nothing is torn down and rebuilt. Narrowing later stops only what falls outside
the new closure.

## Related

- [J3 Download only](j3-download-only.md) — the other narrow slice
- [B1 Forms](../features/b-running/b1-forms.md) — the full form table
