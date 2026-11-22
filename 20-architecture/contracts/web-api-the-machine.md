# Contract: the web API's view of the machine

**Status:** Accepted

Part of the [web API contract](web-api.md): what answers the operator about the machine
itself, namely what a stop would interrupt, how the surface is served, what setup
decided, and what the operator said to leave alone. The requirements it describes are listed with the rest of the contract's, under
[Requirements](web-api.md#requirements).

## What a stop would interrupt

```
GET /api/in-flight?…
```

`GET /api/in-flight` answers the `in-flight` envelope: each download still coming down inside
what stopping the named forms and services would stop, with the kind of client holding it
(`protocol`), its `name` as that client gives it, and how far along it is (`progress`, from 0
to 100) (`ARCH-R447`). It takes `forms` and `services`, each repeatable, which are the arguments
`down` takes, and naming neither asks about the whole stack. Only the download clients that
stop would stop are asked, and they are asked live. A client that does not answer adds
nothing, a finished download is not listed, and an empty list is an answer rather than a
refusal. It changes nothing. The command line asks the same question, of the same forms and
services, before `lemonfiber down` stops anything. An operator session and a key whose scope
reaches reads are answered. A member session and a key scoped to a member are refused.

## How the surface is served

```
GET /api/served
```

`GET /api/served` answers the `served` envelope that `lemonfiber ui` settles when it begins
serving, for the run answering (`ARCH-R448`). The envelope carries:

- the `port` the run listens on;
- whether it is `encrypted`, and whether it is offered to the `network`;
- `named`, the name a request has to carry beyond this machine, where the run is encrypted
  on a network;
- `unrecorded`, why where it is served could not be written down, where it could not;
- `certificate`, where the run is encrypted, which is the certificate the run presents:
  - its `fingerprint`, SHA-256 over its DER encoding in lower-case hex, which is the value a
    phone pins (`N1-R18`);
  - its `subject` and `issuer`, as RFC 4514 strings, with `subject_cut` and `issuer_cut`
    saying whether each was cut short;
  - whether it is `self_signed`;
  - the `names` it is made out to, its subject alternative names, with `names_more`
    counting the names left out for being too many, too long to show, or not written as text;
  - `valid_from` and `valid_until`, as instants, in whole seconds since the epoch
    (`ARCH-R274`).

What a certificate says is the certificate's, and anybody who made one could have written
anything in it, so what is read from it is bounded and written so that it cannot change how
it is shown:

- A control or layout character in a subject, an issuer or a name is written as `\xx`,
  the RFC 4514 hex pair for that byte.
- A subject or issuer longer than 512 characters as written is its first 512, with its
  `_cut` field `true`.
- `names` holds at most 64 names, each whole. A name longer than 512 characters as written,
  a name not written as text, and every name past the sixty-fourth are left out and counted
  in `names_more`.
- No string carries a remark about what was left out. The `_cut` fields and `names_more`
  say it, so a caller never mistakes a remark for a name.

It is read off what the run settled when it began, and it makes, replaces and writes nothing.
It never carries the private key in any form, the certificate's DER or PEM encoding, a file
path or the per-run token. A certificate is recognised by its fingerprint, and nothing a caller
does with this answer needs the rest. It takes no parameter, and it is answered and refused as
the in-flight read is.

## What setup decided

```
GET /api/config?…
```

Setup writes its answers as settings, and every one of them can be changed again
afterwards ([A4](../../10-functional/features/a-getting-started/a4-reconfiguration.md)). A
setup that skipped a step left that step's settings unwritten: the provider of a protocol
nobody chose, the user the containers run as on a platform that does not ask, and how the
media server runs where only one way is offered. Listing only the settings the configuration holds would therefore leave a caller no
way to learn that such a decision exists, let alone change it.

So the `config` read that `GET /api/config` and `lemonfiber config --json` answer carries
`decisions` beside `settings`: one entry for each answer setup writes, in the core's order,
whether or not the configuration holds it (`ARCH-R449`). Each entry has:

- `key`, the setting the answer is kept in;
- `cost`, `cheap` for a change applied with a restart of what it affects, or
  `consequential` for one stated and confirmed before it is applied (`A4-R3`);
- `affects`, what changing it affects, in the core's words;
- `held`, whether it is held, in the configuration or the settings store;
- `credential`, whether its value is withheld as a credential;
- `setting`, the name `settings-set` takes, where the answer is kept in the settings store
  rather than the configuration, such as the house's locale and the VPN's provider, and
  absent where `config-set` takes it.

An entry never carries the value. A value is read where it is held, in this read's
`settings` or in the `settings` read, withheld there as it always is. The keys are a closed
set the contract declares, so a decision the core adds is a change to the contract that
every client sees, rather than a setting that appears without anyone deciding how a client
offers it. A change to one of them is still asked as every change is, through `config-set`
or, for an answer that names its `setting`, through `settings-set`, and each is rehearsed
before it is written: `config-set` unconfirmed answers the review, and `settings-set` its
rehearsal and offer. Where the change turns a way of downloading on, the review's `opens`
names, in order, the accounts to obtain and then each setting the protocol needs.

## What the operator said to leave alone

An operator can declare any area unmanaged, after which lemonfiber observes it and never
writes it (`F1-R7`). The declarations are one setting, `LEMONFIBER_UNMANAGED`, written as
`area=reason` pairs separated by commas, and the `settings` of the `config` read carry that
line as it is written. A line tells a caller what was written, not what it stops: an entry
with a blank half declares nothing, and a misspelt area covers nothing while the operator
believes it does.

So the same read carries `unmanaged` beside `settings` and `decisions`: one entry for each
area the declaration's parser keeps, in the order written (`ARCH-R453`). Each entry has:

- `area`, the name as written, and `area_cut`, whether it was cut short;
- `why`, the reason the operator gave, and `why_cut`, whether it was cut short;
- `covers`, each thing the area covers now by the core's own rule, which is the thing it
  names and anything beneath it after a `/`. Each has its `kind` and its `name`:
  - `service`, a service the stack runs, its manifest's and those its installed plugins
    brought, which is not seeded and is observed rather than wired;
  - `path`, a file lemonfiber writes, a carried stack's file by where it sits beneath the
    stack's directory and the project's own files by name, which is not written on any run;
  - `setting`, a setting the configuration holds or a decision names, which `config-set`
    refuses with the operator's reason;
- `covers_more`, the number of covered things left out.

The kind is taken from what is covered, never from the shape of the name, since a stack may
name a service `config`, and one area can cover things of several kinds. An empty `covers`
says the area covers nothing in this stack. `unmanaged` is always present: an empty list
means nothing is declared, and a caller tells an older core by the field being absent.

Each area and reason is the operator's own text, so what is read from it is bounded and
written so that it cannot change how it is shown:

- A control or layout character in an `area` or a `why` is written as `\xx`, each byte of
  its UTF-8 in hex.
- An `area` or a `why` longer than 512 characters as written is its first 512, with its
  `_cut` field `true`.
- At most 64 entries are listed, and those left out are counted in `unmanaged_more`. At most
  64 covered things are listed for an entry, and those left out are counted in its
  `covers_more`.
- A client renders `area`, `why` and `name` as plain text, never as markup, an address or a
  command it runs.

The field is read off the configuration as it stands and changes nothing. It is answered and
refused as the read is without it, and a change to the setting is asked through `config-set`
as every change is, whose answer carries the list as it would stand.

## Related

- [web-api](web-api.md) — the contract this page is part of, and its requirements
- [web-api-getting-in](web-api-getting-in.md) — who is answered and who is refused
- [N1](../../10-functional/features/n-companion/n1-companion-app.md) — the companion's screen for how the surface is served (`N1-R81`)
- [N2](../../10-functional/features/n-companion/n2-operator-companion.md) — what a stop would interrupt, before it is agreed to (`N2-R42`)
- [C6](../../10-functional/features/c-trust/c6-web-security.md) — the certificate a phone pins
- [A4](../../10-functional/features/a-getting-started/a4-reconfiguration.md) — what changing a decision setup made costs, and how it is reviewed
- [N1](../../10-functional/features/n-companion/n1-companion-app.md) — the companion's screen for what setup decided (`N1-R82`, `N1-R83`)
- [F1](../../10-functional/features/f-extensibility/f1-customisation.md) — declaring an area unmanaged (`F1-R7`)
- [N19](../../10-functional/features/n-companion/n19-getting-underneath-it.md) — the companion shows each area declared unmanaged (`N19-R5`)
