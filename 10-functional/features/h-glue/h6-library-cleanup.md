---
id: H6
title: Library cleanup
kind: feature
area: H
audience: both
status: accepted
tracks: v2
priority: P2
labels: [storage, verification, wiring]
relates: [D5]
---

# H6 — Library cleanup

**Status:** Accepted · **Audience:** Both · **Area:** H — Ecosystem glue

---

## Purpose

Keep the library from growing without bound by removing media that has served its
purpose — watched and unlikely to be rewatched, aged past a keep-window, or simply
low-value against the space it costs — using the household's own watch and request
history to decide. This is the watched-based cleanup Jellyfin operators repeatedly
ask for and that existing tools handle crudely: deleting on a blunt age rule with no
memory of who watched what or who asked for it.

Because this feature deletes real media, it treats silent data loss as a defect.
Every deletion is reversible-by-default: a dry-run first, an explicit confirmation,
and an auditable record of what went and why — so a household never loses a film to
a rule it did not understand.

## Behaviour

### It decides from watch and request data, not age alone

Cleanup candidates are chosen by rules evaluated against real signal: whether
everyone who wanted an item has watched it, how long since it was added or last
played, and whether it was ever requested at all. Age is one input among several,
never the sole trigger — a classic nobody has watched yet is not the same as a
throwaway episode everyone finished a year ago.

### Nothing is deleted without a dry-run and a confirmation

Every cleanup run first produces a **dry-run**: the exact list of items that match
the rules, the space each would reclaim, the rule that selected it, and the watch or
request evidence behind it. No file is removed until the operator has seen that plan
and explicitly confirmed it. A confirmation covers the reviewed plan, not a standing
licence to delete whatever future runs select.

### It leaves an auditable, reversible record

Each deletion is written to a record the household can read back: what was removed,
when, which rule fired, and what evidence justified it. Where the media manager and
request manager support re-acquisition, a removed item can be re-requested and
pulled again — deletion returns an item to "wanted", it does not erase the wish for
it.

### It proves every connection before it deletes

Before selecting a single candidate, H6 confirms it can authenticate to the media
server, the request manager, and the \*arr apps, and reports any it cannot reach.
Watch state comes from the media server; request state from the request manager;
removal is coordinated with the \*arr that owns the file. A cleanup that cannot read
watch data does not fall back to deleting on age alone — it stops and says why,
because deleting without the signal it was designed around is exactly the crude
behaviour this feature exists to replace.

### It honours who still wants the media

An item still wanted by any household member — unwatched by someone who requested
it, or inside another member's keep preference — is never a candidate, even if
others have finished it. Watch state is read across the household, not from one
account ([D6](../d-content/d6-household-identity.md)), and children's viewing is
handled under the parental-data rules ([D8](../d-content/d8-parental-controls.md))
rather than exposed to justify a deletion.

### It coordinates with disk-space pressure

Cleanup can be driven by the same disk-space signals that
[D5](../d-content/d5-disk-space.md) tracks — running when free space crosses a
threshold — but the reclaim target never overrides the dry-run-and-confirm gate.
Pressure changes *when* cleanup is proposed, never *whether* the household gets to
approve it.

### Every step has a non-interactive equivalent

The candidate report, the dry-run, and a confirmed cleanup are each reachable as
plain subcommands, with confirmation supplied explicitly, so cleanup can be
scheduled without ever deleting unattended-and-unconfirmed.

## States

| State | Meaning |
|-------|---------|
| `idle` | No cleanup proposed; the library is within its bounds |
| `dry-run` | A deletion plan produced with evidence, nothing removed |
| `awaiting-confirmation` | A plan presented; deletion blocked until the operator confirms |
| `cleaning` | A confirmed plan being applied, each removal recorded |
| `degraded` | Media server, request manager or an \*arr unreachable; selection refused until connections are proven |
| `held` | Cleanup paused; candidate reporting still readable |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Item still wanted by a household member | Excluded from candidates entirely; another member finishing it does not make it deletable. |
| Shared/household watch state disagreement | An item counts as watched only when every member who wanted it has watched it; one viewer is not the household. |
| Request re-adds an item after deletion | Honoured — the deletion record enables re-acquisition, and a fresh request pulls it again rather than being blocked by its former presence. |
| Watch data unreadable | Refuse to select candidates and say why; never fall back to deleting on age alone. |
| Confirmation given, then the plan is stale | Re-validate the plan at apply time; if candidates changed, re-present rather than delete against an outdated list. |
| Disk critically full | Cleanup may be *proposed* more urgently, but the dry-run-and-confirm gate still holds; pressure never authorises silent deletion. |
| Child's viewing would justify a deletion | Parental watch data stays governed by [D8](../d-content/d8-parental-controls.md); it is not surfaced to the household to explain a candidate. |
| Media file already removed out-of-band | Reconcile the record without error; report it as already-gone, not as a failed deletion. |
| Rule matches an entire series/collection | Present the whole set in the dry-run with per-item evidence; never delete a collection wholesale on a single member's match. |
| No candidates match | Report "nothing to clean" explicitly rather than an empty confirmation prompt. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **H6-R1** | Cleanup candidates MUST be selected from watch and request data, and MUST NOT be selected on age alone. |
| **H6-R2** | No media MUST be deleted without first producing a dry-run listing every candidate, the space it reclaims, the rule that selected it, and the evidence behind it. |
| **H6-R3** | Deletion MUST require an explicit operator confirmation of the reviewed plan, and a confirmation MUST NOT authorise deletions in later runs. |
| **H6-R4** | Every deletion MUST be written to an auditable record naming what was removed, when, the rule, and the justifying evidence. |
| **H6-R5** | A removed item MUST remain re-acquirable through the request manager and \*arr, so deletion returns it to "wanted" rather than erasing the wish for it. |
| **H6-R6** | The tool MUST authenticate to the media server, the request manager, and the \*arr apps, and MUST report any it cannot reach. |
| **H6-R7** | When watch data cannot be read, the tool MUST refuse to select candidates and MUST NOT fall back to deleting on age. |
| **H6-R8** | An item still wanted by any household member MUST NOT be a candidate, and watch state MUST be evaluated across the household, not from a single account. |
| **H6-R9** | Children's viewing data MUST stay governed by the parental-controls rules and MUST NOT be surfaced to justify a deletion. |
| **H6-R10** | Disk-space pressure MAY change when cleanup is proposed but MUST NOT bypass the dry-run-and-confirm gate. |
| **H6-R11** | A confirmed plan MUST be re-validated at apply time, and MUST be re-presented rather than applied if its candidate set has changed. |
| **H6-R12** | A media file already removed out-of-band MUST reconcile without error and be reported as already-gone, not as a failed deletion. |
| **H6-R13** | A rule matching a series or collection MUST present the full set with per-item evidence and MUST NOT delete the set wholesale on a single member's match. |
| **H6-R14** | Candidate reporting, dry-run, and confirmed cleanup MUST each be reachable non-interactively, with confirmation supplied explicitly. |
| **H6-R15** | When no candidates match, the tool MUST state that explicitly rather than present an empty confirmation. |

## Related

- [D5 Disk space management](../d-content/d5-disk-space.md) — the pressure signal that can drive cleanup
- [D6 Household identity & invitations](../d-content/d6-household-identity.md) — whose watch state counts
- [D8 Parental controls](../d-content/d8-parental-controls.md) — the rules governing children's viewing data
- [G8 Privacy stance](../g-ux/g8-privacy.md) — the watch-data posture cleanup must honour
- [H5 Queue self-healing](h5-queue-selfheal.md) — the sibling reversible automation on the queue side
