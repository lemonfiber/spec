# ADR-0021: A plugin is data, and lemonfiber writes its container

**Status:** Proposed
**Date:** 2026-09-11

## Context

[F3](../../10-functional/features/f-extensibility/f3-stack-manifests.md) says a
plugin is declarative data and never executable code (`F3-R1`), that no opt-in,
sandbox or capability grant may make contributed code executable (`F3-R6`), and
that native plugins are not a supported mechanism (`F3-R7`). That is Accepted as
behaviour. It has never been recorded as a decision.

It should be. This section admits only decisions a reasonable engineer could
have made differently, and almost every adjacent tool that has offered
extensibility reached for code — a script directory, a module loader, a
container that speaks a plugin protocol. Choosing data instead is the most
contested call in the product, and the alternatives that lost are written down
nowhere. Somebody will reopen it, and they should start from the argument rather
than from the conclusion.

Two things about it also need settling, because F3 states them without deciding
them.

**The first is that "it ships no code" is not true, and the untrue part is the
large part.** F3's own list of what a manifest declares opens with *the service
— the container description of what runs, with its image pinned*. A container
image is code: arbitrary code, running as a daemon, with network access and a
mount of the operator's library. `F3-R10` wants a plugin to review as a readable
diff, and the manifest does — perhaps forty lines of it. The image does not, and
the image is where the behaviour lives. A claim that overstates this is worse
than a narrower one, because the first person to notice the gap will conclude
the rest of the reasoning was written to the same standard.

**The second is that the container has no contract at all.** Nothing in F3–F7
mentions mounts, network mode, devices, kernel capabilities, `privileged`, the
user a container runs as, or the Docker socket. The recipe language — the
smaller risk by a wide margin — carries four requirements and three paragraphs.
The bundled stack demonstrates what is at stake, because its own Compose uses
most of it: Gluetun holds `NET_ADMIN` and a `/dev/net/tun` device, qBittorrent
runs on `network_mode: "service:gluetun"` so it has no network of its own, and
Gluetun bind-mounts a script from the project directory. A plugin permitted to
supply Compose inherits all of that, and the thing the bundled stack pointedly
never does: a bind mount of `/var/run/docker.sock`, which is root on the host.

What makes this tractable is that a bundled service's Compose entry is
stereotyped. In full, from `compose/tv.yml`:

```yaml
sonarr:
  extends:
    file: compose/_common.yml
    service: rootless
  image: lscr.io/linuxserver/sonarr:4.0.15
  profiles: [tv]
  ports: ["127.0.0.1:8989:8989"]
  volumes:
    - ${DATA_ROOT:-./data}:/data
    - ./config/sonarr:/config
```

Every value that varies between services is already in the manifest: the image,
the tag, the profile, the port, and — as `bind` — whether the published address
is loopback or the LAN. Everything else comes from `_common.yml`'s `rootless`
template, which is four lines of restart policy, timezone and a `PUID`/`PGID`
pair. The Compose entry is not information a plugin has to supply. It is a
rendering of information the manifest already carries.

## Decision

**A plugin is declarative data, and lemonfiber writes the Compose entry rather
than accepting one.**

1. **Plugins are data.** `F3-R1`, `F3-R6` and `F3-R7` stand as written. No
   contributed code is loaded into lemonfiber's process, and no flag, grant,
   sandbox or manifest field changes that.

2. **The claim is stated precisely.** A plugin contributes no code to
   *lemonfiber's own process*. It contributes a container to the stack, and a
   script of calls to the recipe engine. Both execute. What review buys is not
   that nothing runs, but that **what runs, and what it may reach, is stated in
   advance and is checkable without running it.**

3. **A plugin declares its service in the manifest vocabulary that already
   exists** — the fields of a `[[service]]` entry in the
   [stack manifest](../../20-architecture/contracts/stack-manifest.md). It
   supplies no Compose YAML: no fragment, no overlay, no patch, no merge key.

4. **lemonfiber generates the Compose entry**, extending the same
   `compose/_common.yml` template every bundled service extends. The generated
   entry carries exactly: the `extends`, the image at its digest, the profile,
   the published port under the binding tier **the core assigns** from `bind`,
   the single `${DATA_ROOT}:/data` mount where the service takes one, and
   `./config/<id>:/config`.

5. **The shape of that entry is the whole of what a plugin may ask for.** A
   plugin cannot request a second mount, a host path outside its own
   configuration directory, a container or host network mode, a device, a kernel
   capability, a privileged container, a user override, or an entrypoint or
   command of its own — because there is no syntax in which to ask. The bound is
   structural, not a rule a validator has to remember.

6. **The escape hatch is `--stack-dir`, and it is the only one.** An operator
   whose service needs something the generated entry cannot express forks the
   stack and lemonfiber operates it, validating only the manifest contract
   (`F1-R3`). That is an operator taking responsibility for their own machine
   with their eyes open. It is not a plugin: it is not installed, not
   attributed, not journalled as a plugin's change, and not a route a stranger's
   manifest can take on somebody else's behalf.

7. **Nothing widens the generated shape per plugin.** Not by grant, not by flag,
   not by a manifest field held for the purpose. Widening it is an amendment to
   this ADR and to the manifest contract, decided once, for everybody, in the
   open.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **A plugin supplies a Compose fragment** | Inherits everything Compose can express, which is everything. `privileged: true` ends the conversation; a `/var/run/docker.sock` mount is root on the host; `network_mode: host` defeats [C6](../../10-functional/features/c-trust/c6-web-security.md)'s binding tiers without touching `bind`; a second mount breaks [ADR-0006](0006-single-data-mount.md)'s one-`/data` rule silently, turning every import into a copy. Reviewing it means reviewing arbitrary YAML against an unbounded threat model, which is the review that gets done carefully once. |
| **A structured but complete container description** | The same authority with better syntax. Restricting it field by field converges on the generated entry, having first built a second schema and an allow-list to maintain; not restricting it is the row above with extra steps. |
| **A WASM module** | The usual answer, and a genuinely good sandbox — for computation. Nothing a plugin needs is computation: it runs a service and calls an API, both of which are I/O the host must grant anyway, so the sandbox constrains the part nobody feared while the host interface carries all the risk. It also forecloses review — `F3-R10` asks for a readable diff and a `.wasm` is its opposite — and it is a second execution engine to ship, test and cover under [Q](../../40-quality/code-standards.md)'s zero-suppression bar. |
| **A supervised subprocess** | Honest about what it is, and the crash isolation is real. But the process holds lemonfiber's own authority on that machine — the credential store, the Docker socket, the data root — so isolating *faults* buys nothing against *misbehaviour*, which is the threat. Confining it properly needs a different sandbox per platform (seccomp, Landlock, `sandbox-exec`, AppContainer): four implementations of the hardest thing in the product, on a matrix that [already bites](../../20-architecture/platform-matrix.md). |
| **A dynamic library loaded into the core** | No isolation at all: a plugin fault is a lemonfiber crash and a plugin bug is a lemonfiber advisory. It also forbids itself — the workspace sets `unsafe_code = "forbid"`, and loading a shared object is unsafe by construction. |
| **A generated entry, plus an allow-listed passthrough for the rare case** | The reservation F3 already refused once for code: *"reserving a code path 'for the rare case' is how the rare case becomes the common one."* The allow-list is exactly where the next capability gets added under pressure from a plugin somebody wants, and an allow-list extended on the strength of untrusted input is a deny-list wearing a hat. |

## Consequences

**The container is bounded by construction rather than by vigilance.** The
questions that would otherwise be asked of every manifest in review — does this
mount something it shouldn't, does it escape the binding tiers, does it want the
socket — have no way to be true. That is a different kind of guarantee from a
validator that checks for them, because it survives a reviewer having a bad day.

**The review claim becomes true, and smaller.** What a reader of a manifest can
verify is the declaration, not the payload. Saying so plainly is what lets the
rest of the argument be trusted; the image's own trustworthiness is a separate
problem, answered by pinning and provenance rather than by reading.

**Some services cannot be plugins, and that is the intended answer.** Anything
needing a device, a second mount, a kernel capability or another container's
network namespace is not expressible. Gluetun — the one service the catalogue
marks `critical`, because its failure has consequences outside the machine —
could not be a plugin under this rule. That is the right outcome rather than an
awkward one: the service whose misconfiguration exposes the operator's home
address to every peer is not one a stranger installs on their behalf.

**A plugin's service still needs a profile and a form to be reachable**, and
which one it joins is a question this ADR does not answer. It belongs to the
manifest contract, along with how a plugin's service reaches the compose model
without breaking the parity check that holds the manifest and the Compose file
to each other (`REPO-R36`).

**The generator joins the set of things that must be kept honest.** Command
construction is golden-tested for every form on every platform (`Q-R23`) because
it is on the path of everything; the Compose generator is now on the path of
every plugin install and earns the same treatment.

**Digest pinning stops being optional here.** The generated entry names an
image, and naming it by a mutable tag means the thing reviewed and the thing run
can differ without anything changing in the manifest. That is a supply-chain
decision rather than a container-shape one, and it is taken separately.

**Revisit if** a service worth having genuinely cannot be expressed *and* the
demand is broad rather than particular — at which point the answer is to widen
the generated shape here, for everybody, rather than to grant one plugin an
exception.

## Related

- [F3](../../10-functional/features/f-extensibility/f3-stack-manifests.md) — what a plugin is, and the requirements this records the decision behind
- [F1](../../10-functional/features/f-extensibility/f1-customisation.md) — `--stack-dir`, the escape hatch that stays the only one
- [ADR-0006](0006-single-data-mount.md) — the one `/data` mount the generated entry enforces by construction
- [ADR-0001](0001-docker-compose-as-engine.md) — why there is a Compose entry to write at all
- [C6](../../10-functional/features/c-trust/c6-web-security.md) — the binding tiers the core assigns rather than the plugin declaring
- [stack-manifest](../../20-architecture/contracts/stack-manifest.md) — the `[[service]]` vocabulary a plugin declares in
