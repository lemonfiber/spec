# ADR-0043: The core writes every Compose entry from one typed service model

**Status:** Accepted
**Date:** 2026-10-11
**Decided:** 2026-10-11, by the maintainer, Wessel Verheij:

- one typed service model, the same closed vocabulary for first-party and third-party
  plugins; trust decides who may install, never what a manifest can say;
- an environment value is a constant, an operator setting with a default, the URL of a
  capability's filler, or a declared secret; a mount stays inside the service's own
  directory or the single data root, and so does every piece of its state; a device or a
  privilege comes only from a named shape; there is no field for the engine's socket;
- the core derives every network from the asks between capabilities, with no shared
  default network, and assigns every fixed address; no manifest names a network or an
  address;
- an ask reaches the adapter, and reaches the upstream it fronts only where the asker
  names the upstream's own API;
- one operator storage setting, a bind or an NFS export, applied to the single data mount
  of every service that takes data; the NAS overlay retires;
- a peer's URL is named by the capability it fills, never by a service id;
- settings live in the core's settings store and secrets in the secret store, and the
  stack's environment file is read once, at the move; settings are read and changed over
  the web API by the operator alone, and a secret is never read back;
- the forwarded port crosses through the core, from the egress guard's contract to the
  torrent client's;
- `standard` keeps the hardening every plugin's service has today, for every service,
  the stack's own included; `confined` adds to it; every image is run under its posture
  in CI before it ships;
- `network.via` may cross a profile, and is the one exception to `B1-R14`;
- `render` is a shape for a service that serves media, or for the upstream a media
  adapter fronts, approved apart as the egress guard's is;
- the old `grants` spellings are read and refused, naming the shape that replaces each;
- the model ships in 0.18.0;
- an operator's own overlay, merged last and shown as unvetted, is the escape hatch.

**Amended** by [ADR-0045](0045-every-bundled-part-has-its-repository-now-and-its-adapter-later.md): the stack's own services are the parts the bundle assembles from their first-party plugins, and each part's image is run under its posture by its own repository's CI rather than the media stack's.

**Amends**:

- [ADR-0005](0005-embedded-stack-assets.md): what is materialised is the manifests, and the
  Compose project is generated from them;
- [ADR-0021](0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md): the vocabulary
  widens and stays closed and typed, the entry extends no template, and the escape hatch
  of §6 is an operator's overlay rather than a fork;
- [ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md): the egress
  guard's is one of a closed set of named shapes;
- [ADR-0042](0042-the-bundle-is-first-party-plugins-pinned-and-embedded.md): the stack's
  own services and the bundle's plugins are written by one generator, and the media
  stack's Compose files retire before the repository does.

## Context

ADR-0021 fixed a plugin's Compose entry to one shape: an image, a profile, a published
port under a tier, the data mount and one configuration directory. ADR-0041 made every
bundled part a first-party plugin, and ADR-0042 installs the stack through the plugin
path. A part can only move if its plugin's entry can say what the part's entry says
today, and measured against the media stack on 2026-10-11, it cannot:

- **Ports.** A host port that is not the container's (8085 to 8080, 8095 to 8096, 13378
  to 80, 5056 to 8080), and a second published port (the guarded door's 8920, the
  proxy's 443).
- **Mounts.** A second directory beside the configuration directory (the media server's
  cache, the audiobook server's metadata), a configuration directory mounted read-only,
  scratch space in memory, two engine volumes holding the proxy's certificates, and a
  script from the stack mounted into the egress guard.
- **Environment.** Constants, values the operator sets, the address of a peer, and other
  services' credentials, all read from the stack's environment file.
- **Who a container runs as.** Three templates (`defaults`, `rootless`, `confined`), and
  a memory ceiling on lemonfiber's own images.
- **Devices.** The tunnel device, and the render device and group hardware transcoding
  needs.
- **Another container's network.** The torrent client runs inside the egress guard's
  network namespace, starts once the guard is healthy, and has its port published by the
  guard.
- **Networks.** Seven named networks, four of them internal, one translating no address
  off the host, fixed addresses for the door and the proxy, and a shared default network
  over which two links the wiring never states are made.

The stack's own services are written by hand in `compose/*.yml`, beside a manifest that
describes the same services, and the core reads that YAML to build, to check the mount
rule, to find networks, ports and names, and to find the door's address. Two descriptions
of each part drift, and an in-place move would compare a hand-written entry against a
generated one. The NAS overlay replaces the data mount by a list of services kept by
hand, and that list already misses one.

## Decision

1. **One model, and the core writes the whole project.**
   - Every Compose entry is generated from the one `[[service]]` model: the stack's own
     services while it has any, and every plugin's.
   - The core reads no Compose file, fragment, template or overlay from the stack or from
     a plugin. `compose.yml`, `compose/*.yml`, `compose/_common.yml` and
     `stacks/compose.storage.nas.yml` retire.
2. **One vocabulary for everyone.**
   - A first-party plugin, a third-party plugin and the stack declare a service in the
     same closed set of fields, with the same types and the same validation.
   - Trust decides whether a manifest may be installed and which credentials reach its
     services. It never decides what a manifest may say or how its entry is written.
3. **Every field is typed, and the set is closed.**
   - An environment value is a constant, an operator setting with a default, the URL of a
     capability's filler, or a secret the manifest declares. A constant or a setting is
     written so that Compose substitutes nothing in it. A secret is written to a file of
     the service's own, readable by its owner alone, never into the project, and every
     rehearsal and diagnostic shows its name and never its value.
   - A mount's source is inside the service's own mount tree, a directory apart from its
     configuration directory that no container sees except through its own mounts, and
     no source lies inside another; or it is the single data mount. A service's state
     lives under its configuration directory and its mount tree. There are no volumes the
     engine keeps for a service; the move copies the proxy's two into its mount tree once.
     Scratch space in memory reaches nothing of the host.
   - A device, a group or an added kernel capability comes only from a named shape:
     `egress-guard`, and `render` for hardware transcoding, which only a service serving
     media, or the upstream a media adapter fronts, may declare, which the operator approves apart from the offer, and whose
     device is added only where the host has one.
   - Who a container runs as and how tightly it is held are declared, and so is its
     memory ceiling. `standard` is what lemonfiber writes for a plugin's service today, for
     every service, the stack's own included: no privilege gained after start, six kernel
     capabilities and what a shape adds, and a bounded process count. `confined` adds a
     read-only root, no capability at all and the operator's uid, and takes no shape.
     Every plugin's CI runs each image under the posture its manifest declares, and the
     media stack's CI runs the stack's own under `standard` before the version that writes
     them ships. Nothing is refused at run time on account of posture.
   - A service that runs inside another's network names the capability that service
     fills. Its filler starts first and is waited on until healthy, whatever its profile.
   - No field reaches the engine's socket, runs a container privileged, joins a host
     namespace, or names an entrypoint or a command. The old `grants`, under either
     spelling, is read and refused, naming the shape that replaces each grant.
4. **The core derives the networks.** Every network and every service's place on it
   follows from the settled asks between capabilities, and there is no shared default
   network, so every link is one the wiring states. An ask reaches the service that
   speaks the capability's contract; a consumer that talks to the upstream in its own API
   names that API with `native`. The core, an adapter and the upstream it fronts share a
   private network. Every fixed address is the core's to assign, and no manifest names a
   network, a subnet or an address. This extends
   [the networks a plugin's service joins](../../20-architecture/contracts/plugin-manifest.md#the-networks)
   to the whole stack.
5. **Storage is one operator setting.** The data root is a bind of a host path or an NFS
   export, and the generator writes the single data mount of every service that takes
   data from it. No plugin or bundle overlay changes a mount.
6. **A peer is named by capability.** `{ url_of = "<capability>" }` is an ask, settled as
   every ask is, narrowed where needed by the medium a curator files:
   `{ url_of = "library.curate", files = "tv", native = "servarr" }`. A service id is
   never a value ([F4-R12](../../10-functional/features/f-extensibility/f4-capabilities.md)).
7. **Settings and secrets have one home each.** Settings live in the core's settings
   store, read and changed from the command line, the web API and the companion's
   operator screens, by the operator alone. Secrets live in the secret store; a read
   lists them and never carries a value, and none is written over the web API. The in-place move reads the
   stack's environment file once, files each value under its plugin, journals it, and
   the file is not read for that part again.
8. **The forwarded port crosses through the core.** The egress guard's filler reports it
   over `network.egress-guard`, and the core sets it on the torrent client over
   `download.torrent`. Nothing is mounted into the guard.
9. **The model ships in 0.18.0.** 0.18.0's goals take the new requirements, and the ones
   that stated the single shape are superseded or amended in place, under the
   `goals-change` review a staged version's goals need.
10. **The escape hatch is an operator's overlay.** One Compose file the operator writes on
    their own machine, merged last, never accepted from a plugin, named as unvetted by
    the doctor and every rehearsal, and journalled.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **A wider vocabulary for first-party plugins** | Trust would decide what a manifest may say, so there would be two schemas, two generators and two sets of golden files. A third-party substitute could not stand in for a part whose entry it cannot express, which is the substitution ADR-0041 exists for. |
| **The stack keeps its own Compose format** | Two descriptions of every part for as long as the moves take (ADR-0042 §5), drifting. The core keeps reading YAML in every place it reads it today, and an in-place move compares an entry somebody wrote against one the core generated. |
| **Networks declared by the bundle or by a manifest** | A named network is reach a reviewer judges manifest by manifest. A substitute would have to name the networks of the part it replaces, which is naming that part. Derived from asks, reach follows from what the wiring already says. |
| **A shared default network, with some services held off it** | Two links the stack relies on, the indexer manager to the bot-protection solver and the book curator to the download clients, worked over it and were never written down. A default network is reach nobody asked for, and the rule for who is held off it had to be invented case by case. |
| **An ask reaches the upstream by default** | The core speaks contracts, and an upstream reached directly is a product's own API on the wiring. Opting in with `native` keeps that visible where it happens. |
| **Mount sources inside the configuration directory** | The container writes that directory, so it could replace a source with a link, and the engine follows the link whenever it mounts, including when it restarts the container after a boot with nothing of lemonfiber's running first. A check before each start cannot cover that. |
| **Volumes the engine keeps for a service** | State outside the service's directory is missed by a backup, by a move and by the question of what a service reaches. The proxy's two are copied once. |
| **A script mounted into the egress guard to push the port** | A host file inside the one container whose failure exposes the home address, holding the client's credentials. Through the core, guard and client stay substitutable. |
| **Credentials as constants or settings in the project** | The project is read, diffed and shown in rehearsals. A secret in a file of its own, readable by its owner alone, is in none of them. |
| **The stack's environment file stays a source of values** | Two places for one value, one of which no surface edits and nothing journals. |
| **The engine's defaults for `standard`** | A service of the stack would be held more loosely than a stranger's plugin is today, which is trust deciding how an entry is written. Six capabilities and a process bound are what every plugin already runs under. |
| **Posture enforced at run time, or every service confined** | Whether an image runs under a posture is answered where the image is built. Refusing at run time would turn a manifest's declaration into an outage on somebody's machine, and a read-only root breaks every image that writes outside its directory. |
| **`network.via` held to one profile** | The client and the guard are two plugins and so two profiles; holding the edge to one profile would make the killswitch impossible to install. |
| **`render` for any service** | A device on the host for whoever asks is the reach ADR-0021 refused. Hardware transcoding is a media server's need. |
| **The old `grants` accepted for ever, or dropped unread** | Accepting it is reach the model refuses. Dropping it unread would leave the author without the shape to write instead. |
| **0.18.0 keeps the single shape and the model waits for 0.19.0** | 0.18.0 would ship a plugin entry no bundled part can move into, and the requirements the model contradicts would stand beside it. |
| **No escape hatch at all** | The model is for every manifest; an operator's own machine is theirs. An overlay they write, shown as unvetted and journalled, keeps that without opening a route a manifest can take. |
| **A NAS overlay** | A hand-kept list of which services take data, already wrong, in a second file that changes the one mount ADR-0006 is about. |
| **Peers by service id** | A service id in a value is a by-name link, which a plugin may not introduce (F4-R12). A substitution would leave the value pointing at the part it replaced. |
| **Free-form environment, checked against a list of refused names** | A list of refused names is never closed, and a value can carry a reference into the stack's environment file whatever its name. ADR-0021's objection to an allow-list extended on the strength of untrusted input applies unchanged. |

## Consequences

- **The core gains one generator and loses every reader of static Compose.** The build,
  the single-mount check, the network and port readers, the door's address, the
  materialised-file checksums and the carried files read the model. The generator is
  golden-tested as command construction is (`Q-R23`).
- **Every service is held as a plugin's service is.** The stack's own services take
  `standard`, as every plugin's service already does, and lemonfiber's own images keep
  `confined`. Each image is proved under its posture before it ships: a plugin's by its
  own CI, and the stack's by the media stack's (`REPO-R93`).
- **The torrent client's link to the tunnel is an ask.** It names `network.egress-guard`,
  so a substitute egress guard takes the client inside its own network, and the stack's
  by-name wiring for that link goes.
- **The stack's wiring gains two asks.** The indexer manager asks `indexer.proxy`, and the
  book curator asks for the download clients.
- **0.18.0 changes scope.** `ARCH-R86`, `ARCH-R87`, `ARCH-R88` and `ARCH-R101` are
  superseded and leave its goals; `F14-R23`, `F14-R27` and `B1-R14` are amended in place;
  the model's requirements join it.

## Revisit if

- A part worth having cannot be expressed and the demand is broad: the model widens
  here, for everybody, as ADR-0021 says.
- A derived network reaches less than a part needs, or more than its asks say.
