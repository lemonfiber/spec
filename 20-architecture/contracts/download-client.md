# Contract: Servarr download-client registration

**Status:** Accepted

How lemonfiber registers a download client — SABnzbd or qBittorrent — into a
Servarr application during [seed](../../10-functional/features/d-content/d1-seed.md).
The Servarr apps read this shape; lemonfiber writes it.

**Satisfies:**
[D1-R4](../../10-functional/features/d-content/d1-seed.md),
[D1-R8](../../10-functional/features/d-content/d1-seed.md),
[D1-R11](../../10-functional/features/d-content/d1-seed.md)

---

## Why this is written down

A working \*arr needs each download client registered, and the registration is
not a flat set of keys. Servarr carries a client's connection settings as a
`fields` array whose entries differ by implementation, keyed by an
`implementation` name and a `configContract` — so "register SABnzbd in Sonarr" is
a specific document, not a host and a port.

The field set is stable *for a pinned Servarr version*, and the stack pins its
versions. So lemonfiber writes the fields directly rather than discovering them
at runtime; when a stack upgrade moves a field, this contract and the writer move
with it in the same change. Recording the shape here is what makes that a review
rather than a surprise.

## The request

A POST to `/api/v3/downloadclient` on the target Servarr application, JSON:

```json
{
  "enable": true,
  "protocol": "usenet",
  "name": "SABnzbd",
  "implementation": "Sabnzbd",
  "configContract": "SabnzbdSettings",
  "fields": [
    { "name": "host", "value": "sabnzbd" },
    { "name": "port", "value": 8080 },
    { "name": "apiKey", "value": "<read from the client's own config>" },
    { "name": "tvCategory", "value": "tv" }
  ]
}
```

`protocol` is `usenet` for SABnzbd and `torrent` for qBittorrent. `name` is what
the operator sees in the service's own interface. `implementation` and
`configContract` select the field schema and are not interchangeable.

## The fields lemonfiber sets, per implementation

Only the fields that make a working connection are written; the rest keep the
service's own defaults.

| Implementation | `implementation` | `configContract` | Connection fields | Credential fields |
|----------------|------------------|------------------|-------------------|-------------------|
| SABnzbd | `Sabnzbd` | `SabnzbdSettings` | `host`, `port` | `apiKey` |
| qBittorrent | `QBittorrent` | `QBittorrentSettings` | `host`, `port` | `username`, `password` |

The credential is the client's own, obtained the way that client provides it:
SABnzbd's `apiKey` is read from its `sabnzbd.ini`
([D1-R1](../../10-functional/features/d-content/d1-seed.md)); qBittorrent has no
durable key, so its `username`/`password` is the web UI password lemonfiber
generates and sets
([D1-R16](../../10-functional/features/d-content/d1-seed.md)).

## The category field is named per application

The category tags a download so the application that requested it can find its
own completed items and no others. Its field name is not shared — each Servarr
application names it after the media it manages:

| Application | Category field |
|-------------|----------------|
| Sonarr | `tvCategory` |
| Radarr | `movieCategory` |
| Lidarr | `musicCategory` |

So the same download client is registered into Sonarr with `tvCategory` and into
Radarr with `movieCategory`, each carrying that application's category value. A
registration built for the wrong application names a field the target does not
have.

## Read back by connection, not by name

After writing, the client list is read back from the same endpoint and each
entry's `host` and `port` are recovered from its `fields`. An existing client is
matched by that endpoint rather than by its `name`, so a client an operator
renamed is recognised as the same connection and not duplicated
([D1-R8](../../10-functional/features/d-content/d1-seed.md)). A refusal carries
the application's own words rather than a paraphrase
([D1-R11](../../10-functional/features/d-content/d1-seed.md)).

## Related

- [D1 Service auto-wiring](../../10-functional/features/d-content/d1-seed.md) — the feature this serves
- [stack-manifest.md](stack-manifest.md) — where a service's `api.kind` selects the client shape
- [versioning.md](versioning.md) — why a pinned stack makes a written-down field set safe
