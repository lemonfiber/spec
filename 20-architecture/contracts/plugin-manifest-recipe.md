# Contract: `plugin.toml` — `[[recipe]]`

**Status:** Accepted

Part of the [`plugin.toml` contract](plugin-manifest.md): the ordered calls a plugin may
declare, each bounded by what it reads. The requirements this page describes are listed
with the rest of the contract's, under [Requirements](plugin-manifest.md#requirements).

## `[[recipe]]` — ordered calls, bounded by reading

```toml
[[recipe]]
id    = "adopt-existing-library"
title = "Point it at the comics the stack already files"
why   = "…"
on    = "install"

[[recipe.input]]
name   = "admin-password"
origin = "operator"
ask    = "The password you gave Komga's admin account"
secret = true

[[recipe.input]]
name   = "sonarr-key"
origin = "credential-store"
of     = "sonarr"

[[recipe.step]]
id      = "sign-in"
call    = { method  = "POST", to = "komga", path = "/api/v1/login",
            body    = "{\"password\":\"{{admin-password}}\"}" }
expect  = { status = 200 }
capture = [{ name = "token", from = "token", origin = "stack-service" }]
retry   = { times = 5, every = "6s", until = { status = 200 } }

[[recipe.step]]
id      = "create"
when    = { step = "sign-in", status = 200 }
call    = { method  = "POST", to = "komga", path = "/api/v1/libraries",
            headers = { Authorization = "Bearer {{token}}" } }
expect  = { status = 200 }

[[recipe.step]]
id      = "series"
call    = { method  = "GET", to = "sonarr", path = "/api/v3/series",
            headers = { X-Api-Key = "{{sonarr-key}}" } }
expect  = { status = 200 }

[[recipe.pair]]
value = "admin-password"
to    = "komga"

[[recipe.pair]]
value = "sonarr-key"
to    = "sonarr"

[[recipe.pair]]
value = "token"
to    = "komga"
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | ✔ | One word of ASCII letters, digits, `-` and `_`, unique within the plugin. |
| `on` | string | | `install` or `demand`. Absent means `install`. |
| `input[].name` | string | ✔ | One word, unique among the recipe's inputs and captures. |
| `input[].origin` | string | ✔ | `credential-store` or `operator`. |
| `input[].of` | string | for `credential-store` | The service of the stack's whose credential lemonfiber already holds. Never one of this plugin's own: lemonfiber holds no key for those. |
| `input[].ask` | string | for `operator` | The sentence the operator is asked, in one line. |
| `input[].secret` | boolean | | For `operator`: `true` where the value may be a secret, so a terminal takes it without showing it. Absent means `false`. |
| `step[].call.method` | string | ✔ | `GET`, `POST`, `PUT`, `PATCH` or `DELETE`. |
| `step[].call.to` | string | ✔ | A service id in this stack, or a DNS name outside it. Never an address, a range or a bare host port (`F8-R8`). Never a substitution. |
| `step[].call.path` | string | ✔ | A plain absolute path: one leading `/`, then segments and an optional query. Written out, but for a query value, which may substitute an earlier capture or an input. |
| `step[].call.headers` | table | | Headers the call carries. A value may substitute an earlier capture or an input. |
| `step[].call.body` | string | | The body the call carries. It may substitute an earlier capture or an input. |
| `step[].capture[].name` | string | ✔ | One word, unique within the recipe. |
| `step[].capture[].from` | string | ✔ | Where in the answer it is read: an expectation key (below), or `header.<name>`. |
| `step[].capture[].origin` | string | ✔ | `stack-service` or `external-response`. |
| `step[].when` | table | | `{ step, status }` or `{ value, equals }`. The step is skipped where it does not hold. |
| `step[].retry` | table | | `{ times, every, until }`, `until` being `{ status }` or `{ value, equals }`. |
| `pair[].value` | string | ✔ | A captured value's or an input's name. |
| `pair[].to` | string | ✔ | A destination as `call.to` writes it. |
| `pair[].release` | string | | Why a capture from a service in this stack is carried to another destination, in one sentence the operator is shown at consent (`F8-R18`). Refused on a pair it frees nothing on (`F8-R16`). |

**A call needs somewhere to put what an earlier step captured**, and `headers`
and `body` are it. Without them a recipe can name a destination and capture a
value and has no way to carry one to the other — which is every first-run flow
this feature exists for, since creating an account and reading back a token is
worth nothing if the token cannot then be presented. A query value is the third
place, because some first-run flows are written that way: Plex is claimed with
`POST /:/claim?token=…`. After the path's `?`, a `{{name}}` may stand on the value
side of a `name=value`, and what it carries is percent-encoded when it is put
there. It may stand nowhere else in the path: `to`, the path's segments and the
query's names are written out, so no destination is worked out while running and
no call is assembled out of something that came back (`F8-R2`). A header's name is
written out too: it is a fixed identifier of the protocol, not a place for a value,
so a `{{name}}` in one is refused with a code of its own, `PLUGIN-33`, and the
manifest answers with that code whatever else is wrong with it, listing every fault.

They are also what makes the pair check bite. Every `{{name}}` in a call, a query
value's included, is a flow from that value to that call's destination, so the set of flows a recipe
could produce is computable by reading it — and a flow with no
`[[recipe.pair]]` behind it fails validation before a call is made
([ADR-0022](../../00-overview/decisions/0022-a-recipe-declares-pairs-not-lists.md)).
A guard can skip a step and never add one, so the set is every substitution in
every step whatever the guards say: a flow a guard usually skips is still a flow.

### Where a value comes from

Every value a recipe carries has one of four origins, and the manifest writes
it (`F8-R3`):

| Origin | Written on | Held to |
|--------|------------|---------|
| `stack-service` | a capture | the step's `to` is a service in this stack |
| `external-response` | a capture | the step's `to` is a name outside it |
| `credential-store` | an input | `of` names a service of the stack's whose credential lemonfiber holds, never one of this plugin's own |
| `operator` | an input | it is supplied when the recipe runs: asked for at a terminal, given as `--input <name>=<value>` at the command line, or in `inputs` over the web API |

**An operator input is asked for when it is not given.** At a terminal, the
command line asks for each input a recipe of that act needs and was not handed
with `--input`, in the sentence `ask` writes, and takes one marked `secret`
without showing what is typed. Without a terminal, and over the web API, a
missing input is refused as `PLUGIN-34`, naming each one missing, so a client can
ask for exactly those; an input no recipe of that act asks for is refused the same
way, naming it. What an operator supplies is never part of the offer, never
journalled, and never repeated back — not in a report, not in a refusal, and not
in the prompt's own echo.

An origin that disagrees with where the value comes from is refused, naming
both. Written rather than derived, so that what the rehearsal and the record say
about a value is what the manifest's author said, and a manifest that says
something false about it is refused rather than corrected.

**A credential goes back to its own service, and nowhere else** (`F8-R16`). A value
the credential store holds for a service may be carried to that service and to no
other destination: not another service of the stack's, not one of this plugin's
own, and not a host outside. A pair carrying one anywhere but its `of`, and a
`{{name}}` putting one into a call to anywhere but its `of`, are each refused when
the manifest is read, naming the input, the service it belongs to and the
destination. A plugin may present a credential lemonfiber holds, which is what a
first-run flow against a bundled service needs; it may not take one somewhere,
which is what lemonfiber holding it is for.

**What a service answers is held to that service** (`F8-R16`). Every value
captured from the answer of a service in this stack, one of this plugin's own
included, is held to that service because it came from there, whatever it holds
and whatever the call that read it carried. It may be carried back to that service
freely. Carrying it to any other destination needs a pair that releases it:

```toml
[[recipe.pair]]
value   = "library-id"
to      = "sonarr"
release = "Sonarr files new series into the library Komga just made, so it needs that library's id."
```

A pair or a `{{name}}` carrying such a capture anywhere else with no release
behind it is refused when the manifest is read, naming the value, the service it
was read from and the destination. A `release` frees a capture and nothing else.
On a pair carrying a credential-store value, an operator's input, an external
host's answer, or a capture back to its own service, it is refused, naming the
pair, because a release the operator weighs for nothing teaches them to stop
weighing releases.

A guard decides a call as surely as a substitution feeds one. A `when` or a
`retry.until` that reads a held value makes the step it guards a carrier of that
value. Reading the manifest refuses one on a step to anywhere the value may not go,
exactly as it refuses the value in the call. Otherwise which calls a recipe makes,
and where, would answer questions about a value that no call carries.

**And again at the call** (`F8-R17`). Reading the manifest is the first check, not
the only one. While a recipe runs, every value it holds carries the destinations it
may be sent to: a credential-store value its own service alone, a capture from a
service in this stack that service and each destination of a released pair the
operator approved in this act, and any other value the destinations its pairs name. Before a
call is sent, every value it carries is held to that call's `to`, and a value bound
for a host outside the stack is held to the approvals this act was given as well,
as `<value>@<destination>`. A call carrying a value anywhere else is not sent: the
step comes to `withheld`, the recipe ends there, and the act ends with `PLUGIN-38`,
naming the value, the destination and the step, never what the value holds. A
manifest the reading passed meets this refusal only where the reading missed
something, and what it missed is then a call that was not made rather than a value
somewhere it may not be.

### Where a call goes

A destination is one of two things and never a third (`F8-R4`):

- **A service in this stack**: a `to` naming one of the stack's services or one
  of this plugin's own. lemonfiber reaches it at `127.0.0.1` on the port it
  publishes there, and a call to a service that publishes none is refused when
  the manifest is read. Another plugin's services are not a destination.
- **A host outside it**: any other `to`, which is a DNS name of at least two
  labels. It is reached over https on port 443 and nothing else. A one-label name
  that names no such service is refused, because it is neither.

**Where a call goes is the destination, never the path.** A call's address is built
from the scheme, host and port its destination gives it, and the path is set on
that address rather than written after it. So the path is a plain absolute path:
it begins with exactly one `/`, and holds no `@`, `\`, `#`, whitespace or control
character, no percent-encoded `/`, `\`, `@`, `#` or `.`, and no `.` or `..`
segment — any of which could make the text after a host read as another host, or
walk somewhere the destination does not name. A manifest whose path is anything
else is refused with a code of its own, `PLUGIN-37`, whatever else is wrong with
it. A value substituted into a query value is percent-encoded, and a call whose
built address names any host or port other than its destination's is refused
before it is sent.

An external name is resolved **before every call**, once, and the call is
refused where any address it answers with is not out on the internet (`F8-R9`).
The call is then made to the addresses that were checked and no others, so a
name answering differently a moment later is not asked again.

An address is not out on the internet where it is classed, by what the address
is rather than by a list of hosts, as any of these:

| Family | Classes |
|--------|---------|
| IPv4 | loopback `127/8`, unspecified `0/8`, private `10/8` `172.16/12` `192.168/16`, link-local `169.254/16` (where cloud metadata answers), shared `100.64/10`, IETF protocol `192.0.0/24`, documentation `192.0.2/24` `198.51.100/24` `203.0.113/24`, benchmarking `198.18/15`, multicast `224/4`, reserved `240/4`, broadcast `255.255.255.255` |
| IPv6 | loopback, unspecified, unique-local `fc00::/7`, link-local `fe80::/10`, site-local `fec0::/10`, multicast `ff00::/8`, documentation `2001:db8::/32` `3fff::/20`, benchmarking `2001:2::/48` |
| IPv4 inside IPv6 | mapped `::ffff:0:0/96`, compatible `::/96`, NAT64 `64:ff9b::/96` `64:ff9b:1::/48`, 6to4 `2002::/16`, Teredo `2001::/32`: the IPv4 address each carries is classed as itself |

An address written as the host is read as the address it is however it is
written — dotted decimal, a single number, octal, hexadecimal or a short form
such as `127.1` — and classed before anything is asked, so no spelling reaches a
resolver that would read it as an address.
That refusal ends with a code of its own, `PLUGIN-35`, apart from a network that
failed (`ARCH-R149`). A call follows no redirect: a `3xx` is an answer, and a guard may
branch on it.

### Branching, and waiting

A step may carry `when`, and is skipped where it does not hold: `{ step, status }`
holds where that earlier step was made and answered that status, and
`{ value, equals }` where that earlier capture or input holds exactly that text.
A guard names only what came before it. There are no jumps, so a recipe runs
each step at most once, in the order written, and always ends.

A step may carry `retry`, and is made again until `until` holds or `times` is
spent. The bounds are published and are this contract's, not a manifest's:

| Bound | At most |
|-------|---------|
| `retry.times` | 10 |
| `retry.every` | 30 seconds |
| A recipe's retries, waited out in all | 5 minutes |
| One call, from asking to its last byte | 30 seconds |
| One answer's body | 1 MiB |

A step whose retries are spent fails the recipe, naming the call and what it
last answered. A value larger than the bounds allow is refused when the manifest
is read, naming the bound.

### What a capture reads

`capture.from` is an expectation key as `[[proof]]` writes one: a member name, or
a JSON Pointer with the selector this contract defines. A body that is not JSON
has nothing to read, and the capture fails the step. `header.<name>` reads that
header of the answer instead, the first where it arrived twice. A member whose
own name begins `header.` is reached by its pointer. Nothing else is read: a
status is branched on by `when`, never captured.

### When a recipe runs

A recipe runs **on install** or **on demand**, as `on` says.

An install recipe runs during an install and an update, in the order declared,
after the plugin's proofs and the stack's checks hold and before the record is
written. A removal runs none. Where one fails, the install goes back as an
install whose proofs failed goes back, and the act ends with a problem: `PLUGIN-35`
where a call was refused because its host stands for an address not out on the
internet, `PLUGIN-38` where a call was withheld because a value it carries may not go
where it was going (`F8-R17`), and `PLUGIN-36` where a step failed any other way — nothing answered, the
answer was not the one it expects, a capture found nothing, or the answer was larger
than a recipe reads. The problem's detail names the recipe, the step and each call
that had already landed somewhere and cannot be put back from here, and its `steps`
carry what every step came to as data (`G4-R17`). Neither repeats a value: an answer
that was not the one a step expects is said as which constraint did not hold where,
never as what the answer held there, and what a call carried or an operator gave is
named, never shown. A recipe that holds is reported on
the install, every step with what it came to.

A demand recipe runs only through `lemonfiber plugin run <plugin> <recipe>` and
the `plugin-run` action. Its reading lists the steps and pairs, its offer covers
them, and its approvals are given to that act and to no other: approving a pair
at install is not approving it for a demand recipe, and approving it for one run
is not approving it for the next (`ARCH-R147`). A demand recipe that fails
changes no install record, and ends with the same problem, saying what landed.

A pair carrying a value to a host outside the stack is approved as itself, as
`<value>@<destination>`, and so is a pair carrying a release. The consent names
a released pair as the value, the service it was read from, the destination and
the `release` sentence, and an act with any released pair not approved does not
proceed (`F8-R18`). Any other pair to a service in this stack is listed on the
reading and asks for no approval, because it carries nothing out of the machine
and nothing away from the service it came from.

A value a recipe captures is a declared `[[secret]]` and is kept, beside the
settings, in a file only its owner reads. It is taken away with the plugin. An
input is read when the recipe runs and is not kept.

### Running one is asked for by name

```toml
[requires]
capabilities = ["service.add", "service.health.http", "recipe.run"]
```

A lemonfiber that does not offer `recipe.run` refuses such a manifest **by naming
that capability** (`F3-R21`, `ARCH-R90`). Parsing the block and skipping it would
install a plugin whose declared behaviour is wider than its actual one, and that
is the tolerated unknown `ARCH-R91` exists to refuse.

[F8](../../10-functional/features/f-extensibility/f8-recipes.md) governs what the
calls may do; this says where they are written and what bounds them.

## Related

- [plugin-manifest](plugin-manifest.md) — the rest of the contract, its validation and its requirements
- [plugin-manifest-proof](plugin-manifest-proof.md) — what must hold before a plugin is installed
