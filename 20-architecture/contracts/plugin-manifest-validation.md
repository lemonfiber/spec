# Contract: `plugin.toml` — validation

**Status:** Accepted

Part of the [`plugin.toml` contract](plugin-manifest.md): the rules a manifest is held
to before anything in it is acted on, and what each refusal names. The requirements this
page describes are listed with the rest of the contract's, under
[Requirements](plugin-manifest.md#requirements).

## Validation

Every violation is reported in one pass, each naming its location (`F3-R22`,
`F1-R9`). This includes the faults a strict deserialiser would otherwise raise
one at a time — an unknown field, an unknown enum value, a wrong type — because
a third-party manifest is far likelier to carry several of them than a
first-party one, and fixing a manifest one error per run is a guessing game.

| Rule | Failure |
|------|---------|
| `schema_version` supported | Both versions named |
| Every required field present | Field and its table named |
| No field outside the permitted set | Field named, with the permitted set |
| No unrecognised enum value | Value named, with the values available |
| `plugin.id` not already installed | Both origins named (`F5-R12`) |
| `service.id` collides with no other service in this manifest, the stack, or an installed plugin | Both named |
| No port the service publishes (`port`, each `publish.port`, and a `via` service's on its filler) is one another service publishes | Port and both services named |
| `publish` only where `port` is | Service named |
| `wiring.hostname` is not a name the stack's own proxy is written to answer on | Name given |
| At most one service declares a given core capability | Capability and both services named |
| `digest` present and well-formed | Service named |
| `bind` present when `port` is | Service named |
| `criticality` is `critical` only where `shape` is `egress-guard` | Value named, with the shape it needs and the four available without it (`ARCH-R97`) |
| `reaches` and `asks_for` declared together or not at all, `asks_for` not blank where declared | Service and the declared half named (`F2-R10`, `ARCH-R270`) |
| Every starting file lies under `config/<id>/` of a declared service, no path in the tree is a symbolic link, and no service's files number more than 64 or weigh more than 1 MiB in all | Path or service named, with the bound (`ARCH-R271`) |
| `certificate` names two different relative paths beneath the configuration directory, with no `..`, no interpolation and no starting file at either, and one to eight host names, on a service that does not provide `stream.guard` | `service <id>.certificate` named, with what is permitted (`ARCH-R356`) |
| `replaces` names an id the bundle reserves, and the declaring service's own | `service <id>.replaces` named (`ARCH-R222`) |
| `license` present | Plugin named |
| Every `forms` entry names a declared form, checked at install against the stack it joins | Both named |
| Every `[[reach]]` names a host a recipe calls or carries a value to, once, with a `stops` line | Host named |
| Every entry in `requires.capabilities` is offered | Capability named, never a version |
| `config_path` is one absolute path, not `/`, and outside the data root | Path named, with what is permitted |
| Every `mount.from` is a relative path inside the service's own mount tree, `./mounts/<id>`, with no `..`, no interpolation and none inside another of its sources | Mount named, with what is permitted |
| Every `mount.to` and `tmpfs` entry is an absolute path, not `/`, outside `/data` where the service takes data, and no other mount's target | Mount named, with what is permitted |
| Every `env` name is a variable's name and none of `TZ`, `PUID` and `PGID` | Variable named |
| A `user_mode` table names two different variables' names, neither `TZ` nor one the service's `env` declares | Variable named |
| Every `env` value is a constant, `{ setting, default }`, `{ url_of }` (with `files` and `native` only) or `{ secret }`, and nothing else | Variable named, with the four kinds |
| `args`, where declared, holds one to sixteen entries, each a string of 1 to 256 characters holding no `$`, no `{{` and no control character | Service named, with the entry (`ARCH-R407`) |
| `container_hostname`, where declared, is one DNS label of lowercase letters, digits and hyphens, at most 63 of them, beginning with a letter and not ending with a hyphen, and none of `inf`, `infinity` and `nan` | Service named, with the name and what it breaks (`ARCH-R427`) |
| Every `{ secret }` names a `[[secret]]` the manifest declares | Variable and secret named |
| A `minted` secret's `of` names one of the plugin's own services, and no capture names it | Secret named |
| `minted` is `true`, `"password"` or `"email"` | Secret named, with the three |
| `lapses_s` is a positive whole number of seconds, declared only beside `recorded_with`, on a secret that is neither `minted` nor `carried_from`, whose `of` names a service an adapter speaking `owner.claim@1` fronts and whose id that adapter's `upstream` names | Secret named, with what is missing |
| Every `{{secret:<id>}}` in a starting file names a `[[secret]]` the manifest declares whose `of` is one of the plugin's own services, its form is absent, `pbkdf2` or `bcrypt` (`ARCH-R406`), and the file is UTF-8; no service's files hold more than 16 placeholders in all | File and placeholder, or service, named |
| `upstream` is declared only on a service that `speaks`, every field name is lowercase letters, digits and `_` starting with a letter, and every value is `{ secret }` naming a `[[secret]]` the manifest declares whose `of` is one of the plugin's own services | Service, field and secret named |
| `outside` is declared only on a service that `fronts` another, every key names a case of a contract that service speaks, written `<capability>@<major>/<case>`, and every host is a DNS name (`ARCH-R367`) | Service and entry named |
| Every `files` names a medium in `stack.toml`'s vocabulary, and only on `url_of` | Variable named, with the media |
| Every `[[ask]]`'s `media_types` lists at least one medium, each in `stack.toml`'s vocabulary and none twice | Ask named, with the media |
| Every `setting` is one the core publishes or in the plugin's own namespace | Setting named, with the namespace required |
| Every `one_of` lists at least one value and no value twice, at most one reference to a setting declares it, and a reference's `default` is one of its setting's values unless it declares `recorded_with` | Variable and setting named, with the values (`ARCH-R348`) |
| Every setting a `needs` names is one the same service reads and not the one the reference reads, and lists only values its choices hold where it declares them | Variable or secret named, with the setting (`ARCH-R348`) |
| Every `url_of` names a core capability its service does not ask `each` of, and is held to every rule an `[[ask]]` is | Variable and capability named |
| `user_mode` is `uid` where the service speaks a contract or is `confined` | Service named |
| A `confined` service declares no `shape` | Service named |
| `memory_mib` and `mem_limit_mib` above zero where declared | Service named |
| `network.via` names a capability in its closed set, one the service does not provide | Service and capability named, with the set |
| `network` declares `via` or `fenced`, never both | Service named |
| `shape` is declared only where that shape permits | `service <id>.shape` named |
| Every `provides` entry is a published core name or namespaced with the plugin's id | Capability named, with the namespace required |
| Every `[[proof]]` carries `id`, `title`, `expect`, `why` and exactly one of `request` and `run` | Proof and field named |
| At least one `[[proof]]` constrains the body or the output rather than only the status or the exit | Every status-only proof named |
| A `run` carries one to 64 `args`, each at most 4096 bytes with no NUL, and a `timeout_s`, where given, from 1 to 120; only a `[[proof]]` carries one | Proof and field named |
| A run's `expect` uses only `exit` and `stdout_starts_with`, and a request's uses neither | Assertion and key named |
| Every `expected` entry carries `fixture`, `verdict`, `constraint` and `reason`, its `verdict` is `fails`, and its `fixture` names a recording that exists | Assertion, entry and field named |
| Every `expected` entry names a constraint its assertion's `expect` makes, with a `place` exactly where that constraint is key-wise | Assertion, entry and constraint named, with the constraints the assertion makes |
| No two `expected` entries of one assertion name the same recording | Assertion and recording named |
| `wiring.hostname` is a single DNS label | Value named |
| A `loopback` service declares no `wiring.hostname` | Service named, and the tier that governs |
| Every `[[wiring]]`, `[[proof]]` and contributed check names a declared service, and names one where the plugin declares more than one | Name given, with the services declared |
| No service is wired twice | Service named |
| Every `[[ask]]` names a declared service, and names one where the plugin declares more than one | Name given, with the services declared |
| Every `ask.capability` is a core name the published vocabulary carries | Capability named: a namespaced one as naming a plugin, a removed one with its generation, an unknown one with the names carried |
| No service asks for the same capability twice | Service and capability named |
| No service asks for a capability it provides | Service and capability named; nothing asks itself |
| `request.accept` is one media type, not a list and not a wildcard | Value named, with what is permitted |
| Every expectation key names a place an answer could hold | Key named, with what is wrong with it |
| Every secret captured is one `[[secret]]` declared (`F3-R17`) | Value and its origin named |
| Every bundled thing changed is one `[[override]]` declared (`F3-R18`) | Setting and its owner named |
| A third-party plugin's `[[secret]]` whose `of` names a service outside it declares `for`, naming a capability one of its services provides, and no two name one capability (`ARCH-R322`) | Secret named, with the capability and the plugin's own |
| Every core name in `provides` has a `[[claim]]`, and every `[[claim]]` a name in `provides` | Both halves named |
| Every probe a claimed capability declares is bound, and no other | Probe named, with the ones it declares |
| Every binding's status and body constraint are within what its probe permits | Probe named, with what it requires |
| No claim whose capability a service an adapter of the plugin `fronts` provides binds a probe whose vocabulary entry says `credential = "operator"` (`ARCH-R302`) | Probe and adapter named |
| Every `[[contribution]].at` names a published extension point | Point named, with those that exist |
| Every contributed identity is namespaced, and none is one the point records as bundled | Both named |
| Every `doctor.check` carries a `doctor.remedy` naming it | Check named |
| A `[[recipe]]` is declared and `requires.capabilities` does not name `recipe.run` | Capability named, never a version |
| Every `{{name}}` in a call is an earlier capture or an input, and a pair carries it to that call's `to` (`F8-R5`) | Value and destination named |
| No `{{name}}` in a call's `to`, or in its `path` but for a query value (`F8-R2`) | Step and field named |
| No `{{name}}` in a header's name (`F8-R2`) | Step and header named, as `PLUGIN-33` |
| Every call's `path` is a plain absolute path (`F8-R2`) | Step named, with what is wrong with it, as `PLUGIN-37` |
| Every `origin` is one of the four, and agrees with where the value comes from (`F8-R3`) | Value named, with both origins |
| A credential-store value, and every capture from a call that carried or read one, is carried, by a pair or a `{{name}}`, or read by a guard, only to the service it belongs to, and any other capture from a service in this stack only to that service or by a pair releasing it (`F8-R16`) | Value, the service it is held to and the destination named |
| A pair's `release` is on a capture from a service in this stack, by a call that carried and read no credential-store value, carried to another destination, and nowhere else (`F8-R16`) | Pair named |
| Every credential-store input's `of` is a service of the stack's whose credential lemonfiber holds, never one of this plugin's own (`F8-R3`) | Input and service named |
| `input[].secret` is a boolean, and only on an `operator` input | Input named |
| Every `to` is a service in this stack with a published port, or a DNS name of two labels or more (`F8-R4`, `F8-R8`) | Destination named |
| Every `when` names an earlier step or an earlier value | Guard and name given |
| Every `retry` is within the published bounds | Bound named |
| Every `capture.from` is an expectation key or `header.<name>` | Key named, with what is wrong with it |

A manifest that fails any of these is refused outright — never partly applied,
never applied on the strength of the parts that did parse (`F3-R2`).
