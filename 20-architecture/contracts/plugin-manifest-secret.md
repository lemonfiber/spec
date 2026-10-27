# Contract: `plugin.toml` — `[[secret]]` and `[[override]]`

**Status:** Accepted

Part of the [`plugin.toml` contract](plugin-manifest.md): the secrets a plugin holds and
the bundled things it changes, each declared before it is held. The requirements this
page describes are listed with the rest of the contract's, under
[Requirements](plugin-manifest.md#requirements).

## `[[secret]]` and `[[override]]` — declared before they are held

```toml
[[secret]]
id   = "api-key"
of   = "komga"
why  = "Read the library counts the dashboard panel shows"

[[secret]]
id   = "series-key"
of   = "sonarr"
for  = "subtitle.find"
why  = "Read the series it finds subtitles for"

[[secret]]
id     = "upstream-key"
of     = "sabnzbd"
minted = true
why    = "The key the adapter signs in to SABnzbd with"
carried_from = { file = "/config/sabnzbd.ini", format = "ini", key = "misc.api_key" }

[[override]]
id   = "homepage.services"
why  = "Add its own entry to the bundled dashboard"
```

`F3-R17` fails validation on a secret captured but not declared, and `F3-R18` on
a bundled thing changed but not declared. Both need somewhere to declare one.

A secret a service's [`env`](plugin-manifest-service.md#environment--four-kinds-of-value) names is declared here
too. Its value is one lemonfiber mints, one a recipe captures, a credential `F14-R18` or
`F14-R20` lets cross to the plugin, or, where none of those supplies it, one the operator
enters at install without it being shown. Whatever its source, it reaches the container only through the service's
own secrets file (`ARCH-R247`). One only the operator can enter that the service needs to start declares
`recorded_with`, the stand-in a recording runs it with ([`ARCH-R336`](plugin-manifest-service.md#environment--four-kinds-of-value)). One the
service needs only beside some settings' values declares `needs`, as a setting reference
does: the egress guard's WireGuard key is asked for only where `gluetun:vpn-type` is
`wireguard`, and its OpenVPN username and password only where it is `openvpn`. Where
`needs` is not met, nobody is asked for the secret and it is not written, though a value already held is kept
(`ARCH-R349`); where it is met and no value is held, the service waits for it, named
(`ARCH-R351`). A value captured or entered is held in the secret store in
the plugin's namespace, as `<plugin id>:<secret id>`. An assembled part's plugin id is its
service's, so the egress guard's key is `gluetun:wireguard-key` whether the bundle
assembles the part or installs it. Of an assembled part's secrets, only one the operator
enters is held in the store; one whose `of` names another service, as the curators' keys
Unpackerr and Recyclarr declare do, is a credential that crosses (`ARCH-R275`).

**A minted secret is lemonfiber's to make.** `minted = true` declares a credential the
plugin's own service is given rather than one it hands out: lemonfiber makes the value
at install, before any of the plugin's services first starts, as 32 lowercase hex
characters from the operating system's random source, and holds it in the secret store
as `<plugin id>:<secret id>`. `minted = "password"` declares one for a service whose own
rules refuse a value of one character class, as an administrator password often is: 32
characters from the same source, holding at least one uppercase letter, one lowercase
letter, one digit and one of `-`, `_`, `.` and `~`, which every environment file, URL and
form takes as written. Nobody is asked for it and nothing shows it. It reaches the
service through its `env` (`{ secret }`) or a [starting file](plugin-manifest-service.md#a-secret-in-a-starting-file),
and the adapter that `fronts` the service through its `upstream`. A minted secret's `of`
names the plugin's own service it is the credential of, and no recipe captures it. A part moved in place
keeps the credential its service already answers to, secret by secret, by the adapter's
`upstream` field each one fills: a `username` or `password` is the account lemonfiber set up
on the service, and any other is the credential the service wrote itself, read from where
the secret's `carried_from` says. The move files each under its secret once (`ARCH-R315`).

**`carried_from` says where a moved service keeps its own credential.** `file` is a path
inside the replaced service's container, beneath its `config_path`; `format` is `xml`,
`json`, `yaml` or `ini`; `key` is the dotted path to the value in that file:
`Config.ApiKey`, `main.apiKey`, `auth.apikey`, or for `ini` the section and entry,
`misc.api_key`. The move reads the file from the service's configuration directory on the
host and refuses one that leads away. Where it holds no value, the move takes the
credential lemonfiber recorded for the service, and mints one only where neither holds any.
A secret whose service writes no credential of its own, as one lemonfiber minted and
handed it, declares none and is carried as the credential lemonfiber recorded. `plugin record` and a proof mint a throwaway one for
their own container, as they take a throwaway copy of its starting files.

**`was` names the key an earlier release kept it under.** A secret the stack's environment
file held before the stores did, as the egress guard's key was held under
`WIREGUARD_PRIVATE_KEY`, declares that key, and the one filing that moves values into the
stores reads it from there, never from a list the core keeps (`ARCH-R249`, [`ARCH-R337`](plugin-manifest-service.md#environment--four-kinds-of-value)).

**A credential that crosses is read where it is held.** One `F14-R18` or `F14-R20` lets
cross is not copied into the secret store. lemonfiber reads it from the store that holds
it each time it writes an entry naming it, so replacing it regenerates every entry that
reads it, and no stale copy is left behind (`ARCH-R277`).

**A credential the stack records is named for what it reaches, never for its service.**
A key or password lemonfiber keeps for a service of the stack or of a first-party plugin
is named `<CAPABILITY>[_<QUALIFIER>][_<N>]_<ENDING>`:

- **The capability** the service provides first, in the order its manifest lists them,
  in upper case with `_` for `.` and `-`; an administrator's password on the service
  filling `identity.source` is named for `identity.source`.
- **The qualifier** the capability's contract tells its fillers apart by: for
  `library.curate` the media type the service files first, for `media.serve` none on the
  service filling `identity.source` and the media type it serves first on any other, and
  none for any other capability.
- **An ordinal**, `2` and onwards, only where two services would take one name: each
  after the first, in the order it was installed, recorded with the service once and
  kept while it is installed (`ARCH-R347`).
- **The ending**: `API_KEY`, `PASSWORD`, `USERNAME` or `ADMIN_PASSWORD`.

So the curator filing television keeps its key as `LIBRARY_CURATE_TV_API_KEY`, the torrent
client's password is `DOWNLOAD_TORRENT_PASSWORD`, the media server's administrator
password is `IDENTITY_SOURCE_ADMIN_PASSWORD` and an audiobook server's is
`MEDIA_SERVE_AUDIOBOOKS_PASSWORD`. A plugin's own setting and secret names keep its id as
their namespace (`gluetun:wireguard-key`), and so does what a third-party plugin's own
services hold: the plugin chose that id, and it is the plugin's to keep.

A stack an earlier release set up holds each under the service's id, `SONARR_API_KEY`.
The first run of the release that names them by capability moves each to its name once,
with a rotation's pending replacement beside it, journalled by both names and never by
value, and reads the earlier name until it has; a grant recorded under an earlier name is
rewritten with it (`ARCH-R342`).

**A third-party plugin is granted what crosses to it.** A `[[secret]]` whose `of` names
another service declares `for`, the capability one of the plugin's own services provides
that the credential is needed to fill. A third-party plugin declares at most one such
secret for each capability it fills; a manifest declaring two for one capability, or a
`for` naming a capability none of its services provides, is refused at install and
update, naming the secret (`ARCH-R322`). A first-party plugin may leave `for` out,
because `F14-R18` lets the stack's credentials cross to it whole.

What crosses to a third-party plugin is a grant, and the operator gives it. The install
or update reading names each credential that would cross as `<setting>@<plugin>`, with
the capability it is for and the service whose credential it is; the credential is named
by its setting, as the [credentials read](web-api.md) lists it, never by value. The act
takes the grant as another approval (`--approve LIBRARY_CURATE_TV_API_KEY@comics`), and refuses
unless every grant the reading names was approved. An update names every grant again
and takes none over unapproved: one the operator leaves out stops crossing when the
update is made. Each grant given or ended is journalled with the operation that gives or
ends it, by credential and plugin, so undoing that operation ends or restores the grant
(`ARCH-R323`). A granted credential crosses as one `F14-R18` lets cross does: read where
it is held, into the plugin's secrets file and into each connection an ask of the plugin
makes to the service whose credential it is.

**A grant is revoked at the credentials surface.** `lemonfiber credentials revoke
<plugin> <credential>` and the `credentials-revoke` action end one grant: every entry and
connection of the plugin is written again without the credential, the plugin's services
that read it restart, and the whole is journalled as one operation that undo reverses.
It is rehearsed and takes an offer as a plugin write does. The plugin stays installed,
and each capability the credential was for is reported unfilled for that reason; a
plugin and credential with no grant between them are refused, naming the grants the
plugin holds (`ARCH-R324`). The credentials read lists every grant beside the credential
it crosses: the plugin, the capability it is for and when it was approved, with no value
(`ARCH-R325`).

**The journal holds a secret's fingerprint, never its value.** A secret's change is
journalled with the stable fingerprint of the value before and after it, as
[A7](../../10-functional/features/a-getting-started/a7-credential-management.md)
references a credential, and never with the value, sealed or otherwise. The secret store
keeps each secret's one previous value. Undoing the change restores it only while the
values held still match the fingerprints the entry recorded; otherwise the undo says the
secret must be replaced at the terminal, naming it (`ARCH-R276`).

**What counts as capturing, and what counts as changing.** A recipe is
declarable before it is runnable and its block is where both verbs are written,
so both rules are decided by reading the manifest rather than by watching one
run:

| Declared | Held to |
|----------|---------|
| `[[secret]]` | every `[[recipe.step]].capture` |
| `[[override]]` | every `[[recipe.step]].call` whose method is not one that only asks and whose `to` is a service the stack ships |

A secret is matched on the captured value's **name** and nothing else. `of` and
a capture's `origin` both answer *whose*, and they answer it in different
vocabularies — one names a service, the other a kind of source — so holding them
to each other would be inventing a correspondence this contract does not state,
and refusing manifests for not keeping it. What both do name is the value. A
capture whose name no `[[secret]]` carries is refused, naming the value and its
origin.

Every captured value, rather than the ones that look like credentials. There is
no field saying which is which and there should not be: a library id read back
from a first-run flow is a value the plugin now holds and can carry somewhere,
and a format in which the author decides what is worth declaring is one where
the interesting cases are the ones nobody declared.

An override names an owner and what of theirs, and the **owner** is the half a
call can be held to by reading, because a path is a route on a service rather
than the name of a setting. Three destinations, and only one of them is this: a
call to one of the plugin's own services changes what the plugin installed and
is what a recipe is for; a call to a DNS name outside the stack leaves the
machine and is declared as a host rather than as an override; a call to a
service the stack ships is refused, naming the call and the service, unless an
`[[override]]` names that owner. The verbs that change are written as the
complement of the ones that only ask, so a verb added to what a call may use is
a change its author has to declare rather than one nobody is told about.

So both blocks are absent from a manifest declaring no recipe, and are filled in
one that declares a recipe which captures or changes anything. An earlier
reading of this section — that both are in practice always absent until `F8`
arrives in `0.18.0` — held only while a recipe could not be written down at all.
They are in the format for the reason they always were: a rule that cannot be
stated for want of a field is not being enforced, and adding the field later
would make every manifest written against this version wrong.
