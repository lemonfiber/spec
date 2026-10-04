# ADR-0036: A plugin may come from any source the command takes, over the web API too

**Status:** Accepted
**Date:** 2026-10-04
**Decided:** 2026-10-04, by the maintainer, Wessel Verheij: any source the command takes, with a git source fetched only over https from a public host.

## Context

[ADR-0031](0031-a-plugin-and-a-choice-are-web-writes-a-credential-is-not.md) made
installing, updating and removing a plugin web API writes on the premise that the
command names a source by its path on the stack's machine, and rejected installing from
a URL or a git source over the API because `ARCH-R48` forbids the API taking more than
the command. The premise no longer holds. `lemonfiber plugin install` takes a name from
the verified catalogue (`F5-R4`, [ADR-0034](0034-a-catalogue-release-is-signed-with-a-key-the-binary-carries.md))
or a git repository, and ADR-0031 named exactly this as the condition to revisit it.

A source fetched on a request's say-so reaches the network on behalf of whoever sent
the request. A path read from the machine does not. So the question is which sources
the web actions take, now that the command takes all three.

## Decision

**The web actions take every source the command takes**: a catalogue name, a git
repository and a path on the machine. `ARCH-R48` then holds in both directions, and the
companion, which reaches a stack only over the web API (`N1-R16`), can install what the
command can.

A git source named over the web API is held to more than a path is:

1. **It is fetched over https, from a public host.** A name that resolves to a loopback,
   private or link-local address is refused, checked when the fetch is made and again
   for every redirect, so a request cannot point the stack at a service on its own
   network (`ARCH-R152`). This is the check a recipe's call to an external host is held
   to (`F8-R9`).
2. **The rehearsal fetches and states what it fetched.** It names the source and the
   revision it resolved to, and the offer it answers is built from that revision. The
   write fetches again and refuses where the revision moved, naming it, as every other
   moved offer is refused (`F6-R17`, `ARCH-R142`).
3. **Nothing is installed without the offer.** Fetching stages a manifest. What the
   manifest declares is read, refused or offered exactly as a path's is, and lemonfiber
   writes the container ([ADR-0021](0021-a-plugin-is-data-and-lemonfiber-writes-its-container.md)).

ADR-0031's other reasons stand: no secret travels in these requests, each change is
journalled and can be put back, they sit behind the guards every other write does, and
the yes is the offer that was read.

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **Catalogue names only** | Every origin is one the signed index names, but a plugin not yet in the catalogue could be installed at the terminal and not from the companion, so `G1-R1` would carry an exception that is a convenience of the server rather than something the companion is unsuited to. |
| **Any source, unrestricted** | A request that passes the guards could make the stack fetch from an address on its own network. The guards are what every write relies on, and a weakness in them would then reach the network as well as the stack. |
| **A path only, as ADR-0031 had it** | A path is a file on the stack's machine, which an operator on their phone cannot put there, so the action would exist on the API and be usable from nowhere but the machine itself. |

## Consequences

### Positive

- The companion installs from a catalogue name or a repository, as the command does.
- A git source cannot be pointed at the stack's own network, on either surface.

### Negative

- A request that passes the guards can make the stack fetch from a public host. The
  manifest it fetches still has to be offered and agreed to before anything is written.

### Neutral

- ADR-0031 is unchanged apart from the source premise and the rejected alternative this
  supersedes.

## Revisit if

- A source kind is added that fetches by any means other than git over https.
- A fetch gains an effect beyond staging a manifest.

## Related

- [ADR-0031](0031-a-plugin-and-a-choice-are-web-writes-a-credential-is-not.md) — the plugin writes and the choice as web API writes
- [ADR-0034](0034-a-catalogue-release-is-signed-with-a-key-the-binary-carries.md) — the catalogue index, verified offline
- [web API contract](../../20-architecture/contracts/web-api.md) — the actions, their arguments and their refusals
