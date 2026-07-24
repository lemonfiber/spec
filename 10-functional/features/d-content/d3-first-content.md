# D3 — First-content walkthrough

**Status:** Accepted · **Audience:** Operator · **Area:** D — Content & household

---

## Purpose

End setup with something working, not with an empty dashboard.

Setup currently finishes at the moment of maximum uncertainty: sixteen services
are running, everything is green, and the operator has no idea what to do. They
went to the trouble of installing this because they wanted to watch something,
and the product has delivered infrastructure.

The gap between "the stack is running" and "I got what I came for" is where the
whole effort can still fail. Someone who watched something they asked for is
committed; someone staring at a dashboard is not.

## Behaviour

### Offered immediately after setup, and skippable

Setup ends by offering to walk through adding one thing. Declining is fine and
carries no penalty — it can be run later.

### It proves the whole pipeline

The walkthrough deliberately exercises every link: search an indexer, grab a
release, download it, import it, and see it appear in the library. That path
touches Prowlarr, the download client, the VPN if torrents are involved, the
\*arr, the filesystem, and Jellyfin.

**If any link is broken, this is where it shows** — with full context about which
step failed, rather than as a mysterious absence three days later.

### It narrates what's happening

Each stage is explained as it occurs, in plain language:

```
  Searching indexers…                    3 indexers, 47 results
  Selecting best match…                  1080p, matches your Balanced preset
  Sending to download client…            SABnzbd, via usenet
  Downloading…                           2.1 GB · 14 MB/s · ~2m
  Importing…                             hardlinked to /data/media/tv
  ✓ Available in Jellyfin
```

This is the operator's mental model being built. Afterwards they understand what
the stack does, because they watched it happen once.

### It suggests something safe

Rather than asking a newcomer to pick blindly, it can suggest well-seeded,
widely-available content so the first attempt is likely to succeed. A first
attempt that fails because the operator chose something obscure teaches the wrong
lesson.

### Failure is the useful case

If it fails, the operator gets a diagnosis at the exact step, with the relevant
logs inline and a remedy — the failure surfaces at the one moment they're
engaged, expecting to interact, and willing to fix things.

### It ends by handing over

On success it points at what comes next: adding more content, inviting household
members ([D6](d6-household-identity.md)), and where to watch ([G6](../g-ux/g6-client-apps.md)).

## States

| State | Meaning |
|-------|---------|
| `offered` | Presented at end of setup |
| `skipped` | Declined; available later |
| `searching` → `grabbing` → `downloading` → `importing` | In progress |
| `complete` | Content is in the library and playable |
| `failed` | Stopped at a named step with diagnosis |
| `abandoned` | Operator exited mid-walkthrough |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| No indexers configured | Don't offer the walkthrough. Point at prerequisites instead. |
| Library-only configuration | Offer a different walkthrough: point at existing media and confirm Jellyfin can see it. |
| Search returns nothing | Distinguish "indexers working, nothing matched" from "indexers not working". Entirely different problems. |
| Download very large | Estimate the time and offer to continue in the background rather than holding the operator at a progress bar. |
| Download stalls | Surface it as [C7](../c-trust/c7-queue-health.md) would, with the same remedies. |
| Import fails | The highest-value failure to catch. Show the \*arr's reason and offer remediation. |
| Import copied instead of hardlinking | Note it — the walkthrough is the natural place to explain the consequence concretely. |
| Operator exits mid-walkthrough | The download continues. Progress is visible on the dashboard. |
| Content already present | Detect and offer something else rather than re-acquiring. |
| VPN not connected, torrents selected | Halt before grabbing. Never fetch a torrent outside the tunnel to complete a tutorial. |
| Jellyfin not in the active form | Complete through import and explain that playback needs the library serving. |
| Content acquired but Jellyfin hasn't scanned | Trigger a scan rather than leaving the operator wondering. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **D3-R1** | Setup MUST offer the walkthrough on completion, and declining MUST carry no penalty. |
| **D3-R2** | The walkthrough MUST exercise search, grab, download, import and library availability end to end. |
| **D3-R3** | Each stage MUST be narrated in plain language as it happens. |
| **D3-R4** | Failure MUST identify the failing step, show relevant logs inline, and offer a remedy. |
| **D3-R5** | "Indexers returned nothing" MUST be distinguished from "indexers failed". |
| **D3-R6** | With torrents selected, the walkthrough MUST NOT grab anything unless the VPN is verified connected. |
| **D3-R7** | Exiting mid-walkthrough MUST NOT cancel the download in progress. |
| **D3-R8** | An import that copied rather than hardlinked MUST be noted with its consequence. |
| **D3-R9** | A library-only configuration MUST receive a walkthrough appropriate to it. |
| **D3-R10** | On success the walkthrough MUST point at adding more content, inviting household members, and client apps. |
| **D3-R11** | Content already present MUST be detected rather than re-acquired. |
| **D3-R12** | A library scan MUST be triggered so imported content is immediately visible. |
| **D3-R13** | The walkthrough MUST be runnable at any time, not only at end of setup. |

## Related

- [A2 Setup wizard](../a-getting-started/a2-setup-wizard.md) — what precedes it
- [D9 Pipeline trace](d9-pipeline-trace.md) — the same visibility, on demand
- [C7 Queue health](../c-trust/c7-queue-health.md) — shared stall handling
- [D6 Household identity](d6-household-identity.md) · [G6 Client apps](../g-ux/g6-client-apps.md)
- [J1 First run](../../journeys/j1-first-run.md)
