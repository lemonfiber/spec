# Contract: the certificate a program serves beyond its machine

**Status:** Accepted

How a program lemonfiber builds comes by the certificate it serves to clients on other
machines, keeps it current, and keeps its keys. One page, so that every such program, the MCP
server's HTTP mode first and the core's remote access after it, offers the same four ways,
reads the same settings, keeps the same state and fails the same way, while each implements it
in its own language.

**Satisfies:**
[F13-R8](../../10-functional/features/f-extensibility/f13-mcp.md),
[F13-R12](../../10-functional/features/f-extensibility/f13-mcp.md),
[F13-R13](../../10-functional/features/f-extensibility/f13-mcp.md)

---

## Why this is written down

Who can check a certificate decides which certificate is any use. A client lemonfiber wrote
holds the pin of the certificate the stack made itself
([ADR-0018](../../00-overview/decisions/0018-trusting-a-stack-over-the-local-network.md),
[ADR-0025](../../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md)). A
desktop client can be told to trust a root the operator installed. An assistant on a phone or
in a browser can be told nothing: its provider's servers make the connection, and they accept a
chain to a publicly trusted authority and nothing else.

So there is no one right way, and there must always be a way that depends on no company outside
the operator's house. Four are offered, each said plainly to be checkable by whom. Getting a
publicly trusted certificate is a protocol, ACME ([RFC 8555](https://www.rfc-editor.org/rfc/rfc8555)),
and keeping any certificate is a schedule; two programs that each invented their settings,
their state and their renewal would be two things to learn and two ways to fail. So all of it
is written here once. The code is not shared: the core is Rust and the MCP server Python, and a
library crossing the two would be a third program to keep. What is shared is everything an
operator, a volume or a test can see.

## The four ways

`LEMONFIBER_TLS_MODE` chooses one. Setting both of `files`' paths chooses `files`, and where
nothing is chosen `pinned` is served: the one way that trusts nothing beyond a single
certificate and depends on nobody. `acme` and `private-ca` are served only where
`LEMONFIBER_TLS_MODE` names them, because each extends what has to be trusted: an authority's
word, or a root the operator installs.

| Mode | The certificate | Who can check it |
|---|---|---|
| `files` | The operator's own: `LEMONFIBER_TLS_CERTIFICATE` and `LEMONFIBER_TLS_PRIVATE_KEY` | Whoever trusts the authority that issued it |
| `acme` | Obtained and renewed from any RFC 8555 authority: a public one (Let's Encrypt by default, ZeroSSL, Google Trust Services, Buypass) or the operator's own (step-ca, any private ACME directory; Pebble in tests) | A public authority: every client, the assistants reached from a provider's servers included. The operator's own: whoever trusts its root |
| `private-ca` | Issued by a root lemonfiber makes for this program and constrains to its names | Whoever installed that root: the operator's own devices and desktop clients. Not an assistant reached from a provider's servers |
| `pinned` | Made by the program itself, its SHA-256 fingerprint printed to pin | A client given the fingerprint, as the companion is given the stack's. Not an assistant reached from a provider's servers |

`private-ca` and `pinned` depend on nobody, and `acme` against the operator's own authority
depends on nobody but the operator. At start the program writes to its log which mode it
serves and who can check it, in those words; where the mode is `private-ca` or `pinned` it also
says that an assistant on a phone or in a browser reached through its provider cannot connect.

In every mode nothing is answered in plain HTTP but the token of a pending HTTP-01 challenge.

The names a certificate is for are `LEMONFIBER_NAMES`: one or more host names, or for
`private-ca` and `pinned` also addresses, separated by commas.

### `files`

Both files are read at start and refused, by name, where either is unreadable, the key does not
match the certificate, the certificate has expired, or it does not cover every name in
`LEMONFIBER_NAMES` where that is set. They are read again, with no restart, when either
changes, so a certificate renewed by something else is taken. This is also how two programs on
one machine share one certificate: a program beside a core that already holds one for the name
reads the core's files and opens no second account.

### `acme`

| Setting | Default | Holds |
|---|---|---|
| `LEMONFIBER_ACME_DIRECTORY` | `https://acme-v02.api.letsencrypt.org/directory` | Any RFC 8555 directory |
| `LEMONFIBER_ACME_ROOTS` | the system's | A PEM file of the roots the directory's own TLS is checked against, for an authority the operator runs |
| `LEMONFIBER_ACME_CONTACT` | none | A `mailto:` address the authority may write to |
| `LEMONFIBER_ACME_EAB_KID`, `LEMONFIBER_ACME_EAB_HMAC_FILE` | none | External Account Binding (RFC 8555 §7.3.4): the key identifier, and a file holding the HMAC key |
| `LEMONFIBER_ACME_CHALLENGE` | `tls-alpn-01` | `tls-alpn-01`, `http-01` or `dns-01` |
| `LEMONFIBER_ACME_DNS_PROVIDER` | none | The provider DNS-01 is answered through, by its name below |

**Choosing `acme` is agreeing to the authority's terms.** It is the operator accepting the terms
of service the directory publishes, as Caddy treats it. The program writes the terms' address to
its log when it first registers an account, and the documentation of every program that
implements this page says so where it introduces the mode. Where the directory says an external
account is required and no binding is given, the program refuses to start, naming the two
settings.

**TLS-ALPN-01** ([RFC 8737](https://www.rfc-editor.org/rfc/rfc8737)) is answered on the port the
program serves on, while it serves. The listener reads each connection's ClientHello before any
handshake; a connection asking for `acme-tls/1` and nothing else is answered with the challenge
certificate, and every other connection is handed on, still encrypted, to the server that
answers it. Renewal costs no downtime and no second port.

**HTTP-01** needs port 80, which is plain HTTP. The program opens it when a challenge is pending
and closes it once the order is settled; while open it answers
`GET /.well-known/acme-challenge/<token>` for the pending token and `404` to everything else,
with no redirect.

**DNS-01** is answered through a provider, for a host no inbound connection reaches. A provider
does two things, `present(name, value)` and `cleanup(name, value)`, and declares how long its
records take to propagate and how often to look. A `_acme-challenge` name delegated by CNAME is
followed to where it points. Before the authority is told to look, the program asks the zone's
authoritative servers itself and waits until each answers with the value. Providers are named,
and their settings spelled, as [lego](https://go-acme.github.io/lego/dns/) names them, so an
operator's existing configuration carries over:

| Provider | Settings |
|---|---|
| `rfc2136` | `RFC2136_NAMESERVER`, `RFC2136_TSIG_KEY`, `RFC2136_TSIG_ALGORITHM`, `RFC2136_TSIG_SECRET_FILE` |
| `cloudflare` | `CLOUDFLARE_DNS_API_TOKEN_FILE` |
| `route53` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY_FILE`, `AWS_REGION`, `AWS_HOSTED_ZONE_ID` |
| `gcloud` | `GCE_PROJECT`, `GCE_SERVICE_ACCOUNT_FILE` |
| `azuredns` | `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET_FILE`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP` |
| `digitalocean` | `DO_AUTH_TOKEN_FILE` |
| `hetzner` | `HETZNER_API_TOKEN_FILE` |
| `desec` | `DESEC_TOKEN_FILE` |
| `duckdns` | `DUCKDNS_TOKEN_FILE` |
| `exec` | `EXEC_PATH`: the operator's program, called as `<program> present <name> <value>` and `<program> cleanup <name> <value>` |

`rfc2136` and `exec` reach a DNS server the operator runs. A secret is read from the file its
`_FILE` setting names, never from the setting itself, so it never sits in an environment a
process listing or a crash report can show.

**Renewal.** A certificate is renewed when the authority's ACME Renewal Information
([RFC 9773](https://www.rfc-editor.org/rfc/rfc9773)) says to, where it offers it, and otherwise
once a third of its lifetime is left, which holds for a certificate of six days as for one of
ninety. A failed attempt is tried again after a minute, doubling to six hours, with jitter, and
never sooner than a `Retry-After` or a rate-limit problem from the authority says.

### `private-ca`

The program makes a root of its own the first time it starts in this mode, and issues the
certificate it serves from that root.

| | |
|---|---|
| The root | ECDSA P-384, self-signed, valid for ten years, `CA:TRUE` with a path length of 0, so it signs certificates and no other authority |
| Its name constraints | Critical, permitting exactly the names in `LEMONFIBER_NAMES` and, for each address, that address alone; a root that leaks can vouch for nothing else |
| Its key | Kept in the state directory, used for nothing but signing this program's certificate, never served and never logged |
| The certificate served | ECDSA P-256 by default, valid for 30 days, renewed by the program once ten days are left |
| Handing the root over | Written to `ca/root.pem` in the state directory, its SHA-256 fingerprint printed at every start, and served as a file at `GET /root.pem` over the same TLS, so a person can fetch it and check the fingerprint before installing it |

The operator installs the root once on each device that is to connect. From then on every
client that trusts it checks the chain as it checks any other, and renewal is the program's.

**A root is replaced** when the operator asks (`ca replace`), when `LEMONFIBER_NAMES` gains a
name the root's constraints do not cover, and when a year of the root's life is left. Replacement
makes a new root beside the old one, writes it to `ca/next-root.pem` and prints its fingerprint
and, at every start until the switch, that it is waiting to be installed. The program keeps
serving from the old root until the operator switches (`ca switch`), or, where the old root
would expire first, until 30 days before it does. A name the old root does not cover is not
served until the switch; the program says so rather than serving a certificate that would be
refused. After the switch the old root's key is deleted.

### `pinned`

The program makes a certificate of its own, self-signed, for the names in `LEMONFIBER_NAMES`,
ECDSA P-256 by default, valid for ten years, and prints its fingerprint at every start in the
form the companion's pairing material carries: SHA-256 over the DER encoding, lower-case hex
(ADR-0025). A client given the fingerprint pins it and checks it in the handshake. The
certificate is not renewed, since a new one would break every pin; it is replaced only when the
operator asks (`pinned replace`), or when `LEMONFIBER_NAMES` changes, and the program says at
start, with the new fingerprint, that every client must be given it again.

## Keys

| Setting | Default | Holds |
|---|---|---|
| `LEMONFIBER_TLS_KEY_TYPE` | `ec-p256` | `ec-p256`, `ec-p384`, `rsa-2048` or `rsa-3072`, for the certificate served |
| `LEMONFIBER_STATE` | the program's own | The directory the account, the keys and the certificates are kept in |

Every key is generated by the program itself. No two roles share a key: an ACME account key, a
private root's key and a certificate's key are three keys.

A renewed or replaced certificate is taken by new handshakes as soon as it lands; no connection
is dropped for it.

## When it fails

| | |
|---|---|
| Each failed renewal | Logged as an error, with the authority's problem type and detail where there is one and the time left on the certificate in use |
| Inside seven days of expiry, while renewal is failing | Logged as critical once an hour |
| The health answer | `GET /health`, over TLS, without a credential and carrying no other data: the mode, the certificate's expiry, when renewal was last tried and how it went; `503` while renewal is failing inside seven days, `200` otherwise |

A program that holds a stack credential, as the core does, also raises its own alert. One that
holds none, as the MCP server does not, has the log and the health answer.

## The state

```
$LEMONFIBER_STATE/
  account/<sha256 of the directory URL>/key.pem      acme: the account key, one per authority
  account/<sha256 of the directory URL>/account.json acme: its URL and contact
  ca/root.pem, ca/root-key.pem                       private-ca: the root and its key
  ca/next-root.pem, ca/next-root-key.pem             private-ca: a replacement waiting for the switch
  certificates/<first name>/key.pem                  the served certificate's key
  certificates/<first name>/chain.pem                its chain, leaf first
  certificates/<first name>/renewal.json             the mode, when it was issued, when renewal is due, the last attempt and its outcome
```

The directory is `0700` and every file in it `0600`, owned by the user the program runs as; a
program refuses to start on a state directory others can read or that another user owns. A file
is written beside its final name, flushed and renamed into place, so a crash leaves the old file
or the new one and never half of either.

No private key, account key, root key, External Account Binding key or DNS credential is written
to a log, an error, the health answer or a value's printed form, and none is passed to another
process except the one `exec` provider, which is given only the name and the record's value.

## Conformance

Each implementation runs, in its own CI, the same scenarios. Against
[Pebble](https://github.com/letsencrypt/pebble), the authority Let's Encrypt publishes for
testing, with its challenge test server answering DNS: first issuance by each challenge, renewal
by Renewal Information and by lifetime, an authority requiring a binding with and without one, a
rate-limit answer, and an order that fails. Against itself: a private root's constraints refusing
a name outside them, its replacement and switch, a pinned certificate's fingerprint matching what
a client computes, a renewal swapped without dropping a connection, and a key or a state
directory with the wrong permissions. A DNS provider that talks to a remote API is tested against
a stand-in of that API.

## Requirements

| ID | Requirement |
|----|-------------|
| **ARCH-R185** | A program lemonfiber builds that serves clients on other machines MUST offer the four modes `files`, `acme`, `private-ca` and `pinned`, chosen by `LEMONFIBER_TLS_MODE`, `files` where both of its paths are set and `pinned` where nothing is chosen, `acme` and `private-ca` only where `LEMONFIBER_TLS_MODE` names them, MUST refuse to start without `LEMONFIBER_NAMES` in every mode but `files`, and MUST NOT answer in plain HTTP anything but the token of a pending HTTP-01 challenge, in any mode. |
| **ARCH-R186** | At start the program MUST log which mode it serves and who can check its certificate, and in `private-ca` and `pinned` MUST say that an assistant reached through its provider's servers cannot connect; its documentation MUST say the same of each mode. |
| **ARCH-R187** | In `files`, the operator's certificate and key MUST be refused at start, by name, where either is unreadable, the key does not match, the certificate has expired, or it does not cover every name in `LEMONFIBER_NAMES` where that is set, and MUST be read again without a restart when either changes. |
| **ARCH-R188** | In `acme`, the program MUST speak to the RFC 8555 directory `LEMONFIBER_ACME_DIRECTORY` names, Let's Encrypt's by default, checking the directory's TLS against `LEMONFIBER_ACME_ROOTS` where given, with External Account Binding where `LEMONFIBER_ACME_EAB_KID` and `LEMONFIBER_ACME_EAB_HMAC_FILE` are given; where the directory requires an external account and none is given it MUST refuse to start, naming both. Choosing `acme` MUST be taken as accepting the directory's terms, whose address MUST be logged when an account is first registered and stated in the documentation. |
| **ARCH-R189** | In `acme`, the challenge MUST be the one `LEMONFIBER_ACME_CHALLENGE` names, `tls-alpn-01` by default, `http-01` or `dns-01`. TLS-ALPN-01 MUST be answered on the serving port while it serves, answering only a connection whose ClientHello asks for `acme-tls/1` alone and handing every other on still encrypted. For HTTP-01, port 80 MUST be open only while a challenge is pending, MUST answer only the pending token's path, MUST answer everything else `404` with no redirect, and MUST close once the order is settled. |
| **ARCH-R190** | DNS-01 MUST be answered through the provider `LEMONFIBER_ACME_DNS_PROVIDER` names, from `rfc2136`, `cloudflare`, `route53`, `gcloud`, `azuredns`, `digitalocean`, `hetzner`, `desec`, `duckdns` and `exec`, with the settings this page lists; a CNAME-delegated `_acme-challenge` name MUST be followed, and the authority MUST NOT be told to validate before every authoritative server of the zone answers with the value. |
| **ARCH-R191** | In `acme`, a certificate MUST be renewed when the authority's Renewal Information says, where it offers it, and otherwise once a third of its lifetime is left; a failed attempt MUST be retried from one minute doubling to six hours with jitter, never sooner than a `Retry-After` or rate-limit problem allows. |
| **ARCH-R192** | In `private-ca`, the program MUST make an ECDSA P-384 root valid for ten years with a path length of 0 and critical name constraints permitting exactly the names and addresses in `LEMONFIBER_NAMES`; MUST issue the served certificate from it, valid for 30 days and renewed once ten days are left; MUST write the root to the state directory, print its fingerprint at start and serve it at `GET /root.pem` over TLS; and MUST NOT serve or log the root's key. |
| **ARCH-R193** | A private root MUST be replaced on the operator's command, when `LEMONFIBER_NAMES` gains a name it does not cover, and when a year of its life is left: the new root MUST be made beside the old and announced with its fingerprint at every start until the switch; the program MUST serve from the old root until the operator switches or, where the old root expires first, until 30 days before it does; and the old root's key MUST be deleted after the switch. |
| **ARCH-R194** | In `pinned`, the program MUST make its own certificate for `LEMONFIBER_NAMES`, valid for ten years, MUST print its fingerprint at every start as SHA-256 over its DER encoding in lower-case hex, MUST NOT renew it, and MUST replace it only on the operator's command or when `LEMONFIBER_NAMES` changes, saying at start that every client must be given the new fingerprint. |
| **ARCH-R195** | Every key MUST be generated by the program, the served certificate's `ec-p256` by default and `ec-p384`, `rsa-2048` or `rsa-3072` where `LEMONFIBER_TLS_KEY_TYPE` names it; no two of an account key, a root's key and a certificate's key MUST be one key; and a renewed or replaced certificate MUST be served to new handshakes without dropping a connection. |
| **ARCH-R196** | Every failed renewal MUST be logged as an error with what failed and the time left; inside seven days of expiry while renewal fails it MUST be logged as critical hourly; and `GET /health`, over TLS and without a credential, MUST answer the mode, the expiry and the last attempt and its outcome, `503` while renewal fails inside seven days and `200` otherwise, carrying no other data. |
| **ARCH-R197** | The state MUST be kept in `LEMONFIBER_STATE` in the layout this page gives, the directory `0700` and every file `0600`, owned by the program's user and written by rename, and the program MUST refuse to start on a state directory another user owns or others can read. No private key, account key, root key, External Account Binding key or DNS credential MUST be written to a log, an error, the health answer or a printed value; a secret setting MUST be read from the file its `_FILE` setting names; and none MUST be passed to another process but the record name and value given to `exec`. The settings MUST be spelled and mean as this page lists them in every program implementing it. |
| **ARCH-R198** | Each implementation's CI MUST run the conformance scenarios this page lists, against Pebble and against itself, and each DNS provider talking to a remote API MUST be tested against a stand-in of it. |

## Related

- [F13 An assistant's way in](../../10-functional/features/f-extensibility/f13-mcp.md) — the first program it binds
- [ADR-0025](../../00-overview/decisions/0025-nothing-leaves-this-machine-unpinned.md) — the fingerprint's form, which `pinned` prints
- [web-api](web-api.md) — the surface the core serves
