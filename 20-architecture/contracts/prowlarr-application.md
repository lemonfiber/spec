# Contract: Prowlarr application registration

**Status:** Accepted

How lemonfiber registers a media-filing \*arr — Sonarr, Radarr or Lidarr — as an
*application* in Prowlarr during
[seed](../../10-functional/features/d-content/d1-seed.md), so Prowlarr syncs its
indexers to that \*arr. Prowlarr reads this shape; lemonfiber writes it.

**Satisfies:**
[D1-R4](../../10-functional/features/d-content/d1-seed.md),
[D1-R8](../../10-functional/features/d-content/d1-seed.md),
[D1-R11](../../10-functional/features/d-content/d1-seed.md)

---

## Why this is written down

Prowlarr's native app sync is what spares the operator from pasting one indexer
into three \*arrs by hand. It is driven by an *application* entry per \*arr, and —
exactly like a download client — that entry is not a flat set of keys. Prowlarr
carries the connection settings as a `fields` array keyed by an `implementation`
name and a `configContract`, so "register Sonarr in Prowlarr" is a specific
document, not a name and an address.

The field set is stable *for a pinned Prowlarr version*, and the stack pins its
versions. So lemonfiber writes the fields directly rather than discovering them
at runtime; when a stack upgrade moves a field, this contract and the writer move
with it in the same change. Recording the shape here is what makes that a review
rather than a surprise.

This is the same shape as the
[download-client contract](download-client.md), pointed the other way: there a
\*arr is told about a client, here Prowlarr is told about a \*arr.

## Prowlarr speaks `/api/v1`

Prowlarr shares the Servarr HTTP shape but versions its API at `/api/v1`, not the
`/api/v3` of Sonarr and Radarr. The application endpoints are therefore
`/api/v1/applications`. This is the reason app sync is a Prowlarr-specific writer
rather than a reuse of the Servarr client the media \*arrs share.

## The request

A POST to `/api/v1/applications` on Prowlarr, JSON:

```json
{
  "syncLevel": "fullSync",
  "name": "Sonarr",
  "implementation": "Sonarr",
  "configContract": "SonarrSettings",
  "fields": [
    { "name": "prowlarrUrl", "value": "http://prowlarr:9696" },
    { "name": "baseUrl", "value": "http://sonarr:8989" },
    { "name": "apiKey", "value": "<read from the *arr's own config>" },
    { "name": "syncCategories", "value": [5000, 5010, 5020, 5030, 5040, 5045, 5050] }
  ]
}
```

`syncLevel` is `fullSync` — Prowlarr both adds indexers to the \*arr and keeps
them in step. `name` is what the operator sees in Prowlarr's own interface.
`implementation` and `configContract` select the field schema and are not
interchangeable.

## The fields lemonfiber sets, per implementation

Only the fields that make a working sync are written; the rest keep Prowlarr's
own defaults.

| Application | `implementation` | `configContract` | Connection fields | Credential field |
|-------------|------------------|------------------|-------------------|------------------|
| Sonarr | `Sonarr` | `SonarrSettings` | `prowlarrUrl`, `baseUrl`, `syncCategories` | `apiKey` |
| Radarr | `Radarr` | `RadarrSettings` | `prowlarrUrl`, `baseUrl`, `syncCategories` | `apiKey` |
| Lidarr | `Lidarr` | `LidarrSettings` | `prowlarrUrl`, `baseUrl`, `syncCategories` | `apiKey` |

- `prowlarrUrl` is the address the \*arr reaches Prowlarr back on, and `baseUrl`
  is the address Prowlarr reaches the \*arr on — both on the stack's own network,
  by container name, because Prowlarr talks to the \*arr across that network and
  not through the host.
- `apiKey` is the target \*arr's own key, read from its configuration the way
  every service key is
  ([D1-R1](../../10-functional/features/d-content/d1-seed.md)) — never Prowlarr's.
  It is what lets Prowlarr write indexers into that \*arr.

## The sync categories are the standard set for the media

`syncCategories` tells Prowlarr which release categories to sync to the \*arr, and
it is named per application after the media that application manages — a \*arr
that files television has no use for a music category. The values are the
standard Newznab categories for that media, so an indexer's releases reach the
application that wants them:

| Application | Media | Category base | Standard categories |
|-------------|-------|---------------|---------------------|
| Sonarr | Television | `5000` | `5000, 5010, 5020, 5030, 5040, 5045, 5050` |
| Radarr | Movies | `2000` | `2000, 2010, 2020, 2030, 2040, 2045, 2050, 2060, 2070, 2080` |
| Lidarr | Music | `3000` | `3000, 3010, 3020, 3030, 3040, 3050, 3060` |

An application registered with no categories syncs nothing, so the categories are
part of a working connection rather than a preference — which is why they are
written rather than left to a default.

## Read back by connection, not by name

After writing, the application list is read back from `/api/v1/applications` and
each entry's `baseUrl` is recovered from its `fields`. An existing application is
matched by that address rather than by its `name`, so one an operator renamed is
recognised as the same connection and not duplicated
([D1-R8](../../10-functional/features/d-content/d1-seed.md)). A refusal carries
Prowlarr's own words rather than a paraphrase
([D1-R11](../../10-functional/features/d-content/d1-seed.md)).

## Bindery is not among the implementations

Prowlarr's app sync supports a fixed set of Servarr applications, and Bindery is
not one of them. It consumes Prowlarr's Torznab endpoints instead, wired
explicitly rather than through this document
([D1-R15](../../10-functional/features/d-content/d1-seed.md)). That asymmetry is
specified, not glossed.

## Related

- [D1 Service auto-wiring](../../10-functional/features/d-content/d1-seed.md) — the feature this serves
- [download-client.md](download-client.md) — the same `fields` shape, pointed the other way
- [stack-manifest.md](stack-manifest.md) — where a service's `api.kind` selects the client shape
- [versioning.md](versioning.md) — why a pinned stack makes a written-down field set safe
