# Contract: the web API's view of the plugin catalogue

**Status:** Accepted

Part of the [web API contract](web-api.md): what the operator reads about the plugins the
catalogue offers, before choosing one to install. The requirements it describes are listed
with the rest of the contract's, under [Requirements](web-api.md#requirements).

## What can be installed

```
GET /api/plugins/catalogue
```

`GET /api/plugins/catalogue` answers as `lemonfiber plugin catalogue --json` does, from the
verified catalogue index, listing nothing the index's signature does not cover
(`ARCH-R153`). Its envelope is the
`plugin-catalogue` kind, and its `state` is one of three, each a normal answer, so an
empty list never stands in for a catalogue that was not read (`ARCH-R450`):

- `listed`: the index was fetched and verified. The answer carries the index's
  `published` date and `serial`, its `entries`, and `unreadable`, how many entries the
  index holds that this build could not list because they lack a fact an entry needs,
  such as an index cut before the index carried them.
- `off`: reaching the catalogue is switched off, and nothing was asked of it. The answer
  carries `setting`: the `key` that is switched off, `LEMONFIBER_OFFLINE` where every
  request is off and the catalogue's own switch otherwise; the `value` that turns it on;
  and the `action` that writes it, `config-set` for both today. A client offers that
  change through the action's own review and never writes it unasked.
- `failed`: the index or its signature could not be fetched, did not verify, could not be
  read, or is older than one this machine verified. The answer carries `failure`, the
  `code` and `summary` an install by name would have been refused with.

Each entry carries the plugin's `id`, which is the name it is installed by, and its
`name`, `description`, `version` and `without_it` as the index signs them (`ARCH-R451`).
An entry for a plugin installed here carries `installed`: the `version` installed and
`newer`, whether the catalogue's version is above it by semver, decided by the core so no
client compares versions. An entry never carries the origin, the revision, the digest, the
grants or the credentials the plugin asks for: those are the install rehearsal's. The read
is the operator's, as installing is; it asks the catalogue only where reaching it is on,
and it remembers nothing, so it never moves the newest index this machine has verified
(`ARCH-R452`).

## Related

- [web-api](web-api.md) — the contract this page is part of, and its requirements
- [web-api-getting-in](web-api-getting-in.md) — who is answered and who is refused
- [F5](../../10-functional/features/f-extensibility/f5-plugin-catalogue.md) — the catalogue, its signed index and installing by name
- [lemonfiber-plugins](../../30-repos/lemonfiber-plugins.md) — what a catalogue release's index carries (`REPO-R108`)
- [N5](../../10-functional/features/n-companion/n5-connecting-the-stack.md) — the companion's catalogue, and what an entry carries (`N5-R8`)
