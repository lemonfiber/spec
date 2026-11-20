# Contract: the web API's view of the machine

**Status:** Accepted

Part of the [web API contract](web-api.md): two reads that answer the operator about the
machine itself, namely what a stop would interrupt and how the surface is served. The
requirements it describes are listed with the rest of the contract's, under
[Requirements](web-api.md#requirements).

## What a stop would interrupt

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
  - its `subject` and `issuer`, as RFC 4514 strings;
  - whether it is `self_signed`;
  - the `names` it is made out to;
  - `valid_from` and `valid_until`, in RFC 3339.

It is read off what the run settled when it began, and it makes, replaces and writes nothing.
It never carries the private key in any form, the certificate's DER or PEM encoding, a file
path or the per-run token. A certificate is recognised by its fingerprint, and nothing a caller
does with this answer needs the rest. It takes no parameter, and it is answered and refused as
the in-flight read is.

## Related

- [web-api](web-api.md) — the contract this page is part of, and its requirements
- [web-api-getting-in](web-api-getting-in.md) — who is answered and who is refused
- [N1](../../10-functional/features/n-companion/n1-companion-app.md) — the companion's screen for how the surface is served (`N1-R81`)
- [N2](../../10-functional/features/n-companion/n2-operator-companion.md) — what a stop would interrupt, before it is agreed to (`N2-R42`)
- [C6](../../10-functional/features/c-trust/c6-web-security.md) — the certificate a phone pins
