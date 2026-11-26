# Contract: the web API's settings

**Status:** Accepted

Part of the [web API contract](web-api.md): the values the operator sets for the services and
for the core, the closed list of the core's own, and the two writes that change them. The
requirements it describes are listed with the rest of the contract's, under
[Requirements](web-api.md#requirements).

## Settings

```
POST /api/actions/settings-set      POST /api/actions/settings-clear
```

A setting is a value a service's environment reads from the operator rather than from its
manifest: one the core publishes for every service, such as the operator's domain, or one
in a plugin's own namespace, such as the countries an egress guard may exit from
([plugin-manifest](plugin-manifest-service.md#environment--four-kinds-of-value)). The settings live in
the core's settings store, and `GET /api/settings` reads them as `lemonfiber settings --json`
does. Each setting carries its name; whose it is, the core's or a plugin's; each service that
reads it and the variable it is read into; the default its manifest declares, or for one of
the core's own settings the value the core reads while none is recorded; and the
operator's value where one is recorded, so a value still at its default is told apart from one
somebody set to the same text (`ARCH-R254`). A setting that declares choices carries each
value with the `needs` it is a choice under and whether it is one now; each reference
carries its `needs` and whether they are met; and each service waiting for a setting or a
secret is named with what it waits for, as status names it (`ARCH-R351`, `ARCH-R352`).

The same read lists each secret a service's environment names, with whose it is, the services
that read it, where its value came from (the operator, a recipe or a granted credential) and
whether one is held. It never carries the value: the shape it is built from has no field one
could go in, as the credentials read has none (`ARCH-R256`).

Only the operator is answered. A member, a key scoped to one, and a `read` or an `act` key are
refused, because a setting is how the machine is run and the household never sees it.

## The core's own settings

**The core's own settings are a closed list, and this is it.** Beside the settings a
service's environment reads, the settings store holds the ones the core itself reads,
each read back as the core's:

| Core setting | What it holds |
|--------------|---------------|
| `LEMONFIBER_DEVICE_KEY_APPS` | The identities of the operator's own builds a device key may come from, none where none is recorded (`ARCH-R262`) |
| `LEMONFIBER_DASHBOARD_SEARCH` | The address the dashboard's web search box sends a search to, the terms appended to it: an absolute `https` or `http` address, `https://duckduckgo.com/?q=` where none is recorded (`ARCH-R308`) |
| `LEMONFIBER_GUIDE_HOURS` | How many hours from now the live TV guide answers each channel's programmes across: a whole number from 1 to 168, 12 where none is recorded (`D11-R17`) |
| `LEMONFIBER_SIGN_IN_CODES_WAITING` | How many codes to sign a member in by one source may have waiting at once: a whole number from 1 to 100, 3 where none is recorded (`ARCH-R441`) |
| `LEMONFIBER_SIGN_IN_CODES_PER_PERIOD` | How many codes to sign a member in by one source may ask for in each period: a whole number from 1 to 1000, 10 where none is recorded (`ARCH-R441`) |
| `LEMONFIBER_SIGN_IN_CODES_PERIOD` | That period, in whole minutes from 1 to 1440, 15 where none is recorded (`ARCH-R441`) |
| `LEMONFIBER_SIGN_IN_CODES_BY_ADDRESS` | `on` to refuse finishing a sign-in by a code from a network address other than the one that asked for it, `off` where none is recorded (`ARCH-R441`) |
| `LEMONFIBER_BACKUP_LIMIT` | How fast a backup writes at most: a whole number of MiB per second from 1 to 100000, or `off`, `off` where none is recorded. A restore is never held to it (`E3-R18`) |
| `LEMONFIBER_COPY_STALLED_MINUTES` | How many minutes a running backup or restore may write nothing before it reads `stalled`: a whole number from 1 to 1440, 5 where none is recorded (`E3-R19`) |
| `domain` | The domain the household's names are under: labels of letters, digits and hyphens joined by dots, `home.local` where none is recorded (`ARCH-R231`) |
| `LEMONFIBER_LOCALE` | The house's language and region as one `language-REGION` tag, published to every service as `locale`, `en-US` where none is recorded (`A2-R19`) |
| `PLEX_LINK_MODE` | How the request service is linked to Plex: `managed`, `owner` or `fronted`, `managed` where none is recorded (`C6-R26`) |
| `LEMONFIBER_MEMBER_HISTORY` | `off` to keep no viewing history per member and answer none, `on` where none is recorded (`H8-R16`) |

Every other `LEMONFIBER_*` key is `lemonfiber config`'s, read by `GET /api/config`. Each
command refuses the other's names, naming the command that takes the name, so one name
has one writer (`ARCH-R278`).

The two writes take what `lemonfiber settings set` and `lemonfiber settings clear` take:

| Action | Arguments | Answers |
|--------|-----------|---------|
| `settings-set` | `values`, `dry_run`, `offer` | `settings` |
| `settings-clear` | `settings`, `dry_run`, `offer` | `settings` |

`values` is a table of one or more settings to the value each is set to, and `settings`
a list of one or more settings. Each act checks them together, so the settings whose
choices depend on each other move at once, and a value outside its setting's choices, or
an act that leaves another setting's value outside its own, is refused naming the
setting, the value and the choices it has (`ARCH-R350`).

`settings-clear` takes the operator's value away, so the declared default is written again.
Each rehearsal names every entry the change regenerates and every service it restarts, and
answers an offer; the write takes that offer and refuses where what it would change moved since,
naming what moved, as the plugin writes do (`ARCH-R146`). Each write is journalled (`ARCH-R255`).

Each setting an answer moves carries `default`, what it falls back to while it holds no operator
value: the core's own value for one of the core's settings, the one default every reader whose
`needs` are met declares, each such reader's own where they differ, or none where nothing
declares one. A cleared setting is read with the value written again, a setting set to its
default with that said, and a reader whose `needs` are unmet is listed with `met: false`. The
default is part of what the offer answers, so a yes given before it moved is refused naming it,
and the journal keeps the default as it was at the act (`ARCH-R461`). The command line says the
same beside each setting it moves (`ARCH-R462`).
A value is written as exactly itself: nothing in it is substituted (`ARCH-R230`).

**A secret is not written here.** A secret a manifest names is entered as an input of the
install or update that first needs it, never repeated back, and is replaced afterwards at the
terminal, as every credential is
([ADR-0031](../../00-overview/decisions/0031-a-plugin-and-a-choice-are-web-writes-a-credential-is-not.md)).
Naming a secret to either write is refused, naming it (`ARCH-R256`).

The settings ride the operator's event stream as their envelope, a `settings` event, sent when
a client connects and whenever one changes, and only to the operator, by the per-run token or
an operator session: never on a member's stream and never to a key of any scope, so the stream
tells nobody what the read refuses them (`ARCH-R257`).

## Related

- [The web API](web-api.md) — the contract this page is part of
- [Plugin manifest: a service](plugin-manifest-service.md) — the settings a service's environment reads
