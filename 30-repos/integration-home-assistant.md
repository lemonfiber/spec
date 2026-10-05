# Repo: `integration-home-assistant`

**Status:** Accepted

lemonfiber in Home Assistant: a custom integration with the domain `lemonfiber`, installed
from this repository through HACS. Python, Hippocratic 3.0.

**Implements:** [F12 Home Assistant](../10-functional/features/f-extensibility/f12-home-assistant.md).

---

## What this repo is

A Home Assistant integration in the layout HACS reads: `custom_components/lemonfiber/` and
`hacs.json`. It reaches a stack only through [`sdk-python`](sdk-python.md), and only with
an integration key ([C10](../10-functional/features/c-trust/c10-integration-keys.md)).

## What it owns

| Piece | Obligation |
|---|---|
| Config flow | The address, key and pin, verified before an entry exists; reauthentication when a key is refused; reconfiguring the address and pin (`F12-R2`, `F12-R3`) |
| Coordinator | One event stream per entry, gaps shown as unavailable (`F12-R7`) |
| Entities | Exactly what the key's scope admits (`F12-R4` to `F12-R9`) |
| Diagnostics | Withholding the key, the address and the pin (`F12-R10`) |
| Translations | English and Dutch (`F12-R11`) |

## What it must not own

- **The wire.** Shapes, the stream's behaviour and the pin are `sdk-python`'s. The
  integration vendors that client and never edits it.
- **Policy.** Which actions a key may call is the core's published list, not a choice made
  here.
- **The operator password.** It is never asked for.

## Quality bar

Home Assistant's integration quality scale up to and including Platinum (`F12-R12`), and the
organisation's standard on top:

- `pyright` strict, `ruff` with the formatter enforced.
- `pytest` with `pytest-homeassistant-custom-component` at 100% line and branch coverage.
- Mutation testing with a minimum score in CI.
- Home Assistant's `hassfest` and HACS's own validation as required checks.
- The organisation's shared workflows.

## Versioning and the client

The vendored client sits under `custom_components/lemonfiber/_vendor/` at a pinned
`sdk-python` commit, written there by a script, never by hand. A drift check fails when the
pin is behind the client the core's contract asks for, as the companion's `sdk-drift`
does.

## Publishing

Not published to a package registry or to Home Assistant's own catalogue. HACS installs it
from this repository's releases, which ride the version train.

## Related

- [F12 Home Assistant](../10-functional/features/f-extensibility/f12-home-assistant.md) · [C10 Integration keys](../10-functional/features/c-trust/c10-integration-keys.md)
- [`sdk-python`](sdk-python.md)
