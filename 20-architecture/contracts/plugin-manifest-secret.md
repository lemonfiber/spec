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
id     = "upstream-key"
of     = "sabnzbd"
minted = true
why    = "The key the adapter signs in to SABnzbd with"

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
own secrets file (`ARCH-R247`). A value captured or entered is held in the secret store in
the plugin's namespace, as `<plugin id>:<secret id>`. An assembled part's plugin id is its
service's, so the egress guard's key is `gluetun:wireguard-key` whether the bundle
assembles the part or installs it. Of an assembled part's secrets, only one the operator
enters is held in the store; one whose `of` names another service, as the curators' keys
Unpackerr and Recyclarr declare do, is a credential that crosses (`ARCH-R275`).

**A minted secret is lemonfiber's to make.** `minted = true` declares a credential the
plugin's own service is given rather than one it hands out: lemonfiber makes the value
at install, before any of the plugin's services first starts, as 32 lowercase hex
characters from the operating system's random source, and holds it in the secret store
as `<plugin id>:<secret id>`. Nobody is asked for it and nothing shows it. It reaches the
service through its `env` (`{ secret }`) or a [starting file](plugin-manifest-service.md#a-secret-in-a-starting-file),
and the adapter that `fronts` the service through its `upstream`. A minted secret's `of`
names the plugin's own service it is the credential of, and no recipe captures it. A part moved in place
keeps the credential its service already answers to: where lemonfiber reads it from the
service's configuration before the move, the move files that value under the secret once
and mints nothing (`ARCH-R315`). `plugin record` and a proof mint a throwaway one for
their own container, as they take a throwaway copy of its starting files.

**A credential that crosses is read where it is held.** One `F14-R18` or `F14-R20` lets
cross is not copied into the secret store. lemonfiber reads it from the store that holds
it each time it writes an entry naming it, so replacing it regenerates every entry that
reads it, and no stale copy is left behind (`ARCH-R277`).

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
