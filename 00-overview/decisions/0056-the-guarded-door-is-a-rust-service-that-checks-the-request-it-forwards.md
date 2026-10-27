# ADR-0056: The guarded door is a Rust service that checks the request it forwards

**Status:** Accepted
**Date:** 2026-10-27
**Decided:** 2026-10-27, by the maintainer, Wessel Verheij:

- the filler of `stream.guard` the stack ships is a Rust service of its own, built in
  `lemonfiber-door`, that speaks `stream.guard@1` itself as its own upstream
  (`ARCH-R344`), and Caddy leaves the door;
- it reads each request's target as the bytes that arrived, checks them against the
  declaration the core applies in typed code, and forwards exactly those bytes;
- it answers `503` until the core applies a guard, believes `X-Forwarded-For` only from
  the one proxy the guard names, refuses with `403` a question's answer the declaration
  does not class, and refuses with `403` a request presenting a member's token more
  than once;
- `lemonfiber-door` stays the repository that builds the image `plugin-door` runs and
  pins (`OPS-R93`), and `plugin-door` holds the door's manifest with no adapter beside
  it.

**Amends**:

- [ADR-0045](0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md):
  the guarded door's image is no longer Caddy's rebuilt; `plugin-door` builds no image
  and is pinned by revision.

## Context

The door is the one place the household's requests for an item's bytes are held to who
may see the item ([ADR-0050](0050-a-contract-hands-its-filler-all-it-enforces-and-reads-back-no-secret.md)).
`stream.guard@1` hands its filler the media server's declaration, and the filler
enforces it: the paths it refuses, the byte and live paths, the parameters that name
another item, how a member's token reaches the media server, the question it asks, and
the normal form a request is held to before any of that is read (`ARCH-R207`,
`ARCH-R303`, `ARCH-R304`).

The door the stack ships is Caddy with a hand-written configuration that enforces
Jellyfin's declaration, and nothing speaks the contract in front of it. Enforcing any
declaration means generating that configuration from the declaration. Caddy matches a
route on the path it has decoded and forwards the bytes that arrived, and the media
server decodes them again its own way. A name holding an encoded `/`, such as an artist
`AC%2FDC`, is one segment on the wire and two once decoded, so a declared pattern read
against one form says something else against the other. The hand-written configuration
closes that gap with expressions written for Jellyfin's routes alone. A generated one
would have to rewrite every declared pattern into such an expression, and what it
enforces would live in generated text that no test reads byte by byte.

## Decision

1. **The door is a Rust service.** `lemonfiber-door` builds it: one crate on the core's
   adapter kit, serving the household's plain and encrypted ports and its contract port,
   and speaking `stream.guard@1` as its own upstream (`ARCH-R343`, `ARCH-R344`).
2. **It checks the request that arrived, and forwards that request.** The normal form,
   the token, the refused paths, the byte and live paths and the parameters are each
   checked in typed code against the request target as its bytes arrived and as it
   reads decoded once, and a declared pattern either form matches is held to. What is
   forwarded is the target that was checked, byte for byte.
3. **Every rule is tested.** Each check has unit tests to full line coverage, among them
   a corpus of the normal form's edges: an encoded delimiter in a name, a dot segment, a
   `;` parameter, an encoded backslash, an encoded unreserved character and any `%` on a
   byte path.
4. **It fails closed, trusts one proxy, and refuses an answer it was not told about.**
   Until the core has applied an envelope, the door answers `503` to every request on
   the household's ports. It believes `X-Forwarded-For` only from the envelope's
   `proxy`, takes the rightmost entry that proxy sent as the client, and tells the media
   server that client alone, as the whole of `X-Forwarded-For`. An answer to the
   question in one of the declared refusals is handed back with its own status, an
   answer in none of the declared classes is refused with `403`, and a media server
   that cannot be reached, or does not answer in time, is answered `502` or `504`. A
   request presents a member's token once: one carrying more than one `Authorization`
   header, or a bearer token of the declared shape beside a token in one of the
   declared query parameters, is refused with `403`, so the question and the request
   forwarded present the same one.
5. **The repositories keep their places.** `lemonfiber-door` builds the image and moves
   `plugin-door`'s pin to it (`OPS-R93`). `plugin-door` holds the manifest, which runs
   that image with no adapter service, and builds no image of its own.

## Consequences

- **What the door enforces is the declaration, for any media server.** Nothing in the
  door names Jellyfin's routes.
- **The raw and the decoded path cannot disagree unseen.** A pattern is read against
  both, and a byte path carries no `%` at all.
- **The door's HTTP edge is hyper's and rustls's, not Caddy's.** Its upgrades, its
  HTTP/2 and its TLS are held to the same tests.
- **`plugin-door` is no longer cut by the train**, since it builds no image; the bundle
  pins its revision, whose manifest pins the image `lemonfiber-door` published.

## Alternatives considered

| Alternative | Why not |
|---|---|
| **An adapter that generates Caddy's configuration from the declaration and loads it** | Caddy matches the decoded path and forwards the raw one, so every declared pattern would have to be rewritten into an expression over both, and what the door enforces would be generated text no test reads byte by byte. It also needs the adapter to write Caddy's files. |
| **Caddy's hand-written configuration, with the core asking no guard over the contract** | It enforces Jellyfin's declaration alone, and `ARCH-R207`, `ARCH-R303` and `ARCH-R304` hand the declaration to the guard. |

## Revisit when

- a media server's declaration needs a check the typed rules cannot state;
- hyper or rustls stops being maintained for the door's needs.
