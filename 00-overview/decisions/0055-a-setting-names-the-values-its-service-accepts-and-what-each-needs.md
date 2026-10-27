# ADR-0055: A setting names the values its service accepts and what each needs

**Status:** Accepted
**Date:** 2026-10-27
**Decided:** 2026-10-27, by the maintainer, Wessel Verheij:

- a setting a manifest reads may declare `one_of`, the values its service accepts, and a
  setting reference or a `[[secret]]` may declare `needs`, the values of other settings
  under which it is written and asked for;
- the core refuses a value outside the choices by name when it is set and when the
  project is generated, and holds a service back, by name, while a value it needs to
  start is missing;
- setup asks for the VPN type and then the provider, from those choices;
- the egress guard runs OpenVPN as well as WireGuard, with the OpenVPN username and
  password held as secrets.

## Context

A setting reference is `{ setting, default }`: the operator's value is written where one
is recorded and the default otherwise, whatever it holds (`ARCH-R229`, `ARCH-R231`).
Neither the manifest nor the core can say which values a service accepts, or that one
setting's value makes sense only beside another's.

The egress guard runs Gluetun with `VPN_TYPE = "wireguard"` written as a constant and the
provider read from `gluetun:provider`, `""` by default. Gluetun reads an empty provider as
Private Internet Access, which it does not run over WireGuard, and exits; the container
restarts and exits again for as long as the stack runs. Setup asks only whether a VPN
carries the torrents, never which provider, so every stack set up with a VPN starts that
way. The same happens to a provider Gluetun does not run over WireGuard, to port
forwarding turned on with a provider that does not forward a port, and to a custom
provider whose endpoint was never given. The operator sees a service restarting, and
the reason only in its log.

An operator whose provider offers only OpenVPN, Private Internet Access among them,
cannot run the egress guard at all.

## Decision

1. **A setting declares its choices.** `one_of` lists the values the service accepts. A
   value may be listed with `needs`, so it is a choice only where other settings hold
   one of the values named. The choices are the setting's, declared once in a manifest.
2. **A reference or a secret declares what it needs.** `needs` on a setting reference or
   a `[[secret]]` names other settings and the values under which the variable is
   written and the secret asked for and held. Where they are not met, the variable is
   not written and nobody is asked for the secret.
3. **A wrong value is refused by name.** Setting a value outside the choices, or a
   change that leaves another setting's value outside its own, is refused, naming the
   setting, the value and the choices. Several settings change in one act, so the VPN
   type and the provider move together. A value the core finds outside the choices
   when it generates the project, such as one filed from an earlier release's
   environment file, keeps its service from starting, named the same way.
4. **A missing value holds its service back.** A reference that declares
   `recorded_with`, the mark of a value only the operator holds and the service needs to
   start (`ARCH-R336`), and whose needs are met, keeps its service, and every service
   that runs through it, from starting until the operator gives it. Status, the doctor
   and each rehearsal name what it waits for, never by value.
5. **Setup asks from the choices.** Where a VPN carries the torrents, setup asks for the
   egress guard's settings that declare choices, each after those its choices need, so
   the VPN type comes before the provider, and then for each value it needs that its
   answers have made needed.
6. **The egress guard runs OpenVPN too.** `gluetun:vpn-type` is `wireguard` or
   `openvpn`, `wireguard` by default. The providers Gluetun runs over each are the
   provider's choices, and the OpenVPN username and password are secrets the operator
   enters, needed only for OpenVPN.

## Consequences

- **A service never restarts in a loop over a value the manifest could have refused.**
  The operator sees a refusal or a hold-back naming the setting, not a crash.
- **Every plugin can declare choices.** The rules are static and declarative, the same
  for every manifest, and the core holds no knowledge of any one service's values.
- **`settings-set` and `settings-clear` take several settings in one act.** The web API
  and the command line change shape; a single setting is still one act.
- **A stack whose recorded provider is outside the choices stops restarting the egress
  guard** and says which setting to change.
- **The egress guard's choices follow the image it pins.** Updating Gluetun means reading
  which providers it runs over each VPN type again.

## Alternatives considered

| Alternative | Why not |
|---|---|
| **`one_of` alone, and a missing `recorded_with` value holds its service back** | Port forwarding turned on with a provider that does not forward a port, and the custom provider's endpoint asked of every provider, still restart in a loop or ask what nobody holds. |
| **An adapter for the egress guard that the core asks to accept its settings** | It adds a contract call and a container for what static rules state, and an adapter cannot stop the container it fronts from starting. |
| **The core knows each VPN provider** | The core would hold one service's knowledge, and a substitute egress guard could not say its own. |

## Revisit when

- a service's accepted values cannot be stated as a list, such as a server name, so a
  value is refused only by the service itself;
- an egress guard needs a file, such as an OpenVPN configuration, that a setting or a
  secret cannot hold.
