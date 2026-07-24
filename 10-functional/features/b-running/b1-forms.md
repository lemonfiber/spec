# B1 — Forms & partial stacks

**Status:** Accepted · **Audience:** Operator · **Area:** B — Running it

---

## Purpose

Run only the part of the stack you actually need right now.

Most self-hosted media stacks are a single compose file: sixteen services, all or
nothing. Wanting to look up an NZB means booting a media server, a request
portal, a subtitle daemon and four automation services. That isn't primarily a
resource problem — it's that the tooling has no vocabulary for *"I only need part
of this."*

A **form** supplies that vocabulary. It is the primary noun the operator uses,
and the mechanism ([Compose profiles](../../../00-overview/decisions/0002-profiles-and-forms.md))
is deliberately invisible to them.

## Behaviour

### Two layers: profiles are facts, forms are intent

Each service carries **exactly one** profile — a factual statement of what it is.
Forms are named combinations, declared as data in the stack manifest.

| Profile | Services | Count |
|---------|----------|-------|
| `search` | prowlarr, flaresolverr, nzbhydra2 | 3 |
| `usenet` | sabnzbd | 1 |
| `torrent` | gluetun, qbittorrent | 2 |
| `tv` | sonarr | 1 |
| `movies` | radarr | 1 |
| `music` | lidarr | 1 |
| `books` | bindery | 1 |
| `subs` | bazarr | 1 |
| `media` | jellyfin, seerr, calibre-web-automated, audiobookshelf | 4 |
| `tuning` | recyclarr, unpackerr | 2 |
| `dash` | homepage | 1 |
| `proxy` | caddy | 1 |

> **Why acquisition and serving are split.** Bindery *acquires* books and sits in
> `books` alongside the other \*arrs; Calibre-Web-Automated and Audiobookshelf
> *serve* them and sit in `media` alongside Jellyfin. This keeps `library`
> meaningful — you can serve an existing book collection without running an
> acquisition service you have no indexers for.

### Forms

| Form | Profiles | Services | Intent |
|------|----------|----------|--------|
| `search` | search | 3 | "Find me an NZB." |
| `dl` | usenet, torrent | 3 | "I have a link — fetch it." |
| `hunt` | search, usenet, torrent | 6 | Search and grab, manually. |
| `tv` | hunt + tv, subs | 8 | Automated television |
| `movies` | hunt + movies, subs | 8 | Automated film |
| `music` | hunt + music | 7 | Automated music |
| `books` | hunt + books | 7 | Automated books & audiobooks |
| `auto` | hunt + tv, movies, music, books, subs, tuning | 12 | Everything automated, nothing served |
| `library` | media | 4 | Serve what exists. **Requires no third-party accounts.** |
| `full` | all except proxy | 18 | The lot |
| `proxy` | proxy | 1 | Friendly hostnames — composable |

### Forms compose

`lemonfiber up full proxy` starts the union of both closures. Composition is a
set union over profiles, so a service appearing in several active forms starts
exactly once.

This is what makes `proxy` viable as a form rather than a flag: a reverse proxy
is an orthogonal concern that layers onto any other form.

### Closures are filtered by configured protocols

A form's profile set is intersected with what the operator actually configured.
`lemonfiber up dl` on a Usenet-only setup starts SABnzbd and **does not** attempt
to start Gluetun with credentials that don't exist.

Without this, every torrent-containing form would break for Usenet-only
operators — which is a large fraction of them.

### Forms are introspectable

The operator can ask what a form will do before running it: the profiles it
expands to, the services that will start, which were filtered out and why, and
the approximate memory footprint.

### Forms are data, not code

Adding or changing a form is a manifest edit in `media-stack`. It requires no
change to `lemonfiber` and no release — see
[ADR-0002](../../../00-overview/decisions/0002-profiles-and-forms.md).

## States

| State | Meaning |
|-------|---------|
| `available` | Declared in the manifest and startable with current configuration |
| `partially-available` | Declared, but some profiles are filtered out by protocol config |
| `unavailable` | Every profile filtered out, or a prerequisite is unconfigured |
| `active` | Currently running |
| `superseded` | Its services are running under a broader active form |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Form named that doesn't exist | List available forms and suggest the nearest match. Never a bare "not found". |
| Every profile in a form filtered out | Refuse to start, naming the missing configuration and pointing at [A4 reconfiguration](../a-getting-started/a4-reconfiguration.md). |
| Switching from a broad form to a narrow one | Stop only the services outside the new closure. Don't tear down and rebuild what stays. |
| Two forms sharing services | Union. Each service starts once; stopping one form does not stop shared services still required by another. |
| Form declares a profile with no services | Valid but pointless — warn at manifest-validation time, not at runtime. |
| Operator wants an ad-hoc profile combination | Supported via composition. Direct profile selection is deliberately **not** exposed — profiles are an implementation detail. |
| A service in the closure fails to start | Report which, keep the rest running, and state what capability is degraded. Never roll back the whole form for one failure. |
| Manifest declares a form referencing an unknown profile | Fail manifest validation at load, with the offending form and profile named. |
| `library` selected with no media present | Valid. Start normally and note that libraries are empty until content is added or a path is configured. |
| Form composed with itself, or duplicates given | Deduplicate silently. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **B1-R1** | Each service in the manifest MUST declare exactly one profile. |
| **B1-R2** | Forms MUST be declared as manifest data; adding or altering one MUST NOT require a lemonfiber release. |
| **B1-R3** | A form's closure MUST be computed from the manifest, never hardcoded. |
| **B1-R4** | Closures MUST be intersected with the operator's configured protocols before starting anything. |
| **B1-R5** | Multiple forms MUST be startable together, resolving to the union of their closures. |
| **B1-R6** | A service present in several active forms MUST start exactly once. |
| **B1-R7** | lemonfiber MUST report, before starting, which services a form will start and which were filtered out and why. |
| **B1-R8** | Profiles MUST NOT be selectable directly by the operator. |
| **B1-R9** | An unknown form name MUST produce a list of valid forms and a nearest-match suggestion. |
| **B1-R10** | Narrowing the active form MUST stop only services outside the new closure, leaving shared services running. |
| **B1-R11** | A single service failing to start MUST NOT stop or roll back the rest of the form. |
| **B1-R12** | A form referencing an undeclared profile MUST fail manifest validation at load time. |
| **B1-R13** | `library` MUST be startable with no third-party accounts configured. |
| **B1-R14** | No service MAY declare a `depends_on` crossing a profile boundary, except within a profile whose services are always co-activated. |

## Related

- [ADR-0002 Profiles and forms](../../../00-overview/decisions/0002-profiles-and-forms.md)
- [B2 Lifecycle control](b2-lifecycle.md) — starting and stopping what a form selects
- [F2 Service catalogue](../f-extensibility/f2-service-catalogue.md) — what each service does
- [J2 Search only](../../journeys/j2-search-only.md) · [J3 Download only](../../journeys/j3-download-only.md)
