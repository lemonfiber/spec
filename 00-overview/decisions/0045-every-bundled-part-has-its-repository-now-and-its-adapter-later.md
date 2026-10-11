# ADR-0045: Every bundled part has its repository now, and its adapter later

**Status:** Accepted
**Date:** 2026-10-11
**Decided:** 2026-10-11, by the maintainer, Wessel Verheij:

- a part without an adapter is assembled into the stack lemonfiber ships, and moves to
  the plugin path in place when its adapter ships;
- the source switch, the core reading the stack's services from the bundle, lands before
  the settings and secret stores and before the compose cutover, and the media stack is
  frozen at it;
- `lemonfiber-decline` and `lemonfiber-request-gate` each carry a `plugin.toml` in their
  existing repositories;
- the proxy listens on 8080 and 8443, publishes 80 to 8080 and 443 to 8443, and its
  Caddyfile names both ports;
- a plugin that builds no image is pinned by revision and tree digest, with no train tag,
  and only a repository that builds an image rides the train;
- the bundle declares the profiles, the forms, the links by name and the stack's choices
  of filler;
- `critical` is allowed with `shape = "egress-guard"`, for any author;
- any plugin may ship starting files under `config/<service id>/`, materialised, bounded,
  with no symbolic link;
- a plugin's id is the id of the service that takes the part's place, and a first-party
  service that replaces a reserved id keeps the stack's credential names, taken as
  recommended.

**Supersedes in part** [ADR-0042](0042-the-bundle-is-first-party-plugins-pinned-and-embedded.md):
§1 and §2 (what the bundle carries), §5 (when an in-process adapter goes), §6 (when the
media stack is archived) and §7 (which plugins ride the train).
**Amends**:

- [ADR-0002](0002-profiles-and-forms.md): profiles and forms are declared in the bundle;
- [ADR-0005](0005-embedded-stack-assets.md): what is embedded is the bundle and each
  pinned plugin's tree;
- [ADR-0033](0033-each-image-lemonfiber-builds-for-the-stack-has-its-own-repository.md):
  a built image's entry and pin live in its plugin manifest, and a built image may be an
  upstream's, rebuilt;
- [ADR-0041](0041-every-part-is-a-plugin-and-the-core-speaks-contracts.md): a part's
  repository exists before its adapter does;
- [ADR-0043](0043-the-core-writes-every-compose-entry-from-one-typed-service-model.md):
  the stack's own services are the parts the bundle assembles.

## Context

[ADR-0042](0042-the-bundle-is-first-party-plugins-pinned-and-embedded.md) makes the
bundle a manifest in `lemonfiber-plugins` naming each first-party plugin by release and
manifest digest, and keeps each part's in-process adapter in the core until its plugin
is in the bundle. Measured against the repositories on 2026-10-11, that cannot move the
media stack's services out:

- **A part cannot enter the bundle before its adapter.** Of twenty-three services, one
  has an adapter. The catalogue refuses a copy that declares no adapter service, because
  `release` is read from the adapter's tag, so the other twenty-two have no pin to write.
- **The bundle carries one file per plugin.** The binary carries more than manifests from
  the media stack: starting configuration under `config/**` (the download client's
  `sabnzbd.ini`, the quality sync's `recyclarr.yml` and its includes, the dashboard's
  files, both Caddyfiles) and every recording a claim names.
- **The stack's own declarations have no home in a plugin.** The profiles, the forms,
  each service's profile, the stack's choices of filler, the links by name, `critical`
  for the egress guard and `last_release` are stack fields a plugin manifest refuses.
- **The proxy cannot run under `standard`.** It binds 80 and 443, and `standard` holds
  six kernel capabilities, none of them `NET_BIND_SERVICE`. Caddy's image also carries
  that capability on its binary, so the binary does not start under `standard` at any
  port; the guarded door runs the same image.
- **The train would tag twenty-two repositories that build nothing.** ADR-0042 §7 puts a
  first-party plugin's pin on the train's tag, and a tag of a plugin whose image is the
  upstream's adds nothing to a commit pin.

The maintainer's requirement is that every part has its repository now, so the media
stack stops being a second description of each part, without waiting for twenty-two
adapters.

## Decision

1. **Every bundled part has a repository of its own now.** Its manifest, its starting
   files, its recordings and its conformance live there. A part's plugin id is the id of
   the service that takes its place, so the container name, the configuration directory,
   the settings and secret namespaces, the materialised files and the journal's history
   keep their names. The guarded door and the proxy are `plugin-door` and `plugin-caddy`;
   decline and the request gate declare themselves in a `plugin.toml` in
   `lemonfiber-decline` and `lemonfiber-request-gate`.
2. **A part without an adapter is assembled, not installed.** The bundle pins it with
   `stage = "assembled"`: lemonfiber assembles its one service into the stack it ships,
   from the bundle and its copies, as a stack service, under the stack's settings and
   credential names, with its in-process adapter still in the core and named by `api`.
   Its claims fill its capabilities, proved against its recordings as every bundled
   claim is (`F9-R2`).
3. **A part moves to the plugin path when its adapter ships.** The release whose bundle
   pins the part with `stage = "installed"` moves it in place, by ADR-0042 §4's
   substitution with `replaces`, and deletes its in-process adapter. A first-party
   service that replaces a reserved id keeps the stack's setting, secret and credential
   names for it, so the move migrates no credential.
4. **The bundle declares what is about the whole stack.** `bundle.toml` at `schema = 2`
   holds the profiles, the forms, the services the catalogue no longer carries, the
   links by name and the stack's choices of filler, and each `[[plugin]]` names the
   profile its services sit in and the upstream's last release. A plugin declares its
   asks in its own `[[ask]]`, and no manifest names a profile, a form or a link by name.
5. **A pin is a revision and a tree.** Each `[[plugin]]` carries the digest of the
   plugin's manifest and of its tree: the manifest, its starting files, its fixtures and
   its conformance. The catalogue holds that tree at the paths the media stack held
   them, and the core trusts a plugin as first-party only at the id and both digests the
   bundle names. `release` is named only where it was tagged.
6. **Only a plugin that builds an image rides the train.** A plugin builds an image when
   one of its services runs an image under `ghcr.io/lemonfiber/`. The train tags such a
   repository before the core's release and the release tag embeds it at that tag. A
   plugin whose image is the upstream's is pinned by revision and tree alone, never
   tagged, and its pin moves by a reviewed pull request on the catalogue.
7. **Starting files are any plugin's.** A plugin may ship files under
   `config/<service id>/`, which lemonfiber writes into that service's configuration
   directory as materialised files (`F1-R4`): at most 64 files and 1 MiB per service, no
   symbolic link and no path outside the directory.
8. **`critical` belongs to the egress guard's shape.** A service may declare `critical`
   only with `shape = "egress-guard"`, whoever wrote it, because the one failure with
   consequences outside the machine is the guard's. A plugin of one service that
   provides `network.egress-guard` with no adapter takes the shape only where the bundle
   assembles it.
9. **`api` is honoured only where the bundle assembles a part.** An install or update of
   a plugin naming an in-process adapter is refused. `F14-R3` holds every manifest to no
   `api` by the time 0.18.0 is released.
10. **The proxy listens above 1024.** It listens on 8080 and 8443 and publishes 80 and
    443 to them, and its Caddyfile names both (`http_port`, `https_port`). The guarded
    door's 8096 and 8920 need nothing. The door's and the proxy's images are built by
    their repositories from Caddy's with the file capability removed, under Caddy's
    licence, and are proved under `standard` by their own CI.
11. **The source switch comes first.** The core reads the stack's services from the
    bundle before the settings and secret stores and before the compose cutover, and the
    media stack's services, configuration and recordings are frozen at the switch. Tests
    hold the two declarations equal at the switch: the assembled manifest, the carried
    configuration and recordings, and the generated project.
12. **The media stack is archived after the compose cutover.** Its Compose files are
    read until the cutover deletes every static reader, and cannot live in a plugin. Once
    nothing reads it, the maintainer archives it.
13. **0.18.0 keeps its scope.** The bundle's and the manifest's new requirements join its
    goals under `goals-change` review, and 0.18.0, or any pre-release of it, is cut only
    when every goal is met.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Install every part through the plugin path now** | The path that installs a form's first-party plugins from the embedded manifests is not built, and nothing reads the pinned set yet. Twenty-two parts would wait on it, and each would have to be a substitution of itself. |
| **A repository only once a part's adapter exists** | The media stack would stay the description of twenty-two parts beside their future repositories, and its services, configuration and recordings would be maintained twice until the last adapter. |
| **The plugin manifest declares its profile and forms** | A field only first-party manifests could use is trust deciding what a manifest may say (ADR-0043 §2), and a substitute could not stand in a part's profile without naming it. |
| **`critical` for first-party plugins only** | Trust deciding what a manifest may say, again; and a substitute egress guard could not be as critical as the guard it replaces. |
| **No `critical` in a plugin at all** | The egress guard would lose the one classification that reports its failure as leaving the machine. |
| **Starting files for first-party plugins only** | A substitute that needs a starting file could not stand in for a part that has one. |
| **Starting files held by the core or the media stack** | A second home for what describes a part, which drifts from its manifest, and the media stack retires. |
| **Every first-party plugin a train stream** | About twenty more tags and version pull requests per release, for repositories whose image is the upstream's and whose commit pin is already content-addressed. |
| **`plugin-decline` and `plugin-request-gate`** | Two more repositories and their CI for two images that already have repositories, release lanes and recordings. |
| **The source switch after the compose cutover** | The media stack and twenty-three repositories would both be maintained until the cutover lands. |
| **Credentials renamed into the plugin's namespace at the move** | A migration of every stored credential and its consumers for a rename that carries no meaning. |
| **A plugin id apart from its service id** | The container, the configuration directory, the settings, the secrets, the materialised files and the journal would each be renamed or mapped. |
| **`NET_BIND_SERVICE` in `standard`, or a shape for low ports** | It widens every service's entry, or adds a privilege a reviewer has to judge, for a port number a published mapping already gives. |

## Consequences

- **The bundle contract is its own page.** [bundle.md](../../20-architecture/contracts/bundle.md)
  carries `bundle.toml` at schema 2. The stack manifest is the form the core assembles
  the bundle into and the format of a `--stack-dir` stack.
- **The plugin manifest gains** `reaches` and `asks_for`, starting files, `critical`
  with the egress guard's shape, an assembled part's `api`, and `replaces` naming an id
  the bundle reserves.
- **The catalogue reads adapterless copies.** Its CI holds each copy's tree to its
  origin and each built image to its release.
- **The register of reserved ids, ports and hostnames reads the whole bundle,** both
  stages and the proxy's configuration copy, so a part moving to the plugin path keeps
  its port reserved.
- **Each part's image is run under its posture by its own repository's CI**
  (`ARCH-R250`), not the media stack's.

## Revisit if

- A part's adapter cannot move it in place without losing data or a credential.
- Assembled parts outlive 0.18.0's release.
